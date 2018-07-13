# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError

class stock_move_reserve(models.Model):
    """ 
        Stock move report
    """
    _inherit="stock.move.reserve"

    #===========================================================================
    # COLUMNS
    #===========================================================================
    outgoing_wo_id = fields.Many2one('mrp.workorder', string='WO', required=False, ondelete='set null')
    incoming_wo_id = fields.Many2one('mrp.workorder', string='WO consumption', required=False, ondelete='set null')
    
    
    
class display_reservation(models.TransientModel):
    """ 
        Wizard to show reservations for the selected product
    """
    _inherit = 'display.reservation'
    
    def values_stock_move_reserve(self, move, stock_quantity):
        values = super(display_reservation, self).values_stock_move_reserve(move, stock_quantity)
        values['outgoing_wo_id'] = move.wo_outgoing_id.id
        values['incoming_wo_id'] = move.wo_incoming_id.id
        return values