# -*- coding: utf-8 -*-\n

from openerp import models, fields, api
from openerp.exceptions import UserError,except_orm
from openerp.tools.translate import _

AGENT_TYPE_PARTNER = 'partner'
AGENT_TYPE_EMPLOYEE = 'employee'
AGENT_TYPES = (
    (AGENT_TYPE_EMPLOYEE, _('Employee')),
    (AGENT_TYPE_PARTNER, _('Partner'))
)
AGENT_STATE_DRAFT = 'draft'
AGENT_STATE_ACTIVE = 'active'
AGENT_STATE_INACTIVE = 'inactive'
AGENT_STATES = (
    (AGENT_STATE_DRAFT, _('Draft')),
    (AGENT_STATE_ACTIVE, _('Active')),
    (AGENT_STATE_INACTIVE, _('Inactive')),
)
BILLING_FREQUENCY_MONTH = '1'
BILLING_FREQUENCY_TRIMESTER = '3'
BILLING_FREQUENCY_YEAR = '12'
BILLING_FREQUENCIES = (
    (BILLING_FREQUENCY_MONTH, _('Month')),
    (BILLING_FREQUENCY_TRIMESTER, _('Trimester')),
    (BILLING_FREQUENCY_YEAR, _('Year')),
)


class commission_agent(models.Model):

    _name = 'commission.agent'


    @api.model
    def create(self, kwargs):
        if not kwargs.get('%s_id' % kwargs.get('type_')):
            raise UserError('You must assign a user to the agent')
        return super(commission_agent, self).create(kwargs)
    
    
    @api.one
    @api.depends('type_', 'partner_id', 'partner_id.currency_id')
    def _compute_currency(self):
        if self.type_ == 'partner':
            currency_id = self.partner_id and self.partner_id.currency_id and self.partner_id.currency_id.id or False
        else:
            currency_id = self.env.user.company_id.currency_id and self.env.user.company_id.currency_id.id or False
            
        self.currency_id = currency_id
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    billing_frequency = fields.Selection(
        selection=BILLING_FREQUENCIES,
        required=True
    )
    default_rule_set_id = fields.Many2one(
        comodel_name='commission.rule.set',
        string='Commission rate'
    )
    employee_id = fields.Many2one(
        comodel_name='employee',
        string='Employee'
    )
    name = fields.Char(
        size=255, required=True
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Partner'
    )
    type_ = fields.Selection(
        selection=AGENT_TYPES,
        required=True,
        string='Type'
    )
    rate_ids = fields.One2many(
        comodel_name='commission.rate',
        inverse_name='agent_id'
    )
    state = fields.Selection(
        selection=AGENT_STATES,
        required=True,
        default= 'draft'
    )
    currency_id = fields.Many2one('res.currency', string='Currency', compute='_compute_currency', store=True)
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='restrict')
    
    
    #===========================================================================
    # Boutons
    #===========================================================================
    
    @api.multi
    def wkf_draft(self):
        self.write({'state': 'draft'})
    
    
    @api.multi
    def wkf_active(self):
        self.write({'state': 'active'})
    
    
    @api.multi
    def wkf_inactive(self):
        self.write({'state': 'inactive'})



class commission_rate(models.Model):
    _name = 'commission.rate'
    _rec_name = 'commission_rule_set_id'


    @api.onchange('agent_id')
    def on_change_agent_id(self):
        if not (self.commission_rule_set_id or self.agent_id.default_rule_set_id):
            return

        self.commission_rule_set_id = self.agent_id.default_rule_set_id
        
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    agent_id = fields.Many2one(
        comodel_name='commission.agent'
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner'
    )
    commission_rule_set_id = fields.Many2one(
        comodel_name='commission.rule.set'
    )
    related_default_rule_set_id = fields.Many2one(
        related='agent_id.default_rule_set_id'
    )



class commission_sale(models.Model):
    _name = 'commission.sale'


    @api.onchange('agent_id')
    def on_change_agent_id(self):
        if not (self.commission_rule_set_id or self.agent_id.default_rule_set_id):
            return

        self.commission_rule_set_id = self.agent_id.default_rule_set_id
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    sale_order_id = fields.Many2one(
        comodel_name='sale.order'
    )
    agent_id = fields.Many2one(
        comodel_name='commission.agent'
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner'
    )
    commission_rule_set_id = fields.Many2one(
        comodel_name='commission.rule.set'
    )
    name_related = fields.Char(
        related='commission_rule_set_id.name',
        store=True
    )
    rate_id = fields.Many2one(
        comodel_name='commission.rate'
    )



