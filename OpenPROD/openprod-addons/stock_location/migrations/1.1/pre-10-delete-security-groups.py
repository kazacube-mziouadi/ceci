# -*- coding: utf-8 -*-
__name__ = "Delete security groups to update their external ids"


def migrate(cr, v):
    """
    :param cr: Current cursor to the database
    :param v: version number
    """
    cr.execute("""delete from 
                    ir_model_access 
                  where group_id in
                     (select id from res_groups where category_id in 
                        (select id from ir_module_category where name='Stock'))
                """)
    cr.execute("""Delete from 
                      res_groups 
                  where 
                      category_id = (select id from ir_module_category where name='Stock')
                """)
