# -*- coding: utf-8 -*-
#


{
    'name': 'Printers',
    'version': '1.1',
    'category': 'Tools',
    'description': """Allow to manage printers in Open-prod""",
    'author': 'Objectif-pi',
    'website': 'http://www.objectif-pi.com/',
    'license': 'LGPL',
    'depends': [
        'jasper_server',
    ],
    'images': [],
    'data': [
        'security/ir.model.access.csv',
        'menu_view.xml',
        'base_view.xml',
        'server_action_view.xml',
        'printers_view.xml',
        'printers_data.xml',
        'ir_cron_data.xml',
        'printers_report_view.xml',
    ],

    'qweb': [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,

}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
