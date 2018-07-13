# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError, UserError

# mapping invoice type to journal type
TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale_refund',
    'in_refund': 'purchase_refund',
}

class stock_picking(models.Model):
    _inherit = 'stock.picking'
            
    
    def get_invoice_state(self):
        """
            Méthode permetatnt de forcer l'invoice_state à 'none' en cas de facturation sur quantité commandée
            :type self: stock.picking
            :return: État de facturation
            :rtype: char
        """
        invoice_state = super(stock_picking, self).get_invoice_state()
        if invoice_state != 'none':
            invoicing_method_id = (self.sale_id and self.sale_id.invoicing_method_id) or (self.purchase_id and self.purchase_id.invoicing_method_id) or False
            if invoicing_method_id and invoicing_method_id.get_invoiced_on('picking') == 'order':
                invoice_state = 'none'
                
        return invoice_state
    
    
    def get_type_invoice(self):
        type_invoice = False
        if self.type == 'in':
            if self.is_return:
                type_invoice = 'out_refund'
            elif not self.is_return:
                type_invoice = 'in_invoice'
                
        elif self.type == 'out': 
            if self.is_return:
                type_invoice = 'in_refund'
            elif not self.is_return:
                type_invoice = 'out_invoice'
                
        if not type_invoice:
            type_invoice = 'out_invoice'
            
        return type_invoice


    @api.multi
    def create_invoice(self):
        """
            Fonction permettant de créer la facture liée au picking
        """
        res = super(stock_picking, self).create_invoice()
        invoice_line_obj = self.env['account.invoice.line']
        invoice_obj = self.env['account.invoice']
        sale_line_obj = self.env['sale.order.line']
        purchase_line_obj = self.env['purchase.order.line']
        for picking in self:
            context2 = {'force_invoice_price': True}
            context2.update(self.env.context)
            type_invoice = False
            if picking.partner_id:
                remaining_advanced_amount = 0
                other_data = {}
                #On parcourt les moves pour récupérer la vente et l'achat lié
                sale_order = picking.sale_id
                purchase_order = picking.purchase_id
                #Type de facture
                type_invoice = picking.get_type_invoice()
                
                domain_journal_id = [
                    ('type', 'in', filter(None, map(TYPE2JOURNAL.get, [type_invoice]))),
                    ('company_id', '=', picking.company_id.id),
                ]
                journal = self.env['account.journal'].search(domain_journal_id, limit=1)
                #S'il y a une vente, on récupère la plupart des infos à partir de celle-ci
                if sale_order:
                    ail_other_data = {'sale_order_line_id': sale_order.order_line_ids[0].id}
                    balance = (sale_order.sale_invoice_balance_trigger == 'picking') or False
                    invoiced_partner = sale_order.invoiced_customer_id
                    payment_term_id = sale_order.payment_term_id
                    invoicing_method_id = sale_order.invoicing_method_id
                    invoicing_method_line_rs = self.env['account.invoicing.method.line'].search([('invoice_trigger', '=', 'picking'), 
                                                                                                 ('invoicing_method_id', '=', invoicing_method_id.id)], limit=1)
                    if invoicing_method_line_rs and invoicing_method_line_rs.payment_term_id:
                        payment_term_id = invoicing_method_line_rs.payment_term_id
                    
                    other_data2 = {
                              'fiscal_position_id': sale_order.sale_account_system_id.id,
                              'currency_id': sale_order.currency_id.id,
                              'company_id': sale_order.company_id.id,
                              'delivery_partner_id': picking.partner_id.id,
                              'delivery_country_id': picking.country_id and picking.country_id.id or picking.partner_id.country_id.id,
                              'partner_order_id': sale_order.partner_id.id,
                              'lock_invoice': sale_order.locked_invoice,
                              'group_invoices': sale_order.group_invoices,
                              'invoices_period': sale_order.invoices_period,
                              'declaration_deb': sale_order.subject_deb,
                              'tva_number': sale_order.tva_number,
                              'note_invoice_intern': sale_order.inter_note,
                              'note_invoice_header': sale_order.invoice_note,
                              'payment_term_id': payment_term_id.id,
                              'discount_management': sale_order.discount,
                              'discount_value': sale_order.discount_value,
                              'max_delay': sale_order.max_delay,
                              'payment_method_id': sale_order.payment_id.id,
                              'paid_by_id': sale_order.paid_customer_id.id,
                              'contact_ids': [(4, contact_id) for contact_id in invoiced_partner.invoicing_contact_ids.ids],
                              'communication_method': invoiced_partner.accounting_communication_method,
                              'origin': sale_order.name_get()[0][1],
                              'auto_anticipated': not balance,
                              }
                    if journal:
                        other_data2['journal_id'] = journal.id
                        
                    other_data.update(other_data2)
                    invoice_id = invoice_obj.create_invoice(invoiced_partner, picking.address_id, type_invoice, other_data)
                    # Gestion des factures anticipées: on récupère le montant restant de la facture anticipée à répartir
                    remaining_advanced_amount = sale_order.remaining_advanced_amount
                        
                elif purchase_order:
                    ail_other_data = {'purchase_order_line_id': purchase_order.purchase_order_line_ids[0].id}
                    balance = (purchase_order.purchase_invoice_balance_trigger == 'picking') or False
                    payment_term_id = purchase_order.payment_term_id
                    invoicing_method_id = purchase_order.invoicing_method_id
                    invoicing_method_line_rs = self.env['account.invoicing.method.line'].search([('invoice_trigger', '=', 'picking'), 
                                                                                                 ('invoicing_method_id', '=', invoicing_method_id.id)], limit=1)
                    if invoicing_method_line_rs and invoicing_method_line_rs.payment_term_id:
                        payment_term_id = invoicing_method_line_rs.payment_term_id
                        
                    other_data2 = {
                              'fiscal_position_id': purchase_order.purchase_account_system_id.id,
                              'currency_id': purchase_order.currency_id.id,
                              'company_id': purchase_order.company_id.id,
                              'delivery_partner_id': picking.partner_id.id,
                              'delivery_country_id': picking.country_id and picking.country_id.id or picking.partner_id.country_id.id,
                              'partner_order_id': purchase_order.partner_id.id,
                              'note_invoice_intern': purchase_order.inter_note,
                              'note_invoice_header': purchase_order.invoice_note,
                              'payment_term_id': payment_term_id.id,
                              'discount_management': purchase_order.discount,
                              'discount_value': purchase_order.discount_value,
                              'max_delay': purchase_order.max_delay,
                              'payment_method_id': purchase_order.payment_id.id,
                              'paid_by_id': purchase_order.paid_to_id.id,
                              'origin': purchase_order.name_get()[0][1],
                              'auto_anticipated': not balance,
                              }
                    if journal:
                        other_data2['journal_id'] = journal.id
                        
                    other_data.update(other_data2)
                    invoice_id = invoice_obj.create_invoice(purchase_order.invoiced_by_id, purchase_order.invoiced_by_id.address_id, 
                                                                            type_invoice, other_data)
                    remaining_advanced_amount = purchase_order.remaining_advanced_amount
                #Sinon on ne récupère que les infos du picking
                else:
                    ail_other_data = None 
                    balance = False
                    other_data2 = {
                              'delivery_partner_id': picking.partner_id.id,
                              'delivery_country_id': picking.country_id and picking.country_id.id or picking.partner_id.country_id.id,
                              'partner_order_id': picking.partner_id.id,
                              'address_id': picking.address_id.id,
                              'paid_by_id': picking.partner_id.id,
                              'origin': picking.name_get()[0][1],
                              }
                    if journal:
                        other_data2['journal_id'] = journal.id
                        
                    if picking.partner_id.is_supplier:
                        payment_term_id = picking.partner_id.property_supplier_payment_term_id
                        invoicing_method_id = picking.partner_id.purchase_invoicing_method_id
                        if invoicing_method_id:
                            invoicing_method_line_rs = self.env['account.invoicing.method.line'].search([('invoice_trigger', '=', 'picking'), 
                                                                                                         ('invoicing_method_id', '=', invoicing_method_id.id)], limit=1)
                            if invoicing_method_line_rs and invoicing_method_line_rs.payment_term_id:
                                payment_term_id = invoicing_method_line_rs.payment_term_id
                            
                        other_data2['fiscal_position_id'] = picking.partner_id.supplier_account_position_id.id
                        other_data2['payment_term_id'] = payment_term_id.id
                        other_data2['discount_management'] = picking.partner_id.purchase_discount_management
                        other_data2['discount_value'] = picking.partner_id.purchase_discount_value
                        other_data2['payment_method_id'] = picking.partner_id.purchase_payment_method_id.id
                    elif picking.partner_id.is_customer:
                        payment_term_id = picking.partner_id.property_payment_term_id
                        invoicing_method_id = picking.partner_id.sale_invoicing_method_id
                        if invoicing_method_id:
                            invoicing_method_line_rs = self.env['account.invoicing.method.line'].search([('invoice_trigger', '=', 'picking'), 
                                                                                                         ('invoicing_method_id', '=', invoicing_method_id.id)], limit=1)
                            if invoicing_method_line_rs and invoicing_method_line_rs.payment_term_id:
                                payment_term_id = invoicing_method_line_rs.payment_term_id
                                
                        other_data2['fiscal_position_id'] = picking.partner_id.property_account_position_id.id
                        other_data2['payment_term_id'] = payment_term_id.id
                        other_data2['discount_management'] = picking.partner_id.sale_discount_management
                        other_data2['discount_value'] = picking.partner_id.sale_discount_value
                        other_data2['payment_method_id'] = picking.partner_id.sale_payment_method_id.id
                    else:
                        payment_term_id = False
                        invoicing_method_id = False

                    other_data.update(other_data2)
                    invoiced_partner = False
                    if type_invoice in ('in_refund', 'in_invoice'):
                        dico_partner_address = picking.partner_id.get_partner_address(infos={'purchase_invoiced': True}, return_id=False)
                        invoiced_partner = picking.partner_id.invoiced_by and picking.partner_id or dico_partner_address and 'purchase_invoiced_partner' in dico_partner_address and dico_partner_address['purchase_invoiced_partner'] or False
                    
                    elif type_invoice in ('out_refund', 'out_invoice'):
                        dico_partner_address = picking.partner_id.get_partner_address(infos={'invoiced': True}, return_id=False)
                        invoiced_partner = picking.partner_id.can_be_charged and picking.partner_id or dico_partner_address and 'invoiced_partner' in dico_partner_address and dico_partner_address['invoiced_partner'] or False
                    
                    if not invoiced_partner:
                        raise except_orm(_('Error'), _('The partner is not billable.'))
                        
                    invoice_id = invoice_obj.create_invoice(invoiced_partner, picking.address_id, type_invoice, other_data)
                
                res += invoice_id
                first_try = True
                sale_service_line = False
                purchase_service_line = False
                backorder = picking.backorder_id and True or False
                if invoicing_method_id:
                    invoicing_method_percentage = invoicing_method_id.get_invoice_percentage('picking')
                    invoicing_method_fixed_amounts = invoicing_method_id.get_invoice_fixed_amount('picking')

                else:
                    invoicing_method_percentage = 1.0
                    invoicing_method_fixed_amounts = []
                
                # Gestion des facture anticipées en montant fixe
                for fixed_amount, product_id in invoicing_method_id.get_invoice_fixed_amount('picking'):
                    invoice_line_obj.with_context(context2).create_invoice_line(invoice_id.id, product_id, from_invoice=True, other_data=ail_other_data, forced_price_unit=fixed_amount, forced_uoi_qty=1.0)
                
                # Parcourt de tous les moves. S'ils sont liés à une vente ou un achat récupèration des infos de la vente ou de l'achat
                quantity = 0
                quantities = {}
                for line in picking.move_ids:
                    if not line.is_not_billable:
                        if line.sale_line_id:
                            delivery_types = [x.account_invoiced_on for x in line.sale_line_id.sale_order_id.invoicing_method_id.line_ids if x.invoice_trigger == 'picking']
                            if 'delivery' in delivery_types:
                                order_qty = False
                            else:
                                order_qty = True

                            quantity = (order_qty and line.sale_line_id.uoi_qty or line.uoi_qty) * invoicing_method_percentage
                            other_data = {
                                'sec_uom_qty': (order_qty and line.sale_line_id.sec_uom_qty or line.sec_uom_qty) * invoicing_method_percentage,
                                'sec_uom_id': line.sec_uom_id.id,
                                'uom_qty': (order_qty and line.sale_line_id.uom_qty or line.uom_qty) * invoicing_method_percentage,
                                'uom_id': line.uom_id.id,
                                'quantity': quantity,
                                'uoi_id': line.uoi_id.id,
                                'price_unit': line.partner_price,
                                'invoice_line_tax_ids': [(4, x.id) for x in line.sale_line_id.taxes_ids],
                                'name': line.name,
                                'section_id': line.sale_line_id.section_id.id,
                                'customer_product_name': line.sale_line_id.customer_product_name,
                                'customer_product_code': line.sale_line_id.customer_product_code,
                                'sale_order_line_id': line.sale_line_id.id,
                                'note_invoice_header': line.sale_line_id.invoice_printed_note,
                            }
                            # Facturation montant fixe
                            for fixed_amount_price_unit, fixed_amount_product_id in invoicing_method_fixed_amounts:
                                fixed_amount_data = {
                                    'sec_uom_qty': quantity and ((order_qty and line.sale_line_id.sec_uom_qty or line.sec_uom_qty) / quantity) or 1.0,
                                    'sec_uom_id': line.sec_uom_id.id,
                                    'uom_qty': quantity and ((order_qty and line.sale_line_id.uom_qty or line.uom_qty) / quantity) or 1.0,
                                    'uom_id': line.uom_id.id,
                                    'quantity': 1,
                                    'uoi_id': line.uoi_id.id,
                                    'price_unit': fixed_amount_price_unit,
                                    'invoice_line_tax_ids': [(4, x.id) for x in line.sale_line_id.taxes_ids],
                                    'name': line.name,
                                    'section_id': line.sale_line_id.section_id.id,
                                    'customer_product_name': line.sale_line_id.customer_product_name,
                                    'customer_product_code': line.sale_line_id.customer_product_code,
                                    'sale_order_line_id': line.sale_line_id.id,
                                    'note_invoice_header': line.sale_line_id.invoice_printed_note
                                }
                                invoice_line_obj.with_context(context2).create_invoice_line(invoice_id.id, fixed_amount_product_id, True, fixed_amount_data)
                                
                            # Au premier move traité, on recherche s'il y a des lignes de ventes dont le produit est un service dont on ne gère pas la livraison afin de l'ajouter à la facture
                            if first_try and not backorder:
                                sale_service_line = sale_line_obj.search([('product_id.type', '=', 'service'), 
                                                                          ('product_id.manage_service_delivery', '=', False),
                                                                          ('sale_order_id', '=', line.sale_line_id.sale_order_id.id)])
                                first_try = False
                                
                
                        elif line.purchase_line_id:
                            delivery_types = [x.account_invoiced_on for x in line.purchase_line_id.purchase_order_id.invoicing_method_id.line_ids if x.invoice_trigger == 'picking']
                            if 'delivery' in delivery_types:
                                order_qty = False
                            else:
                                order_qty = True
                                
                            quantity = (order_qty and line.purchase_line_id.uoi_qty or line.uoi_qty) * invoicing_method_percentage
                            other_data = {
                                'sec_uom_qty': (order_qty and line.purchase_line_id.sec_uom_qty or line.sec_uom_qty) * invoicing_method_percentage,
                                'sec_uom_id': line.sec_uom_id.id,
                                'uom_qty': (order_qty and line.purchase_line_id.uom_qty or line.uom_qty) * invoicing_method_percentage,
                                'uom_id': line.uom_id.id,
                                'quantity': quantity,
                                'uoi_id': line.uoi_id.id,
                                'price_unit': line.partner_price,
                                'invoice_line_tax_ids': [(4, x.id) for x in line.purchase_line_id.taxes_ids],
                                'name': line.name,
                                'purchase_section_id': line.purchase_line_id.section_id.id,
                                'customer_product_name': line.purchase_line_id.supplier_product_name,
                                'customer_product_code': line.purchase_line_id.supplier_product_code,
                                'purchase_order_line_id': line.purchase_line_id.id,
                                'note_invoice_header': line.purchase_line_id.invoice_printed_note,
                            }
                            # Facturation montant fixe
                            for fixed_amount_price_unit, fixed_amount_product_id in invoicing_method_fixed_amounts:
                                fixed_amount_data = {
                                    'sec_uom_qty': quantity and ((order_qty and line.purchase_line_id.sec_uom_qty or line.sec_uom_qty) / quantity) or 1.0,
                                    'sec_uom_id': line.sec_uom_id.id,
                                    'uom_qty': quantity and ((order_qty and line.purchase_line_id.uom_qty or line.uom_qty) / quantity) or 1.0,
                                    'uom_id': line.uom_id.id,
                                    'quantity': 1,
                                    'uoi_id': line.uoi_id.id,
                                    'price_unit': fixed_amount_price_unit,
                                    'invoice_line_tax_ids': [(4, x.id) for x in line.purchase_line_id.taxes_ids],
                                    'name': line.name,
                                    'purchase_section_id': line.purchase_line_id.section_id.id,
                                    'customer_product_name': line.purchase_line_id.supplier_product_name,
                                    'customer_product_code': line.purchase_line_id.supplier_product_code,
                                    'purchase_order_line_id': line.purchase_line_id.id,
                                    'note_invoice_header': line.purchase_line_id.invoice_printed_note,
                                }
                                invoice_line_obj.with_context(context2).create_invoice_line(invoice_id.id, fixed_amount_product_id, True, fixed_amount_data)
                                
                            if first_try and not backorder:
                                purchase_service_line = purchase_line_obj.search([('product_id.type', '=', 'service'), 
                                                                                  ('product_id.manage_service_receipt', '=', False),
                                                                                  ('purchase_order_id', '=', line.purchase_line_id.purchase_order_id.id)])
                                first_try = False
                                
                        # Sinon on récupère les infos du move uniquement pour créer la ligne de facture
                        else:
                            quantity = line.uoi_qty
                            other_data = {
                                'sec_uom_qty': line.sec_uom_qty,
                                'sec_uom_id': line.sec_uom_id.id,
                                'uom_qty': line.uom_qty,
                                'uom_id': line.uom_id.id,
                                'quantity': line.uoi_qty,
                                'uoi_id': line.uoi_id.id,
                                'price_unit': line.partner_price,
                                'name': line.name,
                            }
                            # Facturation montant fixe
                            for fixed_amount_price_unit, fixed_amount_product_id in invoicing_method_fixed_amounts:
                                fixed_amount_data = {
                                    'sec_uom_qty': quantity and (line.sec_uom_qty / quantity) or 1.0,
                                    'sec_uom_id': line.sec_uom_id.id,
                                    'uom_qty': quantity and (line.uom_qty / quantity) or 1.0,
                                    'uom_id': line.uom_id.id,
                                    'quantity': 1,
                                    'uoi_id': line.uoi_id.id,
                                    'price_unit': fixed_amount_price_unit,
                                    'name': line.name,
                                }
                                invoice_line_obj.with_context(context2).create_invoice_line(invoice_id.id, fixed_amount_product_id, True, fixed_amount_data)
                        
                        quantities[line.id] = quantity
                        # Gestion des lignes de ventes ayant un produit qui est un service dont on ne gère pas la livraison
                        if sale_service_line:
                            for service in sale_service_line:
                                service_data = {
                                    'sec_uom_qty': service.sec_uom_qty,
                                    'sec_uom_id': service.sec_uom_id.id,
                                    'uom_qty': service.uom_qty,
                                    'uom_id': service.uom_id.id,
                                    'quantity': service.uoi_qty,
                                    'uoi_id': service.uoi_id.id,
                                    'price_unit': service.price_unit,
                                    'invoice_line_tax_ids': [(4, x.id) for x in service.taxes_ids],
                                    'name': service.name,
                                    'section_id': service.section_id.id,
                                    'customer_product_name': service.customer_product_name,
                                    'customer_product_code': service.customer_product_code,
                                    'sale_order_line_id': service.id,
                                }
                                invoice_line_obj.with_context(context2).create_invoice_line(invoice_id.id, service.product_id, True, service_data)
                                sale_service_line = False
                        
                        # Gestion des lignes d'achat ayant un produit qui est un service dont on ne gère pas la livraison
                        if purchase_service_line:
                            for purchase_service in purchase_service_line:
                                service_data = {
                                    'sec_uom_qty': purchase_service.sec_uom_qty,
                                    'sec_uom_id': purchase_service.sec_uom_id.id,
                                    'uom_qty': purchase_service.uom_qty,
                                    'uom_id': purchase_service.uom_id.id,
                                    'quantity': purchase_service.uoi_qty,
                                    'uoi_id': purchase_service.uoi_id.id,
                                    'price_unit': purchase_service.price_unit,
                                    'invoice_line_tax_ids': [(4, x.id) for x in purchase_service.taxes_ids],
                                    'name': purchase_service.name,
                                    'purchase_section_id': purchase_service.section_id.id,
                                    'customer_product_name': purchase_service.supplier_product_name,
                                    'customer_product_code': purchase_service.supplier_product_code,
                                    'purchase_order_line_id': purchase_service.id,
                                }
                                invoice_line_obj.with_context(context2).create_invoice_line(invoice_id.id, purchase_service.product_id, True, service_data)
                                purchase_service_line = False
                        
                        invoice_line_id = invoice_line_obj.with_context(context2).create_invoice_line(invoice_id.id, line.product_id, True, other_data)
                        line.write({'invoice_line_id': invoice_line_id.id})

                # On calcule la TVA
                invoice_id._onchange_invoice_line_ids()
                # On lance le onchange de l'adresse
                invoice_id._onchange_address_id()
                picking.write({'invoice_state': 'invoiced'})
                if invoice_id:
                    # Gestion des factures anticipées s'il reste un montant de la facture anticipée à répartir
                    if remaining_advanced_amount:
                        if sale_order:
                            order_type = 'sale'
                            order = sale_order
                        elif purchase_order: 
                            order_type = 'purchase'
                            order = purchase_order
                        else:
                            order_type = False
                            order = False
                        
                        invoice_obj.generate_anticipated_invoice_line(order_type, invoice_id, remaining_advanced_amount, order)
                    
                    # 2ème boucle car doit etre lancé apres generate_anticipated_invoice_line
                    first = True
                    for line in picking.move_ids:
                        if not line.is_not_billable and balance:
                            if line.sale_line_id:
                                invoice_obj.generate_auto_anticipated_invoice_line('sale', invoice_id, line.sale_line_id, line.sale_line_id.uoi_qty and (quantities.get(line.id, 0.0) / line.sale_line_id.uoi_qty) or 0.0)
                                # Au premier move traité, recherche lignes de ventes dont le produit est un service dont on ne gère pas la livraison afin de l'ajouter à la facture
                                if first and not backorder:
                                    first = False
                                    sale_service_line_rcs = sale_line_obj.search([('product_id.type', '=', 'service'), 
                                                                                  ('product_id.manage_service_delivery', '=', False),
                                                                                  ('sale_order_id', '=', line.sale_line_id.sale_order_id.id)])
                                    for sale_service_line_rc in sale_service_line_rcs:
                                        invoice_obj.generate_auto_anticipated_invoice_line('sale', invoice_id, sale_service_line_rc, sale_service_line_rc.uoi_qty and (sale_service_line_rc.uoi_qty * invoicing_method_percentage / sale_service_line_rc.uoi_qty) or 0.0)
                            
                            if line.purchase_line_id:
                                invoice_obj.generate_auto_anticipated_invoice_line('purchase', invoice_id, line.purchase_line_id, line.purchase_line_id.uoi_qty and (quantities.get(line.id, 0.0) / line.purchase_line_id.uoi_qty) or 0.0)
                                # Au premier move traité, recherche lignes d'achat dont le produit est un service dont on ne gère pas la reception afin de l'ajouter à la facture
                                if first and not backorder:
                                    first = False
                                    purchase_service_line_rcs = purchase_line_obj.search([('product_id.type', '=', 'service'), 
                                                                                          ('product_id.manage_service_delivery', '=', False),
                                                                                          ('purchase_order_id', '=', line.purchase_line_id.purchase_order_id.id)])
                                    for purchase_service_line_rc in purchase_service_line_rcs:
                                        invoice_obj.generate_auto_anticipated_invoice_line('purchase', invoice_id, purchase_service_line_rc, purchase_service_line_rc.uoi_qty and (purchase_service_line_rc.uoi_qty * invoicing_method_percentage / purchase_service_line_rc.uoi_qty) or 0.0)
                                        
        return res
    
        
    @api.multi
    def button_create_invoice(self):
        """
            Bouton qui permet de créer la facture à partir d'un picking et qui retourne la facture créée
        """
        invoice_rcs = self.create_invoice()
        if invoice_rcs:
            for invoice in invoice_rcs:
                data_pool = self.env['ir.model.data']
                
                if invoice.type == 'in_invoice':
                    action_model, action_id = data_pool.get_object_reference('account', 'action_invoice_tree2')
                elif invoice.type == 'in_refund':
                    action_model, action_id = data_pool.get_object_reference('account_openprod', 'action_supplier_refund')
                elif invoice.type == 'out_invoice':
                    action_model, action_id = data_pool.get_object_reference('account', 'action_invoice_tree1')
                else:
                    action_model, action_id = data_pool.get_object_reference('account_openprod', 'action_customer_refund')
                
                if action_model:
                    action_pool = self.env[action_model]
                    action = action_pool.browse(action_id).read()[0]
                    action['res_id'] = invoice.id
                    action['domain'] = [('id', 'in', invoice_rcs.ids)]
                    res = action
                    return res
        
        return True
        
        
    
class stock_quality_control(models.Model):
    """ 
    Stock quality control
    """
    _inherit = 'stock.quality.control'
    
    @api.model
    def _type_get(self):
        res = super(stock_quality_control, self)._type_get()
        res.extend([('pdf_purchase_mail', _('Purchase mail (PDF)')),
                    ('pdf_sale_mail', _('Sale mail (PDF)'))])
        return res