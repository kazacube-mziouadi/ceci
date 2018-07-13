# -*- coding: utf-8 -*-
from openerp import models, api, fields
import openerp.addons.decimal_precision as dp
    
    
class shipment_volume_calculate(models.TransientModel):
    _name = 'stock.print.picking.wizard'
    #===========================================================================
    # COLUMNS
    #===========================================================================
    picking_ids = fields.Many2many('stock.picking')
    
    @api.multi
    def validate(self):
        for wizard_rc in self:
            if wizard_rc.picking_ids:
                wizard_rc.picking_ids.print_picking_button()
                
        return True
        
        
    @api.model    
    def default_get(self, fields):
        res = super(shipment_volume_calculate, self).default_get(fields)
        res['picking_ids'] = self.env.context['active_ids']
        return res