class commission_invoice_line(models.Model):
    _name = 'commission.invoice.line'


    @api.onchange('agent_id')
    def on_change_agent_id(self):
        if not (self.commission_rule_set_id or self.agent_id.default_rule_set_id):
            return

        self.commission_rule_set_id = self.agent_id.default_rule_set_id


    @api.one
    @api.depends('commission_rule_set_id', 'account_invoice_line_id')
    def _compute_rule(self):
        self.rule_id = None
        matching_rule_ids = list()
        for rule_id in self.commission_rule_set_id.rule_ids:
            if rule_id.min_total <= self.account_invoice_line_id.price_subtotal:
                matching_rule_ids.append(rule_id)

        if len(matching_rule_ids):
            self.rule_id = matching_rule_ids[-1]
    
    @api.one
    @api.depends('account_invoice_line_id', 'account_invoice_line_id.invoice_id')
    def _compute_invoice(self):
        self.invoice_id = self.account_invoice_line_id and self.account_invoice_line_id.invoice_id.id or False
        
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    sale_order_id = fields.Many2one(
        comodel_name='sale.order'
    )
    agent_id = fields.Many2one(
        comodel_name='commission.agent'
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner'
    )
    commission_rule_set_id = fields.Many2one(
        comodel_name='commission.rule.set'
    )
    name_related = fields.Char(
        related='commission_rule_set_id.name',
        store=True
    )
    rate_id = fields.Many2one(
        comodel_name='commission.rate'
    )
    account_invoice_line_id = fields.Many2one(
        comodel_name='account.invoice.line'
    )
    payment_id = fields.Many2one(
        comodel_name='commission.payment',
        ondelete='set null',
        string='Payment'
    )
    invoice_currency_id = fields.Many2one(
        'res.currency', related='invoice_id.currency_id',
        readonly=True
    )
    total = fields.Monetary(
        currency_field='invoice_currency_id'
    )
    commission_sale_id = fields.Many2one(
        comodel_name='commission.sale'
    )
    rule_id = fields.Many2one(
        comodel_name='commission.rule',
        compute='_compute_rule', store=True
    )
    invoice_id = fields.Many2one('account.invoice', string='Invoice', compute='_compute_invoice', store=True)
    
    #===========================================================================
    # BUTTON
    #===========================================================================
    @api.multi
    def _function_compute_total(self):
        for cil in self:
            total = 0.0
            if cil.account_invoice_line_id and cil.rule_id:
                if cil.rule_id.fix_part:
                    total += float(cil.rule_id.fix_part)
        
                if cil.rule_id.percentage:
                    total += (cil.account_invoice_line_id.price_subtotal * float(cil.rule_id.percentage) / 100)

            cil.write({'total': total})



class commission_rule_set(models.Model):
    _name = 'commission.rule.set'


    name = fields.Char(
        size=255,
        required=True
    )
    rule_ids = fields.One2many(
        comodel_name='commission.rule',
        inverse_name='commission_rule_set_id',
        string='Rules'
    )
    rate_ids = fields.One2many(
        comodel_name='commission.rate',
        inverse_name='commission_rule_set_id',
        string='Rates'
    )



class commission_rule(models.Model):
    _name = 'commission.rule'
    _order = 'min_total'

    @api.model
    def create(self, kwargs):
        if not ('percentage' or 'fix_part') in kwargs:
            raise UserError(_('You must set at least a fix or a percentage'))

        return super(commission_rule, self).create(kwargs)

    min_total = fields.Integer(
        required=True
    )
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    percentage = fields.Integer()
    fix_part = fields.Integer()
    commission_rule_set_id = fields.Many2one(
        comodel_name='commission.rule.set'
    )



