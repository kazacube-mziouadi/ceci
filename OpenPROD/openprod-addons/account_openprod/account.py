# -*- coding: utf-8 -*-
from openerp.tools.float_utils import float_round as round
from openerp.exceptions import AccessError, UserError, ValidationError, except_orm
from openerp.addons.base_openprod.common import get_form_view
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp import api, fields, models, _
from openerp import SUPERUSER_ID
import time
import openerp.addons.decimal_precision as dp

import logging
_logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# Account generation from template wizards
# ---------------------------------------------------------

class WizardMultiChartsAccounts(models.TransientModel):
    _inherit = 'wizard.multi.charts.accounts'
    
    def generate_properties(self, cr, uid, chart_template_id, acc_template_ref, company_id, context=None):
        """
        This method used for creating properties.

        :param chart_template_id: id of the current chart template for which we need to create properties
        :param acc_template_ref: Mapping between ids of account templates and real accounts created from them
        :param company_id: company_id selected from wizard.multi.charts.accounts.
        :returns: True
        """
        property_obj = self.pool.get('ir.property')
        field_obj = self.pool.get('ir.model.fields')
        todo_list = [
            ('property_account_receivable_id','res.partner','account.account'),
            ('property_account_payable_id','res.partner','account.account'),
            ('property_account_expense_categ_id','product.category','account.account'),
            ('property_account_income_categ_id','product.category','account.account'),
            ('property_account_expense','product.product','account.account'),
            ('property_account_income','product.product','account.account'),
        ]
        template = self.pool.get('account.chart.template').browse(cr, uid, chart_template_id, context=context)
        for record in todo_list:
            account = getattr(template, record[0])
            value = account and 'account.account,' + str(acc_template_ref[account.id]) or False
            if value:
                field = field_obj.search(cr, uid, [('name', '=', record[0]),('model', '=', record[1]),('relation', '=', record[2])], context=context)
                vals = {
                    'name': record[0],
                    'company_id': company_id,
                    'fields_id': field[0],
                    'value': value,
                }
                property_ids = property_obj.search(cr, uid, [('name','=', record[0]),('company_id', '=', company_id)], context=context)
                if property_ids:
                    #the property exist: modify it
                    property_obj.write(cr, uid, property_ids, vals, context=context)
                else:
                    #create the property
                    property_obj.create(cr, uid, vals, context=context)
        return True
    

    def execute(self, cr, uid, ids, context=None):
        '''
        This function is called at the confirmation of the wizard to generate the COA from the templates. It will read
        all the provided information to create the accounts, the banks, the journals, the taxes, the tax codes, the
        accounting properties... accordingly for the chosen company.
        '''
        if uid != SUPERUSER_ID and not self.pool['res.users'].has_group(cr, uid, 'base.group_erp_manager'):
            raise AccessError(_("Only administrators can change the settings"))
        
        obj_data = self.pool.get('ir.model.data')
        ir_values_obj = self.pool.get('ir.values')
        obj_wizard = self.browse(cr, uid, ids[0])
        company_id = obj_wizard.company_id.id

        self.pool.get('res.company').write(cr, uid, [company_id], {'currency_id': obj_wizard.currency_id.id})

        # When we install the CoA of first company, set the currency to price types and pricelists
        if company_id==1:
            for ref in (('product','list_price'),('product','standard_price'),('product','list0'),('purchase','list0')):
                try:
                    tmp2 = obj_data.get_object_reference(cr, uid, *ref)
                    if tmp2: 
                        self.pool[tmp2[0]].write(cr, uid, tmp2[1], {
                            'currency_id': obj_wizard.currency_id.id
                        })
                except ValueError:
                    pass

        # If the floats for sale/purchase rates have been filled, create templates from them
        self._create_tax_templates_from_rates(cr, uid, obj_wizard, company_id, context=context)

        # Install all the templates objects and generate the real objects
        acc_template_ref, taxes_ref, tax_code_ref = self._install_template(cr, uid, obj_wizard.chart_template_id.id, company_id, code_digits=obj_wizard.code_digits, obj_wizard=obj_wizard, context=context)

        # write values of default taxes for product as super user
        if obj_wizard.sale_tax and taxes_ref:
            ir_values_obj.set_default(cr, SUPERUSER_ID, 'product.product', "taxes_id", [taxes_ref[obj_wizard.sale_tax.id]], for_all_users=True, company_id=company_id)
        if obj_wizard.purchase_tax and taxes_ref:
            ir_values_obj.set_default(cr, SUPERUSER_ID, 'product.product', "supplier_taxes_id", [taxes_ref[obj_wizard.purchase_tax.id]], for_all_users=True, company_id=company_id)

        # Create Bank journals
        self._create_bank_journals_from_o2m(cr, uid, obj_wizard, company_id, acc_template_ref, context=context)
        return {}

    
    
class account_payment_term(models.Model):
    _inherit = 'account.payment.term'
    
    @api.model
    def _payment_type_get(self):
        return [
                ('before_validation', _('On the order')),
                ('before_delivery', _('Before delivery')),
                ('after_invoicing', _('After invoicing')),
                       ]
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    payment_type = fields.Selection('_payment_type_get', string='Type', required=True, default='after_invoicing', help="Choose the type of the payment."
                                    "On the order will block the order before the payment validation and before delivery will block the delivery "
                                    "before the payment validation.")
    invoice_date = fields.Date(string='Invoice date')
    invoice_date_due = fields.Date(string='Invoice date due')
    
    
    @api.multi
    def compute_date_due(self):
        """
            Fonction du bouton permettant de calculer la date d'échéance à partir d'une date de facture
        """
        for term in self:
            if term.invoice_date:
                pterm_list = term.compute(value=1, date_ref=term.invoice_date)[0]
                if pterm_list:
                    self.invoice_date_due = max(line[0] for line in pterm_list)
                
        return True
    
    def compute_line_term(self, line, amount, result, prec, date_ref, value):
        if line.value == 'fixed':
            amt = round(line.value_amount, prec)
        elif line.value == 'procent':
            amt = round(value * line.value_amount, prec)
        elif line.value == 'balance':
            amt = round(amount, prec)
            
        if amt:
            if line.term_type == 'days_end_then_month':
                next_date = datetime.strptime(date_ref, '%Y-%m-%d') + relativedelta(days=line.days)
                next_first_date = next_date + relativedelta(day=1, months=1)
                next_date = next_first_date + relativedelta(days=-1)
                if line.days2 > 0:
                    next_date += relativedelta(day=line.days2, months=1)
                    
            elif line.term_type == 'end_days_then_month':
                next_date = datetime.strptime(date_ref, '%Y-%m-%d')
                next_first_date = next_date + relativedelta(day=1, months=1)
                next_date = next_first_date + relativedelta(days=-1)
                next_date = (next_date + relativedelta(days=line.days))
                if line.days2 < 0:
                    next_first_date = next_date + relativedelta(day=1, months=1)
                    next_date = next_first_date + relativedelta(days=line.days2)
                elif line.days2 > 0:
                    if next_date.day > line.days2:
                        next_date += relativedelta(day=line.days2, months=1)
                    elif next_date.day < line.days2:
                        next_date += relativedelta(day=line.days2)
            
            elif line.term_type == 'days_then_month':
                next_date = datetime.strptime(date_ref, '%Y-%m-%d') + relativedelta(days=line.days)
                if line.days2 < 0:
                    next_first_date = next_date + relativedelta(day=1, months=1) 
                    next_date = next_first_date + relativedelta(days=line.days2)
                elif line.days2 > 0:
                    if next_date.day > line.days2:
                        next_date += relativedelta(day=line.days2, months=1)
                    elif next_date.day < line.days2:
                        next_date += relativedelta(day=line.days2)
                    
            elif line.term_type == 'month_then_days':
                next_date = datetime.strptime(date_ref, '%Y-%m-%d')
                if line.days2 < 0:
                    next_first_date = next_date + relativedelta(day=1, months=1)
                    next_date = next_first_date + relativedelta(days=line.days2)
                    
                elif line.days2 > 0:
                    if next_date.day > line.days2:
                        next_date += relativedelta(day=line.days2, months=1)
                    elif next_date.day < line.days2:
                        next_date += relativedelta(day=line.days2)
                    
                next_date += relativedelta(days=line.days)
                
            result.append((next_date.strftime('%Y-%m-%d'), amt))
            amount -= amt
        
        return amount, result
        
        
            
    @api.one
    def compute(self, value, date_ref=False):
        """
            On remplace la fonction de base d'Odoo afin de prendre en compte le type de calcul pour la date d'échéance
        """
        if not date_ref:
            date_ref = datetime.now().strftime('%Y-%m-%d')
            
        amount = value
        result = []
        obj_precision = self.env['decimal.precision']
        prec = obj_precision.precision_get('Account')
        for line in self.line_ids:
            amount, result = self.compute_line_term(line, amount, result, prec, date_ref, value)

        amount = reduce(lambda x,y: x+y[1], result, 0.0)
        dist = round(value-amount, prec)
        if dist:
            result.append((time.strftime('%Y-%m-%d'), dist))
            
        return result
    
    
    
