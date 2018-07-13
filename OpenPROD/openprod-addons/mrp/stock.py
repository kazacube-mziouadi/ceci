# -*- coding: utf-8 -*-
from openerp import models, api, fields, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm, ValidationError, UserError
from datetime import timedelta
from decimal import Decimal


class stock_warehouse(models.Model):
    _inherit = 'stock.warehouse'
    #===========================================================================
    # COLUMNS
    #===========================================================================
    production_location_id = fields.Many2one('stock.location', string='Production location', required=False, ondelete='restrict', 
                                             default=lambda self: self.env.ref('stock_location.location_stock'))
    regulation_location_id = fields.Many2one('stock.location', string='Regulation location', required=False, ondelete='restrict')
    
    
    
class stock_picking(models.Model):
    _inherit = 'stock.picking'

    def copy_return_move_st(self, vals):
        """
            Fonction qui permet de déconnecter les mouvements de retour lors de leur copy des ots de soustraitance.
            :param vals: Dico pour la copy du mouvement
            :type vals: dico
        """
        vals['wo_rm_subcontracting_id'] = False
        vals['wo_fp_subcontracting_id'] = False
        return vals
    
    
    
class stock_move(models.Model):
    _inherit = 'stock.move'

    def _supply_method_get(self):
        res = super(stock_move, self)._supply_method_get()
        res.append(('produce', _('Produce')))
        return res     
            
            
    @api.model
    def _type_subcontracting_get(self):
        return [
                ('direct', 'Direct'),
                ('indirect', 'Indirect'),
                ('stock', 'Stock'),
                       ]
        
        
    def get_date_without_covers(self):
        product = self.product_id
        available_stock = product.available_stock
        virtual_stock = product.virtual_stock
        move_qty = self.get_product_uom_qty()
        # Stock virtuel < besoin => delai fournisseur
        if virtual_stock < move_qty:
            res = self.product_id.get_default_supply_delay(return_date=True)[1]
        # Stock réel et stock virtuel >= besoin => AJD
        elif available_stock >= move_qty:
            res = fields.Datetime.now()
        # Stock réel < besoin et stock virtuel >= besoin => Calcul date besoin
        else:
            res = product.get_date_last_stock_min(self.env.user.company_id.warehouse_id.stock_location_id, move_qty, inverse=True)
        
        if res and len(res) > 10:
            res = res[:10]
            
        return res
    
    
    @api.one
    def _compute_available_date(self):
        if self.wo_incoming_id and self.state not in ('done', 'cancel'):
            if self.state == 'waiting':
                if self.in_date:
                    self.available_date = self.in_date
                elif self.covered_by_stock_percent >= 100:
                    self.available_date = fields.Date.today()
                else:
                    self.available_date = self.get_date_without_covers()
            else:       
                self.available_date = self.get_date_without_covers()
        else:
            self.available_date = False

    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wo_incoming_id = fields.Many2one('mrp.workorder', string='WO (RM)', required=False, ondelete='cascade', select=True, help='The stock move is an RM of this WO')
    wo_outgoing_id = fields.Many2one('mrp.workorder', string='WO (FP)', required=False, ondelete='cascade', select=True, help='The stock move is an FP of this WO')
    wo_rm_subcontracting_id = fields.Many2one('mrp.workorder', string='WO (RM Subc)', required=False, ondelete='cascade', help='The stock move is an RM Subcontraction of this WO')
    wo_fp_subcontracting_id = fields.Many2one('mrp.workorder', string='WO (FP Subc)', required=False, ondelete='cascade', help='The stock move is an FP Subcontraction of this WO')
    counterpart_wo_id = fields.Many2one('mrp.workorder', string='WO (FP Subc)', required=False, ondelete='cascade', help='The stock move is an FP Subcontraction of this WO')
    wo_produce_id = fields.Many2one('mrp.wo.produce', string='WO Produce', required=False, ondelete='cascade')
    wo_consumption_id = fields.Many2one('mrp.wo.consumption', string='WO Consumption', required=False, ondelete='cascade')
    efficient_unit_qty = fields.Float(string='Factor Efficient', default=0.0, required=False, digits=(12,12))
    type_subcontracting = fields.Selection('_type_subcontracting_get', default='direct', string='Type')
    available_date = fields.Date(string='Available date', compute='_compute_available_date')
    component_id = fields.Many2one('mrp.bom', string='Component', required=False, ondelete='restrict')
    subc_origin_move_id = fields.Many2one('stock.move', string='Origin subcontracting move', required=False, ondelete='restrict', copy=False)

    
    def update_procurement_vals(self):
        res = super(stock_move, self).update_procurement_vals()
        if self.supply_method == 'produce':
            if self.product_id.planning_manager_id:
                res['responsible_id'] = self.product_id.planning_manager_id.id
            
        if self.wo_incoming_id:
            res['origin_wo_id'] = self.wo_incoming_id.id
            if self.wo_incoming_id.sale_line_id:
                res['sol_id'] = self.wo_incoming_id.sale_line_id.id
            
        return res
    
    
    def need_procurement(self):
        """
        Le mouvement nécessite un procurement si il appartient à un picking ou un OT
        """
        res = super(stock_move, self).need_procurement()
        if not res and self.wo_incoming_id:
            res = True
            
        return res
    
            
    def get_attributes_const(self):
        res = super(stock_move, self).get_attributes_const()
        res.update({
            'wo': self.wo_outgoing_id,
            'mo': self.wo_outgoing_id.mo_id,
            'sol': self.wo_outgoing_id.sale_line_id,
            'so': self.wo_outgoing_id.sale_line_id.sale_order_id,
            'customer': self.wo_outgoing_id.customer_id,
            'final_product': self.wo_outgoing_id.final_product_id,
                   })
            
        return res
    
    
    def move_partner(self):
        res = super(stock_move, self).move_partner()
        if self.wo_outgoing_id:
            res = self.wo_outgoing_id.customer_id and self.wo_outgoing_id.customer_id.id or False
        elif self.picking_id:
            res = self.wo_fp_subcontracting_id.customer_id and self.wo_fp_subcontracting_id.customer_id.id or False
            
        return res
    
    
    def declaration_production(self, future_state):
        """
            Fonction de déclaration de prod si move ST
        """
        if self.wo_fp_subcontracting_id:
            # Si c'est le dernier OT de l'OF
            last_wo = False
            if not self.wo_fp_subcontracting_id.next_wo_ids:
                last_wo = True
            else:
                last_wo = True
                for next_wo in self.wo_fp_subcontracting_id.next_wo_ids:
                    if next_wo.mo_id.id == self.wo_fp_subcontracting_id.mo_id.id:
                        last_wo = False
                        break
            
            if last_wo:
                product_fp_id = self.wo_fp_subcontracting_id.final_product_id.id
            else:
                product_fp_id = False
                for fp in self.wo_fp_subcontracting_id.fp_draft_ids:
                    if fp.product_id.is_int:
                        product_fp_id = fp.product_id.id
                
                if not product_fp_id and future_state == 'cancel':
                    for fp in self.wo_fp_subcontracting_id.fp_done_ids:
                        if fp.product_id.is_int:
                            product_fp_id = fp.product_id.id
            
            # Si le produit du move est celui du produit final ou intermédiaire
            if product_fp_id == self.product_id.id:
                # Si on fait une déclaration
                if future_state == 'done':
                    # Déclaration du premier wizard
                    first_resource_id = self.wo_fp_subcontracting_id.first_resource_id and self.wo_fp_subcontracting_id.first_resource_id.id or False
                    vals = {
                        'wo_id': self.wo_fp_subcontracting_id.id,
                        'user_id': self.env.user.id,
                        'uom_id': self.wo_fp_subcontracting_id.uom_id.id,
                        'product_id': self.wo_fp_subcontracting_id.final_product_id.id,
                        'quantity': self.uom_qty,
                        'type': 'cons_prod',
                        'date': fields.Datetime.now(),
                        'first_resource_id': first_resource_id
                    }
                    wdm_rcs = self.env['wo.declaration.main'].create(vals)
                    # Déclaration de la consomation
                    wdc_rcs = wdm_rcs.create_declaration_consumption()
                    # Déclaration de la production
                    wdp_rcs = wdc_rcs.action_validate_comsuption(no_return_view=True, vals_wo_comsumption_data={'st_move_id': self.id, 
                                                                                                                'st_pol_id': self.purchase_line_id.id})
                    wdp_rcs.write({'sec_qty_ok': self.sec_uom_qty})
                    prod_declaration_rc = wdp_rcs.validate_produce(vals_wo_produce_data={'st_move_id': self.id, 'st_pol_id': self.purchase_line_id.id})
                    # Affectation des étiquettes du mouvement du picking vers le mouvement de l'OT
                    if prod_declaration_rc:
                        for move_rc in prod_declaration_rc.move_ids:
                            if move_rc.product_id.id == self.product_id.id:
                                self.move_label_ids.with_context(override_reserved_test=True).copy({'move_id': move_rc.id})
                                break
                            
                # Si on fait une annulation
                elif future_state == 'cancel':
                    # Annulation des consommations si lié à ce mouvement
                    wo_consumption_rcs = self.env['mrp.wo.consumption'].search([('st_move_id', '=', self.id), ('state', '!=', 'cancel')])
                    if wo_consumption_rcs:
                        wo_consumption_rcs.wkf_cancel()
                    
                    # Annulation des productions si lié à ce mouvement
                    wo_produce_rcs = self.env['mrp.wo.produce'].search([('st_move_id', '=', self.id), ('state', '!=', 'cancel')])
                    if wo_produce_rcs:
                        wo_produce_rcs.wkf_cancel()
                        
        return True
    
    
    def get_write_query(self):
        return """
            SELECT
              sm.id as "id",
              sm.product_id as "product_id",
              sm.state as "state",
              sm.transfer_move_id as "transfer_move_id",
              sm.picking_id as "picking_id",
              proc.id as "procurement_id",
              proc.state as "procurement_state",
              sm.wo_rm_subcontracting_id as "wo_rm_subcontracting_id",
              wo_incoming.id as "wo_incoming_id",
              wo_incoming.is_subcontracting as "wo_incoming_is_subcontracting"
            FROM
              stock_move sm
              LEFT OUTER JOIN procurement_order proc ON sm.procurement_id = proc.id
              LEFT OUTER JOIN mrp_workorder wo_incoming ON sm.wo_incoming_id = wo_incoming.id
            WHERE
              sm.id IN (%s)
        """
    
    def get_covers_type(self, move_vals=False):
        if move_vals:
            if move_vals['wo_incoming_id'] and move_vals['wo_incoming_is_subcontracting'] or move_vals['wo_rm_subcontracting_id']:
                res = 'subcontracting'
            else:
                res = 'normal'
        else:
            if self.wo_incoming_id and self.wo_incoming_id.is_subcontracting or self.wo_rm_subcontracting_id:
                res = 'subcontracting'
            else:
                res = 'normal'
        
        return res
    
        
    def get_default_attributes(self):
        """
            Méthode redéfinie dans mrp et purchase pour avoir les attributs par défaut changés par 
            les ventes ou les achats.
        """
        res = super(stock_move, self).get_default_attributes()
        if self.procurement_id and self.procurement_id.sol_id:
            res.update({x.product_common_attribute_id.name: x.value for x in self.procurement_id.sol_id.product_attribute_ids})
             
        return res
    
    
    def constraint_move_quality_wkf_done(self):
        """
            Fonction qui permet de vérifier que le controle qualité a été fait
        """
        move = self
        if move.type == 'in' and move.is_control_declaration_recep and not move.is_recalculate_frequency_control and not move.control_declaration_id and (not move.wo_fp_subcontracting_id and not move.wo_outgoing_id) and not move.no_control:
                raise except_orm(_('Error'), _('Please make a quality declaration for the product %s')%(move.product_id.name))
        elif move.type == 'in' and move.is_control_declaration_recep and move.control_declaration_id and not move.no_control:
            error_qty = False
            if Decimal(str(move.initial_uom_qty)) != Decimal(str(move.control_declaration_id.qty_ok+move.control_declaration_id.qty_hs+move.control_declaration_id.qty_quarantine)):
                error_qty = True
                if move.control_declaration_id:
                    sum_qty = sum([x.uom_qty for x in move.control_declaration_id.move_ids])
                    if sum_qty == (move.control_declaration_id.qty_ok+move.control_declaration_id.qty_hs+move.control_declaration_id.qty_quarantine):
                        error_qty = False

            if error_qty:
                raise except_orm(_('Error'), _('Please make a quality declaration for the product %s')%(move.product_id.name))
        
        return True
    
    
    def move_post_quality_wkf_done(self):
        """
            Fonction qui permet de générer la qualité post
        """
        move = self
        partner_id = False
        control_declaration_obj = self.env['quality.control.declaration']
        qcp_rcs = False
        if move.wo_outgoing_id or move.wo_fp_subcontracting_id:
            qcp_rcs = self.env['quality.control.product'].search([('type', '=', 'post_intern'), ('product_id', '=', move.product_id.id)])
            type_declaration = 'post_intern'
            if move.wo_outgoing_id:
                name_ot = move.wo_outgoing_id.name_get()[0][1]
                partner_id = move.wo_outgoing_id.customer_id and move.wo_outgoing_id.customer_id.id or False
            else:
                name_ot = move.wo_fp_subcontracting_id.name_get()[0][1]
                partner_id = move.wo_fp_subcontracting_id.customer_id and move.wo_fp_subcontracting_id.customer_id.id or False
                
            name_declaration = _('Post %s %s') %(name_ot, move.name)
        elif move.picking_id:
            qcp_rcs = self.env['quality.control.product'].search([('type', '=', 'post_reception'), ('product_id', '=', move.product_id.id)])
            type_declaration = 'post_reception'
            name_declaration = _('Post %s') %(move.name)
            name_declaration = '%s %s' %(move.picking_id.name, name_declaration)
            partner_id = move.picking_id.partner_id and move.picking_id.partner_id.id or False
            
        if qcp_rcs:
            nb_label = 0
            if move.move_label_ids:
                nb_label = len(move.move_label_ids.ids)
            
            control_location_rs = self.env.user.get_warehouse_location('control')
            post_control_declaration_rcs = control_declaration_obj.generate_control_declaration(qcp_rcs, 
                                                                                                move.uom_qty, 
                                                                                                type_declaration=type_declaration, 
                                                                                                type_control=type_declaration, 
                                                                                                date=fields.Datetime.now(), 
                                                                                                name_declaration=name_declaration, 
                                                                                                move_init_rcs=move, 
                                                                                                product_rcs=move.product_id, 
                                                                                                partner_id=partner_id,
                                                                                                quantity_label=nb_label,
                                                                                                location_rs=control_location_rs,
                                                                                                location_dest_rs=move.product_id.get_storage_location(move.warehouse_id.id) or move.location_dest_id)
            if post_control_declaration_rcs:
                control_move_rs = self.create_move(
                    move.product_id, 
                    src_location=move.location_dest_id.id, 
                    dst_location=control_location_rs.id, 
                    qty=move.uom_qty, 
                    uom=move.uom_id, 
                    sec_qty=move.sec_uom_qty, 
                    sec_uom=move.sec_uom_id, 
                    date=move.date,
                    other_data={
                        'is_principal_quality': False,
                        'post_control_declaration_id': post_control_declaration_rcs.id
                    }
                )
                for move_label in move.move_label_ids:
                    move_label.copy({'move_id': control_move_rs.id})
                    
                control_move_rs.wkf_waiting()
                control_move_rs.wkf_done()
                
                post_control_declaration_rcs.write({'qty_label': nb_label, 'move_control_id': control_move_rs.id})
                move.write({'post_control_declaration_id': post_control_declaration_rcs.id})
            else:
                move.recalculate_frequency_quality_main(post_control=True)
                move.write({'is_recalculate_frequency_control': True})

        return True
    
    
    def compute_price_theo_real_wosub(self):
        """
            Fonction qui permet de calculer le prix théorique et réel d'un mouvement entrant de produit final d'un ot de soustraitance
        """
        if self.wo_fp_subcontracting_id:
            if self.wo_fp_subcontracting_id.final_product_id.id == self.product_id.id:
                move_produce_rcs, theo_price, real_price, currency_id = self.wo_fp_subcontracting_id.mo_id.compute_price_move_fp_button(forced_move_rcs=self)
                move_produce_rcs.write({'partner_price': real_price, 'theo_price': theo_price, 'currency_id': currency_id})
        
        return True
    
    def compute_price_sub_product_move(self):
        """
            Fonction qui permet de calculer le prix théorique et réel dans les sous produits des ots
        """
        if self.wo_fp_subcontracting_id:
            wo = self.wo_fp_subcontracting_id
        elif self.wo_outgoing_id:
            wo = self.wo_outgoing_id
        else:
            wo = False
        
        if wo:
            if self.product_id.id != wo.final_product_id.id and not self.product_id.is_int and wo.mo_id.bom_id:
                bom_id = wo.mo_id.bom_id.id
                subprod_obj = self.env['mrp.subproduct']
                subprod_rcs = subprod_obj.search([('bom_id', '=', bom_id), ('product_id', '=', self.product_id.id)], limit=1)
                if subprod_rcs:
                    price = subprod_rcs.price_unit
                    currency_id = self.env.user.company_id.currency_id.id
                    self.write({'partner_price': price, 'theo_price': price, 'currency_id': currency_id})
        
        return True 
            
    
    #===========================================================================
    # Boutons
    #===========================================================================
    @api.multi
    def button_open_picking(self):
        for line in self:
            if line.picking_id.type == 'out':
                action = self.env.ref('mrp.act_picking_out_open_button')
            else:
                action = self.env.ref('mrp.act_picking_in_open_button')
                
            if action:
                action = action.read()[0]
                if action.get('views'):
                    for index,item in enumerate(action['views']):
                        if item[-1] == 'form':
                            del action['views'][index]
                            action['views'].insert(0, item)
                            
                action['res_id'] = line.picking_id.id
                action['view_mode'] = 'form' 
                
            return action
    
    
    def do_action_on_wkf_done(self):
        res = super(stock_move, self).do_action_on_wkf_done()
        if self.type == 'in' and self.picking_id and self.subc_origin_move_id and \
           self.warehouse_id.id == self.subc_origin_move_id.warehouse_id.id and self.move_label_ids:
            # Qté du mouvement PF de l'OT en UdM produit
            uom_move_qty = self.subc_origin_move_id.get_product_uom_qty()
            # Soustraction des étiquettes déjà affectées
            label_qtys = self.subc_origin_move_id.get_label_qty()
            if label_qtys:
                uom_move_qty -= label_qtys[0].get('um_qty', 0.0)
            
            for ml in self.move_label_ids:
                # Si la quantité de l'étiquette ne dépasse pas la quantité restante du mouvement: affectation de l'étiquette entière
                if uom_move_qty >= ml.uom_qty:
                    ml.copy({'move_id': self.subc_origin_move_id.id})
                    uom_move_qty -= ml.uom_qty
                # Si la quantité de l'étiquette dépasse la quantité restante du mouvement: affectation de l'étiquette à hauteur de la quantité restante du mouvement
                else:
                    if uom_move_qty > 0:
                        ml.copy({'move_id': self.subc_origin_move_id.id,
                                 'uom_qty': uom_move_qty})
                        
                    break
                    
        return res

