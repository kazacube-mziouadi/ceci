# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
import time, datetime
import openerp.addons.decimal_precision as dp

class wiz_cost_simulation(models.TransientModel):
    """ 
        Wiz cost simulation
    """
    _name = 'wiz.cost.simulation'
    _description = 'Wiz cost simulation'
    _rec_name = 'product_id'
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(wiz_cost_simulation, self).default_get(fields_list=fields_list)
        bom_id = False
        routing_id = False
        product_id = False
        uom_id = False
        categ_uom_id = False
        if self._context.get('active_model') == 'mrp.bom':
            bom = self.env['mrp.bom'].browse(self._context.get('active_id'))
            product_id = bom and bom.product_id.id or False
            bom_id = bom.id
            routing = bom.routing_ids._routing_find(options=None) or bom.routing_ids and bom.routing_ids[0] or False
            routing_id = routing and routing.id or False
            uom_id = bom.uom_id.id
            categ_uom_id = bom.uom_id.category_id.id
        elif self._context.get('active_model') == 'product.product':
            product = self.env['product.product'].browse(self._context.get('active_id'))
            bom, routing = self.env['mrp.bom'].compute_bom_routing_for_product(product, with_raise=False)
            product_id = product.id
            bom_id = bom and bom.id or False
            routing_id = routing and routing.id or False
            uom_id = product.uom_id.id
            categ_uom_id = product.uom_id.category_id.id
            
        vals = {
            'routing_id': routing_id,
            'bom_id': bom_id,
            'product_id': product_id,
            'uom_id': uom_id,
            'categ_uom_id': categ_uom_id,
        }
        res.update(vals)
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    routing_id = fields.Many2one('mrp.routing', string='Routing', required=False, ondelete='cascade')
    bom_id = fields.Many2one('mrp.bom', string='BoM', required=False, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='cascade')
    uom_id = fields.Many2one('product.uom', string='UoM', required=False, ondelete='cascade')
    categ_uom_id = fields.Many2one('product.uom.category', string='Categ. UoM', required=False, ondelete='cascade')
    price_qty = fields.Float(string='Price qty', required=False, digits=dp.get_precision('Product quantity'))
    line_ids = fields.One2many('wiz.cost.simulation.line', 'cost_simu_id',  string='Lines')
    option_ids = fields.Many2many('mrp.option', 'wiz_cost_simulation_option_rel', 'wiz_id', 'option_id',   string='Options')
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('bom_id')
    def _onchange_uom_id(self):
        """
            Au changement de la nomenclature, changement de la catégorie de l'uom et de l'uom
        """
        if self.bom_id:
            self.price_qty = 0.0
            self.uom_id = self.bom_id.uom_id.id
            self.uom_category_id = self.bom_id.uom_id.category_id.id
        else:
            self.price_qty = 0.0
            self.uom_id = False
            self.uom_category_id = False
            
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
            Au changement du produit, changement l'uom
        """
        if self.product_id:
            res_onchange = self.env['mrp.manufacturingorder'].onchange_product_id(self.product_id,  None)
            self.uom_id = res_onchange['uom'] and res_onchange['uom'].id or False
            self.bom_id = res_onchange['bom'] and res_onchange['bom'].id or False
            self.routing_id = res_onchange['routing'] and res_onchange['routing'].id or False
            self.categ_uom_id = self.uom_id and self.uom_id.category_id.id or False
        else:
            self.uom_id = False
            self.bom_id = False
            self.routing_id = False
            self.categ_uom_id = False
    
    
    #===========================================================================
    # Boutons
    #===========================================================================
    @api.multi
    def action_validate(self):
        bom_obj = self.env['mrp.bom']
        uom_obj = self.env['product.uom']
        for wiz in self:
            if wiz.bom_id.uom_id == wiz.uom_id:
                price_qty = wiz.price_qty
            else:
                price_qty = uom_obj._compute_qty_obj(wiz.uom_id, wiz.price_qty, wiz.bom_id.uom_id)
            
            option_ids = wiz.option_ids and wiz.option_ids.ids or []
            price_unit_bom, price_total_bom, price_unit_routing, price_total_routing = bom_obj.compute_price_product_produce(price_qty, wiz.bom_id, wiz.routing_id, option_ids=option_ids)
            total_price = price_total_bom + price_total_routing
            total_unit_price = wiz.price_qty and total_price / wiz.price_qty or total_price
            self.env['wiz.cost.simulation.line'].create({'cost_simu_id': wiz.id,
                                                         'routing_id': wiz.routing_id.id,
                                                         'bom_id': wiz.bom_id.id,
                                                         'product_id': wiz.product_id.id,
                                                         'uom_id': wiz.uom_id.id,
                                                         'price_qty': wiz.price_qty,
                                                         'unit_price_bom': price_unit_bom,
                                                         'unit_price_routing': price_unit_routing,
                                                         'total_unit_price': total_unit_price,
                                                         'total_price': total_price,})
        
        return {'type': 'ir.actions.act_window_dialog_reload'}



class wiz_cost_simulation_line(models.TransientModel):
    """ 
        Wiz cost simulation line
    """
    _name = 'wiz.cost.simulation.line'
    _description = 'Wiz cost simulation line'
    _rec_name = 'product_id'   
    _order = 'product_id asc, bom_id asc, routing_id asc, price_qty asc' 
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    cost_simu_id = fields.Many2one('wiz.cost.simulation', string='Cost simu', required=False, ondelete='cascade')
    routing_id = fields.Many2one('mrp.routing', string='Routing', required=False, ondelete='cascade')
    bom_id = fields.Many2one('mrp.bom', string='BoM', required=False, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='cascade')
    uom_id = fields.Many2one('product.uom', string='UoM', required=False, ondelete='cascade')
    price_qty = fields.Float(string='Price qty', required=False, digits=dp.get_precision('Product quantity'))
    unit_price_bom = fields.Float(string='Unit price BoM', default=0.0, digits=dp.get_precision('Price technical'), required=False)
    unit_price_routing = fields.Float(string='Unit price Routing', default=0.0, digits=dp.get_precision('Price technical'), required=False)
    total_unit_price = fields.Float(string='Total unit price', default=0.0, digits=dp.get_precision('Price technical'), required=False)
    total_price = fields.Float(string='Total price', default=0.0, digits=dp.get_precision('Price technical'), required=False)
    
    
    
