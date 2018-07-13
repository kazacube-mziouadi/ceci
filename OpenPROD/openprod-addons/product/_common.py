# -*- coding: utf-8 -*-

from openerp import tools
import math

def rounding(f, r):
    # TODO for trunk: log deprecation warning
    # _logger.warning("Deprecated rounding method, please use tools.float_round to round floats.")
    return tools.float_round(f, precision_rounding=r)


# TODO for trunk: add rounding method parameter to tools.float_round and use this method as hook
def ceiling(f, r):
    if not r:
        return f
       
    return math.ceil(f / r) * r
