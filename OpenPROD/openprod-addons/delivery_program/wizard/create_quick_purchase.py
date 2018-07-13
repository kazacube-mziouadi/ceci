# -*- coding: utf-8 -*-
from openerp import models, fields, api

class create_quick_purchase(models.TransientModel):
    _inherit = 'create.quick.purchase'
    
    
    @api.onchange('product_id', 'partner_id')
    def _onchange_calc_date(self):
        if self.env.context.get('active_model') != 'delivery.program.line':
            super(create_quick_purchase, self)._onchange_calc_date()
    
          
    @api.model
    def default_get(self, fields_list):
        res = super(create_quick_purchase, self).default_get(fields_list=fields_list)
        if self.env.context.get('active_model') == 'delivery.program.line':
            delivery_program_line_rc = self.env['delivery.program.line'].browse(self.env.context.get('active_id'))
            res['quantity'] = delivery_program_line_rc.quantity
            res['date'] = delivery_program_line_rc.date
            res['product_id'] = delivery_program_line_rc.product_id.id
             
        return res