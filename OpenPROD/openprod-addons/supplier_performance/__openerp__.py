# -*- coding: utf-8 -*-
{
    'name' : 'Supplier performance',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'category' : 'Purchase',
    'description' : """ Supplier performance analysis """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
                'purchase',
                ],
                
    'data': [
             'security/ir.model.access.csv',
             'supplier_performance_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}