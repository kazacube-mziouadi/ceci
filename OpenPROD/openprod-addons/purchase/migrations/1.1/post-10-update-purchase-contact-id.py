# -*- coding: utf-8 -*-
__name__ = "Retrieve the contact id of purchases and partners to filled purchase_contact_ids"


def migrate(cr, v):
    """
    :param cr: Current cursor to the database
    :param v: version number
    """
    cr.execute("""INSERT INTO purchase_contact_id_partner_rel (partner_id, contact_id) 
                  SELECT id, purchase_contact_id FROM res_partner WHERE purchase_contact_id IS NOT NULL
                """)
    
    cr.execute("""INSERT INTO purchase_contact_id_purchase_rel (purchase_order_id, contact_id) 
                  SELECT id, purchase_contact_id FROM purchase_order WHERE purchase_contact_id IS NOT NULL
                """)
