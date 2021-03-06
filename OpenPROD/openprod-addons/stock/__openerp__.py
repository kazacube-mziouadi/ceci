# -*- coding: utf-8 -*-
{
    'name' : 'Stock',
    'version' : '1.2',
    'author' : 'Objectif PI',
    'license': 'Open-prod license',
    'category' : 'Warehouse management',
    'description' : """ """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
                'stock_location',
                ],
                
    'data': [
             'data/nonconformity_mail_template.xml',
             'security/stock_security.xml',
             'security/ir.model.access.csv',
             'stock_menu_view.xml',
             'config/stock_config_view.xml',
             'wizard/partial_picking_view.xml',
             'wizard/return_picking_view.xml',
             'wizard/stock_level_rectification_view.xml',
             'wizard/picking_quick_create_view.xml',
             'wizard/picking_update_covers_view.xml',
             'wizard/create_label_view.xml',
             'wizard/add_freight_picking_view.xml',
             'wizard/move_label_view.xml',
             'wizard/assign_label_view.xml',
             'wizard/assign_lot_view.xml',
             'wizard/close_label_view.xml',
             'wizard/balancing_label_view.xml',
             'wizard/split_label_view.xml',
             'wizard/recalculate_label_view.xml',
             'wizard/covers_compute_view.xml',
             'wizard/product_valuation_view.xml',
             'wizard/product_procurement_view.xml',
             'wizard/confirm_date_view.xml',
             'wizard/traceability_view.xml',
             'wizard/product_storage_view.xml',
             'wizard/show_warehouse_stock_level_view.xml',
             'wizard/choose_picking_view.xml',
             'wizard/reopen_picking_view.xml',
             'wizard/change_move_label_qty_view.xml',
             'wizard/change_move_date_view.xml',
             'wizard/add_move_to_picking_view.xml',
             'report/quality_report_view.xml',
             'wizard/change_product_uom_view.xml',
             'wizard/create_transfer_view.xml',
             'stock_incoterms_data.xml',
             'data/stock_sequence.xml',
             'data/stock_data.xml',
             'data/nonconformity_data_workflow.xml',
             'stock_view.xml',
             'product_view.xml',
             'calendar_event_view.xml',
             'company_view.xml',
             'report/stock_level_report_view.xml',
             'report/location_stock_level_report_view.xml',
             'report/stock_move_label_report_view.xml',
             'report/stock_synthesis_valuation_report_view.xml',
             'document_openprod_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}