# -*- coding: utf-8 -*-
from openerp import models, api, fields
from openerp.tools.translate import _
from openerp.exceptions import except_orm

import datetime
import pytz

AVAILABLE_DAYS = [
    ('monday', _('Monday')),
    ('tuesday', _('Tuesday')),
    ('wednesday', _('Wednesday')),
    ('thursday', _('Thursday')),
    ('friday', _('Friday')),
    ('saturday', _('Saturday')),
    ('sunday', _('Sunday')),
]



class wizard_create_template_lines(models.TransientModel):
    _name = 'wizard.create.template.lines'
    _rec_name = 'calendar_template_id'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    calendar_template_id = fields.Many2one('calendar.template', string='Calendar', required=True, ondelete='cascade')
    monday = fields.Boolean(default=True)
    tuesday = fields.Boolean(default=True)
    wednesday = fields.Boolean(default=True)
    thursday = fields.Boolean(default=True)
    friday = fields.Boolean(default=True)
    saturday = fields.Boolean(default=False)
    sunday = fields.Boolean(default=False)
    
    start_date = fields.Date()
    end_date = fields.Date()
    
    hour_start0 = fields.Float(string='Hour start', digits=(16,2))
    hour_end0 = fields.Float(string='Hour end', digits=(16,2))
    hour_number0 = fields.Float(string='Hour number', digits=(16,2))
    hour_start1 = fields.Float(string='Hour start', digits=(16,2))
    hour_end1 = fields.Float(string='Hour end', digits=(16,2))
    hour_number1 = fields.Float(string='Hour number', digits=(16,2))
    hour_start2 = fields.Float(string='Hour start', digits=(16,2))
    hour_end2 = fields.Float(string='Hour end', digits=(16,2))
    hour_number2 = fields.Float(string='Hour number', digits=(16,2))
    hour_start3 = fields.Float(string='Hour start', digits=(16,2))
    hour_end3 = fields.Float(string='Hour end', digits=(16,2))
    hour_number3 = fields.Float(string='Hour number', digits=(16,2))
    hour_start4 = fields.Float(string='Hour start', digits=(16,2))
    hour_end4 = fields.Float(string='Hour end', digits=(16,2))
    hour_number4 = fields.Float(string='Hour number', digits=(16,2))
    hour_start5 = fields.Float(string='Hour start', digits=(16,2))
    hour_end5 = fields.Float(string='Hour end', digits=(16,2))
    hour_number5 = fields.Float(string='Hour number', digits=(16,2))
    hour_start6 = fields.Float(string='Hour start', digits=(16,2))
    hour_end6 = fields.Float(string='Hour end', digits=(16,2))
    hour_number6 = fields.Float(string='Hour number', digits=(16,2))


    @api.model
    def default_get(self, fields_list):
        res = super(wizard_create_template_lines, self).default_get(fields_list=fields_list)
        cal_obj = self.env['calendar.template']
        cal = cal_obj.browse(self._context.get('active_id'))
        vals = {
            'start_date': cal.start_date,
            'end_date': cal.end_date,
            'calendar_template_id': cal.id,
        }
 
        res.update(vals)
        return res

    def create_line(self, dow, start_date):
        start, end, number = 'hour_start%(dow)s' % {'dow':dow}, 'hour_end%(dow)s' % {'dow':dow}, 'hour_number%(dow)s' % {'dow':dow}
        line_template_obj = self.env['calendar.template.line']
        # Le bloc de code ci-dessous permet d'enregistrer les dates dans la bonne "timezone" (celle du serveur)
        # car l'utilisateur saisit dans sa timezone 'ex GMT+1'
        server_tz = "UTC"
        dt_value = start_date
        src_tz = pytz.timezone(server_tz)
        dst_tz = pytz.timezone(self._context.get('tz'))
        src_dt = dst_tz.localize(dt_value, is_dst=True)
        dt_value = src_dt.astimezone(src_tz)
        if self[start] > self[end]:
            end_dt_value = dt_value + datetime.timedelta(days=1)
        else:
            end_dt_value = dt_value
            
        vals = {
            'calendar_template_id': self.calendar_template_id.id,
            'hour': self[number],
            'start_date': dt_value + datetime.timedelta(minutes=self[start] * 60),
            'end_date': end_dt_value + datetime.timedelta(minutes=self[end] * 60),
        }
        return line_template_obj.create(vals)


    def _check_date_and_timezone(self):
        result, msg = True, ''
        # Commenté pour pouvoir génerer une ligne a cheval sur deux jours
#         if self.start_date > self.end_date:
#             result = False
#             msg += "\n The start_date must be inferior to the end_date."
            
        if not self.env.user.tz:
            result = False
            msg += "\n The timezone is not set on the user."
            
        return (result, msg)


    @api.one
    def generate_lines(self):
        check, msg = self._check_date_and_timezone()
        if not check:
            raise except_orm(_('Error'), _(msg))

        line_template_obj = self.env['calendar.template.line']
        template_line_ids = line_template_obj.search([('calendar_template_id', '=', self.calendar_template_id.id), 
                                                      ('start_date', '>=', self.start_date), 
                                                      ('start_date', '<=', self.end_date)])
        if template_line_ids:
            template_line_ids.unlink()

        start_date = datetime.datetime.strptime(self.start_date, '%Y-%m-%d')
        end_date = datetime.datetime.strptime(self.end_date, '%Y-%m-%d') + datetime.timedelta(days=1)
        interval_days = (end_date - start_date).days
        cpt = 1
        while cpt <= interval_days:
            # Traitement ici
            dow = start_date.isoweekday()
            for i, j in enumerate(AVAILABLE_DAYS):
                if self[j[0]] and dow == i + 1:
                    self.create_line(i, start_date)

            # On incremente la date à la fin de la boucle
            start_date += datetime.timedelta(days=1)
            cpt += 1

        return {'type': 'ir.actions.act_window_close'}