# -*- coding: utf-8 -*-

from openerp import models, fields, api, _

class product_product(models.Model):
    _inherit = 'product.product'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    # Douane
    customs_code = fields.Char(size=32, required=False, help='Customs code')
    customs_price = fields.Float(string='Customs price', default=0.0, required=False)
    customs_unit_id = fields.Many2one('product.uom', string='Customs unit', required=False, ondelete='restrict')
    customs_currency_id = fields.Many2one('res.currency', string='Customs currency', required=False, ondelete='restrict')
    customs_stat_nb = fields.Char(string='Customs statistic number', required=False, size=64)
    is_customs_price = fields.Boolean(string='Custome price', default=False, hemlp='Manage a specific price for customs')