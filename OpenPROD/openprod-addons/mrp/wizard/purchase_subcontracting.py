# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
import openerp.addons.decimal_precision as dp
 
class purchase_subcontracting_rm(models.TransientModel):
    """ 
        Subcontracting purchase RM
    """
    _name = 'purchase.subcontracting.rm'
    _description = 'Subcontracting purchase RM'
    _rec_name = 'wo_id'
    
    @api.one
    @api.depends('wo_id')
    def _compute_wo(self):
        """
            Champ Fonction UoM et Produit final de L'ot
        """
        self.uom_id = self.wo_id.uom_id.id
        self.final_product_id = self.wo_id.final_product_id.id
        self.service_ids = [x.product_id.id for x in self.wo_id.consumed_service_ids if x.product_id]
        
        
    @api.model
    def default_get(self, fields_list):
        res = super(purchase_subcontracting_rm, self).default_get(fields_list=fields_list)
        wo = self.env['mrp.workorder'].browse(self._context.get('active_id'))
        res['location_id'] = wo.first_resource_id and wo.first_resource_id.location_id and wo.first_resource_id.location_id.id or False
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wo_id = fields.Many2one('mrp.workorder', string='Work Order', required=True, ondelete='cascade')
    uom_id = fields.Many2one('product.uom', string='UoM', compute='_compute_wo')
    final_product_id = fields.Many2one('product.product', string='Final Product', compute='_compute_wo')
    quantity = fields.Float(string='Quantity', default=0.0, required=False)
    line_ids = fields.One2many('purchase.subcontracting.line.wiz', 'psrm_id',  string='Lines')
    supplier_id = fields.Many2one('res.partner', string='Delivered Supplier for RM', required=False, ondelete='cascade')
    location_id = fields.Many2one('stock.location', string='Delivered Location for RM', required=False, ondelete='cascade')
    service_ids = fields.One2many('product.product', compute='_compute_wo')
    
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('wo_id', 'quantity')
    def _onchange_wo_id(self):
        """
            Récupération ligne
        """
        if self.wo_id:
            # Si pas de qté on recherche la qté restante à réceptionner
            if not self.quantity:
                quantity = self.wo_id.quantity
                dic_qty_wo_ordered_service = {}
                for pol_service in self.wo_id.wo_subc_pol_fp_ids:
                    if pol_service.id not in dic_qty_wo_ordered_service and pol_service.wo_qty and pol_service.purchase_state != 'cancel':
                        dic_qty_wo_ordered_service[pol_service.id] = pol_service.wo_qty
                
                if dic_qty_wo_ordered_service:
                    qty_wo_ordered_service = sum(dic_qty_wo_ordered_service.values())
                    quantity -= qty_wo_ordered_service
                    
                self.quantity = quantity
                
            list_val = []
            for rm in self.wo_id.rm_draft_ids:
                if rm.supply_method == 'buy':
                    type = 'direct'
                    no_order_qty = False
                else:
#                     type = 'stock'
                    type = 'direct'
                    no_order_qty = True
                    
                if rm.type_qty == 'variable':
                    need_qty = rm.efficient_unit_qty * self.quantity or self.quantity
                else:
                    need_qty = rm.uom_qty
                    
                vals = {
                    'wo_id': self.wo_id.id,
                    'rm_fp_draft_id': rm.id,
                    'product_id': rm.product_id.id,
                    'need_qty': need_qty,
                    'type': type,
                    'type_rm_fp': 'rm',
                    'wiz_qty': self.quantity,
                    'date': self.wo_id.planned_start_date,
                    'no_order_qty': no_order_qty,
                }
                list_val.append((0, 0, vals))
            
            
            if self.wo_id.prev_wo_ids:
                product_int_rcs = self.env['product.product'].search([('is_int', '=', True)], limit=1)
                    
                vals = {
                    'wo_id': self.wo_id.id,
                    'product_id': product_int_rcs.id,
                    'need_qty': self.quantity,
                    'onstock_qty': self.quantity,
                    'type': 'direct',
                    'type_rm_fp': 'rm',
                    'wiz_qty': self.quantity,
                    'date': self.wo_id.planned_start_date,
                    'no_order_qty': True,
                }
                list_val.append((0, 0, vals))
            
            if list_val:
                self.line_ids = list_val
    
    
    #===========================================================================
    # Boutons
    #===========================================================================    
    @api.multi
    def validate(self):
        """
            Bouton de validation pour la génération des achats de MP
        """
        for wiz in self:
            dico_create_po_subc_rm_fp = wiz.line_ids.create_purchase_subcontracting_rm_fp(wiz.supplier_id, wiz.location_id, wiz.wo_id, type_rm_fp='rm')
        
        return  {'type': 'ir.actions.act_window_close'} 
    
    
     
