# -*- coding: utf-8 -*-
{
    'name' : 'MRP FTPR',
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
            'wizard/importation_routing_line_ftpr_view.xml',
            'wizard/compute_cost_view.xml',
            'wizard/add_resource_valid_view.xml',
            'wizard/duplicate_ftpr_view.xml',
            'mrp_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}