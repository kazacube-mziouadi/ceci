# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.addons.base_openprod import utils
from datetime import datetime
import calendar
import openerp.addons.decimal_precision as dp
import json
from openerp.exceptions import ValidationError


# mapping invoice type to refund type
TYPE2REFUND = {
    'out_invoice': 'out_refund',        # Customer Invoice
    'in_invoice': 'in_refund',          # Supplier Invoice
    'out_refund': 'out_invoice',        # Customer Refund
    'in_refund': 'in_invoice',          # Supplier Refund
}


class invoice_payment_term_line(models.Model):
    """ 
        Payment term lines for invoice 
    """
    _name = 'invoice.payment.term.line'
    _description = 'Payment term lines for invoice'
    _rec_name = 'due_date'
    _order = 'sequence asc'
        
    @api.one
    @api.depends('amount', 'invoice_id', 'invoice_id.payment_ids')
    def _compute_remaining_amount(self):
        """
            Calcul du montant restant
        """
        actual_remaining_amount = self.amount
        invoice_rcs = self.invoice_id
        #Calcul du total payé
        total_payment = invoice_rcs.amount_total - invoice_rcs.residual
        #Recherche des lignes précédentes
        previous_line_group = self.search_group(fields=['amount'], 
                                                groupby=[], 
                                                args=[('invoice_id', '=', invoice_rcs.id), ('sequence', '<', self.sequence)],
                                                sum='amount',
                                                return_dict=True,
                                                without_order=True)
        
        actual_remaining_amount += previous_line_group and previous_line_group[0]['amount'] or 0.0
        actual_remaining_amount -= total_payment
        self.remaining_amount = actual_remaining_amount > 0 and actual_remaining_amount or 0.0
        
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    due_date = fields.Date(string='Due date')
    sequence = fields.Integer(string='Sequence', default=0, required=False)
    amount = fields.Float(string='Amount', default=0.0, required=False)
    remaining_amount = fields.Float(string='Remaining amount', compute='_compute_remaining_amount', required=False)
    invoice_id = fields.Many2one('account.invoice', string='Invoice', required=False, ondelete='cascade')
    
    

