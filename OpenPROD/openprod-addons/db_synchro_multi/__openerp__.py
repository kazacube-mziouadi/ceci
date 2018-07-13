# -*- coding: utf-8 -*-
{
    "name" : "Database synchro multi",
    "version" : "1.1",
    "author" : "Objectif PI",
    "website" : "www.objectif-pi.com",
    "category" : "Tools",
    "description": """""",
    "depends" : [
             'db_connection',
#              'ir_cron_adv'
             ],
    'update_xml': [
       'security/ir.model.access.csv',
       'db_synchro_multi_view.xml',
    ],
    'installable': True,
    'auto_install': False,
}