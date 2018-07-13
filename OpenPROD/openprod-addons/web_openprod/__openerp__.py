# -*- coding: utf-8 -*-


{
    'name': 'Web OpenProd',
    'author' : 'Objectif PI',
    'license': 'Open-prod license',
    'category': 'Hidden',
    'description':"""
    
OpenProd web features
=====================

""",
    'website': 'http://objectif-pi.com',
    'version': '1.0',
    'depends': [
        'web_char_trim',
        'web_highstock',
        'web_to_upper',
        'web_tree_field_color',
        'web_float_time_seconds',
                ],
    'data' : [
        'web_openprod.xml',
    ],
#     'js': [
#         'static/src/js/web_openprod.js',
#     ],
#     'css': [
#         'static/src/css/web_openprod.css',
#     ],
    'qweb' : [
        'static/src/xml/web_openprod.xml',
    ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': True
}