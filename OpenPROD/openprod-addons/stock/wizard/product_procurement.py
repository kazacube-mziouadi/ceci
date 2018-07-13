# coding: utf8
from openerp import models, fields, api
class product_procurement_wizard(models.TransientModel):
    """ 
    Procurement wizard for a single product 
    """
    _name = 'product.procurement.wizard'
    _description = 'Procurement wizard for a single product'
    #===========================================================================
    # COLUMNS
    #===========================================================================
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    
    
    @api.multi
    def calculate(self):
        return self.product_id.do_procurement()
    

    @api.model
    def default_get(self, fields_list):
        res = super(product_procurement_wizard, self).default_get(fields_list=fields_list)
        if self.env.context.get('active_model') == 'product.product' and self.env.context.get('active_ids'):
            res['product_id'] = self.env.context.get('active_ids')[0]
             
        return res