class purchase_subcontracting_fp(models.TransientModel):   
    """ 
        Subcontracting purchase FP
    """
    _name = 'purchase.subcontracting.fp'
    _description = 'Subcontracting purchase FP'
    _rec_name = 'wo_id'
    
    
    @api.model
    def _type_get(self):
        return [
                ('direct', 'Direct'),
                ('internal', 'Indirect'),
                       ]
    
    
    @api.model
    def _type2_get(self):
        return [
                ('internal', 'Indirect'),
                       ]
    
    
    @api.one
    @api.depends('wo_id', 'supplier_id')
    def _compute_wo(self):
        """
            Champ Fonction UoM et Produit final de L'ot
        """
        self.uom_id = self.wo_id.uom_id.id
        self.final_product_id = self.wo_id.final_product_id.id
        if not self.supplier_id:
            self.service_ids = [x.product_id.id for x in self.wo_id.consumed_service_ids if x.product_id]
        else:
            service_ids = [x.product_id.id for x in self.wo_id.consumed_service_ids if x.product_id]
            if service_ids:
                product_supp_rcs = self.env['product.supplierinfo'].search([('partner_id', '=', self.supplier_id.id), ('product_id', 'in', service_ids)])
                if product_supp_rcs:
                    product_ids = [x.product_id.id for x in product_supp_rcs if x.product_id]
                else:
                    product_ids = []
            else:
                product_ids = []   
            
            self.service_ids = product_ids
        
        # Permet de savoir si l'OT suivant est de sous-traitance et qu'il y a qu'un seul OT suivant
        no_direct_fp = True
        if self.wo_id.next_wo_ids and len(self.wo_id.next_wo_ids) == 1 and self.wo_id.next_wo_ids[0].is_subcontracting and self.wo_id.next_wo_ids[0].consumed_service_ids:
            no_direct_fp = False
            
        self.no_direct_fp = no_direct_fp
        
        
    @api.one
    @api.depends('supplier_id', 'wo_id', 'quantity')
    def _compute_service_ids(self):
        """
            Champ Fonction qui calcule les lignes de services
        """ 
        #Partie service
        wiz_service_ids, error_service = self._compute_value_service_ids()
        self.wiz_service_ids = wiz_service_ids
    
    
    @api.one
    @api.depends('wo_id', 'quantity', 'date')
    def _compute_fp_line_ids(self):
        """
            Champ Fonction qui calcule des produits finis
        """ 
        #Partie produit final
        list_val_fp = []
        for fp in self.wo_id.fp_draft_ids:
            if fp.type_qty == 'variable':
                need_qty = fp.efficient_unit_qty * self.quantity or self.quantity
            else:
                need_qty = fp.uom_qty
                
            vals = {
                'wo_id': self.wo_id.id,
                'rm_fp_draft_id': fp.id,
                'product_id': fp.product_id.id,
                'need_qty': need_qty,
                'type_rm_fp': 'fp',
                'wiz_qty': self.quantity,
                'date': self.date,
            }
            list_val_fp.append((0, 0, vals))
        
        self.fp_line_ids = list_val_fp
        
    
    @api.model
    def default_get(self, fields_list):
        res = super(purchase_subcontracting_fp, self).default_get(fields_list=fields_list)
        wo = self.env['mrp.workorder'].browse(self._context.get('active_id'))
        res['location_id'] = wo.first_resource_id and wo.first_resource_id.location_id and wo.first_resource_id.location_id.id or False
        res['date'] = wo.planned_end_date
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wo_id = fields.Many2one('mrp.workorder', string='Work Order', required=True, ondelete='cascade')
    uom_id = fields.Many2one('product.uom', string='UoM', compute='_compute_wo')
    final_product_id = fields.Many2one('product.product', string='Final Product', compute='_compute_wo')
    quantity = fields.Float(string='Quantity', default=0.0, required=False)
    supplier_id = fields.Many2one('res.partner', string='Delivered Supplier for RM', required=False, ondelete='cascade')
    location_id = fields.Many2one('stock.location', string='Delivered Location for RM', required=False, ondelete='cascade')
    fp_supplier_id = fields.Many2one('res.partner', string='Delivered Supplier for FP', required=False, ondelete='cascade')
    fp_location_id = fields.Many2one('stock.location', string='Delivered Location for FP', required=False, ondelete='cascade')
    service_ids = fields.One2many('product.product', compute='_compute_wo')
    type = fields.Selection('_type_get', default='internal', string='Type')
    type2 = fields.Selection('_type2_get', default='internal', string='Type')
    line_ids = fields.One2many('purchase.subcontracting.line.wiz', 'psfp_id', domain=[('type_rm_fp', '=', 'rm')], string='RM Lines')
    wiz_service_ids = fields.One2many('purchase.subcontracting.services.wiz', compute='_compute_service_ids',  string='Services') 
    fp_line_ids = fields.One2many('purchase.subcontracting.line.wiz', compute='_compute_fp_line_ids', string='FP Lines')
    date = fields.Date(string='Date')
    no_generate_rm = fields.Boolean(string='No generate RM', default=False)
    no_direct_fp = fields.Boolean(string='No direct FP', compute='_compute_wo')
    
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('wo_id', 'supplier_id', 'quantity', 'no_generate_rm', 'date')
    def _onchange_wiz_service_ids(self):
        """
            Au changement de la liste des services, on recrée la liste des services à acheter
        """
        if self.wo_id:
            # Si pas de qté on recherche la qté restante à réceptionner
            if not self.quantity:
                quantity = self.wo_id.quantity
                dic_qty_wo_ordered_service = {}
                for pol_service in self.wo_id.wo_subc_pol_fp_ids:
                    if pol_service.id not in dic_qty_wo_ordered_service and pol_service.wo_qty and pol_service.purchase_state != 'cancel':
                        dic_qty_wo_ordered_service[pol_service.id] = pol_service.wo_qty
                
                if dic_qty_wo_ordered_service:
                    qty_wo_ordered_service = sum(dic_qty_wo_ordered_service.values())
                    quantity -= qty_wo_ordered_service
                    
                self.quantity = quantity
            
        if self.wo_id and self.quantity:
            #Partie service
            wiz_service_ids, error_service = self._compute_value_service_ids()
            if error_service:
                raise except_orm(_('Error'), _('You must check FP services consumed on a et a single line.'))
            
            #Partie matière première
            list_val = []
            if not self.no_generate_rm:
                for rm in self.wo_id.rm_draft_ids:
                    if rm.supply_method == 'buy':
                        type = 'direct'
                        no_order_qty = False
                    else:
#                         type = 'stock'
                        type = 'direct'
                        no_order_qty = True
                    
                    if rm.type_qty == 'variable':
                        need_qty = rm.efficient_unit_qty * self.quantity or self.quantity
                    else:
                        need_qty = rm.uom_qty
                    
                    vals = {
                        'wo_id': self.wo_id.id,
                        'rm_fp_draft_id': rm.id,
                        'product_id': rm.product_id.id,
                        'need_qty': need_qty,
                        'type': type,
                        'type_rm_fp': 'rm',
                        'wiz_qty': self.quantity,
                        'date': self.wo_id.planned_start_date,
                        'no_order_qty': no_order_qty,
                    }
                    list_val.append((0, 0, vals))
                
                
                if self.wo_id.prev_wo_ids:
                    product_int_rcs = self.env['product.product'].search([('is_int', '=', True)], limit=1)
                        
                    vals = {
                        'wo_id': self.wo_id.id,
                        'product_id': product_int_rcs.id,
                        'need_qty': self.quantity,
                        'onstock_qty': self.quantity,
                        'type': 'direct',
                        'type_rm_fp': 'rm',
                        'wiz_qty': self.quantity,
                        'date': self.wo_id.planned_start_date,
                        'no_order_qty': True,
                    }
                    list_val.append((0, 0, vals))
             
            self.line_ids = list_val
        
        
        @api.onchange('no_direct_fp')
        def _onchange_no_direct_fp(self):
            """
                On change pour savoir si l'OT suivant est seul et qu'il est de ST
            """
            if self.no_direct_fp:
                self.fp_supplier_id = False
                self.fp_location_id = False
        
        
        @api.onchange('type2')
        def _onchange_type2(self):
            """
                On change type2 visible que si no_direct_fp = True car du coup laisse que la possibilité de livrer en indirect
            """
            if self.no_direct_fp and self.type2:
                self.type = 'internal'
    
    
    #===========================================================================
    # Fonctions
    #===========================================================================
    def _compute_value_service_ids(self):
        """
            Champ Fonction qui calcule les lignes de services
        """ 
        #Partie service
        is_fp = False
        error = False
        wiz_service_ids = []
        suppinfo_obj = self.env['product.supplierinfo']
        pssw_obj = self.env['purchase.subcontracting.services.wiz']
        for service in self.wo_id.consumed_service_ids:
            # Test si le champ is_fp plusieur fois cochés dans les lignes de services, si oui raise
            if service.is_fp and not is_fp:
                is_fp = True
            elif service.is_fp and is_fp:
                raise except_orm(_('Error'), _('You must check FP services consumed on a et a single line.'))
    
            service_val = False
            if self.supplier_id:
                supp_rcs = suppinfo_obj.search([('partner_id', '=', self.supplier_id.id), ('product_id', '=', service.product_id.id)])
                if supp_rcs:
                    service_val = True
            else:
                service_val = True
                
            if service_val:
                if service.type == 'fixed':
                    quantity = service.quantity
                    price_total = service.price_total
                else:
                    quantity = service.quantity * self.quantity
                    price_total = pssw_obj.compute_price_total(quantity, service.uom_id, service.product_id, supplier_rcs=self.supplier_id, fp_supplier=self.fp_supplier_id, wo=self.wo_id)
                
                vals = {
                        'wo_id': self.wo_id.id,
                        'consum_service_id': service.id,
                        'product_id': service.product_id.id,
                        'quantity': quantity,
                        'price_total': price_total,
                        'uom_id': service.uom_id.id,
                } 
                wiz_service_ids.append((0, 0, vals))
        
        if is_fp == False and self.wo_id.consumed_service_ids:
            error = True
        
        return wiz_service_ids, error
    
    
    #===========================================================================
    # Bouton
    #===========================================================================
    @api.multi
    def validate(self):
        """
            Bouton de validation pour la génération des achats de Service
        """
        for wiz in self:
            quantity = wiz.wo_id.quantity
            dic_qty_wo_ordered_service = {}
            for pol_service in wiz.wo_id.wo_subc_pol_fp_ids:
                if pol_service.id not in dic_qty_wo_ordered_service and pol_service.wo_qty and pol_service.purchase_state != 'cancel':
                    dic_qty_wo_ordered_service[pol_service.id] = pol_service.wo_qty
            
            if dic_qty_wo_ordered_service:
                qty_wo_ordered_service = sum(dic_qty_wo_ordered_service.values())
                quantity -= qty_wo_ordered_service
            
            quantity -=  wiz.quantity
            if quantity < 0:
                raise except_orm(_('Error'), _('We can not produce more and subcontracting.'))
            
            # Gestion de la MP
            dico_create_po_subc_rm_fp = wiz.line_ids.create_purchase_subcontracting_rm_fp(wiz.supplier_id, wiz.location_id, wiz.wo_id, type_rm_fp='fp')
            # Gestion du Service
            other_data = None
            # Si direct changement de l'emplacement et de l'adresse de récepetion (direct chez le fournisseur)
            if wiz.type == 'direct':
                other_data = {
                    'delivered_supplier_id': wiz.fp_supplier_id.id,
                    'location_id': wiz.fp_location_id.id,
                }
            
            po_rcs = self.env['purchase.order'].create_purchase(supplier=wiz.supplier_id, po_line=None, date=False, other_data=other_data, first_qty=False, forced_qty=False)
            wiz.wiz_service_ids.create_service_subcontracting(wiz, po_rcs, wiz.type)
        
        return  {'type': 'ir.actions.act_window_close'} 
    
    

