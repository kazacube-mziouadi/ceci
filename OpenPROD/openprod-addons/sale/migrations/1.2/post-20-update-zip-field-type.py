# -*- coding: utf-8 -*-
__name__ = "Filled the zip field with the stored value and delete the column"


def migrate(cr, v):
    """
    :param cr: Current cursor to the database
    :param v: version number
    """
    cr.execute("""UPDATE sale_order SET delivered_zip=zip_temp""")
    
    cr.execute("""ALTER TABLE sale_order DROP COLUMN zip_temp""")
