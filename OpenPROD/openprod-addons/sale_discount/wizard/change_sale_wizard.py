# -*- coding: utf-8 -*-
from openerp import models, fields, api

    
class change_line_information(models.TransientModel):
    """ 
        Wizard to change the sale line information
    """
    _inherit = 'change.line.information'
    
    def prepar_sale_line_vals(self):
        res = super(change_line_information, self).prepar_sale_line_vals()
        res['price_unit_without_discount'] = self.price_unit
        return res
    
    
    def prepar_invoice_line_vals(self):
        res = super(change_line_information, self).prepar_invoice_line_vals()
        res['price_unit_without_discount'] = self.price_unit
        return res
        
