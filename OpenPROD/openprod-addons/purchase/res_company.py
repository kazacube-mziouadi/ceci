# -*- coding: utf-8 -*-
from openerp import models, fields, api, _


class res_company(models.Model):
    _inherit = 'res.company'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    rml_purchase_footer = fields.Text(string='Purchase footer', help="Footer text displayed at the bottom of purchase reports.")