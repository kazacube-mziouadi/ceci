# coding: utf-8
from openerp import models, api, _, fields


class stock_move(models.Model):
    _inherit = 'stock.move'
    _description = 'Stock move'
        
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    delivery_program_id = fields.Many2one('delivery.program', string='Delivery program', ondelete='cascade')



class stock_warehouse(models.Model):
    _inherit = 'stock.warehouse'
    _description = 'Stock warehouse'
        
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    reservation_location_id = fields.Many2one('stock.location', string='Reservation location', required=False, ondelete='restrict', default=lambda self: self.env.ref('stock_location.stock_location_customers'))