# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm
from openerp.addons.base_openprod.common import get_form_view

class change_delivery_address(models.TransientModel):
    """ 
        Wizard to change the sale delivery address
    """
    _name = 'change.delivery.address'
    _description = 'Modification of the sale delivery address'
    
    @api.model
    def _sale_invoice_postage_get(self):
        return [
                ('never', _('Never')),
                ('always', _('Always')),
                ('threshold', _('< Threshold')),
                       ]
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    sale_id = fields.Many2one('sale.order', string='Sale', required=False, ondelete='set null')
    partner_id = fields.Many2one('res.partner', string='Partner', required=False, ondelete='set null')
    delivered_customer_id = fields.Many2one('res.partner', string='Delivered customer', required=True, ondelete='cascade', 
                                          domain=[('is_company', '=', True), ('can_be_delivered', '=', True), ('is_customer', '=', True), 
                                                  ('state', 'not in', ['prospect', 'stopped'])])
    delivered_name = fields.Char(string='Name', size=32, required=True)
    delivered_street = fields.Char(string='Street', size=32, required=False)
    delivered_street2 = fields.Char(string='Street 2', size=32, required=False)
    delivered_street3 = fields.Char(string='Street 3', size=32, required=False)
    delivered_zip = fields.Char(string='Zip', size=24, required=False)
    delivered_city = fields.Char(string='City', size=32, required=False)
    delivered_region_id = fields.Many2one('res.region', string='Region', required=False, ondelete='cascade')
    delivered_country_id = fields.Many2one('res.country', string='Country', required=True, ondelete='cascade')
    delivered_address_id = fields.Many2one('address', string='Delivered address', required=True, ondelete='cascade')
    sale_account_system_id = fields.Many2one('account.fiscal.position', string='Account system', required=True, ondelete='set null')
    transport_delay = fields.Integer(string='Transport delay', default=0, required=False, help="The transport delay come from "
                                     "the delivered partner.")
    sale_incoterm_id = fields.Many2one('stock.incoterms', string='Incoterm', required=False, ondelete='cascade', help='Incoterm which '
                                       'stands for \'International Commercial terms\' implies its a series of sales terms which are used '
                                       'in the commercial transaction.')
    sale_invoice_postage = fields.Selection('_sale_invoice_postage_get', string='Invoice postage', required=False)
    sale_threshold = fields.Float(string='Threshold', default=0.0, required=False)
    sale_forwarding_agent_id = fields.Many2one('res.partner', string='Forwarding Agent', required=False, ondelete='cascade', 
                                               domain=[('is_company', '=', True)])
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(change_delivery_address, self).default_get(fields_list=fields_list)
        sale_id = self.env.context.get('sale_id')
        if sale_id and self.env.context.get('active_model') == 'sale.order':
            sale = self.env['sale.order'].browse(sale_id)
            if sale:
                res = {
                    'partner_id': sale.partner_id.id,
                    'delivered_customer_id': sale.delivered_customer_id.id,
                    'delivered_street': sale.delivered_street,
                    'delivered_street2': sale.delivered_street2,
                    'delivered_street3': sale.delivered_street3,
                    'delivered_zip': sale.delivered_zip,
                    'delivered_city': sale.delivered_city,
                    'delivered_region_id': sale.delivered_region_id and sale.delivered_region_id.id or False,
                    'delivered_country_id': sale.delivered_country_id.id,
                    'delivered_name': sale.delivered_name,
                    'delivered_address_id': sale.delivered_address_id.id,
                    'sale_id':  sale_id,
                    'sale_account_system_id': sale.sale_account_system_id.id,
                    'transport_delay': sale.transport_delay,
                    'sale_incoterm_id': sale.sale_incoterm_id.id,
                    'sale_invoice_postage': sale.sale_invoice_postage,
                    'sale_threshold': sale.sale_threshold,
                    'sale_forwarding_agent_id': sale.sale_forwarding_agent_id.id,
                       }
                
        return res
    
    
    @api.onchange('delivered_customer_id')
    def _onchange_delivered_customer_id(self):
        """
            Au changement de client, on va récupérer l'adresse d'expédition et les informations de l'onglet livraison
        """
        if self.delivered_customer_id:
            res = {'warning': {}}
            make_onchange = True
            if self.delivered_customer_id.is_company and self.delivered_customer_id.state in ['prospect', 'stopped']:
                res['warning'] = {'title': _('Warning'), 'message': _('The selected delivered customer is not qualified to be charged, '
                                                                      'his state must be "qualified"')}
                make_onchange = False
            
            partner_rs = self.partner_id
            #Si le client est un contact, on récupère le client commandeur qui lui est lié
            if not partner_rs.is_company and partner_rs.parent_id:
                partner_rs = partner_rs.parent_id
            
            partner_verif = self.env['res.partner.type'].search([('partner_type', '=', 'can_be_delivered'), 
                                                                 ('partner_type_id', '=', self.delivered_customer_id.id),
                                                                 ('partner_id', '=', partner_rs.id)], limit=1)
            if not partner_verif and self.delivered_customer_id != self.partner_id:
                res['warning'] = {'title': _('Warning'), 'message': _('The selected delivered customer is not in the delivered list of the partner'
                                                                      ' who orders')}
                make_onchange = False
            
            if not make_onchange:
                self.delivered_customer_id = False
                self.delivered_address_id = False
                self.sale_incoterm_id = False
                self.sale_invoice_postage = False
                self.sale_threshold = 0
                self.sale_forwarding_agent_id = False
                self.transport_delay = 0
                return res
                
            delivered_customer = self.delivered_customer_id
            res = self.env['sale.order'].onchange_delivered_customer_id(delivered_customer)
            for k,v in res.iteritems():
                if k != 'delivered_contact_id':
                    self[k] = v
    
    
    @api.onchange('delivered_address_id')
    def _onchange_delivered_address_id(self):
        """
            Au changement d'adresse d'expédition, on récupère tous les détails de l'adresse
        """
        res = self.env['sale.order'].onchange_delivered_address_id(self.delivered_address_id)
        for k,v in res.iteritems():
            self[k] = v
    
    
    @api.multi
    def change_delivery_address(self):
        """
            Fonction permettant de modifier l'adresse de livraison d'une commande de vente
        """
        sale = self.sale_id
        if sale:
            invoice_rs_list = self.env['account.invoice']
            #Modification de la vente
            res = sale.onchange_delivered_country_id(sale.invoiced_customer_id, self.delivered_country_id)
            tva_number = res.get('tva_number', '')
            sale.write({
                        'delivered_customer_id': self.delivered_customer_id.id,
                        'delivered_street': self.delivered_street,
                        'delivered_street2': self.delivered_street2,
                        'delivered_street3': self.delivered_street3,
                        'delivered_zip': self.delivered_zip,
                        'delivered_city': self.delivered_city,
                        'delivered_region_id': self.delivered_region_id and self.delivered_region_id.id or False,
                        'delivered_country_id': self.delivered_country_id.id,
                        'delivered_address_id': self.delivered_address_id.id,
                        'delivered_name': self.delivered_name,
                        'sale_account_system_id': self.sale_account_system_id.id,
                        'transport_delay': self.transport_delay,
                        'sale_incoterm_id': self.sale_incoterm_id.id,
                        'sale_invoice_postage': self.sale_invoice_postage,
                        'sale_threshold': self.sale_threshold,
                        'sale_forwarding_agent_id': self.sale_forwarding_agent_id.id,
                        'tva_number': tva_number,
                        })
            
            #Gestion du changement de la position fiscale
            for sale_line in sale.order_line_ids:
                sale_line.taxes_ids = self.sale_account_system_id.map_tax(sale_line.product_id.sale_taxes_ids)
            
            sale._onchange_order_line_ids()
            for invoice_line in sale.invoice_line_ids:
                if invoice_line.invoice_id not in invoice_rs_list:
                    invoice_line.invoice_id.write({'fiscal_position_id': self.sale_account_system_id.id,
                                                   'tva_number': tva_number})
                    invoice_rs_list += invoice_line.invoice_id
                
                invoice_line.invoice_line_tax_ids =  self.sale_account_system_id.map_tax(invoice_line.product_id.sale_taxes_ids)
            
            for invoice in invoice_rs_list:
                invoice._onchange_invoice_line_ids()
                
            #Modification des pickings
            picking_rs = sale.delivery_note_ids
            picking_rs.write({
                              'street': self.delivered_street,
                              'street2': self.delivered_street2,
                              'street3': self.delivered_street3,
                              'zip': self.delivered_zip,
                              'city': self.delivered_city,
                              'region_id': self.delivered_region_id and self.delivered_region_id.id or False,
                              'country_id': self.delivered_country_id.id,
                              'address_id': self.delivered_address_id.id,
                              'partner_id': self.delivered_customer_id.id,
                              'incoterm_id': self.sale_incoterm_id.id,
                              'invoice_postage': self.sale_invoice_postage,
                              'threshold': self.sale_threshold,
                              'forwarding_agent_id': self.sale_forwarding_agent_id.id,
                              'delivery_delay': self.transport_delay,
                              })

        return {'type':'ir.actions.act_window_view_reload'}
        
        
        
