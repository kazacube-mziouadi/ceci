# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import except_orm

class wizard_add_move_lot(models.TransientModel):
    """ 
    Assign lot
    """
    _name = 'wizard.add.move.lot'
    _description = 'Add move lot'
    _rec_name = 'move_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    move_id = fields.Many2one('stock.move', string='Move', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='cascade')
    line_ids = fields.One2many('wizard.add.move.lot.line', 'wizard_id')
    supplier_lot_number = fields.Char(size=64)
    move_type = fields.Char(size=8)
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(wizard_add_move_lot, self).default_get(fields_list=fields_list)
        move_rc = self.env['stock.move'].browse(self.env.context.get('active_id'))
        if move_rc:
            res['move_id'] = move_rc.id
            res['move_type'] = move_rc.type
            res['product_id'] = move_rc.product_id.id
            
        return res
    
    
    @api.multi
    def add_move_lot(self):
        move_lot_obj = self.env['stock.move.lot']
        for wizzard_rc in self:
            for lot_line_rc in wizzard_rc.line_ids:
                move_lot_obj.create({
                    'lot_id': lot_line_rc.lot_id.id,
                    'move_id': wizzard_rc.move_id.id,
                })
            
        return False
    
    
    
class wizard_add_move_lot_line(models.TransientModel):
    """ 
    Assign lot line
    """
    _name = 'wizard.add.move.lot.line'
    _description = 'Add move lot line'
    _rec_name = 'wizard_id'
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wizard_id = fields.Many2one('wizard.add.move.lot', string='Wizard', required=True, ondelete='cascade')
    lot_id = fields.Many2one('stock.lot', string='Lot', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='cascade')
    supplier_lot_number = fields.Char(size=64)