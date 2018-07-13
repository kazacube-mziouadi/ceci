# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.addons.base_openprod.common import get_form_view
from openerp.exceptions import ValidationError

class invoice_reconciliation_wizard(models.TransientModel):
    """ 
        Wizard to reconcile payments from an invoice
    """
    _name = 'invoice.reconciliation.wizard'
    _description = 'Wizard to reconcile payments from an invoice'
    
    @api.one
    @api.depends('currency_id', 'company_currency_id')
    def _compute_same_currency(self):
        """
            Fonction permettant de vérifier si les devises sont les mêmes afin d'afficher ou non
            le montant de la facture dans la devise de la société
        """
        same_currency = True
        if self.currency_id != self.company_currency_id:
            same_currency = False
             
        self.same_currency = same_currency
        
        
    @api.one
    @api.depends('credit_ids', 'credit_ids.amount_to_reconcile', 'debit_ids', 'debit_ids.amount_to_reconcile')
    def _compute_total_reconcile_amount(self):
        """
            Fonction permettant de voir s'il s'agit d'un lettrage partiel ou complet
        """
        #On parcourt toutes les lignes et on regarde:
        #    -Si le montant à réconcilier est égal au montant du paiement
        #    -Si le total convertit dans la devise de la facture est égal au total du restant à payer de la facture
        total_amount = 0
        total_payment_amount = 0
        context = self.env.context
        full_reconcile = False
        no_complete_reconcile = False
        for cr_line in self.credit_ids:
            if cr_line.currency_id and not cr_line.is_partial:
                context2 = {'date': cr_line.date}
                context2.update(context)
                total_payment_amount += cr_line.currency_id.with_context(context2).compute(cr_line.move_amount, self.currency_id)
                if cr_line.amount_to_reconcile > 0:
                    total_amount += cr_line.currency_id.with_context(context2).compute(cr_line.amount_to_reconcile, self.currency_id)
                    
        for dt_line in self.debit_ids:
            if dt_line.currency_id and not dt_line.is_partial:
                context2 = {'date': dt_line.date}
                context2.update(context)
                total_payment_amount += dt_line.currency_id.with_context(context2).compute(dt_line.move_amount, self.currency_id)
                if dt_line.amount_to_reconcile > 0:
                    total_amount += dt_line.currency_id.with_context(context2).compute(dt_line.amount_to_reconcile, self.currency_id)
        
        if total_amount == self.residual_amount:
            full_reconcile = True
        elif total_amount > self.residual_amount:
            no_complete_reconcile = True
            
        self.total_reconcile_amount = total_amount
        self.total_payment_amount = total_payment_amount
        self.full_reconcile = full_reconcile
        self.no_complete_reconcile = no_complete_reconcile
    
    
    @api.model
    def _invoice_type_get(self):
        return [('out_invoice',_('Customer Invoice')),
                ('in_invoice',_('Supplier Invoice')),
                ('out_refund',_('Customer Refund')),
                ('in_refund',_('Supplier Refund'))]
        
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    partner_id = fields.Many2one('res.partner', string='Payer partner', required=False, ondelete='set null', readonly=True)
    invoice_id = fields.Many2one('account.invoice', string='Invoice', required=False, ondelete='set null', readonly=True)
    invoice_type = fields.Selection('_invoice_type_get', string='Invoice type')
    residual_amount = fields.Float(string='Residual amount', default=0.0, required=False, readonly=True)
    currency_id = fields.Many2one('res.currency', string='Invoice currency', required=False, ondelete='set null')
    residual_company_amount = fields.Float(string='Residual amount (in company currency)', default=0.0, required=False, readonly=True)
    company_currency_id = fields.Many2one('res.currency', string='Company currency', required=False, ondelete='set null')
    credit_ids = fields.One2many('invoice.reconciliation.credit.line', 'invoice_reconciliation_id',  string='Credits')
    debit_ids = fields.One2many('invoice.reconciliation.debit.line', 'invoice_reconciliation_id',  string='Debits')
    same_currency = fields.Boolean(string='Same currency', default=False, compute='_compute_same_currency', store=False)
    total_reconcile_amount = fields.Float(string='Total reconcile payment', default=0.0, compute='_compute_total_reconcile_amount', store=False)
    total_payment_amount = fields.Float(string='Total payment amount', default=0.0, compute='_compute_total_reconcile_amount', store=False)
    full_reconcile = fields.Boolean(string='Full reconcile', default=False, compute='_compute_total_reconcile_amount', store=False)
    no_complete_reconcile = fields.Boolean(string='No reconcile', default=False, compute='_compute_total_reconcile_amount', store=False)
    
    
    @api.model
    def default_get(self, fields_list):
        """
            Surcharge afin de récupérer la facture, le partenaire payeur, les montants résiduels,
            les devises ainsi que les débits et crédits du payeur
        """
        res = super(invoice_reconciliation_wizard, self).default_get(fields_list=fields_list)
        invoice_id = self.env.context.get('active_id')
        if invoice_id and self.env.context.get('active_model') == 'account.invoice':
            partner_ids = []
            invoice_rs = self.env['account.invoice'].browse(invoice_id)
            #On récupère l'écriture à lettrer de la facture
            for line in invoice_rs.move_id.line_id:
                if line.account_id.reconcile:
                    invoice_move_rs = line
                 
            res2 = {'invoice_id': invoice_id,
                    'partner_id': invoice_rs.paid_by_id.id,
                    'residual_amount': invoice_rs.residual,
                    'currency_id': invoice_rs.currency_id.id,
                    'residual_company_amount': invoice_rs.convert_amount,
                    'company_currency_id': invoice_rs.company_id.currency_id.id,
                    'invoice_type': invoice_rs.type}
            #On recherche les écritures correspondants au partenaire
            type_dict = {'out_invoice': 'out_refund',
                         'in_refund': 'in_invoice',
                         'out_refund': 'out_invoice',
                         'in_invoice': 'in_refund'}
            partner_ids = [invoice_rs.paid_by_id.id]
            move_args = [('reconcile_id','=',False), 
                         ('account_id.reconcile','=',True), 
                         ('partner_id', 'in', partner_ids),
                         ('account_id.type', 'in', ('payable', 'receivable'))]
            if invoice_rs.type in ['out_invoice', 'in_refund']:
                move_args.append(('credit', '>', 0))
            elif invoice_rs.type in ['out_refund', 'in_invoice']:
                move_args.append(('debit', '>', 0))
            
            invoice_type = type_dict[invoice_rs.type]
            #On recherche toutes les écritures comptables non lettrées du partenaire
            partner_ids.append(invoice_rs.partner_id.id)
            partner_move_line_rs = self.env['account.move.line'].search(move_args)
            if partner_move_line_rs:
                list_cr_line = []
                list_dt_line = []
                reconcile_partial_amount = {}
                for move_line in partner_move_line_rs:
                    if (not move_line.invoice or move_line.invoice.type == invoice_type):
                        if move_line.currency_id:
                            currency_rc = move_line.currency_id
                        elif move_line.account_id.currency_id:
                            currency_rc = move_line.account_id.currency_id
                        else:
                            currency_rc = move_line.company_id.currency_id
                            
                        vals = {'account_move_id': move_line.id,
                                'name': move_line.name,
                                'account_id': move_line.account_id.id,
                                'date': move_line.date,
                                'currency_id': currency_rc.id,
                                'invoice_currency_id': invoice_rs.currency_id.id or False,
                                'is_partial': False}
                        
                        if move_line.debit:
                            vals['move_amount'] = move_line.debit
                            if currency_rc != invoice_rs.currency_id:
                                context2 = {'date': move_line.date}
                                context2.update(self.env.context)
                                invoice_amount = currency_rc.with_context(context2).compute(vals['move_amount'], invoice_rs.currency_id)
                            else:
                                invoice_amount = vals['move_amount']

                            vals['invoice_amount'] = invoice_amount
                            list_dt_line.append((0, 0, vals))
                        elif move_line.credit:
                            vals['move_amount'] = move_line.credit
                            if currency_rc != invoice_rs.currency_id:
                                context2 = {'date': move_line.date}
                                context2.update(self.env.context)
                                invoice_amount = currency_rc.with_context(context2).compute(vals['move_amount'], invoice_rs.currency_id)
                            else:
                                invoice_amount = vals['move_amount']

                            vals['invoice_amount'] = invoice_amount
                            list_cr_line.append((0, 0, vals))
                        
                        #Il existe 2 cas de lettrage partiel à afficher:
                        #    -le paiement ou l'avoir qui est déjà partiellement lettré avec la facture
                        #        -> dans ce cas on affiche son montant lettré en RO
                        #    -le paiement ou l'avoir qui est partiellement lettré mais pas avec la facture actuelle 
                        #        -> dans ce cas on récupère le montant restant à lettrer
                        if move_line.reconcile_partial_id:
                            amount_to_rec = 0
                            reconcile_partial_rs = move_line.reconcile_partial_id
                            if not reconcile_partial_rs.id in reconcile_partial_amount:
                                reconcile_partial_amount[reconcile_partial_rs.id] = abs(move_line.amount_residual)
                            
                            if invoice_move_rs in reconcile_partial_rs.line_partial_ids:
                                vals['is_partial'] = True
                                vals['amount_to_reconcile'] = move_line.debit or move_line.credit
                            else:
                                amount_line = move_line.debit or move_line.credit
                                partial_amount = reconcile_partial_amount[reconcile_partial_rs.id]
                                amount_to_rec = 0
                                if partial_amount <= 0:
                                    vals['amount_to_reconcile'] = amount_line
                                elif amount_line - partial_amount > 0:
                                    vals['move_amount'] = amount_line - partial_amount
                                    amount_to_rec = partial_amount
                                elif amount_line - partial_amount < 0:
                                    vals['move_amount'] = partial_amount - amount_line
                                    amount_to_rec = partial_amount
                                else:
                                    vals['move_amount'] = 0
                                    amount_to_rec = amount_line
                                    
                                if currency_rc != invoice_rs.currency_id:
                                    context2 = {'date': move_line.date}
                                    context2.update(self.env.context)
                                    invoice_amount = currency_rc.with_context(context2).compute(vals['move_amount'], invoice_rs.currency_id)
                                else:
                                    invoice_amount = vals['move_amount']

                                vals['invoice_amount'] = invoice_amount
                                
                            reconcile_partial_amount[reconcile_partial_rs.id] -= amount_to_rec
                                    
                res2['credit_ids'] = list_cr_line
                res2['debit_ids'] = list_dt_line
                res.update(res2)
                
        return res
    
    
    def retrieve_account_move_line(self, invoice_rs):
        """
            Fonction permettant de récupérer les montants à lettrer associés aux paiements ainsi que
            toutes les écritures comptables à lettrer. Prend le recordset d'une facture comme argument.
            Retourne:
                - La liste des montants de chaque paiement (account.voucher) à lier à la facture
                - La liste des montants de chaque écriture à lier à la facture (cas d'un lettrage complet
                    avec paiement plus élevé que le montant à payer)
                - La liste des écritures comptables à lettrer (sans celle de la facture)
                - L'écriture comptable correspondant à la facture
        """
        pay_amount_to_reconcile = {}
        move_amount_to_reconcile = {}
        move_rs = invoice_rs.move_id 
        move_line_obj = self.env['account.move.line']
        account_obj = self.env['account.voucher']
        #On recherche l'écriture comptable non lettrée de la facture
        args = [('reconcile_id','=',False), 
                ('account_id.reconcile','=',True), 
                ('move_id', '=', move_rs.id),
                ('account_id.type', 'in', ('payable', 'receivable'))]
        inv_move_line_rs = move_line_obj.search(args)
        reconcile_list = self.env['account.move.line']
        #Récupération des ids des paiements et des montants à lettrer pour chaque paiement
        #Et des écritures comptables non lettrées des débits et crédits
        for move_line_cr in self.credit_ids:
            if move_line_cr.amount_to_reconcile > 0:
                reconcile_list += move_line_cr.account_move_id
                #On récupère le montant correspondant à chaque écriture
                move_amount_to_reconcile[move_line_cr.account_move_id.id] = move_line_cr.amount_to_reconcile
                #on recherche le paiement qui correspond à la pièce comptable de l'écriture
                payment_rs = account_obj.search([('account_move_ids', 'in', move_line_cr.account_move_id.move_id.id)], limit=1)
                if payment_rs:
                    pay_amount_to_reconcile[payment_rs.id] = move_line_cr.amount_to_reconcile
                    
        for move_line_dt in self.debit_ids:
            if move_line_dt.amount_to_reconcile > 0:
                reconcile_list += move_line_dt.account_move_id
                #On récupère le montant correspondant à chaque écriture
                move_amount_to_reconcile[move_line_dt.account_move_id.id] = move_line_dt.amount_to_reconcile
                #on recherche le paiement qui correspond à la pièce comptable de l'écriture
                payment_rs = account_obj.search([('account_move_ids', 'in', move_line_dt.account_move_id.move_id.id)], limit=1)
                if payment_rs:
                    pay_amount_to_reconcile[payment_rs.id] = move_line_dt.amount_to_reconcile
            
        return pay_amount_to_reconcile, move_amount_to_reconcile, reconcile_list, inv_move_line_rs
    
    
    @api.multi
    def create_reconciliation_with_adjust(self):
        """
            Lettrage des écritures en passant par un lettrage avec
            ajustement
        """
        res = {'type':'ir.actions.act_window_view_reload'}
        if self.total_reconcile_amount != self.residual_amount:
            context2 = {}
            context2.update(self.env.context)
            invoice_rs = self.invoice_id
            context2['invoice_id'] = invoice_rs.id
            pay_amount_to_reconcile, move_amount_to_reconcile, reconcile_list, inv_move_line_rs = self.retrieve_account_move_line(invoice_rs)
            context2['payment_lines'] = pay_amount_to_reconcile
            #On passe les ids des écritures à lettrer dans le context
            if reconcile_list:
                reconcile_list += inv_move_line_rs
                context2['active_ids'] = reconcile_list.ids
                #Appel du wizard de lettrage avec ajustement
                context2['default_adjustment_amount'] = self.total_reconcile_amount - self.residual_amount
                res = self.env['account.move.line.reconcile.writeoff'].with_context(context2).trans_rec_addendum()
            
        return res
    
    
    @api.multi
    def create_reconciliation(self):
        """
            Lettrage des écritures:
            - Le montant payé est égal au montant à payer: lettrage total
            - Le montant payé est inférieur au montant à payer: lettrage partiel
            - Le montant payé est supérieur au montant à payer: lettrage et écriture supplémentaire
        """
        context2 = {}
        context2.update(self.env.context)
        invoice_rs = self.invoice_id
        context2['invoice_id'] = invoice_rs.id
        recon_to_write_rs = self.env['account.move.line']
        today_date = fields.Date.today()
        pay_amount_to_reconcile, move_amount_to_reconcile, reconcile_list, inv_move_line_rs = self.retrieve_account_move_line(invoice_rs)
        context2['payment_lines'] = pay_amount_to_reconcile
        #Récupèration de la période de la date du jour
        period_ids = self.env['account.period'].find(dt=today_date)
        period_id = period_ids and period_ids[0] or False
        if period_ids:
            period_id = period_ids[0]
            
        total_reconcile_amount = self.total_reconcile_amount        
        if reconcile_list and total_reconcile_amount > 0:
            residual_amount = self.residual_amount
            total_payment_amount = self.total_payment_amount
            if total_reconcile_amount == residual_amount and total_reconcile_amount == total_payment_amount:
                #Lancement de la méthode de réconciliation totale
                reconcile_list += inv_move_line_rs
                reconcile_list.with_context(context2).reconcile('manual', False, period_id, False)
            elif total_reconcile_amount < residual_amount:
                #Si le montant payé est inférieur au montant à payer, on fait un lettrage partiel
                reconcile_list += inv_move_line_rs
                reconcile_list.with_context(context2).reconcile_partial('manual')
            elif total_payment_amount > residual_amount:
                #Si le montant payé est supérieur au montant à payer, on crée les écritures supplémentaires
                new_reconcile_list, move_not_reconcile = inv_move_line_rs.openprod_adjust_reconcile(move_line_list=reconcile_list, 
                                                                             move_amount_to_reconcile=move_amount_to_reconcile)
                for reconcile in new_reconcile_list:
                    if reconcile:
                        reconcile_list += reconcile
                        recon_to_write_rs += reconcile
                
                for not_reconcile in move_not_reconcile:
                    recon_to_write_rs += not_reconcile
                
                reconcile_list += inv_move_line_rs
                #Puis on fait un lettrage total
                reconcile_id = reconcile_list.with_context(context2).reconcile('manual', False, period_id, False)
                recon_to_write_rs.write({'reconcile_origin_id': reconcile_id.id})
                
        return {'type':'ir.actions.act_window_view_reload'}
    
    

