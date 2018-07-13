# -*- coding: utf-8 -*-
__name__ = "Update accounts data"

def migrate(cr, v):
    """
    :param cr: Current cursor to the database
    :param v: version number
    """
    cr.execute("""UPDATE account_account SET debit_account_type_id=null,credit_account_type_id=null,close_method='none'
                  WHERE type = 'view'
                """)
    