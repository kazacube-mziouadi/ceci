# -*- coding: utf-8 -*-
{
    'name' : 'Schedule planning',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'license': 'Open-prod license',
    'category' : 'Tools',
    'description' : """ Schedule planning """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
                 'mrp'
                ],
                
    'data': [
             'security/ir.model.access.csv',
             'mrp_view.xml',
             'schedule_plannification_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}