# -*- coding: utf-8 -*-
__name__ = "Delete security groups to update their external ids"


def migrate(cr, v):
    """
    :param cr: Current cursor to the database
    :param v: version number
    """
    cr.execute("""Update mrp_wo_produce set product_id=wo.final_product_id from mrp_workorder as wo where wo_id = wo.id""")
