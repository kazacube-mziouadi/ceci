# -*- coding: utf-8 -*-
{
    'name' : 'Debug',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'license': 'Open-prod license',
    'category' : 'Product',
    'description' : """ Mass date import, execution times tests, ... """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
             'product'
                ],
                
    'data': [
             'security/ir.model.access.csv',
             'data_insert_view.xml',
             'times_test_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}