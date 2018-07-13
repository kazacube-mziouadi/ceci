# -*- coding: utf-8 -*-

{
    'name' : 'MRP printers',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'category' : 'Base',
    'description' : """ Module printers for mrp in Open-Prod""",
    'website': 'http://objectif-pi.com',
    'license': 'Open-prod license',
    'images' : [],
    'depends' : [
                 'printers',
                 'mrp',
                 ],
                
    'data': ['data/mrp_reports.xml',],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': True,
}