class change_accounting_information(models.TransientModel):
    """ 
        Wizard to change the accounting information
    """
    _name = 'change.accounting.information'
    _description = 'Modification of the accounting information'
    
    @api.model
    def _sale_send_method_get(self):
        return [
                ('manual', _('Manual printing')),
                ('printer', _('Printer')),
                ('edi', _('EDI')),
                ('email', _('Mail')),
                       ]
        
        
    @api.model
    def _invoices_period_get(self):
        return [
                ('end_week', _('End of week')),
                ('end_month', _('End of month')),
                       ]
    
    
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    sale_id = fields.Many2one('sale.order', string='Sale', required=False, ondelete='set null')
    partner_id = fields.Many2one('res.partner', string='Partner', required=False, ondelete='set null')
    invoiced_customer_id = fields.Many2one('res.partner', string='Invoiced customer', required=True, ondelete='set null', 
                                           domain=[('can_be_charged', '=', True)])
    invoicing_address_id = fields.Many2one('address', string='Invoicing address', required=False, ondelete='set null')
    paid_customer_id = fields.Many2one('res.partner', string='Payer customer name', required=True, ondelete='set null', 
                                       domain=[('can_paid', '=', True)])
    payment_id = fields.Many2one('payment.method', string='Payment', required=True, ondelete='cascade', help="Comes from the customer who pays"
                                 " the order")
    payment_term_id = fields.Many2one('account.payment.term', string='Payment term', required=True, ondelete='cascade', help="Comes from the "
                                      "customer who pays the order")
    discount = fields.Boolean(string='Discount', default=False, help="Comes from the customer who pays the order")
    discount_value = fields.Float(string='Discount value in percentage', default=0.0, required=False)
    max_delay = fields.Integer(string='Maximal delay applicated', default=0, required=False)
    sale_send_method = fields.Selection('_sale_send_method_get', string='Send method', required=False)
    group_invoices = fields.Boolean(string='Group invoices', default=False, help="Comes from the invoiced customer")
    invoices_period = fields.Selection('_invoices_period_get', string='Invoices period', required=False)
    locked_invoice = fields.Boolean(string='Locked invoice', default=False, help="Comes from the invoiced customer")
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(change_accounting_information, self).default_get(fields_list=fields_list)
        sale_id = self.env.context.get('sale_id')
        if sale_id and self.env.context.get('active_model') == 'sale.order':
            sale = self.env['sale.order'].browse(sale_id)
            if sale:
                res = {
                       'partner_id': sale.partner_id.id,
                       'payment_id': sale.payment_id.id,
                       'payment_term_id': sale.payment_term_id.id,
                       'discount': sale.discount,
                       'discount_value': sale.discount_value,
                       'max_delay': sale.max_delay,
                       'sale_send_method': sale.sale_send_method,
                       'group_invoices': sale.group_invoices,
                       'invoices_period': sale.invoices_period,
                       'locked_invoice': sale.locked_invoice,
#                        'payment_type': sale.payment_type,
                       'sale_id': sale_id,
                       'paid_customer_id': sale.paid_customer_id.id,
                       'invoiced_customer_id': sale.invoiced_customer_id.id,
                       'invoicing_address_id': sale.invoicing_address_id.id,
                       }
                
        return res
    
    
    @api.onchange('invoiced_customer_id')
    def _onchange_invoiced_customer_id(self):
        """
            Au changement de client, on va récupérer les informations
            relatives à la facturation de l'onglet de comptabilité
        """
        invoiced_customer = self.invoiced_customer_id
        if invoiced_customer:
            res = {'warning': {}}
            make_onchange = True
            #On vérifie que l'état du facturé soit qualifié
            if self.invoiced_customer_id.is_company and self.invoiced_customer_id.state in ['prospect', 'stopped']:
                res['warning'] = {'title': _('Warning'), 'message': _('The selected invoiced customer is not qualified to be charged, '
                                                                      'his state must be "qualified"')}
                make_onchange = False
            
            partner_rs = self.partner_id
            #Si le client est un contact, on récupère le client commandeur qui lui est lié
            if not partner_rs.is_company and partner_rs.parent_id:
                partner_rs = partner_rs.parent_id
                
            #On vérifie que le facturé sélectionné fasse partie de la liste de partenaires facturé 
            partner_verif = self.env['res.partner.type'].search([('partner_type', '=', 'can_be_charged'), 
                                                                 ('partner_type_id', '=', invoiced_customer.id),
                                                                 ('partner_id', '=', partner_rs.id)], limit=1)
            if not partner_verif and invoiced_customer != self.partner_id:
                res['warning'] = {'title': _('Warning'), 'message': _('The selected invoiced customer is not in the invoiced list of the partner'
                                                                      ' who orders')}
                make_onchange = False
            
            if not make_onchange:
                self.invoiced_customer_id = False
                self.invoicing_address_id = False
                return res
            
            self.invoicing_address_id = invoiced_customer.address_id and invoiced_customer.address_id.id or False
            res2 = self.sale_id.onchange_invoiced_customer_id(invoiced_customer)
            if 'tva_number' in res2:
                del res2['tva_number']
            
                
            for k,v in res2.iteritems():
                self[k] = v
    
    
    
    @api.onchange('paid_customer_id')
    def _onchange_paid_customer_id(self):
        """
            Au changement du client payeur, on va remplir toutes les informations concernant
            le paiement dans l'onglet de comptabilité 
        """
        paid_customer = self.paid_customer_id
        if paid_customer:
            make_onchange = True
            res = {'warning': {}}
            #On vérifie que le partenaire soit dans l'état qualifié
            if paid_customer.is_company and paid_customer.state in ['prospect', 'stopped']:
                res['warning'] = {'title': _('Warning'), 'message': _('The Customer selected to pay the order is not qualified to pay '
                                                                      'his state must be "qualified"')}
                make_onchange = False
            
            partner_rs = self.partner_id
            #Si le client est un contact, on récupère le client commandeur qui lui est lié
            if not partner_rs.is_company and partner_rs.parent_id:
                partner_rs = partner_rs.parent_id
            
            #On vérifie que le partenaire soit payeur du partenaire commandeur
            partner_verif = self.env['res.partner.type'].search([('partner_type', '=', 'can_paid'), 
                                                                 ('partner_type_id', '=', paid_customer.id),
                                                                 ('partner_id', '=', partner_rs.id)], limit=1)
            if not partner_verif and paid_customer != self.partner_id:
                res['warning'] = {'title': _('Warning'), 'message': _('The customer selected to pay the order is not in the '
                                                                      'paid list of the partner who orders')}
                make_onchange = False
            
            if not make_onchange:
                self.paid_customer_id = False
                self.payment_id = False
                self.payment_term_id = False
                self.discount = False
                self.discount_value = 0
                self.max_delay = 0
                return res
            
            res2 = self.sale_id.onchange_paid_customer_id(paid_customer)
            for k,v in res2.iteritems():
                if k != 'invoicing_method_id':
                    self[k] = v
        
    
    @api.multi
    def change_accounting_information(self):
        """
            Fonction permettant de modifier les informations comptable d'une vente
        """
        sale = self.sale_id
        if sale:
            #Message d'erreur si le type de condition de paiement, la méthode de déclenchement
            #de facturation et la quantité facturée ne sont pas les mêmes que celles de la vente
