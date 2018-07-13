# -*- coding: utf-8 -*-
__name__ = "Allow to "


def migrate(cr, v):
    """
    :param cr: Current cursor to the database
    :param v: version number
    """
    cr.execute("""UPDATE 
                    wkf_activity 
                  SET 
                    can_not_be_deleted=false, 
                    required=false 
                  WHERE 
                    name='Generate invoice' AND
                    wkf_id IN (SELECT id FROM wkf WHERE osv='sale.order')""")