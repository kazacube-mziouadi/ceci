# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp

class balancing_label_wizard(models.TransientModel):
    """ 
    Balancing label
    """
    _name = 'balancing.label.wizard'
    _description = 'Balancing label'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    location_id = fields.Many2one('stock.location', string='Location', required=False, ondelete='cascade', domain=[('usage', '=', 'internal')])
    line_ids = fields.One2many('balancing.label.line.wizard', 'wizard_id',  string='Lines')
    is_variable_double_unit = fields.Boolean(default=False)
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(balancing_label_wizard, self).default_get(fields_list=fields_list)
        labels = self.env['stock.label'].browse(self.env.context.get('active_ids', []))
        lines = []
        res['is_variable_double_unit'] = False
        for label in labels:
            if label.type == 'uc':
                lines.append((0, 0, {'label_id': label.id, 'is_variable_double_unit': label.is_variable_double_unit}))
                if not res['is_variable_double_unit'] and label.is_variable_double_unit:
                    res['is_variable_double_unit'] = True
                    
            else:
                for uc_label in label.uc_label_ids:
                    lines.append((0, 0, {'label_id': uc_label.id, 'is_variable_double_unit': label.is_variable_double_unit}))
                    if not res['is_variable_double_unit'] and uc_label.is_variable_double_unit:
                        res['is_variable_double_unit'] = True

        res['line_ids'] = lines
        return res
    
    
    @api.multi
    def balancing_label(self):
        for wizard in self:
            for line in wizard.line_ids:
                line.label_id.balancing(line.uom_qty, wizard.location_id, sec_qty=line.sec_uom_qty, is_variable_double_unit=wizard.is_variable_double_unit)
            
        return True
    


class balancing_label_line_wizard(models.TransientModel):
    """ 
    Balancing label
    """
    _name = 'balancing.label.line.wizard'
    _description = 'Balancing label line'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wizard_id = fields.Many2one('balancing.label.wizard', required=True, ondelete='cascade')
    label_id = fields.Many2one('stock.label', string='Label', required=True, ondelete='cascade', domain=[('type', '=', 'uc')])
    uom_qty = fields.Float(string='UoM qty', required=False, digits=dp.get_precision('Product quantity'), default=0.0)
    sec_uom_qty = fields.Float(string='Second UoM qty', required=False, digits=dp.get_precision('Product quantity'), default=0.0)
    is_variable_double_unit = fields.Boolean(default=False)