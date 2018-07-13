# -*- coding: utf-8 -*-

{
    'name': 'Translator',
    'version': '1.0',
    'author' : 'Objectif PI',
    'website': 'http://objectif-pi.com',
    'license': 'LGPL',
    'category': 'interface',
    'depends': [
        'base',
        'web',
    ],
    'data': [
        'web_imports.xml',
        'translate_wizard_view.xml',
        'res_lang_view.xml',
        'res_company_view.xml',
        'security/groups.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'auto_install': False,
}
