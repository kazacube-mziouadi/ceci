# -*- coding: utf-8 -*-
from openerp import models, fields, api

class create_quick_sale(models.TransientModel):
    _inherit = 'create.quick.sale'
    
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.env.context.get('active_model') != 'delivery.program.line':
            super(create_quick_sale, self)._onchange_product_id()
    
    
    @api.onchange('product_id', 'partner_id')
    def _onchange_calc_date(self):
        if self.env.context.get('active_model') != 'delivery.program.line':
            super(create_quick_sale, self)._onchange_calc_date()
    
          
    @api.model
    def default_get(self, fields_list):
        res = super(create_quick_sale, self).default_get(fields_list=fields_list)
        if self.env.context.get('active_model') == 'delivery.program.line':
            delivery_program_line_rc = self.env['delivery.program.line'].browse(self.env.context.get('active_id'))
            res['quantity'] = delivery_program_line_rc.quantity
            res['date'] = delivery_program_line_rc.date
            res['partner_id'] = delivery_program_line_rc.delivery_program_id.customer_id.id
            res['product_id'] = delivery_program_line_rc.product_id.id
            
        return res


    @api.multi
    def create_quick_sale(self):
        action_struc = super(create_quick_sale, self).create_quick_sale()
        if self.env.context.get('active_model') == 'delivery.program.line':
            sale_id = action_struc and 'res_id' in action_struc and action_struc['res_id'] or False
            sale_order_line_rcs = self.env['sale.order.line'].search([('sale_order_id', '=', sale_id)], order='id desc', limit=1)
            if sale_order_line_rcs:
                sale_order_line_id = sale_order_line_rcs.id
            else:
                sale_order_line_id = False
            
            self.env['delivery.program.line'].browse(self.env.context.get('active_id')).write({'sale_order_id': sale_id, 'sale_order_line_id': sale_order_line_id})          
         
        return action_struc