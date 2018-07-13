# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
from openerp.exceptions import except_orm,Warning



class res_partner(models.Model):
    _inherit = 'res.partner'
    
    
    def additional_function_domain(self, arg):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de res_partner
        """
        arg0, arg1, arg_1 = super(res_partner, self).additional_function_domain(arg)
        if arg[0] == 'domain_certificate_management':
            arg0 = 'id'
            arg1 = arg[1]
            arg_1 = eval(arg[-1])
        
        return arg0, arg1, arg_1