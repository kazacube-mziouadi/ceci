# -*- coding: utf-8 -*-
from openerp import models, fields, api, _

class stock_picking(models.Model):
    _inherit = 'stock.picking'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    sale_id = fields.Many2one('sale.order', string='Sale', required=False, ondelete='restrict')
    
    
    def manage_sale_purchase_state(self, unlink_picking_ids=False):
        """
            Surcharge de la fonction des picking pour lancer la méthode de
            changement de l'état de la vente
        """
        res = super(stock_picking, self).manage_sale_purchase_state(unlink_picking_ids)
        for picking in self:
            if picking.sale_id:
                picking.sale_id.pass_done_sale(False, unlink_picking_ids)
            
        return res
    
    
    def get_transport_files(self, partner):
        """
            Ajout du partenaire de livraison
        """
        res = super(stock_picking, self).get_transport_files(partner)
        if not res:
            res = {}
        
        res['address_contact_id'] = partner.sale_delivery_contact_id and partner.sale_delivery_contact_id.id or False 
        return res
    
    

class stock_move(models.Model):
    _inherit = 'stock.move'

    
    def _get_states(self):
        return {'done': [('readonly', True)], 'cancel': [('readonly', True)]} 

       
    #===========================================================================
    # COLUMNS
    #===========================================================================
    sale_line_id = fields.Many2one('sale.order.line', string='Sale line', required=False, ondelete='set null')
    cinfo_id = fields.Many2one('product.customerinfo', string='Customer info', required=False, ondelete='restrict', states=_get_states)
    
    
    @api.onchange('cinfo_id', 'type')
    def _onchange_cinfo_id(self):
        """
            Au changement du produit, changement des UoM et du nom
        """
        if self.type == 'out' and self.cinfo_id:
            uoms = self.product_id.get_uoms(pinfo=self.cinfo_id, type=self.type, with_factor=True)
            for k, v in uoms.iteritems():
                self[k] = v
                
            
    @api.onchange('product_id', 'type')            
    def _onchange_product_id(self):
        super(stock_move, self)._onchange_product_id()
        if self.product_id:
            self.cinfo_id = self.product_id.get_cinfo()
   
    
    def update_procurement_vals(self):
        res = super(stock_move, self).update_procurement_vals()
        if self.sale_line_id:
            res['sol_id'] = self.sale_line_id.id
            if self.sale_line_id.delay_confirm:
                res['waiting_delay'] = True

        return res
    
    
    def manage_sale_purchase_qty(self):
        """
            Surcharge de la fonction des moves pour gérer les quantités
            livrées de la ligne de vente
        """
        res = super(stock_move, self).manage_sale_purchase_qty()
        for move in self:
            if move.sale_line_id:
                move.sale_line_id.compute_delivered_qty()
            
        return res
    
    

class procurement_order(models.Model):
    _inherit = 'procurement.order'

    #===========================================================================
    # COLUMNS
    #===========================================================================
    sol_id = fields.Many2one('sale.order.line', string='Origin SoL', required=False, ondelete='restrict', select=True)


#     def get_proc_to_compute_by_move(self):
#         """
#             Renvoie tous les procurement comme déclencheur un mouvement avec la même ligne de vente que le mouvement déclencheur
#         """
#         if self.move_id and self.move_id.sol_id:
#             res = self.search([('move_id.sol_id', '=', self.move_id.sol_id.id)])
#         else:
#             res = super(procurement_order, self).get_proc_to_compute()
#             
#         return res
    
    
#     def get_proc_to_compute(self):
#         """
#             Renvoie tous les procurement ayant la ligne de vente du déclencheur
#         """
#         if self.sol_id:
#             res = self.search([('sol_id', '=', self.sol_id.id)])
#         else:
#             res = super(procurement_order, self).get_proc_to_compute()
#             
#         return res
    
    
    def get_properties(self):
        res = super(procurement_order, self).get_properties()
        if self.sol_id and self.sol_id.purchase_property_ids:
            res += self.sol_id.purchase_property_ids
            
        return res
    
    
    def update_delay(self, date=False, with_raise=True):
        for proc in self:
            # Le test sur le produit permet de ne pas valider en auto une vente depuis le procurement d'un sous produit 
            # (tous les procurement des sous produits ont la ligne de vente d'origine) 
            if proc.sol_id and proc.sol_id.product_id.id == proc.product_id.id: 
                proc.sol_id.update_delay(date, with_raise=with_raise)
            
        return True