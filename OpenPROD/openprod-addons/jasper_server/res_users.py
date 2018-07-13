# -*- coding: utf-8 -*-
from openerp import models
from openerp import fields
from openerp import api
from openerp import _


class res_users(models.Model):
    """
        User's signature for reports
    """
    _inherit = 'res.users'
    
    report_signature = fields.Text(string='Report signature')
    binary_signature = fields.Binary(string='Signature', help="The picture used for the signature in invoices, sales and purchases reports")


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
