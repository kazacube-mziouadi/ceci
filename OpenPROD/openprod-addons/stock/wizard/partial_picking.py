# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp

class stock_partial_picking(models.TransientModel):
    """ 
    Partial picking 
    """
    _name = 'stock.partial.picking'
    _description = 'Partial picking'
    _rec_name = 'picking_id'
    #===========================================================================
    # COLUMNS
    #===========================================================================
    picking_id = fields.Many2one('stock.picking', string='Picking', required=True, ondelete='cascade')
    line_ids = fields.One2many('stock.partial.picking.line', 'partial_picking_id',  string='Partial picking')


    def get_order_qty(self, move):
        return move.initial_uom_qty
    

    def _prepare_line_ids(self, move, partial=False):
        manage_scrap = move.picking_id.manage_scrap
        uom_qty = 0.0
        sec_uom_qty = 0.0
        uoi_qty = 0.0
        is_variable_double_unit = move.is_variable_double_unit
        # Produit géré avec étiquettes
        if move.product_id.track_label:
            track_label = True
            # Double unité variable
            if is_variable_double_unit:
                for move_label in move.move_label_ids:
                    uom_qty += move_label.uom_qty
                    sec_uom_qty += move_label.sec_uom_qty
                
                if not move.move_label_ids and move.location_id.usage != 'internal' and move.location_dest_id.usage != 'internal':
                    uom_qty = move.uom_qty
                    sec_uom_qty = move.sec_uom_qty
                    
                if move.uom_id != move.product_id.uom_id:
                    uom_qty = self.env['product.uom']._compute_qty_obj(move.product_id.uom_id, uom_qty, move.uom_id, with_raise=True, with_round=False)
                    
                if move.sec_uom_id != move.product_id.sec_uom_id:
                    sec_uom_qty = self.env['product.uom']._compute_qty_obj(move.product_id.sec_uom_id, sec_uom_qty, move.sec_uom_id, with_raise=True, with_round=False)
                
                if sec_uom_qty:
                    qtys = move.product_id.get_qtys(sec_uom_qty, 
                                                    uom_id=move.product_id.uom_id, 
                                                    sec_uom_id=move.sec_uom_id, 
                                                    uoi_id=move.uoi_id, 
                                                    by_field='sec_uom', 
                                                    dual_unit=move.dual_unit, 
                                                    dual_unit_type=move.dual_unit_type, 
                                                    factor=move.factor, 
                                                    divisor=move.divisor, 
                                                    with_raise=True)
                    
                    uoi_qty = qtys.get('uoi_qty', uom_qty)

            # Double unité fixe ou simple unité
            else:
                for move_label in move.move_label_ids:
                    uom_qty += move_label.uom_qty
                
                if not move.move_label_ids and move.location_id.usage != 'internal' and move.location_dest_id.usage != 'internal':
                    uom_qty = move.uom_qty
                    
                if move.uom_id != move.product_id.uom_id:
                    uom_qty = self.env['product.uom']._compute_qty_obj(move.product_id.uom_id, uom_qty, move.uom_id, with_raise=True, with_round=False)
                
                if uom_qty:
                    qtys = move.product_id.get_qtys(uom_qty, 
                                                    uom_id=move.product_id.uom_id, 
                                                    sec_uom_id=move.sec_uom_id, 
                                                    uoi_id=move.uoi_id, 
                                                    by_field='uom', 
                                                    dual_unit=move.dual_unit, 
                                                    dual_unit_type=move.dual_unit_type, 
                                                    factor=move.factor, 
                                                    divisor=move.divisor, 
                                                    with_raise=True)
                    
                    sec_uom_qty = qtys.get('sec_uom_qty', uom_qty)
                    uoi_qty = qtys.get('uoi_qty', uom_qty)
                
        # Produit géré sans étiquettes
        else:
            track_label = False
            uom_qty = move.uom_qty
            sec_uom_qty = move.sec_uom_qty
            uoi_qty = move.uoi_qty
            
        res = {
            'product_id': move.product_id.id,
            'order_qty': self.get_order_qty(move),
            'initial_uom_qty': move.initial_uom_qty,
            'move_name': move.name,
            
            'uom_qty': uom_qty,
            'sec_uom_qty': sec_uom_qty,
            'uoi_qty': uoi_qty,
            
            'uom_id': move.uom_id.id,
            'sec_uom_id': move.sec_uom_id.id,
            'uoi_id': move.uoi_id.id,
            
            'move_id': move.id,
            'move_type': move.type,
            'is_partial': partial,
            'track_label': track_label,
            'manage_scrap': manage_scrap,
            'is_variable_double_unit': is_variable_double_unit,
        }
        return res
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(stock_partial_picking, self).default_get(fields_list=fields_list)
        picking_id = self.env.context.get('active_id')
        if picking_id:
            picking_rs = self.env['stock.picking'].browse(picking_id)
            res['picking_id'] = picking_id
            res['line_ids'] = [(0, 0, self._prepare_line_ids(move, picking_rs.is_partial)) for move in picking_rs.move_ids if move.state not in ('done', 'cancel')]
             
        return res
    
    
    def get_make_done(self):
        """
            Héritée dans shipment
        """
        return True
    
    
    @api.multi
    def do_partial(self):
        new_picking = self.picking_id.do_partial(self.line_ids, make_done=self.get_make_done())
        if new_picking:
            new_picking.get_form_view()
            
        return False
        
        
        
