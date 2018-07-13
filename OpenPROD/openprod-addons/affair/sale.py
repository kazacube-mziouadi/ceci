# -*- coding: utf-8 -*-
from openerp import models, api, fields


class sale_order_line(models.Model):
    _inherit = 'sale.order.line'

    #===========================================================================
    # COLUMNS
    #===========================================================================
    affair_id = fields.Many2one('affair', string='Affair', required=False, ondelete='restrict')