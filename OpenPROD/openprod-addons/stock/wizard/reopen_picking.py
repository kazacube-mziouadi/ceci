# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp

class stock_reopen_picking(models.TransientModel):
    """ 
    Partial picking 
    """
    _name = 'stock.reopen.picking'
    _description = 'Reopen picking'
    _rec_name = 'picking_id'
    #===========================================================================
    # COLUMNS
    #===========================================================================
    picking_id = fields.Many2one('stock.picking', string='Picking', required=True, ondelete='cascade')
    keep_move_dates = fields.Boolean(string='Keep stock move done dates', default=False, help='If this field is checked, stock moves will keep their actual done dates when the picking will pass done again')
    
    @api.model
    def default_get(self, fields_list):
        res = super(stock_reopen_picking, self).default_get(fields_list=fields_list)
        picking_id = self.env.context.get('active_id')
        if picking_id:
            res['picking_id'] = picking_id
             
        return res
    
    
    @api.multi
    def reopen(self):
        for wizard in self:
            wizard.picking_id.reopen(wizard.keep_move_dates)
        
        return True