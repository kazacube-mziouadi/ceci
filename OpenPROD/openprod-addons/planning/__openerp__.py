# -*- coding: utf-8 -*-
{
    'name' : 'Planning',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'category' : 'Manufacturing',
    'description' : """ Planning """,
    'website': 'http://objectif-pi.com',
    'license': 'Open-prod license',
    'images' : [],
    'depends' : [
                 'mrp',
                ],
                
    'data': [
             'planning_view.xml',
             'mrp_planning_mo_view.xml',
             'data/parameter_data.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}