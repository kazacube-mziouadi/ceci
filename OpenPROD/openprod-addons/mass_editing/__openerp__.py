# -*- coding: utf-8 -*-

{
    "name": "Mass Editing",
    "version": "1.3",
    "author": "Objectif-PI",
    'license': 'LGPL',
    
    "category": "Tools",
   
    'depends': ['base'],
    'data': [
        "security/ir.model.access.csv",
        'views/mass_editing_view.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
