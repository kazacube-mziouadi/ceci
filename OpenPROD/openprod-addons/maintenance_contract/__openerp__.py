# -*- coding: utf-8 -*-
{
    'name' : 'Maintenance contract',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'license': 'Open-prod license',
    'category' : 'Tools',
    'description' : """ Maintenance contract """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
                 'sale_purchase'
                ],
                
    'data': [
             'security/maintenance_contract_security.xml',
             'security/ir.model.access.csv',
             'wizard/wiz_create_invoice_mc_view.xml',
             'maintenance_contract_view.xml',
             'common_model_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}