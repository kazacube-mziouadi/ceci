# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.addons.base_openprod.common import roundingUp
from decimal import Decimal

class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    purchase_order_line_id = fields.Many2one('purchase.order.line', string='Purchase order line', required=False, ondelete='restrict', copy=False, select=True)
    purchase_section_id = fields.Many2one('purchase.order.line.section', string='Section', required=False, ondelete='restrict')
    
    
    def onchange_invoice_product_id(self, product_id, invoice):
        """
            Récupération des infos du produit et du supplierinfo
        """
        res = super(AccountInvoiceLine, self).onchange_invoice_product_id(product_id, invoice)
        if isinstance(product_id, int):
            product_id = self.env['product.product'].browse(product_id)
            
        suppinfo = False
        fiscal_position = invoice.fiscal_position_id
        if product_id:
            if product_id.purchase_ok and invoice.type in ('in_refund', 'in_invoice'):
                res['invoice_line_tax_ids'] = fiscal_position and fiscal_position.map_tax(product_id.purchase_taxes_ids) or []
                if not product_id.free_purchase:
                    suppinfo = product_id.get_sinfo(partner_id=invoice.partner_order_id.id, property_ids=False)
                    if suppinfo:
                        res.update({'customer_product_name': suppinfo.supp_product_name,
                                    'customer_product_code': suppinfo.supp_product_code,
                                    'sec_uom_qty': roundingUp(suppinfo.min_qty, suppinfo.multiple_qty),
                                    'sec_uom_id': suppinfo.uop_id,
                                    'uoi_id': suppinfo.uoi_id,
                                    'factor': suppinfo.factor,
                                    'divisor': suppinfo.divisor,})
                    else:
                        res['sec_uom_qty'] = 0
                
                else:
                    res.update({'sec_uom_qty': roundingUp(product_id.purchase_min_qty, product_id.purchase_multiple_qty),
                                'sec_uom_id': product_id.uop_id,
                                'uoi_id': product_id.purchase_uoi_id,
                                'factor': product_id.purchase_factor,
                                'divisor': product_id.purchase_divisor,})
                
                if res.get('sec_uom_id', False) and res.get('uom_id', False) and res.get('sec_uom_id', False) and res.get('uoi_id', False)\
                and res.get('factor', False) and res.get('divisor', False):
                    qtys = product_id.get_qtys(res['sec_uom_qty'], 
                                         uom_id=res['uom_id'], 
                                         sec_uom_id=res['sec_uom_id'], 
                                         uoi_id=res['uoi_id'], 
                                         by_field='sec_uom', 
                                         dual_unit=product_id.dual_unit, 
                                         dual_unit_type=product_id.dual_unit_type, 
                                         factor=res['factor'], 
                                         divisor=res['divisor'], 
                                         with_raise=True)
                    
                    res['uom_qty'] = qtys.get('uom_qty')
                
                uoms = product_id.get_uoms(pinfo=suppinfo or False, partner=invoice.partner_order_id, type='in', property_ids=False, with_factor=True)
                for k, v in uoms.iteritems():
                    res[k] = v
        
        return res
    
    
    @api.onchange('sec_uom_qty', 'sec_uom_id')
    def _onchange_sec_uom_qty(self):
        """
            Au changement de la qty, changement des autres qty
        """
        res = super(AccountInvoiceLine, self)._onchange_sec_uom_qty()
        product_rs = self.product_id
        if product_rs and product_rs.purchase_ok and self.invoice_id.type in ('in_refund', 'in_invoice'): 
            if not product_rs.free_purchase:
                supplier_info = product_rs.get_sinfo(partner_id=self.invoice_id.partner_order_id.id, property_ids=False)
                if supplier_info:
                    if supplier_info.multiple_qty and self.sec_uom_qty and Decimal(str(self.sec_uom_qty)) % Decimal(str(supplier_info.multiple_qty)):
                        res['warning'] = {'title': _('Warning'), 'message': _('The quantity is not a multiple of %f')%(supplier_info.multiple_qty)}
                     
                    if supplier_info.min_qty and self.sec_uom_qty and supplier_info.min_qty > self.sec_uom_qty:
                        res['warning'] = {'title': _('Warning'), 'message': _('The quantity in measure unit should be higher to the minimum quantity '
                                                                                '(%.2f)')%(supplier_info.min_qty)}
                 
                else:
                    res['warning'] = {'title': _('Warning'), 'message': _('You must have Management unit and Purchase unit for the supplier referencing')}
                    
            else:
                if product_rs.purchase_multiple_qty and self.sec_uom_qty and Decimal(str(self.sec_uom_qty)) % Decimal(str(product_rs.purchase_multiple_qty)):
                        res['warning'] = {'title': _('Warning'), 'message': _('The quantity is not a multiple of %f')%(product_rs.purchase_multiple_qty)}
                     
                if product_rs.purchase_min_qty and self.sec_uom_qty and product_rs.purchase_min_qty > self.sec_uom_qty:
                    res['warning'] = {'title': _('Warning'), 'message': _('The quantity in measure unit should be higher to the minimum quantity '
                                                                            '(%.2f)')%(product_rs.purchase_min_qty)}
        
        return res
    
    
    @api.onchange('quantity', 'uoi_id')
    def _onchange_quantity(self):
        """
            Au changement de la qty, changement des autres qty et calcul du prix
        """
        res = super(AccountInvoiceLine, self)._onchange_quantity()
        context = self.env.context
        if not context.get('force_invoice_price'):
            price_unit = False
            if self.purchase_order_line_id:
                price_unit = self.purchase_order_line_id.price_unit          
            else:
                product_rs = self.product_id
                if product_rs and product_rs.purchase_ok:
                    self.price_unit = product_rs.get_price_purchase(self.invoice_id.partner_order_id, False, currency_price_return=self.currency_id, qty_uop=self.sec_uom_qty,
                                                                  uop=self.sec_uom_id, date=self.invoice_id.date_invoice, type='price', with_uoi=self.uoi_id)
            
            if price_unit:    
                self.price_unit = price_unit
                self.price_unit_without_discount = price_unit
        
        return res



