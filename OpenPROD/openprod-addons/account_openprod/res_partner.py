# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
from openerp.addons.base_openprod.common import get_form_view


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'
    
    @api.model
    def _statement_type_get(self):
        return [
                ('iban', _('IBAN')),
                ('bic', _('BIC/Swift')),
                       ]
    
    statement_type = fields.Selection('_statement_type_get', string='Statement type', required=True)
    
    

class country_tva(models.Model):
    """ 
     TVA rates for some countries
    """
    _name = 'country.tva'
    _description = 'TVA rates'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(size=128, required=True)
    country_id = fields.Many2one('res.country', string='Country', required=True, ondelete='restrict')
    partner_id = fields.Many2one('res.partner', string='Partner', required=False, ondelete='cascade')
    
    _sql_constraints = [
        ('unique_country', 'unique(country_id, partner_id)', 'Error: You can\'t have more than one tax number by country.'),
    ]

class res_partner_financial_notation(models.Model):
    """ 
    Financial notation for partners
    """
    _name = 'res.partner.financial.notation'
    _description = 'Financial notation'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(size=64, required=True)
    date = fields.Date(string='Date')
    rating_agency = fields.Char(string='Rating agency', size=168, required=False)
    rating = fields.Char(string='Rating', size=32, required=False)
    recommended_outstandings = fields.Integer(string='Recommended outstandings', default=0, required=False)
    currency_id = fields.Many2one('res.currency', string='Currency', required=False, ondelete='restrict')
    partner_id = fields.Many2one('res.partner', string='Partner', required=False, ondelete='cascade')

class res_partner(models.Model):
    _inherit = 'res.partner'
    
    @api.model
    def _invoices_period_get(self):
        return [
                ('end_week', _('End of week')),
                ('end_month', _('End of month')),
                       ]
    
    @api.model
    def _accounting_communication_method_get(self):
        return [
                ('email', _('Email')),
                ('printer', _('Printer')),
                ('manual', _('Manual')),
                       ]
    
    @api.one
    @api.depends('email', 'fax', 'invoicing_contact_ids', 'accounting_communication_method')
    def _compute_communication_value(self):
        self.communication_value = self.env['res.partner'].calcul_value_com(self.invoicing_contact_ids, self, self.accounting_communication_method)
            
    @api.one
    def _compute_outstanding(self):
        """
            Fonction permettant de calculer l'encours facture non payé 
            et l'encours facture non payé et dépassé du client et de tous ses partenaires facturés
        """
        invoice_outstanding = 0
        exceed_invoice_outstanding = 0
        no_exceed_invoice_outstanding = 0
        if self.id:
            #On récupère la devise du partenaire et la date du jour pour la conversion de devise
            partner_currency = self.currency_id
            today = fields.Date.today()
            context2 = {'date': today}
            #On recherche toutes les factures client dont le partenaire est le facturé ou le commandeur
            #Et dont l'état n'est pas 'payée' ou 'annulée'
            search_args = [('type', 'in', ('out_invoice', 'out_refund')), ('state', 'not in', ('draft','cancel', 'paid')),
                           '|', ('partner_id', '=', self.id), ('partner_order_id', '=', self.id)]
            invoice_rs = self.env['account.invoice'].search(search_args)
            for invoice in invoice_rs:
                #On converti le montant dans la devise du partenaire si la devise du partenaire et de la facture
                #ne sont pas les mêmes
                if invoice.currency_id != partner_currency:
                    amount = invoice.currency_id.with_context(context2).compute(invoice.residual, partner_currency)
                else:
                    amount = invoice.residual
                
                #On soustrait le montant des avoirs
                if invoice.type == 'out_refund':
                    amount = - amount
                
                invoice_outstanding += amount
                #Si la date d'échéance est dépassée, on ajoute le montant au champ 'Encours facture non payé et dépassé'
                if invoice.date_due < today:
                    exceed_invoice_outstanding += amount
                else:
                    no_exceed_invoice_outstanding += amount
                    
            
        self.invoice_outstanding = invoice_outstanding
        self.exceed_invoice_outstanding = exceed_invoice_outstanding
        self.no_exceed_invoice_outstanding = no_exceed_invoice_outstanding
            
    @api.one
    @api.depends('')
    def _compute_amount_invoice(self):
        """
            Fonction qui calcule le montant facturé non payé et le 
            montant de commande en cours - le montant des factures payées ou à payer
        """
        self.not_paid_invoice = 0 
        self.in_progress_amount = 0
            
    #===========================================================================
    # COLUMNS
    #===========================================================================
    # Onglet comptabilité de la fiche partenaire
    accounting_manager_id = fields.Many2one('res.users', string='Accounting manager', required=False, ondelete='restrict')
    siret_number = fields.Char(string='Siret number', size=32, required=False)
    ape_number = fields.Char(string='APE number', size=16, required=False)
    tva_rate_ids = fields.One2many('country.tva', 'partner_id',  string='TVA rates')
    lock_invoices = fields.Boolean(string='Lock invoices', default=False)
    group_invoices = fields.Boolean(string='Group invoices', default=False)
    invoices_period = fields.Selection('_invoices_period_get', string='Invoices period', required=False)
    invoicing_contact_ids = fields.Many2many('res.partner', 'invoicing_contact_id_partner_rel', 'partner_id', 'contact_id', string='Invoicing contacts')
    #Champ conservé pour la reprise des données, à supprimer plus tard
    invoicing_contact_id = fields.Many2one('res.partner', string='Invoicing contact', required=False, ondelete='restrict')
    accounting_communication_method = fields.Selection('_accounting_communication_method_get', string='Communication method')
    communication_value = fields.Char(string='Communication value', compute='_compute_communication_value')
    credit_limit = fields.Float(string='Credit limit', default=0.0, required=False)
    block_sale_credit = fields.Boolean(string='Block the sale when credit is exceeded', default=False)
    invoice_outstanding = fields.Float(string='Not paid invoice outstanding', compute='_compute_outstanding')
    exceed_invoice_outstanding = fields.Float(string='Exceed invoice outstanding', compute='_compute_outstanding')
    no_exceed_invoice_outstanding = fields.Float(string='No exceed invoice outstanding', compute='_compute_outstanding')
    rating_ids = fields.One2many('res.partner.financial.notation', 'partner_id',  string='Ratings')
    sale_invoice_note = fields.Html(string='Note on sale invoice header')
