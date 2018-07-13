# -*- coding: utf-8 -*-
{
    'name' : 'Wizard mo output',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'category' : 'Manufacturing',
    'license': 'Open-prod license',
    'description' : """ MRP """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
                    'mrp',
                ],
                
    'data': [
                'security/ir.model.access.csv',
                'wizard/wizard_mo_output_view.xml',
                'mrp_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}