class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    

    #===========================================================================
    # COLUMNS
    #===========================================================================
    purchaser_id = fields.Many2one('res.users', string='Purchaser', required=False, ondelete='restrict')
    
    
    def onchange_invoice_partner_id(self, partner, type):
        """
            Récupération des infos du fournisseur 
        """
        res = super(AccountInvoice, self).onchange_invoice_partner_id(partner, type)
        if isinstance(partner, int):
            partner = self.env['res.partner'].browse(partner)
        
        if type in ('in_invoice', 'in_refund'):
            res2 = {
                   'fiscal_position_id': partner.supplier_account_position_id.id,
                   'payment_term_id': partner.property_supplier_payment_term_id.id,
                   'payment_method_id': partner.purchase_payment_method_id.id,
                   'discount_management': partner.purchase_discount_management,
                   'max_delay': partner.purchase_max_delay,
                   'discount_value': partner.purchase_discount_value,
                   }
            res.update(res2)
            infos = {'purchase_delivery': False, 'purchase_paid': True, 'purchase_invoiced': False}
            info_dict = self.partner_id.get_partner_address(infos, return_id=True)
            res['paid_by_id'] = info_dict.get('purchase_pay_partner', False)
            if partner.is_seller:
                res['partner_order_id'] = partner.id
            else:
                res['partner_order_id'] = False
            
            if partner.delivered_by:
                res['delivery_partner_id'] = partner.id
                res['delivery_country_id'] = partner.country_id.id or False
            else:
                res['delivery_partner_id'] = False
            
            if partner.paid_to:
                res['paid_by_id'] = partner.id
            else:
                res['paid_by_id'] = False
            
        return res
    
    
    @api.onchange('paid_by_id')
    def _onchange_paid_by_id(self):
        """
            Au changement du payeur, on récupère les informations de paiement
        """
        super(AccountInvoice, self)._onchange_paid_by_id()
        if self.type in ('in_invoice', 'in_refund'):
            self.payment_method_id = self.paid_by_id.purchase_payment_method_id.id
            self.payment_term_id = self.paid_by_id.property_supplier_payment_term_id.id
            self.discount_management = self.paid_by_id.purchase_discount_management
            self.max_delay = self.paid_by_id.purchase_max_delay
            self.discount_value = self.paid_by_id.purchase_discount_value
    
    
    @api.multi
    def invoice_validate(self):
        """
            Surchage de la fonction de validation de la facture
            Permet de gérer le montant facturé des lignes d'achat
        """
        res = super(AccountInvoice, self).invoice_validate()
        for line in self.invoice_line_ids:
            if line.purchase_order_line_id:
                line_amount = line.quantity * line.price_unit
                line.purchase_order_line_id.change_invoiced_amount(amount=line_amount, add=True, 
                                                                   inv_currency_rs=self.currency_id, inv_date=self.date_invoice)
                
        return res
    
    
    @api.multi
    def action_cancel(self):
        """
            Surchage de la fonction d'annulation de la facture
            Permet de gérer le montant facturé des lignes d'achat
        """
        res = super(AccountInvoice, self).action_cancel()
        if self.state == 'cancel':
            for line in self.invoice_line_ids:
                if line.purchase_order_line_id:
                    line_amount = line.quantity * line.price_unit
                    line.purchase_order_line_id.change_invoiced_amount(amount=line_amount, add=False, 
                                                                       inv_currency_rs=self.currency_id, inv_date=self.date_invoice)
            
        return res
    
    
    def manage_sale_purchase_state(self, unlink_invoice_ids=False):
        """
            Surcharge de la fonction des factures pour lancer la méthode de
            changement de l'état de l'achat
            :type self: account.invoice
            :param unlink_invoice_ids: Liste des factures qui vont être supprimées
            :type unlink_invoice_ids: List
            :return: True
            :rtype: boolean
        """
        res = super(AccountInvoice, self).manage_sale_purchase_state(unlink_invoice_ids)
        for invoice in self:
            purchase_list = [line.purchase_order_line_id.purchase_order_id for line in invoice.invoice_line_ids if line.purchase_order_line_id]
            set_purchase_list = list(set(purchase_list))
            for purchase in set_purchase_list:
                purchase.pass_done_purchase(unlink_invoice_ids, False)
            
        return res

    
    @api.multi
    def confirm_paid(self):
        """
            On surcharge la fonction de base d'Odoo pour débloquer le BR ou l'achat lié à la facture
            lors de son paiement
        """
        res = super(AccountInvoice,self).confirm_paid()
        invoice_line_list = []
        order_ids_list = []
        if self.type in ('in_invoice', 'in_refund') and not self.anticipated:
            #On récupère la liste des ids des lignes de facture de la facture
            #Ainsi que la liste des rs et des ids des achats liées à la facture
            for line in self.invoice_line_ids:
                invoice_line_list.append(line.id)
                purchase_line = line.purchase_order_line_id
                purchase_order = purchase_line.purchase_order_id
                if purchase_order and not purchase_order.id in order_ids_list:
                    purchase_order.write({'check_paid': True})
                    order_ids_list.append(purchase_order.id)
            
            #On va rechercher les moves liés aux lignes de factures
            #et les moves liés aux achats liés aux lignes de factures
            #Cela permet de récupérer tous les BR éventuellement en lien avec la facture
            if invoice_line_list:
                move_list = self.env['stock.move'].search([('type', '=', 'in'), '|',
                                                           ('invoice_line_id', 'in', invoice_line_list),
                                                           ('picking_id.purchase_id', 'in', order_ids_list)])
                for picking in move_list:
                    picking.picking_id.write({'payment_lock': False})
                        
        return res
    
    
    @api.multi
    def unlink(self):
        order_to_update = self.env['purchase.order']
        for invoice in self:
            for line in invoice.invoice_line_ids:
                if line.purchase_order_line_id and not line.purchase_order_line_id.purchase_order_id.show_invoice_button:
                    order_to_update |= line.purchase_order_line_id.purchase_order_id
        
        if order_to_update:
            order_to_update.write({'show_invoice_button': True})
            
        super(AccountInvoice, self).unlink()
    
