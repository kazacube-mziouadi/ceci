# -*- coding: utf-8 -*-
from openerp import models, fields, api


class res_company(models.Model):
    _inherit = 'res.company'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=False, ondelete='restrict')
