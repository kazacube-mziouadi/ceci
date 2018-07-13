# -*- coding: utf-8 -*-
{
    'name': 'Float Time Seconds',
    'version': '1.0',
    'category': 'Tools',
    'complexity': "easy",
    'description': """Monkey patching value parsing/formatting in order to display seconds on demand""",
    'author': 'Objectif-PI',
    'license': 'Open-prod license',
    'website': 'http://openerp.com',
    'depends': [
            'web', 
            'web_kanban',
                ],
    'data': [
             "web_float_time_seconds.xml"
             ],
    'installable': True,
    'auto_install': True,
    'js': ['static/src/js/web_float_time_seconds.js'],
}