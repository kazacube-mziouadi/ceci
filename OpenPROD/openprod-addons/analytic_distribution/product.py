# -*- coding: utf-8 -*-
from openerp import models, api, fields
from openerp.tools.translate import _


class product_product(models.Model):
    _inherit = 'product.product'
    
    @api.model
    def _type_compute_analytic_prod_get(self):
        return [
                ('theoretical', _('Theoretical')),
                ('real', _('Real')),
                       ]

    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    sale_pad_id = fields.Many2one('product.analytic.distribution', string='Analytic distribution', 
                                  required=False, ondelete='restrict')
    purchase_pad_id = fields.Many2one('product.analytic.distribution', string='Analytic distribution', 
                                      required=False, ondelete='restrict')
    
    prod_pad_id = fields.Many2one('product.analytic.distribution', string='Analytic distribution', 
                                  required=False, ondelete='restrict')
    type_compute_analytic_prod = fields.Selection('_type_compute_analytic_prod_get', string='Type compute', default='theoretical')