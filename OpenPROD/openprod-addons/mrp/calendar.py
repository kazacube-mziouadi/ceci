# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp.tools import ustr
from openerp.exceptions import except_orm, ValidationError
import time, datetime
import math


class calendar_loading(models.Model):
    """ 
        Calendar Loading 
    """
    _inherit = 'calendar.loading'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    resource_id = fields.Many2one('mrp.resource', string='Resource', required=False, ondelete='cascade')
    wo_id = fields.Many2one('mrp.workorder', string='WO', required=False, ondelete='cascade')
    mo_id = fields.Many2one('mrp.manufacturingorder', string='MO', required=False, ondelete='cascade')
    area_id = fields.Many2one('mrp.area', string='Area', required=False, ondelete='cascade')
    is_at_earlier = fields.Boolean(string='At earlier', default=False)
    
 