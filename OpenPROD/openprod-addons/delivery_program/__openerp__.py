# -*- coding: utf-8 -*-
{
    'name' : 'Delivery program',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'license': 'Open-prod license',
    'category' : 'Delivery',
    'description' : """ Delivery program """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
        'mrp'       
    ],
                
    'data': [
        'data/stock_data.xml',
        'wizard/create_quick_mo_view.xml',
        'delivery_program_view.xml',
        'stock_view.xml'
    ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}