class commission_payment(models.Model):
    _name = 'commission.payment'


    @api.one
    @api.depends('line_ids', 'line_ids.total')
    def _compute_totals(self):
        total_amount_commission = 0
        for line in self.line_ids:
            total_amount_commission += line.total
        
        self.total_amount_commission = total_amount_commission


    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('validate', _('Validate')),
                ('done', _('Done')),
                ('cancel', _('Cancel')),
                       ]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    agent_id = fields.Many2one('commission.agent', string='Agent', required=True, ondelete='restrict')
    end_date = fields.Date('End date')
    name = fields.Char(
        size=255, required=True,
    )
    start_date = fields.Date('Start date')
    total_amount_commission = fields.Float(
        compute='_compute_totals', store=True
    )
    total_to_pay = fields.Float(string='Total to pay')
    type = fields.Selection(selection=AGENT_TYPES, string='Type', related='agent_id.type_' )
    line_ids = fields.One2many('commission.payment.line', 'commission_payment_id',  string='Line')
    payment_id = fields.Many2one('account.voucher', string='Payment', required=False, ondelete='set null')
    invoice_id = fields.Many2one('account.invoice', string='Invoice', required=False, ondelete='set null')
    state = fields.Selection('_state_get', string='State', default='draft')
    currency_id = fields.Many2one('res.currency', string='Currency', related='agent_id.currency_id')
    journal_payment_id = fields.Many2one('account.journal', string='Journal', required=True)
    period_id = fields.Many2one('account.period', string='Period', domain=[('state', '!=', 'done')], copy=False,)
    
    
    #===========================================================================
    # Boutons
    #===========================================================================
    @api.multi
    def search_commission_payment_line(self):
        """
            Fonction qui permet de rechercher toutes les lignes de factures qui ont au moins une commission et qui n'ont pas encore de règlement durant la période donnée
        """
        cpl_obj = self.env['commission.payment.line']
        invoice_obj = self.env['account.invoice']
        cil_obj = self.env['commission.invoice.line']
        for payment in self:
            cil_rcs = cil_obj.search([('agent_id', '=', payment.agent_id.id), ('payment_id', '=', False)])
            vals_invoice_cil = {}
            if cil_rcs:
                invoice_rcs = self.env['account.invoice']
                for cil in cil_rcs:
                    invoice_rcs |= cil.account_invoice_line_id.invoice_id
                    if cil.account_invoice_line_id.invoice_id in vals_invoice_cil:
                        vals_invoice_cil[cil.account_invoice_line_id.invoice_id] += cil
                    else:
                        vals_invoice_cil[cil.account_invoice_line_id.invoice_id] = cil
                
                if invoice_rcs:
                    vals_inv_search = [('id', 'in', invoice_rcs.ids), ('state', 'not in', ('draft', 'cancel')), ('type', 'in', ('out_invoice', 'out_refund'))]
                    if payment.start_date:
                        vals_inv_search.append(('date_invoice', '>=', payment.start_date))
                    
                    if payment.end_date:
                        vals_inv_search.append(('date_invoice', '<=', payment.end_date))
                    
                    invoice_insert_rcs = invoice_obj.search(vals_inv_search)
                    
                    cil_write_payment = self.env['commission.invoice.line']
                    for invoice_insert in invoice_insert_rcs:
                        if invoice_insert in vals_invoice_cil:
                            for cil_insert in vals_invoice_cil[invoice_insert]:
                                if cil_insert.account_invoice_line_id.invoice_id.type == 'out_invoice': 
                                    total_currency_invoice = cil_insert.total
                                else:
                                    total_currency_invoice = cil_insert.total * -1
                                
                                total = cil_insert.invoice_currency_id.compute(total_currency_invoice, payment.currency_id)
                                invoice_currency_id = cil_insert.invoice_currency_id.id
                                payment_currency_id = payment.currency_id.id
                                cpl_obj.create({'commission_payment_id': payment.id,
                                                'commission_invoice_line_id': cil_insert.id,
                                                'total_currency_invoice': total_currency_invoice,
                                                'total': total,
                                                'invoice_currency_id': invoice_currency_id,
                                                'payment_currency_id': payment_currency_id,})
                                cil_write_payment |= cil_insert
                    cil_write_payment.write({'payment_id': payment.id})
            
            payment.write({'total_to_pay': payment.total_amount_commission})
            
        return True    
    
    
    @api.multi
    def delete_all_payment_line(self):
        """
            Fonction qui supprime les lignes de commissions
        """
        for payment in self:
            payment.line_ids.delete_payment_line()
            
        return {'type': 'ir.actions.act_window_view_reload'}   
                 
                                
    @api.multi
    def generate_invoice(self):
        invoice_obj = self.env['account.invoice']
        invoice_line_obj = self.env['account.invoice.line']
        journal_purchase_rcs = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)
        for payment in self:
            name = _('Commission payment %s')%(payment.name)
            other_data={'origin': name}
            if journal_purchase_rcs:
                other_data['journal_id'] = journal_purchase_rcs.id
                
            invoice_rcs = invoice_obj.create_invoice(payment.agent_id.partner_id.id, payment.agent_id.partner_id.address_id.id, 'in_invoice', other_data=other_data)
            product = payment.agent_id.product_id
            invoice_line_rcs = invoice_line_obj.create_invoice_line(invoice_rcs.id, product.id, from_invoice=True, 
                                                                    other_data={'uom_id': product.uom_id.id,
                                                                                'sec_uom_id': product.uom_id.id,
                                                                                'uoi_id': product.uom_id.id,
                                                                                'uom_qty': 1,
                                                                                'sec_uom_qty': 1,
                                                                                'quantity': 1,})    

            invoice_line_rcs.write({'price_unit': payment.total_to_pay})
            payment.write({'invoice_id': invoice_rcs.id})
            payment.wkf_validate()
        
        return {'type': 'ir.actions.act_window_view_reload'}
    
    
    @api.multi
    def generate_payment(self):
        for payment in self:
            payment.action_generate_payment()

        return {'type': 'ir.actions.act_window_view_reload'}
    
    
    @api.multi
    def done_invoice(self):
        voucher_obj = self.env['account.voucher']
        for payment in self:
            if payment.invoice_id.state == 'draft':
                payment.invoice_id.signal_workflow('invoice_open')
            
            if payment.invoice_id.state == 'open':
                #Suppression du paiement s'il existe déjà
                if payment.payment_id:
                    if payment.payment_id.state != 'cancel':
                        payment.payment_id.signal_workflow('cancel_voucher')
                    payment.payment_id.unlink()
                    
                inv = payment.invoice_id
                account_partner_id = inv.partner_id.property_account_payable_id and inv.partner_id.property_account_payable_id.id or False
                ctx = self.env.context.copy()
                ctx.update( {
                        'payment_expected_currency': inv.currency_id.id,
                        'default_partner_id': inv.partner_id.id,
                        'default_account_partner_id': account_partner_id,
                        'default_amount': inv.type in ('out_refund', 'in_refund') and -inv.residual or inv.residual,
                        'default_reference': inv.name,
                        'close_after_process': True,
                        'invoice_type': inv.type,
                        'invoice_id': inv.id,
                        'default_type': inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment',
                        'type': inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment'
                    })
                
                currency_id = inv.currency_id.id
                vals = {'partner_id': inv.partner_id.id,
                        'account_partner_id': account_partner_id,
                        'amount': inv.type in ('out_refund', 'in_refund') and -inv.residual or inv.residual,
                        'reference': inv.name,
                        'journal_id': payment.journal_payment_id.id,
                        'account_id': payment.journal_payment_id.default_credit_account_id.id,
                        'currency_id': currency_id}
                
                today = fields.Date.today()
                vals.update(voucher_obj.with_context(ctx).onchange_partner_id(inv.partner_id.id, payment.journal_payment_id.id, vals['amount'], currency_id, 'payment', today)['value'])
                rate = inv.currency_id.rate
                vals.update(voucher_obj.with_context(ctx).onchange_amount(vals['amount'], rate, inv.partner_id.id, payment.journal_payment_id.id, currency_id, 'payment', today, 
                                                                          inv.currency_id.id, self.env.user.company_id.id)['value'])
                if payment.period_id:
                    vals['period_id'] =  payment.period_id.id
                
                line_dr_ids = []
                if 'line_dr_ids' in vals:
                    for line_dr in vals['line_dr_ids']:
                        line_dr_ids.append((0, 0, line_dr))
                
                vals['line_dr_ids'] = line_dr_ids    
                
                line_cr_ids = []
                if 'line_cr_ids' in vals:
                    for line_cr in vals['line_cr_ids']:
                        line_cr_ids.append((0, 0, line_cr))
                          
                vals['line_cr_ids'] = line_cr_ids
                voucher_rcs = voucher_obj.with_context(ctx).create(vals)
                payment.write({'payment_id': voucher_rcs.id})
                voucher_rcs.button_proforma_voucher()
    
        return {'type': 'ir.actions.act_window_view_reload'}
    
    
    @api.multi
    def validate_payment(self):
        for payment in self:
            if payment.payment_id.state == 'draft':
                payment.payment_id.signal_workflow('proforma_voucher')
            elif payment.payment_id.state == 'cancel':
                payment.payment_id.action_cancel_draft()
                payment.payment_id.signal_workflow('proforma_voucher')
            elif not payment.payment_id:
                payment.generate_payment()
                payment.payment_id.signal_workflow('proforma_voucher')
            
        return {'type': 'ir.actions.act_window_view_reload'}
    
    
    @api.multi
    def wkf_draft(self):
        self.write({'state': 'draft'})
    
    
    @api.multi
    def wkf_validate(self):
        self.write({'state': 'validate'})
    
    
    @api.multi
    def wkf_done(self):
        self.write({'state': 'done'})
    
    
    @api.multi
    def wkf_cancel(self):
        for payment in self:
            if payment.type == 'partner':
                payment.payment_id.signal_workflow('cancel_voucher')
                payment.payment_id.unlink()
                payment.invoice_id.signal_workflow('invoice_cancel')
                payment.write({'invoice_id': False})
            else:
                payment.payment_id.signal_workflow('cancel_voucher')
                payment.payment_id.unlink()
            
            
        self.delete_all_payment_line()
        self.write({'state': 'cancel'})
    
    
    def action_generate_payment(self):
        """
            Fonction permettant de créer le paiement
        """
        if not self.line_ids:
            raise except_orm(_('Warning'), _('There are no lines on your commission payment!'))
            
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
            
            account_partner_id = self.agent_id.employee_id and self.agent_id.employee_id.account_id.id or False
            if not account_partner_id:
                raise except_orm(_('Warning'), _('The employee of that agent does not have an account!'))
                 
            # Preparation paiement
            vals = {
                    'account_partner_id': account_partner_id,
                    'amount': self.total_to_pay,
                    'journal_id': journal_rs.id,
                    'date': today,
                    'period_id': period_rs.id,
                    'payment_rate_currency_id': payment_rate_currency_rs.id,
                    'company_id': self.env.user.company_id.id,
                    'payment_rate': payment_rate,
                    'payment_option': 'without_writeoff',
                    'currency_id': currency_rs.id,
                    'account_id': journal_rs.default_debit_account_id.id,
                    'type': 'payment'}
            
            # Creation paiement
            voucher_rcs = self.env['account.voucher'].create(vals)
            self.write({'payment_id': voucher_rcs.id})
            self.wkf_validate()
            
        return True



