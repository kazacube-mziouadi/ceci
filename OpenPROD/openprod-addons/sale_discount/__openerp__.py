# -*- coding: utf-8 -*-
{
    'name' : 'Sale discount',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'license': 'Open-prod license',
    'category' : 'Sale',
    'description' : """ Sale discount """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
             'sale',
                ],
                
    'data': [   
                'data/product_data.xml',
                'wizard/sale_order_line_discount_wizard_view.xml',
                'wizard/invoice_line_discount_wizard_view.xml',
                'sale_view.xml',
                'account_invoice_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}