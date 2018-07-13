# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
from openerp.addons.base_openprod.common import get_form_view

import time


class create_transfer_wizard(models.TransientModel):
    """ 
    Create transfer
    """
    _name = 'create.transfer.wizard'
    _description = 'Create transfer'
    _rec_name = 'product_id'
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    uom_id = fields.Many2one('product.uom', related='product_id.uom_id', string='UoM', readonly=True)
    track_label = fields.Boolean(string='Track label', related='product_id.track_label', readonly=True)
    
    uom_qty = fields.Float(string='UoM qty', required=True, default=0.0, digits=dp.get_precision('Product quantity'))
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True, ondelete='cascade')
    warehouse_dest_id = fields.Many2one('stock.warehouse', string='Dest. warehouse', required=True, ondelete='cascade')
    price = fields.Float(string='Price', digits=dp.get_precision('Product price'))
    is_billable = fields.Boolean(string='Billable', default=False)
    partner_id = fields.Many2one('res.partner', string='Partner', required=False, ondelete='cascade', domain=[('is_company', '=', True)])
    date = fields.Date(default=lambda *a: time.strftime('%Y-%m-%d'))
    label_ids = fields.Many2many('stock.label', 'wiz_create_transfer_label_rel', 'wiz_id', 'label_id',  string='Labels')
    make_done = fields.Boolean(default=False, help='If this field is checked, pickings of this transfer will be directly make done')
    is_automatic = fields.Boolean(string='Automatic', default=False, help='If this field is checked, when a stock move will be processed, the corresponding stock move of transfer request will also be processed')
    
    
    @api.onchange('label_ids')
    def _onchange_label_ids(self):
        self.uom_qty = sum([l.uom_qty for l in self.label_ids])
    
    
    @api.onchange('make_done')
    def _onchange_make_done(self):
        self.is_automatic = self.make_done
    
    
    @api.multi
    def create_transfer(self):
        for wizard in self:
            if wizard.label_ids:
                uom_qty = sum([l.uom_qty for l in wizard.label_ids])
            else:
                uom_qty = wizard.uom_qty
                
            transfer_rc = self.env['stock.transfer.request'].create({
                'product_id': wizard.product_id.id,
                'origin': 'Wizard',
                'warehouse_id': wizard.warehouse_id.id,
                'warehouse_dest_id': wizard.warehouse_dest_id.id,
                'uom_qty': uom_qty,
                'uom_id': wizard.product_id.uom_id.id,
                'needed_uom_qty': uom_qty,
                'needed_uom_id': wizard.product_id.uom_id.id,
                'need_date': wizard.date,
                'is_automatic': wizard.is_automatic,
                'departure_date': wizard.date,
                'is_billable': wizard.is_billable,
                'partner_id': wizard.partner_id.id,
                'price': wizard.price,
                'label_ids': [(6, 0, wizard.label_ids.ids)],
            })
            transfer_rc.create_transfer_picking_button()
            if wizard.make_done:
                for out_move_rc in transfer_rc.out_move_ids:
                    if out_move_rc.picking_id:
                        out_move_rc.picking_id.do_partial_auto()
            
        return get_form_view(self, 'stock.act_stock_transfer_request', res_id=transfer_rc.id, view_mode='form', target='current')