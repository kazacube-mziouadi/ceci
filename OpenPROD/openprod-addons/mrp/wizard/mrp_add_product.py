# -*- coding: utf-8 -*-
from openerp import models, api, fields
import openerp.addons.decimal_precision as dp

class create_rm(models.TransientModel):
    """ 
        Wizard qui permet de créer un mouvement dans les OTs dans les matières premières
    """
    _name = 'create.rm'
    _rec_name = 'product_id'
    _description = 'Wizard for creating a movement in the WO in the raw materials'
    
    @api.model
    def default_get(self, fields_list):
        res = super(create_rm, self).default_get(fields_list=fields_list)
        location_obj = self.env['stock.location']
        wo = self.env['mrp.workorder'].browse(self._context.get('active_id'))
        location_dest_rcs = location_obj.search([('usage', '=', 'production')], limit=1)
        location_id = wo.first_resource_id and wo.first_resource_id.location_id and wo.first_resource_id.location_id.id or False
        if not location_id:
            location_id = location_obj.search([('usage', '=', 'intern')], limit=1).id
            
        vals = {
            'wo_id': wo.id,
            'location_dest_id': location_dest_rcs.id,
            'location_id': location_id
        }
        res.update(vals)
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wo_id = fields.Many2one('mrp.workorder', string='Workorder', required=False, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    uom_id = fields.Many2one('product.uom', string='UoM', required=True, ondelete='cascade')
    quantity = fields.Float(string='Quantity', default=0.0, required=True, digits=dp.get_precision('Product quantity'))
    location_id = fields.Many2one('stock.location', string='Src location', required=True, select=True, ondelete='cascade')
    location_dest_id = fields.Many2one('stock.location', string='Dest location', required=True, select=True, ondelete='cascade')
    validate = fields.Boolean(default=True, help="Procurement will be validated if the box is checked")
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
            Au changement du produit, changement de l'uom
        """
        self.uom_id = self.product_id and self.product_id.uom_id or False

    #===========================================================================
    # Bouton
    #===========================================================================
    @api.multi
    def action_validate(self):
        """
            Fonction qui crée le mouvement dans l'OT de type matière première
        """
        for wiz in self:
            efficient_unit_qty = wiz.wo_id.quantity and wiz.quantity/wiz.wo_id.quantity or wiz.quantity
            move = self.env['stock.move'].create_move(wiz.product_id, wiz.location_id.id, wiz.location_dest_id.id, 
                                                      qty=wiz.quantity, uom=wiz.uom_id, other_data={'wo_incoming_id':wiz.wo_id.id, 
                                                                                                     'efficient_unit_qty':efficient_unit_qty, 
                                                                                                     'is_forecast': wiz.wo_id.is_forecast,}, in_product_uom=True)
            if wiz.validate and move:
                move.wkf_waiting()
            
        return {'type': 'ir.actions.act_window_close'}
    
    

class create_fp(models.TransientModel):
    """ 
        Wizard qui permet de créer un mouvement dans les OTs dans les produits finals
    """
    _name = 'create.fp'
    _rec_name = 'product_id'
    _description = 'Wizard for creating a movement in the Os in the final products'
   
    @api.model
    def default_get(self, fields_list):
        res = super(create_fp, self).default_get(fields_list=fields_list)
        location_obj = self.env['stock.location']
        wo = self.env['mrp.workorder'].browse(self._context.get('active_id'))
        location_rcs = location_obj.search([('usage', '=', 'production')], limit=1)
        location_dest_id = wo.first_resource_id and wo.first_resource_id.location_id and wo.first_resource_id.location_id.id or False
        if not location_dest_id:
            location_dest_id = location_obj.search([('usage', '=', 'intern')], limit=1).id
            
        vals = {
            'wo_id': wo.id,
            'location_dest_id': location_dest_id,
            'location_id': location_rcs.id
        }
        res.update(vals)
        return res
    

    #===========================================================================
    # COLUMNS
    #===========================================================================
    wo_id = fields.Many2one('mrp.workorder', string='Workorder', required=False, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    uom_id = fields.Many2one('product.uom', string='UoM', required=True, ondelete='cascade')
    quantity = fields.Float(string='Quantity', default=0.0, required=True, digits=dp.get_precision('Product quantity'))
    location_id = fields.Many2one('stock.location', string='Src location', required=True, select=True, ondelete='cascade')
    location_dest_id = fields.Many2one('stock.location', string='Dest location', required=True, select=True, ondelete='cascade')
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
            Au changement du produit, changement de l'uom
        """
        self.uom_id = self.product_id and self.product_id.uom_id or False
    
    #===========================================================================
    # Bouton
    #===========================================================================
    @api.multi
    def action_validate(self):
        """
            Fonction qui crée le mouvement dans l'OT de type produit final
        """
        efficient_unit_qty = self.wo_id.quantity and self.quantity/self.wo_id.quantity or self.quantity
        move = self.env['stock.move'].create_move(self.product_id, self.location_id.id, self.location_dest_id.id, qty=self.quantity, uom=self.uom_id, other_data={'wo_outgoing_id':self.wo_id.id, 'efficient_unit_qty':efficient_unit_qty, 'is_forecast': self.wo_id.is_forecast,}, in_product_uom=True)
#         move.wkf_waiting()
        return {'type': 'ir.actions.act_window_close'}