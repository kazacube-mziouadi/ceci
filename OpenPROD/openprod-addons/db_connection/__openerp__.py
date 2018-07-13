# -*- coding: utf-8 -*-
{
    'name': 'DB connection',
    'version': '0.1',
    'category': 'Tools',
    'complexity': "easy",
    'description': """ Database connection """,
    'author': 'Objectif PI',
    'website': 'http://objectif-pi.com',
    'depends': ['base_openprod'],
    'init_xml': [],
    'update_xml': [
           'security/ir.model.access.csv',
           'db_connection_view.xml',
    ],
    'installable': True
}