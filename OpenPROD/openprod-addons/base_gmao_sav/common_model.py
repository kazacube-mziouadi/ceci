# -*- coding: utf-8 -*-
from openerp import models, fields, api

class note_openprod(models.Model):
    _inherit = 'note.openprod'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    park_id = fields.Many2one('park', string='Park', required=False, ondelete='cascade')


