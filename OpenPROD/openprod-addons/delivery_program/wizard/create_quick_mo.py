# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp


class create_quick_mo(models.TransientModel):
    _name = 'create.quick.mo'
    _description = 'Create quick MO'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    product_id = fields.Many2one('product.product', string='Product', ondelete='cascade')
    unit_id = fields.Many2one('product.uom', string='Unit', ondlete='cascade')
    quantity = fields.Float(string='Quantity', digits=dp.get_precision('Product quantity'), required=True)
    date = fields.Date(string='Date', required=True)
    is_forecast = fields.Boolean(string='Is forecast')
    
          
    @api.model
    def default_get(self, fields_list):
        res = super(create_quick_mo, self).default_get(fields_list=fields_list)
        if self.env.context.get('active_model') == 'delivery.program.line':
            delivery_program_line_rc = self.env['delivery.program.line'].browse(self.env.context.get('active_id'))
            res['product_id'] = delivery_program_line_rc.product_id.id
            res['unit_id'] = delivery_program_line_rc.unit_id.id
            res['quantity'] = max(0, 0-delivery_program_line_rc.stock_date)
            res['date'] = delivery_program_line_rc.date
            res['is_forecast'] = self.env.context.get('is_forecast', False)
            
        return res
    

    @api.multi
    def create_quick_mo(self):
        if self.env.context.get('active_model') == 'delivery.program.line':
            other_data = {'requested_date': self.date, 'is_forecast': self.is_forecast}
            
        return {
            'name': 'Manufacturing order',
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'mrp.manufacturingorder',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'res_id': self.env['mrp.manufacturingorder'].create_mo(self.product_id, quantity=self.quantity, uom=self.unit_id, other_data=other_data, with_raise=True)[0].id
        }