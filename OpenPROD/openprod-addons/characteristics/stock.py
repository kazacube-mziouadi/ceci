# coding: utf-8

from openerp import models, fields, api

class stock_label(models.Model):
    _inherit = 'stock.label'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    characteristics_ids = fields.One2many('characteristic', 'label_id', string='Characteristics')
    
    @api.model
    def create(self, vals):
        res = super(stock_label, self).create(vals=vals)
        if vals and 'product_id' in vals:
            self.env['product.product'].browse(vals['product_id']).characteristics_ids.copy(default={'product_id': False,
                                                                                                     'label_id': res.id})
            
        return res