# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp

class stock_product_storage_wizard(models.TransientModel):
    """ 
        Product storage
    """
    _name = 'stock.product.storage'
    _description = 'Product storage'
    
    
    @api.model
    def _move_type_get(self):
        return [('in', 'IN'),
                ('out', 'OUT')]
        
    
    @api.model
    def default_get(self, fields_list):
        res = super(stock_product_storage_wizard, self).default_get(fields_list=fields_list)
        if self.env.context.get('active_model') == 'stock.move' and self.env.context.get('active_id'):
            stock_move = self.env['stock.move'].browse(self.env.context.get('active_id'))
            res['product_id'] = stock_move.product_id.id
            res['location_id'] = stock_move.location_dest_id.id 
            res['uom_qty'] = stock_move.uom_qty
            res['uom_id'] = stock_move.uom_id.id
            
            
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    location_id = fields.Many2one('stock.location', string='Source location', required=True, ondelete='cascade')
    location_dest_id = fields.Many2one('stock.location', string='Destination location', required=True, ondelete='cascade')
    uom_qty = fields.Float(required=False, digits=dp.get_precision('Product quantity (UoM)'), default=0.0)
    uom_id = fields.Many2one('product.uom', string='UdM', required=False, ondelete='cascade', readonly=True)
    move_type = fields.Selection('_move_type_get', string='Type')
    track_label = fields.Boolean(default=False)
    label_ids = fields.Many2many('stock.label', 'stock_product_storage_stock_label_rel', 'product_storage_id', 'label_id', string='Labels')

    
    @api.onchange('product_id')
    def onchange_product_id(self):
        self.uom_id = self.product_id.uom_id.id
        self.track_label = self.product_id.track_label
        if self.move_type == 'in':
            self.location_dest_id = self.product_id.get_storage_location().id
        elif self.move_type == 'out':
            self.location_id = self.product_id.get_storage_location().id
            
            
    @api.multi
    def validate(self):
        """
            Création d'un mouvement et passage à done
        """
        if self.track_label:
            if self.label_ids:
                self.label_ids.move(self.location_dest_id)

        else:
            move_rs = self.env['stock.move'].create_move(self.product_id, 
                                                         src_location=self.location_id, 
                                                         dst_location=self.location_dest_id, 
                                                         qty=self.uom_qty, 
                                                         other_data={'origin': _('Storage')})
            move_rs.wkf_waiting()
            move_rs.wkf_done()
            
        return True 