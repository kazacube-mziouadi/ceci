# -*- coding: utf-8 -*-
from openerp import models, api, fields


class stock_partial_picking(models.TransientModel):
    _inherit = 'stock.partial.picking'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    not_done = fields.Boolean(default=False)
        
        
    def get_make_done(self):
        """
            Héritée dans shipment
        """
        return not self.not_done


    @api.multi
    def do_partial_shipment(self):
        new_picking = self.picking_id.do_partial_shipment(self.line_ids)
        if new_picking:
            new_picking.get_form_view()

        return False