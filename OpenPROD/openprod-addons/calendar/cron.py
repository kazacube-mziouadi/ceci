# -*- coding: utf-8 -*-
from openerp import models, fields, api, SUPERUSER_ID, exceptions
import openerp


class ir_cron(models.Model):
    _inherit = 'ir.cron'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    calendar_id = fields.Many2one('calendar.template', string='Calendar', required=False, ondelete='restrict')
    
    def get_nextcall_calendar(self, job_cr, job):
        if job['calendar_id']:
            registry = openerp.registry(job_cr.dbname)
            calendar = [job['calendar_id'], registry['calendar.line'], registry['calendar']]
        else:
            calendar = None
            
        return calendar
