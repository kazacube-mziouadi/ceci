# coding: utf-8
from openerp import models, fields, api

class stock_move(models.Model):
    _inherit = 'stock.move'
            
    track_label = fields.Boolean(related='product_id.track_label', readonly=True)
    #consumed_qty = fields.Float(string='Consumed quantity', default=0.0, required=False, related="wo_consumption_id.quantity")
    @api.one
    @api.depends('wo_consumption_id')
    def _compute_consumed_qty(self):
        self.consumed_qty = sum([x.uom_qty for x in self.wo_consumption_id.move_ids if x.product_id == self.product_id])
            
    consumed_qty = fields.Float(string='Consumed qty', compute='_compute_consumed_qty')

