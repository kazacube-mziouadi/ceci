# -*- coding: utf-8 -*-
{
    'name' : 'Purchase',
    'version' : '1.3',
    'author' : 'Objectif PI',
    'category' : 'Purchase',
    'license': 'Open-prod license',
    'description' : """ Purchases management """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
                'stock',
                ],
                
    'data': [
             'menu_purchase.xml',
             'security/purchase_security.xml',
             'security/ir.model.access.csv',
             'data/purchase_order_sequence.xml',
             'data/purchase_email_template.xml',
             'data/purchase_cron.xml',
             'data/purchase_order_workflow.xml',
             'config/stock_config_view.xml',
             'config/technical_data_config_view.xml',
             'config/purchase_config_view.xml',
             'wizard/change_confirmed_date_view.xml',
             'wizard/select_confirm_date_view.xml',
             'wizard/create_quick_purchase_view.xml',
             'wizard/change_supplier_view.xml',
             'wizard/change_product_uom_view.xml',
             'wizard/merge_purchases_view.xml',
             'wizard/generate_called_order_view.xml',
             'wizard/anticipated_invoice_view.xml',
             'wizard/choose_partner_view.xml',
             'wizard/confirm_date_view.xml',
             'wizard/purchase_change_account_system_view.xml',
             'wizard/purchase_change_note_view.xml',
             'wizard/change_purchase_wizard_view.xml',
             'purchase_view.xml',
             'product_view.xml',
             'stock_view.xml',
             'res_partner_view.xml',
             'account_invoice_view.xml',
             'calendar_event_view.xml',
             'res_company_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}