class stock_lot(models.Model):
    """ 
    Stock lot 
    """
    _inherit = 'stock.lot'    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    traceability_ids = fields.One2many('stock.label.traceability', 'from_lot_id',  string='Traceabiliy')
    
    
    def additional_function_domain(self, arg):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de stock_lot
        """
        arg0, arg1, arg_1 = super(stock_lot, self).additional_function_domain(arg)
        if arg[0] == 'domain_lot_wo':
            arg0 = 'id'
            arg1 = 'in'
            lot_ids = []
            if arg[-1]:
                # Retourne la liste des lots de l'OT
                wo_read = self.env['mrp.workorder'].browse(arg[-1]).read(['final_product_id'], load='_classic_write')
                move_rcs = self.env['stock.move'].search([('product_id', '=', wo_read[0]['final_product_id']), ('wo_outgoing_id', '=', wo_read[0]['id'])])
                lot_rcs = self.env['stock.lot']
                if move_rcs:
                    move_label_rcs = self.env['stock.move.label'].search([('move_id', 'in', move_rcs.ids)])
                    for move_label in move_label_rcs:
                        if move_label.label_id and move_label.label_id.lot_id:
                            lot_rcs |= move_label.label_id.lot_id
                            
                if lot_rcs:
                    lot_ids = lot_rcs.ids
                    
            arg_1 = lot_ids
                
        return arg0, arg1, arg_1
    
    
    @api.multi
    def build_traceability(self):
        """
        Construction de la traçabilité
        """
        traceability_obj = self.env['stock.label.traceability']
        for lot_rc in self:
            if lot_rc.traceability_ids:
                lot_rc.traceability_ids.unlink()
                
            traceability_obj.build_traceability(lot_rc=lot_rc)
            traceability_obj.after_build_traceability(lot_rc=lot_rc)
            
        return True
    
    
    
class stock_label(models.Model):
    """ 
    Label 
    """
    _inherit = 'stock.label'
    _description = 'Label'
       
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    traceability_ids = fields.One2many('stock.label.traceability', 'from_label_id',  string='Traceabiliy')
    
    
    @api.multi
    def build_traceability(self):
        """
        Construction de la traçabilité
        """
        traceability_obj = self.env['stock.label.traceability']
        for label_rc in self:
            if label_rc.traceability_ids:
                label_rc.traceability_ids.unlink()
                
            traceability_obj.build_traceability(label_rc=label_rc)
            traceability_obj.after_build_traceability(label_rc)
            
        return True
        
        
    def additional_function_domain(self, arg):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de stock_label
        """
        arg0, arg1, arg_1 = super(stock_label, self).additional_function_domain(arg)
        if arg[0] == 'assign_label_wo_consumption':
            arg0 = 'id'
            arg1 = arg[1]
            consum_line_obj = self.env['wo.declaration.consumption.line']
            consumption_line = consum_line_obj.browse(arg[-1])
            util_label_ids = []
            for label_consumption in consumption_line.label_consumption_ids:
                util_label_ids_int = [line.label_id.id for line in label_consumption.line_ids if line.label_id]
                if util_label_ids_int:
                    util_label_ids.extend(util_label_ids_int)
                    
            if util_label_ids:
                label_rcs = self.env['stock.label'].search([('product_id', '=', consumption_line.product_id.id), ('is_active', '=', True), ('id', 'not in', util_label_ids)])
                label_ids = [x.id for x in label_rcs]
            else:
                label_rcs = self.env['stock.label'].search([('product_id', '=', consumption_line.product_id.id), ('is_active', '=', True)])
                label_ids = [x.id for x in label_rcs]
                
            arg_1 = label_ids
        
        elif arg[0] == 'label_wo_search':
            arg0 = 'id'
            arg1 = '='
            wo_obj = self.env['mrp.workorder']
            wo = wo_obj.browse(arg[-1])
            product_rcs = self.env['product.product']
            for rm_ids in wo.rm_draft_ids:
                if rm_ids.product_id not in product_rcs:
                    product_rcs += rm_ids.product_id
                    
            label_ids = []
            label_used_rcs = self.env['stock.label']
            for label_consumption in self.env['mrp.label.consumption'].search([('wo_id', '=', wo.id)]):
                label_used_rcs += label_consumption.label_id
                
            if product_rcs:
                label_used_ids = label_used_rcs and label_used_rcs.ids or []
                label_rcs = self.env['stock.label'].search([('product_id', 'in', product_rcs.ids), ('is_active', '=', True), ('id', 'not in', label_used_ids)])
                label_ids = [x.id for x in label_rcs]
                
            arg_1 = label_ids
            
        elif arg[0] == 'assign_add_label_wo_produce':
            arg0 = 'id'
            arg1 = arg[1]
            produce_obj = self.env['wo.declaration.produce']
            decla_produce = produce_obj.browse(arg[-1])
            util_label_ids = []
            for asign_label in decla_produce.asign_label_ids:
                util_label_ids.append(asign_label.label_id.id)
                    
            if util_label_ids:
                label_rcs = self.env['stock.label'].search([('product_id', '=', decla_produce.product_id.id), ('is_active', '=', False), ('is_before_create', '=', True), ('id', 'not in', util_label_ids)])
                label_ids = [x.id for x in label_rcs]
            else:
                label_rcs = self.env['stock.label'].search([('product_id', '=', decla_produce.product_id.id), ('is_active', '=', False), ('is_before_create', '=', True)])
                label_ids = [x.id for x in label_rcs]
                
            arg_1 = label_ids
        
        elif arg[0] == 'label_wo_production_search':
            arg0 = 'id'
            arg1 = '='
            wo_obj = self.env['mrp.workorder']
            wo = wo_obj.browse(arg[-1])
            product_rcs = self.env['product.product']
            for fp_draft in wo.fp_draft_ids:
                product_rcs |= fp_draft.product_id
                
            label_ids = []
            label_used_rcs = self.env['stock.label']
            for label_production in self.env['mrp.label.production'].search([('wo_id', '=', wo.id)]):
                label_used_rcs += label_production.label_id
                
            if product_rcs:
                label_used_ids = label_used_rcs and label_used_rcs.ids or []
                label_rcs = self.env['stock.label'].search([('product_id', 'in', product_rcs.ids), ('id', 'not in', label_used_ids)])
                label_ids = [x.id for x in label_rcs]
                
            arg_1 = label_ids
                
        return arg0, arg1, arg_1
    


