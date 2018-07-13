# -*- coding: utf-8 -*-

import os
import logging

from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import Warning

class ir_ui_view(models.Model):
    _inherit = 'ir.ui.view'
    
    def __init__(self, pool, cr):
        super(ir_ui_view, self).__init__(pool, cr)
        states_list = super(ir_ui_view, self)._columns['type'].selection
        if 'highstock' not in [key for key, value in states_list]:
            super(ir_ui_view, self)._columns['type'].selection.append(('highstock', _('HighStock')))
        
        
class ir_actions_act_window_view(models.Model):
    _inherit = 'ir.actions.act_window.view'
    
    def __init__(self, pool, cr):
        super(ir_actions_act_window_view, self).__init__(pool, cr)
        states_list = super(ir_actions_act_window_view, self)._columns['view_mode'].selection
        if 'highstock' not in [key for key, value in states_list]:
            super(ir_actions_act_window_view, self)._columns['view_mode'].selection.append(('highstock', _('HighStock')))
    
