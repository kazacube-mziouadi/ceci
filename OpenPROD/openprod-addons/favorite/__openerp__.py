# -*- coding: utf-8 -*-
{
    'name' : 'Favorite',
    'version' : '0.1',
    'author' : 'Objectif PI',
    'category' : 'Favorite',
    'description' : """ Favorite """,
    'website': 'http://objectif-pi.com',
    'license': 'Open-prod license',
    'images' : [],
    'depends' : ['web'],
    'data': ['favorite_view.xml',
             'security/ir.model.access.csv', 
             'menu_template.xml'],
    'qweb' : ['static/src/xml/favorite_template.xml'],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': True,
}
