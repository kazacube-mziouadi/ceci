# -*- coding: utf-8 -*-
from openerp import models, api, fields


class account_journal(models.Model):
    _inherit = 'account.journal'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    is_timetracking_journal = fields.Boolean(string='Timetracking journal', default=False, 
                                             help="Check this field to use this journal for analytic distribution on time lines")