# -*- coding: utf-8 -*-

{
    'name' : 'Base Printers',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'license': 'LGPL',
    'category' : 'Base',
    'description' : """ Base printers module for Open-Prod""",
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
                 'base',
                 'base_setup',
                 ],
                
    'data': ['security/ir.model.access.csv',],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}