class purchase_subcontracting_line_wiz(models.TransientModel):
    """ 
        Subcontracting Purchase Line Wiz
    """
    _name = 'purchase.subcontracting.line.wiz'
    _description = 'Subcontracting Purchase Line Wiz'
    _rec_name = 'product_id'

     
    @api.model
    def _type_get(self):
        return [
                ('direct', 'Direct'),
                ('indirect', 'Indirect'),
#                 ('stock', 'Stock'),
                       ]
    
    
    @api.model
    def _type_rm_fp_get(self):
        return [
                ('fp', 'FP'),
                ('rm', 'RM'),
                        ]
     
     
    @api.one
    @api.depends('rm_fp_draft_id', 'rm_fp_draft_id.uom_qty', 'product_id')
    def _compute_qty(self):
        """
            Chanp fonction pour la quantité commandée, restante, prise sur stock, du besoin et l'UoM
        """
        uom_obj = self.env['product.uom']
        move_obj = self.env['stock.move']
        pol_obj = self.env['purchase.order.line']
        pol_rm_rcs = pol_obj.search([('wo_rm_subcontracting_id', '=', self.wo_id.id), 
                                       ('product_id', '=', self.product_id.id), 
                                       ('purchase_state', 'in', ('draft', 'waiting'))])
        
        move_rm_rcs = move_obj.search([('wo_rm_subcontracting_id', '=', self.wo_id.id), 
                                       ('product_id', '=', self.product_id.id), 
                                       ('state', '!=', 'cancel'),
                                       '|', ('type_subcontracting', '!=', 'indirect'), 
                                       '&', ('type_subcontracting', '=', 'indirect'), ('type', '=', 'out')])
        ordered_qty = 0
        taken_fromstock_qty = 0
        out_qty = 0
        soon_out_qty = 0
        # Calcule de la qté commandée, prise sur le stock et envoyé
        for pol_rm in pol_rm_rcs:
            qty = uom_obj._compute_qty_obj(pol_rm.uom_id, pol_rm.uom_qty, self.rm_fp_draft_id.uom_id, with_raise=True, with_round=False)
            soon_out_qty += qty
            if pol_rm.type_subcontracting == 'stock':
                taken_fromstock_qty += qty
            elif pol_rm.type_subcontracting == 'indirect':
                ordered_qty += qty
            else:
                ordered_qty += qty
            
            
        for move_rm in move_rm_rcs:
            qty = uom_obj._compute_qty_obj(move_rm.uom_id, move_rm.uom_qty, self.rm_fp_draft_id.uom_id, with_raise=True, with_round=False)
            out_qty += qty
            if move_rm.type_subcontracting == 'stock':
                taken_fromstock_qty += qty
            elif move_rm.type_subcontracting == 'indirect':
                ordered_qty += qty
            else:
                ordered_qty += qty   
            
        # Si c'est le dernier OT de l'OF, déclaration du produit final
# TODO THOMAS: commenté car non utilisé. À supprimer ulterieurement
#         last_wo = False
#         if not self.wo_id.next_wo_ids:
#             last_wo = True
#         else:
#             last_wo = True
#             for next_wo in self.wo_id.next_wo_ids:
#                 if next_wo.mo_id.id == self.wo_id.mo_id.id:
#                     last_wo = False
#                     break
#         
#         if last_wo:
#             product_fp_id = self.wo_id.final_product_id.id
#         else:
#             product_fp_id = False
#             for fp in self.wo_id.fp_draft_ids:
#                 if fp.product_id.is_int:
#                     product_fp_id = fp.product_id.id
                    
        # Calcule de la qté déjà utilisée et la déduction des qtés déjà achetées mais non utilisées
        pol_fp_rcs = pol_obj.search([('wo_fp_subcontracting_id', '=', self.wo_id.id)])
        qty_product_final_use = 0
        po_ids = []
        for pol_fp in pol_fp_rcs:
            if pol_fp.purchase_order_id.id not in po_ids and pol_fp.purchase_state != 'cancel':
                po_ids.append(pol_fp.purchase_order_id.id)
                qty_product_final_use += pol_fp.wo_qty
        
        wo_in_use_qty = self.rm_fp_draft_id.efficient_unit_qty * qty_product_final_use
        # Initialisation des champs fonctions
        self.virtual_stock = self.product_id.virtual_stock
        self.wo_total_ordered_qty = ordered_qty
        self.taken_fromstock_qty = taken_fromstock_qty
        self.wo_total_remaining_qty = (self.rm_fp_draft_id.efficient_unit_qty*self.wo_id.quantity) - ordered_qty - taken_fromstock_qty
        if self.rm_fp_draft_id.type_qty == 'variable':
            need_qty = self.rm_fp_draft_id.efficient_unit_qty * self.wiz_qty or self.wiz_qty  
        else:
            need_qty = self.rm_fp_draft_id.uom_qty
            
        self.need_qty = need_qty
        self.uom_id = self.rm_fp_draft_id and self.rm_fp_draft_id.uom_id.id or self.product_id.uom_id.id                 
        self.wo_delivred_qty = out_qty
        self.wo_soon_delivred_qty = soon_out_qty
        self.forecast_delivred_qty = self.wo_delivred_qty + self.wo_soon_delivred_qty
        self.wo_in_use_qty = wo_in_use_qty
        if self.need_qty < ((self.wo_delivred_qty+self.wo_soon_delivred_qty)-self.wo_in_use_qty):
            self.wo_remaining_need_qty = 0
        else:
            self.wo_remaining_need_qty = self.need_qty - ((self.wo_delivred_qty+self.wo_soon_delivred_qty) - self.wo_in_use_qty)
        
        # Calcule des quantités libres dans l'emplacement de st
        warehouse_rs = self.wo_id.first_resource_id and self.wo_id.first_resource_id.location_id.warehouse_id or False
        if warehouse_rs:
            self.release_virtual_qty, self.release_qty = self.product_id.get_available_stock(return_real_stock=True, warehouse_id=warehouse_rs.id)
        else:
            self.release_qty = 0.0
            self.release_virtual_qty = 0.0
                         
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wo_id = fields.Many2one('mrp.workorder', string='Wo', required=False, ondelete='cascade')
    rm_fp_draft_id = fields.Many2one('stock.move', string='RM Draft', required=False, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='cascade')
    date = fields.Date(string='Expected Date')
    wiz_qty = fields.Float(string='Wiz Qty')
    uom_id = fields.Many2one('product.uom', string='UoM', compute='_compute_qty')
    need_qty = fields.Float(string='Need Qty', compute='_compute_qty')
    wo_total_ordered_qty = fields.Float(string='Wo Total Ordered Qty', compute='_compute_qty')
    taken_fromstock_qty = fields.Float(string='Total Taken from stock Qty', compute='_compute_qty')
    wo_total_remaining_qty = fields.Float(string='Wo Total Remaining Qty', compute='_compute_qty')
    wo_delivred_qty = fields.Float(string='Delivered Qty', compute='_compute_qty')
    wo_soon_delivred_qty = fields.Float(string='Soon Delivered Qty', compute='_compute_qty')
    forecast_delivred_qty = fields.Float(string='Forecast Delivered Qty', compute='_compute_qty')
    wo_in_use_qty = fields.Float(string='Used Qty', compute='_compute_qty')
    wo_remaining_need_qty = fields.Float(string='Remaining Need Qty', compute='_compute_qty')
    virtual_stock = fields.Float(string='Virtual Stock', compute='_compute_qty')
    release_qty = fields.Float(string='Real stock (SC)', compute='_compute_qty', help='Real stock level of subcontractor\'s warehouse')
    release_virtual_qty = fields.Float(string='Virtual stock (SC)', compute='_compute_qty', help='Virtual stock level of subcontractor\'s warehouse')
    order_qty = fields.Float(string='Order Qty', required=False)
    onstock_qty = fields.Float(string='On stock Qty', required=False)
    supplier_id = fields.Many2one('res.partner', string='Supplier', required=False, ondelete='cascade')
    type = fields.Selection('_type_get', default='direct', string='Type')
    type_rm_fp = fields.Selection('_type_rm_fp_get', default='', string='Type rm/fp')
    psrm_id = fields.Many2one('purchase.subcontracting.rm', string='Purchase subcontraction RM', required=False, ondelete='cascade')
    psfp_id = fields.Many2one('purchase.subcontracting.fp', string='Purchase subcontraction FP', required=False, ondelete='cascade')
    no_order_qty = fields.Boolean(string='No order qty', default=False) 
    
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('rm_fp_draft_id', 'type', 'order_qty')
    def _onchange_type(self):
        """
            Au changement le mouvement et le type car si le mouvement est à produire alors type ne peut être que stock
        """
        if self.rm_fp_draft_id and self.rm_fp_draft_id.supply_method == 'produce':