#             wiz_payment_type = self.payment_term_id.payment_type
#             wiz_invoiced_on = self.payment_term_id.sale_account_invoiced_on
#             if (wiz_payment_type != sale.payment_type) or (wiz_invoiced_on != sale.sale_account_invoiced_on):
#                 raise except_orm(_('The invoice quantity, invoice trigger method and payment type must be the same for '
#                                    'the sale and the chosen partners in the change wizard'))
            
            wiz_invoiced_customer = self.invoiced_customer_id
            invoice_list = self.env['account.invoice']
            res = sale.onchange_delivered_country_id(self.invoiced_customer_id, sale.delivered_country_id)
            tva_number = res.get('tva_number', '')
            sale.write({'payment_id': self.payment_id.id,
                        'payment_term_id': self.payment_term_id.id,
                        'discount': self.discount,
                        'discount_value': self.discount_value,
                        'max_delay': self.max_delay,
                        'sale_send_method': self.sale_send_method,
                        'group_invoices': self.group_invoices,
                        'invoices_period': self.invoices_period,
                        'lock_invoice': self.locked_invoice,
                        'invoiced_customer_id': wiz_invoiced_customer.id,
                        'paid_customer_id': self.paid_customer_id.id,
                        'invoicing_address_id': self.invoicing_address_id.id,
                        'tva_number': tva_number,
                        })
            for invoice_line in sale.invoice_line_ids:
                if not invoice_line.invoice_id in invoice_list:
                    invoice_list += invoice_line.invoice_id
            
            #On récupère les valeurs sélectionnées dans le wizard
            invoice_res = {'partner_id': wiz_invoiced_customer.id,
                           'payment_term_id': self.payment_term_id.id,
                           'payment_method_id': self.payment_id.id,
                           'discount_management': self.discount,
                           'max_delay': self.max_delay,
                           'discount_value': self.discount_value,
                           'group_invoices': self.group_invoices,
                           'invoices_period': self.invoices_period,
                           'lock_invoice': self.locked_invoice,
                           'address_id': self.invoicing_address_id.id,
                           'paid_by_id': self.paid_customer_id.id,
                           'delivery_partner_id': sale.delivered_customer_id.id,
                           'partner_order_id': sale.partner_id.id,
                           'tva_number': tva_number,
                           }
            #Pour chaque facture, on récupère les valeurs du onchange que l'on met à jour avec les
            #valeurs du wizard et on applique les modifications
            for invoice_rs in invoice_list:
                write_res = invoice_list.onchange_invoice_partner_id(wiz_invoiced_customer, invoice_rs.type)
                write_res.update(invoice_res)
                invoice_rs.write(write_res) 
                invoice_rs._onchange_address_id()
                
            #Deuxième write pour prendre en compte les modifications éventuellement saisies dans le wizard
            if self.payment_term_id.payment_type == 'before_delivery':
                picking_rs = sale.delivery_note_ids
                picking_rs.write({'lock': True})
                     
        return {'type':'ir.actions.act_window_view_reload'}
        
        
        
