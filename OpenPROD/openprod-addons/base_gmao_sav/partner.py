# -*- coding: utf-8 -*-
from openerp import models, fields, api



class res_partner(models.Model):
    """ 
    Partner
    """
    _inherit = 'res.partner'
    #===========================================================================
    # COLUMNS
    #===========================================================================
    guarantee = fields.Integer(string='Guarantee', default=0, required=False)
    guarantee_unity_id = fields.Many2one('product.uom', string='Guarantee unity', required=False, ondelete='restrict')
    
    
    
    