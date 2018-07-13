# -*- coding: utf-8 -*-


{
    'name': 'Binary Attachment',
    'author' : 'Objectif PI',
    'license': 'Open-prod license',
    'category': 'Hidden',
    'description':"""

Store binary fields in ir_attachment object.    

""",
    'website': 'http://objectif-pi.com',
    'version': '1.0',
    'depends': [
                'base',
                'document',
                ],
    'data' : [
#         'product_view.xml',
          'ir_attachment_view.xml',
          'binary_attachment_web.xml',
    ],
#     'js': [
#         'static/src/js/web_openprod.js',
#     ],
#     'css': [
#         'static/src/css/web_openprod.css',
#     ],
#     'qweb' : [
#         'static/src/xml/web_openprod.xml',
#     ],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': True
}