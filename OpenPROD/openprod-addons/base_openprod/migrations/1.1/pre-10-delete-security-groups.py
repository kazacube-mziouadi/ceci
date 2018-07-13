# -*- coding: utf-8 -*-
__name__ = "Delete security groups to create them in the good module"


def migrate(cr, v):
    """
    :param cr: Current cursor to the database
    :param v: version number
    """
    cr.execute("""delete from 
                    ir_model_access 
                  where group_id in
                     (select id from res_groups where category_id in 
                        (select id from ir_module_category where name='Resource'))
                """)
    cr.execute("""Delete from 
                      res_groups 
                  where 
                      category_id = (select id from ir_module_category where name='Resource')
                  or
                      name in ('Resource user', 'Resource analysis', 'Resource configuration')
                """)
    cr.execute("""Delete from 
                      ir_module_category 
                  where 
                      name='Resource'
                """)
