# -*- coding: utf-8 -*-
__name__ = "Provide dual unit fields"


def migrate(cr, v):
    """
    :param cr: Current cursor to the database
    :param v: version number
    """
    cr.execute("""
        UPDATE
          account_invoice_line ail
        SET
          dual_unit = p.dual_unit,
          dual_unit_type = p.dual_unit_type
        FROM
          product_product p
        WHERE
          ail.product_id = p.id
    """)