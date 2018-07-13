# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError


class mrp_resource(models.Model):
    """ 
    Resource 
    """
    _inherit = 'mrp.resource'
    
    
    def additional_function_domain(self, arg):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de mrp_resource
        """
        arg0, arg1, arg_1 = super(mrp_resource, self).additional_function_domain(arg)
        if arg[0] == 'domain_certificate_management':
            arg0 = 'id'
            arg1 = arg[1]
            arg_1 = eval(arg[-1])
        
        return arg0, arg1, arg_1