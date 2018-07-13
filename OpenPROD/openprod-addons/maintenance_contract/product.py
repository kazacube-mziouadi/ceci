# -*- coding: utf-8 -*-
from openerp import models, fields, api



class product_product(models.Model):
    """ 
        description 
    """
    _inherit = 'product.product'
    
    def additional_function_domain(self, arg):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de product_product
        """
        arg0, arg1, arg_1 = super(product_product, self).additional_function_domain(arg)
        if arg[0] == 'domain_maintenance_contract':
            arg0 = 'id'
            arg1 = 'in'
            product_ids = []
            if arg[-1] and arg[-1][-1] and arg[-1][0]:
                if arg[-1][-1] == 'customer':
                    product_free_rcs = self.env['product.product'].search([('sale_ok', '=', True), ('free_sale', '=', True)])
                    product_free_ids = product_free_rcs and product_free_rcs.ids or []
                    product_custom_ids = self.env['product.customerinfo'].search_group(fields=['product_id'], 
                                                                            groupby=['product_id'], 
                                                                            args=[('partner_id', '=', arg[-1][0]), ('state', '!=', 'obsolete')])
                    product_ids = list(set(product_free_ids + product_custom_ids))
                else:
                    product_free_rcs = self.env['product.product'].search([('purchase_ok', '=', True), ('free_purchase', '=', True)])
                    product_free_ids = product_free_rcs and product_free_rcs.ids or []
                    product_supp_ids = self.env['product.supplierinfo'].search_group(fields=['product_id'], 
                                                                            groupby=['product_id'], 
                                                                            args=[('partner_id', '=', arg[-1][0]), ('state', '!=', 'obsolete')])
                    product_ids = list(set(product_free_ids + product_supp_ids))
            
            arg_1 = product_ids
                
        return arg0, arg1, arg_1