class change_note(models.TransientModel):
    """ 
        Wizard to change the note
    """
    _name = 'change.note'
    _description = 'Modification of the note'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    sale_id = fields.Many2one('sale.order', string='Sale', required=False, ondelete='set null')
    inter_note = fields.Text(string='Intern note / Preparation note')
    work_note = fields.Text(string='Printed work note')
    delivery_note = fields.Html(string='Note on delivery note')
    invoice_note = fields.Html(string='Invoice note')
    customer_order_note = fields.Html(string='Note printed on customer order')
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(change_note, self).default_get(fields_list=fields_list)
        sale_id = self.env.context.get('sale_id')
        if sale_id and self.env.context.get('active_model') == 'sale.order':
            sale = self.env['sale.order'].browse(sale_id)
            if sale:
                res = {
                       'sale_id': sale_id,
                       'inter_note': sale.inter_note,
                       'work_note': sale.work_note,
                       'delivery_note': sale.delivery_note,
                       'invoice_note': sale.invoice_note,
                       'customer_order_note': sale.customer_order_note,
                       }
                
        return res
    
    
    def modification_mrp(self, sale, work_note):
        """
            Fonction permettant de propager la modification de la note dans les OFs et OTs
        """
        return True

    
    @api.multi
    def change_note(self):
        """
            Fonction permettant de modifier les notes d'une vente
        """
        for wiz in self:
            sale = wiz.sale_id
            if sale:
                invoice_list = self.env['account.invoice']
                sale.write({
                            'inter_note': wiz.inter_note,
                            'work_note': wiz.work_note,
                            'delivery_note': wiz.delivery_note,
                            'invoice_note': wiz.invoice_note,
                            'customer_order_note': wiz.customer_order_note,
                            })
                for invoice_line in sale.invoice_line_ids:
                    if not invoice_line.invoice_id in invoice_list:
                        invoice_list += invoice_line.invoice_id
    
                invoice_list.write({
                                  'note_invoice_header': wiz.invoice_note,
                                  'note_invoice_intern': wiz.inter_note,
                                  })
                picking_rs = sale.delivery_note_ids
                picking_rs.write({
                                  'internal_note': wiz.inter_note,
                                  'printed_note': wiz.delivery_note,
                                  })
                
                wiz.modification_mrp(sale, wiz.work_note)
                
        return {'type':'ir.actions.act_window_view_reload'}
    
    
    
