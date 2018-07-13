# -*- coding: utf-8 -*-
{
    'name': 'commission',
    'version': '1.1',
    'category': 'Hidden/Dependency',
    'license': 'LGPL',
    'description': '',
    'author': 'Objectif-PI',
    'website': '',
    'depends': [
        'human_resource',
        'sale',
        'warning',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/agent_add_modif_view.xml',
        'commission_view.xml',
        'product_view.xml',
        'res_partner_view.xml',
        'sale_view.xml',
        'account_invoice_view.xml',
    ],
    'demo': [],
    'installable': True,
}
