# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm


class update_move_customs_price(models.TransientModel):
    """ 
        Wizard to update customs prices moves from an out picking
    """
    _name = 'update.move.customs.price'
    _description = 'Wizard to update customs prices moves from an out picking'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    update_move_line_ids = fields.One2many('update.move.customs.price.line', 'update_move_id',  string='Lines to update')
    
    @api.model
    def default_get(self, fields_list):
        res = super(update_move_customs_price, self).default_get(fields_list=fields_list)
        picking_id = self.env.context.get('active_id')
        if picking_id:
            picking = self.env['stock.picking'].browse(picking_id)
            list_update_line = []
            for move in picking.move_ids:
                vals = {
                    'move_id': move.id,
                    'is_customs_price': move.is_customs_price,
                    'product_id': move.product_id and move.product_id.id or False,
                    'move_uom_category_id': move.uom_id and move.uom_id.category_id and move.uom_id.category_id.id or False,
                    'price': move.customs_price,
                    'currency_id': move.customs_currency_id and move.customs_currency_id.id or False,
                    'customs_unit_id': move.customs_unit_id and move.customs_unit_id.id or False
                }
                list_update_line.append((0, 0, vals))
                
            res.update({'update_move_line_ids': list_update_line})
            
        return res
    
    
    @api.multi
    def update_customs_price_move(self):
        """
            Fonction permettant de créer un nouveau partenaire
        """
        for wizard in self:
            for update_line in wizard.update_move_line_ids:
                if update_line.move_id.state != 'done':
                    currency_id = update_line.currency_id and update_line.currency_id.id or False
                    is_customs_price = update_line.is_customs_price
                    customs_unit_id = update_line.customs_unit_id and update_line.customs_unit_id.id or False
                    update_line.move_id.update_customs_price(update_line.price, currency_id, customs_unit_id, is_customs_price)
                else:
                    raise except_orm(_('Error'), _("You can't update a customs price of a done move"))
                
        return  {'type': 'ir.actions.act_window_close'}



class update_move_customs_price_line(models.TransientModel):
    """ 
        Lines to update customs prices moves from an out picking
    """
    _name = 'update.move.customs.price.line'
    _description = 'Lines to update customs prices moves from an out picking'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    move_id = fields.Many2one('stock.move', string='Move', required=False, ondelete='set null')
    move_uom_category_id = fields.Many2one('product.uom.category', string='Category', required=False, ondelete='set null', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='set null')
    price = fields.Float(string='Price', default=0.0, required=False)
    currency_id = fields.Many2one('res.currency', string='Currency', required=False, ondelete='set null')
    update_move_id = fields.Many2one('update.move.customs.price', string='Update move', required=False, ondelete='cascade')
    customs_unit_id = fields.Many2one('product.uom', string='Customs unit', required=False, ondelete='restrict')
    is_customs_price = fields.Boolean(string='Custome price', default=False, hemlp='Manage a specific price for customs')