#             self.type = 'stock'
            self.order_qty = 0.0
            self.no_order_qty = True
        else:
            self.no_order_qty = False
        
#         if self.type == 'stock':
#             self.no_order_qty = True
#             self.order_qty = 0.0
            
    
    #===========================================================================
    # FONCTION
    #===========================================================================
    def create_purchase_subcontracting_wo(self, dico_value, po_obj, pol_obj, move_obj, picking_obj, type, type_out_in, 
                                          purchase_rcs, supplier_rcs, location_rcs, out_picking_rcs, move_rcs, wo_rcs):
            """
                Creation d'un achat et de ligne d'achat ou/et des Bon de livraisons Externes
                :param dico_value: Un dico avec comme clé le recordset du partenaire et comme valeur une liste de recordset de l'objet purchase.subcontracting.line.wiz
                :type dico_value: dico
                :param type: Pour indiquer si c'est de type indirect, direct, stock
                :type type: selection
                :param type_out_in: Pour indiquer si c'est de type in ou out pour savoir si c'est le wizard d'achat MP ST (in) ou l'achat de service (out)
                :type type_out_in: selection
                :param purchase_rcs: Liste de recordset des achats créées
                :type purchase_rcs: Liste de recordset
            """
            transfer_obj = self.env['stock.transfer.request']
            location_obj = self.env['stock.location']
            for supplier_val in dico_value:
                other_data = None
                # Si direct changement de l'emplacement et de l'adresse de récepetion (direct chez le fournisseur)
                if type_out_in == 'out':
                    other_data = {
                        'delivered_supplier_id': supplier_rcs.id,
                        'location_id': location_rcs.id,
                    }
                    if wo_rcs.sale_line_id and wo_rcs.sale_line_id.name_get():
                        other_data['source_document'] = wo_rcs.sale_line_id.name_get()[0][-1]
                    else:
                        other_data['source_document'] = wo_rcs.name_get()[0][-1]
                
                if type != 'stock':
                    po_rcs = po_obj.create_purchase(supplier=supplier_val, po_line=None, date=False, other_data=other_data, first_qty=False, forced_qty=False)
                    purchase_rcs += po_rcs
                else:
                    po_rcs = False
                
                if type in ('indirect', 'stock') and not out_picking_rcs:
                    # Création du picking pour le mouvement de stock à sous traitant
                    out_picking_rcs = picking_obj.create_picking('out', partner=supplier_rcs, product_qty_uom=None, date=False, other_data={'invoice_postage': 'never', 
                                                                                                                                        'invoice_state': 'none', 
                                                                                                                                        'origin': wo_rcs.name_get()[0][-1]})

                for line in dico_value[supplier_val]:
                    need_date = line.date or fields.Date.today()
                    if line.order_qty or line.onstock_qty: # or line.onstock_subc_qty:
                        pol_rcs = False
                        if type != 'stock':
                            if type == 'internal':
                                type_pol = 'indirect'
                            else:
                                type_pol = type
                            
                            if line.order_qty:
                                subcontracting = _('Subcontracting')
                                source = '%s: %s'%(subcontracting, line.wo_id.name_get()[0][1])
                                pol_rcs = pol_obj.create_purchase_order_line(purchase=po_rcs, product=line.product_id, 
                                                                             values={'expected_date': line.date, 'uom_qty': line.order_qty, 'need_date': line.wo_id.planned_start_date,
                                                                                     'source': source, 'wo_rm_subcontracting_id': line.wo_id.id, 'uom_id': line.uom_id.id, 'type_subcontracting': type_pol,
                                                                                     'subc_origin_move_id': line.rm_fp_draft_id.id}, 
                                                                             first_qty='uom_qty', forced_qty=True)
                            if line.onstock_qty:
                                if not out_picking_rcs:
                                    # Création du picking pour le mouvement de stock à sous traitant
                                    out_picking_rcs = picking_obj.create_picking('out', partner=supplier_rcs, product_qty_uom=None, date=False, 
                                                                                 other_data={'invoice_postage': 'never', 'invoice_state': 'none','origin': wo_rcs.name_get()[0][-1]})
                                
                                move_rc_warehouse_rs = out_picking_rcs.warehouse_id or self.env.user.company_id.warehouse_id
                                # Création du mouvement OUT du stock vers ST au cas ou le produit est pris sur stock
                                transfer_rs = transfer_obj.create({'product_id': line.product_id.id,
                                                                   'origin': line.wo_id.mo_id.name,
                                                                   'warehouse_id': move_rc_warehouse_rs.id,
                                                                   'warehouse_dest_id': location_rcs.warehouse_id.id,
                                                                   'uom_qty': line.onstock_qty,
                                                                   'uom_id': line.uom_id.id,
                                                                   'needed_uom_qty': line.onstock_qty,
                                                                   'needed_uom_id': line.uom_id.id,
                                                                   'need_date': need_date,
                                                                   'is_automatic': True,
                                                                   'departure_date': transfer_obj.get_departure_date(need_date, warehouse_id=move_rc_warehouse_rs.id, warehouse_dest_id=location_rcs.warehouse_id.id)})
                                move_rc = move_obj.create_move(line.product_id, qty=line.onstock_qty, uom=line.uom_id, dst_location=location_obj.get_transfer_location(with_raise=True).id,
                                                                other_data={'transfer_id': transfer_rs.id, 'wo_rm_subcontracting_id': line.wo_id.id, 
                                                                            'type_subcontracting': 'stock', 'subc_origin_move_id': line.rm_fp_draft_id.id},
                                                                type='out', date=line.date, picking=out_picking_rcs, partner=supplier_val, with_price=False, 
                                                                in_product_uom=True, warehouse_rs=move_rc_warehouse_rs)
                                move_rcs += move_rc
                            
                            
