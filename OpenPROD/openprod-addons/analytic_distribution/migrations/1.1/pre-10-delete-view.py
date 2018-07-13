# -*- coding: utf-8 -*-
__name__ = "Delete view view_form_product_analytic_mrp"


def migrate(cr, v):
    """
    :param cr: Current cursor to the database
    :param v: version number
    """
    cr.execute("""Delete from 
                      ir_ui_view 
                  where 
                      id = (select 
                                res_id 
                            from 
                                ir_model_data 
                            where 
                                model = 'ir.ui.view' and 
                                name = 'view_form_product_analytic_mrp' and 
                                module = 'analytic_distribution' limit 1)
                """)
