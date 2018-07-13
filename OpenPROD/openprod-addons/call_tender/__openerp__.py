# -*- coding: utf-8 -*-
{
    'name' : 'Call for tender',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'category' : 'Purchase',
    'description' : """ Call for tender """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
                'purchase',
                ],
                
    'data': [
             'security/ir.model.access.csv',
             'data/call_tender_sequence.xml',
             'data/call_tender_mail_template.xml',
             'wizard/select_products_view.xml',
             'wizard/generate_answer_view.xml',
             'call_tender_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}