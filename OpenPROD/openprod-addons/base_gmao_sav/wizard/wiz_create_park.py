# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
import time, datetime


class wiz_create_park(models.TransientModel):
    """ 
        Wiz manufacturing order for repair
    """
    _name = 'wiz.create.park'
    _description = 'Wiz manufacturing order for repair'
    
    
    @api.model
    def _type_get(self):
        return [
                ('intern', _('Intern')),
                ('external', _('External')),
                       ]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='string', size=256, required=False)
    label_ids = fields.Many2many('stock.label', 'wiz_create_park_label_rel', 'wiz_id', 'label_id',  string='List labels')
    type = fields.Selection('_type_get', string='Type', required=False)
    is_equipment = fields.Boolean(string='Equipment', default=False)
    
    
    #===========================================================================
    # Button
    #===========================================================================
    @api.multi
    def action_validation(self):  
        park_obj = self.env['park']
        for wiz in self:
            park_ids = []
            context = self.env.context.copy()
            context['default_type'] = wiz.type
            for label in wiz.label_ids:
                park_rcs = park_obj.create_park(label, wiz.type, is_equipment=wiz.is_equipment)
                park_ids.append(park_rcs.id)
        
        
            return {'name': _('Parks'),
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'park',
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'domain': [('id', '=', park_ids)],
                    'context': context,
                    'nodestroy': True,
                    }
            
        return {'type': 'ir.actions.act_window_close'}

