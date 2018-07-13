# -*- coding: utf-8 -*-


{
    'name': 'JasperReport Server Interface',
    'version': '6.3',
    'license': 'LGPL',
    'category': 'Reporting',
    'sequence': 20,
    'complexity': "expert",
    'description': """This module interface JasperReport Server with OpenERP
Features:
- Document source must be in CSV, XML
- Save document as attachment on object
- Retrieve attachment if present
- Launch multiple reports and merge in one printing action
- Add additionnals parameters (ex from fields function)
- Affect group on report
- Use context to display or not the print button
    (eg: in stock.picking separate per type)
- Execute SQL query before and after treatement
- Launch report based on SQL View
- Add additional pages at the begining or at the end of the document

This module required library to work properly

# pip install httplib2 (>= 0.6.0)
# pip install pyPdf (>= 1.13)



""",
    'author': 'Objectif-PI SYLEAM',
    'website': 'http://www.syleam.fr',
    'images': ['images/accueil.png', 'images/palette.png',
               'images/document_form.png'],
    'depends': [
        'base_printers',
    ],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/jasper_document_extension.xml',
        'wizard/wizard.xml',
        'wizard/load_file_view.xml',
        'obj_server_view.xml',
        'obj_document_view.xml',
        'res_users_view.xml',
    ],
    'demo': [
        'demo/jasper_document.xml',
    ],
    'installable': True,
    'auto_install': False,
    'external_dependencies': {'python': ['httplib2', 'pyPdf', 'dime']},
    'application': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
