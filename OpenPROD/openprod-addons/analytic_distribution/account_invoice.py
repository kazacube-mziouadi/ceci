# -*- coding: utf-8 -*-
from openerp import models, api, fields
from openerp.exceptions import ValidationError
from openerp.tools.translate import _
from decimal import Decimal

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    

    def _prepare_analytic_line_vals(self, line, refund, journal, user_id, general_account_id, company_currency, convert, from_currency, account_id, total, context2):
        amount = convert and from_currency.with_context(context2).compute(total, company_currency) or total
        if refund:
            amount /= -1
            
        vals = {
            'name': self.number, 
            'account_id': account_id, 
            'user_id': user_id, 
            'amount': amount, 
            'amount_invoice': total, 
            'product_id': line.product_id.id, 
            'unit_amount': line.quantity, 
            'product_uom_id': line.uoi_id.id, 
            'general_account_id': general_account_id, 
            'invoice_line_id': line.id, 
            'price_unit': line.price_unit, 
            'journal_id': journal.id
        }
        if self.date_invoice:
            vals['date'] = self.date_invoice
            
        return vals


    @api.multi
    def invoice_validate(self):
        """
            Surchage de la fonction de validation de la facture
            Permet de faire les écritures analytiques
            On vérifie que le montant total des lignes analytique est égal au
            montant HT de la facture 
        """
        res = super(AccountInvoice, self).invoice_validate()
        refund = False
        if self.type == 'out_refund':
            inv_type = 'out_invoice'
            refund = True
        elif self.type == 'in_refund':
            inv_type = 'in_invoice'
            refund = True
        elif self.type in ('out_invoice', 'in_invoice'):
            inv_type = self.type
            
        journal = self._get_journal_analytic(inv_type)
        user_id = self.env.user.id
        account_id = self.account_id.id
        analytic_line_obj = self.env['account.analytic.line']
        company_currency = self.company_id.currency_id
        check_analytic_amount = 0
        if self.currency_id != company_currency:
            convert = True
            from_currency = self.currency_id
            context2 = {'date': self.date_invoice}
        else:
            convert = False
            from_currency = False
            context2 = {}
            
        account_amount_dict = {}
        proportional_lines = []
        for line in self.invoice_line_ids:
            proportional = False
            if line.distribution_ids:
                # Trie des lignes par type inverse pour avoir le proportionnel en premier
                sorted_lines = line.distribution_ids.sorted(key=lambda r: r.type, reverse=True)
                for distribution_line in sorted_lines:
                    # Si il y a une distribution proportionnelle pour cette ligne, pas de traitement du ramasse miettes pour le moment et interdiction d'avoir une ligne d'un autre type
                    if proportional:
                        if distribution_line.type == 'garbage':
                            continue
                        else:
                            raise ValidationError(_('Impossible to join proportional line with another type than garbage collector'))
                        
                    if distribution_line.type == 'proportional':
                        proportional = True
                        proportional_lines.append(line)
                    else:
                        check_analytic_amount += distribution_line.total
                        vals = self._prepare_analytic_line_vals(
                                        line, 
                                        refund, 
                                        journal, 
                                        user_id, 
                                        account_id, 
                                        company_currency, 
                                        convert, 
                                        from_currency, 
                                        distribution_line.account_id.id,
                                        distribution_line.total,
                                        context2
                                    )
                        analytic_line_obj.create(vals)
                        if vals.get('amount'):
                            if distribution_line.account_id.id in account_amount_dict:
                                account_amount_dict[distribution_line.account_id.id] += vals['amount']
                            else:
                                account_amount_dict[distribution_line.account_id.id] = vals['amount']
                                
        if proportional_lines:
            if account_amount_dict:
                account_percent_dict = {}
                total = sum(account_amount_dict.values())
                for normal_line_account_id, normal_line_amount in account_amount_dict.iteritems():
                    account_percent_dict[normal_line_account_id] = normal_line_amount / total 
                
                for proportional_line in proportional_lines:
                    for prop_account_id, prod_percentage in account_percent_dict.iteritems():
                        analytic_line_obj.create(self._prepare_analytic_line_vals(
                                                          proportional_line, 
                                                          refund, 
                                                          journal, 
                                                          user_id, 
                                                          account_id, 
                                                          company_currency, 
                                                          convert, 
                                                          from_currency, 
                                                          prop_account_id,
                                                          prod_percentage * proportional_line.price_subtotal,
                                                          context2
                                                     ))
            else:
                for proportional_line in proportional_lines:
                    for distribution_line in proportional_line.distribution_ids:
                        if distribution_line.type == 'garbage':
                            check_analytic_amount += distribution_line.total
                            vals = self._prepare_analytic_line_vals(
                                            line, 
                                            refund, 
                                            journal, 
                                            user_id, 
                                            account_id, 
                                            company_currency, 
                                            convert, 
                                            from_currency, 
                                            distribution_line.account_id.id,
                                            distribution_line.total,
                                            context2
                                        )
                            analytic_line_obj.create(vals)
                            
        if Decimal(str(check_analytic_amount)) != Decimal(str(self.amount_untaxed)):
            company_rcs = self.company_id
            if company_rcs and company_rcs.check_analytic_amount:
                raise ValidationError(_('The amount of the analytic lines are not equal to the total without taxes of the invoice'))
            
        return res
    
    
    @api.multi
    def action_cancel(self):
        """
            Surchage de la fonction d'annulation de la facture
            Permet de supprimer les écritures analytiques liées à la facture
        """
        res = super(AccountInvoice, self).action_cancel()
        for line in self.invoice_line_ids:
            line.analytic_line_ids.unlink()
            
        return res
    
    

