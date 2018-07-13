# -*- coding: utf-8 -*-
{
    'name' : 'Affair',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'license': 'Open-prod license',
    'category' : 'Manufacturing',
    'description' : """ Affair""",
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
                 'mrp',
                 'project'
                ],
                
    'data': [
             'security/ir.model.access.csv',
             'data/affair_sequence.xml',
             'data/affair_state.xml',
             'data/affair_mail_template.xml',
             'calendar_event_view.xml',
             'affair_view.xml',
             'sale_view.xml',
             'mrp_view.xml',
             'purchase_view.xml',
             'project_view.xml',
             'common_model_view.xml',
             'wizard/quick_create_project_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}