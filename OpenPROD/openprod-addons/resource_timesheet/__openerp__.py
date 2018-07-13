# -*- coding: utf-8 -*-
{
    'name' : 'Resource timesheet',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'category' : '',
    'license': 'Open-prod license',
    'description' : """ Resource""",
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
                'calendar',
                ],
                
    'data': [
             'security/resource_security.xml',
             'security/ir.model.access.csv',
             'wizard/clock_in_out_view.xml',
             'wizard/wizard_create_timetracking_view.xml',
             'resource_timesheet.xml',
             'resource_timesheet_view.xml',
             ],
             
    'qweb': ['static/src/xml/resource_timesheet.xml',],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}