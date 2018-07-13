# -*- coding: utf-8 -*-

{
    'name' : 'Printers resource',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'category' : 'Base',
    'description' : """ Module printers for resource Open-Prod""",
    'website': 'http://objectif-pi.com',
    'license': 'Open-prod license',
    'images' : [],
    'depends' : [
                 'printers',
                 'base_openprod',
                 ],
                
    'data': [
             'data/mrp_resource_reports.xml',
             'mrp_resource_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': True,
}