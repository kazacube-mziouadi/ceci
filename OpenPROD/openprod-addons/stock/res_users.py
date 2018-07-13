# -*- coding: utf-8 -*-
from openerp import models, _
from openerp.exceptions import ValidationError

class res_users(models.Model):
    _inherit = 'res.users'
    def get_warehouse_location(self, location_type, with_raise=True):
        if location_type == 'control':
            res = self.company_id.warehouse_id.control_location_id
        else:
            res = False
            
        if not res and with_raise:
            raise ValidationError(_('Control location not found. Set it in the warehouse'))
        
        return res