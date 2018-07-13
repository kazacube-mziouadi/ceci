# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm

class print_wo(models.TransientModel):
    """ 
        Wizard which allow to print work orders with plans
    """
    _inherit = 'print.wo'

    
    @api.model
    def default_get(self, fields_list):
        res = super(print_wo, self).default_get(fields_list=fields_list)
        if self.env.context.get('active_model') == 'schedule.planning.mo' and self.env.context.get('active_id'):
            spm_rcs = self.env['schedule.planning.mo'].browse(self.env.context.get('active_id'))
            res['mrp_workorder_id'] = spm_rcs.wo_id.id
            
        return res
    

class print_mo(models.TransientModel):
    """ 
        Wizard which allow to print work orders with plans
    """
    _inherit = 'print.mo'

    
    @api.model
    def default_get(self, fields_list):
        res = super(print_mo, self).default_get(fields_list=fields_list)
        if self.env.context.get('active_model') == 'schedule.planning.mo' and self.env.context.get('active_id'):
            spm_rcs = self.env['schedule.planning.mo'].browse(self.env.context.get('active_id'))
            res['mrp_workorder_id'] = spm_rcs.mo_id.id
            
        return res