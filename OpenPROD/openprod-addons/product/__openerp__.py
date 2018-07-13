# -*- coding: utf-8 -*-
{
    'name' : 'Product',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'category' : 'Product',
    'description' : """ Product """,
    'website': 'http://objectif-pi.com',
    'license': 'Open-prod license',
    'images' : [],
    'depends' : [
             'base_openprod',
                ],
                
    'data': [
             'security/product_security.xml',
             'security/ir.model.access.csv',
             'data/product_data.xml',
             'data/product_sequence.xml',
             'data/product_data_workflow.xml',
             'wizard/change_dual_unit_view.xml',
             'wizard/change_product_uom_view.xml',
             'wizard/switch_document_view.xml',
             'product_view.xml',
             'document_openprod_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}