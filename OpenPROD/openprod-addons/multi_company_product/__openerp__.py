# -*- coding: utf-8 -*-
{
    'name' : 'Multi company product',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'category' : 'Base',
    'description' : """ Multiple company product""",
    'website': 'http://objectif-pi.com',
    'license': 'Open-prod license',
    'images' : [],
    'depends' : [
                    'sale_purchase'
                ],
                
    'data': [
                'security/ir.model.access.csv',
                'product_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}