class account_payment_term_line(models.Model):
    _inherit = 'account.payment.term.line'
    @api.model
    def _term_type_get(self):
        return [
            ('days_end_then_month', _('Day number + end of month + day in the month')),
            ('end_days_then_month', _('End of month + day number + day in the month')),
            ('month_then_days', _('Day in the month + day number')),
            ('days_then_month', _('Day number + day in the month')),
               ]
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    term_type = fields.Selection('_term_type_get', string='Compute type', required=True, default='days_then_month',
                                 help="""Choose the type of the computation. If invoice date=05/10, number of days=45 and day of month=-1:
If you choose 'Day in the month + day number', then the due date is 30/11.
If you choose 'Day number + day in the month', then the due date is 15/12.""")
            
            
    @api.onchange('value', 'value_amount')
    def _onchange_value(self):
        res = {}
        if self.value == 'procent':
            if self.value_amount < 0:
                self.value_amount = 0
                res = {'warning': {'title': _('Warning'), 'message': _('Error! The percentage must be between 0 and 1.')}}
            elif self.value_amount > 1:
                self.value_amount = 1
                res = {'warning': {'title': _('Warning'), 'message': _('Error! The percentage must be between 0 and 1.')}}
        
        return res
    
    
    
class account_invoicing_method_payment_line(models.Model):
    """
        Paiement anticipé
    """
    _name = 'account.invoicing.method.payment.line'
    _order = 'payment_type'
    
    @api.model
    def _payment_type_get(self):
        return [('before_validation', _('On the order')),
                ('before_delivery', _('Before delivery'))]
    

    @api.model
    def _value_get(self):
        return [('procent', _('Percent')),
                ('fixed', _('Fixed amount'))]
        
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    payment_type = fields.Selection('_payment_type_get', string='Type', required=True, default='before_validation', help="Choose the type of the payment."
                                    "On the order will block the order before the payment validation and before delivery will block the delivery "
                                    "before the payment validation.")
    value = fields.Selection('_value_get', required=True)
    value_amount = fields.Float(string='Amount to pay', digits=dp.get_precision('Payment Term'), default=0.0, required=False, help="For percent enter a ratio between 0-1.")
    is_blocking = fields.Boolean(string='Is blocking', default=False)
    invoicing_method_id = fields.Many2one('account.invoicing.method', 'Invoicing method', required=True, select=True, ondelete='cascade')
            
            
    @api.onchange('value', 'value_amount')
    def _onchange_value(self):
        res = {}
        if self.value == 'procent':
            if self.value_amount < 0:
                self.value_amount = 0
                res = {'warning': {'title': _('Warning'), 'message': _('Error! The percentage must be between 0 and 1.')}}
            elif self.value_amount > 1:
                self.value_amount = 1
                res = {'warning': {'title': _('Warning'), 'message': _('Error! The percentage must be between 0 and 1.')}}
        
        return res



class account_invoicing_method_line(models.Model):
    """
        Ligne de méthode de facturation
    """
    _name = 'account.invoicing.method.line'
    _rec_name = 'sequence'
    
    @api.model
    def _value_get(self):
        return [('procent', 'Percent'),
                ('balance', 'Balance'),
                ('fixed', 'Fixed Amount')]
        
    
    @api.model
    def _invoice_trigger_get(self):
        return [
            ('picking', _('To the delivery')),
            ('manual', _('On demand')),
            ('postpaid', _('On the order')),
               ]
        
        
    @api.model
    def _account_invoiced_on_get(self):
        return [
            ('order', _('Ordered quantities')),
            ('delivery', _('Delivered quantities')),
               ]
        
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    sequence = fields.Integer(default=0, required=True, help='The sequence field is used to order the payment term lines from the lowest sequences to the higher ones')
    value = fields.Selection('_value_get', string='Valuation', required=True, default='balance', help='Select here the kind of valuation related to this payment term line. Note that you should have your last line with the type \'Balance\' to ensure that the whole amount will be threated.')
    value_amount = fields.Float(string='Amount To Pay', digits_compute=dp.get_precision('Payment Term'), default=0.0, required=False, help='For percent enter a ratio between 0-1.')
    invoicing_method_id = fields.Many2one('account.invoicing.method', 'Invoicing method', required=True, select=True, ondelete='cascade')
    payment_term_id = fields.Many2one('account.payment.term', string='Forced payment term', required=False, ondelete='restrict', help='Payment term for the invoice generated by this line (if field is empty, the invoice will have the order payment term)')
    invoice_trigger = fields.Selection('_invoice_trigger_get', string='Invoicing method trigger', required=True)
    account_invoiced_on = fields.Selection('_account_invoiced_on_get', string='Invoiced on', required=True, default='order')
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='restrict')
    
    
    @api.one
    @api.constrains('invoice_trigger', 'account_invoiced_on')
    def _check_function(self):
        if self.invoice_trigger != 'picking' and self.account_invoiced_on == 'delivery':
            raise Warning(_('Error! Impossible to invoice on delivered quantities if the invoice trigger is not on delivery.'))
        

    @api.onchange('invoice_trigger')
    def _onchange_invoice_trigger(self):
        if self.invoice_trigger != 'picking':
            self.account_invoiced_on = 'order'
        elif self.invoice_trigger == 'picking':
            self.account_invoiced_on = 'delivery'
            
            
    @api.onchange('value', 'value_amount')
    def _onchange_value(self):
        res = {}
        if self.value == 'procent':
            if self.value_amount < 0:
                self.value_amount = 0
                res = {'warning': {'title': _('Warning'), 'message': _('Error! The percentage must be between 0 and 1.')}}
            elif self.value_amount > 1:
                self.value_amount = 1
                res = {'warning': {'title': _('Warning'), 'message': _('Error! The percentage must be between 0 and 1.')}}
        
        return res
            
     
        
