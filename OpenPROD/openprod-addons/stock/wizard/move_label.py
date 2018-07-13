# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm

class move_label_wizard(models.TransientModel):
    """ 
    Move label
    """
    _name = 'move.label.wizard'
    _description = 'Move label'
    _rec_name = 'location_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    location_id = fields.Many2one('stock.location', string='Location', required=True, ondelete='cascade', domain=[('usage', '=', 'internal')])
    
    
    @api.multi
    def move_label(self):
        label_rs = self.env['stock.label']
        location_id = self.location_id.id
        for label in label_rs.browse(self.env.context['active_ids']):
            if label.type == 'uc' and label.location_id.id != location_id:
                label_rs += label
                
            elif label.type == 'um':
                location_id = False
                for uc_label in label.uc_label_ids:
                    if not location_id:
                        location_id = uc_label.location_id.id
                    
                    if location_id != uc_label.location_id.id:
                        raise  except_orm(_('Error'), _('All labels on the UM must be in the same location.'))
                        
                    label_rs += uc_label
                    
        return label_rs.move(self.location_id)