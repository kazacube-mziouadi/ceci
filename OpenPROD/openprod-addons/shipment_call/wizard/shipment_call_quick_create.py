# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp

class stock_shipment_call_quick_create(models.TransientModel):
    """ 
    Shipment call quick create 
    """
    _name = 'stock.shipment.call.quick.create'
    _description = 'Shipment call quick create'
    _rec_name = 'product_id'

    @api.model
    def _get_default_warehouse(self):
        return self.env.user.company_id.warehouse_id
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Partner', required=True, ondelete='cascade')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True, ondelete='cascade', default=_get_default_warehouse)
    
    uom_qty = fields.Float(string='Quantity', required=False, digits=dp.get_precision('Product quantity'))
    uom_id = fields.Many2one(related='product_id.uom_id')
    sec_uom_qty = fields.Float(string='Second UoM qty', digits=dp.get_precision('Product quantity'))
    sec_uom_id = fields.Many2one(related='product_id.sec_uom_id')
    
    date = fields.Datetime(default=lambda self: fields.Datetime.now(), required=True)
    variable = fields.Boolean(string='Variable', default=False)
    note = fields.Text()

    
    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            if self.product_id.dual_unit and self.product_id.dual_unit_type == 'variable':
                self.variable = True
            else:  
                self.variable = False
        else:
            self.variable = False
            
    
    @api.multi
    def quick_create(self):
        new_picking_rc = self.env['stock.picking'].create_picking(
            'in', 
            partner=self.partner_id, 
            product_qty_uom={
                self.product_id: {
                    'uom_qty': self.uom_qty, 
                    'uom_id': None, 
                    'sec_uom_qty': self.variable and self.sec_uom_qty or None,
                    'sec_uom_id': None,
                }
            }, 
            date=self.date,
            warehouse_rs=self.warehouse_id
        )
        
        if new_picking_rc:
            new_picking_rc.wkf_waiting()
            res = new_picking_rc.add_to_shipment_call()
        else:
            res = False
            
        return res