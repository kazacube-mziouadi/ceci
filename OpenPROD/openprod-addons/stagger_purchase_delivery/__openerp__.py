# -*- coding: utf-8 -*-
{
    'name' : 'Stagger purchase delivery',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'license': 'Open-prod license',
    'category' : 'Purchase',
    'description' : """ Stagger purchase delivery """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
                'purchase',
                ],
                
    'data': [
             'wizard/stagger_delivery_view.xml',
             'purchase_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}