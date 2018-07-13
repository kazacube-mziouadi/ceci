# -*- coding: utf-8 -*-
{
    'name' : 'SAV',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'license': 'Open-prod license',
    'category' : 'Tools',
    'description' : """ SAV""",
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
                 'base_gmao_sav',
                 'quick_creation_mo'
                ],
                
    'data': [
             'data/sequence.xml',
             'data/mail_template.xml',
             'data/state.xml',
             'security/sav_security.xml',
             'security/ir.model.access.csv',
             'wizard/quick_creation_mo_view.xml',
             'sav_view.xml',
             'stock_view.xml',
             'calendar_event_view.xml',
             'crm_reclaim_view.xml'
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}