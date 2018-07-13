# coding: utf-8
from openerp import models, api, fields

class calendar_loading(models.Model):
    _inherit = 'calendar.loading'
    
    capacity = fields.Float(related="calendar_line_id.real_hour", store=True)
    resource_category_id = fields.Many2one(related="wo_id.categ_first_resource_id", store=True)
    