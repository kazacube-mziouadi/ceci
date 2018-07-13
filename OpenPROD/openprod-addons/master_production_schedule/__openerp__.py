# -*- coding: utf-8 -*-
{
    'name' : 'Master production schedule',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'license': 'Open-prod license',
    'category' : 'Production',
    'description' : """ Master production schedule (MPS) """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
                'mrp',
                'charge',
                ],
                
    'data': [
             'security/ir.model.access.csv',
             'wizard/change_program_line_view.xml',
             'wizard/display_reservation_view.xml',
             'master_production_schedule_view.xml',
             'mrp_view.xml',
             'calendar_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}