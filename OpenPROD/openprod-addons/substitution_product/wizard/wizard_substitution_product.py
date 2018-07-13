# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
from openerp.addons.base_openprod import utils
import time, datetime
import openerp.addons.decimal_precision as dp

class wizard_substitution_product(models.TransientModel):
    """ 
        Wizard substitution product
    """
    _name = 'wizard.substitution.product'
    _description = 'Change Date Wo'
    
    @api.model
    def default_get(self, fields_list):
        res = super(wizard_substitution_product, self).default_get(fields_list=fields_list)
        vals = {}
        #Si on est dans l'ot sur les mouvements de matières premières
        if self._context.get('active_model') == 'stock.move':
            move = self.env['stock.move'].browse(self._context.get('active_id'))
            component_id = move.component_id and move.component_id.id or False
            move_product_id = move.product_id and move.product_id.id or False
            vals = {
                'move_id': move.id,
                'component_id': component_id,
                'move_product_id': move_product_id,
                'partner_invisible': True,
            }
            
            pol_rcs = self.env['purchase.order.line'].search([('subc_origin_move_id', '=', move.id)], limit=1)
            if pol_rcs:
                vals['is_subcontracting'] = True
                vals['pol_id'] = pol_rcs.id
            
            
        # Si on est sur la ligne d'achat de l'appro de la matière première ou achat de ST
        elif self._context.get('active_model') == 'purchase.order.line':
            component_id = False
            move_product_id = False
            move_id = False
            is_subcontracting = False
            pol_id = self._context.get('active_id')
            pol = self.env['purchase.order.line'].browse(self._context.get('active_id'))
            if pol.purchase_order_id.state == 'draft':
                # Partie soustraitance PF
                if pol.wo_fp_subcontracting_id:
                    component_id = False
                    move_product_id = False
                    move_id = False
                    is_subcontracting = True
                # Partie soustraitance MP
                elif pol.wo_rm_subcontracting_id:
                    component_id = pol.subc_origin_move_id and pol.subc_origin_move_id.component_id and pol.subc_origin_move_id.component_id.id or False
                    move_product_id = pol.subc_origin_move_id and pol.subc_origin_move_id.product_id and pol.subc_origin_move_id.product_id.id or False
                    move_id = pol.subc_origin_move_id and pol.subc_origin_move_id.id or False
                    is_subcontracting = True
                # Partie MP
                else:
                    procurement = self.env['procurement.order'].search([('pol_id', '=', pol.id), ('origin_wo_id', '!=', False), ('move_id', '!=', False)], limit=1)
                    if procurement:
                        component_id = procurement.move_id and procurement.move_id.component_id and procurement.move_id.component_id.id or False
                        move_product_id = procurement.product_id and procurement.product_id.id or False
                        move_id = procurement.move_id and procurement.move_id.id or False
                        
                if move_product_id and component_id and move_id:
                    vals = {
                        'move_id': move_id,
                        'component_id': component_id,
                        'move_product_id': move_product_id,
                        'partner_invisible': False,
                        'is_subcontracting': is_subcontracting,
                        'pol_id': pol_id
                    }
                else:
                    raise except_orm(_('Warning'), _('This button changes the raw material for a work order, purchase online this is not related to the supply of a work order.'))
            
            else:
                raise except_orm(_('Warning'), _('Purchase order %s must be draft.')%(pol.purchase_order_id.name))
        
        res.update(vals)
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    move_id = fields.Many2one('stock.move', string='Move', required=True, ondelete='set null')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='set null')
    component_id = fields.Many2one('mrp.bom', string='Component', required=False, ondelete='set null')
    move_product_id = fields.Many2one('product.product', string='Move product', required=False, ondelete='set null')
    partner_id = fields.Many2one('res.partner', string='Partner', required=False, ondelete='set null')
    partner_invisible = fields.Boolean(string='Partner invisible')
    is_subcontracting = fields.Boolean(string='Is subcontracting', default=False)
    pol_id = fields.Many2one('purchase.order.line', string='POL', required=False, ondelete='set null')
    
    #===========================================================================
    # Bouton
    #===========================================================================
    @api.multi
    def action_validation(self):
        """
            Bouton de validation
        """
        pol_obj = self.env['purchase.order.line']
        po_obj = self.env['purchase.order']
        move_obj = self.env['stock.move']
        for wiz in self:
            # Création du nouveau mouvement
            new_uom_qty = self.env['product.uom']._compute_qty_obj(wiz.move_id.uom_id, wiz.move_id.uom_qty, wiz.product_id.uom_id)
            vals= {'product_id': wiz.product_id.id}
            vals_onchange = wiz.move_id.onchange_product_id(wiz.product_id)
            vals.update(utils.transform_to_ids(wiz.move_id, vals_onchange))
            current_state = wiz.move_id.state
            wiz.move_id.wkf_cancel()
            new_move, move = wiz.move_id.with_context({'procurement_partner_rcs': wiz.partner_id}).wkf_draft()
            if not new_move:
                move = wiz.move_id 
            
            move.write(vals)
            vals_uom_qty = move.onchange_uom_qty(new_uom_qty, move.uom_id, move.sec_uom_id, move.uoi_id, move.dual_unit, move.dual_unit_type, move.factor, move.divisor)
            if 'uom_qty' not in vals_uom_qty:
                vals_uom_qty['uom_qty'] = new_uom_qty
                
            move.write(vals_uom_qty)
            if current_state == 'waiting':
                move.wkf_waiting()
            
            #Si ot non de soutraitance
            if not wiz.is_subcontracting:
                if wiz.pol_id and wiz.pol_id.procurement_deleted and wiz.pol_id.purchase_order_id.state == 'draft':
                    procurement_deleted_pol_rcs = pol_obj.search([('purchase_order_id', '=', wiz.pol_id.purchase_order_id.id)])
                    if len(procurement_deleted_pol_rcs) == 1:
                        wiz.pol_id.purchase_order_id.wkf_cancel()
                        wiz.pol_id.purchase_order_id.unlink()
                    elif len(procurement_deleted_pol_rcs) > 1:
                        wiz.pol_id.unlink()
                
            #Si ot de soutraitance
            elif wiz.is_subcontracting and wiz.pol_id:
                if wiz.product_id:
                    # Création de nouvel achat
                    if wiz.partner_id:
                        partner = wiz.partner_id
                    else:
                        sinfo = wiz.product_id.get_sinfo()
                        if sinfo:
                            partner = sinfo.partner_id
                        else:
                            raise except_orm(_('Warning'), _('There is not supplier for the product %s.')%(wiz.product_id.name))
                            
                    other_data = {}
                    po_line = {move.product_id: {'uom_qty': wiz.pol_id.uom_qty, 
                                                 'uom_id': wiz.pol_id.uom_id.id, 
                                                 'wo_rm_subcontracting_id': wiz.pol_id.wo_rm_subcontracting_id.id, 
                                                 'wo_qty': wiz.pol_id.wo_qty, 
                                                 'type_subcontracting': wiz.pol_id.type_subcontracting,
                                                 'subc_origin_move_id': move.id}}
                    new_purchase = po_obj.create_purchase(partner, po_line, wiz.pol_id.purchase_order_id.expected_date, other_data, 
                                                          first_qty='uom_qty', not_need_qty=True)
                    old_order = wiz.pol_id.purchase_order_id
                    move_rcs = move_obj.search([('purchase_line_id', '=', wiz.pol_id.id), 
                                                ('wo_rm_subcontracting_id', '=', wiz.pol_id.wo_rm_subcontracting_id.id), 
                                                ('type', '=', 'out')])
                    delete_old_move_rcs = move_obj.search([('purchase_line_id', '=', wiz.pol_id.id), 
                                                           ('wo_rm_subcontracting_id', '=', wiz.pol_id.wo_rm_subcontracting_id.id), 
                                                           ('type', '=', 'in')])
                    if move_rcs:
                        # Creation de la nouvelle ligne d'achat
                        new_purchase_order_line_rcs = pol_obj.search([('purchase_order_id', '=', new_purchase.id), ('product_id', '=', move.product_id.id)], limit=1)
                        if new_purchase_order_line_rcs:
                            for old_move in move_rcs:
                                current_state = old_move.state
                                old_move.wkf_cancel()
                                is_new_move, new_move = old_move.wkf_draft()
                                if not is_new_move:
                                    new_move = old_move
                                else:
                                    delete_old_move_rcs += old_move
                                
                                vals_new_move = {'purchase_line_id': new_purchase_order_line_rcs.id, 'product_id': wiz.product_id.id}
                                new_picking = False
                                if old_move.picking_id == new_move.picking_id:
                                    new_picking = old_move.picking_id.copy({'move_ids': []})
                                    vals_new_move['picking_id'] = new_picking.id
                                    
                                new_move.write(vals_new_move)
                                if current_state == 'waiting':
                                    if new_picking:
                                        new_picking.wkf_waiting()
                                    else:
                                        new_move.wkf_waiting()
                    
                    # Suppression de l'ancien achat et des mouvements liés
                    pol_rcs = pol_obj.search([('purchase_order_id', '=', old_order.id)])
                    if len(pol_rcs) == 1:
                        old_order.wkf_cancel()
                        for delete_old_move in delete_old_move_rcs:
                            if delete_old_move.state != 'cancel':
                                delete_old_move.wkf_cancel()
                                
                            delete_old_move.unlink()
                            
                        old_order.unlink()
                    elif len(pol_rcs) > 1:
                        for delete_old_move in delete_old_move_rcs:
                            if delete_old_move.state != 'cancel':
                                delete_old_move.wkf_cancel()
                                
                            delete_old_move.unlink()
                            
                        wiz.pol_id.unlink()
            
        return {'type':'ir.actions.act_window_view_reload'}


    