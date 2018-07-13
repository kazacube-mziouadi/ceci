# -*- coding: utf-8 -*-
{
    'name' : 'Stock location',
    'version' : '1.1',
    'author' : 'Objectif PI',
    'license': 'Open-prod license',
    'category' : 'Warehouse management',
    'description' : """ Stock location """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
                'account_openprod'
                ],
                
    'data': [
             'security/stock_location_security.xml',
             'security/ir.model.access.csv',
             'data/stock_data.xml',
             'stock_view.xml',
             'res_partner_view.xml',
             'mrp_resource_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}