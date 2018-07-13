# -*- coding: utf-8 -*-
from openerp import models, api

class stock_partial_picking_line(models.TransientModel):
    """ 
    Partial picking line
    """
    _inherit = 'stock.partial.picking.line'
    def manage_scrap_compute(self, picking):
        res = super(stock_partial_picking_line, self).manage_scrap_compute(picking)
        if res and self.move_id.purchase_line_id:
            purchase_qty = self.partial_picking_id.get_order_qty(self.move_id)
            if ((self.move_id.uom_qty - self.uom_qty) * 100 / purchase_qty) > self.product_id.purchase_remainder_percentage:
                res = True
            else:
                res = False
            
        return res
    
    
    
class stock_partial_picking(models.TransientModel):
    """ 
    Partial picking 
    """
    _inherit = 'stock.partial.picking'
    
    def get_order_qty(self, move):
        if move.purchase_line_id:
            qty = move.purchase_line_id.uom_qty
            if move.purchase_line_id.uom_id != move.uom_id:
                res = self.env['product.uom']._compute_qty_obj(move.purchase_line_id.uom_id, move.purchase_line_id.uom_qty, move.uom_id)
            else:
                res = qty
        else:
            res = super(stock_partial_picking, self).get_order_qty(move)
            
        return res