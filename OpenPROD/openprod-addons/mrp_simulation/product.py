# -*- coding: utf-8 -*-
from openerp import models, api, fields
class product_product(models.Model):
    _inherit = 'product.product'
    
    def get_delay_confirmation_with_stock(self):
        return False