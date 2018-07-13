# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp.tools import ustr
from openerp.exceptions import except_orm, ValidationError
from openerp.addons.base_openprod.common import roundingUp, rounding


class more_produce(models.TransientModel):
    """ 
        Wizard More Produce
    """
    _name = 'more.produce'
    _description = 'Wizard More Produce'
    _rec_name = 'wo_id'
    
    @api.model
    def default_get(self, fields_list):
        res = super(more_produce, self).default_get(fields_list=fields_list)
        wo_obj = self.env['mrp.workorder']
        #Fonction permettant de passer par défaut l'id de l'OT ouvert
        wo = wo_obj.browse(self._context.get('active_id'))
        vals = {
            'wo_id': wo.id,
            'uom_id': wo.uom_id.id,
        }
        res.update(vals)
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wo_id = fields.Many2one('mrp.workorder', string='WO', required=True, ondelete='cascade')
    line_rm_ids = fields.One2many('more.produce.line', 'produce_id',  string='Draft Raw Material', domain=[('type','=', 'rm')], copy=False)
    line_fp_ids = fields.One2many('more.produce.line', 'produce_id',  string='Draft Final Product', domain=[('type','=', 'fp')], copy=False)
    qty = fields.Float(string='Add Qty', default=1, required=True)
    uom_id = fields.Many2one('product.uom', string='UoM', related='wo_id.uom_id', readonly=True)
    

    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('qty')
    def _onchange_product_id(self):
        values_rm = []
        values_fp = []
        if self.qty:
            dict_product_rm, dict_product_fp = self.wo_id.return_product_qty_wo_rm_fp(wo_new_qty=self.qty)
            for product_rm in dict_product_rm:
                values_rm.append((0, 0, {'product_id': product_rm, 'qty': dict_product_rm[product_rm]['qty'], 'type': 'rm', 'no_modif': True,
                                         'uom_id': dict_product_rm[product_rm]['uom_id'], 'move_id': dict_product_rm[product_rm]['move_id']}))
            
            for product_fp in dict_product_fp:
                values_fp.append((0, 0, {'product_id': product_fp, 'qty': dict_product_fp[product_fp]['qty'], 'type': 'fp', 'no_modif': True,
                                         'uom_id': dict_product_fp[product_fp]['uom_id'], 'move_id': dict_product_fp[product_fp]['move_id']}))

        self.line_rm_ids = values_rm
        self.line_fp_ids = values_fp
    
    
    #===========================================================================
    # Boutons
    #===========================================================================
    @api.multi
    def validate(self):
        move_obj = self.env['stock.move']
        wo_resource_obj = self.env['mrp.wo.resource']
        location_obj = self.env['stock.location']
        for wiz in self:
            if wiz.qty <= 0:
                raise except_orm(_('Error'), _('Quantity must be higher than 0'))
            
            wo_resource_rcs = wo_resource_obj.search([('wo_id', '=', wiz.wo_id.id)], order='sequence asc', limit=1)
            if wo_resource_rcs:
                location_in = wo_resource_rcs.resource_id.location_id
            else:
                location_in = location_obj.search([('usage', '=', 'internal')], limit=1)
            
            if not location_in:
                raise except_orm(_('Error'), _('There is not location internal.'))
            
            location_out = location_obj.search([('usage', '=', 'production')], limit=1)
            if not location_out:
                raise except_orm(_('Error'), _('There is not location production.'))
            
            new_move_rm = self.env['stock.move']
            for line_rm in wiz.line_rm_ids:
                if line_rm.move_id:
                    move_qty_uom = line_rm.qty
                    uom_qty = line_rm.move_id.uom_qty or 1.0
                    move_qty_sec_uom = line_rm.move_id.sec_uom_qty * line_rm.qty / uom_qty
                    move_qty_uoi = line_rm.move_id.uoi_qty * line_rm.qty / uom_qty
                    history_rm_id = line_rm.move_id.history_id and line_rm.move_id.history_id.id or False
                    new_move_rm += line_rm.move_id.copy({'uom_qty': move_qty_uom,
                                                         'sec_uom_qty': move_qty_sec_uom,
                                                         'uoi_qty': move_qty_uoi,
                                                         'procurement_id': False,
                                                         'history_id': history_rm_id})
                
                else:
                    efficient_unit_qty = line_rm.qty / wiz.qty
                    new_move_rm += move_obj.create_move(line_rm.product_id, location_in.id, location_out.id, qty=line_rm.qty, 
                                           uom=line_rm.uom_id, other_data={'wo_incoming_id': wiz.wo_id.id, 
                                                                           'efficient_unit_qty': efficient_unit_qty,
                                                                           'origin': wiz.wo_id.name_get()[0][1],
                                                                           'is_forecast': wiz.wo_id.is_forecast})
            
            new_move_fp = self.env['stock.move']
            for line_fp in wiz.line_fp_ids:
                if line_fp.move_id:       
                    move_qty_uom = line_fp.qty
                    uom_qty = line_fp.move_id.uom_qty or 1.0
                    move_qty_sec_uom = line_fp.move_id.sec_uom_qty * line_fp.qty / uom_qty
                    move_qty_uoi = line_fp.move_id.uoi_qty * line_fp.qty / uom_qty
                    history_fp_id = line_fp.move_id.history_id and line_fp.move_id.history_id.id or False
                    new_move_fp += line_fp.move_id.copy({'uom_qty': move_qty_uom,
                                                         'sec_uom_qty': move_qty_sec_uom,
                                                         'uoi_qty': move_qty_uoi,
                                                         'procurement_id': False,
                                                         'history_id': history_fp_id})
                else:
                    efficient_unit_qty = line_fp.qty / wiz.qty
                    new_move_fp += move_obj.create_move(line_fp.product_id, location_out.id, location_in.id, qty=line_fp.qty, 
                                           uom=line_fp.uom_id, other_data={'wo_outgoing_id': wiz.wo_id.id, 
                                                                           'efficient_unit_qty': efficient_unit_qty,
                                                                           'origin': wiz.wo_id.name_get()[0][1],
                                                                           'is_forecast': wiz.wo_id.is_forecast})
            
            if new_move_rm:  
                wiz.wo_id.aggregate_move(new_move_rm, type='rm', waiting_state=True)
                
            if new_move_fp:
                wiz.wo_id.aggregate_move(new_move_fp, type='fp', waiting_state=True)
            
            quantity = wiz.wo_id.quantity + wiz.qty
            wiz.wo_id.write({'quantity': quantity})
            
        return True



class more_produce_line(models.TransientModel):
    """ 
        Wizard More Produce Line
    """
    _name = 'more.produce.line'
    _description = 'Wizard More Produce Line'
    _rec_name = 'product_id'
    
    @api.model
    def _type_get(self):
        return [
                ('rm', 'RM'),
                ('fp', 'FP'),
                       ]

    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    produce_id = fields.Many2one('more.produce', string='Produce', required=False, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    move_id = fields.Many2one('stock.move', string='Move', required=False, ondelete='cascade')
    qty = fields.Float(string='Qty', default=0.0, required=True)
    type = fields.Selection('_type_get', string='Type', default='rm')
    uom_id = fields.Many2one('product.uom', string='UoM', required=True, ondelete='cascade')
    no_modif = fields.Boolean(string='No modif', default=False)
    uom_categ_id = fields.Many2one('product.uom.category', string='UoM categ', required=False, ondelete='cascade')
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.uom_categ_id = self.product_id and self.product_id.uom_id and self.product_id.uom_id.id and self.product_id.uom_id.category_id and self.product_id.uom_id.category_id.id or False
        self.uom_id = self.product_id and self.product_id.uom_id and self.product_id.uom_id.id or False
        
        
        