class account_invoicing_method(models.Model):
    """
        Méthode de facturation
    """
    _name = 'account.invoicing.method'
    _sql_constraints = [('invoicing_method_name_unique', 'unique(name)', 'Invoicing method name already exists')]
    @api.one
    @api.constrains('line_ids')
    def _check_balance(self):
        balance_rs = self.env['account.invoicing.method.line'].search([('invoicing_method_id', '=', self.id),
                                                                       ('value', '=', 'balance')])
        if len(balance_rs) != 1:
            raise ValidationError(_('You must to have one and only one balance line'))
        elif balance_rs.invoice_trigger != 'picking':
            if self.env['account.invoicing.method.line'].search([('invoicing_method_id', '=', self.id),
                                                                 ('invoice_trigger', '=', 'picking')], limit=1):
                raise ValidationError(_('Impossible to have a balance before delivery with an invoicing method line on delivery'))
            
            
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(size=128, required=True)
    active = fields.Boolean(default=True)
    payment_line_ids = fields.One2many('account.invoicing.method.payment.line', 'invoicing_method_id', 'Terms', copy=True)
    line_ids = fields.One2many('account.invoicing.method.line', 'invoicing_method_id', 'Invoicing', copy=True)
    note = fields.Text()

    
    def get_invoiced_on(self, invoice_trigger): 
        line_rs =  self.env['account.invoicing.method.line'].search([('invoicing_method_id', '=', self.id), ('invoice_trigger', '=', invoice_trigger)], limit=1)
        if line_rs:
            res = line_rs.account_invoiced_on
        else:
            res = False
            
        return res
    
    
    def get_total_amount(self, compute_type, payment_type, amount):
        """
            Calcul du montant à payer / facturer en fonction des conditions de paiement
            :param compute_type: char: 'payment' ou 'invoice'
            :param payment_type: Type de paiement (commande ou livraison)
            :param amount: Montant de base
            :return: True
        """
        res = 0.0
        if compute_type == 'payment':
            for payment_line in self.env['account.invoicing.method.payment.line'].search([('invoicing_method_id', '=', self.id), ('payment_type', '=', payment_type)]):
                if payment_line.value == 'procent':
                    res += amount * payment_line.value_amount
                elif payment_line.value == 'fixed':
                    res += payment_line.value_amount
                    
        return res
    
    
    def get_invoice_percentage(self, invoice_trigger):
        """
            Calcul pourcentage à facturer
            :param invoice_trigger: char: 'picking', 'manual' ou 'postpaid'
            :return: True
        """
        if invoice_trigger:
            res = 0.0
            for line in self.env['account.invoicing.method.line'].search([('invoicing_method_id', '=', self.id), 
                                                                          ('invoice_trigger', '=', invoice_trigger),
                                                                          ('value', 'in', ('procent', 'balance'))]):
                if line.value == 'procent':
                    res += line.value_amount
                elif line.value == 'balance':
                    res = 1.0
                    break
        
        else:
            res = 1.0
        
        return res
    
    
    def get_invoice_fixed_amount(self, invoice_trigger):
        """
            Calcul pourcentage à facturer
            :param invoice_trigger: char: 'picking', 'manual' ou 'postpaid'
            :return: True
        """
        res = []
        if invoice_trigger:
            fixed_amount_sums = self.env['account.invoicing.method.line'].search_group(fields=['value_amount', 'product_id'], 
                                                                                      groupby=['product_id'], 
                                                                                      args=[('invoicing_method_id', '=', self.id), 
                                                                                            ('invoice_trigger', '=', invoice_trigger),
                                                                                            ('value', '=', 'fixed')],
                                                                                      sum=['value_amount'],
                                                                                      return_dict=True,
                                                                                      without_order=True)
            for fixed_amount_sum in fixed_amount_sums:
                res.append((fixed_amount_sum['value_amount'] or 0.0, fixed_amount_sum['product_id']))

        return res
    
    
    @api.multi
    def copy(self, default=None):
        """
            Changement du nom
        """
        if not default:
            default = {}
        
        if 'name' not in default:
            default['name'] = '%s (copy)'%(self.name)
            
        return super(account_invoicing_method, self).copy(default=default)
    


class payment_method(models.Model):
    """ 
    Payment method
    """
    _name = 'payment.method'
    _description = 'Payment method'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(size=64, required=True)



class account_journal(models.Model):
    _inherit = 'account.journal'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    is_default = fields.Boolean(string='Is default', default=False, help="Check if you want this journal for automatic payments")

    
    
class account_move(models.Model):
    _inherit = 'account.move'
    
    @api.multi
    def button_cancel(self):
        if self.env.context.get('manual_move_cancel'):
            for move in self:
                if move.voucher_id:
                    raise ValidationError(_('Unable to manually cancel an account move linked to a voucher.'))                    
                else:
                    for move_line in move.line_id:
                        if move_line.invoice:
                            raise ValidationError(_('Unable to manually cancel an account move linked to an invoice.'))                    
        
        return super(account_move, self).button_cancel()
    
    

