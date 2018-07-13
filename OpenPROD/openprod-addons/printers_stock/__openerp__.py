# -*- coding: utf-8 -*-

{
    'name' : 'Stock printers',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'category' : 'Base',
    'description' : """ Module printers for stock Open-Prod""",
    'website': 'http://objectif-pi.com',
    'license': 'Open-prod license',
    'images' : [],
    'depends' : [
                 'printers',
                 'stock',
                 ],
                
    'data': [
             'data/stock_reports.xml',
             'stock_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': True,
}