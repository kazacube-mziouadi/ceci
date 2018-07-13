# -*- coding: utf-8 -*-
{
    'name' : 'Test Builder',
    'version' : '1.1',
    'author' : 'Objectif PI',
    'license': 'Open-prod license',
    'category' : 'test',
    'description' : """ Test Builder and launcher     """,
    'website': 'http://objectif-pi.com',
    'data': [
             'wizard/launch_test_suit_view.xml',
             'wizard/add_scenarios_view.xml',
             'test_builder_view.xml',
             'data/run_sequence.xml',
             'data/rules.xml',
             'data/default_values.xml',
             'security/ir.model.access.csv',
             ],
    'depends': [
        'jasper_server',
    ],
    'installable': True,
    'auto_install': False,
}