class account_move_line(models.Model):
    _inherit = 'account.move.line'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    is_adjustment = fields.Boolean(string='Is adjustment', default=False, readonly=True, 
                                   help="Checked if the account move line is an adjustment")
    reconcile_origin_id = fields.Many2one('account.move.reconcile', string='Origin reconcile', required=False, ondelete='set null',
                                          readonly=True)
    
    
    def voucher_line_reconcile(self):
        """
            Fonction permettant de récupérer les écritures comptables des paiements et des factures afin de faire le lien
            dans l'objet des paiements 
        """
        context = self.env.context
        move_id_list = []
        #Si on a passé l'id d'une facture, une liste de paiement et leur montant à lettrer, on les récupère pour lancer la fonction de 
        #création de lignes de paiement, sinon on lance la fonction de création avec les écritures comptables
        voucher_obj = self.env['account.voucher']
        # Depuis le wizard
        if context.get('payment_lines') and context.get('invoice_id'):
            invoice_rs = self.env['account.invoice'].browse(context['invoice_id'])
            #Gestion du passage des ids en unicode
            payment_dict = {}
            for payment_id, amount in context['payment_lines'].items():
                if isinstance(payment_id, int):
                    payment_dict[payment_id] = amount
                elif isinstance(payment_id, unicode):
                    payment_dict[int(payment_id)] = amount
            
            if payment_dict:
                payment_list = voucher_obj.browse(payment_dict.keys())
                payment_list.create_voucher_line(move_line_list=False, invoice_rs=invoice_rs, pay_amount_to_reconcile=payment_dict)
        # Manuel
        else:
            list_ids = self.ids
            move_list = []
            move_line_list = []
            pay_amount_to_reconcile = {}
            payment_rs = self.env['account.voucher']
            #On recherche les paiements liés aux mouvements et les écritures comptables liées à une facture
            for move_line in self:
                if move_line.move_id:
                    move_list.append(move_line.move_id)
                    
                if move_line.invoice:
                    move_line_list.append(move_line)
            
            if move_list:
                move_list = list(set(move_list))
            
            #En cas d'écritures d'ajustement, on lie les montants aux bons paiements
            #Pour cela on recherche d'abord le montant correct en parcourant les pièces comptables
            for move in move_list:
                tot_debit = 0
                tot_credit = 0
                amount_not_rec_debit = 0
                amount_not_rec_credit = 0
                move_id_list.append(move.id)
                if move.voucher_id:
                    pay_amount = 0
                    adjust_rec = False
                    for line in move.line_id:
                        if line.is_adjustment and (not line.reconcile_id and not line.reconcile_partial_id):
                            if not line.id in list_ids:
                                amount_not_rec_debit += line.debit
                                amount_not_rec_credit += line.credit
                            else:
                                tot_debit += line.debit
                                tot_credit += line.credit
                                    
                    if amount_not_rec_debit > 0 or tot_credit > 0:
                        pay_amount = tot_credit - amount_not_rec_debit
                        adjust_rec = True
                    elif amount_not_rec_credit > 0 or tot_debit > 0:
                        pay_amount = tot_debit - amount_not_rec_credit
                        adjust_rec = True
                    
                    if adjust_rec:
                        if not move.voucher_id.id in pay_amount_to_reconcile:
                            pay_amount_to_reconcile[move.voucher_id.id] = abs(pay_amount)
                        else:
                            pay_amount_to_reconcile[move.voucher_id.id] = 0
            
            payment_search_rs = voucher_obj.search([('account_move_ids', 'in', move_id_list)])
            if move_line_list:
                for payment in payment_search_rs:
                    if payment.writeoff_amount > 0:
                        payment_rs += payment
                
                payment_rs.create_voucher_line(move_line_list=move_line_list, invoice_rs=False, pay_amount_to_reconcile=pay_amount_to_reconcile)
                
        return True
    
    
    @api.multi
    def reconcile(self, type='auto', writeoff_acc_id=False, writeoff_period_id=False, writeoff_journal_id=False):
        """
            Surcharge de la fonction de lettrage afin de permettre la création des lignes de
            paiement afin de rattacher une ou des factures au paiement
        """
        self.voucher_line_reconcile()
        reconcile_id = super(account_move_line, self).reconcile(type=type, writeoff_acc_id=writeoff_acc_id, 
                                                       writeoff_period_id=writeoff_period_id, writeoff_journal_id=writeoff_journal_id)
        if reconcile_id:
            reconcile_rs = self.env['account.move.reconcile'].browse(reconcile_id)
            partner_list = [line.partner_id.id for line in reconcile_rs.line_id if line.partner_id]
            partner_diff = partner_list and list(set(partner_list)) or []
            if partner_diff and len(partner_diff) > 1:
                reconcile_rs.different_partner_reconcile(reconcile_id)
            
        return reconcile_rs
    
    
    @api.multi
    def reconcile_partial(self, type='auto', writeoff_acc_id=False, writeoff_period_id=False, writeoff_journal_id=False):
        """
            Surcharge de la fonction de lettrage partiel afin de permettre la création des lignes de
            paiement pour rattacher une ou des factures au paiement
        """
        self.voucher_line_reconcile()
        res = super(account_move_line, self).reconcile_partial(type=type, writeoff_acc_id=writeoff_acc_id, 
                                                       writeoff_period_id=writeoff_period_id, writeoff_journal_id=writeoff_journal_id)
        return res
    
    
    @api.multi
    def openprod_adjust_reconcile(self, move_line_list=False, move_amount_to_reconcile=False):
        """
            Fonction permettant de créer automatiquement des écritures comptables d'ajustement lorsqu'on
            souhaite lettrer un montant supérieur au montant de la ou des factures.
            On envoie soit une liste d'écritures comptable à lettrer, soit une écriture de facture avec des écritures 
            à lettrer et le montant correspondant
            :type self: account.move.line (écritures des factures ou avoirs à lettrer)
            :param move_line_list: Liste de recordset de account.move.line à lettrer avec les factures ou les avoirs
            :type move_line_list: List
            :param move_amount_to_reconcile: Dictionnaire contenant le montant à lettrer pour chaque écriture
            :type move_amount_to_reconcile: dictionnaire à lettrer
            :rtype: List, recordset de account.move.line
        """
        move_line_dict = {}
        moves_to_reconcile = self.env['account.move.line']
        moves_not_reconcile = self.env['account.move.line']
        today_date = fields.Date.today()
        account_move_obj = self.env['account.move']
        period_obj = self.env['account.period']
        voucher_obj = self.env['account.voucher']
        #On crée un dictionnaire contenant l'écriture comptable ainsi que le montant restant à lettrer de chacune
        if move_line_list:
            move_line_dict = {move_line: move_line.amount_residual for move_line in move_line_list}
        
        if move_line_dict:
            #On récupère le montant total des écritures correspondant aux factures (ou aux avoirs)
            amount_invoiced_list = [invoice_move_line.amount_residual for invoice_move_line in self]
            residual_amount = sum(amount_invoiced_list)
            for line, remaining_amount in move_line_dict.items(): 
                #Si on a passé un montant à lettrer on récupère celui-ci, sinon on va ajouter le montant de
                #l'écriture comptable en la déduisant 
                # Lettrage par le wizard
                if move_amount_to_reconcile and line.id in move_amount_to_reconcile:
                    move_line_dict[line] -= move_amount_to_reconcile[line.id]
                # Lettrage manuel
                else:
                    line_amount = remaining_amount
                    write_amount = 0
                    if residual_amount > 0:
                        if residual_amount - line_amount >= 0:
                            write_amount = line_amount
                        else:
                            write_amount = line_amount + (residual_amount - line_amount)
                    
                    else:
                        write_amount = 0
                        
                    residual_amount -= write_amount
                    move_line_dict[line] -= write_amount
                        
            #On récupère toutes les écritures de paiement dont le montant n'a pas été totalement lettré
            last_pay_moves = [move_line_rs for move_line_rs in move_line_dict.keys() if move_line_dict[move_line_rs] > 0]
            #On va créer une pièce comptable ainsi que toutes les écritures comptables à lettrer par 
            #écritures à ajuster
            for pay_move_line in last_pay_moves:
                pay_move = pay_move_line.move_id
                if pay_move:
                    #Si l'écriture comptable est liée à un paiement, on lie aussi la nouvelle pièce comptable
                    #à ce paiement
                    if pay_move.voucher_id:
                        linked_payment = pay_move.voucher_id
                    else:
                        linked_payment = voucher_obj.search([('number', '=', pay_move.name), 
                                                             ('account_move_ids', 'in', pay_move.id)], limit=1)
                    voucher_id = linked_payment and linked_payment.id or False
                    #Création de la pièce comptable
                    period_rs = period_obj.find(today_date)
                    move_name = _('%s adjustment')%(pay_move.name)
                    move_vals = {
                        'name': move_name,
                        'journal_id': pay_move.journal_id.id,
                        'narration': pay_move.narration,
                        'date': today_date,
                        'ref': pay_move.ref,
                        'period_id': period_rs.id,
                        'voucher_id': voucher_id,
                    }
                    new_move = account_move_obj.create(move_vals)
                    # Création de l'écriture comptable
                    moves_to_reconcile_list, move_not_reconcile = self.create_move_line_from_ex(pay_move_line, move_line_dict[pay_move_line], new_move)
                    for move_rec in moves_to_reconcile_list:
                        if move_rec:
                            moves_to_reconcile += move_rec
                        
                    moves_not_reconcile += move_not_reconcile
                        
                    # Validation de la pièce comptable
                    new_move.post()
        
        return moves_to_reconcile, moves_not_reconcile
    
    
    def create_move_line_from_ex(self, move_pattern, remaining_amount, move):
        """
            Fonction permettant de créer trois écritures comptables.
            On lui passe une écriture modèle, le montant restant sur cette écriture 
            et la pièce comptable à rattacher aux écritures
            Retourne les écritures à lettrer et l'écriture à ne pas lettrer séparément
        """
        context = self.env.context
        context2 = {}
        #Création d'un dictionnaire pour ne pas avoir à répéter le même code 3 fois
        #Les deux premières écritures seulement sont à lettrer
        #1 : Création de la ligne 'annulant' celle du paiement
        #2 : Création de la ligne correspondant au montant à lettrer
        #3 : Création de la ligne du montant restant de l'écriture 
        vals_list = {'first_to_reconcile' : 
                        {'amount_currency': move_pattern.amount_currency, 
                         'amount': move_pattern.amount_residual},
                     'second_to_reconcile':
                        {'amount': (move_pattern.amount_residual or remaining_amount) - (remaining_amount)},
                      'third_not_reconcile':
                        {'amount': remaining_amount}}
        context2.update(context)
        context2['novalidate'] = True
        for dict_key, dict_val in vals_list.items():
            if dict_val.get('amount_currency'):
                amount_currency = dict_val['amount_currency']
            else:
                amount_currency = dict_val.get('amount', 0)
            
            if dict_val.get('amount'):
                move_line_vals = {
                    'journal_id': move_pattern.journal_id.id,
                    'period_id': move.period_id.id,
                    'name': move.name,
                    'account_id': move_pattern.account_id.id,
                    'move_id': move.id,
                    'partner_id': move_pattern.partner_id.id,
                    'currency_id': move_pattern.currency_id.id,
                    'quantity': 1,
                    'state': 'valid',
                    'date': move.date,
                    'is_adjustment': True,
                }
                if move_pattern.debit > 0:
                    if dict_key == 'first_to_reconcile':
                        move_line_vals['credit'] = dict_val.get('amount', 0)
                        move_line_vals['debit'] = 0
                    else:
                        move_line_vals['debit'] = dict_val.get('amount', 0)
                        move_line_vals['credit'] = 0
                elif move_pattern.credit > 0:
                    if dict_key == 'first_to_reconcile':
                        move_line_vals['credit'] = 0
                        move_line_vals['debit'] = dict_val.get('amount', 0)
                    else:
                        move_line_vals['debit'] = 0
                        move_line_vals['credit'] = dict_val.get('amount', 0)
                
                if move_pattern.currency_id:
                    move_line_vals['amount_currency'] = amount_currency
                
                dict_val['move_line_to_reconcile'] = self.with_context(context2).create(move_line_vals)
        
        #Écritures à lettrer
        move_to_reconcile = [vals_list[key].get('move_line_to_reconcile', False) for key in vals_list.keys() if key in ['first_to_reconcile', 'second_to_reconcile']]
        #Écriture à ne pas lettrer
        move_not_reconcile = vals_list['third_not_reconcile'].get('move_line_to_reconcile')
        return move_to_reconcile, move_not_reconcile



