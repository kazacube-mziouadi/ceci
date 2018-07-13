# -*- coding: utf-8 -*-

from openerp import models, fields
class res_company(models.Model):
    _inherit = "res.company"
    
    reference_lang_id = fields.Many2one('res.lang', 'Reference lang')