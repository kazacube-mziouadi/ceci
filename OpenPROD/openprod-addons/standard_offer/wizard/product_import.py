# coding:utf-8
'''
Created on 9 juin 2015

@author: sylvain
'''
from openerp import models, fields, api


class product_import(models.TransientModel):
    """ 
        Create print line for a product
    """
    _name = 'product.import'
    _description = 'Import one product'

    #===========================================================================
    # COLUMNS
    #===========================================================================
    offer_id = fields.Many2one('standard.offer', string='Tariff', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    

    @api.one
    def import_product(self):
        self.env["standard.offer.print.line"].create_print_lines(self.product_id, self.offer_id)
