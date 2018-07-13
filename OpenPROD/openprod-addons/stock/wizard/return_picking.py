# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _

class stock_return_picking(models.TransientModel):
    """ 
    Return picking 
    """
    _name = 'stock.return.picking'
    _description = 'Return picking'
    _rec_name = 'picking_id'

    
    @api.model
    def _invoice_state_get(self):
        return [
                ('2binvoiced', _('To be refunded/invoiced')),
                ('none', _('No invoicing'))]
        
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    picking_id = fields.Many2one('stock.picking', string='Picking', required=True, ondelete='cascade')
    line_ids = fields.One2many('stock.return.picking.line', 'return_picking_id',  string='Return picking')
    invoice_state = fields.Selection('_invoice_state_get', string='Invoicing', required=True, default='2binvoiced')
    expected_return = fields.Boolean(default=False)
    expected_date = fields.Date()
    note = fields.Text()

    def _prepare_line_ids(self, move, dico_label=None):
        label_id = False
        if dico_label and move.id in dico_label:
            label_id = dico_label[move.id][0]
            origin_qty = dico_label[move.id][1]
        
        if label_id:
            move_qty = move.uom_qty or 1
            uom_qty = origin_qty
            sec_uom_qty = move.sec_uom_qty * (origin_qty / move_qty)
            uoi_qty = move.uoi_qty * (origin_qty / move_qty)
        else:
            uom_qty = move.uom_qty
            sec_uom_qty = move.sec_uom_qty
            uoi_qty = move.uoi_qty
        
        res = {
            'product_id': move.product_id.id,
            'uom_qty': uom_qty,
            'sec_uom_qty': sec_uom_qty,
            'uoi_qty': uoi_qty,
            'uom_id': move.uom_id.id,
            'sec_uom_id': move.sec_uom_id.id,
            'uoi_id': move.uoi_id.id,
            'move_id': move.id,
            'label_id': label_id,
        }
        return res
    
    
    @api.model
    def default_get(self, fields_list):
        move_obj = self.env['stock.move']
        res = super(stock_return_picking, self).default_get(fields_list=fields_list)
        dico_label = {}
        if self.env.context.get('active_model') == 'stock.picking':
            picking_id = self.env.context.get('active_id')
            if self.env.context.get('move_ids'):
                move_rcs = move_obj.browse(self.env.context.get('move_ids'))
            else:
                move_rcs = self.env['stock.picking'].browse(picking_id).move_ids
                
        elif self.env.context.get('picking_id'):
            picking_id = self.env.context.get('picking_id')
            if self.env.context.get('move_ids'):
                move_rcs = self.env['stock.move'].browse(self.env.context.get('move_ids'))
            elif self.env.context.get('move_and_label_rcs'):
                move_rcs = self.env['stock.move']
                for move_id, label_id, origin_qty in self.env.context.get('move_and_label_rcs'):
                    move_rcs += move_obj.browse(move_id)
                    dico_label[move_id] = [label_id, origin_qty]
            else:
                move_rcs = self.env['stock.picking'].browse(picking_id).move_ids
                
        else:
            picking_id = False
            move_rcs = False
        
        if picking_id:
            res['picking_id'] = picking_id
            if move_rcs:
                res['line_ids'] = [(0, 0, self._prepare_line_ids(move, dico_label)) for move in move_rcs if move.state == 'done']
             
        return res
    
    
    @api.multi
    def do_return(self):
        new_picking = self.picking_id.do_return(self.line_ids, self.expected_return, self.expected_date, self.note, self.invoice_state)
        if new_picking:
            return new_picking.get_form_view()
        
        return True
        
        
        
class stock_return_picking_line(models.TransientModel):
    """ 
    Return picking line
    """
    _name = 'stock.return.picking.line'
    _description = 'Return picking line'
    _rec_name = 'move_id'
    #===========================================================================
    # COLUMNS
    #===========================================================================
    return_picking_id = fields.Many2one('stock.return.picking', string='Return picking', required=True, ondelete='cascade')
    move_id = fields.Many2one('stock.move', string='Move', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='cascade')
    manage_scrap = fields.Boolean(string='Manage rest', default=False)
    label_id = fields.Many2one('stock.label', string='Label', required=False, ondelete='cascade')
    # Qtys
    uom_qty = fields.Float(string='UoM qty', required=True, digits=dp.get_precision('Product quantity'))
    sec_uom_qty = fields.Float(string='Second UoM qty', digits=dp.get_precision('Product quantity'))
    uoi_qty = fields.Float(string='UoM qty', digits=dp.get_precision('Product quantity'))
    # UoM
    uom_id = fields.Many2one('product.uom', string='UoM', required=True, ondelete='cascade')
    sec_uom_id = fields.Many2one('product.uom', string='Second UoM', required=False, ondelete='cascade')
    uoi_id = fields.Many2one('product.uom', string='UoI', required=False, ondelete='cascade')
    
    @api.onchange('uom_qty', 'uom_id')
    def _onchange_uom_qty(self):
        """
            Au changement de la qty, changement des autres qty
        """
        qtys = self.move_id.product_id.get_qtys(self.uom_qty, 
                                 uom_id=self.uom_id, 
                                 sec_uom_id=self.sec_uom_id, 
                                 uoi_id=self.uoi_id, 
                                 by_field='uom', 
                                 dual_unit=self.move_id.dual_unit, 
                                 dual_unit_type=self.move_id.dual_unit_type, 
                                 factor=self.move_id.factor, 
                                 divisor=self.move_id.divisor, 
                                 with_raise=True)
        
        for k, v in qtys.iteritems():
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