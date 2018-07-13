# -*- coding: utf-8 -*-
from openerp import models, api, fields
from openerp.tools.translate import _


class res_company(models.Model):
    _inherit = 'res.company'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    print_delivered_address = fields.Boolean(string='Print delivered address on invoices', default=False)
    us_accounting = fields.Boolean(string='Canada accounting', default=False, help="Added to take in count US and Canada report demands")
    rml_invoice_footer = fields.Text(string='Invoice footer', help="Footer text displayed at the bottom of invoice reports.")

