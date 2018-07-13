# -*- coding: utf-8 -*-
{
    'name' : 'EDI Openprod',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'license': 'Open-prod license',
    'category' : '',
    'description' : """ EDI Openprod 
                        Penser à lancer ces commandes avant d'installer le module: 
                            pip install xlutils
                            pip install xlrd
                            pip install xlwt
                """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
             'base_openprod',
             'jasper_server',
                ],
                
    'data': [
             'security/edi_security.xml',
             'security/ir.model.access.csv',
             'wizard/choose_m2o_view.xml',
             'edi_openprod_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}