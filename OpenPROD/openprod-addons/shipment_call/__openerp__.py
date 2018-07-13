# -*- coding: utf-8 -*-
{
    'name': 'Shipment call',
    'version': '0.1',
    'author': 'Objectif PI',
    'license': 'Open-prod license',
    'category': 'Wharehouse',
    'description': """ Shipment call """,
    'website': 'http://objectif-pi.com',
    'images': [],
    'depends': [
        'shipment',
        'purchase',
    ],
    'data': [
        'wizard/shipment_call_quick_create_view.xml',
        'wizard/volume_compute_view.xml',
        'wizard/update_shipment_call_date_view.xml',
        'shipment_call_view.xml',
        'stock_view.xml',
        'data/shipment_sequence.xml',
        'security/ir.model.access.csv',
    ],
    'qweb': [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}
