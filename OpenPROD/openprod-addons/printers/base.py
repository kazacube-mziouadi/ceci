# -*- coding: utf-8 -*-


from openerp import models
from openerp import fields
from openerp import api
from openerp import _


class res_users(models.Model):

    """
    User\'s printer management
    """
    _inherit = 'res.users'

    context_printer_id = fields.Many2one('printers.list', string='Printer 1', required=False, ondelete='restrict', help='Printer used by default for this user')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
