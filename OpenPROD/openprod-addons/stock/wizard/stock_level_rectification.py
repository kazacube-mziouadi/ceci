# -*- coding: utf-8 -*-
from openerp import models, fields, api

class stock_level_rectification(models.TransientModel):
    """ 
    Stock level rectification 
    """
    _name = 'stock.level.rectification'
    _description = 'Stock level rectification'

    #===========================================================================
    # COLUMNS
    #===========================================================================
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='cascade', help='Let this field empty to compute all products')

    @api.one
    def do_rectification(self):
        if self.product_id:
            self.product_id.stock_level_rectification()
        else:
            self.env.cr.execute("""UPDATE stock_level sl SET uom_qty = slr.dynamic_qty FROM stock_level_report slr WHERE sl.id = slr.sl_id AND slr.static_qty <> slr.dynamic_qty""")

        return {'type': 'ir.actions.act_window_close'}