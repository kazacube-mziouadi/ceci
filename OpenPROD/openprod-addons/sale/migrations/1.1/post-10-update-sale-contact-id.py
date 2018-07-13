# -*- coding: utf-8 -*-
__name__ = "Retrieve the contact id of sales and partners to filled sale_contact_ids"


def migrate(cr, v):
    """
    :param cr: Current cursor to the database
    :param v: version number
    """
    cr.execute("""INSERT INTO sale_contact_id_partner_rel (partner_id, contact_id) 
                  SELECT id, sale_contact_id FROM res_partner WHERE sale_contact_id IS NOT NULL
                """)
    
    cr.execute("""INSERT INTO sale_contact_id_sale_rel (sale_order_id, contact_id) 
                  SELECT id, sale_contact_id FROM sale_order WHERE sale_contact_id IS NOT NULL
                """)
