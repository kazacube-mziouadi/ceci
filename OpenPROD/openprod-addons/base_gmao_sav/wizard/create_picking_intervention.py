# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp

class create_picking_intervention(models.TransientModel):
    """ 
    Create picking intervention
    """
    _name = 'create.picking.intervention'
    _description = 'Create picking intervention'
    _rec_name = 'pm_intervention_id'

    
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
    pm_intervention_id = fields.Many2one('piece.maintenance.intervention', string='Piece maintenance', required=False, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Partner', required=False, ondelete='cascade')
    customer_id = fields.Many2one('res.partner', string='Partner', required=False, ondelete='cascade')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True, ondelete='cascade', default=_get_default_warehouse)
    uom_qty = fields.Float(string='Quantity', required=False, digits=dp.get_precision('Product quantity'))
    uom_id = fields.Many2one('product.uom', string='UoM', readonly=True, ondelete='cascade')
    type = fields.Selection('_type_get')
    date = fields.Datetime(default=lambda self: fields.Datetime.now(), required=True)
    variable = fields.Boolean(string='Variable', default=False)
    is_existant = fields.Boolean(string='Picking existant', default=False)
    picking_id = fields.Many2one('stock.picking', string='Picking', required=False, ondelete='cascade')
    
    @api.multi
    def quick_create(self):
        for wiz in self:
            picking_rcs = False
            if not wiz.picking_id:
                picking_rcs = self.env['stock.picking'].create_picking(self.type, 
                                                               partner=self.partner_id, 
                                                               product_qty_uom={self.product_id: {'uom_qty': self.uom_qty, 
                                                                                                  'uom_id': self.uom_id, 
                                                                                                  'sec_uom_qty': self.uom_qty, 
                                                                                                  'sec_uom_id': self.uom_id,
                                                                                                  }}, 
                                                               date=self.date,
                                                               warehouse_rs=self.warehouse_id)
        
            else:
                picking_rcs = wiz.picking_id
                self.env['stock.move'].create_move(self.product_id, 
                                                   qty=self.uom_qty, 
                                                   uom=self.uom_id, 
                                                   sec_qty=self.uom_qty, 
                                                   sec_uom=self.uom_id, 
                                                   type=self.type, 
                                                   date=self.date, 
                                                   picking=picking_rcs, 
                                                   partner=picking_rcs.partner_id, 
                                                   with_price=True,
                                                   warehouse_rs=self.warehouse_id)
            
            if picking_rcs:
                wiz.pm_intervention_id.write({'picking_id': picking_rcs.id})
                return picking_rcs.get_form_view()