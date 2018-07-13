# -*- encoding: utf-8 -*-


{
    'name': 'France - FEC',
    'version': '9.0.0.1.0',
    'category': 'French Localization',
    'license': 'LGPL',
    'summary': "Fichier d'Échange Informatisé (FEC) for France",
    'author': "OpenERP",
    'website': 'http://www.openerp.com',
    'depends': ['account'],
    'external_dependencies': {
        'python': ['unicodecsv'],
        },
    'data': [
        'wizard/fec_view.xml',
    ],
    'installable': True,
}
