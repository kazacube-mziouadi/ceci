# -*- coding: utf-8 -*-

from openerp.osv import fields, osv

class product_category(osv.osv):
    _inherit = "product.category"
    _columns = {
        'property_account_income_categ_id': fields.many2one(
            'account.account',
            string="Income Account",
            ondelete="restrict",
            help="This account will be used for invoices to value sales."),
        'property_account_expense_categ_id': fields.many2one(
            'account.account',
            string="Expense Account",
            ondelete="restrict",
            help="This account will be used for invoices to value expenses."),
    }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