class account_move_reconcile(models.Model):
    _inherit = 'account.move.reconcile'
    
    
    @api.multi
    def unlink(self):
        """
            Surcharge du unlink pour supprimer les pièces comptables d'ajustement
        """
        move_line_obj = self.env['account.move.line']
        unlink_move_list = self.env['account.move']
        move_list = self.env['account.move']
        list_ids = self.ids
        move_list_ids = []
        
        #On récupère toutes les écritures comptables liées aux lettrages: celles d'ajustement créée pour le lettrage
        #mais qui n'en font pas parties et celles qui font parties du lettrage
        move_line_rs = move_line_obj.search(['|', ('reconcile_id', 'in', list_ids), 
                                             '|', ('reconcile_origin_id', 'in', list_ids), ('reconcile_partial_id', 'in', list_ids)])
        #On récupère deux listes de pièces comptable: l'une correspondant aux ajustements qui est à supprimer et l'autre
        #qui correspond à toutes les pièces comptables liées au lettrage
        for move_line in move_line_rs:
            move_list_ids.append(move_line.id)
            #Si on a une écriture qui est lettrée avec un lettrage (total ou partiel) qui n'est pas à supprimer, on renvoi un message d'erreur
            if (move_line.reconcile_id and move_line.reconcile_id.id not in list_ids) or (move_line.reconcile_partial_id and move_line.reconcile_partial_id.id not in list_ids):
                raise ValidationError(_('Some adjustment account move line have been reconciled (partially or totally) with other account move line. ' 
                'Please, delete this reconciles first'))
            
            elif move_line.is_adjustment and move_line.reconcile_origin_id.id in list_ids and move_line.move_id not in unlink_move_list:
                unlink_move_list += move_line.move_id
            elif move_line.move_id not in move_list:
                move_list += move_line.move_id
        
        move_list += unlink_move_list
        res = super(account_move_reconcile, self).unlink()
        #On recherche et on supprime toutes les lignes de paiement générées par le lettrage 
        voucher_line_rs = self.env['account.voucher.line'].search([('move_line_id', 'in', move_list_ids), 
                                                                   ('voucher_id.account_move_ids', 'in', move_list.ids)])
        voucher_line_rs.unlink()
        #On parcourt toutes les pièces comptables à supprimer 
        for move_rs in unlink_move_list:
            line_rs_to_unlink = self.env['account.move.line']
            line_ids_not_unlink = []
            #Annulation des pièces comptables pour permettre suppression des lignes 
            move_rs.button_cancel()
            for line in move_rs.line_id:
                if line not in move_line_rs:
                    line_ids_not_unlink.append(line.id)
                else:
                    line_rs_to_unlink |= line
            
            if line_ids_not_unlink:
                line_rs_to_unlink.unlink()
            else:
                #Suppression de la pièce comptable
                move_rs.unlink()
                    
        return res
    
    
    @api.one
    def different_partner_reconcile(self, origin_reconcile_id=False):
        """
            Fonction permettant de créer une pièce comptable contenant des écritures qui ajustent les 
            comptes dans le cas de payeurs et facturés différents dans le lettrage. On va copier
            les écritures comptables qui permettent d'équilibrer les comptes
            :type self: account.move.reconcile
            :param origin_reconcile_id: id du lettrage à l'origine de l'ajustement
            :type origin_reconcile_id: integer
            :return: True
            :rtype: boolean
        """
        today_date = fields.Date.today()
        account_move_obj = self.env['account.move']
        account_move_line_obj = self.env['account.move.line']
        period_rs = self.env['account.period'].find(today_date)
        dict_from_reconcile = {}
        context = self.env.context
        context2 = {}
        context2.update(context)
        context2['novalidate'] = True
        journal_id = False
        #On commence par enlever les écritures que l'on ne copie pas et par récupérer celles que l'on copie
        #grâce à un dictionnaire de la forme:
        #{(id_partenaire, montant_écriture, 'débit' ou 'crédit'): recordset de la ligne de lettrage}
        #Pour ça, on crée une clé et une clé inverse pour chaque ligne, et si cette clé
        #inverse existe dans le dictionnaire, on supprime l'entrée correspondant à cette clé.
        #Permet de gérer les cas d'ajustements
        i = 0
        for rec_line in self.line_id:
            i+=1
            if not journal_id and rec_line.journal_id.type in ['purchase', 'sale']:
                journal_id = rec_line.journal_id.id
                
            if rec_line.debit:
                amount_line = rec_line.debit
                type_line = 'debit'
                inv_type_line = 'credit'
            else:
                amount_line = rec_line.debit or rec_line.credit
                type_line = 'credit'
                inv_type_line = 'debit'
                
            # key et inv_key servent à detecter les lignes déja équilibrées
            key = (rec_line.partner_id.id, amount_line, type_line)
            inv_key = (rec_line.partner_id.id, amount_line, inv_type_line)
            if inv_key in dict_from_reconcile:
                # Suppression des lignes déjà équilibrées
                del dict_from_reconcile[inv_key]
            elif key in dict_from_reconcile.keys():
                # Traitement des lignes non équilibrées
                # Gestion des lignes semblables 
                key += (i, )
                dict_from_reconcile[key] = rec_line
            else:
                dict_from_reconcile[key] = rec_line
        
        if journal_id and period_rs:
            #On crée une pièce comptable globale
            move_vals = {
                'name': _('%s partner adjustment')%(self.name),
                'journal_id': journal_id,
                'date': today_date,
                'ref': self.name,
                'period_id': period_rs.id,
            }
            new_move = account_move_obj.create(move_vals)
            #On crée une ligne d'ajustement pour chaque ligne trouvée précédemment
            for line_rs in dict_from_reconcile.values():
                move_line_vals = {
                    'journal_id': journal_id,
                    'period_id': period_rs.id,
                    'name': _('%s partner adjustment')%(line_rs.name),
                    'account_id': line_rs.account_id.id,
                    'move_id': new_move.id,
                    'partner_id': line_rs.partner_id.id,
                    'currency_id': line_rs.currency_id.id,
                    'quantity': 1,
                    'state': 'valid',
                    'date': today_date,
                    'reconcile_id': self.id,
                    'is_adjustment': True,
                    'reconcile_origin_id': origin_reconcile_id,
                }
                if line_rs.credit > 0:
                    move_line_vals['debit'] = line_rs.credit
                    move_line_vals['credit'] = 0
                elif line_rs.debit > 0:
                    move_line_vals['credit'] = line_rs.debit
                    move_line_vals['debit'] = 0
                
                amount_currency = line_rs.amount_currency
                if line_rs.currency_id:
                    if move_line_vals['debit'] > 0 and amount_currency < 0:
                        amount_currency /= -1
                    elif move_line_vals['credit'] > 0 and amount_currency > 0:
                        amount_currency /= -1
                        
                    move_line_vals['amount_currency'] = amount_currency
                
                account_move_line_obj.with_context(context2).create(move_line_vals)

            new_move.post()
            
        return True
    
    
    def find_cust_partners(self, partner_id):
        """
            Anticipation du module sale, permettra de gérer les payeurs
            et facturés des clients
            :type self: account.move.reconcile
            :param partner_id: id du partenaire
            :type partner_id: integer
            :return: Liste d'ids de partenaire
            :rtype: list
        """
        return []
    
    
    def find_supp_partners(self, partner_id):
        """
            Anticipation du module purchase, permettra de gérer les payés à
            et factureurs des fournisseurs
            :type self: account.move.reconcile
            :param partner_id: id du partenaire
            :type partner_id: integer
            :return: Liste d'ids de partenaire
            :rtype: list
        """
        return []
    
    
    @api.multi
    def _check_same_partner(self):
        """
            On écrase la fonction de odoo pour prendre en compte les payeurs et facturés des clients
            et les payés à et factureurs des fournisseurs
        """
        for reconcile in self:
            move_lines = []
            can_reconcile = False
            if not reconcile.opening_reconciliation:
                partners_rs = []
                if reconcile.line_id:
                    partners_rs = [line.partner_id.id for line in reconcile.line_id]
                    move_lines = reconcile.line_id
                elif reconcile.line_partial_ids:
                    partners_rs = [line.partner_id.id for line in reconcile.line_partial_ids]
                    move_lines = reconcile.line_partial_ids
                
                if partners_rs:
                    unique_list = list(set(partners_rs))
                    partners_rs = unique_list[:] 
                    partners_ids = unique_list[:]
                    partners_ids.sort()
                    if len(partners_rs) > 1:
                        for partner_id in partners_rs:
                            paid_by_rs = self.find_cust_partners(partner_id)
                            supp_paid_by_rs = self.find_supp_partners(partner_id)
                            paid_by_rs.extend(supp_paid_by_rs)
                            paid_by_ids = list(set(paid_by_rs))
                            paid_by_ids.append(partner_id)
                            paid_by_ids.sort()
                            if (partners_ids or paid_by_ids):
                                rec = True
                                for p_id in partners_ids:
                                    if not p_id in paid_by_ids:
                                        rec = False
                                        break
                                
                                if rec:
                                    can_reconcile = True
                        
                        for line in move_lines:
                            if line.account_id.type in ('receivable', 'payable') and not can_reconcile:
                                return False
                
        return True
    
    
    _constraints = [
        (_check_same_partner, 'You can only reconcile journal items with the same partner.', ['line_id', 'line_partial_ids']),
    ]



