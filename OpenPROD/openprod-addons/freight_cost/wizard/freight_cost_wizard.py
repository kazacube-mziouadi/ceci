# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

class freight_cost_wizard(models.TransientModel):
    """ 
        Freight cost wizard
    """
    _name = 'freight.cost.wizard'
    _description = 'Freight cost wizard'
    _rec_name = 'sale_id'
    
    @api.model
    def default_get(self, fields_list):
        res = super(freight_cost_wizard, self).default_get(fields_list=fields_list)
        mod_obj = self.env['ir.model.data']
        product_id = mod_obj.get_object_reference('freight_cost', 'int_product_transport') and mod_obj.get_object_reference('freight_cost', 'int_product_transport')[-1] or False
        sale = self.env['sale.order'].browse(self._context.get('active_id'))
        price_unit = 0.0
        sec_uom_qty = 1
        if product_id:
            product = self.env['product.product'].browse(product_id)
            customer = product.get_cinfo(partner_id=sale.partner_id.id, property_ids=False)
            uoms = product.get_uoms(pinfo=customer, partner=sale.partner_id, type='out', property_ids=False, with_factor=True)
            qtys = product.get_qtys(1, 
                                     uom_id=uoms['uom_id'], 
                                     sec_uom_id=uoms['sec_uom_id'], 
                                     uoi_id=uoms['uoi_id'], 
                                     by_field='uom', 
                                     dual_unit=product.dual_unit, 
                                     dual_unit_type=product.dual_unit_type, 
                                     factor=uoms['factor'], 
                                     divisor=uoms['divisor'], 
                                     with_raise=True)
            sec_uom_qty = qtys['sec_uom_qty']
            price_unit = product.get_price_sale(sale.partner_id, False, currency_price_return=sale.currency_id, qty_uos=qtys['sec_uom_qty'], 
                                                             uos=uoms['sec_uom_id'], date=sale.requested_date, type='price', with_uoi=uoms['uoi_id'])
            
        vals = {
            'sale_id': sale.id,
            'partner_id': sale.partner_id.id,
            'product_id': product_id,
            'price_unit': price_unit,
            'sec_uom_qty': sec_uom_qty,
            'requested_date': sale.requested_date or fields.Datetime.now(),
        }
        res.update(vals)
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    sale_id = fields.Many2one('sale.order', string='Sale', required=False, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Partner', required=False, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    price_unit = fields.Float(string='Price', default=0.0, required=True, digits=dp.get_precision('Price technical') )
    sec_uom_qty = fields.Float(string='uom_qty', default=0.0, required=False)
    requested_date = fields.Date(string='Requested date', required=True)
    
    
    @api.multi
    def create_sale_line(self):
        sol_obj = self.env['sale.order.line']
        for wiz in self:
            values = {'sec_uom_qty': wiz.sec_uom_qty, 'requested_date': wiz.requested_date, 'is_freight_cost': True}
            sol_obj.create_sale_order_line(sale=wiz.sale_id, product=wiz.product_id, values=values, forced_qty=True, forced_price_unit=wiz.price_unit)
            wiz.sale_id._onchange_order_line_ids()
        return {'type': 'ir.actions.act_window_close'}