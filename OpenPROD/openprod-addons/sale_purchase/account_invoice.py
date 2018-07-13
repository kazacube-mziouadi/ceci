# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.translate import _

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'


    def generate_anticipated_invoice_line(self, order_type, invoice_id, remaining_advanced_amount, order=False):
        """
            Fonction permettant de gérer le montant de la facture anticipée à répartir et de
            créer les lignes de facture correspondantes
            :type self: stock.picking
            :param order_type: Type de la commande liée à la facture : 'purchase' ou 'sale'
            :type order_type: string
            :param invoice_id: Facture liée au picking
            :type invoice_id: recordset: account.invoice
            :param remaining_advanced_amount: Montant de facture anticipée restant à facturer
            :type remaining_advanced_amount: float
            :param order: Commande liée à la facture 
            :type order: recordset: sale.order ou purchase.order
            :return: True
            :rtype: boolean
        """
        res = super(AccountInvoice, self).generate_anticipated_invoice_line(order_type, invoice_id, remaining_advanced_amount, order)
        if order_type and order and remaining_advanced_amount:
            invoice_line_obj = self.env['account.invoice.line']
            context2 = {'force_invoice_price': True}
            context2.update(self.env.context)
            anticipated_invoice_amount = 0
            search_args = [('invoice_id.anticipated', '=', True)]
            order_lines = False
            product_list = {}
            if order_type == 'sale':
                if order.order_line_ids:
                    order_lines = True
                    search_args += [('sale_order_line_id', 'in', order.order_line_ids.ids)]
                    # Liaison des lignes de facture à la première ligne de vente trouvée
                    global_data = {'sale_order_line_id': order.order_line_ids[0].id}
                    
            elif order_type == 'purchase':
                if order.purchase_order_line_ids:
                    order_lines = True
                    search_args += [('purchase_order_line_id', 'in', order.purchase_order_line_ids.ids)]
                    # Liaison des lignes de facture à la première ligne d'achat trouvée
                    global_data = {'purchase_order_line_id': order.purchase_order_line_ids[0].id}

            if order_lines:
                #On récupère le montant total de la facture ainsi que le montant total de la commande afin de 
                #faire le prorata du montant de la facture anticipée à répartir
                total_amount = order.total_amount
                invoice_total_amount = invoice_id.amount_total
                if total_amount > 0:
                    anticipated_invoice_amount = order.advanced_amount_without_tax * (round(invoice_total_amount, 4) / round(total_amount, 4))
                
                # Rercherche des éventuelles lignes de facture anticipée
                anticipated_lines = invoice_line_obj.search(search_args)
                if anticipated_lines:
                    #On va simplifier la création des lignes en récupérant le total à répartir divisé par le nombre
                    #de lignes de factures anticipées à créer afin de les saisir comme montants
                    nb = float(len(anticipated_lines))
                    if anticipated_invoice_amount > remaining_advanced_amount:
                        anticipated_invoice_amount = remaining_advanced_amount
                        
                    unit_price = anticipated_invoice_amount / nb
                    for line in anticipated_lines:
                        if line.product_id not in product_list:
                            product_list[line.product_id] = {
                                    'sec_uom_qty': -1,
                                    'sec_uom_id': line.sec_uom_id.id,
                                    'uom_qty': -1,
                                    'uom_id': line.uom_id.id,
                                    'quantity': -1,
                                    'uoi_id': line.uoi_id.id,
                                    'price_unit': unit_price,
                                    'invoice_line_tax_ids': [(4, x.id) for x in line.invoice_line_tax_ids],
                                    }
                        else:
                            product_list[line.product_id]['price_unit'] += -unit_price
                    
                    for product, datas in product_list.iteritems():
                        product_list[product].update(global_data)
                        invoice_line_obj.with_context(context2).create_invoice_line(invoice_id.id, product, True, datas, forced_price_unit=unit_price)
                        
                # Calcule de la TVA
                invoice_id._onchange_invoice_line_ids()
            
        return res
    
    
    def generate_auto_anticipated_invoice_line(self, order_type, invoice_id, order_line, factor=1):
        """
            Fonction permettant de gérer le montant de la facture anticipée à répartir et de
            créer les lignes de facture correspondantes
            :type self: stock.picking
            :param order_type: Type de la commande liée à la facture : 'purchase' ou 'sale'
            :type order_type: string
            :param invoice_id: Facture liée au picking
            :type invoice_id: recordset: account.invoice
            :param order: Commande liée à la facture 
            :type order: recordset: sale.order ou purchase.order
            :return: True
            :rtype: boolean
        """
        res = super(AccountInvoice, self).generate_auto_anticipated_invoice_line(order_type, invoice_id, order_line, factor=factor)
        if order_type and order_line:
            invoice_line_obj = self.env['account.invoice.line']
            context2 = {'force_invoice_price': True}
            context2.update(self.env.context)
            search_args = [('invoice_id.auto_anticipated', '=', True)]
            order_lines = False
            if order_type == 'sale':
                order_lines = True
                search_args += [('sale_order_line_id', '=', order_line.id)]
                # Liaison des lignes de facture à la première ligne de vente trouvée
                global_data = {'sale_order_line_id': order_line.id}
                    
            elif order_type == 'purchase':
                order_lines = True
                search_args += [('purchase_order_line_id', '=', order_line.id)]
                # Liaison des lignes de facture à la première ligne d'achat trouvée
                global_data = {'purchase_order_line_id': order_line.id}
            
            if order_lines:
                # Rercherche des éventuelles lignes de facture anticipée
                anticipated_lines = invoice_line_obj.search(search_args)
                if anticipated_lines:
                    for line in anticipated_lines:
                        qty_already_done = invoice_line_obj.search_group(fields=['quantity'], 
                                                                         groupby=[], 
                                                                         args=[('auto_anticipated_line_id', '=', line.id)],
                                                                         sum='quantity',
                                                                         return_dict=True,
                                                                         without_order=True)[0]['quantity']
                                                                         
                        qty = line.quantity * factor
                        rest_qty = line.quantity - (qty_already_done or 0.0)
                        if qty > rest_qty:
                            qty_factor = rest_qty / qty
                            qty = rest_qty          
                        else:
                            qty_factor = 1
                        
                        if rest_qty:
                            vals = {'sec_uom_qty': -line.sec_uom_qty * factor * qty_factor,
                                    'sec_uom_id': line.sec_uom_id.id,
                                    'uom_qty': -line.uom_qty * factor * qty_factor,
                                    'uom_id': line.uom_id.id,
                                    'quantity': -qty,
                                    'uoi_id': line.uoi_id.id,
                                    'price_unit': line.price_unit,
                                    'auto_anticipated_line_id': line.id,
                                    'invoice_line_tax_ids': [(4, x.id) for x in line.invoice_line_tax_ids]}
                            vals.update(global_data)
                            invoice_line_obj.with_context(context2).create_invoice_line(invoice_id.id, line.product_id, True, vals, forced_price_unit=line.price_unit)
                        
                # Calcule de la TVA
                invoice_id._onchange_invoice_line_ids()
            
        return res



