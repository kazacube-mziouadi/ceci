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
    _name = 'account.analytic.journal'
    _description = 'Analytic journal'


    @api.model
    def _type_get(self):
        return [
                ('sale', _('Sale')),
                ('purchase', _('Purchase')),
                ('cash', _('Cash')),
                ('general', _('General')),
                ('situation', _('Situation')),
                       ]

    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True, size=256)
    code = fields.Char(string='Code', size=8, required=False)
    active = fields.Boolean(string='True', default=True, help="If the active field is set to False, it will allow you to hide the analytic journal without removing it.")
    type = fields.Selection('_type_get', string='Type', default='general', required=True, help="Gives the type of the analytic journal. When it needs for a document (eg: an invoice) to create analytic entries, Odoo will look for a matching journal of the same type.")
    line_ids = fields.One2many('account.analytic.line', 'journal_id',  string='Lines', copy=False)
    company_id = fields.Many2one('res.company', string='Company', required=True, ondelete='restrict', default=lambda self: self.env.user.company_id)