class account_fiscal_position(models.Model):
    _inherit = 'account.fiscal.position'


    def compute_domain_args(self, args):
        #Fonction appelée par le search afin d'empécher la sélection d'une autre position
        #fiscale après création d'une ligne
        args2 = []
        for arg in args:
            match = False
            if isinstance(arg, str) or (isinstance(arg, list) and arg[0] in ('!', '|', '&')):
                args2.append(arg)
                continue
            
            if arg[0] == 'line_system_domain':
                if isinstance(arg[-1], list) and arg[-1][0]:
                    arg = ('id', '=', arg[-1][1])
                else:
                    match = True
                    
            if not match:
                args2.append(arg)
             
        return args2
 
     
    @api.model
    def search(self,args=None, offset=0, limit=None, order=None, count=None):
        #Modification du search afin d'empécher la sélection d'une autre position
        #fiscale après création d'une ligne
        args = args or []
        args_modified = self.compute_domain_args(args)
        return super(account_fiscal_position,self).search(args=args_modified, offset=offset, limit=limit, order=order)
    
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=1000):
        """
            Fonction name_search des positions fiscales
        """
        args = self.compute_domain_args(args)
        recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()
    
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = self.compute_domain_args(domain)
        return super(account_fiscal_position, self).read_group(domain=domain, fields=fields, groupby=groupby, offset=offset, limit=limit, orderby=orderby,lazy=lazy)



class account_tax(models.Model):
    _inherit = 'account.tax'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    account_id = fields.Many2one(string='Invoice tax account (On invoice)')
    account_payment_id = fields.Many2one('account.account', 'Invoice tax account (On payment)', help='Set the account that will be set by default on invoice tax lines for refunds. Leave empty to use the expense account.')
    tax_on_payment = fields.Boolean(default=False)
    refund_account_id = fields.Many2one(string='Refund Tax Account (On invoice)')
    refund_account_payment_id = fields.Many2one('account.account', 'Refund Tax Account (On payment)', help='Set the account that will be set by default on invoice tax lines for refunds. Leave empty to use the expense account.')
    
    
    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None):
        """ Returns all information required to apply taxes (in self + their children in case of a tax goup).
            We consider the sequence of the parent for group of taxes.
                Eg. considering letters as taxes and alphabetic order as sequence :
                [G, B([A, D, F]), E, C] will be computed as [A, D, F, C, E, G]

        RETURN: {
            'total_excluded': 0.0,    # Total without taxes
            'total_included': 0.0,    # Total with taxes
            'taxes': [{               # One dict for each tax in self and their children
                'id': int,
                'name': str,
                'amount': float,
                'sequence': int,
                'account_id': int,
                'refund_account_id': int,
                'analytic': boolean,
            }]
        } """
        if len(self) == 0:
            company_id = self.env.user.company_id
        else:
            company_id = self[0].company_id
        if not currency:
            currency = company_id.currency_id
        taxes = []
        # By default, for each tax, tax amount will first be computed
        # and rounded at the 'Account' decimal precision for each
        # PO/SO/invoice line and then these rounded amounts will be
        # summed, leading to the total amount for that tax. But, if the
        # company has tax_calculation_rounding_method = round_globally,
        # we still follow the same method, but we use a much larger
        # precision when we round the tax amount for each line (we use
        # the 'Account' decimal precision + 5), and that way it's like
        # rounding after the sum of the tax amounts of each line

        prec = currency.decimal_places
        if company_id.tax_calculation_rounding_method == 'round_globally':
            prec += 5
        total_excluded = total_included = base = round(price_unit * quantity, prec)
        
        for tax in self:
            if tax.type == 'group':
                ret = tax.children_tax_ids.compute_all(price_unit, currency, quantity, product, partner)
                total_excluded = ret['total_excluded']
                base = ret['total_excluded']
                total_included = ret['total_included']
                tax_amount = total_included - total_excluded
                taxes += ret['taxes']
                continue

            tax_amount = tax._compute_amount(base, price_unit, quantity, product, partner)
            tax_amount = round(tax_amount, prec)

            if tax.price_include:
                total_excluded -= tax_amount
                base -= tax_amount
            else:
                total_included += tax_amount

            if tax.include_base_amount:
                base += tax_amount
            
            if partner:
                tax_name = tax.with_context(lang=partner.lang).name
            else:
                tax_name = tax.name
                
            taxes.append({
                'id': tax.id,
                'name': tax_name,
                'amount': tax_amount,
                'sequence': tax.sequence,
                'account_id': tax.account_id.id,
                'tax_code_id': tax.tax_code_id.id,
                'ref_tax_code_id': tax.ref_tax_code_id.id,
                'refund_account_id': tax.refund_account_id.id,
                'base_code_id': tax.base_code_id.id,
                'ref_base_code_id': tax.ref_base_code_id.id,
                'account_analytic_collected_id': tax.account_analytic_collected_id.id,
                'account_analytic_paid_id': tax.account_analytic_paid_id.id,
                'base_sign': tax.base_sign,
                'tax_sign': tax.tax_sign,
                'ref_base_sign': tax.ref_base_sign,
                'ref_tax_sign': tax.ref_tax_sign,
                'price_unit': price_unit,
                'tax_on_payment': tax.tax_on_payment,
                'account_payment_id': tax.account_payment_id.id,
                'refund_account_payment_id': tax.refund_account_payment_id.id,
            })
        
        return {
            'taxes': sorted(taxes, key=lambda k: k['sequence']),
            'total_excluded': total_excluded,
            'total_included': total_included
        }
    
    
    @api.multi
    def unlink(self):
        """
            On empêche la suppression de la taxe si elle est utilisée dans un produit
        """
        product_obj = self.env['product.product']
        for tax in self:
            tax_rel_rs = product_obj.search(['|', ('purchase_taxes_ids', 'in', tax.id), ('sale_taxes_ids', 'in', tax.id)], limit=1)
            if tax_rel_rs:
                raise except_orm(_('Error'), _('The tax %s is used in a product. Please delete the tax reference in '
                                               'the product before delete it')%(tax.name))
        
        return super(account_tax, self).unlink()



   
    
class account_vat_return_template(models.Model):
    """ 
    Account VAT return template
    """
    _name = 'account.vat.return.template'
    _description = 'Account VAT return template'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(size=64, required=True)
    debit_vat_account_ids = fields.Many2many('account.account', 'vat_return_debit_account_rel', 'vat_return_id', 'account_id', string='Debit VAT accounts', copy=True, domain=[('type', 'not in', ('view', 'closed', 'consolidation'))])
    credit_vat_account_ids = fields.Many2many('account.account', 'vat_return_credit_account_rel', 'vat_return_id', 'account_id', string='Credit VAT accounts', copy=True, domain=[('type', 'not in', ('view', 'closed', 'consolidation'))])
    waiting_vat_account_ids = fields.Many2many('account.account', 'vat_return_waiting_account_rel', 'vat_return_id', 'account_id', string='Waiting VAT accounts', copy=True, domain=[('type', 'not in', ('view', 'closed', 'consolidation'))])
    sale_account_ids = fields.Many2many('account.account', 'vat_return_sale_account_rel', 'vat_return_id', 'account_id', string='Sale accounts', copy=True, domain=[('type', 'not in', ('view', 'closed', 'consolidation'))])
    purchase_account_ids = fields.Many2many('account.account', 'vat_return_purchase_account_rel', 'vat_return_id', 'account_id', string='Purchase accounts', copy=True, domain=[('type', 'not in', ('view', 'closed', 'consolidation'))])
    
    
    
