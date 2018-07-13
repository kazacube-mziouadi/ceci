from openerp import models, fields, api

class WizardSandboxReset(models.TransientModel):
    _name = 'sandbox.wizard_reset'

    @api.multi
    def reset(self):
        list_id = self.env.context.get('default_wo_ids')
        list_wo = self.env['mrp.workorder'].search([('state', 'not in', ['draft', 'done', 'cancel']),('id' ,'in' , list_id)])
        for wo in list_wo :
            wo.write({ 'asynchronous' : False , 'sandbox_planned_start_date' : wo.planned_start_date , 'sandbox_planned_end_date' : wo.planned_end_date , 'sandbox_first_resource_id' : wo.first_resource_id.id  })
        return {'type': 'ir.actions.act_window_close'} 


class WizardSandboxValidate(models.TransientModel):
    _name = 'sandbox.wizard_validate'

    @api.multi
    def validate(self):
        list_id = self.env.context.get('default_wo_ids')
        list_wo = self.env['mrp.workorder'].search([('asynchronous','=',True),('state', 'not in', ['draft', 'done', 'cancel']),('id' ,'in' , list_id)])
        for wo in list_wo :
            new_resource_id = wo.sandbox_first_resource_id
            wo_resource = self.env['mrp.wo.resource'].search([('wo_id', '=', wo.id)], order="sequence ASC", limit=1)
            resource = self.env['mrp.resource'].search([('id', '=', new_resource_id.id )])
            if wo_resource.resource_category_id in resource.category_resource_ids :
                wo.write({ 'asynchronous' : False , 'planned_start_date' : wo.sandbox_planned_start_date , 'planned_end_date' : wo.sandbox_planned_end_date })
                wo.change_resource(wo_resource, resource, wo_resource.rl_resource_category_id)
        return {'type': 'ir.actions.act_window_close'} 