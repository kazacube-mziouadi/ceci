# -*- coding: utf-8 -*-
__name__ = "Retrieve the contact id of invoices and partners to filled contact_ids"


def migrate(cr, v):
    """
    :param cr: Current cursor to the database
    :param v: version number
    """
    cr.execute("""INSERT INTO invoicing_contact_id_partner_rel (partner_id, contact_id) 
                  SELECT id, invoicing_contact_id FROM res_partner WHERE invoicing_contact_id IS NOT NULL
                """)
    
    cr.execute("""INSERT INTO invoicing_contact_id_invoice_rel (invoice_id, contact_id) 
                  SELECT id, contact_id FROM account_invoice WHERE contact_id IS NOT NULL
                """)
