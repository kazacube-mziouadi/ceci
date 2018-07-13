# -*- coding: utf-8 -*-
__name__ = "Week compute"


def migrate(cr, v):
    """
    :param cr: Current cursor to the database
    :param v: version number
    """
    cr.execute("""
        UPDATE stock_move SET week = extract(week FROM stock_move.date);
    """)
