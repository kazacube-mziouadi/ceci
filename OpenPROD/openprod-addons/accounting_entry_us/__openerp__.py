# -*- coding: utf-8 -*-
{
    'name' : 'Accounting entry US',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'license': 'Open-prod license',
    'category' : 'Accounting & Finance',
    'description' : """ Accounting entry US """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
                 'mrp',
                ],
                
    'data': [             
                'security/ir.model.access.csv',
                'data/stock_data.xml',
                'product_view.xml',
                'stock_view.xml',
                'mrp_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}