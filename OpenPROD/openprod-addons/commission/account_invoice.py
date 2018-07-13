# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.exceptions import UserError,except_orm


SALE_ORDER_ORIGIN = 'SO'



class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    
    @api.multi
    def copy(self, default=None):
        copy_ = super(AccountInvoice, self).copy(default)
        for account_invoice_line_id in copy_.invoice_line_ids:
            account_invoice_line_id._on_change_product_id()
        return copy_
    
    
    @api.multi
    def invoice_validate(self):
        """
            Surchage de la fonction de validation de la facture
            Permet de calculer le total des commissions
        """
        res = super(AccountInvoice, self).invoice_validate()
        for invoice in self:
            for line in invoice.invoice_line_ids:
                if line.commission_ids:
                    line.commission_ids._function_compute_total()
        
        return res
    
    
    @api.multi
    def confirm_paid(self):
        """
            Terminer la commission lié à la facture
        """
        res = super(AccountInvoice,self).confirm_paid()
        cm_obj = self.env['commission.payment']
        for invoice_rs in self:
            commission_payment_rcs = cm_obj.search([('invoice_id', '=', invoice_rs.id), ('state', '!=', 'done')])
            if commission_payment_rcs:
                commission_payment_rcs.wkf_done()
                
        return res
    
    
    
class account_invoice_line(models.Model):
    _inherit = 'account.invoice.line'

    @api.onchange('product_id', 'quantity')
    def _on_change_product_id(self):
        self.commission_ids = [(5, 0)]
        if not self.product_id:
            return

        if self.product_id.is_not_commissionable:
            return

        partner_id = self.invoice_id.partner_id and self.invoice_id.partner_id.id or False
        self.commission_ids = partner_id and self._create_commisions_from_partner(partner_id) or []

    @api.multi
    def copy(self, default=None):
        copy_ = super(account_invoice_line, self).copy(default)
        for commission_id in self.commission_ids:
            commission_id.copy(default={'account_invoice_line_id': copy_.id})
        return copy_
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    commission_ids = fields.One2many(
        comodel_name='commission.invoice.line',
        inverse_name='account_invoice_line_id'
    )
    
    
    #===========================================================================
    # Fonctions
    #===========================================================================
    def create_invoice_line(self, invoice_id, product_id, from_invoice=True, other_data=None, forced_price_unit=None, forced_uoi_qty=False):
        if isinstance(product_id, int):
            product_id = self.env['product.product'].browse([product_id])
        
        if not other_data:
            other_data = dict()

        if not product_id.is_not_commissionable:
            if 'sale_order_line_id' in other_data:
                other_data['commission_ids'] = self._create_commissions_from_sale_order(
                    sale_order_line__id=other_data.get('sale_order_line_id')
                )
            else:
                invoice_read = self.env['account.invoice'].browse(invoice_id).read(['partner_id'], load='_classic_write')
                other_data['commission_ids'] = self._create_commisions_from_partner(
                    partner_id=invoice_read[0]['partner_id']
                )

        return super(account_invoice_line, self).create_invoice_line(
            invoice_id=invoice_id,
            product_id=product_id,
            from_invoice=from_invoice,
            other_data=other_data,
            forced_price_unit=forced_price_unit,
            forced_uoi_qty=forced_uoi_qty
        )

    def _create_commisions_from_partner(self, partner_id):
        rate_obj = self.env['commission.rate']
        rate_rs = rate_obj.search([
            ('partner_id', '=', partner_id)
        ])
        commission_ids = list()
        for rate_id in rate_rs:
            commission_ids.append([
                0, False, {
                    'agent_id': rate_id.agent_id.id,
                    'partner_id': rate_id.partner_id.id,
                    'commission_rule_set_id': rate_id.commission_rule_set_id.id,
                }
            ])
        return commission_ids

    def _create_commissions_from_sale_order(self, sale_order_line__id):
        commission_sale_obj = self.env['commission.sale']
        sale_order_line_obj = self.env['sale.order.line']
        sale_order_id = sale_order_line_obj.browse([sale_order_line__id]).sale_order_id
        commission_sale_rs = commission_sale_obj.search([
            ('sale_order_id', '=', sale_order_id.id)
        ])
        commission_ids = list()
        for commission_sale_id in commission_sale_rs:
            commission_ids.append([
                0, False, {
                    'agent_id': commission_sale_id.agent_id.id,
                    'partner_id': commission_sale_id.partner_id.id,
                    'commission_rule_set_id': commission_sale_id.commission_rule_set_id.id,
                    'commission_sale_id': commission_sale_id.id,
                }
            ])
        return commission_ids



class account_voucher(models.Model):
    _inherit = 'account.voucher'
    
    @api.model
    def proforma_voucher(self):
        """
            Surcharge pour lier l'écriture comptable du paiement à la commission
        """
        res = super(account_voucher, self).proforma_voucher()
        commission_payment_rcs = self.env['commission.payment'].search([('payment_id', '=', self.id)])
        if commission_payment_rcs:
            commission_payment_rcs.wkf_done()
                
        return res
    
    
    @api.multi
    def cancel_voucher(self):
        """
            Surchage de la fonction d'annulation du paiement
            Permet de remettre la commission à valider si elle est terminée
        """
        res = super(account_voucher, self).cancel_voucher()
        cm_obj = self.env['commission.payment']
        for voucher in self:
            commission_payment_rcs = cm_obj.search([('payment_id', '=', voucher.id), ('state', '=', 'done')])
            if commission_payment_rcs:
                commission_payment_rcs.wkf_validate()
            
        return res
    
