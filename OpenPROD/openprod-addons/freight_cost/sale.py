# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _


class sale_order(models.Model):
    """ 
    Sale module 
    """
    _inherit = 'sale.order'
    _description = 'Sale module'
    
    
    @api.one
    @api.depends('sale_incoterm_id', 'sale_invoice_postage', 'sale_threshold', 'amount_ex_taxes')
    def _compute_is_freight_cost(self):
        is_freight_cost = True
        if self.sale_incoterm_id.id == 1:
            is_freight_cost = False
        elif self.sale_invoice_postage == 'never':
            is_freight_cost = False
            
        self.is_freight_cost = is_freight_cost


    @api.one
    @api.depends('order_line_ids')
    def _compute_freight_cost(self):
        freight_cost_total = 0.0
        for line in self.order_line_ids:
            if line.is_freight_cost:
                freight_cost_total += line.price_unit * line.uoi_qty
                
        self.freight_cost_total = freight_cost_total
        
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    amount_ex_taxes = fields.Float(string='Amount excluding taxes', default=0.0, required=False, compute='_compute_amount')
    is_freight_cost = fields.Boolean(string='Freight cost', compute='_compute_is_freight_cost')
    freight_cost_total = fields.Float(string='Freight cost total', compute='_compute_freight_cost', default=0.0, required=False)
    
    
    
class sale_order_line(models.Model):
    """ 
    Sale line module 
    """
    _inherit = 'sale.order.line'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    is_freight_cost = fields.Boolean(string='Freight cost', default=False)