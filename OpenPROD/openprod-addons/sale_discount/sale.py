# -*- coding: utf-8 -*-
from openerp import models, api, fields
import openerp.addons.decimal_precision as dp


class sale_order_line(models.Model):
    _inherit = 'sale.order.line'

    @api.one
    @api.depends('price_unit_without_discount', 'fixed_discount', 'variable_discount', 'uoi_qty')
    def _compute_price_unit_discount(self):
        """
            Fonction qui permet de calculer le prix par rapport aux remise
        """
        if self.price_unit_without_discount > 0:
            price_unit = self.price_unit_without_discount - self.fixed_discount - self.variable_discount*self.price_unit_without_discount/100
            if price_unit < 0:
                price_unit = 0.0
        else:
            price_unit = self.price_unit_without_discount
            
        self.price_unit = price_unit
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    price_unit = fields.Float(string='Price unit', digits=dp.get_precision('Product price'), compute='_compute_price_unit_discount', store=True)
    
    
    @api.multi
    def write(self, vals=None):
        if 'price_unit' in vals and ('price_unit_without_discount' not in vals or not vals['price_unit_without_discount']):
            vals['price_unit_without_discount'] = vals['price_unit']
            
        return super(sale_order_line, self).write(vals=vals)
