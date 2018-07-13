# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.addons.base_openprod.common import roundingUp
from openerp.exceptions import except_orm, ValidationError, Warning

from decimal import Decimal
import openerp.addons.decimal_precision as dp

class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'
    
    @api.one
    @api.depends('fixed_discount_ids', 'fixed_discount_ids.amount')
    def _compute_fixed_discount(self):
        """
            Fonction permettant de calculer la remise fixe sur le prix unitaire
        """
        fixed_discount = 0.0
        for line in self.fixed_discount_ids:
            fixed_discount += line.amount
        
        self.fixed_discount = fixed_discount
    
    
    @api.one
    @api.depends('variable_discount_ids', 'variable_discount_ids.amount', 'variable_discount_ids.type')
    def _compute_variable_discount(self):
        """
            Fonction permettant de calculer la remise fixe sur le prix unitaire
        """
        variable_discount = 0.0
        type = False
        for line in self.variable_discount_ids:
            if not type:
                type = line.type
            else:
                if type != line.type:
                    raise except_orm(_('All lines must be of the same type!'))
                    break
                    
            if type == 'cumulative':
                variable_discount += line.amount
            else:
                if variable_discount == 0:
                    variable_discount = 1
                    
                variable_discount *= (line.amount/100+1)
                                    
        if type:
            if type != 'cumulative':
                variable_discount = variable_discount and variable_discount*100-100 or 0
        
        self.variable_discount = variable_discount
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    #Général
    section_id = fields.Many2one('sale.order.line.section', string='Section', required=False, ondelete='restrict')
    #Divers
    sale_order_line_id = fields.Many2one('sale.order.line', string='Sale order line', required=False, ondelete='restrict', copy=False)
    # Discount
    fixed_discount_ids = fields.One2many('sale.order.line.fixed.discount', 'invoice_line_id',  string='Fixed discount', copy=True)
    variable_discount_ids = fields.One2many('sale.order.line.variable.discount', 'invoice_line_id',  string='Variable discount', copy=True)
    price_unit_without_discount = fields.Float(string='Price unit without discount', default=0.0, digits=dp.get_precision('Product price'), 
                              required=False, copy=True)
    fixed_discount = fields.Float(string='Fixed discount on unit price', compute='_compute_fixed_discount', store=True, readonly=True, digits=dp.get_precision('Product quantity'))
    variable_discount = fields.Float(string='Variable discount % on unit price', compute='_compute_variable_discount', store=True, readonly=True, digits=dp.get_precision('Product quantity'))
    is_print_discount = fields.Boolean(string='Discount visible in reports', default=False, copy=True)
    
    
    def onchange_invoice_product_id(self, product_id, invoice):
        """
            Récupération des infos du produit et du customerinfo
        """
        res = super(AccountInvoiceLine, self).onchange_invoice_product_id(product_id, invoice)
        if isinstance(product_id, int):
            product_id = self.env['product.product'].browse(product_id)
            
        customer = False
        fiscal_position = invoice.fiscal_position_id
        if product_id:
            if product_id.sale_ok and invoice.type in ('out_refund', 'out_invoice'):
                res['invoice_line_tax_ids'] = fiscal_position and fiscal_position.map_tax(product_id.sale_taxes_ids) or []
                if not product_id.free_sale:
                    customer = product_id.get_cinfo(partner_id=invoice.partner_order_id.id, property_ids=False)
                    if customer:
                        res.update({'customer_product_name': customer.cust_product_name,
                                    'customer_product_code': customer.cust_product_code,
                                    'sec_uom_qty': roundingUp(customer.min_qty, customer.multiple_qty),
                                    'sec_uom_id': customer.uos_id,
                                    'uoi_id': customer.uoi_id,
                                    'factor': customer.factor,
                                    'divisor': customer.divisor})
                    else:
                        res['sec_uom_qty'] = 0
                else:
                    res.update({'sec_uom_qty': roundingUp(product_id.sale_min_qty, product_id.sale_multiple_qty),
                                'sec_uom_id': product_id.uos_id,
                                'uoi_id': product_id.sale_uoi_id,
                                'factor': product_id.sale_factor,
                                'divisor': product_id.sale_divisor})
                        
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
            
                uoms = product_id.get_uoms(pinfo=customer or False, partner=invoice.partner_order_id, type='out', property_ids=False, with_factor=True)
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
        if product_rs and product_rs.sale_ok and self.invoice_id.type in ('out_refund', 'out_invoice'): 
            if not product_rs.free_sale:
                customer_info = product_rs.get_cinfo(partner_id=self.invoice_id.partner_order_id.id, property_ids=False)
                if customer_info:
                    if customer_info.multiple_qty and self.sec_uom_qty and Decimal(str(self.sec_uom_qty)) % Decimal(str(customer_info.multiple_qty)):
                        res['warning'] = {'title': _('Warning'), 'message': _('The quantity is not a multiple of %d')%(customer_info.multiple_qty)}
                     
                    if customer_info.min_qty and self.sec_uom_qty and Decimal(str(customer_info.min_qty)) > Decimal(str(self.sec_uom_qty)):
                        res['warning'] = {'title': _('Warning'), 'message': _('The quantity in measure unit should be higher to the minimum quantity '
                                                                                '(%.2f)')%(customer_info.min_qty)}
                
                else:
                    res['warning'] = {'title': _('Warning'), 'message': _('You must have Management unit and Sale unit for the customer referencing')}
            else:
                if product_rs.sale_multiple_qty and self.sec_uom_qty and Decimal(str(self.sec_uom_qty)) % Decimal(str(product_rs.sale_multiple_qty)):
                    res['warning'] = {'title': _('Warning'), 'message': _('The quantity is not a multiple of %d')%(product_rs.sale_multiple_qty)}
                     
                if product_rs.sale_min_qty and self.sec_uom_qty and Decimal(str(product_rs.sale_min_qty)) > Decimal(str(self.sec_uom_qty)):
                    res['warning'] = {'title': _('Warning'), 'message': _('The quantity in measure unit should be higher to the minimum quantity '
                                                                            '(%.2f)')%(product_rs.sale_min_qty)}
        
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
            if self.sale_order_line_id:
                price_unit = self.sale_order_line_id.price_unit          
            else:    
                product_rs = self.product_id
                if product_rs and product_rs.sale_ok:
                    price_unit = product_rs.get_price_sale(self.invoice_id.partner_order_id, False, currency_price_return=self.currency_id, qty_uos=self.sec_uom_qty,
                                                                      uos=self.sec_uom_id, date=self.invoice_id.date_invoice, type='price', with_uoi=self.uoi_id)
            
            if price_unit:    
                self.price_unit = price_unit
                self.price_unit_without_discount = price_unit
                
        return res
        
        
        
