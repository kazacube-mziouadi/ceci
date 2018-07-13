# -*- coding: utf-8 -*-
{
    'name' : 'Substitution product',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'license': 'Open-prod license',
    'category' : 'Manufacturing',
    'description' : """ Substitution product """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
                'mrp',
                ],
                
    'data': [            
             'security/ir.model.access.csv',
             'wizard/wizard_substitution_product_view.xml',
             'mrp_view.xml',
             'purchase_view.xml',
             'product_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}