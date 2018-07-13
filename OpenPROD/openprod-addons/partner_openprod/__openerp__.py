# -*- coding: utf-8 -*-
{
    'name' : 'Partner Open-Prod',
    'version' : '1.0',
    'author' : 'Objectif PI',
    'category' : 'Partner',
    'description' : """ Partners """,
    'website': 'http://objectif-pi.com',
    'license': 'Open-prod license',
    'images' : [],
    'depends' : [
                 'calendar',
                ],
                
    'data': [
            'data/partner_email_template.xml',
            'data/partner_sequence.xml',
            'data/partner_data_workflow.xml',
            'security/partner_security.xml',
            'security/ir.model.access.csv',
            'wizard/mail_compose_message_view.xml',
            'wizard/switch_document_view.xml',
            'wizard/all_reset_workflow_view.xml',
            'res_partner_view.xml',
            'res_company_view.xml',
            'mail_template_view.xml',
            'document_openprod_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}