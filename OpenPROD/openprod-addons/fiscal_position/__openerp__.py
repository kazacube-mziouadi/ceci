# -*- coding: utf-8 -*-
{
    'name' : 'Fiscal position',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'license': 'Open-prod license',
    'category' : 'Fiscal position',
    'description' : """ Fiscal position """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
        'sale'        
    ],
                
    'data': [
        'res_company_view.xml',
        'sale_view.xml',
        'tax_exemption_view.xml',
        'account_invoice_view.xml',
        'security/ir.model.access.csv'
    ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}