class stock_valuation(models.Model):
    """ 
    Valuation 
    """
    _inherit = 'stock.valuation'
    
    def _supply_method_get(self):
        res = super(stock_valuation, self)._supply_method_get()
        res.append(('produce', _('Produce')))
        return res
    
    

class stock_valuation_lot(models.Model):
    """ 
    Valuation 
    """
    _inherit = 'stock.valuation.lot'
    
    def _supply_method_get(self):
        res = super(stock_valuation_lot, self)._supply_method_get()
        res.append(('produce', _('Produce')))
        return res
    
    
    
class procurement_order(models.Model):
    """ 
    Procurement order 
    """
    _inherit = 'procurement.order'
    
    
    def _supply_method_get(self):
        res = super(procurement_order, self)._supply_method_get()
        res.append(('produce', _('Produce')))
        return res
            
            
    #===========================================================================
    # COLUMNS
    #===========================================================================
    mo_id = fields.Many2one('mrp.manufacturingorder', string='MO', required=False, ondelete='set null', copy=False, select=True)
    origin_wo_id = fields.Many2one('mrp.workorder', string='Origin WO', required=False, ondelete='set null', copy=False, select=True)
    consider_mo = fields.Boolean(string='Consider MO', default=lambda self:self.env['stock.config.settings'].get_param('procurement_consider_mo'))

    
    def get_draft_qtys(self, action=False):
        """
            Calcul de la quantité à commander pour les procurement
            Quantité du procurement - stock virtuel - OF brouillon avec un minimum de 0 et un maximum à la quantité du procurement
        """
        res = super(procurement_order, self).get_draft_qtys(action)
        if action == 'mo' and self.consider_mo and self.trigger_supply != 'make_to_order':
            res = self.product_id.get_draft_mo_qty()

        return res


