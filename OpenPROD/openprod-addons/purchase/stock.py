# -*- coding: utf-8 -*-
from openerp import models, api, fields
from openerp.tools.translate import _
from openerp.exceptions import except_orm
from openerp.addons.base_openprod.common import get_form_view


class stock_picking(models.Model):
    _inherit = 'stock.picking'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    purchase_id = fields.Many2one('purchase.order', string='Purchase', required=False, ondelete='restrict')

    
    def manage_sale_purchase_state(self, unlink_picking_ids=False):
        """
            Surcharge de la fonction des picking pour lancer la méthode de
            changement de l'état de l'achat
        """
        res = super(stock_picking, self).manage_sale_purchase_state(unlink_picking_ids)
        for picking in self:
            if picking.purchase_id:
                picking.purchase_id.pass_done_purchase(False, unlink_picking_ids)
            
        return res
    
    

class stock_move(models.Model):
    _inherit = 'stock.move'
    
    def _get_states(self):
        return {'done': [('readonly', True)], 'cancel': [('readonly', True)]} 
       
    #===========================================================================
    # COLUMNS
    #===========================================================================
    purchase_line_id = fields.Many2one('purchase.order.line', string='Purchase line', required=False, ondelete='restrict', select=True)
    sinfo_id = fields.Many2one('product.supplierinfo', string='Supplier info', required=False, ondelete='restrict', states=_get_states)
    
        
    @api.onchange('sinfo_id', 'type')
    def _onchange_sinfo_id(self):
        """
            Au changement du produit, changement des UoM et du nom
        """
        if self.type == 'in' and self.sinfo_id:
            uoms = self.product_id.get_uoms(pinfo=self.sinfo_id, type=self.type, with_factor=True)
            for k, v in uoms.iteritems():
                self[k] = v
                
                
    @api.onchange('product_id', 'type')         
    def _onchange_product_id(self):
        super(stock_move, self)._onchange_product_id()
        if self.product_id:
            self.sinfo_id = self.product_id.get_sinfo()
    
    
    def get_default_attributes(self):
        """
            Méthode redéfinie dans mrp et purchase pour avoir les attributs par défaut changés par 
            les ventes ou les achats.
        """
        res = super(stock_move, self).get_default_attributes()
        if self.purchase_line_id:
            res.update({x.product_common_attribute_id.name: x.value for x in self.purchase_line_id.product_attribute_ids})
            
        return res
    
    
    def update_procurement_vals(self):
        res = super(stock_move, self).update_procurement_vals()
        if self.supply_method == 'buy' and self.product_id.purchase_responsible_id:
            res['responsible_id'] = self.product_id.purchase_responsible_id.id
            
        return res
    
            
    def get_attributes_const(self):
        res = super(stock_move, self).get_attributes_const()
        res.update({
            'pol': self.purchase_line_id,
            'po': self.purchase_line_id.purchase_order_id,
            'supplier': self.purchase_line_id.purchase_order_id.partner_id,
               })
            
        return res
    

    def manage_sale_purchase_qty(self):
        """
            Surcharge de la fonction des moves pour gérer les quantités
            livrées de la ligne d'achat et de l'achat (cancel)
        """
        res = super(stock_move, self).manage_sale_purchase_qty()
        for move in self:
            if move.read(['purchase_line_id'], load='_classic_write')[0]['purchase_line_id']:
                move.purchase_line_id.compute_received_qty()
            
        return res

            
            
