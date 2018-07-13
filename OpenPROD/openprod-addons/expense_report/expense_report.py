# -*- coding: utf-8 -*-
from openerp import models, api, fields, _
from openerp.exceptions import except_orm
from openerp.addons.base_openprod.common import get_form_view
import openerp.addons.decimal_precision as dp
from openerp.addons.analytic_distribution.compute_amount import compute_amount


class expense_report(models.Model):
    """ 
        Expense report 
    """
    _name = 'expense.report'
    _description = 'Expense report'
    _inherit = 'workflow.base'

    
    @api.model
    def _payment_get(self):
        return [
                ('employee', _('Employee (to repay)')),
                ('company', _('Company')),
                       ]

    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('waiting', _('Waiting for validation')),
                ('validated', _('Validated')),
                ('payment_requested', _('Payment requested')),
                ('paid', _('Paid')),
                ('cancel', _('Cancel')),
        ]
        
    
    @api.one
    @api.depends('line_ids.total_price', 'tax_line_ids.amount', 'currency_id', 'company_id')
    def _compute_amount(self):
        self.amount_untaxed = sum(line.total_price for line in self.line_ids)
        self.amount_tax = sum(line.amount for line in self.tax_line_ids)
        self.amount_total = self.amount_untaxed + self.amount_tax
        amount_total_company_signed = self.amount_total
        amount_untaxed_signed = self.amount_untaxed
        if self.currency_id and self.currency_id != self.company_id.currency_id:
            amount_total_company_signed = self.currency_id.compute(self.amount_total, self.company_id.currency_id)
            amount_untaxed_signed = self.currency_id.compute(self.amount_untaxed, self.company_id.currency_id)
        
        self.amount_total_company_signed = amount_total_company_signed
        self.amount_total_signed = self.amount_total
        self.amount_untaxed_signed = amount_untaxed_signed
    
    
    @api.model
    def _reinvoicing_state_get(self):
        return [
                ('no_invoicing', _('no reinvoicing')),
                ('to_reinvoice', _('To reinvoice')),
                ]
    
    
    @api.one
    def _company_invoice_id(self):
        invoice_id = False
        invoice_rcs = self.env['account.invoice'].search([('expense_report_id', '=', self.id)], limit=1)
        if invoice_rcs:
            invoice_id = invoice_rcs.id
        
        self.invoice_id = invoice_id
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    #Entête
    name = fields.Char('Description of the expense report', required=True, size=256)
    requested_date = fields.Date(string='Requested date', default=lambda self: fields.Date.today())
    payment = fields.Selection('_payment_get', string='Payment', required=True, default='employee')
    employee_id = fields.Many2one('employee', string='employee', required=False, ondelete='restrict')
    company_id = fields.Many2one('res.company', string='Company', required=True, ondelete='restrict', default=lambda self: self.env.user.company_id)
    account_id = fields.Many2one('account.account', string='Account', required=True, ondelete='restrict')
    state = fields.Selection('_state_get', string='State', default='draft', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, track_visibility='always')
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    journal_id = fields.Many2one('account.journal', string='Journal', required=True)
    journal_payment_id = fields.Many2one('account.journal', string='Payment journal', required=False)
    period_id = fields.Many2one('account.period', string='Period', domain=[('state', '!=', 'done')], copy=False,)
    #Ligne de frais
    #    Ligne
    line_ids = fields.One2many('expense.report.line', 'expense_report_id',  string='Lines', copy=True)
    comment = fields.Text(string='Comment')
    #    Taxes
    tax_line_ids = fields.One2many('expense.report.tax', 'expense_report_id', string='Tax Lines', copy=True)
    #    Total
    amount_untaxed = fields.Monetary(string='Untaxed Amount',
        store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    amount_untaxed_signed = fields.Monetary(string='Untaxed Amount', currency_field='company_currency_id',
        store=True, readonly=True, compute='_compute_amount')
    amount_tax = fields.Monetary(string='Tax',
        store=True, readonly=True, compute='_compute_amount')
    amount_total = fields.Monetary(string='Total',
        store=True, readonly=True, compute='_compute_amount')
    amount_total_signed = fields.Monetary(string='Total', currency_field='currency_id',
        store=True, readonly=True, compute='_compute_amount', help="")
    amount_total_company_signed = fields.Monetary(string='Total', currency_field='company_currency_id',
        store=True, readonly=True, compute='_compute_amount', help="")
    #Autres liens
    #    Historique
    validation_date = fields.Date(string='Validation date', copy=False)
    payment_date = fields.Date(string='Payment date', copy=False)
    reinvoicing_state = fields.Selection('_reinvoicing_state_get', string='Reinvoicing state')
    reinvoicing_date = fields.Date(string='Reinvoicing date', copy=False)
    customer_id = fields.Many2one('res.partner', string='Customer', required=False, ondelete='restrict')
    valid_move_id = fields.Many2one('account.move', string='Account move validation', required=False, ondelete='set null', copy=False)
    pay_move_id = fields.Many2one('account.move', string='Account move payment', required=False, ondelete='set null', copy=False)
    pay_voucher_id = fields.Many2one('account.voucher', string='Payment', required=False, ondelete='set null', copy=False)
    invoice_id = fields.Many2one('account.invoice', compute='_company_invoice_id', string='Invoice', store=False, copy=False)
    
    #===========================================================================
    # onchange
    #===========================================================================
    @api.onchange('company_id')
    def _onchange_company_id(self):
        self.currency_id = self.company_id and self.company_id.currency_id.id or False

    
    @api.onchange('payment', 'employee_id', 'company_id')
    def _onchange_account_id(self):
        if self.payment == 'employee':
            self.account_id = self.employee_id and self.employee_id.account_id and self.employee_id.account_id.id or False
        elif self.payment == 'company':
            self.account_id = self.company_id and self.company_id.partner_id and self.company_id.partner_id.property_account_payable_id and self.company_id.partner_id.property_account_payable_id.id or False
        else:
            self.account_id = False
        
        
    #===========================================================================
    # bouton
    #===========================================================================
    @api.onchange('line_ids')
    def _onchange_invoice_line_ids(self):
        self.function_reset_taxes()
        reinvoicing = False
        for line in self.line_ids:
            if line.reinvoicing:
                reinvoicing = True
                break
        
        if reinvoicing:
            self.reinvoicing_state = 'to_reinvoice'
        else:
            self.reinvoicing_state = 'no_invoicing'
    
    @api.multi
    def button_reset_taxes(self):
        for export_report in self:
            export_report.function_reset_taxes()
        
        return
    
    @api.multi
    def function_reset_taxes(self):
        """
            Bouton qui permet de recalculer les taxes
        """
        taxes_grouped = self.get_taxes_values()
        tax_lines = self.tax_line_ids.browse([])
        for tax in taxes_grouped.values():
            tax_lines += tax_lines.new(tax)
            
        self.tax_line_ids = tax_lines
        return
    
    
    @api.multi
    def get_taxes_values(self):
        tax_grouped = {}
        for line in self.line_ids:
            taxes = line.expense_line_tax_ids.compute_all(line.price_unit, self.currency_id, line.quantity, line.product_id)['taxes']
            for tax in taxes:
                val = {
                    'expense_report_id': self.id,
                    'name': tax['name'],
                    'tax_id': tax['id'],
                    'amount': tax['amount'],
                    'manual': False,
                    'sequence': tax['sequence'],
                    'account_id': line.account_id.id,
                    'base_code_id': tax['base_code_id'],
                    'tax_code_id': tax['tax_code_id']
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
    
    @api.multi
    def compute_expense_totals(self, company_currency, ref, expense_lines):
        """
            Create one move line for the total and possibly adjust the other lines amount
        """
        total = 0
        total_currency = 0
        for line in expense_lines:
            if self.currency_id != company_currency:
                currency = self.currency_id.with_context(date=fields.Date.context_today(self))
                line['currency_id'] = currency.id
                line['amount_currency'] = currency.round(line['price'])
                line['price'] = currency.compute(line['price'], company_currency)
            else:
                line['currency_id'] = False
                line['amount_currency'] = False
                line['price'] = self.currency_id.round(line['price'])
            line['ref'] = ref
            total -= line['price']
            total_currency -= line['amount_currency'] or line['price']
        return total, total_currency, expense_lines
    
    
    @api.multi
    def wkf_cancel(self):
        analytic_line_obj = self.env['account.analytic.line']
        for expense in self:
            if expense.valid_move_id:
                expense.valid_move_id.button_cancel()
                expense.valid_move_id.with_context({'ok_delete': True}).unlink()
            
            if expense.pay_move_id:
                expense.pay_move_id.button_cancel()
                expense.pay_move_id.with_context({'ok_delete': True}).unlink()
            
            if expense.pay_voucher_id:
                expense.pay_voucher_id.signal_workflow('cancel_voucher')
                expense.pay_voucher_id.with_context({'ok_delete': True}).unlink()
            
            if expense.invoice_id:
                expense.invoice_id.signal_workflow('cancel_voucher')
                expense.invoice_id.unlink()
                
            if expense.line_ids:
                analytic_line_rcs = analytic_line_obj.search([('erl_id', 'in', expense.line_ids.ids)])
                if analytic_line_rcs:
                    analytic_line_rcs.unlink()
            
            expense.write({'validation_date': False, 'payment_date': False, 'reinvoicing_date': False})

    
    @api.multi
    def button_create_reinvoice(self):
        invoice_rcs = self.env['account.invoice']
        for expense in self:
            invoice_rcs += expense.create_reinvoice()
            expense.write({'reinvoicing_date': fields.Date.context_today(expense)})
            
        return {'name': _('Invoice'),
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'account.invoice',
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'domain': [('id', 'in', invoice_rcs.ids)],
                    'nodestroy': True,
                    }
    
    
    #===========================================================================
    # Fonctions
    #===========================================================================
    
    @api.multi
    def _get_analytic_lines(self):
        """ 
            Return a list of dict for creating analytic lines for self[0] 
        """
        company_currency = self.company_id.currency_id
        expense_lines = self.env['expense.report.line'].move_line_get(self.id)
        for expense_line in expense_lines:
            if expense_line['account_analytic_id']:
                ref = self.name
                if not self.journal_id.analytic_journal_id:
                    raise except_orm(_('No Analytic Journal!'),
                        _("You have to define an analytic journal on the '%s' journal!") % (self.journal_id.name,))
                
                date = fields.Date.context_today(self)
                currency = self.currency_id.with_context(date=date)
                expense_line['analytic_lines'] = [(0,0, {
                    'name': expense_line['name'],
                    'date': date,
                    'account_id': expense_line['account_analytic_id'],
                    'unit_amount': expense_line['quantity'],
                    'amount': currency.compute(expense_line['price'], company_currency),
                    'product_id': expense_line['product_id'],
                    'product_uom_id': expense_line['uos_id'],
                    'general_account_id': expense_line['account_id'],
                    'journal_id': self.journal_id.analytic_journal_id.id,
                    'ref': ref,
                })]
        return expense_lines
    
    
    @api.model
    def line_get_convert(self, line, date):
        """
            Preparation des lignes d ecritures comptable
        """
        return {
            'date_maturity': line.get('date_maturity', False),
            'name': line['name'][:64],
            'date': date,
            'debit': line['price']>0 and line['price'],
            'credit': line['price']<0 and -line['price'],
            'account_id': line['account_id'],
            'analytic_lines': line.get('analytic_lines', []),
            'amount_currency': line['price']>0 and abs(line.get('amount_currency', False)) or -abs(line.get('amount_currency', False)),
            'currency_id': line.get('currency_id', False),
            'tax_code_id': line.get('tax_code_id', False),
            'tax_amount': line.get('tax_amount', False),
            'ref': line.get('ref', False),
            'quantity': line.get('quantity',1.00),
            'product_id': line.get('product_id', False),
            'product_uom_id': line.get('uos_id', False),
            'analytic_account_id': line.get('account_analytic_id', False),
        }
    
    
    @api.multi
    def action_move_create(self):
        """
            Fonction de création des lignes d'écritures comptables
        """
        ert_obj = self.env['expense.report.tax']
        account_move = self.env['account.move']
        analytic_line_obj = self.env['account.analytic.line']
        for expense in self:
            ctx = dict(self._context, lang=self.env.user.lang)
            date = fields.Date.context_today(expense)
            company_currency = expense.company_currency_id
            # create the analytical lines, one move line per invoice line
            expense_lines = expense._get_analytic_lines()
            # one move line per tax line
            expense_lines += ert_obj.move_line_get(expense.id)
            ref = expense.name
            diff_currency = expense.currency_id != company_currency
            # create one move line for the total and possibly adjust the other lines amount
            total, total_currency, expense_lines = expense.with_context(ctx).compute_expense_totals(company_currency, ref, expense_lines)
            name = expense.name or '/'
            expense_lines.append({
                'type': 'dest',
                'name': name,
                'price': total,
                'account_id': expense.account_id.id,
                'date_maturity': False,
                'amount_currency': diff_currency and total_currency,
                'currency_id': diff_currency and expense.currency_id.id,
                'ref': ref
            })
            line = [(0, 0, self.line_get_convert(l, date)) for l in expense_lines]
            journal = expense.journal_id.with_context(ctx)
            if journal.centralisation:
                raise except_orm(_('User Error!'),
                        _('You cannot create an invoice on a centralized journal. Uncheck the centralized counterpart box in the related journal from the configuration menu.'))

            move_vals = {
                'ref': expense.name,
                'line_id': line,
                'journal_id': journal.id,
                'date': date,
                'narration': expense.comment,
                'company_id': expense.company_id.id,
            }
            ctx['company_id'] = expense.company_id.id
            period = expense.period_id
            if not period:
                period = period.with_context(ctx).find(date)[:1]
            if period:
                move_vals['period_id'] = period.id
                for i in line:
                    i[2]['period_id'] = period.id

            ctx['expense_report'] = expense
            ctx_nolang = ctx.copy()
            ctx_nolang.pop('lang', None)
            move = account_move.with_context(ctx_nolang).create(move_vals)
            # make the invoice point to that move
            vals = {
                'move_id': move.id,
                'period_id': period.id,
                'move_name': move.name,
            }
            expense.with_context(ctx).write(vals)
            # Pass invoice in context in method post: used if you want to get the same
            # account move reference when creating the same invoice after a cancelled one:
            move.post()
            expense.write({'valid_move_id': move.id, 'validation_date': fields.Date.context_today(expense)})
            #Partie analytique distribution
            convert = False
            company_currency = self.company_id.currency_id
            journal_analytic = journal.analytic_journal_id
            if not journal_analytic:
                raise except_orm(_('Warning'), _('Please enter the anaylique journal in the journal you have chosen (%s)!')%(journal.name))
                
            if self.currency_id != company_currency:
                convert = True
                from_currency = self.currency_id
                context2 = {'date': date}
                
            for line in expense.line_ids:
                product_id = line.product_id.id
                uoi_qty = line.quantity
                uom_id = line.uom_id.id
                price_unit = line.price_unit
                if line.pad_id:
                    for distribution_line in line.pad_id.distribution_ids:
                        total = line._compute_total_analytic_distribution(distribution_line)
                        amount = convert and from_currency.with_context(context2).compute(total, company_currency) or total
                        vals = {
                                'name': line.product_id.name,
                                'ref': name,
                                'account_id': distribution_line.account_id.id,
                                'user_id': self.env.user.id,
                                'amount': amount,
                                'amount_invoice': line.total_price,
                                'product_id': product_id,
                                'unit_amount': uoi_qty,
                                'product_uom_id': uom_id,
                                'general_account_id': expense.account_id.id,
                                'erl_id': line.id,
                                'price_unit': price_unit,
                                'journal_id': journal_analytic.id
                                }
                        analytic_line_obj.create(vals)

        return True
    
    
    def action_generate_payment(self):
        """
            Fonction permettant de créer le paiement
        """
        if not self.line_ids:
            raise except_orm(_('Warning'), _('There are no lines on your expense report!'))
            
        #On récupère toutes les valeurs du paiement
        journal_obj = self.env['account.journal']
        payment_rate = 1
        today = fields.Date.today()
        period_rs = self.period_id or self.env['account.period'].find(today)
        currency_rs = self.currency_id or False
        #On recherche le journal par défaut du paiement. S'il n'y en a pas on prend le premier trouvé
        journal_rs = self.journal_payment_id or journal_obj.search([('is_default', '=', True), ('type', 'in', ['cash', 'bank'])], limit=1)
        if not journal_rs:
            journal_rs = journal_obj.search([('type', 'in', ['cash', 'bank'])], limit=1)
        
        payment_rate_currency_rs = journal_rs and journal_rs.currency or currency_rs
        if journal_rs and period_rs and currency_rs:
            currency_rate = currency_rs.rate
            if currency_rate != 0:
                payment_rate = payment_rate_currency_rs.rate / currency_rate
            
            account_partner_id = self.account_id.id
            # Preparation paiement
            vals = {
                    'account_partner_id': account_partner_id,
                    'amount': self.amount_total,
                    'journal_id': journal_rs.id,
                    'date': today,
                    'period_id': period_rs.id,
                    'payment_rate_currency_id': payment_rate_currency_rs.id,
                    'company_id': self.company_id.id,
                    'payment_rate': payment_rate,
                    'payment_option': 'without_writeoff',
                    'currency_id': currency_rs.id,
                    'account_id': journal_rs.default_debit_account_id.id,
                    'expense_report_id': self.id,
                    'type': 'payment'}
            
            if self.valid_move_id:
                aml_rcs = self.env['account.move.line'].search([('move_id', '=', self.valid_move_id.id), ('account_id', '=', self.account_id.id), ('credit', '!=', 0.0)], limit=1)
                if aml_rcs:
                    line_dr_ids = [(0, 0, {'name': aml_rcs.name,
                                           'account_id': aml_rcs.account_id.id,
                                           'amount': aml_rcs.credit,
                                           'reconcile': True,
                                           'type': 'dr',
                                           'move_line_id':aml_rcs.id,})]
                    vals['line_dr_ids'] = line_dr_ids
            
            # Creation paiement
            voucher_rcs = self.env['account.voucher'].create(vals)
#             # Validation paiement
#             voucher_rcs.signal_workflow('proforma_voucher')

#             move_rcs = self.env['account.move'].search([('voucher_id', '=', voucher_rcs.id)], limit=1)
#             self.write({'pay_move_id': move_rcs.id, 'payment_date': today, 'pay_voucher_id': voucher_rcs.id})
            self.write({'payment_date': today, 'pay_voucher_id': voucher_rcs.id})
        return True
        
    
    def create_reinvoice(self):
        invoice_obj = self.env['account.invoice']
        invoice_line_obj = self.env['account.invoice.line']
        if not self.line_ids:
            raise except_orm(_('Warning'), _('There are no lines on your expense report!'))
        
        if not self.customer_id:
            raise except_orm(_('Warning'), _('There is no customer on your expense report!'))
        
        invoice_rcs = invoice_obj.create_invoice(self.customer_id.id, self.customer_id.address_id.id, 'out_invoice', other_data={'expense_report_id': self.id})
        for line in self.line_ids:
            invoice_line_tax_ids = line.expense_line_tax_ids and line.expense_line_tax_ids.ids or False
            if invoice_line_tax_ids:
                invoice_line_tax_ids = [(6, 0, invoice_line_tax_ids)]
                
            invoice_line_rcs = invoice_line_obj.create_invoice_line(invoice_rcs.id, line.product_id.id, from_invoice=True, 
                                                                    other_data={'uom_id': line.uom_id.id,
                                                                                'sec_uom_id': line.uom_id.id,
                                                                                'uoi_id': line.uom_id.id,
                                                                                'uom_qty': line.quantity,
                                                                                'sec_uom_qty': line.quantity,
                                                                                'quantity': line.quantity,
                                                                                'invoice_line_tax_ids': invoice_line_tax_ids})    

            if self.currency_id and invoice_rcs.currency_id.id != self.currency_id.id:
                context2 = {}
                context2.update(self.env.context)
                if invoice_rcs.date_invoice:
                    context2['date'] = invoice_rcs.date_invoice
                    
                price = invoice_rcs.currency_id.with_context(context2).compute(line.price_unit, self.currency_id)
            else:
                price = line.price_unit
            
            invoice_line_rcs.write({'price_unit': price})
        
        invoice_rcs.button_reset_taxes()
        return invoice_rcs
    
    
    @api.multi
    def unlink(self):
        for exp_report in self:
            if exp_report.state not in ('draft', 'cancel'):
                raise except_orm(_('Error!'), _("The expense report can not be deleted if it is draft or canceled (%s)!") % (exp_report.name))
            
        return super(expense_report, self).unlink()
    
    
    
class expense_report_line(models.Model):
    """ 
        Expense report line
    """
    _name = 'expense.report.line'
    _description = 'Expense report line'
    _rec_name = 'product_id'
    
    
    @api.one
    @api.depends('price_unit', 'expense_line_tax_ids', 'quantity', 'product_id', 'currency_id')
    def _compute_total_price(self):
        price = self.price_unit
        taxes = self.expense_line_tax_ids.compute_all(price, self.currency_id, self.quantity, product=self.product_id)
        self.total_price = taxes['total_excluded']

    
    @api.one
    @api.depends('expense_report_id', 'expense_report_id.currency_id')
    def _compute_currency_id(self):
        self.currency_id = self.expense_report_id.currency_id and self.expense_report_id.currency_id.id or False
        
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    expense_report_id = fields.Many2one('expense.report', string='Expense report', required=False, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='restrict')
    price_unit = fields.Float(string='Unit price', default=0.0, required=True)
    quantity = fields.Float(string='Quantity', default=0.0, required=True)
    uom_id = fields.Many2one('product.uom', string='UoM', required=True, ondelete='restrict')
    expense_line_tax_ids = fields.Many2many('account.tax', 'expense_report_line_tax_rel', 'expense_report_line_id', 'tax_id', string='Taxes', domain=[('parent_id', '=', False)])
    total_price = fields.Monetary(string='Amount', compute='_compute_total_price', store=True)
    remark = fields.Char(string='Remark', size=256, required=False)
    reinvoicing = fields.Float(string='% reinvoicing', default=100.0, required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', compute='_compute_currency_id')
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic account')
    pad_id = fields.Many2one('product.analytic.distribution', string='Analytic distribution', required=False, ondelete='restrict')
    account_id = fields.Many2one('account.account', string='Account', required=True)

    
    #===========================================================================
    # onchange
    #===========================================================================
    @api.onchange('product_id')
    def product_id_change(self):
        product = self.product_id
        self.account_id = product.property_account_expense_id and product.property_account_expense_id.id or product.categ_id.property_account_expense_categ_id and product.categ_id.property_account_expense_categ_id.id or False
        self.expense_line_tax_ids = product.purchase_taxes_ids and product.purchase_taxes_ids.ids or self.account_id.tax_ids and self.account_id.tax_ids.ids or False
        self.uom_id = product.uom_id.id
        self.pad_id = product.purchase_pad_id and product.purchase_pad_id.id or False
    
    
    #===========================================================================
    # fonction
    #===========================================================================
    @api.model
    def move_line_get(self, expense_report_id):
        expense_report= self.env['expense.report'].browse(expense_report_id)
        date = fields.Date.context_today(expense_report)
        currency = expense_report.currency_id.with_context(date=date)
        company_currency = expense_report.company_id.currency_id
        res = []
        for line in expense_report.line_ids:
            mres = self.move_line_get_item(line)
            mres['invl_id'] = line.id
            res.append(mres)
            tax_code_found = False
            taxes = line.expense_line_tax_ids.compute_all(
                line.price_unit,
                line.currency_id, line.quantity, line.product_id)['taxes']
            for tax in taxes:
                tax_code_id = tax['base_code_id']
                tax_amount = tax['price_unit'] * line.quantity * tax['base_sign']

                if tax_code_found:
                    if not tax_code_id:
                        continue
                    res.append(dict(mres))
                    res[-1]['price'] = 0.0
                    res[-1]['account_analytic_id'] = False
                elif not tax_code_id:
                    continue
                tax_code_found = True

                res[-1]['tax_code_id'] = tax_code_id
                res[-1]['tax_amount'] = currency.compute(tax_amount, company_currency)

        return res

    
    @api.model
    def move_line_get_item(self, line):
        name = line.product_id.name
        return {
            'type': 'src',
            'name': name.split('\n')[0][:64],
            'price_unit': line.price_unit,
            'quantity': line.quantity,
            'price': line.total_price,
            'account_id': line.account_id.id,
            'product_id': line.product_id.id,
            'uos_id': line.uom_id.id,
            'account_analytic_id': line.account_analytic_id.id,
            'taxes': line.expense_line_tax_ids,
        }
        
    
    def _compute_total_analytic_distribution(self, distribution_line):
        """
            Fonction permettant de calculer le montant de la ligne de distribution analytique en 
            fonction de la ligne de la note frais
        """
        total_price = self.total_price
        if distribution_line.type == 'garbage':
            total_amount = sum([compute_amount(l.type, l.value, total_price) 
                                for l in self.pad_id.distribution_ids if l.type != 'garbage'])
            total_price = total_price - total_amount
        else:
            total_price = compute_amount(distribution_line.type, distribution_line.value, total_price)
        
        return total_price
    


class expense_report_tax(models.Model):
    """ 
        Expense report tax
    """
    _name = "expense.report.tax"
    _description = "Expense report tax"
    _order = 'sequence'

    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    expense_report_id = fields.Many2one('expense.report', string='Expense report', required=False, ondelete='cascade')
    name = fields.Char(string='Tax Description', required=True)
    tax_id = fields.Many2one('account.tax', string='Tax', ondelete='restrict')
    account_id = fields.Many2one('account.account', string='Tax Account', required=True)
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic account')
    amount = fields.Monetary()
    manual = fields.Boolean(default=True)
    sequence = fields.Integer(help="Gives the sequence order when displaying a list of expense report tax.")
    company_id = fields.Many2one('res.company', string='Company', related='expense_report_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', related='expense_report_id.currency_id', store=True, readonly=True)
    base_code_id = fields.Many2one('account.tax.code', string='Base Code', help="The account basis of the tax declaration.")
    base_amount = fields.Float(string='Base Code Amount', digits=dp.get_precision('Account'), default=0.0)
    tax_code_id = fields.Many2one('account.tax.code', string='Tax Code', help="The tax basis of the tax declaration.")
    tax_amount = fields.Float(string='Tax Code Amount', digits=dp.get_precision('Account'), default=0.0)
    tax_on_payment = fields.Boolean(default=False)
    account_payment_id = fields.Many2one('account.account', 'Invoice tax account (On payment)', help='')

    @api.multi
    def amount_change(self, amount, currency_id=False, company_id=False, date=False):
        company = self.env['res.company'].browse(company_id)
        if currency_id and company.currency_id:
            currency = self.env['res.currency'].browse(currency_id)
            currency = currency.with_context(date=date or fields.Date.context_today(self))
            amount = currency.compute(amount, company.currency_id, round=False)
        tax_sign = (self.tax_amount / self.amount) if self.amount else 1
        return {'value': {'tax_amount': amount * tax_sign}}


    @api.model
    def move_line_get(self, expense_report_id):
        """
            Preparation des lignes d'écritures comptable pour chaque lignes de TVA
        """
        res = []
        self._cr.execute(
            'SELECT * FROM expense_report_tax WHERE expense_report_id = %s',
            (expense_report_id,)
        )
        for row in self._cr.dictfetchall():
            if not (row['amount'] or row['tax_code_id'] or row['tax_amount']):
                continue
            if row['account_analytic_id'] == None:
                row['account_analytic_id'] = False
            
            if row['tax_code_id'] == None:
                row['tax_code_id'] = False

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
        return res


    
    