class change_line_information(models.TransientModel):
    """ 
        Wizard to change the sale line information
    """
    _name = 'change.line.information'
    _description = 'Modification of the sale line information'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    sale_line_id = fields.Many2one('sale.order.line', string='Sale line', required=False, ondelete='set null')
    requested_date = fields.Date(string='Requested date', required=True)
    confirmed_departure_date = fields.Date(string='Confirmed departure date (after planning)', required=True)
    name = fields.Text(string='Description', required=True)
    price_unit = fields.Float(string='Price unit', default=0.0, digits=dp.get_precision('Product price'), 
                              required=True)
    internal_note = fields.Text(string='Internal note')
    delivery_printed_note = fields.Text(string='Note printed on the delivery note line')
    invoice_printed_note = fields.Text(string='Note printed on the invoice line')
    order_printed_note = fields.Text(string='Product note printed on order')
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(change_line_information, self).default_get(fields_list=fields_list)
        sale_line_id = self.env.context.get('sale_line_id')
        if sale_line_id and self.env.context.get('active_model') == 'sale.order.line':
            sale_line = self.env['sale.order.line'].browse(sale_line_id)
            if sale_line:
                res = {
                       'sale_line_id': sale_line.id,
                       'requested_date': sale_line.requested_date,
                       'confirmed_departure_date': sale_line.confirmed_departure_date,
                       'name': sale_line.name,
                       'price_unit': sale_line.price_unit,
                       'internal_note': sale_line.internal_note,
                       'delivery_printed_note': sale_line.delivery_printed_note,
                       'invoice_printed_note': sale_line.invoice_printed_note,
                       'order_printed_note': sale_line.order_printed_note,
                       }
                
        return res
    
    
    def prepar_sale_line_vals(self):
        return {
                'requested_date': self.requested_date,
                'confirmed_departure_date': self.confirmed_departure_date,
                'name': self.name,
                'price_unit': self.price_unit,
                'internal_note': self.internal_note,
                'delivery_printed_note': self.delivery_printed_note,
                'invoice_printed_note': self.invoice_printed_note,
                'order_printed_note': self.order_printed_note,
              }
    
    
    def prepar_invoice_line_vals(self):
        return {
                  'name': self.name,
                  'price_unit': self.price_unit,
                  'note_invoice_header': self.invoice_printed_note,
                  'note_invoice_intern': self.internal_note,
                  }
        
        
    @api.multi
    def change_line_information(self):
        """
            Fonction permettant de modifier les informations d'une ligne de vente
        """
        sale_line = self.sale_line_id
        invoice_list = self.env['account.invoice']
        if sale_line:
            sale_vals = self.prepar_sale_line_vals()
            sale_line.write(sale_vals)
            sale_line._onchange_requested_date()
            sale_line.sale_order_id._onchange_order_line_ids()
            move_rs = sale_line.stock_move_ids
            date = sale_line.confirmed_departure_date or sale_line.departure_date
            move_rs.write({
                            'name': self.name,
                            'date_expected': date,
                            'date': date,
                            'priority_date': date,
                            'partner_price': self.price_unit,
                            'note': self.internal_note,
                            })
            
            
            move_label_rcs = self.env['stock.move.label']
            for move in move_rs:
                if move.state == 'done':
                    move_label_rcs |= move.move_label_ids
            
            if move_label_rcs:
                move_label_rcs.write({'done_date': date})
            
            
            for invoice_line in sale_line.invoice_line_ids:
                if invoice_line.invoice_id not in invoice_list:
                    invoice_list += invoice_line.invoice_id
                
                invoice_line_vals = self.prepar_invoice_line_vals()
                invoice_line.write(invoice_line_vals)

            for invoice in invoice_list:    
                invoice._onchange_invoice_line_ids()
            
        return {'type':'ir.actions.act_window_view_reload'}
        
        
        
