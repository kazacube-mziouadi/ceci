# -*- coding: utf-8 -*-


{
    'name' : 'Analytic Accounting',
    'version': '1.1',
    'author' : 'Objectif-PI OpenERP SA',
    'license': 'LGPL',
    'website' : 'http://www.open-prod.com',
    'category': 'Hidden/Dependency',
    'depends' : ['base', 'decimal_precision', 'mail'],
    'description': """
Module for defining analytic accounting object.
===============================================

In OpenERP, analytic accounts are linked to general accounts but are treated
totally independently. So, you can enter various different analytic operations
that have no counterpart in the general financial accounts.
    """,
    'data': [
        'security/analytic_security.xml',
        'security/ir.model.access.csv',
        'analytic_sequence.xml',
        'analytic_view.xml',
        'analytic_data.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
