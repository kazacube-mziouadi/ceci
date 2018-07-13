# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from datetime import datetime, timedelta
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm, ValidationError, Warning
from dateutil.relativedelta import relativedelta


class park(models.Model):
    """ 
        Park 
    """
    _inherit = 'park'
    _description = 'Park'
    
    
    @api.multi
    def button_create_intervention(self):
        interv_id = super(park, self).button_create_intervention()
        data_pool = self.env['ir.model.data']
        for park_int in self:
            if park_int.type == 'external' and interv_id:
                action_model, action_id = data_pool.get_object_reference('sav', 'act_sav_intervention_id2')
                if action_model:
                    action_pool = self.env[action_model]
                    action = action_pool.browse(action_id).read()[0]
                    action['res_id'] = interv_id
                    res = action
                    return res
            
        return interv_id
