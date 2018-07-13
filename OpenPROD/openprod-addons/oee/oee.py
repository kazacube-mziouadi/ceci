# -*- coding: utf-8 -*-
import datetime
from collections import defaultdict

from openerp import models, api, fields, _
from openerp.exceptions import UserError
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT


help_period = """ Number of days from today. 1 for 24h, 2 for 48h ... """


class oee(models.Model):
    """
    Overall Equipment Effectiveness
    """
    _name = 'oee'
    _description = 'Overall Equipment Effectiveness'

    _sql_constraints = [
        ('period_1_positive', 'CHECK(period_1 >= 0)',
         'Period 1 must be positive'),
        ('period_2_positive', 'CHECK(period_2 >= 0)',
         'Period 2 must be positive'),
    ]

    @api.depends('period_1', 'period_2')
    @api.one
    def _compute_oee(self):
        self.oee_period_1 = self._get_oee(self.period_1)
        self.oee_period_2 = self._get_oee(self.period_2)

    @api.depends('resource_id')
    @api.one
    def _compute_last_mo(self):
        last_timetracking = self.env['resource.timetracking'].search([
            ('resource_id', '=', self.resource_id.id),
            ('activity', '=', 'production'),
        ], order='start_date desc', limit=1)
        self.last_mo_id = last_timetracking.wo_id.mo_id.id

    @api.depends('resource_id')
    @api.one
    def _compute_last_activity(self):
        timetracking_obj = self.env['resource.timetracking']
        last_timetracking = timetracking_obj.search([
            ('resource_id', '=', self.resource_id.id),
        ], order='start_date desc', limit=1)
        self.last_activity = last_timetracking.activity
        self.last_activity_start_date = last_timetracking.start_date
        self.last_time_ids = timetracking_obj.search([
            ('resource_id', '=', self.resource_id.id),
        ], limit=10, order="start_date desc").ids

    resource_id = fields.Many2one('mrp.resource', required=True)
    name = fields.Char(related='resource_id.name', store=True, readonly=True)
    area_id = fields.Many2one('mrp.area', related='resource_id.area_id',
                              store=True, readonly=True)
    period_1 = fields.Integer(string='Period 1', required=True,
                              help=help_period)
    oee_period_1 = fields.Float(compute='_compute_oee', string='OEE period 1')
    period_2 = fields.Integer(string='Period 2', required=True,
                              help=help_period)
    oee_period_2 = fields.Float(compute='_compute_oee', string='OEE period 2')
    last_mo_id = fields.Many2one('mrp.manufacturingorder', string="Last MO",
                                 compute='_compute_last_mo')
    last_activity = fields.Char(compute='_compute_last_activity')
    last_activity_start_date = fields.Datetime(
        string="Last activity date",
        compute='_compute_last_activity')
    last_time_ids = fields.One2many('resource.timetracking',
                                    compute='_compute_last_activity')

    def _get_oee(self, period):
        self.ensure_one()
        if not period:
            return 0
        calendar_line_obj = self.env['calendar.line']
        start_date = date_for_period(period)
        end_date = datetime.date.today() + datetime.timedelta(days=1)
        end_date_str = end_date.strftime(DEFAULT_SERVER_DATE_FORMAT)
        open_time_lines = calendar_line_obj.search([
            ('real_start_date', '>=', start_date),
            ('real_end_date', '<=', end_date_str),
            ('calendar_id', '=', self.resource_id.calendar_id.id),
        ])
        open_time = sum(x.real_hour for x in open_time_lines)
        if open_time == 0:
            raise UserError(_('Resource is closed for the period'))
        timetracking_obj = self.env['resource.timetracking']
        production_time_lines = timetracking_obj.search([
            ('resource_id', '=', self.resource_id.id),
            ('start_date', '>=', start_date),
            ('activity', '=', 'production'),
        ])
        production_time = sum(x.time for x in production_time_lines)
        oee_value = 100 * production_time / open_time
        return round(oee_value, 2)

    @api.model
    def get_timetracking_totals(self, start, end):
        calendar_line_obj = self.env['calendar.line']
        tt = defaultdict(lambda: defaultdict(int))
        tt_lines = self.env['resource.timetracking'].search([
            ('start_date', '>=', start),
            ('end_date', '<=', end),
        ])
        open_time_lines = calendar_line_obj.search([
            ('real_start_date', '>=', start),
            ('real_end_date', '<=', end),
        ])
        open_time_by_calendar = defaultdict(int)
        for line in open_time_lines:
            open_time_by_calendar[line.calendar_id.id] += line.real_hour
        for line in tt_lines:
            open_time = open_time_by_calendar[line.resource_id.calendar_id.id]
            activity = line.activity
            tt[line.resource_id.id][activity] += (
                0 if not open_time
                else 100 * line.time / open_time)
        return tt

    @api.multi
    def write(self, vals):
        if 'area_id' in vals:
            vals.pop('area_id')
            raise UserError(_('You can\'t change area from there'))
        return super(oee, self).write(vals)


def date_for_period(period):
    """ Retourne le jour aujourd'hui - period dans un format
        utilisable par la recherche """
    if not period:
        return fields.Date.today()
    else:
        start_date = datetime.date.today() - datetime.timedelta(days=period)
        return start_date.strftime(DEFAULT_SERVER_DATE_FORMAT)
