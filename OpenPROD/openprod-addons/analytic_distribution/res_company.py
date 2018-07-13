# -*- coding: utf-8 -*-
from openerp import models, api, fields
from openerp.tools.translate import _


class res_company(models.Model):
    _inherit = 'res.company'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    check_analytic_amount = fields.Boolean(string='Check analytic amount', default=False, help="Check this field if you want to check if "
                                                        "the total analytic amount is equal to the total without taxes of the "
                                                        "invoice when you validate an invoice")