class commission_payment_line(models.Model):
    """ 
        Commission payment line 
    """
    _name = 'commission.payment.line'
    _description = 'Commission payment'
    _rec_name='agent_id'
    
    
    
    @api.one
    @api.depends('commission_invoice_line_id', 'commission_invoice_line_id.invoice_id')
    def _compute_invoice(self):
        self.invoice_id = self.commission_invoice_line_id and self.commission_invoice_line_id.invoice_id.id or False
        

    #===========================================================================
    # COLUMNS
    #===========================================================================
    commission_payment_id = fields.Many2one('commission.payment', string='Commission payment', required=False, ondelete='cascade')
    commission_invoice_line_id = fields.Many2one('commission.invoice.line', string='Commission invoice line', required=True, ondelete='restrict')
    agent_id = fields.Many2one('commission.agent', string='Agent', related='commission_invoice_line_id.agent_id')
    commission_rule_set_id = fields.Many2one('commission.rule.set', string='Commission', related='commission_invoice_line_id.commission_rule_set_id')
    total_currency_invoice = fields.Monetary(string='Amount with invoice currency', currency_field='invoice_currency_id')
    invoice_currency_id = fields.Many2one('res.currency', string='Currency of the invoice')
    total = fields.Monetary(string='Amount', currency_field='payment_currency_id', required=True)
    payment_currency_id = fields.Many2one('res.currency', string='Currency of the payment')
    invoice_id = fields.Many2one('account.invoice', string='Invoice', compute='_compute_invoice', store=True)
    
    
    #===========================================================================
    # Boutons
    #===========================================================================
    @api.multi
    def delete_payment_line(self):
        commission_invoice_line_rcs = self.env['commission.invoice.line']
        for line in self:
            commission_invoice_line_rcs += line.commission_invoice_line_id
        
        commission_invoice_line_rcs.write({'payment_id': False})
        self.unlink()
        return {'type': 'ir.actions.act_window_view_reload'}
        
        
        
        
        
        