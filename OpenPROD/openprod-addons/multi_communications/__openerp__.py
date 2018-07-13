# -*- coding: utf-8 -*-
{
    'name' : 'Multi communications',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'category' : 'Communication',
    'description' : """ Multiple communications """,
    'website': 'http://objectif-pi.com',
    'license': 'Open-prod license',
    'images' : [],
    'depends' : [
                 'partner_openprod',
                ],
                
    'data': [
            'security/ir.model.access.csv',
            'data/communication_type_data.xml',
            'communication_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}