class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    distribution_ids = fields.One2many('purchase.sale.analytic.distribution', 'invoice_line_id',  string='Analytic distribution')
    analytic_line_ids = fields.One2many('account.analytic.line', 'invoice_line_id',  string='Analytic lines')
    
    def onchange_invoice_product_id(self, product_id, invoice):
        """
            Surchage
            Récupération des lignes analytiques de la vente ou de l'achat
        """
        res = super(AccountInvoiceLine, self).onchange_invoice_product_id(product_id, invoice)
        pad = self.env['product.analytic.distribution']
        if self.invoice_id.type == 'out_invoice' and not self.sale_order_line_id:
            pad = product_id.sale_pad_id
        elif self.invoice_id.type == 'in_invoice' and not self.purchase_order_line_id:
            pad = product_id.purchase_pad_id
        
        list_line = []
        for line in pad.distribution_ids:
            vals = {
                    'company_id': pad.company_id.id,
                    'type': line.type,
                    'value': line.value,
                    'account_id': line.account_id.id,
                    }
            list_line.append((0, 0, vals))
            
        res['distribution_ids'] = list_line
        return res

    
    def create_invoice_line(self, invoice_id, product_id, from_invoice=True, other_data=None, forced_price_unit=None, forced_uoi_qty=False):
        """
            Surchage
            Récupération des lignes analytiques de la vente ou de l'achat
        """
        invoice_line = super(AccountInvoiceLine, self).create_invoice_line(invoice_id, product_id, from_invoice, other_data, forced_price_unit=forced_price_unit, forced_uoi_qty=forced_uoi_qty)
        list_line = []
        if invoice_line.sale_order_line_id:
            for distrib in invoice_line.sale_order_line_id.analytic_distribution_ids:
                vals = {
                    'invoice_line_id': invoice_line.id,
                    'company_id': distrib.company_id.id,
                    'type': distrib.type,
                    'value': distrib.value,
                    'account_id': distrib.account_id.id,
                    }
                list_line.append([0, False, vals])
                
            invoice_line.distribution_ids = list_line
        elif invoice_line.purchase_order_line_id:
            for distrib in invoice_line.purchase_order_line_id.analytic_distribution_ids:
                vals = {
                    'invoice_line_id': invoice_line.id,
                    'company_id': distrib.company_id.id,
                    'type': distrib.type,
                    'value': distrib.value,
                    'account_id': distrib.account_id.id,
                    }
                list_line.append([0, False, vals])
                
            invoice_line.distribution_ids = list_line
        
        return invoice_line