# -*- coding: utf-8 -*-
from openerp import models, fields, api, _


class res_company(models.Model):
    _inherit = 'res.company'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    rml_sale_footer = fields.Text(string='Sale footer', help="Footer text displayed at the bottom of sale reports.")