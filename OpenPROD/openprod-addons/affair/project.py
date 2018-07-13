# coding: utf-8
from openerp import models, fields

class project_phase(models.Model):
    _inherit = 'project.phase'
    _order = 'affair_id, sequence asc'
    
    
    affair_id = fields.Many2one('affair', string='Affair', required=False, ondelete='cascade')