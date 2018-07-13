# -*- coding: utf-8 -*-
from openerp import models, api, fields, _
from openerp.exceptions import except_orm
from openerp.addons.base_openprod.common import get_form_view
import openerp.addons.decimal_precision as dp
from openerp.addons.analytic_distribution.compute_amount import compute_amount


class account_analytic_journal(models.Model):
    """ 
        Analytic journal 
    """
    _inherit = 'account.analytic.journal'


    @api.model
    def _type_get(self):
        res = super(account_analytic_journal, self)._type_get()
        res.append(('manufacturing', _('Manufacturing')))
        return res


