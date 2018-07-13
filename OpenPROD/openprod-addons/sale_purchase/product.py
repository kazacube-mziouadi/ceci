# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError


class product_supplierinfo(models.Model):
    """ 
    product_supplierinfo 
    """
    _inherit = 'product.supplierinfo'
    
    
    def additional_function_domain(self, arg):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de product_supplierinfo
        """
        arg0, arg1, arg_1 = super(product_supplierinfo, self).additional_function_domain(arg)
        if arg[0] == 'domain_certificate_management':
            arg0 = 'id'
            arg1 = arg[1]
            arg_1 = eval(arg[-1])
        
        return arg0, arg1, arg_1
    
    
    
class product_customerinfo(models.Model):
    """ 
    product_customerinfo 
    """
    _inherit = 'product.customerinfo'
    
    
    def additional_function_domain(self, arg):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de product_customerinfo
        """
        arg0, arg1, arg_1 = super(product_customerinfo, self).additional_function_domain(arg)
        if arg[0] == 'domain_certificate_management':
            arg0 = 'id'
            arg1 = arg[1]
            arg_1 = eval(arg[-1])
        
        return arg0, arg1, arg_1