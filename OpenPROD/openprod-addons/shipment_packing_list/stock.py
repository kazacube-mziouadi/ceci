# -*- coding: utf-8 -*-
from openerp import models, api, fields
import openerp.addons.decimal_precision as dp


class stok_label(models.Model):
    _inherit = 'stock.label'
    #===========================================================================
    # COLUMNS
    #===========================================================================
    gross_weight = fields.Float(default=0.0, required=True)
    net_weight = fields.Float(default=0.0, required=True)
    length = fields.Float(digits=dp.get_precision('Stock Weight'), )
    width = fields.Float(digits=dp.get_precision('Stock Weight'), )
    height = fields.Float(digits=dp.get_precision('Stock Weight'), )
    volume = fields.Float('Volume (M3)', digits=dp.get_precision('Stock Weight'), )