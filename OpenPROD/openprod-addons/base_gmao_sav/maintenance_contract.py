# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from datetime import datetime, timedelta
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm, ValidationError, Warning
from openerp.addons.base_openprod.common import get_form_view, roundingUp
from dateutil.relativedelta import relativedelta


class maintenance_contract(models.Model):
    """ 
        Maintenance contract 
    """
    _inherit = 'maintenance.contract'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    #Maintenance
    is_maintenance_contract = fields.Boolean(string='Maintenance contract', default=False)
    maintenance_operation_ids = fields.Many2many('maintenance.operation', 'maintenance_contract_maintenance_operation_rel', 'maintenance_contract_id',  
                                                 'maintenance_operation_id', string='Maintenance operation', copy=False, domain="[('type', 'in', ('preventive', 'security'))]")
    park_ids = fields.Many2many('park', 'maintenance_contract_park_rel', 'maintenance_contract_id',
                                'park_id', string='Park', copy=False, domain="type == 'customer' and [('customer_id', '=', customer_id)] or type == 'supplier' and [('supplier_id', '=', supplier_id)]")