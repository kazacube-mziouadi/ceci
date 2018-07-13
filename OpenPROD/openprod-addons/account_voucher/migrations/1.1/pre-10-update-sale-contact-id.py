# -*- coding: utf-8 -*-
__name__ = "Modification de l'etat"


def migrate(cr, v):
    """
    :param cr: Current cursor to the database
    :param v: version number
    """
    cr.execute("""
        UPDATE 
          account_bank_statement_openprod
        SET
          state = 'done'
        WHERE
          state = 'generated_payment'  
    """)