class procurement_order(models.Model):
    """ 
    Procurement order 
    """
    _inherit = 'procurement.order'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    pol_id = fields.Many2one('purchase.order.line', string='PoL', required=False, ondelete='set null', select=True)
    consider_purchase = fields.Boolean(string='Consider purchase', default=lambda self:self.env['stock.config.settings'].get_param('procurement_consider_purchase'), help='Consider draft purchases quantities')
    consider_min_multiple = fields.Boolean(string='Consider min and multiple', default=lambda self:self.env['stock.config.settings'].get_param('procurement_consider_min_multiple'), help='Consider minimum and multiple purchase quantities')
 
    
    def get_draft_qtys(self, action=False):
        """
            Calcul de la quantité à commander pour les procurement
            Quantité du procurement - stock virtuel - achats brouillon avec un minimum de 0 et un maximum à la quantité du procurement
        """
        res = super(procurement_order, self).get_draft_qtys(action)
        if action == 'purchase' and self.consider_purchase and self.trigger_supply != 'make_to_order':
            res = self.product_id.get_draft_purchase_qty()

        return res
    
    
    def update_procurement_deleted(self):
        """
            Passage du booléen procurement_deleted à False
        """
        pol_id = self and self.read(['pol_id'], load='_classic_write')[0]['pol_id']
        if pol_id:
            if self.pol_id.procurement_deleted:
                vals = {'can_be_del': False}
                # Flag à false si aucun autre procurement n'est approvisionné par cette ligne (merge d'achat par ex.)
                proc_rs = self.search([('pol_id', '=', self.pol_id.id), 
                                       ('state', '=', 'cancel'),
                                       ('id', '!=', self.id)], limit=1)
                if proc_rs:
                    vals['procurement_deleted'] = True
                else:
                    vals['procurement_deleted'] = False
                    
                self.pol_id.write(vals)
                
            procurement_deleted = False
            purchase_order_rs = self.pol_id.purchase_order_id
            # Si le flag de l'achat est coché alors qu'aucun des flag des lignes n'est coché: On déflag l'achat
            if purchase_order_rs.procurement_deleted:
                for pol_rs in purchase_order_rs.purchase_order_line_ids:
                    if pol_rs.procurement_deleted:
                        procurement_deleted = True
                        break
                
                if not procurement_deleted:
                    self.pol_id.purchase_order_id.write({'procurement_deleted': False})
                
        else:
            super(procurement_order, self).update_procurement_deleted()
            
        return False
    
    
    def do_default_procurement(self, overwrite=True):
        """
            Achat automatique
        """
        res = super(procurement_order, self).do_default_procurement(overwrite=overwrite)
        # Si pas de transfert d'entrepôt et produit fabriqué: Création Achat
        if not res and self.supply_method == 'buy':
            if not self.is_forecast and (overwrite or not self.pol_id):
                self.create_po(partner=self._context.get('procurement_partner_rcs', None))
        
        return res
    
    
    def do_action_on_cancel(self):
        if self.pol_id:
            if self.pol_id.purchase_order_id.state == 'cancel':
                todel = True
            elif self.pol_id.purchase_order_id.state == 'draft':
                vals = {'procurement_deleted': True}
                # Flag à false si aucun autre procurement n'est approvisionné par cette ligne (merge d'achat par ex.)
                proc_rs = self.search([('pol_id', '=', self.pol_id.id), 
                                       ('state', '!=', 'cancel'),
                                       ('id', '!=', self.id)], limit=1)
                if proc_rs:
                    vals['can_be_del'] = False
                else:
                    vals['can_be_del'] = True

                self.pol_id.write(vals)
                if vals['can_be_del']:
                    todel = True
                    for pol_rs in  self.pol_id.purchase_order_id.purchase_order_line_ids:
                        if pol_rs.id != self.pol_id.id and not pol_rs.can_be_del:
                            todel = False
                            break
                        
                else:
                    todel = False
                    
            else:
                todel = False
                
            if todel:
                self.pol_id.purchase_order_id.unlink()
            else:
                self.pol_id.write({'procurement_deleted': True})
                self.pol_id.purchase_order_id.write({'procurement_deleted': True})
                
        return super(procurement_order, self).do_action_on_cancel()
    
    
    def do_action_on_unlink(self, with_raise=False):
        """
            Delete de l'Achat
        """
        self_copy = self
        for proc in self:
            if proc.pol_id:
                # Si avec raise, la suppression du PO déclanche l'erreur au cas ou il n'est ni draft ni cancel
                if with_raise or proc.pol_id.purchase_order_id.state in ('draft', 'cancel'):
                    proc.pol_id.purchase_order_id.unlink()
                # Si pas de raise et que le PO est dans un autre état: procurement est enlevé de la liste à supprimer
                else:
                    self_copy -= proc
                    
        return super(procurement_order, self_copy).do_action_on_unlink(with_raise=with_raise)


    def create_po_update_pol_datas(self):
        return {}
    
    
    def get_properties(self):
        return self.env['purchase.property']
    
    
    @api.multi
    @api.v8
    def create_po(self, partner=None):
        """
            Création de l'achat à partir du procurement
        """
        po_obj = self.env['purchase.order']
        move_obj = self.env['stock.move']
        purchase = False
        for proc in self:
            try:
                with self.env.cr.savepoint():
                    if proc.product_id.free_purchase:
                        properties = []
                        if partner:
                            delivery_delay = proc.product_id.free_supply_delay
                        else:
                            continue
                        # À décommenter si on souhaite générer un achat avec le premier fournisseur trouvé
        #                         partner_ids = partner_obj.search([('is_supplier', '=', True), ('state', '=', 'qualified')], limit=1)
        #                         if partner_ids:
        #                             partner_id = partner_ids[0]
        #                             delivery_delay = proc.product_id.free_supply_delay
        #                         else:
        #                             raise except_orm(_('Error'), _('No supplier found'))
                            
                    else:
                        initial_properties = properties = self.get_properties()
                        if partner:
                            sinfo = proc.product_id.get_sinfo(partner_id=partner.id, property_ids=properties)
                        else:
                            sinfo = proc.product_id.get_sinfo(property_ids=properties)
                        
                        if sinfo:
                            partner = sinfo.partner_id
                            delivery_delay = sinfo.delivery_delay
                            properties = sinfo.property_ids & properties
                        else:
                            raise except_orm(_('Error'), _('No supplier found'))
                        
                    if partner and partner.calendar_id:
                        if proc.is_forecast:
                            qty = 0
                        else:
                            qty = proc.compute_qty_to_procure('purchase')
                            
                        if qty > 0:
                            prev_date = partner.calendar_id.get_date_inverse(proc.needed_date or fields.Date.today(), 1)
                            compress_supplier_delay = self.env['stock.config.settings'].get_param('compress_supplier_delay') or False
                            if compress_supplier_delay:
                                compress_delay_without_past_date = self.env['stock.config.settings'].get_param('compress_delay_without_past_date') or False
                                if compress_delay_without_past_date:
                                    expected_date = max(prev_date, fields.Date.today())
                                else:
                                    expected_date = prev_date
                            else:
                                expected_date = max(prev_date, partner.calendar_id.get_date(fields.Date.today(), delivery_delay))
                                
                            pol_vals = {'source': proc.name,
                                        'uom_qty': qty,
                                        'waiting_delay': proc.waiting_delay,
                                        'need_delay_validation': proc.waiting_delay,
                                        'need_date': prev_date,
                                        'expected_date': expected_date}
                            pol_vals.update(proc.create_po_update_pol_datas())
                            if properties:
                                pol_vals['internal_note'] = 'Properties:\n%s'%(''.join(['  - %s\n'%(x.name) for x in initial_properties]))
                                pol_vals['property_ids'] = [(6, 0, properties.ids)]
                                
                            other_data = {}
                            if self.sol_id and self.sol_id.name_get():
                                other_data['source_document'] = self.sol_id.name_get()[0][1]
                            
                            purchase = po_obj.create_purchase(supplier=partner, 
                                                              po_line={proc.product_id: pol_vals},
                                                              first_qty='uom_qty',
                                                              forced_qty=not proc.consider_min_multiple,
                                                              other_data=other_data)
                            if purchase.purchase_order_line_ids:
                                proc.write({'pol_id': purchase.purchase_order_line_ids[0].id, 
                                            'uom_qty': qty, 
                                            'uom_id': proc.product_id.uom_id.id})
                                proc.wkf_progress()
                                
                        else:
                            proc.update_delay(proc.move_id.in_date or fields.Date.today(), with_raise=False)
                            if proc.state in ('draft', 'exception'):
                                if move_obj.search([('state', 'not in', ('done', 'cancel')),
                                                    ('type', '=', 'out'),
                                                    ('procurement_id', '=', proc.id)], limit=1):
                                    proc.wkf_progress()
                                else:
                                    proc.wkf_done()
                                
                    else:
                        raise except_orm(_('Error'), _('No supplier found'))

            except Exception as e:
                error = ''
                if e and isinstance(e.args, tuple):
                    for i in e.args:
                        if error:
                            error = '%s\n%s'%(error, i)
                        else:
                            error = i
                    proc.write({'error': error, 'state': 'exception'})
                    
        return purchase
    
    
    @api.multi
    def unlink_po(self):
        for proc in self:
            if proc.pol_id:
                proc.pol_id.purchase_order_id.unlink()
                
                
                    
