# -*- coding: utf-8 -*-
from openerp import models, fields, api, _


class resource_timetracking(models.Model):
    _inherit = 'resource.timetracking'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    phase_id = fields.Many2one('project.phase', string='Phase', required=False, ondelete='restrict')
    
    def _timesheet_fields_list(self):
        res = super(resource_timetracking, self)._timesheet_fields_list()
        res.append('phase_id')
        return res