#                             if line.onstock_subc_qty:
#                                 if line.onstock_subc_qty > line.release_qty:
#                                     raise except_orm(_('Error'), _('Delete line order and on stock qty 0.'))
#                                 
# #                                 if not out_picking_rcs:
# #                                     out_picking_rcs = picking_obj.create_picking('out', partner=supplier_rcs, product_qty_uom=None, date=False, 
# #                                                                                  other_data={'invoice_postage': 'never', 'invoice_state': 'none','origin': wo_rcs.name_get()[0][-1]})
#                                 
#                                 regul_location = line.wo_id.company_id.warehouse_id.regulation_location_id and line.wo_id.company_id.warehouse_id.regulation_location_id.id or False
#                                 if not regul_location:
#                                     raise except_orm(_('Error'), _('The regulation location is not defined.'))
#                                 
#                                 # Création du mouvement libre de l'emplacement de ST vers l'emplacement de régulation
#                                 origin = _('Regulation release')
#                                 move_inter1 = move_obj.create_move(line.product_id, src_location=location_rcs.id, dst_location=regul_location, qty=line.onstock_subc_qty, 
#                                                                     uom=line.uom_id, sec_qty=None, sec_uom=None, type='out',date=False, other_data={'origin': origin}, 
#                                                                     picking=False, partner=False, with_price=False, in_product_uom=False)
#                                 move_inter1.wkf_waiting()
#                                 move_inter1.wkf_done()
#                                 # Création du mouvement libre de l'emplacement de régulation vers de l'emplacement de ST rattaché à l'OT 
#                                 move_rc = move_obj.create_move(line.product_id, src_location=regul_location, dst_location=location_rcs.id, qty=line.onstock_subc_qty, 
#                                                                     uom=line.uom_id, sec_qty=None, sec_uom=None, type='out',date=False, other_data={'wo_rm_subcontracting_id': line.wo_id.id, 'type_subcontracting': 'stock'}, 
#                                                                     picking=False, partner=False, with_price=False, in_product_uom=False)
#                                 move_rc.wkf_waiting()
#                                 move_rc.wkf_done()
                                    
                        if type in ('indirect', 'stock'):
                            other_data={'wo_rm_subcontracting_id': line.wo_id.id, 'type_subcontracting': 'stock'}
                            if type == 'indirect':
                                qty = line.order_qty
                                if pol_rcs:
                                    other_data['purchase_line_id'] = pol_rcs.id
                                    
                                other_data['trigger_supply'] = 'without_stock'
                            else:
                                qty = line.onstock_qty
                            
                            move_rc_warehouse_rs = out_picking_rcs.warehouse_id or self.env.user.company_id.warehouse_id
                            transfer_rs = transfer_obj.create({'product_id': line.product_id.id,
                                                               'origin': line.wo_id.mo_id.name,
                                                               'warehouse_id': move_rc_warehouse_rs.id,
                                                               'warehouse_dest_id': location_rcs.warehouse_id.id,
                                                               'uom_qty': line.onstock_qty,
                                                               'uom_id': line.uom_id.id,
                                                               'needed_uom_qty': line.onstock_qty,
                                                               'needed_uom_id': line.uom_id.id,
                                                               'need_date': need_date,
                                                               'is_automatic': True,
                                                               'departure_date': transfer_obj.get_departure_date(need_date, warehouse_id=move_rc_warehouse_rs.id, warehouse_dest_id=location_rcs.warehouse_id.id)})
                            other_data['transfer_id'] = transfer_rs.id
                            other_data['subc_origin_move_id'] = line.rm_fp_draft_id.id
                            # Création du mouvement OUT du stock vers ST au cas ou le produit est acheté en indirect
                            move_rc = move_obj.create_move(line.product_id, qty=qty, uom=line.uom_id, other_data=other_data, dst_location=location_obj.get_transfer_location(with_raise=True).id,
                                                           type='out', date=line.date, picking=out_picking_rcs, partner=supplier_val, 
                                                           with_price=False, in_product_uom=True, warehouse_rs=move_rc_warehouse_rs)
                            move_rcs += move_rc
                            
                if po_rcs and not po_rcs.purchase_order_line_ids:
                    po_rcs.unlink()
            
            return purchase_rcs, out_picking_rcs, move_rcs
    
    
    def create_purchase_subcontracting_rm_fp(self, supplier_rcs, location_rcs, wo_rcs, type_rm_fp='rm'):
        """
            Création de purchase
        """
        purchase_direct_rcs = self.env['purchase.order']
        purchase_indirect_rcs = self.env['purchase.order']
        purchase_stock_rcs = self.env['purchase.order']
        move_rcs = self.env['stock.move']
        dico_value = {'purchase_direct': {}, 'stock': {}, 'purchase_indirect':{}}
        po_obj = self.env['purchase.order']
        pol_obj = self.env['purchase.order.line']
        move_obj = self.env['stock.move']
        picking_obj = self.env['stock.picking']
        for line in self:
#             if not line.order_qty and not line.onstock_qty: # and not line.onstock_subc_qty:
#                 raise except_orm(_('Error'), _('Delete line order and on stock qty 0.'))
            
            # Grouper les lignes par fournisseur
            # Si de type direct
            if line.type == 'direct':
                partner_rcs = line.supplier_id or supplier_rcs
                if not dico_value['purchase_direct'] or dico_value['purchase_direct'] and partner_rcs not in dico_value['purchase_direct']:
                    dico_value['purchase_direct'][partner_rcs] = []
                    dico_value['purchase_direct'][partner_rcs].append(line)
                else:
                    dico_value['purchase_direct'][partner_rcs].append(line)
            # Si de type Indirect
            elif line.type == 'indirect':
                partner_rcs = line.supplier_id or supplier_rcs
                if not dico_value['purchase_indirect'] or dico_value['purchase_indirect'] and partner_rcs not in dico_value['purchase_indirect']:
                    dico_value['purchase_indirect'][partner_rcs] = []
                    dico_value['purchase_indirect'][partner_rcs].append(line)
                else:
                    dico_value['purchase_indirect'][partner_rcs].append(line)
            
        
        # Génération des BLs ou/et des achats
        out_picking_rcs = False
        if dico_value['purchase_direct']:
            purchase_direct_rcs, out_picking_rcs, move_rcs = self.create_purchase_subcontracting_wo(dico_value['purchase_direct'], 
                                                                        po_obj, pol_obj, move_obj, picking_obj, 'direct', 'out', purchase_direct_rcs, 
                                                                        supplier_rcs, location_rcs, out_picking_rcs, move_rcs, wo_rcs)
                
        if dico_value['purchase_indirect']:
            purchase_indirect_rcs, out_picking_rcs, move_rcs = self.create_purchase_subcontracting_wo(dico_value['purchase_indirect'], 
                                                                        po_obj, pol_obj, move_obj, picking_obj, 'indirect', 'in', purchase_indirect_rcs, 
                                                                        supplier_rcs, location_rcs, out_picking_rcs, move_rcs, wo_rcs)
        
        if dico_value['stock']:
            purchase_stock_rcs, out_picking_rcs, move_rcs = self.create_purchase_subcontracting_wo(dico_value['stock'], 
                                                                        po_obj, pol_obj, move_obj, picking_obj, 'stock', 'out', purchase_stock_rcs, 
                                                                        supplier_rcs, location_rcs, out_picking_rcs, move_rcs, wo_rcs)
        
        if out_picking_rcs:
            out_picking_rcs.wkf_waiting()
        
        dico_create_po_subc_rm_fp = {'purchase_direct_rcs': purchase_direct_rcs, 'purchase_indirect_rcs': purchase_indirect_rcs, 
                                     'purchase_stock_rcs': purchase_stock_rcs, 'move_rcs': wo_rcs}
        
        return dico_create_po_subc_rm_fp
 


