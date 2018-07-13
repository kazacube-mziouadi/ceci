# -*- coding: utf-8 -*-
{
    'name': 'Shipment packing list',
    'version': '0.1',
    'author': 'Objectif PI',
    'license': 'Open-prod license',
    'category': 'Wharehouse',
    'description': """ Shipment packing list """,
    'website': 'http://objectif-pi.com',
    'images': [],
    'depends': [
        'shipment',
    ],
    'data': [
        'wizard/create_packing_list_view.xml',
        'wizard/delete_packing_list_view.xml',
        'shipment_view.xml',
        'stock_view.xml',
    ],
    'qweb': [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}
