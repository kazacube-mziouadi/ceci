# -*- coding: utf-8 -*-
{
    'name' : 'Characteristics',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'license': 'Open-prod license',
    'category' : 'Sale',
    'description' : """ Production declaration interface """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
             'product',
             'sale',
             'purchase',
                ],
                
    'data': [
             'characteristics_view.xml',
             'product_view.xml',
             'stock_view.xml',
             'security/ir.model.access.csv',
             'wizard/change_product_uom_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}