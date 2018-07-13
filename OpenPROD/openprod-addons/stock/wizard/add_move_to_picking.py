# -*- coding: utf-8 -*-
from openerp import models, api, fields
import openerp.addons.decimal_precision as dp


class add_move_to_picking(models.TransientModel):
    """ 
    Add move to picking 
    """
    _name = 'add.move.to.picking'
    _description = 'Add move to picking'
    _rec_name = 'product_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    picking_id = fields.Many2one('stock.picking', string='Picking', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    location_id = fields.Many2one('stock.location', string='Src location', required=True, ondelete='cascade')
    location_dest_id = fields.Many2one('stock.location', string='Dest location', required=True, ondelete='cascade')
    uom_qty = fields.Float(string='UoM qty', required=True, digits=dp.get_precision('Product quantity'), default=0.0)
    uom_id = fields.Many2one('product.uom', related='product_id.uom_id', string='UoM', readonly=True)
    uom_category_id = fields.Many2one('product.uom.category', related='uom_id.category_id', string='UoM category', readonly=True)
    uoi_id = fields.Many2one('product.uom', string='UoI', required=True, ondelete='cascade')
    price = fields.Float(default=0.0, digits=dp.get_precision('Account'), required=False)
    
    
    @api.multi
    def add_move_to_picking(self):
        move_rs =  self.env['stock.move'].create_move(self.product_id, 
                                                      qty=self.uom_qty, 
                                                      uom=self.uom_id,
                                                      src_location=self.location_id.id,
                                                      dst_location=self.location_dest_id.id,
                                                      type=self.picking_id.type, 
                                                      date=self.picking_id.date, 
                                                      picking=self.picking_id, 
                                                      partner=self.picking_id.partner_id,
                                                      warehouse_rs=self.picking_id.warehouse_id,
                                                      other_data={'partner_price': self.price,
                                                                  'theo_price': self.price,
                                                                  'date': self.picking_id.date,
                                                                  'date_expected': self.picking_id.date_expected,
                                                                  'priority_date': self.picking_id.date_create})
        
        if move_rs:
            if move_rs.uoi_id.id != self.uoi_id.id:
                uoi_qty = self.env['product.uom']._compute_qty_obj(self.uom_id, self.uom_qty, self.uoi_id, with_raise=False, with_round=False)
                move_rs.write({'uoi_id': self.uoi_id.id, 'uoi_qty': uoi_qty})
                
            if self.picking_id.state in ('waiting', 'done'):
                move_rs.wkf_waiting()
                if self.picking_id.state == 'done':
                    move_rs.wkf_done()
                
        return move_rs
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(add_move_to_picking, self).default_get(fields_list=fields_list)
        if self.env.context.get('active_id', False):
            res['picking_id'] = self.env.context['active_id']
            picking_rs = self.env['stock.picking'].browse(res['picking_id']) 
            picking_type = picking_rs.type
            move_obj = self.env['stock.move']
            location_id = move_obj.with_context(picking_type=picking_type)._default_location_id(picking_rs.warehouse_id)
            if location_id:
                res['location_id'] = location_id.id
                
            location_dest_id = move_obj.with_context(picking_type=picking_type)._default_location_dest_id(picking_rs.warehouse_id)
            if location_dest_id:
                res['location_dest_id'] = location_dest_id.id
            
        return res
    
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.uoi_id = self.product_id.uom_id.id