class change_account_system(models.TransientModel):
    """ 
        Wizard to change the account system
    """
    _name = 'change.account.system'
    _description = 'Modification of the account system'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    sale_id = fields.Many2one('sale.order', string='Sale', required=False, ondelete='set null')
    sale_account_system_id = fields.Many2one('account.fiscal.position', string='Account system', required=True, ondelete='set null')
    
    @api.model
    def default_get(self, fields_list):
        res = super(change_account_system, self).default_get(fields_list=fields_list)
        sale_id = self.env.context.get('sale_id')
        if sale_id and self.env.context.get('active_model') == 'sale.order':
            sale = self.env['sale.order'].browse(sale_id)
            if sale:
                res = {
                       'sale_id': sale.id,
                       'sale_account_system_id': sale.sale_account_system_id.id,
                       }
                
        return res
    
    
    @api.multi
    def change_account_system(self):
        """
            Fonction permettant de modifier la position fiscale d'une vente et de sa facture
            et de recalculer les taxes
        """
        sale = self.sale_id
        if sale:
            invoice_rs_list = self.env['account.invoice']
            sale.write({'sale_account_system_id': self.sale_account_system_id.id})
            for sale_line in sale.order_line_ids:
                sale_line.taxes_ids = self.sale_account_system_id.map_tax(sale_line.product_id.sale_taxes_ids)
            
            sale._onchange_order_line_ids()
            for invoice_line in sale.invoice_line_ids:
                if invoice_line.invoice_id not in invoice_rs_list:
                    invoice_line.invoice_id.write({'fiscal_position_id': self.sale_account_system_id.id})
                    invoice_rs_list += invoice_line.invoice_id
                
                invoice_line.invoice_line_tax_ids =  self.sale_account_system_id.map_tax(invoice_line.product_id.sale_taxes_ids)
            
            for invoice in invoice_rs_list:
                invoice._onchange_invoice_line_ids()
                
        return {'type':'ir.actions.act_window_view_reload'}
    