class stock_transfer_request(models.Model):
    """ 
        Stock transfer request
    """
    _inherit = 'stock.transfer.request'

                
    @api.multi
    def create_transfer_purchase(self):
        """
            Fonction permettant de créer rapidement un achat
        """
        action_struc = {}
        if self.product_id and self.partner_id:
            other_data = {}
            po_line = {self.product_id: {'sec_uom_qty': self.quantity}}
            new_purchase = self.env['purchase.order'].create_purchase(self.partner_id, po_line, self.date, other_data)
            #Lien avec les actions. Si on retrouve l'id d'une action dans le context et que l'action n'est pas
            #liée à un objet, on la lie avec l'achat
            context = self.env.context
            if context.get('active_model') == 'calendar.event' and context.get('active_id'):
                action = self.env['calendar.event'].browse(context['active_id'])
                if action and not action.purchase_id:
                    action.write({'purchase_id': new_purchase.id})
        
        action_dict = get_form_view(self, 'purchase.purchase_order_see_form')
        if action_dict and action_dict.get('id') and action_dict.get('type'):
            action = self.env[action_dict['type']].browse(action_dict['id'])
            action_struc = action.read()
            action_struc[0]['res_id'] = new_purchase.id
            action_struc = action_struc[0]
              
        return action_struc
                