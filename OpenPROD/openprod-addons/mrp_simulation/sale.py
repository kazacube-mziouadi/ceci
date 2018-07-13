# -*- coding: utf-8 -*-
from openerp import models, api, fields


class sale_order_line(models.Model):
    _inherit = 'sale.order.line'

    #===========================================================================
    # COLUMNS
    #===========================================================================
    simulation_id = fields.Many2one('mrp.simulation', string='Simulation', required=False, ondelete='restrict')