# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp

class stock_change_move_date(models.TransientModel):
    """ 
    Change move date 
    """
    _name = 'stock.change.move.date'
    _description = 'Change move date'
    _rec_name = 'move_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    move_id = fields.Many2one('stock.move', string='Move', required=False, ondelete='cascade')
    picking_id = fields.Many2one('stock.picking', string='Picking', required=False, ondelete='cascade')
    new_date = fields.Datetime(required=True)
    
    @api.model
    def default_get(self, fields_list):
        res = super(stock_change_move_date, self).default_get(fields_list=fields_list)
        active_id = self.env.context.get('active_id')
        active_model = self.env.context.get('active_model')
        if active_id:
            if active_model == 'stock.move':
                res['move_id'] = active_id
            elif active_model == 'stock.picking':
                res['picking_id'] = active_id
            
        return res
    
    
    @api.multi
    def change_move_date(self):
        for wiz in self:
            if wiz.picking_id:
                move_rs = wiz.picking_id.move_ids
#                 wiz.picking_id.write({''})
            elif wiz.move_id:
                move_rs = wiz.move_id
            else:
                move_rs = False
                
            if move_rs:
                move_rs.write({'date': wiz.new_date,
                               'date_expected': wiz.new_date,
                               'priority_date': wiz.new_date})
                
                move_label_rcs = self.env['stock.move.label']
                for move in move_rs:
                    if move.state == 'done':
                        move_label_rcs |= move.move_label_ids
                
                if move_label_rcs:
                    move_label_rcs.write({'done_date': wiz.new_date})
                
        return True