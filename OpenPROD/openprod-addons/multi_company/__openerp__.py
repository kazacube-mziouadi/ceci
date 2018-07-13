# -*- coding: utf-8 -*-
{
    'name' : 'Multi company',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'category' : 'Base',
    'description' : """ Multiple company """,
    'website': 'http://objectif-pi.com',
    'license': 'Open-prod license',
    'images' : [],
    'depends' : [
                    'sale_purchase'
                ],
                
    'data': [
                'security/ir.model.access.csv',
                'res_partner_view.xml',
                'product_view.xml',
                'sale_view.xml',
                'purchase_view.xml',
                'mrp_view.xml',
                'stock_view.xml',
                'account_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}