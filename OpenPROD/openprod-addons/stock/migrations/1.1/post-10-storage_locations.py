# -*- coding: utf-8 -*-
__name__ = "Insert storage locations"


def migrate(cr, v):
    """
    :param cr: Current cursor to the database
    :param v: version number
    """
    cr.execute("""
    INSERT INTO
      product_storage_location (create_uid, create_date, product_id, warehouse_id, location_id)
     
      SELECT
        1, 
        now(),
        p.id,
        l.warehouse_id,
        l.id
      FROM
        product_product p
          JOIN stock_location l on p.storage_location_id = l.id
       
    """)