#     def get_proc_to_compute_by_move(self):
#         """
#             Renvoie tous les procurement comme déclencheur un mouvement avec la même ligne de vente que le mouvement déclencheur
#         """
#         if self.move_id and self.move_id.wo_incoming_id:
#             res = self.search([('move_id.wo_incoming_id', '=', self.move_id.wo_incoming_id.id)])
#         else:
#             res = super(procurement_order, self).get_proc_to_compute()
#             
#         return res


#     def get_proc_to_compute(self):
#         """
#             Renvoie tous les procurement ayant l'OT du déclencheur
#         """
#         if self.origin_wo_id:
#             res = self.search([('move_id', '=', self.move_id.id)])
#         else:
#             res = super(procurement_order, self).get_proc_to_compute()
#             
#         return res


    def test_override_stock(self):
        return False
    

    def do_default_procurement(self, overwrite=True):
        """
            OF automatique
        """
        res = super(procurement_order, self).do_default_procurement(overwrite=overwrite)
        # Si pas de transfert d'entrepôt et produit fabriqué: Création OF
        if (not res or self.test_override_stock()) and self.supply_method == 'produce':
            if overwrite or not self.mo_id:
                mo = self.create_mo()
                config_obj = self.env['stock.config.settings']
                if mo and config_obj.get_param('is_auto_planning') and self.from_mrp:
                    self.env['mrp.workorder'].plannification_mo_at_the_latest(
                                  self.needed_date and self.needed_date + ' 00:00:00' or False, 
                                  mo, 
                                  is_sublevel=config_obj.get_param('is_sublevel'), 
                                  is_procur_level_manufact=config_obj.get_param('is_procur_level_manufact'),
                                  is_product_sublevel_manufact=config_obj.get_param('is_product_sublevel_manufact'),
                                  is_procur_level_purchase=config_obj.get_param('is_procur_level_purchase'),
                                  automatic_purchase=config_obj.get_param('automatic_purchase'),
                                  is_procur_sublevel_purchase=config_obj.get_param('is_procur_sublevel_purchase'), 
                                  change_resources = config_obj.get_param('change_resources'), 
                                  first_pass=True, no_modif_prio_date=False)
                    
        return res
    
    
    def get_properties(self):
        res = super(procurement_order, self).get_properties()
        if self.move_id and self.move_id.parameter_ids:
            res += self.move_id.parameter_ids[0].property_ids
            
        return res
    

    def update_procurement_deleted(self):
        """
            Passage du booléen procurement_deleted à False
        """
        if self.mo_id and self.mo_id.procurement_deleted:
            self.mo_id.write({'procurement_deleted': False})
        else:
            super(procurement_order, self).update_procurement_deleted()
            
        return False
    
    
    def do_action_on_cancel(self):
        """
            Suppression de l'OF si l'état est brouillon ou annulé. Sinon passage du booléen procurement_deleted à True
        """
        if self.mo_id:
            mo_state = self.mo_id.read(['state'])[0]['state']
            if mo_state == 'waiting':
                self.mo_id.wkf_cancel()
                mo_state = self.mo_id.read(['state'])[0]['state']
                
            if mo_state in ('draft', 'cancel'):
                self.mo_id.unlink()
            else:
                self.mo_id.write({'procurement_deleted': True})
        
        return super(procurement_order, self).do_action_on_cancel()

    
    def do_action_on_unlink(self, with_raise=False):
        """
            Delete de l'OF
        """
        self_copy = self
        for proc in self:
            if proc.mo_id:
                # Si avec raise, la suppression de l'OT déclanche l'erreur au cas ou il n'est ni draft ni cancel
                if with_raise or proc.mo_id.state in ('draft', 'cancel'):
                    proc.mo_id.unlink()
                # Si l'OF provient du CBN on le supprime même si son état est waiting
                elif proc.from_procurement and proc.mo_id.state == 'waiting':
                    proc.mo_id.button_del_mo_and_son_mo()
                # Si pas de raise et que l'OT est dans un autre état: procurement est enlevé de la liste à supprimer
                else:
                    self_copy -= proc
            
        return super(procurement_order, self_copy).do_action_on_unlink(with_raise=with_raise)
    
    
    def _get_product(self, proc):
        return proc.product_id
    
    
    def _get_option_ids(self, proc):
        if len(proc.origin_wo_id):
            return proc.origin_wo_id.mo_id.option_ids
        else:
            option_ids = [x.option_id.id for x in proc.sol_id.option_lines_ids]
            return self.env['mrp.option'].browse(option_ids)
    
    
    def _get_variant_value_ids(self, proc):
        return []
    
    
    def _get_parameters(self, proc):
        dimensions = proc.sol_id.parameter_ids
        return [(0,0,{'name': dim.name, 
                      'type_param_id': dim.type_param_id.id,
                      'value': dim.value}) for dim in dimensions]


    def create_mo_update_other_wo_data(self):
        res = {}
        if self.origin_wo_id and self.origin_wo_id.mo_id:
            res['is_use_kit'] = self.origin_wo_id.mo_id.is_use_kit
            
        return res

    
    def create_wo_update_other_wo_data(self):
        return {}
    
    
    def do_action_on_mo_create(self, mo):
        return True
    
    
    def test_create_wo(self):
        return True
    
    
    def test_create_without_qty(self):
        return False
    

    @api.multi
    def create_mo(self):
        """
            Création de l'OF à partir du procurement
        """
        mo_obj = self.env['mrp.manufacturingorder']
        wo_obj = self.env['mrp.workorder']
        move_obj = self.env['stock.move']
        mo = False
        for proc in self:
            try:
                with self.env.cr.savepoint():
                    if proc.is_forecast:
                        move_proc_qty = proc.move_id.get_product_uom_qty()
                        qty = min (move_proc_qty, max(0, - proc.product_id.get_available_stock(is_forecast=True)))
                    else:
                        qty = proc.compute_qty_to_procure('mo')
                    
                    if qty > 0 or self.test_create_without_qty():
                        if qty < 0:
                            qty = 0.0
                            
                        max_date = proc.origin_wo_id and proc.origin_wo_id.planned_start_date or proc.needed_date
                        other_wo_data = {'requested_date': fields.Date.to_string(fields.Date.from_string(proc.needed_date) - timedelta(days=1)),
                                         'is_forecast': proc.is_forecast,
                                         'max_date': max_date}
                        other_mo_data = {'max_end_date': max_date,
                                         'need_delay_validation': proc.waiting_delay,
                                         'waiting_delay': proc.waiting_delay,
                                         'is_forecast': proc.is_forecast,
                                         'note_origin': proc.name}
                        if proc.move_id.wo_incoming_id:
                            other_mo_data['level'] = proc.move_id.wo_incoming_id.mo_id.level + 1
                        else:
                            other_mo_data['level'] = 0
                        
                        if proc.move_id.sale_line_id:
                            other_mo_data['sale_line_id'] = proc.move_id.sale_line_id.id or proc.sale_line_id.id 
                            other_mo_data['max_end_date'] = proc.move_id.sale_line_id.departure_date
                            other_wo_data['max_date'] = proc.move_id.sale_line_id.departure_date
                            other_mo_data['note_planned'] = proc.move_id.sale_line_id.sale_order_id.work_note
                            other_mo_data['note_manufacturing'] = proc.move_id.sale_line_id.work_note
                        elif proc.sol_id:
                            other_mo_data['sale_line_id'] = proc.sol_id.id
                        # Gestion du cas des clients seuls
                        elif proc.move_id.wo_incoming_id:
                            mo_rs = proc.move_id.wo_incoming_id.mo_id
                            if mo_rs and mo_rs.customer_id:
                                other_mo_data['customer_id'] = mo_rs.customer_id.id
                            
                        product_id = self._get_product(proc)
                        other_wo_data.update(proc.create_wo_update_other_wo_data())
                        other_mo_data.update(proc.create_mo_update_other_wo_data())
                        option_ids = self._get_option_ids(proc)
                        variant_values = self._get_variant_value_ids(proc)
                        parameter_ids = self._get_parameters(proc)
                        if self.test_create_wo():
                            creation_res = wo_obj.create_mo_and_wo(
                                product_id, 
                                qty_mo=qty, 
                                other_wo_data=other_wo_data,
                                other_mo_data=other_mo_data,
                                other_data_last_move={'procurement_id': proc.id},
                                with_raise=True,
                                options=option_ids,
                                variant_values=variant_values,
                                parameters=parameter_ids
                            )
                        else:
                            creation_res = mo_obj.create_mo(
                                product_id, 
                                quantity=qty, 
                                other_data=other_mo_data, 
                                with_raise=True, 
                                options=option_ids, 
                                variant_values=variant_values, 
                                parameters=parameter_ids
                            )
                        mo = creation_res and creation_res[0]
                        proc.do_action_on_mo_create(mo)
                        if mo:
                            proc.write({'mo_id': mo.id, 
                                        'uom_qty': qty, 
                                        'uom_id': proc.product_id.uom_id.id})
                            proc.wkf_progress()
                    else:
                        proc.update_delay(fields.Date.today(), with_raise=False)
                        if proc.state in ('draft', 'exception'):
                            if move_obj.search([('state', 'not in', ('done', 'cancel')),
                                                ('type', '=', 'out'),
                                                ('procurement_id', '=', proc.id)], limit=1):
                                proc.wkf_progress()
                            else:
                                proc.wkf_done()
                         
            except Exception as e:
                error = ''
                if e and isinstance(e.args, tuple):
                    for i in e.args:
                        if error:
                            error = '%s\n%s'%(error, i)
                        else:
                            error = i
                    
                    proc.write({'error': error, 'state': 'exception'})
                        
        return mo
    
        
    @api.multi
    def unlink_mo(self):
        for proc in self:
            if proc.mo_id:
                proc.mo_id.unlink()

        

