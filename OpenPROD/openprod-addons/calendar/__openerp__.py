# -*- coding: utf-8 -*-
{
    'name' : 'Calendar',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'category' : 'Calendar',
    'license': 'Open-prod license',
    'description' : """ Calendar """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
             'base_openprod',
                ],
                
    'data': [
             'security/ir.model.access.csv',
             'data/calendar_data.xml',
             'wizard/create_template_lines_view.xml',
             'calendar_view.xml',
             'mrp_resource_view.xml',
             'cron_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}