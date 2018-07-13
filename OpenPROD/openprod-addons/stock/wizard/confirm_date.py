# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp

class confirm_date_wizard(models.TransientModel):
    """ 
    Confirm sale delay
    """
    _name = 'confirm.date.wizard'
    _description = 'Confirm sale delay'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    date = fields.Date(required=True)
    
    
    @api.multi
    def confirm_date(self):
        return True
    