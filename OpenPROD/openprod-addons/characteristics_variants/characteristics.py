# -*- coding: utf-8 -*-
from openerp import models, api, fields



class characteristic(models.Model):
    _inherit = 'characteristic'
    
    variant_value_id = fields.Many2one('variant.category.value', string='Variant', required=False, ondelete='cascade')