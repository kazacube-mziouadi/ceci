# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
from datetime import timedelta, datetime
from openerp.tools.float_utils import float_round
from openerp.addons.base_openprod.common import roundingUp, rounding
from math import *


class account_bank_statement_openprod(models.Model):
    """ 
        Account bank statement openprod 
    """
    _name = 'account.bank.statement.openprod'
    _inherit = 'workflow.base'
    _description = 'Account bank statement openprod'

    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('validated', _('Validated')),
                ('done', _('Done')),
                ('cancel', _('Cancel')),
                       ]
    

    @api.one   
    def _compute_move_voucher_no_used_ids(self):
        """
            Toutes les resources
        """
        self.move_voucher_no_used_ids = self.compute_move_voucher_no_used_ids()
    
    
    @api.one   
    def _compute_final_solde(self):
        """
            Toutes les resources
        """
        final_solde = self.init_solde
        currency_rcs = self.currency_id
        for line in self.line_ids:
            if currency_rcs != line.currency_id:
                context2 = {}
                context2.update(self.env.context)
                context2['date'] = line.date
                if line.credit:
                    final_solde += line.currency_id.with_context(context2).compute(line.credit, currency_rcs)
                else:
                    final_solde -= line.currency_id.with_context(context2).compute(line.debit, currency_rcs)
            else:
                if line.credit:
                    final_solde += line.credit
                else:
                    final_solde -= line.debit
        
        self.final_solde_cal = final_solde
    
    
    @api.one   
    @api.depends('company_id','journal_id')
    def _compute_currency_id(self):
        self.currency_id = self.journal_id and self.journal_id.currency and self.journal_id.currency.id or self.company_id and self.company_id.currency_id and self.company_id.currency_id.id or False
    
    
    @api.one   
    def _compute_record_solde(self):
        """
            Toutes les resources
        """
        record_final_solde = self.final_solde
        total_unused_bank = 0
        move_line_obj = self.env['account.move.line']
        account_debit_id = self.journal_id.default_debit_account_id.id
        account_credit_id = self.journal_id.default_credit_account_id.id
        if self.move_voucher_no_used_ids:
            move_line_debit_rcs = move_line_obj.search([('move_id', 'in', self.move_voucher_no_used_ids.ids),
                                                        ('account_id', '=', account_debit_id),
                                                        ('debit', '!=', 0)])
            for move_line in move_line_debit_rcs:
                total_unused_bank += move_line.debit
        
            move_line_credit_rcs = move_line_obj.search([('move_id', 'in', self.move_voucher_no_used_ids.ids),
                                                        ('account_id', '=', account_credit_id),
                                                        ('credit', '!=', 0)])
            for move_line in move_line_credit_rcs:
                total_unused_bank -= move_line.debit
        
        
        self.record_final_solde = record_final_solde
        self.total_unused_bank = total_unused_bank
        self.total_theoretical_bank = record_final_solde + total_unused_bank
        
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Name', size=256, required=True)
    date = fields.Date(string='Create date', default=lambda self: fields.Datetime.now())
    period_id = fields.Many2one('account.period', string='Period', domain=[('state', '!=', 'done')], copy=False,)
    company_id = fields.Many2one('res.company', string='Company', required=True, ondelete='restrict', default=lambda self: self.env.user.company_id)
    journal_id = fields.Many2one('account.journal', string='Bank journal', required=True, ondelete='restrict', domain=[('type', '=', 'bank')])
    init_solde = fields.Float(string='Init solde', default=0.0, required=False, digits=dp.get_precision('Account'))
    final_solde = fields.Float(string='Final solde', default=0.0, required=False, digits=dp.get_precision('Account'))
    final_solde_cal = fields.Float(string='Final solde', compute='_compute_final_solde', required=False, digits=dp.get_precision('Account'))
    nb_day_deviation = fields.Integer(string='Number of days deviation', default=0, required=False)
    amount_deviation = fields.Float(string='Amount of deviation', default=0.0, required=False, digits=dp.get_precision('Account'))
    state = fields.Selection('_state_get', string='State', default='draft')
    line_ids = fields.One2many('account.bank.statement.line.openprod', 'bank_statement_id',  string='Lines')
    currency_id = fields.Many2one('res.currency', string='Currency', compute='_compute_currency_id', store=True)
    move_voucher_no_used_ids = fields.One2many('account.move', compute='_compute_move_voucher_no_used_ids',  string='Voucher no used')
    record_final_solde = fields.Float(string='Final solde', compute='_compute_record_solde')
    total_unused_bank = fields.Float(string='Total unused bank', compute='_compute_record_solde')
    total_theoretical_bank = fields.Float(string='Total theoretical bank', compute='_compute_record_solde')
    
    
    #===========================================================================
    # onchange
    #===========================================================================
    @api.onchange('journal_id')
    def _onchange_company_id(self):
        init_solde = 0
        if self.journal_id:
            agrs_search = [('journal_id', '=', self.journal_id.id), ('state', 'not in', ('draft', 'cancel'))]
            if self.id:
                agrs_search.append(('id', '!=', self.id))
                
            bank_statement_rcs = self.search(agrs_search, order='date desc', limit=1)
            if bank_statement_rcs:
                init_solde = bank_statement_rcs.final_solde
        
        self.init_solde = init_solde
    
    
    #===========================================================================
    # Bouton
    #===========================================================================
    @api.multi
    def button_search_partner(self):
        partner_obj = self.env['res.partner']
        for abso in self:
            for line in abso.line_ids:
                if line.name and not line.partner_id:
                    partner_rcs = self.env['res.partner']
                    for name in line.name.split(' '):
                        if len(name) > 2:
                            partner_rcs |= partner_obj.search([('is_company', '=', True), '|', ('reference', 'ilike', name), ('name', 'ilike', name)])

                    if partner_rcs and len(partner_rcs) == 1:
                        account_id = line.compute_account_id(partner_rcs)
                        vals = {'partner_id': partner_rcs.id}
                        if account_id:
                            vals['account_id'] = account_id
                        
                        line.write(vals)
            
        return True
            
    
    @api.multi
    def button_search_payment(self):
        move_line_obj = self.env['account.move.line']
        for abso in self:
            for line in abso.line_ids:
                if not line.move_voucher_ids:
                    partner_id = line.partner_id and line.partner_id.id or False
                    account_id = line.account_id and line.account_id.id or False
                    move_voucher_ids = self.search_move_payment(line.journal_id.id, line.credit, line.debit, partner_id, account_id, line.currency_id.id, line.date, 
                                                                line.amount_deviation, line.nb_day_deviation, line.abso_currency_id.id, move_line_obj)
                    
                    if move_voucher_ids:
                        line.write({'move_voucher_ids': [(6, 0, move_voucher_ids)]})
                        
        return True
    
    
    def search_move_payment(self, journal_id, credit, debit, partner_id, account_id, currency_id, date, 
                            amount_deviation, nb_day_deviation, abso_currency_id, move_line_obj, line_id=False):
        move_voucher_ids = []
        list_search = [('journal_id', '=', journal_id), ('move_id', '!=', False)]
        # Recherche partenaire ou compte si pas de partenaire
        if partner_id:
            list_search.append(('partner_id', '=', partner_id))
        else:
            list_search.append(('account_id', '=', account_id))
        
        # Calcule montant par rapport à la devise de la société
        amount = credit or debit
        if abso_currency_id != currency_id:
            context2 = {}
            context2.update(self.env.context)
            context2['date'] = date
            currency_obj = self.env['res.currency']
            amount = currency_obj.browse(currency_id).with_context(context2).compute(amount, currency_obj.browse(abso_currency_id))
        
        # Recherche montant avec ajout ou non d'un écart
        if amount_deviation:
            amount_max = amount + amount_deviation
            amount_min = amount - amount_deviation
            if credit:
                list_search.append(('credit', '<=', amount_max))
                list_search.append(('credit', '>=', amount_min))
            else:
                list_search.append(('debit', '<=', amount_max))
                list_search.append(('debit', '>=', amount_min))
        else:
            if credit:
                list_search.append(('credit', '=', amount))
            else:
                list_search.append(('debit', '=', amount))
        
        # Recherche date avec ajout ou non d'un écart
        if nb_day_deviation:
            max_date = fields.Date.to_string(datetime.strptime(date, '%Y-%m-%d') + timedelta(days=nb_day_deviation))
            min_date = fields.Date.to_string(datetime.strptime(date, '%Y-%m-%d') - timedelta(days=nb_day_deviation))
            list_search.append(('date', '<=', max_date))
            list_search.append(('date', '>=', min_date))
        else:
            list_search.append(('date', '=', date))
        
        move_voucher_line_rcs = move_line_obj.search(list_search)
        if move_voucher_line_rcs:
            move_voucher_rcs = self.env['account.move']
            for move_voucher_line in move_voucher_line_rcs:
                if move_voucher_line.move_id.state == 'posted':
                    move_voucher_rcs |= move_voucher_line.move_id
            
            if move_voucher_rcs:
                if line_id:
                    self.env.cr.execute(""" select 
                                            account_move.id
                                        from 
                                            (select id from account_move where id in %s) as account_move
                                        where 
                                            account_move.id not in (select move_voucher_id from absl_move_voucher_rel where absl_id != %s)
                                        """, (tuple(move_voucher_rcs.ids), line_id)) 
                else:
                    self.env.cr.execute(""" select 
                                            account_move.id
                                        from 
                                            (select id from account_move where id in %s) as account_move
                                        where 
                                            account_move.id not in (select move_voucher_id from absl_move_voucher_rel)
                                        """, (tuple(move_voucher_rcs.ids), ))
                res = self.env.cr.fetchall()  
                if res:
                    move_voucher_ids = [x[0] for x in res]
                        
        return move_voucher_ids
    
    
    @api.multi
    def button_search_move_invoice(self):
        invoice_obj = self.env['account.invoice']
        for abso in self:
            for line in abso.line_ids:
                if not line.move_invoice_ids:
                    partner_id = line.partner_id and line.partner_id.id or False
                    move_invoice_ids = abso.search_move_invoice(line.name, line.credit, line.debit, partner_id, abso.amount_deviation, invoice_obj, payment_move_ids=line.move_voucher_ids.ids)
                    if move_invoice_ids:
                        line.write({'move_invoice_ids': [(6, 0, move_invoice_ids)]})
                        
        return True
    
    
    def search_move_invoice(self, name, credit, debit, partner_id, amount_deviation, invoice_obj, payment_move_ids=None, line_id=False):
        move_invoice_rcs = self.env['account.move']
        invoice_rcs = self.env['account.invoice']
        move_invoice_ids = []
        for name in name.split(' '):
            if len(name) > 2:
                if credit:
                    invoice_rcs |= invoice_obj.search([('number', 'ilike', name), ('type', 'in', ('out_invoice', 'in_refund')), 
                                                       ('state', 'not in', ('draft', 'cancel')), ('move_id', '!=', False)])
                else:
                    invoice_rcs |= invoice_obj.search([('number', 'ilike', name), ('type', 'in', ('in_invoice', 'out_refund')),
                                                       ('state', 'not in', ('draft', 'cancel')), ('move_id', '!=', False)])
                
        if partner_id and not invoice_rcs:
            list_search = [('state', 'not in', ('draft', 'cancel')), ('move_id', '!=', False)]
            # Recherche facture entrant ou sortant
            if credit:
                list_search.append(('type', 'in', ('out_invoice', 'in_refund')))
            else:
                list_search.append(('type', 'in', ('in_invoice', 'out_refund')))
            
            # Recherche partenaire
            if partner_id:
                list_search.append(('paid_by_id', '=', partner_id))
            
            # Recherche montant avec ajout ou non d'un écart
            amount = credit or debit
            if amount_deviation:
                amount_max = amount + amount_deviation
                amount_min = amount - amount_deviation
                list_search.append(('amount_total', '<=', amount_max))
                list_search.append(('amount_total', '>=', amount_min))
            else:
                list_search.append(('amount_total', '=', amount))
        
            invoice_rcs = invoice_obj.search(list_search)
            aml_obj = self.env['account.move.line']
            if payment_move_ids:
                move_line_temp_rcs = aml_obj.search([('reconcile_id', '!=', False), ('move_id', 'in', payment_move_ids)])
                reconcile_ids = [move_line_temp.reconcile_id.id for move_line_temp in move_line_temp_rcs]
            else:
                reconcile_ids = []
            
            for invoice in invoice_rcs:
                if invoice.move_id:
                    invoice_reconcile_rcs = aml_obj.search([('reconcile_id', '!=', False), ('move_id', '=', invoice.move_id.id)], limit=1)
                    if invoice_reconcile_rcs:
                        invoice_reconcile_id = invoice_reconcile_rcs.reconcile_id.id
                    else:
                        invoice_reconcile_id = False
                    
                    if not invoice_reconcile_id or invoice_reconcile_id in reconcile_ids:
                        move_invoice_rcs |= invoice.move_id
        
        if move_invoice_rcs:
            if line_id:
                self.env.cr.execute(""" select 
                                        account_move.id
                                    from 
                                        (select id from account_move where id in %s) as account_move
                                    where 
                                        account_move.id not in (select move_invoice_id from absl_move_invoice_rel where absl_id != %s)
                                    """, (tuple(move_invoice_rcs.ids), line_id))
            else:
                self.env.cr.execute(""" select 
                                        account_move.id
                                    from 
                                        (select id from account_move where id in %s) as account_move
                                    where 
                                        account_move.id not in (select move_invoice_id from absl_move_invoice_rel)
                                    """, (tuple(move_invoice_rcs.ids), ))
            res = self.env.cr.fetchall()  
            if res:
                move_invoice_ids = [x[0] for x in res]
            
        return move_invoice_ids
    
    
    @api.multi
    def button_generate_regulation_payment(self):
        for abso in self:
            abso.line_ids.button_generate_regulation_payment()
                
        return True
    
    
    @api.multi
    def wkf_cancel(self):
        for abso in self:
            for line in abso.line_ids:
                if line.reconcile_id:
                    line.reconcile_id.unlink()
                
        return True
    
    
    @api.multi
    def wkf_validated(self):
        for abso in self:
            for line in abso.line_ids:
                if line.credit and line.debit:
                    raise except_orm(_('Error!'),
                        _("There may be the values in credit or debit (%s)!") % (line.name,))
                
                elif not line.credit and not line.debit:
                    raise except_orm(_('Error!'),
                        _("There may be the values in credit or debit (%s)!") % (line.name,))
                
                elif line.credit < 0 or line.debit < 0:
                    raise except_orm(_('Error!'),
                        _("The value in credit or debit must be greater than zero (%s)!") % (line.name,))
                
                if not line.account_id:
                    raise except_orm(_('Error!'),
                        _("Please indicate the account on each line (%s)!") % (line.name,))
            
            if not (abso.final_solde >= floor(abso.final_solde_cal*100)/100 and abso.final_solde <= ceil(abso.final_solde_cal*100)/100):
                raise except_orm(_('Error!'),
                        _("The final balance should not match the initial balance added to the amount of lines (%s) !") %(abso.name))
                
        return True
    
    @api.multi
    def wkf_done(self):
        for abso in self:
            for line in abso.line_ids:
                if not line.move_voucher_ids:
                    raise except_orm(_('Error!'),
                        _("It is compulsory to have a payment account per line to done the bank statement(%s) !") %(abso.name))
                
                
                
    @api.multi
    def return_view_bank_statement_line_openprod(self):
        line_rcs = self.env['account.bank.statement.line.openprod'].search([('bank_statement_id', 'in', self.ids)])
        if line_rcs:
            return {
                    'name': _('Bank statement lines'),
                    'view_type': 'form',
                    'view_mode': 'tree',
                    'res_model': 'account.bank.statement.line.openprod',
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'domain': [('id', 'in', line_rcs.ids)],
                    }
        else:
            return True
        
    
    #===========================================================================
    # Fonction
    #===========================================================================
    def compute_move_voucher_no_used_ids(self):
        compute_move_voucher_no_used_ids= []
        if self.journal_id:
            self.env.cr.execute(""" select
                                        id
                                    from
                                        account_move
                                    where
                                        state = 'posted' and
                                        id in ( select 
                                                    move_id
                                                from 
                                                    account_move_line
                                                where 
                                                    move_id not in (select move_voucher_id from absl_move_voucher_rel) and
                                                    account_id = %s and
                                                    journal_id = %s)
                                        """, (self.journal_id.default_debit_account_id.id, self.journal_id.id))
            res = self.env.cr.fetchall()  
            if res:
                compute_move_voucher_no_used_ids = [x[0] for x in res]
        
        return compute_move_voucher_no_used_ids
    


