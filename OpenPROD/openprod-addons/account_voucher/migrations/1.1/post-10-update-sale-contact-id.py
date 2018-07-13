# -*- coding: utf-8 -*-
__name__ = "TODO"


def migrate(cr, v):
    """
    :param cr: Current cursor to the database
    :param v: version number
    """
    cr.execute("""UPDATE 
                    wkf_activity 
                  SET 
                    can_not_be_deleted=false, 
                    required=false 
                  WHERE 
                    name='Generated payment' AND
                    wkf_id IN (SELECT id FROM wkf WHERE osv='account.bank.statement.openprod')""")
    