class account_vat_return(models.Model):
    """ 
    Account VAT return
    """
    _name = 'account.vat.return'
    _description = 'Account VAT return'
    
    @api.model
    def _state_get(self):
        return [
                ('draft', 'Draft'),
                ('progress', 'Progress'),
                ('done', 'Done'),
                ('cancel', 'Cancel'),
                       ]
        
        
    @api.model
    def _default_period_id(self):
        return self.env['account.period'].find(fields.Date.today())
    
    
    def _get_states(self):
        return {
            'draft': [('readonly', False)], 
            'progress': [('readonly', True)], 
            'done': [('readonly', True)], 
            'cancel': [('readonly', True)], 
                }

    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(size=64, required=True, states=_get_states)
    template_id = fields.Many2one('account.vat.return.template', string='Return template', required=True, ondelete='restrict', states=_get_states)
    partner_id = fields.Many2one('res.partner', string='Partner', required=True, ondelete='restrict', states=_get_states)
    start_date = fields.Date(states=_get_states)
    end_date = fields.Date(states=_get_states)
    credit = fields.Float(default=0.0, required=False)
    debit = fields.Float(default=0.0, required=False)
    debit_vat_account_ids = fields.One2many('account.vat.return.line', 'vat_return_id', string='Debit VAT accounts', domain=[('line_type', '=', 'debit')])
    credit_vat_account_ids = fields.One2many('account.vat.return.line', 'vat_return_id', string='Credit VAT accounts', domain=[('line_type', '=', 'credit')])
    waiting_vat_account_ids = fields.One2many('account.vat.return.line', 'vat_return_id', string='VAT waiting', domain=[('line_type', '=', 'vat_waiting')])
    sale_account_ids = fields.One2many('account.vat.return.line', 'vat_return_id', string='Sale accounts', domain=[('line_type', '=', 'sale')])
    purchase_account_ids = fields.One2many('account.vat.return.line', 'vat_return_id', string='Purchase accounts', domain=[('line_type', '=', 'purchase')])
    period_id = fields.Many2one('account.period', 'Period', required=True, readonly=False, default=_default_period_id, states=_get_states)
    validation_journal_id = fields.Many2one('account.journal', 'Journal', required=True, readonly=False, domain=[('type', '=', 'general')], states=_get_states)
    payment_journal_id = fields.Many2one('account.journal', 'Journal', required=True, readonly=False, domain=[('type', 'in', ('bank', 'cash'))], states=_get_states)
    company_id = fields.Many2one('res.company', string='Company', required=True, ondelete='restrict', default=lambda self: self.env.user.company_id, states=_get_states)
    validation_move_id = fields.Many2one('account.move', string='Validation account move', required=False, ondelete='set null', copy=False)
    validation_date = fields.Date(copy=False)
    payment_move_id = fields.Many2one('account.move', string='Payment account move', required=False, ondelete='set null', copy=False)
    payment_date = fields.Date(copy=False)
    payment_amount = fields.Float(string='Amount', default=0.0, required=False, copy=False)
    theorical_amount = fields.Float(default=0.0, required=False, readonly=True)
    state = fields.Selection('_state_get', default='draft')
    payment_id = fields.Many2one('account.voucher', string='Payment', required=False, ondelete='restrict')
    draft_purchase_amount = fields.Float(string='Draft purchase invoice amount', default=0.0, required=False, copy=False, readonly=True)
    draft_sale_amount = fields.Float(string='Draft sale invoice amount', default=0.0, required=False, copy=False, readonly=True)
    
    
    def get_amount(self, account_rs, amount_type):
        move_line_obj = self.env['account.move.line']
        args = [('account_id', '=', account_rs.id), ('move_id.state', '=', 'posted'), ('journal_id.type', '!=', 'situation'), ('reconcile_id', '=', False)]
        if self.start_date:
            args.append(('date', '>=', self.start_date))
            
        if self.end_date:
            args.append(('date', '<=', self.end_date))
        
        move_line_datas = move_line_obj.search_group(fields=['debit', 'credit'],
                                                     groupby=['account_id'],
                                                     args=args,
                                                     sum=['debit', 'credit'],
                                                     return_dict=True,
                                                     without_order=True)
        move_line_ids = move_line_obj.search(args)
        res = 0.0
        if move_line_datas:
            for move_line_data in move_line_datas:
                if amount_type == 1:
                    res += move_line_data['debit'] - move_line_data['credit']
                else:
                    res += move_line_data['credit'] - move_line_data['debit']
        
        return (res, move_line_ids.ids)
        
    
    @api.multi
    def compute(self):
        inv_obj = self.env['account.invoice']
        move_obj = self.env['account.move.line']
        self.env['account.vat.return.line'].search([('vat_return_id', 'in', self.ids)]).unlink()
        fields_to_process =  [('debit_vat_account_ids', 'debit', 1),
                              ('credit_vat_account_ids', 'credit', 2),
                              ('sale_account_ids', 'sale', 2),
                              ('purchase_account_ids', 'purchase', 1)]
        line_obj = self.env['account.vat.return.line']
        for vat_return in self:
            debit = 0.0
            credit = 0.0
            theorical_amount = 0.0
            account_ids = []
            for field, line_type, amount_type in fields_to_process:
                for account_rs in vat_return.template_id[field]:
                    account_ids.append(account_rs.id)
                    amount, line_ids = vat_return.get_amount(account_rs, amount_type)
                    if amount_type == 1:
                        debit += amount
                        if line_type == 'debit':
                            theorical_amount -= amount
                    else:
                        credit += amount
                        if line_type == 'credit':
                            theorical_amount += amount
                        
                    line_obj.create({'vat_return_id': vat_return.id,
                                     'amount': amount,
                                     'line_type': line_type,
                                     'account_id': account_rs.id,
                                     'move_line_ids': [(6, 0, line_ids)]})
            
            if len(account_ids) != len(list(set(account_ids))):
                raise ValidationError(_('Impossible to have twice the same account'))
            
            args = []
            if self.start_date:
                args.append(('date_invoice', '>=', self.start_date))
                
            if self.end_date:
                args.append(('date_invoice', '<=', self.end_date))   
            
            draft_args = args + [('state', '=', 'draft')]
            out_invoice_sum = inv_obj.search_group(fields=['amount_total'], 
                                                   groupby=[], 
                                                   args=draft_args + [('type', '=', 'out_invoice')],
                                                   sum='amount_total',
                                                   return_dict=True,
                                                   without_order=True)
            in_invoice_sum = inv_obj.search_group(fields=['amount_total'], 
                                                   groupby=[], 
                                                   args=draft_args + [('type', '=', 'in_invoice')],
                                                   sum='amount_total',
                                                   return_dict=True,
                                                   without_order=True)
            
            tax_account_rs = vat_return.template_id.waiting_vat_account_ids
            tax_account_ids = tax_account_rs.ids
            account_line_dict = {}
            for waiting_vat_account_rs in tax_account_rs:
                account_line_dict[waiting_vat_account_rs.id] = {'vat_return_id': vat_return.id,
                                                                'amount': 0.0,
                                                                'line_type': 'vat_waiting',
                                                                'account_id': waiting_vat_account_rs.id,
                                                                'move_line_ids': [(6, 0, [])]}
            for inv_rs in inv_obj.search(args + [('state', 'not in', ('draft', 'cancel'))]):
                if inv_rs.move_id:
                    factor = (inv_rs.amount_total - inv_rs.residual) / inv_rs.amount_total
                    for move_line_rs in inv_rs.move_id.line_id:
                        if move_line_rs.account_id.id in tax_account_ids:
                            amount = move_line_rs.credit or move_line_rs.debit
                            account_line_dict[move_line_rs.account_id.id]['amount'] += amount - ((move_line_rs.credit or move_line_rs.debit) * factor)
                            account_line_dict[move_line_rs.account_id.id]['move_line_ids'][0][-1].append(move_line_rs.id)        
