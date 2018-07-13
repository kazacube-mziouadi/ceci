# coding:utf-8
'''
Created on 8 juin 2015

@author: sylvain
'''
from openerp import models, fields, api


class category_import(models.TransientModel):
    """ 
        Create print lines for all products of a category 
    """
    _name = 'category.import'
    _description = 'Create print lines for all products of a category'

    #===========================================================================
    # COLUMNS
    #===========================================================================
    offer_id = fields.Many2one('standard.offer', string='Tariff', required=True, ondelete='cascade')
    category_id = fields.Many2one('sale.family', string='Category', required=True, ondelete='cascade')

    @api.one
    def import_category(self):
        product_ids = self.env["product.product"].search([("sale_family_id", "=", self.category_id.id)])
        standard_offer_print_line_obj = self.env["standard.offer.print.line"]
        for product_id in product_ids:
            standard_offer_print_line_obj.create_print_lines(product_id, self.offer_id)
