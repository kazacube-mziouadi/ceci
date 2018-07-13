# -*- coding: utf-8 -*-
from openerp import models, fields, api

class compute_stored_fields_compute(models.TransientModel):
    """ 
    Compute stored fields compute 
    """
    _name = 'compute.stored.fields.compute'
    _description = 'Compute stored fields compute'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    date = fields.Date()
    override_errors = fields.Boolean(help='If this field is checked, errors will not stop processing')
    
    
    @api.multi
    def compute_models(self):
        return self.env['compute.stored.fields'].compute_selection(self[0].date, override_errors=self[0].override_errors)