class invoice_reconciliation_credit_line(models.TransientModel):
    """ 
        Credit lines to reconcile payments from an invoice
    """
    _name = 'invoice.reconciliation.credit.line'
    _description = 'Credit lines to reconcile payments from an invoice'
    
    
    @api.one
    @api.depends('account_move_id')
    def _compute_currency_id(self):
        """
            On récupère la devise de l'écriture comptable, 
            ou celle du compte de l'écriture comptable,
            ou celle de la société de l'écriture comptable
        """
        currency_id = False
        account_move = self.account_move_id
        if account_move:
            if account_move.currency_id:
                currency_id = account_move.currency_id
            elif account_move.account_id.currency_id:
                currency_id = account_move.account_id.currency_id.id
            else:
                currency_id = account_move.company_id.currency_id and account_move.company_id.currency_id.id or False  
                
        self.currency_id = currency_id
        
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    account_move_id = fields.Many2one('account.move.line', string='Account move', required=False, ondelete='set null', readonly=True)
    name = fields.Char(string='Name', size=64, required=False, readonly=True)
    invoice_reconciliation_id = fields.Many2one('invoice.reconciliation.wizard', string='Reconciliation wizard', required=False, ondelete='set null', readonly=True)
    move_amount = fields.Float(string='Amount', default=0.0, required=False, readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=False, ondelete='set null', readonly=True)
    invoice_amount = fields.Float(string='Amount in invoice currency', default=0.0, required=False, readonly=True)
    invoice_currency_id = fields.Many2one('res.currency', string='Invoice currency', required=False, ondelete='set null', readonly=True)
    date = fields.Date(string='Date', readonly=True)
    account_id = fields.Many2one('account.account', string='Account', required=False, ondelete='set null', readonly=True)
    amount_to_reconcile = fields.Float(string='Amount to reconcile', default=0.0, required=False)
    amount_to_reconcile_inv_curr = fields.Float(string='Amount to reconcile (invoice currency)', default=0.0, required=False)
    is_partial = fields.Boolean(string='Partial payment', default=False, readonly=True)
    
    _sql_constraints = [
        ('check_amount_to_reconcile', 'CHECK(amount_to_reconcile<=move_amount)', 'The amount to reconcile must be inferior to the available '
                                                                                        'amount of the account move')
    ]
    
    
    @api.onchange('amount_to_reconcile_inv_curr')
    def _onchange_amount_to_reconcile(self):
        """
            Au changement du montant à réconcilier, on vérifie qu'il ne soit pas supérieur
            au montant restant de l'écriture
        """
        res = {'warning': {}}
        if self.amount_to_reconcile_inv_curr > self.invoice_amount:
            res['warning'] = {'title': _('Warning'), 'message': _('The amount to reconcile must be inferior to the available '
                                                                  'amount of the account move')}
        
        if self.currency_id != self.invoice_currency_id:
            context2 = {'date': self.date}
            context2.update(self.env.context)
            self.amount_to_reconcile = self.invoice_currency_id.with_context(context2).compute(self.amount_to_reconcile_inv_curr, self.currency_id)
        else:
            self.amount_to_reconcile = self.amount_to_reconcile_inv_curr
            
        return res
    
    
    
