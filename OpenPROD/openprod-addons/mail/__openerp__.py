# -*- coding: utf-8 -*-

{
    'name': 'Mail',
    'version': '1.0',
    'category': 'Discuss',
    'author' : 'Objectif PI',
    'sequence': 25,
    'summary': 'Mails',
    'description': """
    Send mail
""",
    'website': 'http://objectif-pi.com',
    'license': 'LGPL',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/mail_compose_message_view.xml',
        'views/mail_message_views.xml',
        'views/mail_mail_views.xml',
        'data/mail_data.xml',
        'views/mail_template_views.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': True,
    'qweb': [],
}
