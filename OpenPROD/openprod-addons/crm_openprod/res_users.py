# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _


class res_users(models.Model):
    _inherit = 'res.users'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    crm_b2c = fields.Boolean(string='B2C (CRM)', default=False, help="Check this case if you want to manage CRM for B2C")