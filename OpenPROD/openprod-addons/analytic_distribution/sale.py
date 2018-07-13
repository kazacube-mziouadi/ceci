# -*- coding: utf-8 -*-
from openerp import models, api, fields

class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    analytic_distribution_ids = fields.One2many('purchase.sale.analytic.distribution', 'analytic_sale_order_line_id',  
                                                string='Analytic distribution', copy=True)
    
    
    @api.onchange('product_id', 'property_ids')
    def _onchange_product_id(self):
        """
            Surcharge du onchange du produit afin d'ajouter les lignes de distribution analytique
        """
        res = super(sale_order_line, self)._onchange_product_id()
        if self.product_id and self.product_id.sale_pad_id:
            pad = self.product_id.sale_pad_id
            list_line = []
            for line in pad.distribution_ids:
                vals = {
                        'company_id': pad.company_id.id,
                        'type': line.type,
                        'value': line.value,
                        'account_id': line.account_id.id,
                        }
                list_line.append([0, False, vals])
            
            self.analytic_distribution_ids = list_line
        else:
            self.analytic_distribution_ids = []
        
        return res
    
    
    def create_sale_order_line(self, sale=False, product=None, values=None, forced_qty=False, forced_price_unit=None):
        """
            Surcharge de la méthode de création des lignes de vente afin de prendre en compte la
            distribution analytique
        """
        res = super(sale_order_line, self).create_sale_order_line(sale=sale, product=product, values=values, 
                                                                  forced_qty=forced_qty, forced_price_unit=forced_price_unit)
        if not 'analytic_distribution_ids' in values:
            if res.product_id and res.product_id.sale_pad_id:
                pad = res.product_id.sale_pad_id
                list_line = []
                for line in pad.distribution_ids:
                    vals = {
                            'analytic_sale_order_line_id': res.id,
                            'company_id': pad.company_id.id,
                            'type': line.type,
                            'value': line.value,
                            'account_id': line.account_id.id,
                            }
                    list_line.append([0, False, vals])
                
                res.write({'analytic_distribution_ids': list_line})
        
        return res
