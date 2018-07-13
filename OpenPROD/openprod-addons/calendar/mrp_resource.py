# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _


class mrp_resource(models.Model):
    """ 
        Resource 
    """
    _inherit = 'mrp.resource'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    calendar_id = fields.Many2one('calendar', string='Calendar', required=True, ondelete='restrict')