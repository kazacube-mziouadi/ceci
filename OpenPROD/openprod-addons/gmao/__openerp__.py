# -*- coding: utf-8 -*-
{
    'name' : 'GMAO',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'license': 'Open-prod license',
    'category' : 'Tools',
    'description' : """ GMAO""",
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
                 'base_gmao_sav'
                ],
                
    'data': [
             'security/gmao_security.xml',
             'gmao_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}