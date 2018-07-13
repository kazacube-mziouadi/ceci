# -*- coding: utf-8 -*-
from openerp import models, api, fields
from openerp.tools.translate import _



class purchase_order(models.Model):
    _inherit = 'purchase.order'
    @api.multi
    def action_progress_purchase_state(self):
        res = super(purchase_order, self).action_progress_purchase_state()
        for po in self:
            for pol in po.purchase_order_line_ids:
                pol.do_action_on_line_cancel()
                
        return res
    
    

class purchase_order_line(models.Model):
    _inherit = 'purchase.order.line'

    @api.model
    def _type_subcontracting_get(self):
        return [
                ('direct', 'Direct'),
                ('indirect', 'Indirect'),
                ('stock', 'Stock'),
                       ]
        

    #===========================================================================
    # COLUMNS
    #===========================================================================
    wo_rm_subcontracting_id = fields.Many2one('mrp.workorder', string='WO RM Subc.', required=False, ondelete='restrict')
    wo_fp_subcontracting_id = fields.Many2one('mrp.workorder', string='WO FP Subc.', required=False, ondelete='restrict')
    wo_qty = fields.Float(string='Wo qty', default=0.0, required=False)
    type_subcontracting = fields.Selection('_type_subcontracting_get', default='direct', string='Type Subc.')
    subc_origin_move_id = fields.Many2one('stock.move', string='Origin subcontracting move', required=False, ondelete='restrict', copy=False)

    
    #===========================================================================
    # Boutons
    #===========================================================================
    @api.multi
    def button_open_achat(self):
        for line in self:
            action = self.env.ref('mrp.act_purchase_order_open_button')
            if action:
                action = action.read()[0]
                if action.get('views'):
                    for index,item in enumerate(action['views']):
                        if item[-1] == 'form':
                            del action['views'][index]
                            action['views'].insert(0, item)
                            
                action['res_id'] = line.purchase_order_id.id
                action['view_mode'] = 'form'
                
            return action
    
    
    #===========================================================================
    # Fonction
    #===========================================================================
    def move_other_data_subcontracting(self, move_other_data):
        """
            Fonction qui permet de rajouter des champs pour la création d'un mouvement lors dans de la validation de l'achat de soustraitance
            :param move_other_data: Un dico contenant les champs pour la création d'un mouvement lors de la validation d'un achat
            :type move_other_data: boolean
            :return: La lignee d'achat créée
            :rtype: recordset purchase.order.line
        """
        res = super(purchase_order_line, self).move_other_data_subcontracting(move_other_data)
        if self.wo_rm_subcontracting_id:
            res.update({'wo_rm_subcontracting_id': self.wo_rm_subcontracting_id.id,
                        'type_subcontracting': self.type_subcontracting,
                        'subc_origin_move_id': self.subc_origin_move_id.id})
        elif self.wo_fp_subcontracting_id:
            res.update({'wo_fp_subcontracting_id': self.wo_fp_subcontracting_id.id,
                        'type_subcontracting': self.type_subcontracting})
        
        return res
    
    
    def do_action_on_line_cancel(self):
        res = super(purchase_order_line, self).do_action_on_line_cancel()
        if self.wo_fp_subcontracting_id:
            self.wo_fp_subcontracting_id.compute_subcontracting_counterpart_move()
            
        return res
    
    
    def create_move_pf_st(self, picking_rcs, currency_id, supplier_info):
        """
            Function pour la Soustraitance pour la création des réceptions des produits finis lors de la génération de picking pour la confirmation d'achat 
            :type self: purchase.order.line
            :param picking_rcs: Le Bon de réception
            :type picking_rcs: recordset: stock.picking
            :param currency_id: La Devise
            :type currency_id: recordset: res.currency
            :param supplier_info: Le supplier_info
            :type supplier_info: recordset: product.supplierinfo
            :return: True
        """
        move_obj = self.env['stock.move']
        if self.wo_fp_subcontracting_id:
            cosumed_service_rcs = self.env['mrp.wo.consumed.service'].search([('wo_id', '=', self.wo_fp_subcontracting_id.id), ('product_id', '=', self.product_id.id)], limit=1)
            if cosumed_service_rcs and cosumed_service_rcs.is_fp:
                if self.confirmed_date:
                    date = self.confirmed_date
                else:
                    date = self.expected_date

                move_other_data = {
                   'sequence': self.sequence,
                   'purchase_line_id': self.id,
                   'date_expected': self.confirmed_date,
                   'date': self.confirmed_date,
                   'priority_date': self.confirmed_date,
                   'note': self.internal_note,
                   'partner_price': 0.00,
                   'currency_id': currency_id,
                   'sinfo_id': supplier_info and supplier_info.id or False,
                   'date_expected': date,
                   'date': date,
                   'priority_date': date,
                   'origin': self.name_get()[0][1]}
                move_other_data = self.move_other_data_subcontracting(move_other_data)
                    
                picking_rcs.write({'origin': self.wo_fp_subcontracting_id.name_get()[0][-1]})  
                transfer_obj = self.env['stock.transfer.request']
                for move_pf in self.wo_fp_subcontracting_id.fp_draft_ids:
                    uom_qty = move_pf.efficient_unit_qty * self.wo_qty
                    move_other_data_move_pf = {
                       'name': move_pf.name,
                       'uom_id': move_pf.uom_id.id,
                       'initial_uom_qty': uom_qty,
                       'sec_uom_id': move_pf.sec_uom_id.id,
                       'uoi_id': move_pf.uoi_id.id,
                       'factor': move_pf.factor,
                       'divisor': move_pf.divisor,
                       'efficient_unit_qty': move_pf.efficient_unit_qty, 
                       'is_not_billable': True}
                    move_other_data_move_pf.update(move_other_data)
                    dst_location = self.purchase_order_id and self.purchase_order_id.location_id  or False
                    #On récupère l'emplacement de sous-traitance
                    src_location = self.wo_fp_subcontracting_id and self.wo_fp_subcontracting_id.first_resource_id and self.wo_fp_subcontracting_id.first_resource_id.location_id or False
                    if not src_location:
                        src_location = self.purchase_order_id.company_id and self.purchase_order_id.company_id.warehouse_id.supplier_location_id or False
                        
                    transfer_rs = transfer_obj.create({'product_id': move_pf.product_id.id,
                                                       'origin': self.wo_fp_subcontracting_id.name_get()[0][-1],
                                                       'warehouse_id': src_location.warehouse_id.id,
                                                       'warehouse_dest_id': dst_location.warehouse_id.id,
                                                       'uom_qty': uom_qty,
                                                       'uom_id': move_pf.uom_id.id,
                                                       'needed_uom_qty': uom_qty,
                                                       'needed_uom_id': move_pf.uom_id.id,
                                                       'need_date': date,
                                                       'is_automatic': True,
                                                       'departure_date': date})
                    out_picking_rs = transfer_rs.create_transfer_picking(without_waiting=True)
                    if out_picking_rs and out_picking_rs.move_ids:
                        transit_location = out_picking_rs.move_ids[0].location_dest_id
                        move_other_data_move_pf['transfer_id'] = transfer_rs.id
                        move_rs = move_obj.create_move(move_pf.product_id, qty=uom_qty, type='in', other_data=move_other_data_move_pf, 
                                                       picking=picking_rcs, uom=move_pf.uom_id, sec_uom=move_pf.sec_uom_id, dst_location=dst_location.id, 
                                                       src_location=transit_location.id, in_product_uom=True)
                        out_picking_rs.move_ids.write({'transfer_move_id': move_rs.id})
                        out_picking_rs.wkf_waiting()
        
        if self.wo_rm_subcontracting_id:
            picking_rcs.write({'origin': self.wo_rm_subcontracting_id.name_get()[0][-1]})
             
        return True

    
    @api.multi
    def write(self, vals=None):
        """
            On Crée un action suite à changement de date d'une ligne d'achat de soustraitance d'un produit finit pour informer qu'il faudra peut être modifier les dates dans l'ot
        """
        if not vals:
            vals = {}
        
        modif_date = False
        if 'expected_date' in vals:
            modif_date = True
            
        res = super(purchase_order_line, self).write(vals)
        for pol in self:
            if pol.wo_fp_subcontracting_id and modif_date:
                name_action = _('Warning Change Date Purchase Order Line %s')%(pol.name_get()[0][1])
                action_obj = self.env['calendar.event']
                description_warn_st = _('Warning WO ST new date %s')%(pol.expected_date)
                affected_user_id = pol.wo_fp_subcontracting_id.final_product_id and pol.wo_fp_subcontracting_id.final_product_id.production_manager_id and self.wo_fp_subcontracting_id.final_product_id.production_manager_id.id or self.env.user.id
                action_obj.create({ 'name': name_action,
                                    'requested_by_user_id': self.env.user.id,
                                    'affected_user_id': affected_user_id,
                                    'workorder_id':pol.wo_fp_subcontracting_id.id,
                                    'date': fields.Date.today(),
                                    'description': description_warn_st,
                                   })
                   
        return res