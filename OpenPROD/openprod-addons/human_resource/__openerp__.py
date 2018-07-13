# -*- coding: utf-8 -*-
{
    'name' : 'Human resource',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'category' : 'Human resource',
    'license': 'Open-prod license',
    'description' : """ Human resource """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
                    'account_openprod',
                ],
                
    'data': [
             'data/holiday_workflow.xml',
             'security/human_resource_security.xml',
             'security/ir.model.access.csv',
             'data/holiday_type.xml',
             'employee_view.xml',
             'holiday_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}