class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'
    
    
    @api.one
    @api.constrains('invoice_id.anticipated', 'invoice_line_tax_ids')    
    def _check_taxes_on_anticipated_invoices(self):
        """
            On vérifie que pour une même vente ou un même achat, toutes les lignes de factures
            anticipées ont les mêmes taxes
        """
        if self.invoice_id.anticipated:
            search_args = [('invoice_id.anticipated', '=', True)]
            #On récupère la liste des ids des taxes de la ligne
            tax_list_ids = [tax.id for tax in self.invoice_line_tax_ids]
            tax_list_ids.sort()
            if self.sale_order_line_id:
                search_args += [('sale_order_line_id.sale_order_id', '=', self.sale_order_line_id.sale_order_id.id)]
            elif self.purchase_order_line_id:
                search_args += [('purchase_order_line_id.purchase_order_id', '=', self.purchase_order_line_id.purchase_order_id.id)]
            else:
                return True
            
            #On recherche les lignes de factures anticipées qui sont liés à la même vente ou au même achat
            invoice_lines = self.search(search_args)
            for line in invoice_lines:
                other_taxes = [taxe.id for taxe in line.invoice_line_tax_ids]
                other_taxes.sort()
                if other_taxes != tax_list_ids:
                    raise Warning(_('Error'), _('You have an other invoice line for this sale or this purchase whith different taxes.'
                                                'When you have many anticipated invoice lines for a sale or a purchase, all the lines '
                                                'must have the same taxes.'))
