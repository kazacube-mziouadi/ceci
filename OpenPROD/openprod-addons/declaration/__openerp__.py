# -*- coding: utf-8 -*-
{
    'name' : 'Declaration',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'license': 'Open-prod license',
    'category' : 'Manufacturing',
    'description' : """ Production declaration interface """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
             'base_openprod',
             'stock',
             'mrp',
                ],
                
    'data': [
             'security/declaration_security.xml',
             'stock_config_view.xml',
             'declaration_view.xml',
             'mrp_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}