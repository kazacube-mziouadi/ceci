# -*- coding: utf-8 -*-
{
    'name' : 'Analytic distribution',
    'version' : '1.2',
    'author' : 'Objectif PI',
    'category' : 'Account',
    'license': 'Open-prod license',
    'description' : """ Analytic distribution """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
                 'sale_purchase',
                 'mrp',
                ],
                
    'data': [
             'data/account_data.xml',
             'config/stock_config_view.xml',
             'config/purchase_config_view.xml',
             'security/ir.model.access.csv',
             'analytic_distribution_view.xml',
             'product_view.xml',
             'sale_view.xml',
             'purchase_view.xml',
             'account_invoice_view.xml',
             'account_view.xml',
             'res_config_view.xml',
             'resource_timetracking_view.xml',
             'wizard/wizard_create_timetracking_view.xml',
             'wizard/wizard_analytic_distrib_timetracking_view.xml',
             'mrp_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}