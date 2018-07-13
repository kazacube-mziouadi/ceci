# -*- coding: utf-8 -*-
{
    'name' : 'Freight cost',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'license': 'Open-prod license',
    'category' : 'Sale',
    'description' : """ Freight cost """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
             'mrp',
                ],
                
    'data': [
                'data/product_data.xml',
                'wizard/freight_cost_wizard_view.xml',
                'sale_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}