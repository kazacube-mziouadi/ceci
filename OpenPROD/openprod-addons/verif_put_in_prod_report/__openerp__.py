# -*- coding: utf-8 -*-
{
    'name': 'Verification put in production report',
    'version': '0.1',
    'category': 'Tools',
    'complexity': "easy",
    'description': """""",
    'author': 'Objectif PI',
    'website': 'http://objectif-pi.com',
    'depends': ['jasper_server'],
    'init_xml': [],
    'update_xml': [
            'security/ir.model.access.csv',
            'verif_putinprod_report_view.xml',

    ],
    'installable': True
}

