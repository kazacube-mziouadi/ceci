# -*- coding: utf-8 -*-

from openerp import models, fields


class product_product(models.Model):

    _inherit = 'product.product'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    is_not_commissionable = fields.Boolean(
        default=False, string='Expempt of commission'
    )