class quality_control_declaration(models.Model):
    """ 
        Quality Control Declaration
    """
    _inherit = 'quality.control.declaration'
    
    def control_link_move_wo(self, type_declaration, move_init_rcs, control, wo_rcs):
        res = super(quality_control_declaration, self).control_link_move_wo(type_declaration, move_init_rcs, control, wo_rcs)
        if type_declaration == 'intern':
            res['wo_id'] = wo_rcs and wo_rcs.id or False
        
        return res
    
    
    @api.multi
    def validate(self):
        res = super(quality_control_declaration, self).validate()
        for declaration in self:
            wdp_rcs = self.env['wo.declaration.produce'].search([('control_declaration_id', '=', declaration.id)], limit=1)
            if wdp_rcs:
                wdp_rcs.write({'qty_hs': declaration.qty_hs,
                               'qty_ok': declaration.qty_ok,
                               'qty_quarantine': declaration.qty_quarantine})
        
        return res



class quality_control_declaration_line_result(models.Model):
    """ 
        Quality Control Declaration Lines Result
    """
    _inherit = 'quality.control.declaration.line.result'
    _description = 'Quality Control Declaration Lines Result'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wo_id = fields.Many2one('mrp.workorder', string='WO', required=False, ondelete='cascade')
    wo_produce_id = fields.Many2one('mrp.wo.produce', string='Production declaration', required=False, ondelete='cascade')



