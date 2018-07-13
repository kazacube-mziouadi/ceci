# coding: utf-8

from openerp import models, api, fields
from openerp.exceptions import except_orm
from openerp.tools.translate import _

class mrp_workorder(models.Model):
    _inherit = 'mrp.workorder'
    
    @api.one
    @api.depends('next_wo_ids.planned_start_date', 'prev_wo_ids.planned_end_date')
    def _compute_prev_next_step(self):
        #TODO Sylvain: à commenter
        prev_step = sorted(self.prev_wo_ids, key=lambda x: x.planned_end_date, reverse=True)
        next_step = sorted(self.next_wo_ids, key=lambda x: x.planned_start_date)
        self.prev_step = prev_step[0].planned_end_date if len(prev_step) else None
        self.next_step = next_step[0].planned_start_date if len(next_step) else None
        self.prev_id = prev_step[0].id if len(prev_step) else None
        self.next_id = next_step[0].id if len(next_step) else None
    
            
    client_date = fields.Date(related='mo_id.requested_date', readonly=True)
    sale_order_id = fields.Many2one(related='sale_line_id.sale_order_id', readonly=True)
    prev_step = fields.Datetime(string='Prev Step', compute="_compute_prev_next_step", store=True)
    next_step = fields.Datetime(string='Next Step', compute="_compute_prev_next_step", store=True)
    prev_id = fields.Integer(string='Prev Step ID', compute="_compute_prev_next_step", store=True)
    next_id = fields.Integer(string='Next Step ID', compute="_compute_prev_next_step", store=True)
    
    @api.multi
    def reschedule(self, new_start_date, new_end_date):
        #TODO Sylvain: à commenter
        self.ensure_one()
            
        if self.group_wo_id:
            wo_ids = self.group_wo_id.wo_ids
            self.group_wo_id.write({'planned_start_date': new_start_date})
        else:
            wo_ids = self
            if self.is_at_earlier:
                for wo_id in wo_ids:
                    end_date = wo_id.action_plannification_wo_at_earlier(new_start_date, automatic_purchase=False, is_procur_level_manufact=False, is_procur_level_purchase=False, no_modif_prio_date=False)
            else:
                for wo_id in wo_ids:
                    start_date = wo_id.action_plannification_wo_at_the_latest(new_end_date, automatic_purchase=False, is_procur_level_manufact=False, is_procur_level_purchase=False, no_modif_prio_date=False)
        return [{'wo_id': x.id, 'start_date': x.planned_start_date, 'end_date': x.planned_end_date} for x in wo_ids]
    
