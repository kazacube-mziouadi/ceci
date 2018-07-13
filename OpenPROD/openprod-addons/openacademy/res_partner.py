# -*- coding: utf-8 -*-
from openerp import models, api, fields

class res_partner(models.Model):
    _inherit = 'res.partner'
    
    is_instructor = fields.Boolean(string='Instructor', default=False)
    session_ids = fields.One2many('oa.session', 'instructor_id',  string='Sessions')