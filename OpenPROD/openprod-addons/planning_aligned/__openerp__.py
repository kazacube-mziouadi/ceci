# -*- coding: utf-8 -*-
{
    'name' : 'Planning aligned',
    'version' : '1.1',
    'author' : 'Objectif PI',
    'category' : 'Planning aligned',
    'license': 'Open-prod license',
    'description' : """ MRP """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
                    'mrp',
                ],
                
    'data': [
            'wizard/planning_aligned_mo_view.xml',
            'mrp_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}