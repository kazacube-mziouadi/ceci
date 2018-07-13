# -*- coding: utf-8 -*-
{
    'name' : 'Sale Purchase',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'license': 'Open-prod license',
    'category' : 'Sale',
    'description' : """ Sales and Purchases management """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
                'sale',
                'purchase',
                ],
                
    'data': [
             'security/ir.model.access.csv',
             'wizard/wizard_price_purchase_view.xml',
             'wizard/display_reservation_view.xml',
             'wizard/wiz_add_certificate_application_view.xml',
             'wizard/compute_taxes_view.xml',
             'certificate_management_view.xml',
             'product_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}