# -*- encoding: utf-8 -*-


{
    'name': 'Decimal Precision Configuration',
    'description': """
Configure the price accuracy you need for different kinds of usage: accounting, sales, purchases.
=================================================================================================

The decimal precision is configured per company.
""",
    'author': 'Objectif-PI',
    'license': 'LGPL',
    'version': '0.1',
    'depends': ['calendar_event'],
    'category' : 'Hidden/Dependency',
    'data': [
        'decimal_precision_view.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [],
    'installable': True,
    'images': ['images/1_decimal_accuracy_form.jpeg','images/1_decimal_accuracy_list.jpeg'],
    'auto_install': True,
}



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
