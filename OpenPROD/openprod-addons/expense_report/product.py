# -*- coding: utf-8 -*-
from openerp import models, api, fields, _
from openerp.exceptions import except_orm

class product_product(models.Model):
    _inherit = 'product.product'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    is_expense_report = fields.Boolean(string='Expense report', default=False)
    
