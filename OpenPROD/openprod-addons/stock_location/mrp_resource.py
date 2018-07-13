# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _


class mrp_resource(models.Model):
    _inherit = 'mrp.resource'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    location_id = fields.Many2one('stock.location', string='Location', required=True, ondelete='restrict')