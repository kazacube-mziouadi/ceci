# -*- coding: utf-8 -*-
{
    'name': 'Charge',
    'version': '1.0',
    'category': 'Tools',
    'description': """Charge charts""",
    'author': 'Objectif-PI',
    'license': 'Open-prod license',
    'website': 'http://open-prod.com',
    'depends': [
            'web_charts',
            'mrp',
            'calendar',
                ],
    'data': [
             "charge_view.xml",
             ],
    'installable': True,
    'auto_install': True,
}