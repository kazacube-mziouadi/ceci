# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp

class recalculate_label_wizard(models.TransientModel):
    """ 
    Recalculate label
    """
    _name = 'recalculate.label.wizard'
    _description = 'Recalculate label'
    _rec_name = 'product_compute'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    product_compute = fields.Boolean(default=False, help='Recalculate all labels of this product')
    
    @api.multi
    def recalculate_label(self):
        label_rs = self.env['stock.label'].browse(self.env.context['active_ids'])
        if self.product_compute:
            label_rs = self.env['stock.label'].search([('product_id', 'in', [l.product_id.id for l in label_rs])]) 
                
        return label_rs.refresh()