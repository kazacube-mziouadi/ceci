# coding: utf-8

from openerp import models, api, fields
from openerp.exceptions import except_orm
from openerp.tools.translate import _

class mrp_workorder(models.Model):
    _inherit = 'mrp.workorder'

    #===========================================================================
    # Bac à sable
    #===========================================================================
    sandbox_first_resource_id = fields.Many2one('mrp.resource', string="First Resource", required=False, ondelete='restrict')
    sandbox_planned_start_date = fields.Datetime(string='Planned Start Date')
    sandbox_planned_end_date = fields.Datetime(string='Planned End Date')
    asynchronous = fields.Boolean(string='Asynchronous', default=False)

    @api.multi
    def reschedule(self, new_start_date, new_end_date , is_sandbox=False):      
        if is_sandbox : 
            self.ensure_one()  
            if self.is_at_earlier :
                dates = self.sandbox_first_resource_id.calendar_id.get_dates(new_start_date, self.total_time_theo)
            else :
                dates = self.sandbox_first_resource_id.calendar_id.get_dates_inverse(new_end_date, self.total_time_theo)
            self.write({ 'sandbox_planned_start_date' :  dates['start_date'] , 'sandbox_planned_end_date' :  dates['end_date'] , 'asynchronous' : True })
            return [{'wo_id': self.id, 'start_date': dates['start_date'], 'end_date': dates['end_date']}]
        else :
            return super(mrp_workorder,self).reschedule(new_start_date, new_end_date)

    @api.multi
    def write(self, vals):
        if 'planned_start_date' in vals:
            vals['sandbox_planned_start_date'] = vals['planned_start_date']
        if 'planned_end_date' in vals:
            vals['sandbox_planned_end_date'] = vals['planned_end_date']
        if 'first_resource_id' in vals:
            vals['sandbox_first_resource_id'] = vals['first_resource_id']
        return super(mrp_workorder, self).write(vals)
    
    @api.model
    def create(self, vals):
        workorder = super(mrp_workorder, self).create(vals)
        if 'wo_resource_ids' in vals :
            workorder.sandbox_first_resource_id = workorder.first_resource_id
        return workorder

    @api.multi
    def sandbox_validate (self):
        new_resource_id = self.sandbox_first_resource_id
        wo_resource = self.env['mrp.wo.resource'].search([('wo_id', '=', self.id)], order="sequence ASC", limit=1)
        resource = self.env['mrp.resource'].search([('id', '=', new_resource_id.id )])
        if wo_resource.resource_category_id not in resource.category_resource_ids :
            return False
        self.write({ 'asynchronous' : False , 'planned_start_date' : self.sandbox_planned_start_date , 'planned_end_date' : self.sandbox_planned_end_date })
        self.change_resource(wo_resource, resource, wo_resource.rl_resource_category_id)
        
    @api.multi
    def sandbox_reset (self):
        self.write({ 'asynchronous' : False , 'sandbox_planned_start_date' : self.planned_start_date , 'sandbox_planned_end_date' : self.planned_end_date , 'sandbox_first_resource_id' : self.first_resource_id.id  })
        return {'sandbox_planned_start_date': self.planned_start_date , 'sandbox_planned_end_date': self.planned_start_date ,  'sandbox_first_resource_id' : self.first_resource_id.id }

    @api.model
    def sandbox_reset_all(self):
        list_wo = self.search([('asynchronous','=',True),('state', 'not in', ['draft', 'done', 'cancel'])])
        for wo in list_wo :
            wo.write({ 'asynchronous' : False , 'sandbox_planned_start_date' : wo.planned_start_date , 'sandbox_planned_end_date' : wo.planned_end_date , 'sandbox_first_resource_id' : wo.first_resource_id.id  })
        return [{'wo_id': x.id, 'start_date': x.planned_start_date, 'end_date': x.planned_end_date , 'first_resource_id' : x.first_resource_id.id} for x in list_wo]

    @api.model
    def sandbox_validate_all(self):
        list_wo = self.search([('asynchronous','=',True),('state', 'not in', ['draft', 'done', 'cancel'])])
        for wo in list_wo :
            new_resource_id = wo.sandbox_first_resource_id
            wo_resource = self.env['mrp.wo.resource'].search([('wo_id', '=', wo.id)], order="sequence ASC", limit=1)
            resource = self.env['mrp.resource'].search([('id', '=', new_resource_id.id )])
            if wo_resource.resource_category_id in resource.category_resource_ids :
                wo.write({ 'asynchronous' : False , 'planned_start_date' : wo.sandbox_planned_start_date , 'planned_end_date' : wo.sandbox_planned_end_date })
                wo.change_resource(wo_resource, resource, wo_resource.rl_resource_category_id)