class stock_partial_picking_line(models.TransientModel):
    """ 
    Partial picking line
    """
    _name = 'stock.partial.picking.line'
    _description = 'Partial picking line'
    _rec_name = 'move_id'
    
    
    @api.model
    def _move_type_get(self):
        return [
            ('in', 'IN'),
            ('out', 'OUT'),
            ('int', 'INTERNAL'),
            ('ext', 'EXTERNAL'),
               ]
    
    @api.one   
    @api.depends('move_id')
    def _compute_display_name(self):
        self.move_name = self.move_id.id
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    partial_picking_id = fields.Many2one('stock.partial.picking', string='Partial picking', required=True, ondelete='cascade')
    move_id = fields.Many2one('stock.move', string='Move', required=True, ondelete='cascade')
    move_name = fields.Char(size=64, string='Name', compute='_compute_display_name')
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='cascade')
    manage_scrap = fields.Boolean(string='Manage rest', default=True)
    track_label = fields.Boolean(default=False)
    is_partial = fields.Boolean(string='Partial picking')
    is_variable_double_unit = fields.Boolean()
    move_type = fields.Selection('_move_type_get')
    # Qtys
    order_qty = fields.Float(string='Initial UoM qty', digits=dp.get_precision('Product quantity'))
    initial_uom_qty = fields.Float(string='Initial UoM qty', required=True, digits=dp.get_precision('Product quantity'))
    uom_qty = fields.Float(string='UoM qty', required=True, digits=dp.get_precision('Product quantity'))
    sec_uom_qty = fields.Float(string='Second UoM qty', digits=dp.get_precision('Product quantity'))
    uoi_qty = fields.Float(string='UoM qty', digits=dp.get_precision('Product quantity'))
    # UoM
    uom_id = fields.Many2one('product.uom', string='UoM', required=True, ondelete='cascade')
    sec_uom_id = fields.Many2one('product.uom', string='Second UoM', required=False, ondelete='cascade')
    uoi_id = fields.Many2one('product.uom', string='UoI', required=False, ondelete='cascade')
    
    
    def manage_scrap_compute(self, picking):
        return picking.manage_scrap
    
    
    def onchange_uom_qty(self, uom_qty):
        res = self.move_id.product_id.get_qtys(uom_qty, 
                                          uom_id=self.uom_id, 
                                          sec_uom_id=self.sec_uom_id, 
                                          uoi_id=self.uoi_id, 
                                          by_field='uom', 
                                          dual_unit=self.move_id.dual_unit, 
                                          dual_unit_type=self.move_id.dual_unit_type, 
                                          factor=self.move_id.factor, 
                                          divisor=self.move_id.divisor, 
                                          with_raise=True)
        res['manage_scrap'] = self.manage_scrap_compute(self.move_id.picking_id)
        return res
    
    
    @api.onchange('uom_qty', 'uom_id')
    def _onchange_uom_qty(self):
        """
            Au changement de la qty, changement des autres qty
        """
        res = self.onchange_uom_qty(self.uom_qty)
        for k, v in res.iteritems():
            self[k] = v
            
            
    @api.onchange('sec_uom_qty', 'sec_uom_id')
    def _onchange_sec_uom_qty(self):
        """
            Au changement de la qty, changement des autres qty
        """
        qtys = self.move_id.product_id.get_qtys(self.sec_uom_qty, 
                                 uom_id=self.uom_id, 
                                 sec_uom_id=self.sec_uom_id, 
                                 uoi_id=self.uoi_id, 
                                 by_field='sec_uom', 
                                 dual_unit=self.move_id.dual_unit, 
                                 dual_unit_type=self.move_id.dual_unit_type, 
                                 factor=self.move_id.factor, 
                                 divisor=self.move_id.divisor, 
                                 with_raise=True)
        
        for k, v in qtys.iteritems():
            self[k] = v
            
            
    @api.onchange('uoi_qty', 'uoi_id')
    def _onchange_uoi_qty(self):
        """
            Au changement de la qty, changement des autres qty
        """
        qtys = self.move_id.product_id.get_qtys(self.uoi_qty, 
                                 uom_id=self.uom_id, 
                                 sec_uom_id=self.sec_uom_id, 
                                 uoi_id=self.uoi_id, 
                                 by_field='uoi', 
                                 dual_unit=self.move_id.dual_unit, 
                                 dual_unit_type=self.move_id.dual_unit_type, 
                                 factor=self.move_id.factor, 
                                 divisor=self.move_id.divisor, 
                                 with_raise=True)
        
        for k, v in qtys.iteritems():
            self[k] = v
            
            
    @api.onchange('move_id')
    def _onchange_move_id(self):
        self.move_name = self.move_id.name
        
        
        
        