#     in_progress_amount = fields.Float(string='In progress order amount', compute='_compute_amount_invoice', store=False)
#     not_paid_invoice = fields.Float(string='Not paid invoice amount', compute='_compute_amount_invoice', store=False)
    invoice_copy = fields.Integer(string='Invoice copy', default=1, required=True, help='res_partner.invoice_copy.help')
    invoice_send_address_id = fields.Many2one('address', string='Invoice send address', required=False, ondelete='restrict', help='res_partner.invoice_send_address_id.help')
    
    @api.multi
    def show_partner_invoice(self):
        """
            Fonction qui cherche et retourne les factures du partenaire
        """
        action_struc = {}
        action_dict = get_form_view(self, 'account_openprod.action_see_all_invoices')
        if action_dict and action_dict.get('id') and action_dict.get('type'):
            action = self.env[action_dict['type']].browse(action_dict['id'])
            action_struc = action.read()
            action_struc[0]['context'] = {'partner_id': self.id, 'type': ('out_invoice', 'in_invoice')}
            action_struc = action_struc[0]
              
        return action_struc
    
    
    @api.multi
    def show_partner_refund(self):
        """
            Fonction qui cherche et retourne les avoirs et notes de crédit du partenaire
        """
        action_struc = {}
        action_dict = get_form_view(self, 'account_openprod.action_see_all_invoices')
        if action_dict and action_dict.get('id') and action_dict.get('type'):
            action = self.env[action_dict['type']].browse(action_dict['id'])
            action_struc = action.read()
            action_struc[0]['context'] = {'partner_id': self.id, 'type': ('out_refund', 'in_refund')}
            action_struc = action_struc[0]
              
        return action_struc
    
    
    def compute_domain_args_account(self, args):
        """
            Fonction appelée par le search afin de n'afficher que les contacts inscrits dans la liste de contact du partenaire
        """
        args2 = []
        for arg in args:
            if isinstance(arg, str) or (isinstance(arg, list) and arg[0] in ('!', '|', '&')):
                args2.append(arg)
                continue
             
            #On affiche que les contacts qui font partie de la liste de contact du partenaire
            if arg[0] == 'contact_in_partner_account':
                arg[0] = 'id'
                arg[-1] = [x[1] for x in arg[-1] if x[0] != 2]
            elif arg[0] == 'invoice_contact_in_partner_account':
                arg[0] = 'id'
                arg[1] = 'in'
                invoice_partner = self.browse(arg[-1])
                if invoice_partner and invoice_partner.contact_ids:
                    arg[-1] = [contact_id for contact_id in invoice_partner.contact_ids.ids]
                else:
                    arg[-1] = []
                 
            args2.append(arg)
             
        return args2
 
    @api.model
    def search(self,args=None, offset=0, limit=None, order=None, count=None):
        """
            Modification du search afin de n'afficher que les contacts inscrits dans la liste de contact
            Permet également de n'afficher que les partenaires qui ont le client de la facture en tant
            que client facturé 
        """
        args = args or []
        args_modified = self.compute_domain_args_account(args)
        return super(res_partner,self).search(args=args_modified, offset=offset, limit=limit, order=order, count=count)
     
     
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False,lazy=True):
        domain = self.compute_domain_args_account(domain)
        return super(res_partner, self).read_group(domain=domain, fields=fields, groupby=groupby, offset=offset, limit=limit, orderby=orderby,lazy=lazy)
    
    
    
    