class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    
    @api.model
    def _communication_method_get(self):
        return [
                ('fax', _('Fax')),
                ('printer', _('Printer')),
                ('email', _('Email')),
                       ]
        
        
    @api.model
    def _invoices_period_get(self):
        return [
                ('end_week', _('End of week')),
                ('end_month', _('End of month')),
                       ]
        
        
    @api.model
    def _invoice_trigger_get(self):
        return [
                ('picking', _('To the delivery')),
                ('manual', _('On demand')),
                ('postpaid', _('On the order')),
                       ]
    
    
    @api.one
    @api.depends('contact_ids', 'communication_method', 'partner_id')
    def _compute_communication_value(self):
        if self.partner_id:
            self.communication_value = self.env['res.partner'].calcul_value_com(self.contact_ids, 
                                                                                     self.partner_id, self.communication_method)
        else:
            self.communication_value = ''
    
    
    @api.one
    def _compute_invoice_payment_term_lines(self):
        """
            True si inv_term_line_ids doit être affiché
        """
        see_inv_term_line = False
        payment_term = self.payment_term_id
        if self.date_invoice and self.payment_term_id and self.state in ('open', 'paid'):
            if len(payment_term.line_ids) > 1:
                see_inv_term_line = True
         
        self.see_inv_term_line = see_inv_term_line
    
    
    @api.one
    @api.depends('paid_by_id', 'residual')
    def _compute_available_amount(self):
        """
            Fonction permettant de calculer le montant total des écritures disponibles
            pour le lettrage du partenaire payeur de la facture
        """
        available_amount = 0
        if self.residual > 0 and self.move_id:
            context2 = {}
            reconcile_partial_list = []
            context2.update(self.env.context)
            credit_search = False
            debit_search = False
            #Dictionnaire permettant de récupérer les bons mouvements
            type_dict = {'out_invoice': 'out_refund',
                         'in_refund': 'in_invoice',
                         'out_refund': 'out_invoice',
                         'in_invoice': 'in_refund'}
            #On récupère les partenaires
            partner_ids = [self.paid_by_id.id]
            partner_ids.append(self.partner_id.id)
            args = [('reconcile_id','=',False), ('account_id.reconcile','=',True), 
                    ('partner_id', 'in', partner_ids)]
            #On récupère le bon type de montant en fonction du type de la facture ou de l'avoir
            if self.type in ['out_invoice', 'in_refund']:
                credit_search = True
                args.append(('credit', '>', 0))
            elif self.type in ['out_refund', 'in_invoice']:
                debit_search = True
                args.append(('debit', '>', 0))
                
            #On recherche toutes les écritures comptables non lettrées du partenaire
            partner_move_line_rs = self.env['account.move.line'].search(args)
            #On récupère la devise de la société pour la comparer avec la devise de l'écriture
            company_currency = self.env.user.company_id.currency_id or False
            if company_currency: 
                for move_line in partner_move_line_rs:
                    can_reconcile = True
                    if move_line.reconcile_partial_id and move_line.reconcile_partial_id.id in reconcile_partial_list:
                        continue
                    
                    if not move_line.invoice or move_line.invoice.type in type_dict[self.type]:
                        move_currency = move_line.currency_id or move_line.account_id.currency_id or False 
                        #Conversion du montant dans la devise de la société en cas de devise différente
                        move_amount = move_line.credit or move_line.debit
                        #Gestion du cas des écritures partiellement lettrées
                        if move_line.reconcile_partial_id:
                            can_reconcile = False
                            partial_credit = 0
                            partial_debit = 0
                            #On calcule le montant total du débit et du crédit dans le lettrage partiel
                            #Dans le cas d'une facture client ou d'un avoir fournisseur on recherche des 
                            #écritures au crédit donc on ne prend pas en compte le lettrage partiel si le crédit total
                            #de ce lettrage est inférieur au débit total.
                            #Idem pour les factures fournisseurs et les avoirs clients, on recherche les écritures au débit.
                            for partial_line in move_line.reconcile_partial_id.line_partial_ids:
                                partial_debit += partial_line.debit
                                partial_credit += partial_line.credit
                            
                            if (credit_search and partial_credit > partial_debit) or (debit_search and partial_debit >  partial_credit):
                                can_reconcile = True
                                reconcile_partial_list.append(move_line.reconcile_partial_id.id)
                                move_amount = abs(move_line.amount_residual)
                        
                        if can_reconcile:
                            if move_currency and move_currency.id != company_currency.id:
                                context2 = {'date': move_line.date}
                                available_amount += move_currency.with_context(context2).compute(move_amount, company_currency)
                            else:
                                available_amount += move_amount
                
        self.available_amount = available_amount
    
    
    @api.one
    @api.depends('currency_id', 'company_id', 'residual')
    def _compute_convert_amount(self):
        """
            Fonction permettant de calculer le montant total dans la devise de la société de la facture
            dans le cas où les devises sont différentes
        """
        convert_amount = 0
        invoice_currency_rs = self.currency_id
        company_currency_rs = self.company_id.currency_id
        #On ne lance le calcul que si les devises de la facture et de la société de la facture sont différentes et 
        #si le montant restant dû est supérieur à 0
        if invoice_currency_rs and company_currency_rs and invoice_currency_rs != company_currency_rs and self.residual > 0:
            context2 = {}
            context2.update(self.env.context)
            context2 = {'date': self.date_invoice}
            convert_amount = invoice_currency_rs.with_context(context2).compute(self.residual, company_currency_rs)
            
        self.convert_amount = convert_amount
        
        
    @api.one
    @api.depends('payment_ids')
    def _compute_has_payments(self):
        """
            Fonction permettant de calculer le montant total dans la devise de la société de la facture
            dans le cas où les devises sont différentes
        """
        payment = False
        if self.payment_ids:
            payment = True
            
        self.has_payments = payment
            
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        """
            On surcharge le fields view get pour récupérer les vues d'openprod et non celles d'odoo
        """
        def get_view_id(xid, name):
            try:
                return self.env.ref('account.' + xid)
            except ValueError:
                view = self.env['ir.ui.view'].search([('name', '=', name)], limit=1)
                if not view:
                    return False
                 
                return view.id
         
        context = self._context
        view = False
        if not view_id and context.get('active_model') == 'res.partner' and context.get('active_ids'):
            partner = self.env['res.partner'].browse(context['active_ids'])[0]
            if not view_type:
                view = get_view_id('invoice_tree', 'account.invoice.tree')
                view_type = 'tree'
            elif view_type == 'form':
                if partner.is_supplier and not partner.is_customer:
                    view = get_view_id('account_supp_openprod_invoice_form', 'account.supplier.openprod.invoice.form')
                elif partner.is_customer and not partner.is_supplier:
                    view = get_view_id('account_cust_openprod_invoice_form', 'account.customer.openprod.invoice.form')
                else:
                    view = get_view_id('account_cust_openprod_invoice_form', 'account.customer.openprod.invoice.form')
             
        if view:
            if isinstance(view, models.Model):
                view_id = view.id
            elif isinstance(view, int):
                view_id = view
         
        return super(AccountInvoice, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
     
    
    @api.one
    @api.depends(
        'state', 'currency_id', 'invoice_line_ids.price_subtotal',
        'move_id.line_id.account_id.type',
        'move_id.line_id.amount_residual',
        # Fixes the fact that move_id.line_id.amount_residual, being not stored and old API, doesn't trigger recomputation
        'move_id.line_id.reconcile_id',
        'move_id.line_id.amount_residual_currency',
        'move_id.line_id.currency_id',
        'move_id.line_id.reconcile_partial_id.line_partial_ids.invoice.type',
    )
    # An invoice's residual amount is the sum of its unreconciled move lines and,
    # for partially reconciled move lines, their residual amount divided by the
    # number of times this reconciliation is used in an invoice (so we split
    # the residual amount between all invoice)
    def _compute_residual(self):
        self.residual = 0.0
        # Each partial reconciliation is considered only once for each invoice it appears into,
        # and its residual amount is divided by this number of invoices
        partial_reconciliations_done = []
        for line in self.sudo().move_id.line_id:
            if line.account_id.type not in ('receivable', 'payable'):
                continue
            
            if line.reconcile_partial_id and line.reconcile_partial_id.id in partial_reconciliations_done:
                continue
            
            # Get the correct line residual amount
            if line.currency_id == self.currency_id:
                line_amount = line.amount_residual_currency if line.currency_id else line.amount_residual
            else:
                from_currency = line.company_id.currency_id.with_context(date=line.date)
                line_amount = from_currency.compute(line.amount_residual, self.currency_id)
                
            # For partially reconciled lines, split the residual amount
            if line.reconcile_partial_id:
                partial_reconciliation_invoices = {}
                for pline in line.reconcile_partial_id.line_partial_ids:
                    if pline.invoice and self.type == pline.invoice.type:
                        if pline.invoice.id in partial_reconciliation_invoices:
                            partial_reconciliation_invoices[pline.invoice.id] += pline.invoice.amount_total
                        else:
                            partial_reconciliation_invoices[pline.invoice.id] = pline.invoice.amount_total
                            
                line_amount = self.currency_id.round((line_amount / sum(partial_reconciliation_invoices.values())) * self.amount_total)
                partial_reconciliations_done.append(line.reconcile_partial_id.id)
                
            self.residual += line_amount
        self.residual = max(self.residual, 0.0)
        
    @api.one
    @api.depends('mail_ids', 'mail_ids.model_template_id')
    def _compute_reminder_mail(self):
        reminder_date = False
        reminder_nb = 0
        for mail in self.mail_ids:
            if mail.model_template_id and mail.model_template_id.edi_select == 'reminder':
                reminder_nb += 1
                if not reminder_date or mail.date > reminder_date:
                    reminder_date = mail.date
        
        self.reminder_date = reminder_date
        self.reminder_nb = reminder_nb


    @api.model
    def _month_get(self):
        return [
                    ('00', _('Without month')), 
                    ('01', _('January')), 
                    ('02', _('February')), 
                    ('03', _('March')), 
                    ('04', _('April')), 
                    ('05', _('May')), 
                    ('06', _('June')), 
                    ('07', _('July')), 
                    ('08', _('August')), 
                    ('09', _('September')), 
                    ('10', _('October')), 
                    ('11', _('November')), 
                    ('12', _('December'))
           ]
    
    
    @api.one
    @api.depends('date_invoice')
    def _compute_date_invoice_detail(self):
        """
        Fonction qui calcule la semaine, le mois et l'année de la date de facture
        """
        wo_vals = self.read(['date_invoice']) 
        if wo_vals[0]['date_invoice']:
            date = '%s'%(wo_vals[0]['date_invoice'][0:10])
            date = datetime.strptime(date, '%Y-%m-%d')
            isocal = date.isocalendar()
            
            # Sur 2 caractères
            if len(str(isocal[1])) == 1:
                self.week_number = '0%s'%(str(isocal[1]))
            else:
                self.week_number = str(isocal[1])
            
            # Sur 2 caractères
            if len(str(date.month)) == 1:
                self.month = '0%s'%(str(date.month))
            else:
                self.month = str(date.month)
                
            self.year = str(isocal[0])
        else:
            self.week_number = '00'
            self.month = '00'
            self.year = '0'
    
    
    @api.one
    @api.depends('invoice_line_ids')
    def _compute_is_readonly_currency(self):
        self.is_readonly_currency = len(self.invoice_line_ids) > 0
            
            
    #===========================================================================
    # COLUMNS
    #===========================================================================
    #En-tête
    lang_id = fields.Many2one('res.lang', string='Langue', required=False, ondelete='restrict',
                              readonly=True, states={'draft': [('readonly', False)]})
    external_reference = fields.Char(string='External reference', size=32, required=False,
                              readonly=True, states={'draft': [('readonly', False)]})
    delivery_partner_id = fields.Many2one('res.partner', string='Delivered customer', required=True, ondelete='restrict',
                              readonly=True, states={'draft': [('readonly', False)]})
    partner_order_id = fields.Many2one('res.partner', string='Customer of the order', required=True, ondelete='restrict',
                              readonly=True, states={'draft': [('readonly', False)]})
    anticipated = fields.Boolean(string='Anticipated invoice', default=False)
    auto_anticipated = fields.Boolean(string='Anticipated invoice', default=False)
    has_payments = fields.Boolean(string='Has payments', default=False, compute='_compute_has_payments', store=False)
    #Ligne de facture
    tax_amount_20 = fields.Float(string='Tax (20%)', default=0.0, required=False, readonly=True, 
                                 states={'draft': [('readonly', False)]})
    #Adresse
    address_id = fields.Many2one('address', string='Address', required=False, ondelete='restrict',
                              readonly=True, states={'draft': [('readonly', False)]})
    corporate_name = fields.Char(string='Corporate name', size=32, required=False,
                              readonly=True, states={'draft': [('readonly', False)]})
    street = fields.Char(string='Street', size=32, required=False, readonly=True, states={'draft': [('readonly', False)]})
    street2 = fields.Char(string='Street 2', size=32, required=False, readonly=True, states={'draft': [('readonly', False)]})
    street3 = fields.Char(string='Street 3', size=32, required=False, readonly=True, states={'draft': [('readonly', False)]})
    zip = fields.Char(string='Zip', size=32, required=False, readonly=True, states={'draft': [('readonly', False)]})
    city = fields.Char(string='City', size=128, required=False, readonly=True, states={'draft': [('readonly', False)]})
    region_id = fields.Many2one('res.region', string='Region', required=False, ondelete='restrict',
                              readonly=True, states={'draft': [('readonly', False)]})
    country_id = fields.Many2one('res.country', string='Country', required=True, ondelete='restrict',
                              readonly=True, states={'draft': [('readonly', False)]})
    tva_number = fields.Char(string='TVA number', size=32, required=False,
                              readonly=True, states={'draft': [('readonly', False)]})
    print_packaging_list = fields.Boolean(string='Print packaging list', default=False, 
                                          help='If this field is checked, the packaging list will be printed on reports')
    declaration_deb = fields.Boolean(string='DEB declaration', default=False,
                              readonly=True, states={'draft': [('readonly', False)]})
    contact_ids = fields.Many2many('res.partner', 'invoicing_contact_id_invoice_rel', 'invoice_id', 'contact_id', string='Contacts',
                                   readonly=True, states={'draft': [('readonly', False)]})
    #Champ conservé pour la reprise des données, à supprimer plus tard
    contact_id = fields.Many2one('res.partner', string='Contact', required=False, ondelete='restrict',
                              readonly=True, states={'draft': [('readonly', False)]})
    communication_method = fields.Selection('_communication_method_get', string='Communication method',
                              readonly=True, states={'draft': [('readonly', False)]})
    communication_value = fields.Char(string='Communication value', compute='_compute_communication_value')
    group_invoices = fields.Boolean(string='Group invoices', default=False,
                              readonly=True, states={'draft': [('readonly', False)]})
    accounting_manager_id = fields.Many2one('res.users', string='Accounting manager', required=False, ondelete='restrict')
    lock_invoice = fields.Boolean(string='Lock invoice', default=False,
                              readonly=True, states={'draft': [('readonly', False)]})
    invoices_period = fields.Selection('_invoices_period_get', string='Invoices period', required=False,
                              readonly=True, states={'draft': [('readonly', False)]})
    note_invoice_header = fields.Html(string='Note on the printed invoice\'s header',
                              readonly=True, states={'draft': [('readonly', False)]})
    note_invoice_intern = fields.Text(string='Note on the internal invoice\'s header',
                              readonly=True, states={'draft': [('readonly', False)]})
    inv_term_line_ids = fields.One2many('invoice.payment.term.line', 'invoice_id', string='Invoice payment term lines', readonly=True)
    see_inv_term_line = fields.Boolean(string='See invoice payment term lines', compute='_compute_invoice_payment_term_lines', store=False)
    #Payment
    payment_method_id = fields.Many2one('payment.method', string='Payment method', required=True, ondelete='restrict', readonly=True, states={'draft': [('readonly', False)]})
    paid_by_id = fields.Many2one('res.partner', string='Paid by', required=True, ondelete='restrict', readonly=True, states={'draft': [('readonly', False)]})
    discount_management = fields.Boolean(string='Discount management', default=False, readonly=True, states={'draft': [('readonly', False)]})
    max_delay = fields.Integer(string='Max delay for application (in days)', default=0, required=False, readonly=True, states={'draft': [('readonly', False)]})
    discount_value = fields.Float(string='Discount value', default=0.0, required=False, readonly=True, states={'draft': [('readonly', False)]})
    available_amount = fields.Float(string='Available amount for this partner', default=0.0, compute='_compute_available_amount', store=False)
    convert_amount = fields.Float(string='Residual amount in company currency', default=0.0, compute='_compute_convert_amount', store=False)
    disbursement_move_id = fields.Many2one('account.move', string='Disbursement move', required=False, ondelete='restrict', states={'draft': [('readonly', False)]})

    residual = fields.Float(string='Balance', digits=dp.get_precision('Account'), compute='_compute_residual', store=True, help="Remaining amount due.")
    mail_ids = fields.One2many('mail.mail', 'res_id', string='Mails', domain=[("model", "=", "account.invoice")])
    reminder_date = fields.Date(string='Reminder date', compute='_compute_reminder_mail', readonly=True)
    reminder_nb = fields.Integer(string='Reminder number', compute='_compute_reminder_mail', readonly=True)
    invoice_trigger = fields.Selection('_invoice_trigger_get', string='Invoicing method trigger', required=False)
    # Date
    month = fields.Selection('_month_get', string='Month', compute='_compute_date_invoice_detail', store=True)
    week_number = fields.Char(string='Week number', size=2, compute='_compute_date_invoice_detail', store=True) 
    year = fields.Char(string='Year', size=4, compute='_compute_date_invoice_detail', store=True)       
    invoice_send_address_id = fields.Many2one('address', string='Invoice send address', required=False, ondelete='restrict')
    delivery_country_id = fields.Many2one('res.country', ondelete='restrict', string='Delivered country', readonly=True, 
                                          states={'draft': [('readonly', False)]})
    is_readonly_currency = fields.Boolean(compute='_compute_is_readonly_currency', string='Is readonly currency')
    
    
    def onchange_invoice_partner_id(self, partner, type):
        """
            Récupération des infos du partenaire 
        """
        if isinstance(partner, int):
            partner = self.env['res.partner'].browse(partner)
        
        if type in ('in_invoice', 'in_refund'):
            account_id = partner.property_account_payable_id.id
        else:
            account_id = partner.property_account_receivable_id.id
        
        if partner:
            if partner.is_company:
                corporate_name = partner.corporate_name
            else:
                corporate_name = '%s %s'%(partner.name, partner.first_name)
                
        else:
            corporate_name = ''
        
        lang_rs = self.env['res.lang'].search([('code', '=', partner.lang)], limit=1)
        res = {
                'lang_id': lang_rs and lang_rs.id or False,
                'address_id': partner.address_id.id,
                'currency_id': partner.currency_id.id,
                'account_id': account_id,
                'lock_invoice': partner.lock_invoices,
                'group_invoices': partner.group_invoices,
                'invoices_period': partner.invoices_period,
                'contact_ids': [(4, contact_id) for contact_id in partner.invoicing_contact_ids.ids],
                'communication_method': partner.accounting_communication_method,
                'note_invoice_header': partner.sale_invoice_note,
                'corporate_name': corporate_name,
                'accounting_manager_id': partner.accounting_manager_id and partner.accounting_manager_id.id or False,
                'invoice_send_address_id': partner.invoice_send_address_id and partner.invoice_send_address_id.id or False,
               }
            
        return res
    
    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """
            Au changement du partenaire, on vient renseigner son adresse, son compte, 
            sa langue, sa devise, ...
        """
        res = self.onchange_invoice_partner_id(self.partner_id, self.type)
        for k,v in res.iteritems():
            self[k] = v
            
    @api.onchange('delivery_partner_id')
    def _onchange_delivery_partner_id(self):
        self.delivery_country_id = self.delivery_partner_id and self.delivery_partner_id.country_id and self.delivery_partner_id.country_id.id or False
    
    
    def onchange_address_id(self, address):
        """
            Récupération des infos de l'adresse 
        """
        if isinstance(address, int):
            address = self.env['address'].browse(address)
            
        res = {
               'street': address.street,
               'street2': address.street2,
               'street3': address.street3,
               'zip': address.zip,
               'city': address.city,
               'region_id': address.region_id and address.region_id.id or False,
               'country_id': address.country_id.id,
               }
        return res
    
    
    @api.onchange('paid_by_id')
    def _onchange_paid_by_id(self):
        if not self.paid_by_id:
            self.payment_method_id = False
            self.payment_term_id = False
            self.discount_management = False
            self.max_delay = False
            self.discount_value = False
            self.partner_bank_id = False
        else:
            self.partner_bank_id = self.env['res.partner.bank'].search([('partner_id', '=',  self.paid_by_id.id)], limit=1) or False
    
    
    @api.onchange('address_id')
    def _onchange_address_id(self):
        """
            Au changement de l'adresse, on récupère et affiche toutes ses informations:
            rues, code postal, pays etc...
        """
        if self.address_id:
            res = self.onchange_address_id(self.address_id)
            for k,v in res.iteritems():
                self[k] = v
                
        else:
            self.street = ''
            self.street2 = ''
            self.street3 = ''
            self.zip = ''
            self.city = ''
            self.region_id = False
            self.country_id = False
    
    
    def onchange_country_id(self, country, partner):
        """
            Récupération du numéro de TVA
        """
        res = {}
        if isinstance(country, int):
            country = self.env['res.country'].browse(country)
        
        if isinstance(partner, int):
            partner = self.env['res.partner'].browse(partner)
        
        tva_obj = self.env['country.tva']
        if partner:
            #On récupère le numéro de TVA
            find_tva = False
            if country:
                #Si on a un pays on recherche le numéro de TVA de ce pays chez le partenaire
                tva_ids = tva_obj.search([('partner_id', '=', partner.id), 
                                          ('country_id', '=', country.id)], limit=1)
                if tva_ids:
                    res['tva_number'] = tva_ids[0].name
                    find_tva = True
                    
            if not country or not find_tva:
                #Sinon on recherche le numéro de TVA du pays de l'adresse du partenaire
                if partner.address_id.country_id:
                    tva_ids = tva_obj.search([('partner_id', '=', partner.id), 
                                              ('country_id', '=', partner.address_id.country_id.id)], limit=1)
                    if tva_ids:
                        res['tva_number'] = tva_ids[0].name
                        find_tva = True
            
            #Si on a trouvé aucun numéro TVA, on vide le champ
            if not find_tva:
                res['tva_number'] = ''
        
        return res
    
    
    @api.onchange('country_id', 'partner_id')
    def _onchange_country_id(self):
        """
            Au changement de pays ou de partenaire, on va rechercher le numéro de TVA correspondant
        """
        res = self.onchange_country_id(self.country_id, self.partner_id)
        if self.region_id and self.region_id.country_id != self.country_id:
            self.region_id = False
            
        for k,v in res.iteritems():
            self[k] = v
    
    
    @api.multi
    def invoice_validate(self):
        """
            Surchage de la fonction de validation de la facture
            Permet de générer les lignes de dates d'échéance
        """
        res = super(AccountInvoice, self).invoice_validate()
        for invoice in self:
            
            # CONTRAINTES SUR LES UNITÉES
            ## Seconde unité <=> Unité de prix
            product_qty_prec = self.env['decimal.precision'].precision_get('Product quantity')
            product_qty_prec = product_qty_prec and int(product_qty_prec) or 2
            for invoice_line_rc in invoice.invoice_line_ids:
                self.env.cr.execute("""
                    SELECT
                      CASE 
                        WHEN ail.dual_unit AND ail.dual_unit_type = 'variable' THEN 
                          true
                        ELSE
                          (SELECT 
                             CASE
                               WHEN round(ail.sec_uom_qty::numeric, %(product_precision)s)=round((ail.quantity * sec_uom.factor / uoi.factor)::numeric, %(product_precision)s) THEN
                                 true
                               WHEN round(ail.quantity::numeric, %(product_precision)s)=round((ail.sec_uom_qty * uoi.factor / sec_uom.factor)::numeric, %(product_precision)s) THEN
                                 true
                               ELSE
                                 false
                             END      
                           FROM 
                             account_invoice_line ail1 
                           WHERE 
                             ail1.id=ail.id)
                      END as test
                    FROM
                      account_invoice_line ail
                      JOIN product_uom sec_uom ON ail.sec_uom_id = sec_uom.id
                      JOIN product_uom uoi ON ail.uoi_id = uoi.id
                    WHERE
                      ail.id = %(id)s
                    ORDER BY test DESC
                """%{'id': invoice_line_rc.id, 'product_precision': product_qty_prec})
                res = self.env.cr.fetchone()
                if res and not res[0]:
                    raise ValidationError(_('Price unit quantity and second unit quantity are inconsistent'))
                
                ## Unité de gestion <=> Seconde unité
                self.env.cr.execute("""
                    SELECT
                      CASE 
                        WHEN NOT ail.dual_unit THEN 
                          (SELECT 
                             CASE
                               WHEN round(ail.sec_uom_qty::numeric, %(product_precision)s)=round((ail.uom_qty * sec_uom.factor / uom.factor)::numeric, %(product_precision)s) THEN
                                 true
                               WHEN round(ail.uom_qty::numeric, %(product_precision)s)=round((ail.sec_uom_qty * uom.factor / sec_uom.factor)::numeric, %(product_precision)s) THEN
                                 true
                               ELSE
                                  false
                             END      
                           FROM 
                             account_invoice_line ail1 
                           WHERE ail1.id=ail.id)
                        WHEN ail.dual_unit and ail.dual_unit_type = 'fixed' THEN 
                          (SELECT 
                             CASE
                               WHEN round(ail.sec_uom_qty::numeric, %(product_precision)s)=round((ail.uom_qty * ail.factor / ail.divisor)::numeric, %(product_precision)s) THEN
                                 true
                               WHEN round(ail.uom_qty::numeric, %(product_precision)s)=round((ail.sec_uom_qty * ail.divisor / ail.factor)::numeric, %(product_precision)s) THEN
                                 true
                               ELSE
                                 false
                             END      
                           FROM 
                             account_invoice_line ail1 
                           WHERE ail1.id=ail.id)
                        ELSE 
                          true
                      END as test
                     FROM
                       account_invoice_line ail
                       JOIN product_uom uom ON ail.uom_id = uom.id
                       JOIN product_uom sec_uom ON ail.sec_uom_id = sec_uom.id
                       JOIN product_uom uoi ON ail.uoi_id = uoi.id
                    WHERE
                      ail.id = %(id)s
                    ORDER BY test DESC
                """%{'id': invoice_line_rc.id, 'product_precision': product_qty_prec})
                res = self.env.cr.fetchone()
                if res and not res[0]:
                    raise ValidationError(_('Management unit quantity and second unit quantity are inconsistent'))
            
            inv_term_line_ids = []
            payment_term = invoice.payment_term_id
            date_invoice = invoice.date_invoice
            if date_invoice and payment_term:
                prec = self.env['decimal.precision'].precision_get('Account')
                term_lines = payment_term.line_ids
                if len(term_lines) > 1:
                    amount_total = self.amount_total
                    amount = amount_total
                    sequence = 10
                    for line in term_lines:
                        amount, result = payment_term.compute_line_term(line, amount, [], prec, date_invoice, amount_total)
                        if result:
                            vals = {'due_date': result[0][0],
                                    'amount': result[0][1],
                                    'remaining_amount': 0,
                                    'sequence': sequence}
                            inv_term_line_ids.append((0, 0, vals))
                            sequence += 10
                                
                    invoice.write({'inv_term_line_ids': inv_term_line_ids})
                    
        return res
    
    
    @api.multi
    def action_cancel(self):
        """
            On vide les lignes de dates d'échéance
        """
        res = super(AccountInvoice, self).action_cancel()
        for invoice_rs in self:
            invoice_rs.cancel_disbursement()
            
        self.write({'inv_term_line_ids': [[5]]})
        return res
    
    
    def create_invoice(self, partner_id, address_id, type, other_data=None):
        """
            Fonction permettant de créer une facture
            :type self: sale.invoice
            :param partner_id: id du partenaire de la facture
            :type partner_id: integer
            :param address_id: id de l'adresse de la facture
            :type address_id: integer
            :param type: type de la facture : out_invoice, in_invoice, out_refund ou in_refund
            :type type: char
            :param options: dictionnaire contenant les valeurs que l'on souhaite forcer
            :type options: dictionnaire
            :return: Facture créée
            :rtype: recordset : account.invoice
        """
        if isinstance(partner_id, int):
            partner_id = self.env['res.partner'].browse(partner_id)
        
        if isinstance(address_id, int):
            address_id = self.env['address'].browse(address_id)
        
        vals = {
                'partner_id': partner_id.id,
                'address_id': address_id.id,
                'company_id': partner_id.company_id.id,
                'type': type,
                }
        #On appelle les deux onchanges principaux (du partenaire et de l'adresse)
        vals.update(self.onchange_invoice_partner_id(partner_id, type))
        vals.update(self.onchange_address_id(address_id))
        #On gère les éventuelles valeurs forcées
        if isinstance(other_data, dict):
            vals.update(other_data)
            
        if not 'tva_number' in vals:
            tva_number = self.onchange_country_id(vals.get('country_id', False), partner_id)
            vals['tva_number'] = tva_number.get('tva_number', '')
        
        invoice = self.create(vals)
        return invoice
    
    
    def generate_auto_anticipated_invoice_line(self, order_type, invoice_id, line=False, factor=1):
        return True

    
    def generate_anticipated_invoice_line(self, order_type, invoice_id, remaining_advanced_amount, order=False):
        """
            Fonction permettant de gérer le montant de la facture anticipée à répartir et de
            créer les lignes de facture correspondantes (Prévue pour être surchargée par sale_purchase)
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
        return True
    
    
    @api.model
    def cron_do_merge(self):
        """
            Fonction du cron qui recherche et merge les factures à grouper
        """
        search_args = []
        search_week = False
        today = datetime.strptime(fields.Date.today(), '%Y-%m-%d')
        if today.weekday() == 5:
            search_week = True
            search_args.extend([('invoices_period', '=', 'end_week')])
        
        if today.day == calendar.monthrange(today.year, today.month)[1]:
            if search_week:
                search_args = [('invoices_period', 'in', ('end_week', 'end_month'))]
            else:
                search_args.extend([('invoices_period', '=', 'end_month')])
        
        if search_args:
            #On recherche les factures qui doivent être mergées
            search_args.extend([('type', '=', 'out_invoice'), ('state', '=', 'draft'), ('group_invoices', '=', True)])
            invoices_rs = self.search(search_args)
            invoices_rs.do_merge()
            
        return True
    
    
    @api.multi
    def pay_more_invoice(self):
        dummy, view_id = self.env['ir.model.data'].get_object_reference('account_voucher', 'view_vendor_receipt_dialog_form')
        inv = self[0]
        if inv.type in ('out_invoice','out_refund'):
            account_partner_id = inv.partner_id.property_account_receivable_id and inv.partner_id.property_account_receivable_id.id or False
        else:
            account_partner_id = inv.partner_id.property_account_payable_id and inv.partner_id.property_account_payable_id.id or False
        
        amount = 0
        for invoice in self:
            if invoice.type in ('out_refund', 'in_refund'):
                amount -= invoice.residual
            else:
                amount += invoice.residual
                
        return {
            'name':_("Pay Invoice"),
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'account.voucher',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            'context': {
                'payment_expected_currency': inv.currency_id.id,
                'default_partner_id': inv.partner_id.id,
                'default_account_partner_id': account_partner_id,
                'default_amount': amount,
                'close_after_process': True,
                'invoice_type': inv.type,
                'invoice_id': inv.id,
                'invoice_ids': self.ids,
                'default_type': inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment',
                'type': inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment'
            }
        }
        
     
    @api.multi
    def do_merge(self):
        """
            Fonction permettant de merger plusieurs factures en une seule
            Les lignes de facture ne sont pas mergées
        """
        #Pour trouver les factures qui doivent être mergées ensemble, on va créer une clé permettant d'identifier les
        #informations essentielles de la facture. Pour chaque clé on va remplir un dictionnaire contenant l'id de la 
        #première facture. Si une des factures est identique à cette première facture, on va aller écrire l'id de la
        #première facture dans les lignes de cette facture, puis supprimer la facture
        data = {}
        first_invoice_list = self.env['account.invoice']
        for invoice in self:
            key = invoice.get_key_for_merge()
            if not data.get(key):
                data[key] = invoice.id
                first_invoice_list += invoice
            else:
                invoice.invoice_line_ids.write({'invoice_id': data[key]})
                invoice.unlink()
        
        for invoice in first_invoice_list:
            invoice._onchange_invoice_line_ids() 
            
        return True
     
     
    def get_key_for_merge(self):
        """
            Création d'une clé pour identifier les factures qui peuvent être mergées
        """
        
        key = '%s/%s/%s/%s/%s/%s/%s/%s/%s/%s/%s/%s/%s/%s/%s/%s/%s/%s/%s/%s/%s/%s/%s/%s/%s/%s/%s/%s/%s/%s/%s/%s/%s/%s'%(
                            self.type,
                            self.partner_id.id or 0,
                            self.journal_id.id or 0,
                            self.account_id.id or 0,
                            self.delivery_partner_id.id or 0,
                            self.partner_order_id.id or 0,
                            self.currency_id.id or 0,
                            self.address_id.id or 0,
                            self.corporate_name,
                            self.street,
                            self.street2,
                            self.street3,
                            self.city,
                            self.region_id,
                            self.country_id.id or 0,
                            self.zip,
                            self.tva_number,
                            self.payment_term_id.id or 0,
                            self.payment_method_id.id or 0,
                            self.paid_by_id.id or 0,
                            self.partner_bank_id.id or 0,
                            self.fiscal_position_id.id or 0,
                            self.note_invoice_header,
                            self.note_invoice_intern,
                            self.declaration_deb,
                            self.date_due,
                            self.discount_management,
                            self.max_delay,
                            self.discount_value,
                            self.lock_invoice,
                            self.group_invoices,
                            self.contact_ids.ids or 0,
                            self.communication_method,
                            self.anticipated,
                            )
        if self.group_invoices:
            key += '%s'%(self.invoices_period)
        return key
    
    
    @api.multi
    def unreconcile_invoice(self):
        """
            Fonction permettant de rechercher et de supprimer tous les lettrages liés à la facture
        """
        partial_move_lines = self.env['account.move.line']
        reconcile_dict = {}
        partial_reconcile_dict = {}
        for invoice in self:
            for line in invoice.move_id.line_id:
                if line.reconcile_id:
                    if not line.reconcile_id in reconcile_dict:
                        reconcile_dict[line.reconcile_id] = []
                    
                    reconcile_dict[line.reconcile_id].append(line)
                    
                elif line.reconcile_partial_id:
                    if not line.reconcile_partial_id in partial_reconcile_dict:
                        partial_reconcile_dict[line.reconcile_partial_id] = []
                    
                    partial_reconcile_dict[line.reconcile_partial_id].append(line)
            
            for reconcile, line_list in reconcile_dict.items():
                tot_debit = 0
                tot_credit = 0
                for move_line in reconcile.line_id:
                    if move_line not in line_list and move_line.reconcile_origin_id != reconcile:
                        partial_move_lines += move_line
                        tot_debit = move_line.debit
                        tot_credit = move_line.credit
                    
                reconcile.unlink()
                if len(partial_move_lines) >= 2 and tot_debit > 0 and tot_credit > 0:
                    partial_move_lines.reconcile_partial('auto')
                    
            for reconcile, line_list in partial_reconcile_dict.items():
                tot_debit = 0
                tot_credit = 0
                for move_line in reconcile.line_id:
                    if move_line not in line_list and move_line.reconcile_origin_id != reconcile:
                        partial_move_lines += move_line
                        tot_debit = move_line.debit
                        tot_credit = move_line.credit
                    
                reconcile.unlink()
                if len(partial_move_lines) >= 2 and tot_debit > 0 and tot_credit > 0:
                    partial_move_lines.reconcile_partial('auto')
            
        return True
    
    
    @api.one
    @api.constrains('state', 'lock_invoice')
    def _check_block_before(self):
        """
            Empêche la validation de la facture si elle est bloquée
        """
        if self.lock_invoice and self.state == 'open':
            raise Warning(_('Error'), _('You can\'t validate a locked invoice'))
        
        return True
    
    
    def manage_sale_purchase_state(self, unlink_invoice_ids=False):
        """
            Gestion de l'état des ventes et des achats liés au picking
            :type self: stock.picking
            :return: True
            :rtype: boolean
        """
        return True
    
    
    def tax_on_payment(self):
        move_obj = self.env['account.move']
        for invoice_rs in self:
            res = []
            self._cr.execute('''SELECT * FROM account_invoice_tax 
                                WHERE invoice_id = %s AND tax_on_payment AND account_payment_id IS NOT NULL''', (invoice_rs.id,))
            for row in self._cr.dictfetchall():
                if not (row['amount'] or row['tax_code_id'] or row['tax_amount']):
                    continue
                
                res.append({
                    'type': 'tax',
                    'name': row['name'],
                    'price_unit': row['amount'],
                    'quantity': 1,
                    'price': -row['amount'] or 0.0,
                    'account_id': row['account_payment_id'],
                    'tax_code_id': row['tax_code_id'],
                    'tax_amount': row['tax_amount'],
                    'account_analytic_id': row['account_analytic_id'],
                })
                res.append({
                    'type': 'tax',
                    'name': row['name'],
                    'price_unit': row['amount'],
                    'quantity': 1,
                    'price': row['amount'] or 0.0,
                    'account_id': row['account_id'],
                    'tax_code_id': row['tax_code_id'],
                    'tax_amount': row['tax_amount'],
                    'account_analytic_id': row['account_analytic_id'],
                })
            
            if res:
                date_invoice = invoice_rs.date_invoice
                ctx = dict(self._context, lang=invoice_rs.partner_id.lang)
                ctx['date'] = date_invoice
                line = [(0, 0, self.line_get_convert(l, invoice_rs.partner_id.id, date_invoice)) for l in res]
                line = invoice_rs.group_lines(res, line)
                line = invoice_rs.finalize_invoice_move_lines(line)
                journal = invoice_rs.journal_id.with_context(ctx)
                move_vals = {
                    'ref': invoice_rs.reference or invoice_rs.name,
                    'line_id': line,
                    'journal_id': journal.id,
                    'date': invoice_rs.date_invoice,
                    'narration': invoice_rs.comment,
                    'company_id': invoice_rs.company_id.id,
                }
                ctx['company_id'] = invoice_rs.company_id.id
                period = invoice_rs.period_id
                if not period:
                    period = period.with_context(ctx).find(date_invoice)[:1]
                    
                if period:
                    move_vals['period_id'] = period.id
                    for i in line:
                        i[2]['period_id'] = period.id
    
                ctx['invoice'] = invoice_rs
                ctx_nolang = ctx.copy()
                ctx_nolang.pop('lang', None)
                move_rs = move_obj.with_context(ctx_nolang).create(move_vals)
                if move_rs:
                    invoice_rs.with_context(ctx).write({'disbursement_move_id': move_rs.id})

                move_rs.post()
                
        return True
    
    
    @api.multi
    def get_taxes_values(self):
        tax_grouped = {}
        for line in self.invoice_line_ids:
            price_unit = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = line.invoice_line_tax_ids.compute_all(price_unit, self.currency_id, line.quantity, line.product_id, self.partner_id)['taxes']
            for tax in taxes:
                val = {
                    'invoice_id': self.id,
                    'name': tax['name'],
                    'tax_id': tax['id'],
                    'amount': tax['amount'],
                    'manual': False,
                    'sequence': tax['sequence'],
                    'account_id': self.type in ('out_invoice', 'in_invoice') and (tax['account_id'] or line.account_id.id) or (tax['refund_account_id'] or line.account_id.id),
                    'base_code_id': tax['base_code_id'],
                    'tax_code_id': tax['tax_code_id'],
                    'tax_on_payment': tax['tax_on_payment'],
                    'account_payment_id': self.type in ('out_invoice', 'in_invoice') and (tax['account_payment_id'] or line.account_id.id) or (tax['refund_account_payment_id'] or line.account_id.id),
                }
                # If the taxes generate moves on the same financial account as the invoice line,
                # propagate the analytic account from the invoice line to the tax line.
                # This is necessary in situations were (part of) the taxes cannot be reclaimed,
                # to ensure the tax move is allocated to the proper analytic account.
                if not val.get('account_analytic_id') and line.account_analytic_id and val['account_id'] == line.account_id.id:
                    val['account_analytic_id'] = line.account_analytic_id.id

                key = tax['id']
                if key not in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    
        return tax_grouped
    
    
    def cancel_disbursement(self):
        if self.disbursement_move_id:
            disbursement_move_id = self.disbursement_move_id
            self.write({'disbursement_move_id': False})
            disbursement_move_id.button_cancel()
            disbursement_move_id.unlink()
    
    
    @api.multi
    def action_reopen(self):
        """
            Décaissement TVA
        """
        self.write({'state':'open'})
        for invoice_rs in self:
            invoice_rs.cancel_disbursement()
            
        return True
    
    
    @api.multi
    def action_send_mail_reminder(self):
        """
            Envoie de mail
        """
        for invoice in self:
            return self.env['mail.message'].action_send_mail(invoice.partner_id, 'account.invoice', 'reminder', invoice.id)
    
    
    @api.multi
    def confirm_paid(self):
        """
            Décaissement TVA
        """
        res = super(AccountInvoice,self).confirm_paid()
        for invoice_rs in self:
            invoice_rs.cancel_disbursement()
            
        self.tax_on_payment()
        return res
    
    
    @api.multi
    def unlink(self):
        """
            A la suppression de la facture, on passe les BL/BR liés à "to be invoiced"
            et on appelle la fonction permettant de gérer l'état de la vente ou de l'achat lié
        """
        context = self.env.context
        for invoice in self:
            line_ids = [line.id for line in invoice.invoice_line_ids]
            move_ids = self.env['stock.move'].search([('invoice_line_id', 'in', line_ids)])
            picking_ids = [move.picking_id for move in move_ids]
            for picking in picking_ids:
                picking.write({'invoice_state': '2binvoiced'})
            
            if not context.get('without_manage_state'):
                self.manage_sale_purchase_state([invoice.id])

        return super(AccountInvoice, self).unlink()
    
    
    @api.model
    def create(self, vals):
        """
            Surcharge du create afin de gérer les changements d'état des ventes et 
            des achats
        """
        context = self.env.context.copy()
        if 'default_type' in context and context['default_type'] in ('out', 'in', 'int'):
            del context['default_type']
             
        invoice = super(AccountInvoice, self.with_context(context)).create(vals)
        invoice.manage_sale_purchase_state()
        return invoice

    
    @api.multi
    def write(self, vals=None):
        """
            Surcharge du write afin de gérer les changements d'état des ventes et 
            des achats
        """
        if not vals:
            vals = {}
            
        res = super(AccountInvoice, self).write(vals)
        if vals.get('state'):
            self.manage_sale_purchase_state()
            
        return res
    
    
    
class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'
    
    
    @api.one
    @api.depends('price_unit', 'quantity', 'invoice_id.currency_id', 'invoice_id.date_invoice')
    def _compute_price_with_currency(self):
        """
            Fonction permettant de calculer le prix total de la ligne de facture dans la devise de
            la société ainsi que le taux de conversion utilisé lors du calcul
        """
        company_currency = self.invoice_id.company_id.currency_id
        invoice_currency = self.invoice_id.currency_id
        if invoice_currency and invoice_currency != company_currency:
            context2 = {}
            if self.invoice_id.date_invoice:
                context2 = {'date': self.invoice_id.date_invoice}
            
            self.total_price_currency = invoice_currency.with_context(context2).compute((self.price_unit * self.quantity), company_currency)
            self.currency_rate = invoice_currency.with_context(context2)._get_conversion_rate(invoice_currency, company_currency)
        else:
            self.total_price_currency = self.price_unit * self.quantity
            self.currency_rate = 0
    
    @api.one
    @api.depends('invoice_id.state', 'invoice_id.period_id', 'invoice_id.date_invoice', 'invoice_id.type')
    def _compute_fields_invoice(self):
        """
            Fonction qui récup des champs de la facture
        """
        self.state = self.invoice_id.state
        self.period_id = self.invoice_id.period_id and self.invoice_id.period_id.id or False
        self.date_invoice = self.invoice_id.date_invoice
        self.type = self.invoice_id.type
        
    
    @api.v8
    def get_invoice_line_account(self, type, product, fpos, company):
        accounts = product.get_product_accounts(fpos)
        if type in ('out_invoice', 'out_refund'):
            return accounts['income']
        
        return accounts['expense']
    
    
    @api.model
    def _type_get(self):
        return [
            ('out_invoice', _('Customer Invoice')),
            ('in_invoice', _('Supplier Invoice')),
            ('out_refund', _('Customer Refund')),
            ('in_refund', _('Supplier Refund')),
        ]
    
    
    @api.model
    def _state_get(self):
        return [
            ('draft', _('Draft')),
            ('proforma', _('Pro-forma')),
            ('proforma2', _('Pro-forma')),
            ('open', _('Open')),
            ('paid', _('Paid')),
            ('cancel', _('Cancelled')),
        ]
    
    
    @api.model
    def _month_get(self):
        return [
                    ('00', _('Without month')), 
                    ('01', _('January')), 
                    ('02', _('February')), 
                    ('03', _('March')), 
                    ('04', _('April')), 
                    ('05', _('May')), 
                    ('06', _('June')), 
                    ('07', _('July')), 
                    ('08', _('August')), 
                    ('09', _('September')), 
                    ('10', _('October')), 
                    ('11', _('November')), 
                    ('12', _('December'))
           ]

    
    @api.one
    @api.depends('date_invoice')
    def _compute_date_invoice_detail(self):
        """
        Fonction qui calcule la semaine, le mois et l'année de la date de facture
        """
        wo_vals = self.read(['date_invoice']) 
        if wo_vals and wo_vals[0]['date_invoice']:
            date = '%s'%(wo_vals[0]['date_invoice'][0:10])
            date = datetime.strptime(date, '%Y-%m-%d')
            isocal = date.isocalendar()
            
            # Sur 2 caractères
            if len(str(isocal[1])) == 1:
                self.week_number = '0%s'%(str(isocal[1]))
            else:
                self.week_number = str(isocal[1])
            
            # Sur 2 caractères
            if len(str(date.month)) == 1:
                self.month = '0%s'%(str(date.month))
            else:
                self.month = str(date.month)
                
            self.year = str(isocal[0])
        else:
            self.week_number = '00'
            self.month = '00'
            self.year = '0'  
            
            
    #===========================================================================
    # COLUMNS
    #===========================================================================
    #Général
    sec_uom_qty = fields.Float(string='Quantity in sale unity', default=0.0, digits=dp.get_precision('Product quantity'), required=True)
    uom_qty = fields.Float(string='Ordered quantity in measure unit', default=0.0, digits=dp.get_precision('Product quantity'), required=True)
    quantity = fields.Float(digits=dp.get_precision('Product quantity'))
    sec_uom_id = fields.Many2one('product.uom', string='Sale unity', required=True, ondelete='restrict')
    uom_id = fields.Many2one('product.uom', string='Measure unity', required=True, ondelete='restrict')
    uoi_id = fields.Many2one('product.uom', string='Price unity', required=True, ondelete='restrict')
    sec_uom_category_id = fields.Many2one('product.uom.category', string='Second uom category', required=False, ondelete='restrict')
    uom_category_id = fields.Many2one('product.uom.category', string='Uom category', required=False, ondelete='restrict')
    uoi_category_id = fields.Many2one('product.uom.category', string='Uoi category', required=False, ondelete='restrict')
    factor = fields.Float(string='Factor', default=1, required=False)
    divisor = fields.Float(string='Divisor', default=1, required=False)
    total_price_currency = fields.Float(string='Total price currency company', default=0.0, required=False, compute='_compute_price_with_currency', store=True)
    currency_rate = fields.Float(string='Currency rate', default=0.0, required=False, compute='_compute_price_with_currency', store=True, digits=(12,6))
    customer_product_name = fields.Char(string='Customer product name', size=32, required=False)
    customer_product_code = fields.Char(string='Customer product code', size=32, required=False)
    dual_unit = fields.Boolean(string='Dual unit', default=False, help="Check if you want manage a dual unit for this product")
    dual_unit_type = fields.Selection(string='Dual unit type', selection=[('fixed', 'Fixed'), ('variable', 'Variable')], default='fixed')
    #Divers
    note_invoice_header = fields.Text(string='Note on the printed invoice\'s line')
    note_invoice_intern = fields.Text(string='Note on the internal invoice\'s line')
    auto_anticipated_line_id = fields.Many2one('account.invoice.line', 'Anticipated invoice line', select=True)
    state = fields.Selection(_state_get, string='Status',  compute='_compute_fields_invoice', store=True)
    period_id = fields.Many2one('account.period', string='Force Period',  compute='_compute_fields_invoice', store=True)
    date_invoice = fields.Date(string='Invoice Date', compute='_compute_fields_invoice', store=True)
    type = fields.Selection(_type_get, string='Type', compute='_compute_fields_invoice', store=True)
    # Date
    month = fields.Selection('_month_get', string='Month', compute='_compute_date_invoice_detail', store=True)
    week_number = fields.Char(string='Week number', size=2, compute='_compute_date_invoice_detail', store=True) 
    year = fields.Char(string='Year', size=4, compute='_compute_date_invoice_detail', store=True)  
    company_id = fields.Many2one('res.company', string='Company', related='invoice_id.company_id', store=True, readonly=True)
    
    
    def onchange_invoice_product_id(self, product_id, invoice):
        """
            Récupération des infos du produit et du customerinfo
        """
        res = {}
        if isinstance(product_id, int):
            product_id = self.env['product.product'].browse(product_id)
            
        if product_id:
            customer = False
            fiscal_position = invoice.fiscal_position_id
            invoice_type = invoice.type
            company = invoice.company_id
            account = self.get_invoice_line_account(invoice_type, product_id, fiscal_position, company)
            if account:
                res['account_id'] = account.id
                
            res['invoice_line_tax_ids'] = self._set_taxes()
            res['uom_id'] = product_id.uom_id.id
            res['dual_unit'] = product_id.dual_unit
            res['dual_unit_type'] = product_id.dual_unit_type
            res['note_invoice_intern'] = product_id.internal_note
            res['note_invoice_header'] = product_id.description_invoice
            res['name'] = product_id.with_context(lang=invoice.partner_id.lang).name
            uoms = product_id.get_uoms(pinfo=customer or False, partner=invoice.partner_id, type='out', property_ids=False,
                                    with_factor=True)
            for k, v in uoms.iteritems():
                res[k] = v

        return res

    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
            Au changement du produit, on va ramener son nom, ainsi que ses unités de vente, de gestion, de prix
            et les quantités associées
        """
        res = {'warning': {}}
        if not self.partner_id:
            res['warning'] = {'title': _('Warning'), 'message': _('You must first select a partner!')}
            return res
        else:
            res = self.onchange_invoice_product_id(self.product_id, self.invoice_id)
            for k,v in res.iteritems():
                self[k] = v
    
    
    @api.onchange('uom_qty', 'uom_id')
    def _onchange_uom_qty(self):
        """
            Au changement de la qty, changement des autres qty
        """
        res = {'warning': {}}
        if self.product_id: 
            qtys = self.product_id.get_qtys(self.uom_qty, 
                                     uom_id=self.uom_id, 
                                     sec_uom_id=self.sec_uom_id, 
                                     uoi_id=self.uoi_id, 
                                     by_field='uom', 
                                     dual_unit=self.dual_unit, 
                                     dual_unit_type=self.dual_unit_type, 
                                     factor=self.factor, 
                                     divisor=self.divisor,
                                     with_raise=True)
            if 'uoi_qty' in qtys:
                qtys['quantity'] = qtys['uoi_qty']
                del qtys['uoi_qty']
            
            for k, v in qtys.iteritems():
                self[k] = v
                
            self.uom_category_id = self.uom_id.category_id.id
            if not self.uom_id or not self.sec_uom_id:
                res['warning'] = {'title': _('Warning'), 'message': _('You must have Management unit and Sale unit')}
        
        return res
    
    
    @api.onchange('sec_uom_qty', 'sec_uom_id')
    def _onchange_sec_uom_qty(self):
        """
            Au changement de la qty, changement des autres qty
        """
        res = {'warning': {}, 'domain': {}}
        if self.product_id:
            qtys = self.product_id.get_qtys(self.sec_uom_qty, 
                                     uom_id=self.uom_id, 
                                     sec_uom_id=self.sec_uom_id, 
                                     uoi_id=self.uoi_id, 
                                     by_field='sec_uom', 
                                     dual_unit=self.dual_unit, 
                                     dual_unit_type=self.dual_unit_type, 
                                     factor=self.factor, 
                                     divisor=self.divisor, 
                                     with_raise=True)
            if 'uoi_qty' in qtys:
                qtys['quantity'] = qtys['uoi_qty']
                del qtys['uoi_qty']
            
            for k, v in qtys.iteritems():
                self[k] = v
            
            self.sec_uom_category_id = self.sec_uom_id.category_id.id
            if not self.uom_id or not self.sec_uom_id:
                res['warning'] = {'title': _('Warning'), 'message': _('You must have Management unit and Sale unit')}
                self.uom_qty = 0
                self.sec_uom_qty = 0
                
        return res
            
            
    @api.onchange('quantity', 'uoi_id')
    def _onchange_quantity(self):
        """
            Au changement de la qty, changement des autres qty
        """
        if self.product_id:
            qtys = self.product_id.get_qtys(self.quantity, 
                                     uom_id=self.uom_id, 
                                     sec_uom_id=self.sec_uom_id, 
                                     uoi_id=self.uoi_id, 
                                     by_field='uoi', 
                                     dual_unit=self.dual_unit, 
                                     dual_unit_type=self.dual_unit_type, 
                                     factor=self.factor, 
                                     divisor=self.divisor, 
                                     with_raise=True)
            if 'uoi_qty' in qtys:
                qtys['quantity'] = qtys['uoi_qty']
                del qtys['uoi_qty']
                
            for k, v in qtys.iteritems():
                self[k] = v
            
            self.uoi_category_id = self.uoi_id.category_id.id
            if not self.uom_id or not self.uoi_id:
                self.sec_uom_qty = 0
            
    
    def _set_taxes(self):
        """ 
            Récupération des taxes
        """
        if self.invoice_id.type in ('out_invoice', 'out_refund'):
            taxes = self.product_id.sale_taxes_ids or self.account_id.tax_ids
        else:
            taxes = self.product_id.purchase_taxes_ids or self.account_id.tax_ids
            
        return self.invoice_id.fiscal_position_id.map_tax(taxes)
    
    
    def fonction_discount_invoice(self, sale_order_line_id):
        """
            Fonction permettant de recopier dans la facture les remises faites dans la vente
        """
        discount_vals = {}
        return discount_vals
          
    
    def create_invoice_line(self, invoice_id, product_id, from_invoice=True, other_data=None, forced_price_unit=None, forced_uoi_qty=False):
        """
            Fonction permettant de créer une ligne de facture
            :type self: account.invoice.line
            :param invoice_id: Recordset de la facture à laquelle est reliée la ligne de facture
            :type invoice_id: recordset de account.invoice
            :param product_id: Recordset du produit de la ligne de facture
            :type product_id: recordset de product.product
            :param from_invoice: False si on lance juste la méthode sans créer la facture
            :type from_invoice: boolean
            :param other_data: dictionnaire contenant les valeurs que l'on souhaite forcer
            :type other_data: dictionnaire
            :return: Ligne de facture créée
            :rtype: recordset : account.invoice.line
        """
        if isinstance(product_id, int):
            product_id = self.env['product.product'].browse(product_id)
        
        if isinstance(invoice_id, int):
            invoice_id = self.env['account.invoice'].browse(invoice_id)
        
        vals = {'product_id': product_id.id,
                'invoice_id': invoice_id.id}
        # Récuperation des informations principales du produit
        vals.update(self.onchange_invoice_product_id(product_id, invoice_id))
        # Traitement des éventuelles valeurs forcées
        if forced_uoi_qty:
            vals['quantity'] = forced_uoi_qty
        
        if isinstance(other_data, dict):
            vals.update(other_data)
        
        # Si on récupère des recordsets, on fait en sorte de récupérer leurs ids
        vals = utils.transform_to_ids(self, vals)
        # Point d'entrée pour les remises
        if 'sale_order_line_id' in vals and vals['sale_order_line_id']:
            discount_invoice = self.fonction_discount_invoice(vals['sale_order_line_id'])
            if discount_invoice:
                vals.update(discount_invoice)
        
        invoice_line = self.create(vals)
        if not from_invoice:
            invoice_id._onchange_invoice_line_ids()
        
        if forced_uoi_qty:
            invoice_line._onchange_quantity()
            invoice_line._onchange_sec_uom_qty()
            invoice_line._onchange_uom_qty()
        else:
            invoice_line._onchange_sec_uom_qty()
            invoice_line._onchange_uom_qty()
            invoice_line._onchange_quantity()
            
        if isinstance(forced_price_unit, (float, int)):
            invoice_line.price_unit = forced_price_unit
        
        return invoice_line
    
    
    @api.model
    def create(self, vals):
        """
            Surcharge pour ne pas avoir le problème du default_type dans le context provenant des picking
        """
        context = self.env.context.copy()
        if 'default_type' in context and context['default_type'] in ('out', 'in', 'int'):
            del context['default_type']
         
        return super(AccountInvoiceLine, self.with_context(context)).create(vals)
    
    
    
class account_invoice_tax(models.Model):
    _inherit = 'account.invoice.tax'
    #===========================================================================
    # COLUMNS
    #===========================================================================
    tax_on_payment = fields.Boolean(default=False)
    account_payment_id = fields.Many2one('account.account', 'Invoice tax account (On payment)', help='Set the account that will be set by default on invoice tax lines for invoices. Leave empty to use the expense account.')