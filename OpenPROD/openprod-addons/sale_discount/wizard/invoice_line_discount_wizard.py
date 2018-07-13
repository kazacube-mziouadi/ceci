# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
import time, datetime
import openerp.addons.decimal_precision as dp


class ai_discount_wizard(models.TransientModel):
    """ 
        AI discount wizard
    """
    _name = 'ai.discount.wizard'
    _description = 'AI discount wizard'
    _rec_name = 'invoice_id'
    

    @api.model
    def default_get(self, fields_list):
        res = super(ai_discount_wizard, self).default_get(fields_list=fields_list)
        mod_obj = self.env['ir.model.data']
        product_id = mod_obj.get_object_reference('sale_discount', 'int_product_discount') and mod_obj.get_object_reference('sale_discount', 'int_product_discount')[-1] or False
        invoice = self.env['account.invoice'].browse(self._context.get('active_id'))
        sec_uom_qty = 1
        if product_id:
            product = self.env['product.product'].browse(product_id)
            customer = product.get_cinfo(partner_id=invoice.partner_id.id, property_ids=False)
            uoms = product.get_uoms(pinfo=customer, partner=invoice.partner_id, type='out', property_ids=False, with_factor=True)
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
        vals = {
            'invoice_id': invoice.id,
            'partner_id': invoice.partner_id.id,
            'product_id': product_id,
            'sec_uom_qty': sec_uom_qty,
        }
        res.update(vals)
        return res
    
    
    @api.model
    def _type_get(self):
        return [
                ('fixed', _('Fixed')),
                ('variable', _('Variable')),
                       ]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    invoice_id = fields.Many2one('account.invoice', string='Invoice', required=False, ondelete='cascade')
    type = fields.Selection('_type_get', string='Type', default='fixed', required=True)
    partner_id = fields.Many2one('res.partner', string='Partner', required=False, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    value = fields.Float(string='Value', default=0.0, required=True)
    sec_uom_qty = fields.Float(string='uom_qty', default=0.0, required=False)
    section_id = fields.Many2one('sale.order.line.section', string='Section', required=False, ondelete='cascade')
    
    
    @api.multi
    def create_sale_line(self):
        ail_obj = self.env['account.invoice.line']
        for wiz in self:
            values = {'sec_uom_qty': wiz.sec_uom_qty}
            if wiz.type == 'fixed':
                price_unit = -wiz.value
                values['name'] = _('Discount %.2f')%(wiz.value)
            else:
                price_unit = -wiz.sale_id.amount_ex_taxes*wiz.value/100
                values['name'] = _('Discount %.2f %%')%(wiz.value)
            
            if wiz.section_id:
                values['section_id'] = wiz.section_id.id

            ail_obj.create_invoice_line(wiz.invoice_id, wiz.product_id, from_invoice=False, other_data=values, forced_price_unit=price_unit)
        
        return {'type': 'ir.actions.act_window_close'}
    