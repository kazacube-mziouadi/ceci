# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError



class stock_label(models.Model):
    """ 
    Label 
    """
    _inherit = 'stock.label'
    _description = 'Label'
       
       
    def additional_function_domain(self, arg):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de stock_label
        """
        arg0, arg1, arg_1 = super(stock_label, self).additional_function_domain(arg)
        
        if arg[0] == 'domain_wizard_mo_output':
            arg0 = 'id'
            arg1 = 'not in'
            label_ids = []
            for arg_temp in arg[-1]:
                label_ids.extend(arg_temp[-1])
            
            arg_1 = label_ids
            
        return arg0, arg1, arg_1