# -*- coding: utf-8 -*-
{
    'name' : 'Planning priority',
    'version' : '1.1',
    'author' : 'Objectif PI',
    'category' : 'Planning priority',
    'license': 'Open-prod license',
    'description' : """ MRP """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
                    'sandbox',
                ],
                
    'data': [
            'wizard/planning_priority_wo_view.xml',
            'mrp_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}