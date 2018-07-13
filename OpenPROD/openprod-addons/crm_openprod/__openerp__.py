# -*- coding: utf-8 -*-
{
    'name' : 'CRM',
    'version' : '1.1',
    'author' : 'Objectif PI',
    'category' : 'Customer Relationship Management',
    'license': 'Open-prod license',
    'description' : """ The Customer Relationship Management""",
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
                 'sale',
                 ],
                
    'data': [
             'security/ir.model.access.csv',
             'security/crm_security.xml',
             'data/sequence.xml',
             'data/mail_template.xml',
             'data/state.xml',
             'wizard/create_partner_view.xml',
             'calendar_event_view.xml',
             'res_users_view.xml',
             'crm_view.xml',
             'common_model_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}