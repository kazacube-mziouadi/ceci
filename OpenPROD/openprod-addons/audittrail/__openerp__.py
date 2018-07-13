# -*- coding: utf-8 -*-
{
    'name' : 'Audit Trail',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'license': 'Open-prod license',
    'category' : 'Tools',
    'description' : """ Audit trails """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
                 'base_openprod'
                ],
                
    'data': [
             'audittrail_view.xml',
             'wizard/model_log_view.xml',
             'security/ir.model.access.csv',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}