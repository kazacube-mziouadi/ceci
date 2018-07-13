# -*- coding: utf-8 -*-

from openerp import fields
from openerp.models import Model


class resource_timetracking(Model):
    _inherit = 'resource.timetracking'

    issue_id = fields.Many2one(
        comodel_name='tracker.issue', required=False,
        string='Issue', inverse_name='time_tracking_ids',
        ondelete='restrict'
    )

    def _timesheet_fields_list(self):
        list_ = super(resource_timetracking, self)._timesheet_fields_list()
        list_.append('issue_id')
        return list_
