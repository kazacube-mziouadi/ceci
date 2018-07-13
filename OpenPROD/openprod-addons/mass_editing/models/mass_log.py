# coding: utf-8

from openerp import models, fields

class mass_log(models.Model):
    """ 
    Log entry for mass editing 
    """
    _name = 'mass.log'
    _description = 'Log entry for mass editing'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    model = fields.Char(string='Model', required=True)
    field = fields.Char(string='Field', required=True)
    record_ids = fields.Char(string='Record Ids', required=True)
    type = fields.Char(string='Editing type', required=True)
    value = fields.Char(string='Values', required=False)