#             
# #             inv_rs = inv_obj.search(args + [('state', 'not in', ('draft', 'cancel'))])
# #                 inv_dict = {x.id: x for x in inv_rs}
#             inv_move_dict = {}
#             for move_rs in move_obj.search([('reconcile_partial_id', '!=', False)]):
#                 if move_rs.reconcile_partial_id:
#                     if move_rs.invoice in inv_move_dict:
#                         inv_move_dict[move_rs.reconcile_partial_id] += move_rs.credit - move_rs.debit 
#                     else:
#                         inv_move_dict[move_rs.reconcile_partial_id] = move_rs.credit - move_rs.debit
#             
#             from pprint import pprint
#             pprint(inv_move_dict)
#             for invoice_rs, move_amount in inv_move_dict.iteritems():
#                 if invoice_rs.amount_total and move_amount:
#                     invoice_factor = move_amount / invoice_rs.amount_total
#                     for move_rs in invoice_rs.move_id.line_id:
#                         if move_rs.account_id.id in tax_account_ids:
#                             account_line_dict[move_rs.account_id.id]['amount'] += (move_rs.credit or move_rs.debit) * invoice_factor
#                             account_line_dict[move_rs.account_id.id]['move_line_ids'][0][-1].append(move_rs.id)
            
            for line_datas in account_line_dict.values():
                line_obj.create(line_datas)
                
            vat_return.write({'debit': debit, 
                              'credit': credit, 
                              'theorical_amount': theorical_amount, 
                              'draft_purchase_amount': in_invoice_sum and in_invoice_sum[0]['amount_total'] or 0.0, 
                              'draft_sale_amount': out_invoice_sum and out_invoice_sum[0]['amount_total'] or 0.0})

            
    @api.multi
    def cancel_validation(self):
        move_line_obj = self.env['account.move.line']
        for vat_return_rs in self:
            if vat_return_rs.validation_move_id:
                move_line_to_unreconcile = self.env['account.move.line']
                for move_line in vat_return_rs.validation_move_id.line_id:
                    if move_line and move_line not in move_line_to_unreconcile:
                        move_line_to_unreconcile |= move_line_obj.search([('reconcile_id', '=', move_line.reconcile_id.id)])
                
                if move_line_to_unreconcile:
                    move_line_to_unreconcile._remove_move_reconcile(move_ids=move_line_to_unreconcile.ids)
                            
                vat_return_rs.validation_move_id.button_cancel()
                vat_return_rs.validation_move_id.unlink()
                 
        self.write({'state': 'draft', 'validation_date': False, 'validation_move_id': False})
            
            
    @api.multi
    def validate(self):
        today = fields.Date.today()
        move_obj = self.env['account.move']
        invoice_obj = self.env['account.invoice']
        line_obj = self.env['account.vat.return.line']
        for vat_return_rs in self:
            res = []
            total_amount = 0.0
            to_reconcile_dict = {}
            for line_rs in line_obj.search([('vat_return_id', '=', vat_return_rs.id), ('line_type', 'in', ('debit', 'credit'))]):
                if line_rs.account_id.reconcile:
                    if line_rs.account_id.id in to_reconcile_dict:
                        to_reconcile_dict[line_rs.account_id.id] |= line_rs.move_line_ids
                    else:
                        to_reconcile_dict[line_rs.account_id.id] = line_rs.move_line_ids
                    
                if line_rs.line_type == 'credit':
                    factor = 1
                else:
                    factor = -1
                    
                if line_rs.amount:
                    amount = (-line_rs.amount or 0.0) * factor
                    res.append({
                        'type': 'tax',
                        'name': vat_return_rs.name,
                        'price_unit': amount,
                        'quantity': 1,
                        'price': -amount,
                        'account_id': line_rs.account_id.id})
                    total_amount += amount
                
            if res:
                res.append({
                    'type': 'tax',
                    'name': vat_return_rs.name,
                    'price_unit': total_amount,
                    'quantity': 1,
                    'price': total_amount,
                    'account_id': vat_return_rs.partner_id.property_account_payable_id.id})
                date_invoice = today
                ctx = dict(self._context, lang=vat_return_rs.partner_id.lang)
                ctx['date'] = date_invoice
                line = [(0, 0, invoice_obj.line_get_convert(l, vat_return_rs.partner_id.id, date_invoice)) for l in res]
                move_vals = {
                    'line_id': line,
                    'journal_id': vat_return_rs.validation_journal_id.id,
                    'date': today,
                    'company_id': vat_return_rs.company_id.id,
                    'period_id': vat_return_rs.period_id.id}
                move_rs = move_obj.create(move_vals)
                if move_rs:
                    vat_return_rs.with_context(ctx).write({'validation_move_id': move_rs.id, 'validation_date': today, 'state': 'progress'})
                    move_rs.post()
                    for move_line_rs in move_rs.line_id:
                        if move_line_rs.account_id.id != vat_return_rs.partner_id.property_account_payable_id.id and \
                           move_line_rs.account_id.reconcile:
                            if move_line_rs.account_id.id in to_reconcile_dict:
                                to_reconcile_dict[move_line_rs.account_id.id] |= move_line_rs
                            else:
                                to_reconcile_dict[move_line_rs.account_id.id] = move_line_rs

                    for move_line_to_reconcile_rs in to_reconcile_dict.values():
                        if move_line_to_reconcile_rs:
                            move_line_to_reconcile_rs.reconcile()
                
        return True
        
            
    @api.multi
    def cancel_payment(self):
        for vat_return_rs in self:
            if vat_return_rs.payment_id:
                payment_id = vat_return_rs.payment_id
                vat_return_rs.write({'state': 'progress', 'payment_date': False, 'payment_move_id': False, 'payment_id': False})
                ctx = self.env.context.copy()
                ctx.update({'vat_payement_cancel': True})
                payment_id.with_context(ctx).cancel_voucher()
                payment_id.unlink()
            
        
    @api.multi
    def payment(self):
        payment_obj = self.env['account.voucher']
        move_obj = self.env['account.move']
        for vat_return_rs in self:
            payment_rs = payment_obj.create({'partner_id': vat_return_rs.partner_id.id,
                                             'amount': vat_return_rs.payment_amount,
                                             'period_id': vat_return_rs.period_id.id,
                                             'journal_id': vat_return_rs.payment_journal_id.id,
                                             'type': 'payment',
                                             'account_id': vat_return_rs.payment_journal_id.default_credit_account_id.id,
                                             'date': fields.Date.today()})
            if payment_rs:
                payment_rs.signal_workflow('proforma_voucher')
                vals = {'payment_date': fields.Date.today(), 'state': 'done', 'payment_id': payment_rs.id}
                move_rs = move_obj.search([('voucher_id', '=', payment_rs.id)], limit=1)
                if move_rs:
                    vals['payment_move_id'] = move_rs.id
                    
                vat_return_rs.write(vals)
            
        

class account_vat_return_line(models.Model):
    """ 
    Account VAT return line
    """
    _name = 'account.vat.return.line'
    _description = 'Account VAT return line'

    
    @api.model
    def _line_type_get(self):
        return [
            ('debit', 'Debit'),
            ('credit', 'Credit'),
            ('sale', 'Sale'),
            ('purchase', 'Purchase'),
            ('vat_waiting', 'VAT waiting'),
               ]
    

    #===========================================================================
    # COLUMNS
    #===========================================================================
    vat_return_id = fields.Many2one('account.vat.return', string='VAT return', required=True, ondelete='cascade')
    account_id = fields.Many2one('account.account', string='Account', domain=[])
    amount = fields.Float(default=0.0, required=False)
    line_type = fields.Selection('_line_type_get', string='Type')
    move_line_ids = fields.Many2many('account.move.line', 'vat_return_line_move_line_rel', 'vat_return_line_id', 'move_line_id', string='Move lines')

    


class account_account(models.Model):
    _inherit = 'account.account'
    
    
    def method_see_entries(self, domain=False):
        """
            Fonction qui retourne les écritures comptables liées à un compte. 
            On peut forcer le domaine avec le paramètre domain
        """
        action_struc = {}
        action_dict = get_form_view(self, 'account.action_account_moves_all_a')
        account_id = self.id
        if action_dict and action_dict.get('id') and action_dict.get('type'):
            action = self.env[action_dict['type']].browse(action_dict['id'])
            action_struc = action.read()
            action_struc[0]['domain'] = [('journal_id.type', '!=', 'situation'), ('account_id', '=', account_id)]
            if domain and isinstance(domain, list):
                action_struc[0]['domain'].extend(domain)
                
            action_struc = action_struc[0]
              
        return action_struc
    
    
    @api.multi
    def see_entries(self):
        """
            Vue des écritures du compte
        """
        return self.method_see_entries(False)
    
    
    @api.multi
    def see_unreconcile_entries(self):
        """
            Vue des écritures non lettrées du compte
        """
        action_struc = True
        if self.reconcile:
            action_struc = self.method_see_entries(domain=[('reconcile_id', '=', False)])
            
        return action_struc
    
    