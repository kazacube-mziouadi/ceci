# -*- encoding: utf-8 -*-

from openerp import models, fields, api, _, exceptions
import openerp.addons.decimal_precision as dp
from datetime import datetime
from openerp.osv import orm
from openerp.exceptions import except_orm, Warning, RedirectWarning


class account_move(models.Model):
    _inherit = "account.move"

    invoice_id = fields.Many2one(comodel_name="account.invoice", string="Facture", required=False, )

account_move()