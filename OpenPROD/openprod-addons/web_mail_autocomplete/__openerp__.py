# -*- coding: utf-8 -*-
{
    'name': 'Web mail autocomplete',
    'version': '1.0',
    'category': 'Tools',
    'complexity': "easy",
    'description': """Add autocomplete on char fields when widget="multimail" declared on form view""",
    'author': 'Objectif-PI',
    'license': 'Open-prod license',
    'website': 'http://www.objectif-pi.com',
    'depends': ['base','web'],
    'installable': True,
    'auto_install': False,
    'data': [
             'email_template_view.xml',
             ]
}
