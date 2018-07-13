# -*- coding: utf-8 -*-
{
    "name" : "Control management",
    "version" : "1.1",
    "author" : "Objectif PI",
    "website" : "www.objectif-pi.com",
    'license': 'Open-prod license',
    "category" : "",
    "description": """""",
    "depends" : [
        'analytic_distribution'
    ],
    'update_xml': [
       'security/ir.model.access.csv',
       'control_management_view.xml',
       'account_analytic_view.xml',
       'treasury_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}