class invoice_reconciliation_debit_line(models.TransientModel):
    """ 
        Debit lines to reconcile payments from an invoice
    """
    _name = 'invoice.reconciliation.debit.line'
    _description = 'Debit lines to reconcile payments from an invoice'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    account_move_id = fields.Many2one('account.move.line', string='Account move', required=False, ondelete='set null', readonly=True)
    name = fields.Char(string='Name', size=64, required=False, readonly=True)
    invoice_reconciliation_id = fields.Many2one('invoice.reconciliation.wizard', string='Reconciliation wizard', required=False, ondelete='set null', readonly=True)
    move_amount = fields.Float(string='Amount', default=0.0, required=False, readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=False, ondelete='set null', readonly=True)
    invoice_amount = fields.Float(string='Amount in invoice currency', default=0.0, required=False, readonly=True)
    invoice_currency_id = fields.Many2one('res.currency', string='Invoice currency', required=False, ondelete='set null', readonly=True)
    date = fields.Date(string='Date', readonly=True)
    account_id = fields.Many2one('account.account', string='Account', required=False, ondelete='set null', readonly=True)
    amount_to_reconcile = fields.Float(string='Amount to reconcile', default=0.0, required=False)
    amount_to_reconcile_inv_curr = fields.Float(string='Amount to reconcile (invoice currency)', default=0.0, required=False)
    is_partial = fields.Boolean(string='Partial payment', default=False, readonly=True)
    
    _sql_constraints = [
        ('check_amount_to_reconcile', 'CHECK(amount_to_reconcile<=move_amount)', 'The amount to reconcile must be inferior to the available '
                                                                                        'amount of the account move')
    ]
    
    
    @api.onchange('amount_to_reconcile_inv_curr')
    def _onchange_amount_to_reconcile(self):
        """
            Au changement du montant à réconcilier, on vérifie qu'il ne soit pas supérieur
            au montant restant de l'écriture
        """
        res = {'warning': {}}
        if self.amount_to_reconcile_inv_curr > self.invoice_amount:
            res['warning'] = {'title': _('Warning'), 'message': _('The amount to reconcile must be inferior to the available '
                                                                  'amount of the account move')}
        
        if self.currency_id != self.invoice_currency_id:
            context2 = {'date': self.date}
            context2.update(self.env.context)
            self.amount_to_reconcile = self.invoice_currency_id.with_context(context2).compute(self.amount_to_reconcile_inv_curr, self.currency_id)
        else:
            self.amount_to_reconcile = self.amount_to_reconcile_inv_curr
            
        return res



