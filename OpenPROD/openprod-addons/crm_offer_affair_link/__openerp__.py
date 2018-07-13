# -*- coding: utf-8 -*-
{
    'name' : 'CRM, offer and affair link',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'license': 'Open-prod license',
    'category' : '',
    'description' : """ Link between CRM, specific offers and affairs """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
             'affair',
             'specific_offer',
                ],
                
    'data': [
             'crm_offer_affair_link_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}