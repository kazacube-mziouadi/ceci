# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp

class stock_change_move_label_qty(models.TransientModel):
    """ 
    Partial picking 
    """
    _name = 'stock.change.move.label.qty'
    _description = 'Change label quantities'
    _rec_name = 'move_id'
    
    @api.one
    def dummy_inv(self):
        return True
    
    
    @api.one
    def dummy(self):
        self.move_label_ids = []
        return True
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    move_id = fields.Many2one('stock.move', string='Move', required=True, ondelete='cascade')
    is_variable_double_unit = fields.Boolean(default=False)
    move_label_ids = fields.One2many('stock.move.label', compute='dummy', inverse='dummy_inv')
    
    @api.model
    def default_get(self, fields_list):
        res = super(stock_change_move_label_qty, self).default_get(fields_list=fields_list)
        move_id = self.env.context.get('active_id')
        if move_id:
            res['move_id'] = move_id
            move_label_rs = self.env['stock.move.label'].search([('move_id', '=', move_id)])
            if move_label_rs:
                res['move_label_ids'] = move_label_rs.ids 
            
            res['is_variable_double_unit'] = self.env['stock.move'].browse([move_id]).read(['is_variable_double_unit'])[0]['is_variable_double_unit']
            
        return res
    
    
    @api.multi
    def validate_qtys(self):
        return True