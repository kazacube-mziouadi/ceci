# -*- coding: utf-8 -*-
{
    'name' : 'Stagger sale delivery',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'license': 'Open-prod license',
    'category' : 'Sale',
    'description' : """ Stagger sale delivery """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
                'sale',
                ],
                
    'data': [
             'wizard/stagger_delivery_view.xml',
             'sale_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}