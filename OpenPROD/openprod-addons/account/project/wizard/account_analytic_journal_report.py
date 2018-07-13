# -*- coding: utf-8 -*-


import time
from openerp.osv import fields, osv


class account_analytic_journal_report(osv.osv_memory):
    _name = 'account.analytic.journal.report'
    _description = 'Account Analytic Journal'

    _columns = {
        'date1': fields.date('Start of period', required=True),
        'date2': fields.date('End of period', required=True),
        'analytic_account_journal_id': fields.many2many('account.analytic.journal', 'account_analytic_journal_name', 'journal_line_id', 'journal_print_id', 'Analytic Journals', required=True),
    }

    _defaults = {
        'date1': lambda *a: time.strftime('%Y-01-01'),
        'date2': lambda *a: time.strftime('%Y-%m-%d')
    }


    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res = super(account_analytic_journal_report, self).default_get(cr, uid, fields, context=context)
        if not context.has_key('active_ids'):
            journal_ids = self.pool.get('account.analytic.journal').search(cr, uid, [], context=context)
        else:
            journal_ids = context.get('active_ids')
        if 'analytic_account_journal_id' in fields:
            res.update({'analytic_account_journal_id': journal_ids})
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
