# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
import time, datetime
import openerp.addons.decimal_precision as dp
from decimal import Decimal

class wo_declaration_main(models.TransientModel):
    """ 
        WorkOrder Declaration Main
    """
    _inherit = 'wo.declaration.main'
    
    @api.model
    def default_get(self, fields_list):
        res = super(wo_declaration_main, self).default_get(fields_list=fields_list)
        wo = self.env['mrp.workorder'].browse(self._context.get('active_id'))
        if wo.rm_draft_ids and not wo.reservation_ids:
            raise except_orm(_('Error'), _('It is necessary to first make the output of the materials.'))
        
        return res
    