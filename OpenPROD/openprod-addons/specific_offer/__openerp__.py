# -*- coding: utf-8 -*-
{
    'name' : 'Specific offer',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'license': 'Open-prod license',
    'category' : 'Sale',
    'description' : """ Simulator price """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
             'crm_openprod',
                ],
                
    'data': [
             'wizard/change_simulation_line_view.xml',
             'wizard/create_sale_view.xml',
             'data/mail_template.xml',
             'security/ir.model.access.csv',
             'specific_offer_view.xml',
             'data/specific_offer_sequence.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}