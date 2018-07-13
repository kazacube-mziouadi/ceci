# -*- coding: utf-8 -*-
__name__ = "Modification des dates de lignes analytique pour qu'elles soient egale aux dates des factures"

def migrate(cr, v):
    """
    :param cr: Current cursor to the database
    :param v: version number
    """
    cr.execute("""
        UPDATE
          account_analytic_line aal
        SET
          date = ai.date_invoice
        FROM
          account_invoice ai
          JOIN account_invoice_line ail ON ai.id = ail.invoice_id
        WHERE
          aal.invoice_line_id = ail.id
    """)