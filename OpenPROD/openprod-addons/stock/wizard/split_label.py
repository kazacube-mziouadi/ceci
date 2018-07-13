# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp

class split_label_choice_wizard(models.TransientModel):
    """ 
    Split label choice
    """
    _name = 'split.label.choice.wizard'
    _description = 'Split label choice'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    line_ids = fields.One2many('split.label.choice.line.wizard', 'wizard_id',  string='Lines')
    classic_split = fields.Boolean(default=False)
    equal_split = fields.Boolean(default=False)


    @api.onchange('classic_split')
    def _onchange_classic_split(self):
        if self.classic_split:
            self.equal_split = False


    @api.onchange('equal_split')
    def _onchange_equal_split(self):
        if self.equal_split:
            self.classic_split = False
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(split_label_choice_wizard, self).default_get(fields_list=fields_list)
        res['line_ids'] = [(0, 0,  {'label_id': x}) for x in self.env.context.get('active_ids', [])]
        return res
    
    
    @api.multi
    def validate_choice(self):
        if self.classic_split:
            res = self.env.ref('stock.act_stock_split_label').read()[0]
        elif self.equal_split:
            res = self.env.ref('stock.act_stock_equal_split_label').read()[0]
        else:
            res = False

        return res



class split_label_choice_line_wizard(models.TransientModel):
    """ 
    Split label choice line
    """
    _name = 'split.label.choice.line.wizard'
    _description = 'Split label choice line'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wizard_id = fields.Many2one('split.label.choice.wizard', string='Wizard', required=False, ondelete='cascade')
    label_id = fields.Many2one('stock.label', string='Label', required=False, ondelete='cascade')


    
class split_label_wizard(models.TransientModel):
    """ 
    Split label
    """
    _name = 'split.label.wizard'
    _description = 'Split label'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    choice_id = fields.Many2one('split.label.choice.wizard', string='Wizard', required=True, ondelete='cascade')
    remaining_qty = fields.Float(required=True, digits=dp.get_precision('Product quantity (UoM)'), default=0.0)
    sec_remaining_qty = fields.Float(required=False, digits=dp.get_precision('Product quantity (sec. UoM)'), default=0.0)
    uom_id = fields.Many2one('product.uom', string='UoM', required=False, ondelete='cascade', readonly=True)
    sec_uom_id = fields.Many2one('product.uom', string='Second UoM', required=False, ondelete='cascade', readonly=True)
    is_variable_double_unit = fields.Boolean(default=False)
    
        
    @api.model
    def default_get(self, fields_list):
        res = super(split_label_wizard, self).default_get(fields_list=fields_list)
        res['choice_id'] = self.env.context.get('active_id')
        choice_rs = self.env['split.label.choice.wizard'].browse(res['choice_id'])
        if choice_rs and choice_rs.line_ids:
            labels_data = choice_rs.line_ids[0].label_id.read(['is_variable_double_unit', 'uom_id', 'sec_uom_id'], load='_classic_write')[0]
            res['is_variable_double_unit'] = labels_data['is_variable_double_unit']
            res['uom_id'] = labels_data['uom_id']
            res['sec_uom_id'] = labels_data['sec_uom_id']
            
        return res
    
    
    @api.multi
    def split_label(self):
        label_rs = self.env['stock.label']
        for l in self.choice_id.line_ids:
            label_rs |= l.label_id
            
        return label_rs.split(self.remaining_qty, self.sec_remaining_qty, self.is_variable_double_unit)
    
    
    
class equal_split_label_wizard(models.TransientModel):
    """ 
    Equal plit label
    """
    _name = 'equal.split.label.wizard'
    _description = 'Equal split label'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    choice_id = fields.Many2one('split.label.choice.wizard', string='Wizard', required=True, ondelete='cascade')
    number = fields.Integer(string='New number of labels', default=2, required=True)
    is_variable_double_unit = fields.Boolean(default=False)

        
    @api.model
    def default_get(self, fields_list):
        res = super(equal_split_label_wizard, self).default_get(fields_list=fields_list)
        res['choice_id'] = self.env.context.get('active_id')
        choice_rs = self.env['split.label.choice.wizard'].browse(res['choice_id'])
        if choice_rs and choice_rs.line_ids:
            labels_data = choice_rs.line_ids[0].label_id.read(['is_variable_double_unit'], load='_classic_write')[0]
            res['is_variable_double_unit'] = labels_data['is_variable_double_unit']
            
        return res
    
    
    @api.multi
    def equal_split_label(self):
        label_rs = self.env['stock.label']
        for l in self.choice_id.line_ids:
            label_rs |= l.label_id

        return label_rs.equal_split(self.number, self.is_variable_double_unit)