class purchase_subcontracting_services_wiz(models.TransientModel):
    """ 
        Subcontracting Purchase Services Wiz
    """
    _name = 'purchase.subcontracting.services.wiz'
    _description = 'Subcontracting Purchase Services Wiz'
    _rec_name = 'product_id'
    

    def compute_price_total(self, quantity, uom, product, supplier_rcs=False, fp_supplier=False, wo=False):
        price = 0.0
        bon_obj = self.env['mrp.bom']
        currency_price_return = wo and wo.company_id and wo.company_id.currency_id or False
        supplier = supplier_rcs or fp_supplier or False
        if product:
            if supplier:
                sinfo_brw = self.env['product.supplierinfo'].search([('product_id', '=', product.id), ('partner_id', '=', supplier.id)])
            else:
                sinfo_brw = False
                
            price_unit_product = bon_obj.compute_price_component_buy(product, quantity, uom, currency_price_return, supplier=supplier, sinfo_brw=sinfo_brw)
            price = price_unit_product * quantity
            
        return price
    
    @api.one
    @api.depends('psfp_id', 'psfp_id.quantity')
    def _compute_qty(self):
        """
            Chanp fonction pour la quantité, le prix, l'UoM
        """
        self.uom_id = self.consum_service_id.uom_id.id
        self.product_id = self.consum_service_id.product_id.id
        if self.consum_service_id.type == 'fixed':
            self.quantity = self.consum_service_id.quantity
            self.price_total = self.consum_service_id.price_total
        else:
            self.quantity = self.consum_service_id.quantity / self.psfp_id.wo_id.quantity * self.psfp_id.quantity
            self.price_total = self.compute_price_total(self.quantity, self.uom_id, self.product_id, supplier_rcs=self.psfp_id.supplier_id, fp_supplier=self.psfp_id.fp_supplier_id, wo=self.psfp_id.wo_id)
        
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wo_id = fields.Many2one('mrp.workorder', string='Wo', required=False, ondelete='cascade')
    consum_service_id = fields.Many2one('mrp.wo.consumed.service', string='Consumed Service', required=False, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', compute='_compute_qty')
    quantity = fields.Float(string='Qty', compute='_compute_qty')
    price_total = fields.Float(string='Price Total', compute='_compute_qty', digits=dp.get_precision('Price technical'))
    uom_id = fields.Many2one('product.uom', string='UoM', compute='_compute_qty')
    psfp_id = fields.Many2one('purchase.subcontracting.fp', string='Purchase subcontraction FP', required=False, ondelete='cascade')
     
     
    #===========================================================================
    # FONCTION
    #===========================================================================
    def create_service_subcontracting(self, psfp_rcs, po_rcs, type):
        pol_obj = self.env['purchase.order.line']
        for service in self:
            price_unit = service.quantity and service.price_total/service.quantity or service.price_total
            subcontracting = _('Subcontracting')
            source = '%s %s'%(subcontracting, psfp_rcs.wo_id.name_get()[0][1])
            purchase_line_rcs = pol_obj.create_purchase_order_line(purchase=po_rcs, product=service.product_id, 
                                               values={'expected_date': psfp_rcs.date, 'uom_qty': service.quantity, 'wo_fp_subcontracting_id': psfp_rcs.wo_id.id, 'need_date': psfp_rcs.wo_id.planned_end_date, 
                                                       'source': source, 'uom_id':service.uom_id.id, 'price_unit': price_unit, 'wo_qty': psfp_rcs.quantity}, first_qty='uom_qty', forced_qty=True)
            purchase_line_rcs.write({'price_unit': price_unit})
            
        # Si c'est le dernier OT de l'OF, déclaration du produit final
# TODO THOMAS: commenté car non utilisé. À supprimer ulterieurement
#         last_wo = False
#         if not psfp_rcs.wo_id.next_wo_ids:
#             last_wo = True
#         else:
#             last_wo = True
#             for next_wo in psfp_rcs.wo_id.next_wo_ids:
#                 if next_wo.mo_id.id == psfp_rcs.wo_id.mo_id.id:
#                     last_wo = False
#                     break
                
        if po_rcs and not po_rcs.purchase_order_line_ids:
            po_rcs.unlink()
        
        return True




class subcontracting_regul_wiz(models.TransientModel):
    """ 
        Subcontracting Regulation Wiz
    """
    _name = 'subcontracting.regul.wiz'
    _description = 'Subcontracting Regulation Wiz'
    _rec_name = 'wo_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wo_id = fields.Many2one('mrp.workorder', string='Wo', required=False, ondelete='cascade')
    line_ids = fields.One2many('subcontracting.regul.wiz.line', 'regul_id',  string='Lines')
    
    
    def create_wiz(self, wo):
        """ 
            Fonction qui permet de créer le wizard et les lignes à partir d'un OT et qui retourne l'id du wizard créé
        """
        product_dics = self.compute_qty_regul_st(wo)
        if product_dics:
            vals = {'wo_id': wo.id,
                    'line_ids': []
                    }
            for product_dic in product_dics:
                vals['line_ids'].append((0, 0, product_dics[product_dic]))
            
            wiz_rcs = self.create(vals)
        else:
            wiz_rcs = False
            raise except_orm(_('Error'), _('No product.'))
    
        return wiz_rcs
    
    
    def compute_qty_regul_st(self, wo, product_ids=False):
        uom_obj = self.env['product.uom']
        move_obj = self.env['stock.move']
        product_dics = {}
        location_st_id = wo.first_resource_id and wo.first_resource_id.location_id and wo.first_resource_id.location_id.id or False
        if not location_st_id:
            raise except_orm(_('Error'), _('No resource in workorder or No emplacement in workorder resource.'))
        
        args_search = [('state', '=', 'done'), ('wo_rm_subcontracting_id', '=', wo.id), '|', ('location_dest_id', '=', location_st_id), ('location_id', '=', location_st_id)]
        if product_ids:
            args_search.append(('product_id', 'in', product_ids))
        
        move_rcs = move_obj.search(args_search)
        for move_rm in move_rcs:
            if move_rm.product_id in product_dics:
                if location_st_id == move_rm.location_dest_id.id:
                    sent_qty = uom_obj._compute_qty_obj(move_rm.uom_id, move_rm.uom_qty, move_rm.product_id.uom_id, with_raise=False, with_round=False)
                    regul_qty = 0.0
                else:
                    sent_qty = 0.0
                    regul_qty = uom_obj._compute_qty_obj(move_rm.uom_id, move_rm.uom_qty, move_rm.product_id.uom_id, with_raise=False, with_round=False)
            
            
                product_dics[move_rm.product_id]['sent_qty'] += sent_qty
                product_dics[move_rm.product_id]['regul_qty'] += regul_qty
                product_dics[move_rm.product_id]['remaining_qty']  = product_dics[move_rm.product_id]['sent_qty'] - product_dics[move_rm.product_id]['consummed_qty'] - product_dics[move_rm.product_id]['regul_qty']
            
            else:
                if location_st_id == move_rm.location_dest_id.id:
                    sent_qty = uom_obj._compute_qty_obj(move_rm.uom_id, move_rm.uom_qty, move_rm.product_id.uom_id, with_raise=False, with_round=False)
                    regul_qty = 0.0
                else:
                    sent_qty = 0.0
                    regul_qty = 0.0
                    if location_st_id == move_rm.location_id.id:
                        regul_qty = uom_obj._compute_qty_obj(move_rm.uom_id, move_rm.uom_qty, move_rm.product_id.uom_id, with_raise=False, with_round=False)
                
                move_rm_qtys = move_obj.search_group(fields=['uom_qty', 'uom_id'], 
                                       groupby=['uom_id'], 
                                       args=[('product_id', '=', move_rm.product_id.id), ('state', '=', 'done'), ('wo_incoming_id', '=', wo.id)],
                                       sum='uom_qty',
                                       return_dict=True)
                
                consummed_qty = 0
                for move_rm_qty in move_rm_qtys:
                    if move_rm.product_id.uom_id and move_rm.product_id.uom_id.id == move_rm_qty['uom_id']:
                        consummed_qty += move_rm_qty['uom_qty']
                    else:
                        consummed_qty += self.env['product.uom']._compute_qty(move_rm_qty['uom_id'], move_rm_qty['uom_qty'], 
                                                                    to_uom_id=move_rm.product_id.uom_id.id, with_raise=True, with_round=False)
                
                
                remaining_qty = sent_qty - consummed_qty - regul_qty
                product_dics[move_rm.product_id] = {'sent_qty': sent_qty,
                                                    'consummed_qty': consummed_qty,
                                                    'regul_qty': regul_qty,
                                                    'remaining_qty': remaining_qty,
                                                    'product_id': move_rm.product_id.id,
                                                    'uom_id': move_rm.product_id.uom_id.id,
                                                   }
        
        return product_dics


class subcontracting_regul_wiz_line(models.TransientModel):
    """ 
        Subcontracting Regulation Wiz Line
    """
    _name = 'subcontracting.regul.wiz.line'
    _description = 'Subcontracting Regulation Wiz Line'
    _rec_name = 'product_id'
    
    @api.one
    @api.depends()
    def _compute_qty(self):
        """
            Chanp fonction pour les quantités
        """
        product_dics = self.regul_id.compute_qty_regul_st(self.regul_id.wo_id, product_ids=[self.product_id.id])
        sent_qty = 0
        consummed_qty = 0
        remaining_qty = 0
        regul_qty = 0
        for product_dic in product_dics:
            if product_dic == self.product_id:
                sent_qty = product_dics[product_dic]['sent_qty']
                consummed_qty = product_dics[product_dic]['consummed_qty']
                remaining_qty = product_dics[product_dic]['remaining_qty']
                regul_qty = product_dics[product_dic]['regul_qty']
                
        self.sent_qty = sent_qty
        self.consummed_qty = consummed_qty
        self.remaining_qty = remaining_qty
        self.regul_qty = regul_qty
        
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    regul_id = fields.Many2one('subcontracting.regul.wiz', string='Regul', required=False, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', ondelete='cascade')
    uom_id = fields.Many2one('product.uom', string='UOM', ondelete='cascade')
    sent_qty = fields.Float(string='Sent qty', default=0.0, digits=dp.get_precision('Product quantity'), compute='_compute_qty')
    consummed_qty = fields.Float(string='Consummed qty', default=0.0, digits=dp.get_precision('Product quantity'), compute='_compute_qty')
    remaining_qty = fields.Float(string='Remaining qty', default=0.0, digits=dp.get_precision('Product quantity'), compute='_compute_qty')
    regul_qty = fields.Float(string='Regulation qty', default=0.0, digits=dp.get_precision('Product quantity'), compute='_compute_qty')
    
    @api.multi
    def button_modificate(self):
        for wiz in self:
            modificate_rcs = self.env['subcontracting.regul.wiz.action'].create({'regul_id': wiz.regul_id.id,
                                                                                 'reguline_id': wiz.id,})
            return {
                        'name': _('Modificate'),
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'subcontracting.regul.wiz.action',
                        'type': 'ir.actions.act_window',
                        'target': 'new',
                        'res_id': modificate_rcs.id,
                        'nodestroy': True,
                        'context': {'dialog_size': 'medium'}
                        }
        return True



class subcontracting_regul_wiz_action(models.TransientModel):
    """ 
        Subcontracting Regulation Wiz action
    """
    _name = 'subcontracting.regul.wiz.action'
    _description = 'Subcontracting Regulation Wiz action'
    _rec_name = 'reguline_id'
    
    @api.model
    def _action_type_get(self):
        return [
                ('cons_direct', _('Direct consumption')),
                ('cons_regul', _('consumption regulation')),
                ('reallocation', _('Reallocation')),
                ('release', _('Release')),
                       ]

    #===========================================================================
    # COLUMNS
    #===========================================================================
    regul_id = fields.Many2one('subcontracting.regul.wiz', string='Regul', required=False, ondelete='cascade')
    reguline_id = fields.Many2one('subcontracting.regul.wiz.line', string='Regul line', required=False, ondelete='cascade')
    action_type = fields.Selection('_action_type_get', string='Action')
    regul_qty = fields.Float(string='Regulation qty', default=0.0, digits=dp.get_precision('Product quantity'))
    reallocation_wo_id = fields.Many2one('mrp.workorder', string='Reallocation Wo', required=False, ondelete='cascade')
    
    
    @api.multi
    def validate(self):
        move_obj = self.env['stock.move']
        uom_obj = self.env['product.uom']
        for wiz in self:
            # Consommation Direct
            if wiz.action_type == 'cons_direct':
                if wiz.regul_qty > 0 and wiz.regul_qty <= wiz.reguline_id.remaining_qty:
                    # Recherche de tous les mouvements du produit dans l'ot qui sont annulés, pour utiliser les mouvements annulés afin de faire la consommation
                    move_rcs = move_obj.search([('product_id', '=', wiz.reguline_id.product_id.id), ('state', '=', 'cancel'), ('wo_incoming_id', '=', wiz.regul_id.wo_id.id), ('not_usable', '=', False)])
                    if not move_rcs:
                        move_inter_rcs = move_obj.search([('product_id', '=', wiz.reguline_id.product_id.id), ('wo_incoming_id', '=', wiz.regul_id.wo_id.id), ('not_usable', '=', False)], limit=1)
                        if move_inter_rcs:
                            move_uom_qty = uom_obj._compute_qty_obj(move_inter_rcs.product_id.uom_id, wiz.regul_qty, move_inter_rcs.uom_id, with_raise=False, with_round=False)
                            move_sec_uom_qty = uom_obj._compute_qty_obj(move_inter_rcs.product_id.uom_id, wiz.regul_qty, move_inter_rcs.sec_uom_id, with_raise=False, with_round=False)
                            move_uoi_qty = uom_obj._compute_qty_obj(move_inter_rcs.product_id.uom_id, wiz.regul_qty, move_inter_rcs.uoi_id, with_raise=False, with_round=False)
                            move_rcs = move_inter_rcs.copy({'uom_qty': move_uom_qty, 'sec_uom_qty': move_sec_uom_qty, 'uoi_qty': move_uoi_qty})
                            move_rcs.wkf_cancel()
                            
                    move_dic = wiz.move_dic_qty(move_rcs, uom_obj)
                    # Boucle sur les mouvements annulés à modifier
                    for move in move_dic:
                        move_qty = uom_obj._compute_qty_obj(move.uom_id, move.uom_qty, move.product_id.uom_id, with_raise=False, with_round=False)
                        # Si l'on utilise toute la quantité du mouvement on passe le mouvement à terminé
                        if move_qty == move_dic[move]:
                            dummy, new_move = move.wkf_draft()
                            if dummy:
                                move = new_move
                                
                            move.wkf_waiting()
                            move.wkf_done()
                        # Si non on split le mouvement
                        else:
                            uom_qty = uom_obj._compute_qty_obj(move.product_id.uom_id, move_dic[move], move.uom_id, with_raise=False, with_round=False)
                            sec_uom_qty = uom_qty * move.sec_uom_qty / move.uom_qty
                            uoi_qty = uom_qty * move.uoi_qty / move.uom_qty
                            
                            remaining_uom_qty = move.uom_qty - uom_qty
                            remaining_sec_uom_qty = move.sec_uom_qty - sec_uom_qty
                            remaining_uoi_qty = move.uoi_qty - uoi_qty
                            
                            dummy, new_move = move.wkf_draft()
                            if dummy:
                                move = new_move
                                
                            move.write({'uom_qty': uom_qty,
                                        'sec_uom_qty': sec_uom_qty,
                                        'uoi_qty': uoi_qty,})
                            
                            new_move = move.copy({'uom_qty': remaining_uom_qty,
                                        'sec_uom_qty': remaining_sec_uom_qty,
                                        'uoi_qty': remaining_uoi_qty,})
                            
                            move.wkf_waiting()
                            move.wkf_done()
                            new_move.wkf_cancel()
                
                else:
                    raise except_orm(_('Error'), _('The quantity must be greater than 0 and less than %f.')%(wiz.reguline_id.remaining_qty))
            # Régulation de consommation
            elif wiz.action_type == 'cons_regul':
                if wiz.regul_qty > 0 and wiz.regul_qty <= wiz.reguline_id.consummed_qty:
                    # Recherche de tous les mouvements du produit dans l'ot qui sont terminés, pour utiliser les mouvements terminés afin de faire la régulation de consommation
                    move_rcs = move_obj.search([('product_id', '=', wiz.reguline_id.product_id.id), ('state', '=', 'done'), ('wo_incoming_id', '=', wiz.regul_id.wo_id.id)])
                    move_dic = wiz.move_dic_qty(move_rcs, uom_obj)
                    # Boucle sur les mouvements terminés à modifier
                    for move in move_dic:
                        move_qty = uom_obj._compute_qty_obj(move.uom_id, move.uom_qty, move.product_id.uom_id, with_raise=False, with_round=False)
                        # Si l'on utilise toute la quantité du mouvement on passe le mouvement à terminé
                        if move_qty == move_dic[move]:
                            move.wkf_cancel()
                        # Si non on split le mouvement
                        else:
                            uom_qty = uom_obj._compute_qty_obj(move.product_id.uom_id, move_dic[move], move.uom_id, with_raise=False, with_round=False)
                            sec_uom_qty = uom_qty * move.sec_uom_qty / move.uom_qty
                            uoi_qty = uom_qty * move.uoi_qty / move.uom_qty
                            
                            remaining_uom_qty = move.uom_qty - uom_qty
                            remaining_sec_uom_qty = move.sec_uom_qty - sec_uom_qty
                            remaining_uoi_qty = move.uoi_qty - uoi_qty
                            
                            move.write({'uom_qty': remaining_uom_qty,
                                        'sec_uom_qty': remaining_sec_uom_qty,
                                        'uoi_qty': remaining_uoi_qty,})
                            
                            new_move = move.copy({'uom_qty': uom_qty,
                                        'sec_uom_qty': sec_uom_qty,
                                        'uoi_qty': uoi_qty,})
                            
                            new_move.wkf_cancel()
                else:
                    raise except_orm(_('Error'), _('The quantity must be greater than 0 and less than %f.')%(wiz.reguline_id.consummed_qty))
            # Réaffectation ou libération
            elif wiz.action_type == 'reallocation' or wiz.action_type == 'release':
                if wiz.regul_qty > 0 and wiz.regul_qty <= wiz.reguline_id.remaining_qty:
                    regul_location = wiz.regul_id.wo_id.company_id.warehouse_id.regulation_location_id and wiz.regul_id.wo_id.company_id.warehouse_id.regulation_location_id.id or False
                    if not regul_location:
                        raise except_orm(_('Error'), _('The regulation location is not defined.'))
                    
                    origin = _('Regulation')
                    origin = '%s %s'%(origin, wiz.regul_id.wo_id.name_get()[0][1])
                    other_data = {'wo_rm_subcontracting_id': wiz.regul_id.wo_id.id, 'origin': origin}
                    # On crée un mvt de stock de l'emplacement de la ressource vers l'emplacement de regulation
                    move_inter1 = move_obj.create_move(wiz.reguline_id.product_id, src_location=wiz.regul_id.wo_id.first_resource_id.location_id.id, 
                                         dst_location=regul_location, qty=wiz.regul_qty, uom=wiz.reguline_id.uom_id, sec_qty=None, sec_uom=None, type='out', 
                                         date=False, other_data=other_data, picking=False, partner=False, with_price=False, in_product_uom=False)
                    
                    move_inter1.wkf_waiting()
                    move_inter1.wkf_done()
                    other_data2 = {'origin': origin}
                    # Si réafectation on affecte le future mouvement au prochain OT
                    if wiz.action_type == 'reallocation':
                        other_data2['wo_rm_subcontracting_id'] = wiz.reallocation_wo_id.id
                    
                    # On crée un mvt de stock de l'emplacement de regulation vers l'emplacement de la ressource 
                    move_inter2 = move_obj.create_move(wiz.reguline_id.product_id, src_location=regul_location, 
                                         dst_location=wiz.regul_id.wo_id.first_resource_id.location_id.id, qty=wiz.regul_qty, uom=wiz.reguline_id.uom_id, sec_qty=None, sec_uom=None, type='out', 
                                         date=False, other_data=other_data2, picking=False, partner=False, with_price=False, in_product_uom=False)
                    move_inter2.wkf_waiting()
                    move_inter2.wkf_done()
                else:
                    raise except_orm(_('Error'), _('The quantity must be greater than 0 and less than %f.')%(wiz.reguline_id.remaining_qty))
        
            return {
                    'name': _('Regulation'),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'subcontracting.regul.wiz',
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'res_id': wiz.regul_id.id,
                    'context': {'dialog_size': 'large'}
                    }
        
        return True
    
    
    @api.multi
    def button_cancel(self):
        for wiz in self:
            return {
                    'name': _('Regulation'),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'subcontracting.regul.wiz',
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'res_id': wiz.regul_id.id,
                    'context': {'dialog_size': 'large'}
                    }
        return True
    
    
    def move_dic_qty(self, move_rcs, uom_obj):
        remaining_qty = 0
        move_dic = {}
        for move in move_rcs:
            move_qty = uom_obj._compute_qty_obj(move.uom_id, move.uom_qty, move.product_id.uom_id, with_raise=False, with_round=False)
            # Si la quantité de la consommation est égale au mouvement on prend celui là
            if move_qty == self.regul_qty:
                move_dic = {}
                move_dic[move] = move_qty
                break
            # Si la quantité du mouvement est inférieure
            elif move_qty < self.regul_qty:
                if remaining_qty + move_qty > self.regul_qty:
                    move_dic[move] = self.regul_qty - remaining_qty
                else:
                    move_dic[move] = move_qty
                
                remaining_qty += move_qty
                if remaining_qty == self.regul_qty:
                    break
            # Si la quantité du mouvement est supérieur
            else:
                move_dic = {}
                move_dic[move] = self.regul_qty
                break
        
        return move_dic
    


class subcontracting_inventory_location(models.TransientModel):
    """ 
        Subcontracting inventory location
    """
    _name = 'subcontracting.inventory.location'
    _description = 'Subcontracting inventory location'
    _rec_name = 'location_id'
    
    location_id = fields.Many2one('stock.location', string='Location', required=True, ondelete='cascade')
    line_ids = fields.One2many('subcontracting.inventory.location.line', 'inventory_id',  string='Lines')
    
    
    @api.multi
    def visualization(self):
        product_obj = self.env['product.product']
        uom_obj = self.env['product.uom']
        move_obj = self.env['stock.move']
        line_obj = self.env['subcontracting.inventory.location.line']
        for wiz in self:
            in_args = [('location_dest_id', '=', wiz.location_id.id),('state', '=', 'done'), ('wo_outgoing_id', '=', False), ('wo_incoming_id', '=', False), ('wo_rm_subcontracting_id', '=', False), ('wo_fp_subcontracting_id', '=', False)]
            out_args = [('location_id', '=', wiz.location_id.id), ('state', '=', 'done'), ('wo_outgoing_id', '=', False), ('wo_incoming_id', '=', False), ('wo_rm_subcontracting_id', '=', False), ('wo_fp_subcontracting_id', '=', False)]
            datas = wiz.location_id.get_location_product_qty(product_obj, uom_obj, move_obj, in_args=in_args, out_args=out_args)
            wiz.line_ids.unlink()
            for data in datas.values():
                if data['quantity'] != 0.0:
                    vals_line = {'inventory_id': wiz.id,
                                 'product_id': data['product_id'],
                                 'uom_id': data['uom_id'],
                                 'qty': data['quantity'],}
                    line_obj.create(vals_line)
                    
        return {'type': 'ir.actions.act_window_dialog_reload'} 
    
    

class subcontracting_inventory_location_line(models.TransientModel):
    """ 
        Subcontracting inventory location line
    """
    _name = 'subcontracting.inventory.location.line'
    _description = 'Subcontracting inventory location line'
    _rec_name = 'product_id'
    
    inventory_id = fields.Many2one('subcontracting.inventory.location', string='Inventory', required=False, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='cascade')
    qty = fields.Float(string='Qty', default=0.0, required=False)
    uom_id = fields.Many2one('product.uom', string='UoM', required=False, ondelete='cascade')
    
    
    
    
    
    
    