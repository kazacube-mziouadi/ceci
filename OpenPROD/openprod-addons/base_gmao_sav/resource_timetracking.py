# -*- coding: utf-8 -*-
from openerp import models, fields, api


class resource_timetracking(models.Model):
    """ 
        Suivi des temps des ressources
    """
    _inherit = 'resource.timetracking'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    intervention_id = fields.Many2one('intervention', string='Intervention', required=False, ondelete='restrict')
    
    def _timesheet_fields_list(self):
        res = super(resource_timetracking, self)._timesheet_fields_list()
        res.append('intervention_id')
        return res