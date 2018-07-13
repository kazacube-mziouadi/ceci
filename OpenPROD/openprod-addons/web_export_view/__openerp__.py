# -*- coding: utf-8 -*-


{
    'name': 'Export Current View',
    'version': '8.0.1.2.0',
    'category': 'Web',
    'author': "Objectif-PI",
    'website': 'http://www.open-prod.com',
    'license': 'LGPL',
    'depends': [
        'web',
    ],
    'data': [
        'view/web_export_view.xml',
    ],
    'qweb': [
        'static/src/xml/web_export_view_template.xml',
    ],
    'installable': True,
    'auto_install': False,
}
