# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp

class close_label_wizard(models.TransientModel):
    """ 
    Close label
    """
    _name = 'close.label.wizard'
    _description = 'Close label'
    
    @api.one
    def close_label(self):
        label_rs = self.env['stock.label']
        for label in label_rs.browse(self.env.context['active_ids']):
            if label.type == 'uc':
                label_rs += label
                
            elif label.type == 'um':
                for uc_label in label.uc_label_ids:
                    label_rs += uc_label
            
        return label_rs.close() 