class nonconformity_file(models.Model):
    """ 
        Nonconformity File 
    """
    _inherit = 'nonconformity.file'
    #===========================================================================
    # COLUMNS
    #===========================================================================
    complaint_id = fields.Many2one('mrp.rl.complaint', string='Complaint', required=False, ondelete='restrict')
    
    @api.model
    def _origin_type_get(self):
        res = super(nonconformity_file, self)._origin_type_get()
        if res:
            res.append(('complaint', _('Complaint')))
        
        return res
    
    

class stock_label_traceability(models.Model):
    """
    Label traceability
    """
    _name = 'stock.label.traceability'
    _description = 'Label traceability'
    _rec_name = 'from_label_id'
    _order = 'level'

    #===========================================================================
    # COLUMNS
    #===========================================================================
    from_label_id = fields.Many2one('stock.label', string='Label', required=False, ondelete='cascade')
    from_lot_id = fields.Many2one('stock.lot', string='Lot', required=False, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product')
    level = fields.Integer(default=0, required=False)
    parent_id = fields.Many2one('stock.label.traceability', string='Parent', required=False, ondelete='cascade')
    # Initial
    initial_label_id = fields.Many2one('stock.label', string='Initial label', required=False, ondelete='cascade')
    initial_lot_id = fields.Many2one('stock.lot', string='Initial lot', required=False, ondelete='cascade')
    initial_origin = fields.Char(size=128, required=False)
    initial_date = fields.Datetime()
    initial_quantity = fields.Float(default=0.0, digits=dp.get_precision('Product quantity'), required=False)
    # Actuel
    label_id = fields.Many2one('stock.label', string='Label', required=False, ondelete='cascade')
    lot_id = fields.Many2one('stock.lot', string='Lot', required=False, ondelete='cascade')
    origin = fields.Char(size=128, required=False)
    quantity = fields.Float(default=0.0, digits=dp.get_precision('Product quantity'), required=False)
    date = fields.Datetime()


    def prepare_line(self, datas, origin, final_label_id=False, final_lot_id=False, level=0, parent_rc=False):
        res = {
            'from_label_id': final_label_id, 
            'from_lot_id': final_lot_id, 
            'product_id': datas['product_id'], 
            'level': level, 
            'parent_id': parent_rc and parent_rc.id or False,
            'initial_origin': origin, 
            'initial_date': datas['move_date'],
            'initial_quantity': datas['qty'], 
            'initial_label_id': datas.get('label_id', False),
            'initial_lot_id': datas.get('lot_id', False),
            'origin': origin, 
            'date': datas['move_date'],
            'quantity': datas['qty'], 
            'label_id': datas.get('label_id', False),
            'lot_id': datas.get('lot_id', False),
        }
        return res
    
    
    def get_additional_clause(self):
        return ''
        
    
    def unlink_childs(self):
        child_rcs = self.search([('parent_id', 'in', self.ids)])
        if child_rcs:
            child_rcs.unlink()
            res = True
        else:
            res = False
                        
        return res
        

    def get_label_origin(self, label_id, order='asc'):
        """
            Retourne les informations de du premier ou dernier mouvement d'origine de l'étiquette
            :type self: stock.label.traceability
            :param order: asc pour le premier ou desc pour le dernier mouvement
            :type order: char
            :return: Id du mouvement, id de l'OT, id de l'OF, nom de l'achat, quantité du move_label
            :rtype: tuple
        """
        # Premier/Dernier mouvement IN ou terminé pour l'étiquette
        self.env.cr.execute('''
            SELECT
                sm.id as move_id,
                sm.date as move_date,
                sm.product_id as product_id,
                prod.id as prod_id,
                wo.id as wo_id,
                mo.id as mo_id,
                mo.name as mo_name,
                po.name as po_name,
                sml.uom_qty as qty,
                sml.label_id as label_id,
                picking.name as picking_name
            FROM
                stock_move sm
                JOIN stock_move_label sml ON sml.move_id = sm.id
                JOIN stock_label sl ON sml.label_id = sl.id
                LEFT OUTER JOIN purchase_order_line pol ON sm.purchase_line_id = pol.id
                LEFT OUTER JOIN purchase_order po ON pol.purchase_order_id = po.id 
                LEFT OUTER JOIN mrp_wo_produce prod ON sm.wo_produce_id = prod.id
                LEFT OUTER JOIN mrp_workorder wo ON prod.wo_id = wo.id
                LEFT OUTER JOIN mrp_manufacturingorder mo on wo.mo_id = mo.id
                LEFT OUTER JOIN stock_picking picking ON sm.picking_id = picking.id
            WHERE
                %s
                (sm.purchase_line_id IS NOT NULL OR sm.wo_produce_id IS NOT NULL) AND
                sm.state = 'done' AND
                sm.type = 'in' AND
                label_id = %s
            ORDER BY
                sm.date %s
            LIMIT 1
        '''%(self.get_additional_clause(), label_id, order))
        return self.env.cr.dictfetchone()
        

    def get_lot_origin(self, lot_id, order='asc'):
        """
            Retourne les informations de du premier ou dernier mouvement d'origine de l'étiquette
            :type self: stock.label.traceability
            :param order: asc pour le premier ou desc pour le dernier mouvement
            :type order: char
            :return: Id du mouvement, id de l'OT, id de l'OF, nom de l'achat, quantité du move_label
            :rtype: tuple
        """
        # Premier/Dernier mouvement IN ou terminé pour l'étiquette
        self.env.cr.execute('''
            SELECT
                sm.id as move_id,
                sm.date as move_date,
                sm.product_id as product_id,
                prod.id as prod_id,
                wo.id as wo_id,
                mo.id as mo_id,
                mo.name as mo_name,
                po.name as po_name,
                sm.uom_qty as qty,
                sml.lot_id as lot_id,
                picking.name as picking_name
            FROM
                stock_move sm
                JOIN stock_move_lot sml ON sml.move_id = sm.id
                JOIN stock_lot sl ON sml.lot_id = sl.id
                LEFT OUTER JOIN purchase_order_line pol ON sm.purchase_line_id = pol.id
                LEFT OUTER JOIN purchase_order po ON pol.purchase_order_id = po.id 
                LEFT OUTER JOIN mrp_wo_produce prod ON sm.wo_produce_id = prod.id
                LEFT OUTER JOIN mrp_workorder wo ON prod.wo_id = wo.id
                LEFT OUTER JOIN mrp_manufacturingorder mo on wo.mo_id = mo.id
                LEFT OUTER JOIN stock_picking picking ON sm.picking_id = picking.id
            WHERE
                %s
                (sm.purchase_line_id IS NOT NULL OR sm.wo_produce_id IS NOT NULL) AND
                sm.state = 'done' AND
                sm.type = 'in' AND
                lot_id = %s
            ORDER BY
                sm.date %s
            LIMIT 1
        '''%(self.get_additional_clause(), lot_id, order))
        return self.env.cr.dictfetchone()
    
    
    def after_build_traceability(self, label_rc=False, lot_rc=False):
        return True
    
    
    def compute_traceability(self):
        for label_traceability in self:
            self.unlink_childs()
            self.build_traceability(
                label_rc=label_traceability.label_id, 
                lot_rc=label_traceability.lot_id, 
                final_label_rc=label_traceability.from_label_id, 
                final_lot_rc=label_traceability.from_lot_id, 
                level=label_traceability.level, 
                parent_rc=label_traceability, 
                without_first=True
            )
            
        return True
     
    
    def build_traceability(self, label_rc=False, lot_rc=False, final_label_rc=False, final_lot_rc=False, level=0, label_already_treated=None, lot_already_treated=None, parent_rc=False, without_first=False):
        """
            Construit les lignes de traçabilité de l'étiquette passée en paramètre
            :type self: stock.label.traceability
            :param label_rc: Étiquette dont la traçabilité doit être contstruite
            :type label_rc: recordset: stock.label
            :return: True
            :rtype: boolean
        """
        existing_line_rc = False
        if not final_label_rc:
            final_label_rc = label_rc
            
        if not final_lot_rc:
            final_lot_rc = lot_rc
        
        if not label_already_treated:
            label_already_treated = []
        elif label_rc.id not in label_already_treated:
            label_already_treated.append(label_rc.id)
            
        if not lot_already_treated:
            lot_already_treated = []
        elif lot_rc.id not in lot_already_treated:
            lot_already_treated.append(lot_rc.id)
        
        prod_obj = self.env['mrp.wo.produce']
        # Récupération du premier mouvement entrant pour cette étiquette / ce lot
        if label_rc:
            last_datas = self.get_label_origin(label_rc.id, order='asc')
        
        elif lot_rc:
            last_datas = self.get_lot_origin(lot_rc.id, order='asc')
            existing_line_rc = self.search([('from_label_id', '=', final_label_rc.id), ('initial_lot_id', '=', lot_rc.id)], limit=1)
                            
        if last_datas:
            # Si l'étiquette provient d'une production:
            if last_datas['prod_id']:
                name = last_datas['mo_name']
                if not without_first:
                    if existing_line_rc:
                        existing_line_rc.write({'origin': name, 'initial_origin': name})
                        parent_rc = existing_line_rc
                    else:
                        parent_rc = self.create(self.prepare_line(last_datas, name, final_label_rc and final_label_rc.id, final_lot_rc and final_lot_rc.id, level=level, parent_rc=parent_rc))
                    
                consumption_rc = prod_obj.browse(last_datas['prod_id']).get_corresponding_consumption()
                if consumption_rc:
                    for move_rc in consumption_rc.move_ids:
                        if move_rc.move_label_ids:
                            for move_line in move_rc.move_label_ids:
                                if move_line.label_id.id not in label_already_treated:
                                    new_label_already_treated, new_lot_already_treated = self.build_traceability(
                                        label_rc=move_line.label_id, 
                                        final_label_rc=final_label_rc, 
                                        final_lot_rc=final_lot_rc, 
                                        level=level+1, 
                                        label_already_treated=label_already_treated, 
                                        lot_already_treated=lot_already_treated, 
                                        parent_rc=parent_rc
                                    )
                                    label_already_treated.extend(new_label_already_treated)
                                    lot_already_treated.extend(new_lot_already_treated)
                                    
                        elif move_rc.move_lot_ids:
                            for move_line in move_rc.move_lot_ids:
                                if move_line.lot_id.id not in lot_already_treated:
                                    self.create({
                                        'from_label_id': final_label_rc and final_label_rc.id, 
                                        'from_lot_id': final_lot_rc and final_lot_rc.id, 
                                        'product_id': move_rc.product_id.id, 
                                        'level': level+1, 
                                        'parent_id': parent_rc and parent_rc.id or False,
                                        'initial_date': move_rc.date,
                                        'initial_quantity': move_rc.uom_qty, 
                                        'initial_lot_id': move_line.lot_id.id,
                                        'date': move_rc.date,
                                        'quantity': move_rc.uom_qty, 
                                        'lot_id': move_line.lot_id.id
                                    })
                                    new_label_already_treated, new_lot_already_treated = self.build_traceability(
                                        lot_rc=move_line.lot_id, 
                                        final_label_rc=final_label_rc, 
                                        final_lot_rc=final_lot_rc, 
                                        level=level+1, 
                                        label_already_treated=label_already_treated, 
                                        lot_already_treated=lot_already_treated, 
                                        parent_rc=parent_rc
                                    )
                                    label_already_treated.extend(new_label_already_treated)
                                    lot_already_treated.extend(new_lot_already_treated)
                                
            elif not without_first:
                if last_datas['po_name']:
                    name = last_datas['po_name']
                    if existing_line_rc:
                        existing_line_rc.write({'origin': name, 'initial_origin': name})
                        parent_rc = existing_line_rc
                    else:
                        parent_rc = self.create(self.prepare_line(last_datas, name, final_label_rc and final_label_rc.id, final_lot_rc and final_lot_rc.id, level=level))
                        
                elif last_datas['picking_name']:
                    name = last_datas['picking_name']
                    if existing_line_rc:
                        existing_line_rc.write({'origin': name, 'initial_origin': name})
                        parent_rc = existing_line_rc
                    else:
                        parent_rc = self.create(self.prepare_line(last_datas, name, final_label_rc and final_label_rc.id, final_lot_rc and final_lot_rc.id, level=level))
                else:
                    name = ''
                    if existing_line_rc:
                        parent_rc = existing_line_rc
                    else:
                        parent_rc = self.create(self.prepare_line(last_datas, name, final_label_rc and final_label_rc.id, final_lot_rc and final_lot_rc.id, level=level))
            
            # Gestion des OF de SAV => commenté car géré directement dans le module SAV
#             # Récupération du dernier mouvement entrant pour cette étiquette
#             first_datas = self.get_label_origin(label_rc.id, order='desc')
#             if first_datas:
#                 if first_datas['prod_id']:
#                     name = first_datas['mo_name']
#                 elif first_datas['po_name']:
#                     name = first_datas['po_name']
#                 elif first_datas['picking_name']:
#                     name = first_datas['picking_name']
#                 else:
#                     name = ''
# 
#                 vals.update(self.prepare_line(first_datas, name, final_label_rc.id, initial=False, level=level))

            
        return label_already_treated, lot_already_treated