class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    seller_id = fields.Many2one('res.users', string='Seller', required=False, ondelete='restrict')
    sale_manager_id = fields.Many2one('res.users', string='Sale manager', required=False, ondelete='restrict')
    
    
    def onchange_invoice_partner_id(self, partner, type):
        """
            Récupération des infos du client 
        """
        res = super(AccountInvoice, self).onchange_invoice_partner_id(partner, type)
        if isinstance(partner, int):
            partner = self.env['res.partner'].browse(partner)
        
        if type in ('out_invoice', 'out_refund'):
            res2 = {
                   'fiscal_position_id': partner.property_account_position_id.id,
                   'payment_term_id': partner.property_payment_term_id.id,
                   'payment_method_id': partner.sale_payment_method_id.id,
                   'discount_management': partner.sale_discount_management,
                   'max_delay': partner.sale_max_delay,
                   'discount_value': partner.sale_discount_value,
                   }
            infos = {'delivery': False, 'paid': True, 'invoiced': False}
            info_dict = self.partner_id.get_partner_address(infos, return_id=True)
            res2['paid_by_id'] = info_dict.get('pay_partner', False) 
            res.update(res2)
            if partner.can_order:
                res['partner_order_id'] = partner.id
            else:
                res['partner_order_id'] = False
            
            infos = {'delivery': True, 'paid': True}
            info_dict = partner.get_partner_address(infos, return_id=True)
            res['delivery_partner_id'] = info_dict and 'delivery_partner' in info_dict and info_dict['delivery_partner'] or False
            res['delivery_country_id'] = res['delivery_partner_id'] and self.env['res.partner'].browse(res['delivery_partner_id']).country_id.id or False
            
            res['paid_by_id'] = info_dict and 'pay_partner' in info_dict and info_dict['pay_partner'] or False
            
        return res
    
    
    @api.multi
    def invoice_validate(self):
        """
            Surchage de la fonction de validation de la facture
            Permet de gérer le montant facturé des lignes de ventes
        """
        res = super(AccountInvoice, self).invoice_validate()
        for line in self.invoice_line_ids:
            if line.sale_order_line_id:
                line_amount = line.quantity * line.price_unit
                line.sale_order_line_id.change_invoiced_amount(amount=line_amount, add=True, 
                                                               inv_currency_rs=self.currency_id, inv_date=self.date_invoice)
        return res
    
    
    @api.multi
    def action_cancel(self):
        """
            Surchage de la fonction d'annulation de la facture
            Permet de gérer le montant facturé des lignes de ventes
        """
        res = super(AccountInvoice, self).action_cancel()
        if self.state == 'cancel':
            for line in self.invoice_line_ids:
                if line.sale_order_line_id:
                    line_amount = line.quantity * line.price_unit
                    line.sale_order_line_id.change_invoiced_amount(amount=line_amount, add=False, 
                                                                   inv_currency_rs=self.currency_id, inv_date=self.date_invoice)
            
        return res
    
    
    def manage_sale_purchase_state(self, unlink_invoice_ids=False):
        """
            Surcharge de la fonction des factures pour lancer la méthode de
            changement de l'état de la vente
            :type self: account.invoice
            :param unlink_invoice_ids: Liste des factures qui vont être supprimées
            :type unlink_invoice_ids: List
            :return: True
            :rtype: boolean
        """
        res = super(AccountInvoice, self).manage_sale_purchase_state(unlink_invoice_ids)
        for invoice in self:
            sale_list = [line.sale_order_line_id.sale_order_id for line in invoice.invoice_line_ids if line.sale_order_line_id]
            set_sale_list = list(set(sale_list))
            for sale in set_sale_list:
                sale.pass_done_sale(unlink_invoice_ids, False)
            
        return res
    
    
    @api.onchange('paid_by_id')
    def _onchange_paid_by_id(self):
        """
            Au changement du payeur, on récupère les informations de paiement
        """
        super(AccountInvoice, self)._onchange_paid_by_id()
        if self.type in ('out_invoice', 'out_refund'):
            self.payment_method_id = self.paid_by_id.sale_payment_method_id.id
            self.payment_term_id = self.paid_by_id.property_payment_term_id.id
            self.discount_management = self.paid_by_id.sale_discount_management
            self.max_delay = self.paid_by_id.sale_max_delay
            self.discount_value = self.paid_by_id.sale_discount_value
    
    
    @api.multi
    def confirm_paid(self):
        """
            On surcharge la fonction de base d'Odoo pour débloquer le BL ou la vente liées à la facture
            lors de son paiement
        """
        res = super(AccountInvoice,self).confirm_paid()
        order_list = []
        invoice_line_list = []
        order_ids_list = []
        if self.type in ('out_invoice', 'out_refund') and not self.anticipated:
            #On récupère la liste des ids des lignes de facture de la facture
            #Ainsi que la liste des rs et des ids des ventes liées à la facture
            for line in self.invoice_line_ids:
                invoice_line_list.append(line.id)
                sale_line = line.sale_order_line_id
                sale_order = sale_line.sale_order_id
                if sale_order and not sale_order in order_list:
                    sale_order.write({'check_paid': True})
                    order_ids_list.append(sale_order.id)
            
            #On va rechercher les moves liés aux lignes de factures
            #et les moves liés aux ventes liées aux lignes de factures
            #Cela permet de récupérer tous les BL éventuellement en lien avec la facture
            if invoice_line_list:
                picking_list = self.env['stock.move'].search([('type', '=', 'out'), '|',
                                                              ('invoice_line_id', 'in', invoice_line_list),
                                                              ('picking_id.sale_id', 'in', order_ids_list)])
                for picking in picking_list:
                    if picking.picking_id.payment_lock:
                        picking.picking_id.write({'payment_lock': False})
                        
        return res
    

    @api.multi
    def unlink(self):
        order_to_update = self.env['sale.order']
        for invoice in self:
            for line in invoice.invoice_line_ids:
                if line.sale_order_line_id and not line.sale_order_line_id.sale_order_id.show_invoice_button:
                    order_to_update |= line.sale_order_line_id.sale_order_id
        
        if order_to_update:
            order_to_update.write({'show_invoice_button': True})
            
        super(AccountInvoice, self).unlink()