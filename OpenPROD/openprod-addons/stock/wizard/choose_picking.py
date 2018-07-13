# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp

class choose_picking_wizard(models.TransientModel):
    """ 
        Choose picking
    """
    _name = 'choose.picking.wizard'
    _description = 'Choose picking'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    transfer_id = fields.Many2one('stock.transfer.request', string='Transfer', required=True, ondelete='cascade')
    picking_id = fields.Many2one('stock.picking', string='Picking', required=True, ondelete='cascade')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True, ondelete='cascade')
    
    
    @api.multi
    def choose_picking(self):
        self.transfer_id.affect_to_picking(self.picking_id)
        
        
    @api.model
    def default_get(self, fields_list):
        res = super(choose_picking_wizard, self).default_get(fields_list=fields_list)
        active_id = self.env.context.get('active_id', False)
        if active_id:
            res['transfer_id'] = self.env.context.get('active_id', False)
            res['warehouse_id'] = self.env['stock.transfer.request'].browse(res['transfer_id']).read(['warehouse_id'], load='_classic_write')[0]['warehouse_id']
            
        return res
    