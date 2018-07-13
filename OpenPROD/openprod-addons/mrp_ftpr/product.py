# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError

class product_product(models.Model):
    _inherit = 'product.product'
    _description = 'Product'


    @api.multi
    def write(self, vals=None):
        """
        """
        if not vals:
            vals = {}
        
        res = super(product_product, self).write(vals=vals)
        ctx = self.env.context.copy()
        if 'price_qty' in vals and ('no_recursive_ftpr_routing' not in ctx or ( 'no_recursive_ftpr_routing' in ctx and not ctx['no_recursive_ftpr_routing'])):
            ctx['no_recursive_ftpr_product'] = True
            ftpr_obj = self.env['mrp.ftpr']
            for product in self:
                ftpr_rcs = ftpr_obj.search([('product_id', '=', product.id)])
                for ftpr in ftpr_rcs:
                    ftpr.routing_id.with_context(ctx).write({'price_qty': vals['price_qty']})
        
        return res 
