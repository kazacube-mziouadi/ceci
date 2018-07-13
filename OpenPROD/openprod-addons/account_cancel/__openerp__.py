# -*- coding: utf-8 -*-

{
    'name': 'Cancel Journal Entries',
    'version': '1.1',
    'author': 'Objectif-PI OpenERP SA',
    'category': 'Accounting & Finance',
    'license': 'LGPL',
    'description': """
Allows canceling accounting entries.
====================================

This module adds 'Allow Canceling Entries' field on form view of account journal.
If set to true it allows user to cancel entries & invoices.
    """,
    'website': 'https://www.odoo.com/page/accounting',
    'depends' : ['account'],
    'data': ['account_cancel_view.xml' ],
    'demo': [],
    'installable': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
