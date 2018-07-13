# -*- coding: utf-8 -*-
{
    'name' : 'MRP',
    'version' : '1.1',
    'author' : 'Objectif PI',
    'category' : 'Manufacturing',
    'license': 'Open-prod license',
    'description' : """ MRP """,
    'website': 'http://objectif-pi.com',
    'images' : [],
    'depends' : [
                    'sale_purchase',
                ],
                
    'data': [
            'data/product_data.xml',
            'data/mrp_group_wo_sequence.xml',
            'data/mrp_manufacturingorder_sequence.xml',
            'data/cron.xml',
            'security/manufacturing_security.xml',
            'security/ir.model.access.csv',
            'config/stock_config_view.xml',
            'config/technical_data_config_view.xml',
            'wizard/importation_component_bom_view.xml',
            'wizard/importation_routing_line_view.xml',
            'wizard/mrp_add_product_view.xml',
            'wizard/mrp_see_bom_view.xml',
            'wizard/mrp_add_resource_view.xml',
            'wizard/wo_declaration_view.xml',
            'wizard/change_qty_mo_view.xml',
            'wizard/split_wo_view.xml',
            'wizard/split_mo_view.xml',
            'wizard/mrp_planning_mo_view.xml',
            'wizard/change_date_wo_view.xml',
            'wizard/print_wo_view.xml',
            'wizard/purchase_subcontracting_view.xml',
            'wizard/production_operator_time_view.xml',
            'wizard/mrp_add_operation_view.xml',
            'wizard/report_wo_planning_view.xml',
            'wizard/confirm_date_view.xml',
            'wizard/switch_document_view.xml',
            'wizard/display_reservation_view.xml',
            'wizard/son_mo_wo_view.xml',
            'wizard/wizard_create_timetracking_view.xml',
            'wizard/more_produce_view.xml',
            'wizard/cost_simulation_view.xml',
            'wizard/compute_cost_view.xml',
            'wizard/label_comsuption_view.xml',
            'report/quality_report_view.xml',
            'mrp_view.xml',
            'product_view.xml',
            'sale_view.xml',
            'mrp_replacement_resource_view.xml',
            'stock_view.xml',
            'calendar_view.xml',
            'purchase_view.xml',
            'res_partner_view.xml',
            'calendar_event_view.xml',
            'document_openprod_view.xml',
             ],
             
    'qweb' : [],
    'demo': [],
    'test': [],
    'installable': True,
    'auto_install': False,
}