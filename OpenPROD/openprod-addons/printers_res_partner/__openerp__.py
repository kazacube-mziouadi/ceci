# -*- coding: utf-8 -*-

{
    'name' : 'Partner printers',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'category' : 'Base',
    'description' : """ Module printers for partner Open-Prod""",
    'website': 'http://objectif-pi.com',
    'license': 'Open-prod license',
    'images' : [],
    'depends' : [
                 'printers',
                 'partner_openprod',
                 ],
                
    'data': [
             'data/res_partner_reports.xml',
             'security/ir.model.access.csv',
             'wizard/print_partner_address_view.xml',
             'res_partner_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': True,
}