# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
import time, datetime
import openerp.addons.decimal_precision as dp

class add_freight_picking(models.TransientModel):
    """ 
        Add freight picking
    """
    _name = 'add.freight.picking'
    _description = 'Add freight picking'
    _rec_name = 'total_price'
    
    @api.model
    def default_get(self, fields_list):
        res = super(add_freight_picking, self).default_get(fields_list=fields_list)
        res['picking_ids'] = [(6, 0,self._context.get('active_ids'))]
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    total_price = fields.Float(string='Total Price', default=0.0, required=True, digits=dp.get_precision('Account') )
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, ondelete='cascade', default=lambda self: self.env.user.company_id.currency_id)
    picking_ids = fields.Many2many('stock.picking', 'add_freight_picking_picking_rel', 'add_freight_picking_id', 'picking_id', string='Pickings')
    
    
    @api.multi
    def validate(self):
        for wiz in self:
            move_rcs = self.env['stock.move'].search([('picking_id', 'in', wiz.picking_ids.ids), ('state', '!=', 'cancel')])
            if move_rcs:
                freight_price = wiz.total_price / len(move_rcs)
                move_rcs.write({'freight_price': freight_price})
                 
        return {'type': 'ir.actions.act_window_close'}
    
    
    
    
    
    
    
    
    
    
    