# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm

class print_wo(models.TransientModel):
    """ 
        Wizard which allow to print work orders with plans
    """
    _name = 'print.wo'
    _description = 'Wizard which allow to print work orders with plans'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    print_plan = fields.Boolean(string='Print plans', default=False)
    mrp_workorder_id = fields.Many2one('mrp.workorder', string='Work order', required=False, ondelete='set null')
    
    @api.model
    def default_get(self, fields_list):
        res = super(print_wo, self).default_get(fields_list=fields_list)
        if self.env.context.get('active_model') == 'mrp.workorder' and self.env.context.get('active_id'):
            res['mrp_workorder_id'] = self.env.context.get('active_id')
            
        return res
    
    
    @api.multi
    def action_print_wo(self):
        """
            Fonction permettant de modifier le fournisseur d'un achat
        """
        for wizard in self:
            if wizard.mrp_workorder_id:
                wizard.mrp_workorder_id.do_print_wo(wizard.print_plan, print_plan_mo=wizard.print_plan)
                return True
            else:
                return  {'type': 'ir.actions.act_window_close'}
            
            
            

class print_mo(models.TransientModel):
    """ 
        Wizard which allow to print work orders with plans
    """
    _name = 'print.mo'
    _description = 'Wizard which allow to print work orders with plans'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    print_plan = fields.Boolean(string='Print plans', default=False)
    mo_id = fields.Many2one('mrp.manufacturingorder', string='Manufacturing order', required=False, ondelete='set null')
    
    @api.model
    def default_get(self, fields_list):
        res = super(print_mo, self).default_get(fields_list=fields_list)
        if self.env.context.get('active_model') == 'mrp.manufacturingorder' and self.env.context.get('active_id'):
            res['mo_id'] = self.env.context.get('active_id')
            
        return res
    
    
    @api.multi
    def action_print_mo(self):
        """
            Fonction permettant de modifier le fournisseur d'un achat
        """
        for wizard in self:
            if wizard.mo_id and wizard.mo_id.workorder_ids:
                wizard.mo_id.workorder_ids.do_print_wo(wizard.print_plan, print_plan_mo=wizard.print_plan)
                return True
            else:
                return  {'type': 'ir.actions.act_window_close'}