class account_bank_statement_line_openprod(models.Model):
    """ 
        Account bank statement line openprod 
    """
    _name = 'account.bank.statement.line.openprod'
    _description = 'Account bank statement line openprod'

    
    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('validated', _('Validated')),
                ('done', _('Done')),
                ('cancel', _('Cancel')),
                       ]
    
    
    @api.one
    @api.depends('bank_statement_id', 'bank_statement_id.period_id', 'bank_statement_id.journal_id', 'bank_statement_id.amount_deviation',
                 'bank_statement_id.nb_day_deviation', 'bank_statement_id.currency_id', 'bank_statement_id.state', 'name')
    def _compute_val_bank_statement_id(self):
        self.period_id = self.bank_statement_id and self.bank_statement_id.period_id and self.bank_statement_id.period_id.id or False
        self.journal_id = self.bank_statement_id and self.bank_statement_id.journal_id and self.bank_statement_id.journal_id.id or False
        self.amount_deviation = self.bank_statement_id and self.bank_statement_id.amount_deviation or 0
        self.abso_currency_id = self.bank_statement_id and self.bank_statement_id.currency_id and self.bank_statement_id.currency_id.id or False
        self.nb_day_deviation = self.bank_statement_id and self.bank_statement_id.nb_day_deviation or 0
        self.state = self.bank_statement_id and self.bank_statement_id.state or ''
    
    @api.one
    @api.depends('move_voucher_ids', 'move_voucher_ids.name')
    def _compute_amount_voucher(self):
        account_id = self.journal_id.default_debit_account_id.id
        self.amount_voucher = self._compute_amount_line(account_id, self.move_voucher_ids.ids)
        
    
    @api.one
    @api.depends('move_invoice_ids', 'move_invoice_ids.name')
    def _compute_amount_invoice(self):
        account_id = self.account_id.id
        self.amount_invoice = self._compute_amount_line(account_id, self.move_invoice_ids.ids)
    
    
    @api.one
    def _compute_reconcile_id(self):
        reconcile_id = False
        for move_invoice in self.move_invoice_ids:
            for line in move_invoice.line_id:
                if line.reconcile_id:
                    reconcile_id = line.reconcile_id.id
                    break
            
            if reconcile_id:
                break
        
        self.reconcile_id = reconcile_id
        
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    bank_statement_id = fields.Many2one('account.bank.statement.openprod', string='Bank statement', required=False, ondelete='cascade')
    date = fields.Date(string='Date', default=lambda self: fields.Datetime.now(), required=True)
    name = fields.Char(string='Name', size=256, required=True)
    ref = fields.Char(string='Reference', size=256, required=False)
    partner_id = fields.Many2one('res.partner', string='Partner', required=False, ondelete='restrict')
    account_id = fields.Many2one('account.account', string='Account', required=False, ondelete='restrict')
    debit = fields.Float(string='Debit', default=0.0, required=False, digits=dp.get_precision('Account'))
    credit = fields.Float(string='Credit', default=0.0, required=False, digits=dp.get_precision('Account'))
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, ondelete='restrict')
    move_voucher_ids = fields.Many2many('account.move', 'absl_move_voucher_rel', 'absl_id', 'move_voucher_id', string='Account move vouchers')
    analysis = fields.Char(string='Analysis', size=256, required=False)
    move_invoice_ids = fields.Many2many('account.move', 'absl_move_invoice_rel', 'absl_id', 'move_invoice_id', string='Account move invoices')
    reconcile_id = fields.Many2one('account.move.reconcile', string='Reconcile', compute='_compute_reconcile_id')
    period_id = fields.Many2one('account.period', string='Period', compute='_compute_val_bank_statement_id', store=True)
    journal_id = fields.Many2one('account.journal', string='Bank journal', compute='_compute_val_bank_statement_id', store=True)
    amount_deviation = fields.Float(string='Amount deviation', compute='_compute_val_bank_statement_id', store=True)
    nb_day_deviation = fields.Integer(string='Number of days deviation', compute='_compute_val_bank_statement_id', store=True)
    abso_currency_id = fields.Many2one('res.currency', string='Currency', compute='_compute_val_bank_statement_id', store=True)
    amount_voucher = fields.Float(string='Total amount vouchers', compute='_compute_amount_voucher', store=True)
    amount_invoice = fields.Float(string='Total amount invoices', compute='_compute_amount_invoice', store=True)
    state = fields.Selection('_state_get', string='State', compute='_compute_val_bank_statement_id', store=True)
    
    
    #===========================================================================
    # onchange
    #===========================================================================
    @api.onchange('partner_id', 'debit', 'credit')
    def _onchange_partner_id(self):
        account_id = self.compute_account_id(self.partner_id)
        if account_id:
            self.account_id = account_id
            
    
    #===========================================================================
    # Fonction
    #===========================================================================
    def compute_account_id(self, partner):
        account_id = False
        if partner:
            if self.credit:
                account_id = partner.property_account_receivable_id and partner.property_account_receivable_id.id or False
            else:
                account_id = partner.property_account_payable_id and partner.property_account_payable_id.id or False
                
        return account_id
    
    
    def _compute_amount_line(self, account_id, move_ids):
        amount_debit = 0
        amount_credit = 0
        is_credit = self.credit and True or False
        for move_id in move_ids:
            self.env.cr.execute(""" SELECT SUM(debit) 
            FROM account_move_line 
            WHERE move_id = %s 
            and account_id = %s
            group by move_id""", (move_id, account_id))
            res_debit = self.env.cr.fetchall()  
            if res_debit:
                amount_debit += res_debit[0][0]
                
            self.env.cr.execute(""" SELECT SUM(credit) 
            FROM account_move_line 
            WHERE move_id = %s 
            and account_id = %s
            group by move_id""", (move_id, account_id))
            res_credit = self.env.cr.fetchall()  
            if res_credit:
                amount_credit += res_credit[0][0]
                
        return is_credit and amount_debit - amount_credit or amount_credit - amount_debit
    

    def action_generate_payment(self, journal_rs, company_id, payment_type, partner_id, date, amount):
        """
            Fonction permettant de créer le paiement
        """
        #On récupère toutes les valeurs du paiement
        payment_rate = 1
        period_rs = self.env['account.period'].find(date)
        currency_rs = self.currency_id or False
        payment_rate_currency_rs = journal_rs and journal_rs.currency or currency_rs
        if journal_rs and period_rs and currency_rs:
            currency_rate = currency_rs.rate
            if currency_rate != 0:
                payment_rate = payment_rate_currency_rs.rate / currency_rate
            
            account_partner_id = self.account_id.id
            # Preparation paiement
            vals = {
                    'account_partner_id': account_partner_id,
                    'amount': amount,
                    'journal_id': journal_rs.id,
                    'date': date,
                    'partner_id': partner_id,
                    'period_id': period_rs.id,
                    'payment_rate_currency_id': payment_rate_currency_rs.id,
                    'company_id': company_id,
                    'payment_rate': payment_rate,
                    'payment_option': 'without_writeoff',
                    'currency_id': currency_rs.id,
                    'account_id': journal_rs.default_debit_account_id.id,
                    'type': payment_type}
            
            # Creation paiement
            voucher_rcs = self.env['account.voucher'].create(vals)
            # Validation paiement
            voucher_rcs.signal_workflow('proforma_voucher')

        return voucher_rcs
    
    
    @api.multi
    def button_generate_regulation_payment(self):
        for line in self:
            partner_id = line.partner_id and line.partner_id.id or False
            amount = line.credit or line.debit
            if amount != line.amount_voucher:
                amount -= line.amount_voucher
                if amount > 0:
                    payment_type = line.credit and 'receipt' or 'payment'
                else:
                    payment_type = line.credit and 'payment' or 'receipt'
                    amount *= -1
                    
                voucher_rcs = line.action_generate_payment(line.journal_id, line.bank_statement_id.company_id.id, payment_type, partner_id, line.date, amount)
                voucher_rcs.write({'name': line.bank_statement_id.name, 'reference': line.ref})
                move_rcs = False
                for move_line in voucher_rcs.move_ids:
                    if move_line.move_id:
                        move_rcs = move_line.move_id
                        break
                
                if move_rcs:
                    line.write({'move_voucher_ids': [(4, move_rcs.id)]})
                
        return True
    
    
    @api.multi
    def button_reconcile_move_line(self):
        for line in self:
            move_line_rcs = self.env['account.move.line']
            for move in line.move_voucher_ids:
                for move_line in move.line_id:
                    if move_line.account_id == line.account_id:
                        move_line_rcs |= move_line
            
            for move in line.move_invoice_ids:
                for move_line in move.line_id:
                    if move_line.account_id == line.account_id:
                        move_line_rcs |= move_line
            
            if move_line_rcs:
                context2 = self.env.context.copy()
                context2['active_ids'] = move_line_rcs.ids
                context2['account_bank_statement_line_id'] = line.id
                amlr_rcs = self.env['account.move.line.reconcile'].with_context(context2).create({})
                return {
                            'name': _('Reconciliation'),
                            'view_type': 'form',
                            'view_mode': 'form',
                            'res_model': 'account.move.line.reconcile',
                            'type': 'ir.actions.act_window',
                            'target': 'new',
                            'res_id': amlr_rcs.id,
                            'context': context2,
                            'nodestroy': True,
                            } 
        
        
        return {'type': 'ir.actions.act_window_view_reload'} 
        
        
    @api.multi
    def button_view_account_voucher(self):
        for line in self:
            if line.move_voucher_ids:
                return {'name': _('Account move vouchers'),
                        'view_type': 'form',
                        'view_mode': 'tree,form',
                        'res_model': 'account.move',
                        'type': 'ir.actions.act_window',
                        'target': 'current',
                        'domain': [('id', '=', line.move_voucher_ids.ids)],
                        'nodestroy': True,}    

