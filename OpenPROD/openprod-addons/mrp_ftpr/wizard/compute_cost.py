# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm



class compute_ftpr_cost(models.TransientModel):
    """ 
        Compute ftpr cost
    """
    _name = 'compute.ftpr.cost'
    _description = 'Compute routing cost'
    
    @api.model
    def default_get(self, fields_list):
        res = super(compute_ftpr_cost, self).default_get(fields_list=fields_list)
        if self.env.context.get('active_ids'):
            res['ftpr_ids'] = self.env.context.get('active_ids')
            
        return res
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    ftpr_ids = fields.Many2many('mrp.ftpr', 'compute_ftpr_cost_mo_routing_rel', 'wiz_id', 
                                       'ftpr_id', string='Ftpr', readonly=True)    
    
    
    @api.multi
    def action_compute_cost(self):
        """
            Fonction lance le calcul des couts
        """
        for wizard in self:
            wizard.ftpr_ids.action_compute_price()
            return  {'type': 'ir.actions.act_window_close'}        
        
        