# -*- coding: utf-8 -*-
{
    'name' : 'Base GMAO SAV',
    'version' : '1.1',
    'author' : 'Objectif PI',
    'license': 'Open-prod license',
    'category' : 'Tools',
    'description' : """ Base GMAO SAV """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
                 'mrp',
                 'maintenance_contract',
                 'quick_creation_mo'
                ],
                
    'data': [
             'data/base_gmao_sav_sequence.xml',
             'data/mail_template.xml',
             'security/gmao_sav_security.xml',
             'security/ir.model.access.csv',
             'wizard/add_operation_or_park_view.xml',
             'wizard/wizard_create_timetracking_view.xml',
             'wizard/wiz_intervention_quotation_view.xml',
             'wizard/create_picking_intervention_view.xml',
             'wizard/wiz_create_park_view.xml',
             'wizard/wiz_mo_repair_view.xml',
             'wizard/wiz_add_certificate_application_view.xml',
             'common_model_view.xml',
             'gmao_sav_view.xml',
             'maintenance_contract_view.xml',
             'certificate_management_view.xml',
             'partner_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}