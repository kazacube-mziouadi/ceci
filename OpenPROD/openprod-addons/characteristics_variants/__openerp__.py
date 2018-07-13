# -*- coding: utf-8 -*-
{
    'name' : 'Characteristics Variants',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'license': 'Open-prod license',
    'category' : 'Sale',
    'description' : """ Production declaration interface """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
             'characteristics',
             'variants',
                ],
                
    'data': [
             'wizard/create_variants_view.xml',
             'wizard/update_variants_view.xml',
             'characteristics_variants_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': True,
}