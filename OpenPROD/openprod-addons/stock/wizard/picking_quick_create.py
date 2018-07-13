# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp

class stock_picking_quick_create(models.TransientModel):
    """ 
    Picking quick create 
    """
    _name = 'stock.picking.quick.create'
    _description = 'Return picking'
    _rec_name = 'product_id'

    
    @api.model
    def _invoice_state_get(self):
        return [
                ('2binvoiced', 'To be refunded/invoiced'),
                ('none', 'No invoicing')]


    @api.model
    def _type_get(self):
        return [
                ('in', 'IN'),
                ('out', 'OUT'),
                       ]
    

    @api.model
    def _get_default_warehouse(self):
        return self.env.user.company_id.warehouse_id
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Partner', required=False, ondelete='cascade')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True, ondelete='cascade', default=_get_default_warehouse)
    
    uom_qty = fields.Float(string='Quantity', required=False, digits=dp.get_precision('Product quantity'))
    uom_id = fields.Many2one('product.uom', string='UoM', readonly=True, ondelete='cascade')
    sec_uom_qty = fields.Float(string='Second UoM qty', digits=dp.get_precision('Product quantity'))
    sec_uom_id = fields.Many2one('product.uom', string='Second UoM', readonly=True, ondelete='cascade')
    
    type = fields.Selection('_type_get')
    date = fields.Datetime(default=lambda self: fields.Datetime.now(), required=True)
    variable = fields.Boolean(string='Variable', default=False)

    
    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id
            if self.product_id.dual_unit and self.product_id.dual_unit_type == 'variable':
                self.variable = True
                self.sec_uom_id = self.product_id.sec_uom_id
            else:  
                self.variable = False
                self.sec_uom_id = False
        else:
            self.uom_id = False
            self.sec_uom_id = False
            self.variable = False
            
    
    @api.multi
    def quick_create(self):
        new_picking = self.env['stock.picking'].create_picking(self.type, 
                                                               partner=self.partner_id, 
                                                               product_qty_uom={self.product_id: {'uom_qty': self.uom_qty, 
                                                                                                  'uom_id': None, 
                                                                                                  'sec_uom_qty': self.variable and self.sec_uom_qty or None,
                                                                                                  'sec_uom_id': None,
                                                                                                  }}, 
                                                               date=self.date,
                                                               warehouse_rs=self.warehouse_id)
        
        
        return new_picking.get_form_view()