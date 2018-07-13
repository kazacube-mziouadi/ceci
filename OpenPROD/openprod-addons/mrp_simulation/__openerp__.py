# -*- coding: utf-8 -*-
{
    'name' : 'Simulation',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'category' : 'Manufacturing',
    'license': 'Open-prod license',
    'description' : """ Simulation """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
        'mrp',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'simulation_view.xml',
    ],
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}