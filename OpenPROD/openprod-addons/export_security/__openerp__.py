# -*- coding: utf-8 -*-
{
    'name': 'Export security',
    'version': '1.0',
    'category': '',
    'description': """
     """,
    'author': 'Objectif PI',
    'depends': ['web'],
    'update_xml': [
       'security/ir.model.access.csv',
       'export_security_view.xml',
                   ],
    'test': [],
    'qweb': [
    ],
    'installable': True,
    'active': True,
    'auto_install': True,
}
