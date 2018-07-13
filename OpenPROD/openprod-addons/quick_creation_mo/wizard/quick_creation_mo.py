# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
from decimal import Decimal

class quick_creation_mo(models.TransientModel):
    """ 
        Wizard quick creation of MO
    """
    _name = 'quick.creation.mo'
    _description = 'Wizard quick creation of MO'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    routing_id = fields.Many2one('mrp.routing', string='Routing', required=True, ondelete='cascade')
    uom_id = fields.Many2one('product.uom', string='UoM', required=True, ondelete='cascade')
    categ_uom_id = fields.Many2one('product.uom.category', string='UoM categ', required=True, ondelete='cascade')
    qty = fields.Float(string='Qty', default=0.0, required=True)
    requested_date = fields.Date(string='Requested date')
    label_rm_ids = fields.Many2many('stock.label', 'rel_quick_creation_mo_label_rm', 'wizard_id', 'label_id', string='Labels')
    product_rm_ids = fields.One2many('quick.creation.mo.product', 'qcm_id',  string='Raw material', domain=[('is_rm', '=', True)])
    label_fp_ids = fields.Many2many('stock.label', 'rel_quick_creation_mo_label_fp', 'wizard_id', 'label_id', string='Labels')
    product_fp_ids = fields.One2many('quick.creation.mo.product', 'qcm_id',  string='Final product', domain=[('is_rm', '=', False)])
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True, ondelete='cascade', default=lambda self: self.env.user.company_id.warehouse_id)
    
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
            Au changement du produit, changement l'uom
        """
        self.uom_id = self.product_id and self.product_id.uom_id.id or False
        self.categ_uom_id = self.product_id and self.product_id.uom_id.category_id.id or False
    
    
    #===========================================================================
    # Button
    #===========================================================================
    @api.multi
    def action_validation(self):  
        wo_obj = self.env['mrp.workorder']
        product_obj = self.env['product.product']
        location_obj = self.env['stock.location']
        move_obj = self.env['stock.move']
        wo_resource_obj = self.env['mrp.wo.resource']
        move_label_obj = self.env['stock.move.label']
        product_int_rcs = product_obj.search([('is_int', '=', True)], limit=1)
        for wiz in self:
            location_out = location_obj.search([('usage', '=', 'production'), ('warehouse_id', '=', wiz.warehouse_id.id)], limit=1)
            location_in = location_obj.search([('usage', '=', 'internal'), ('warehouse_id', '=', wiz.warehouse_id.id)], limit=1)
            # Création OF et Ots
            other_data_arg_mo = {
                                 'requested_date': wiz.requested_date,
                                 }
               
            no_wo = {'quantity': wiz.qty, 'uom': wiz.uom_id, 'product': wiz.product_id, 'routing_id': wiz.routing_id.id} 
            mo_rcs = wo_obj.add_operation_wo(wiz.routing_id.routing_line_ids.ids, True, False, False, False, no_wo=no_wo, other_data_arg=other_data_arg_mo)
            # Récupération du dernier et premier OT
            first_wo_rcs = wo_obj.search([('mo_id', '=', mo_rcs.id)], order='sequence asc', limit=1)
            last_wo_rcs = wo_obj.search([('mo_id', '=', mo_rcs.id)], order='sequence desc', limit=1)
            wo_resource_rcs = wo_resource_obj.search([('wo_id', '=', last_wo_rcs.id)], order='sequence asc', limit=1)
            if wo_resource_rcs:
                location_in_int = wo_resource_rcs.resource_id.location_id
            else:
                location_in_int = location_in
            
            # Si l'OF à plusieurs OTs, on crée les ints en PF sur tous les ots sauf le dernier 
            if first_wo_rcs.id != last_wo_rcs.id:
                wo_int_rcs = wo_obj.search([('mo_id', '=', mo_rcs.id), ('id', '!=', last_wo_rcs.id)])
                for wo_int in wo_int_rcs:
                    self.add_fp(wo_int, wo_int.quantity, product_int_rcs.uom_id, product_int_rcs, location_in_int.id, location_out.id, move_obj)
            
            # Création de matières à consommer
            if wiz.label_rm_ids:
                move_same_label_ids = move_label_obj.search([('move_id.state', 'not in', ['done', 'cancel']), 
                                                             ('move_id.picking_id', '!=', False), 
                                                             ('label_id', 'in', wiz.label_rm_ids.ids)], limit=1)
                if move_same_label_ids:
                    raise except_orm(_('Error'), _('UC label %s is already assign.')%(move_same_label_ids[0].label_id.name))
                
                for label_rm in wiz.label_rm_ids:
                    move_rm = self.add_rm(first_wo_rcs, label_rm.uom_qty, label_rm.uom_id, label_rm.product_id, label_rm.location_id.id, location_out.id, move_obj)
                    move_label_obj.create_move_label(label_rm, move_rs=move_rm)
            
            for product_rm in wiz.product_rm_ids:
                move_rm = self.add_rm(first_wo_rcs, product_rm.qty, product_rm.uom_id, product_rm.product_id, location_in.id, location_out.id, move_obj)
            
            # Créations des produits Finit
            move_pf_rcs = self.add_fp(last_wo_rcs, wiz.qty, wiz.uom_id, wiz.product_id, location_out.id, location_in.id, move_obj)
            if wiz.label_fp_ids:
                move_same_label_ids = move_label_obj.search([('move_id.state', 'not in', ['done', 'cancel']), 
                                                             ('move_id.picking_id', '!=', False), 
                                                             ('label_id', 'in', wiz.label_fp_ids.ids)], limit=1)
                if move_same_label_ids:
                    raise except_orm(_('Error'), _('UC label %s is already assign.')%(move_same_label_ids[0].label_id.name))
                
                for label_fp in wiz.label_fp_ids:
                    if label_fp.product_id.id != wiz.product_id.id:
                        move_fp = self.add_fp(last_wo_rcs, label_fp.uom_qty, label_fp.uom_id, label_fp.product_id, label_fp.location_id.id, location_in.id, move_obj)
                    
                    self.create_label_production(label_fp, last_wo_rcs)

            
            for product_fp in wiz.product_fp_ids:
                move_fp = self.add_fp(last_wo_rcs, product_fp.qty, product_fp.uom_id, product_fp.product_id, location_out.id, location_in.id, move_obj)
            
            wiz.function_entry_point(mo_rcs)
            
        return {'name': _('Manufacturing order'),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'mrp.manufacturingorder',
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'res_id': mo_rcs.id,
                    'nodestroy': True}
    
    
    def function_entry_point(self, mo):
        return True
    
    def add_rm(self, wo, quantity, uom, product, location_id, location_dest_id, move_obj):
        efficient_unit_qty = wo.quantity and float(quantity) / wo.quantity or float(quantity)
        move = move_obj.create_move(product, 
                                    location_id, 
                                    location_dest_id, 
                                    qty=float(quantity), 
                                    uom=uom, 
                                    other_data={'wo_incoming_id':wo.id, 
                                                'efficient_unit_qty':efficient_unit_qty, 
                                                'is_forecast': wo.is_forecast,}, 
                                    in_product_uom=True)
        
        return move


    def add_fp(self, wo, quantity, uom, product, location_id, location_dest_id, move_obj):
        efficient_unit_qty = wo.quantity and float(quantity)/wo.quantity or float(quantity)
        move = move_obj.create_move(product, 
                                    location_id,
                                    location_dest_id, 
                                    qty=float(quantity), 
                                    uom=uom, 
                                    other_data={'wo_outgoing_id':wo.id, 
                                                'efficient_unit_qty':efficient_unit_qty, 
                                                'is_forecast': wo.is_forecast,}, 
                                    in_product_uom=True)
        
        return move

    
    def create_label_production(self, label, last_wo_rcs):
        self.env['mrp.label.production'].create({
                                                    'wo_id': last_wo_rcs.id,
                                                    'label_id': label.id,
                                                })
        

class quick_creation_mo_product(models.TransientModel):
    """ 
        Wizard quick creation of MO product
    """
    _name = 'quick.creation.mo.product'
    _description = 'Wizard quick creation of MO product'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    is_rm = fields.Boolean(string='RM', default=False)
    qcm_id = fields.Many2one('quick.creation.mo', string='QCM', required=False, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    uom_id = fields.Many2one('product.uom', string='UoM', required=True, ondelete='cascade')
    categ_uom_id = fields.Many2one('product.uom.category', string='UoM categ', required=True, ondelete='cascade')
    qty = fields.Float(string='Qty', default=0.0, required=True)
    
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
            Au changement du produit, changement l'uom
        """
        self.uom_id = self.product_id and self.product_id.uom_id.id or False
        self.categ_uom_id = self.product_id and self.product_id.uom_id.category_id.id or False
        
        