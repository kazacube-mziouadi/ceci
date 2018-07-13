# -*- coding: utf-8 -*-
__name__ = "Delete security groups to update their external ids"


def migrate(cr, v):
    """
    :param cr: Current cursor to the database
    :param v: version number
    """
    cr.execute("""Delete from 
                      res_groups 
                  where 
                      name in ('GMAO user', 'GMAO manager', 'GMAO configuration', 'SAV user', 'SAV manager', 'SAV configuration')
                """)
    
    cr.execute("""Delete from 
                      ir_model_data 
                  where 
                      id in (select id from ir_model_data where name ilike '%menu%gmao%' and model = 'res.groups')
                """)
    
    cr.execute("""Delete from 
                      ir_model_data 
                  where 
                      id in (select id from ir_model_data where name ilike '%menu%sav%' and model = 'res.groups')
                """)