class account_move_line_reconcile(models.TransientModel):
    _inherit = 'account.move.line.reconcile'


    @api.multi
    def create_reconciliation_with_adjust(self):
        """
            Lettrage des écritures en passant par un lettrage avec
            ajustement
        """
        res = {'type':'ir.actions.act_window_view_reload'}
        if self.writeoff != 0:
            context2 = {}
            context2.update(self.env.context)
            context2['default_adjustment_amount'] = self.writeoff / -1
            res = self.env['account.move.line.reconcile.writeoff'].with_context(context2).trans_rec_addendum()
        
        return res
    
    
    @api.multi
    def create_reconciliation(self):
        """
            Lettrage des écritures:
            - Le montant payé est égal au montant à payer: lettrage total
            - Le montant payé est inférieur au montant à payer: lettrage partiel
            - Le montant payé est supérieur au montant à payer: lettrage et écriture supplémentaire
        """
        active_ids = self.env.context.get('active_ids')
        if active_ids:
            new_reconcile_list = []
            move_not_reconcile = []
            reconcile_list = self.env['account.move.line'].browse(active_ids)
            inv_move_line_rs = self.env['account.move.line']
            refund_move_line_rs = self.env['account.move.line']
            no_inv_move_line_rs = self.env['account.move.line']
            recon_to_write_rs = self.env['account.move.line']
            today_date = fields.Date.today()
            #Récupèration de la période de la date du jour
            period_ids = self.env['account.period'].find(dt=today_date)
            period_id = period_ids and period_ids[0] or False
            if period_ids:
                period_id = period_ids[0]
            
            context = self.env.context
            if self.writeoff == 0:
                reconcile_list.reconcile('manual', False, period_id, False)
                if context and 'account_bank_statement_line_id' in context and context['account_bank_statement_line_id'] and reconcile_list and reconcile_list[0].reconcile_id:
                    self.env['account.bank.statement.line.openprod'].browse(context['account_bank_statement_line_id']).write({'reconcile_id': reconcile_list[0].reconcile_id.id})
                
            elif self.writeoff > 0:
                self.env['account.move.line.reconcile.writeoff'].trans_rec_reconcile_partial()
                move_line_int = self.env['account.move.line'].browse(active_ids[0])
                if context and 'account_bank_statement_line_id' in context and context['account_bank_statement_line_id'] and move_line_int.reconcile_partial_id:
                    self.env['account.bank.statement.line.openprod'].browse(context['account_bank_statement_line_id']).write({'reconcile_id': reconcile_list[0].reconcile_partial_id.id})
            else:
                #Si le montant payé est supérieur au montant à payer, on crée les écritures supplémentaires
                #On récupère uniquement les écritures des factures s'il y a des factures et des avoirs
                #ou uniquement les avoirs s'il n'y a que des avoirs
                #Et on met les autres mouvements (de paiement et d'avoir) dans une autre liste
                for reco_move in reconcile_list:
                    if reco_move.invoice:
                        if reco_move.invoice.type in ['out_invoice', 'in_invoice']:
                            inv_move_line_rs += reco_move
                        elif reco_move.invoice.type in ['out_refund', 'in_refund']:
                            refund_move_line_rs += reco_move
                    
                    else:
                        no_inv_move_line_rs += reco_move
                
                if inv_move_line_rs:
                    no_inv_move_line_rs += refund_move_line_rs
                    new_reconcile_list, move_not_reconcile = inv_move_line_rs.openprod_adjust_reconcile(move_line_list=no_inv_move_line_rs, 
                                                                                 move_amount_to_reconcile={})
                elif refund_move_line_rs:
                    new_reconcile_list, move_not_reconcile = inv_move_line_rs.openprod_adjust_reconcile(move_line_list=no_inv_move_line_rs, 
                                                                                 move_amount_to_reconcile={})
                    
                for reconcile in new_reconcile_list:
                    if reconcile:
                        reconcile_list += reconcile
                        recon_to_write_rs += reconcile
                
                for not_reconcile in move_not_reconcile:
                    recon_to_write_rs += not_reconcile
                
                #Puis on fait un lettrage total
                reconcile_rs = reconcile_list.reconcile('manual', False, period_id, False)
                recon_to_write_rs.write({'reconcile_origin_id': reconcile_rs.id})
                if context and 'account_bank_statement_line_id' in context and context['account_bank_statement_line_id'] and reconcile_rs:
                    self.env['account.bank.statement.line.openprod'].browse(context['account_bank_statement_line_id']).write({'reconcile_id': reconcile_rs.id})
                    
        return {'type':'ir.actions.act_window_view_reload'}



