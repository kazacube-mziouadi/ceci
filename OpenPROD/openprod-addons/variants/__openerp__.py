# -*- coding: utf-8 -*-
{
    'name' : 'Variants',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'license': 'Open-prod license',
    'category' : 'Manufacturing',
    'description' : """ Variants """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
                 'base_openprod',
                 'product',
                 'mrp',
                ],
                
    'data': [
             'wizard/create_variants_view.xml',
             'wizard/edit_categories_view.xml',
             'wizard/update_variants_view.xml',
             'wizard/update_variants_categories_view.xml',
             'wizard/fill_questionnaire_view.xml',
             'wizard/create_configure_sol_view.xml',
             'product_view.xml',
             'mrp_view.xml',
             'sale_view.xml',
             'security/ir.model.access.csv',
             'questionnaire_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}