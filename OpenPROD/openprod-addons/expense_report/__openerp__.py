# -*- coding: utf-8 -*-
{
    'name' : 'Expense report',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'category' : 'Human resource',
    'license': 'Open-prod license',
    'description' : """ Expense report """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
                    'human_resource',
                    'analytic_distribution',
                ],
                
    'data': [
                'data/expense_report_data_workflow.xml',
                'security/expense_report_security.xml',
                'security/ir.model.access.csv',
                'expense_report_view.xml',
                'product_view.xml',
            ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}