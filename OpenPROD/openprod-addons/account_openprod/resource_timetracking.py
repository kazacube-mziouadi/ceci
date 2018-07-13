# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError


class resource_timetracking(models.Model):
    _inherit = 'resource.timetracking'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    invoice_line_id = fields.Many2one('account.invoice.line', string='Invoice line', required=False, ondelete='set null')