class account_move_line_reconcile_writeoff(models.TransientModel):
    _inherit = 'account.move.line.reconcile.writeoff'
    
    
    @api.multi
    def trans_rec_reconcile(self):
        """
            On écrase la fonction de base de Odoo pour lier les écritures de
            write-off au lettrage de base afin de les supprimer en cas de délettrage
        """
        context = self.env.context
        account_move_line_obj = self.env['account.move.line']
        merges = self.env['account.move.line']
        period_obj = self.env['account.period']
        move_ids_list = []
        if context is None:
            context = {}
            
        context2 = {}
        context2.update(context)
        if context.get('data_read') and isinstance(context['data_read'], dict):
            data = context['data_read']
            account_id = data['writeoff_acc_id']
            context2['date_p'] = data['date_p']
            journal_id = data['journal_id']
            context2['comment'] = data['comment']
            if data.get('analytic_id', False):
                context2['analytic_id'] = data['analytic_id']
                
        else:
            data = self.read()[0]
            account_id = data['writeoff_acc_id'][0]
            context2['date_p'] = data['date_p']
            journal_id = data['journal_id'][0]
            context2['comment'] = data['comment']
            if data['analytic_id']:
                context2['analytic_id'] = data['analytic_id'][0]
                
        if context2.get('date_p'):
            date = context2['date_p']
        else:
            date = fields.Date.today()
        
        period_rs = period_obj.find(date)
        if period_rs:
            period_id = period_rs[0].id
        
        account_move_rs = account_move_line_obj.browse(context['active_ids'])
        for account_move_line in account_move_rs:
            merges += account_move_line
            if account_move_line.reconcile_partial_id:
                for line2 in account_move_line.reconcile_partial_id.line_partial_ids:
                    if not line2.reconcile_id:
                        if line2 not in merges:
                            merges += line2
                            
        reconcile_rs = merges.with_context(context2).reconcile('manual', account_id, period_id, journal_id)
        #On recherche les écritures comptable en plus dans le lettrage afin de les marquer comme ajustement de
        #ce lettrage. Pour cela on remonte jusqu'à la pièce comptable et on modifie toutes les écritures de cette pièce
        adjustment_move_rs = account_move_line_obj.search([('reconcile_id', '=', reconcile_rs.id), ('id', 'not in', context['active_ids'])])
        for adjustment_move in adjustment_move_rs:
            move_ids_list.append(adjustment_move.move_id.id)
        
        adjustment_to_write_rs = account_move_line_obj.search([('move_id', 'in', move_ids_list)])
        adjustment_to_write_rs.write({'is_adjustment': True,
                             'reconcile_origin_id': reconcile_rs.id})
        
        if context and 'account_bank_statement_line_id' in context and context['account_bank_statement_line_id']:
            self.env['account.bank.statement.line.openprod'].browse(context['account_bank_statement_line_id']).write({'reconcile_id': reconcile_rs.id})

        return {'type': 'ir.actions.act_window_close'}
