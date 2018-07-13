# -*- coding: utf-8 -*-


import time
from openerp.osv import fields, osv


class account_analytic_inverted_balance(osv.osv_memory):
    _name = 'account.analytic.inverted.balance'
    _description = 'Account Analytic Inverted Balance'

    _columns = {
        'date1': fields.date('Start of period', required=True),
        'date2': fields.date('End of period', required=True),
    }

    _defaults = {
        'date1': lambda *a: time.strftime('%Y-01-01'),
        'date2': lambda *a: time.strftime('%Y-%m-%d')
    }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
