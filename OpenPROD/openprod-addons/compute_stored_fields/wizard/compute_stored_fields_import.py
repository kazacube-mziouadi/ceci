# -*- coding: utf-8 -*-
from openerp import models, api

class compute_stored_fields_import(models.TransientModel):
    """ 
    Compute stored fields import 
    """
    _name = 'compute.stored.fields.import'
    _description = 'Compute stored fields import'
    
    @api.multi
    def import_models(self):
        return self.env['compute.stored.fields'].import_models()