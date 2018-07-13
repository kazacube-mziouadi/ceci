# -*- coding: utf-8 -*-
{
    'name' : 'Customs',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'category' : 'Customs',
    'license': 'Open-prod license',
    'description' : """ Allow to manage customs prices """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
                 'sale_purchase',
                 ],
                
    'data': [
             'wizard/update_move_customs_price_view.xml',
             'stock_view.xml',
             'product_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}