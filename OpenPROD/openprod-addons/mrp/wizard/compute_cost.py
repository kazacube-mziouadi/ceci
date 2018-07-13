# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm

class compute_real_cost_mo(models.TransientModel):
    """ 
        Compute real cost MO
    """
    _name = 'compute.real.cost.mo'
    _description = 'Compute real cost MO'
    
    @api.model
    def default_get(self, fields_list):
        res = super(compute_real_cost_mo, self).default_get(fields_list=fields_list)
        if self.env.context.get('active_ids'):
            res['mo_ids'] = self.env.context.get('active_ids')
            
        return res
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    mo_ids = fields.Many2many('mrp.manufacturingorder', 'compute_real_cost_mo_manufacturingorder_rel', 'wiz_id', 
                                       'manufacturingorder_id', string='MO', readonly=True)    
    
    
    @api.multi
    def action_compute_cost(self):
        """
            Fonction lance le calcul des couts
        """
        for wizard in self:
            wizard.mo_ids.button_compute_real_costs()
            return  {'type': 'ir.actions.act_window_close'}
            


class compute_theo_cost_mo(models.TransientModel):
    """ 
        Compute theo cost MO
    """
    _name = 'compute.theo.cost.mo'
    _description = 'Compute theo cost MO'
    
    @api.model
    def default_get(self, fields_list):
        res = super(compute_theo_cost_mo, self).default_get(fields_list=fields_list)
        if self.env.context.get('active_ids'):
            res['mo_ids'] = self.env.context.get('active_ids')
            
        return res
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    mo_ids = fields.Many2many('mrp.manufacturingorder', 'compute_theo_cost_mo_manufacturingorder_rel', 'wiz_id', 
                                       'manufacturingorder_id', string='MO', readonly=True)    
    
    
    @api.multi
    def action_compute_cost(self):
        """
            Fonction lance le calcul des couts
        """
        for wizard in self:
            wizard.mo_ids.button_compute_theo_costs()
            return  {'type': 'ir.actions.act_window_close'}
        
        
        
class compute_bom_cost(models.TransientModel):
    """ 
        Compute bom cost
    """
    _name = 'compute.bom.cost'
    _description = 'Compute bom cost'
    
    @api.model
    def default_get(self, fields_list):
        res = super(compute_bom_cost, self).default_get(fields_list=fields_list)
        if self.env.context.get('active_ids'):
            res['bom_ids'] = self.env.context.get('active_ids')
            
        return res
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    bom_ids = fields.Many2many('mrp.bom', 'compute_bom_cost_mo_bom_rel', 'wiz_id', 
                                       'bom_id', string='BoM', readonly=True)   
    all = fields.Boolean(string='All records', default=False) 
    
    
    @api.multi
    def action_compute_cost(self):
        """
            Fonction lance le calcul des couts
        """
        for wizard in self:
            if wizard.all:
                bom_rcs = self.env['mrp.bom'].search([])
                bom_rcs.action_compute_price()
            else:
                wizard.bom_ids.action_compute_price()
            
            return  {'type': 'ir.actions.act_window_close'}
        


class compute_routing_cost(models.TransientModel):
    """ 
        Compute routing cost
    """
    _name = 'compute.routing.cost'
    _description = 'Compute routing cost'
    
    @api.model
    def default_get(self, fields_list):
        res = super(compute_routing_cost, self).default_get(fields_list=fields_list)
        if self.env.context.get('active_ids'):
            res['routing_ids'] = self.env.context.get('active_ids')
            
        return res
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    routing_ids = fields.Many2many('mrp.routing', 'compute_routing_cost_mo_routing_rel', 'wiz_id', 
                                       'routing_id', string='Routing', readonly=True)    
    all = fields.Boolean(string='All records', default=False) 
    
    @api.multi
    def action_compute_cost(self):
        """
            Fonction lance le calcul des couts
        """
        for wizard in self:
            if wizard.all:
                routing_rcs = self.env['mrp.routing'].search([])
                routing_rcs.action_compute_price()
            else:
                wizard.routing_ids.action_compute_price()
            
            return  {'type': 'ir.actions.act_window_close'}        




class compute_generate_op_cons(models.TransientModel):
    """ 
        Compute generate_op_cons
    """
    _name = 'compute.generate.op.cons'
    _description = 'Compute routing cost'
    
    @api.model
    def default_get(self, fields_list):
        res = super(compute_generate_op_cons, self).default_get(fields_list=fields_list)
        if self.env.context.get('active_ids'):
            res['routing_ids'] = self.env.context.get('active_ids')
            
        return res
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    routing_ids = fields.Many2many('mrp.routing', 'compute_routing_cost_mo_routing_rel', 'wiz_id', 
                                       'routing_id', string='Routing', readonly=True)    
    all = fields.Boolean(string='All records', default=False)
    
    @api.multi
    def action_generate_op_cons(self):
        """
            Fonction lance le lien de consomation des liges de gamme
        """
        for wizard in self:
            if wizard.all:
                routing_rcs = self.env['mrp.routing'].search([])
                routing_rcs.action_compute_price()
            else:
                wizard.routing_ids.boutton_generate_op_cons()
            
            return  {'type': 'ir.actions.act_window_close'}        
             
        