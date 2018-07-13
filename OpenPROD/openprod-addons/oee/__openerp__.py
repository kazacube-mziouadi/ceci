# -*- coding: utf-8 -*-
{
    'name': 'OEE',
    'version': '1.0',
    'author': 'Objectif PI',
    'category': 'Manufacturing',
    'license': 'Open-prod license',
    'description': """ Overall Equipment Effectiveness """,
    'website': 'http://objectif-pi.com',
    'images': [],
    'depends': [
                'mrp',
                ],
    'data': [
             'oee_view.xml',
             'security/ir.model.access.csv',
             ],
    'qweb': [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}
