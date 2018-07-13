# -*- coding: utf-8 -*-
__name__ = "Create a column to store the zip value"


def migrate(cr, v):
    """
    :param cr: Current cursor to the database
    :param v: version number
    """
    cr.execute("""ALTER TABLE purchase_order ADD COLUMN zip_temp varchar(30)""")
    
    cr.execute("""UPDATE purchase_order SET zip_temp=delivered_zip""")
