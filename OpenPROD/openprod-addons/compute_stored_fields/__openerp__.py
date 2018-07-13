# -*- coding: utf-8 -*-
{
    "name" : "Compute stored fields",
    "version" : "1.0",
    "author" : "Objectif PI",
    "website" : "www.objectif-pi.com",
    'license': 'Open-prod license',
    "category" : "",
    "description": """ Allow to recompute computed stored fields """,
    "depends" : [
        'base_openprod'
    ],
    'data': [
       'wizard/compute_stored_fields_import_view.xml',
       'wizard/compute_stored_fields_compute_view.xml',
       'compute_stored_fields_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}