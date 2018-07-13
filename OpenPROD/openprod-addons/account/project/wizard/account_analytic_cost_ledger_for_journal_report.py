# -*- coding: utf-8 -*-


import time
from openerp.osv import fields, osv


class account_analytic_cost_ledger_journal_report(osv.osv_memory):
    _name = 'account.analytic.cost.ledger.journal.report'
    _description = 'Account Analytic Cost Ledger For Journal Report'

    _columns = {
        'date1': fields.date('Start of period', required=True),
        'date2': fields.date('End of period', required=True),
        'journal': fields.many2many('account.analytic.journal', 'ledger_journal_rel', 'ledger_id', 'journal_id', 'Journals'),
    }

    _defaults = {
        'date1': lambda *a: time.strftime('%Y-01-01'),
        'date2': lambda *a: time.strftime('%Y-%m-%d')
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
