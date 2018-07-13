# -*- encoding: utf-8 -*-

from openerp import models, fields, api, _, exceptions
import openerp.addons.decimal_precision as dp
from datetime import datetime
from openerp.osv import orm
from openerp.tools import float_compare
from openerp.exceptions import except_orm, Warning, RedirectWarning


class account_invoice(models.Model):
    _inherit = "account.invoice"

    invoice_id = fields.Many2one(comodel_name="account.invoice", string="Facture", required=False, )

    #MZ###############################################

    commercial_partner_id = fields.Many2one('res.partner', string='Commercial Entity',
                                            related='partner_id.commercial_partner_id', store=True, readonly=True,
                                            help="The commercial entity that will be used on Journal Entries for this invoice")
    @api.multi
    def check_tax_lines(self, compute_taxes):
        account_invoice_tax = self.env['account.invoice.tax']
        company_currency = self.company_id.currency_id
        if not self.tax_line_ids:
            for tax in compute_taxes.values():
                account_invoice_tax.create(tax)
        else:
            tax_key = []
            precision = self.env['decimal.precision'].precision_get('Account')
            for tax in self.tax_line_ids:
                if tax.manual:
                    continue
                key = (tax.tax_code_id.id, tax.base_code_id.id, tax.account_id.id)
                tax_key.append(key)
                if key not in compute_taxes:
                    raise except_orm(_('Warning!'), _('Global taxes defined, but they are not in invoice lines !'))
                base = compute_taxes[key]['base']
                if tax.base == None:
                    tax.base = 0
                if float_compare(abs(base - tax.base), company_currency.rounding, precision_digits=precision) == 1:
                    raise except_orm(_('Warning!'), _('Tax base different!\nClick on compute to update the tax base.'))
            for key in compute_taxes:
                if key not in tax_key:
                    raise except_orm(_('Warning!'), _('Taxes are missing!\nClick on compute button.'))
    ########################################################

    @api.multi
    def action_move_create(self):
      '''Check that products with must_have_dates=True have
      Start and End Dates'''
      # for invoice in self.browse(self.ids):
      #     for invline in invoice.invoice_line:
      #         if invline.product_id and invline.product_id.must_have_dates:
      #            if not invline.start_date or not invline.end_date:
      #               raise orm.except_orm(
      #                   _('Error:'),
      #                   _("Missing Start Date and End Date for invoice "
      #                       "line with Product '%s' which has the "
      #                       "property 'Must Have Start and End Dates'.")
      #                   % (invline.product_id.name))

      """ Creates invoice related analytics and financial move lines """
      account_invoice_tax = self.env['account.invoice.tax']
      account_move = self.env['account.move']

      for inv in self:
          if not inv.journal_id.sequence_id:
            raise except_orm(_('Error!'), _('Please define sequence on the journal related to this invoice.'))
          if not inv.invoice_line_ids:
             raise except_orm(_('No Invoice Lines!'), _('Please create some invoice lines.'))
          if inv.move_id:
             continue

          ctx = dict(self._context, lang=inv.partner_id.lang)

          if not inv.date_invoice:
             inv.with_context(ctx).write({'date_invoice': fields.date.today()})
          date_invoice = inv.date_invoice

          company_currency = inv.company_id.currency_id
          # create the analytical lines, one move line per invoice line
          iml = inv._get_analytic_lines()
          # check if taxes are all computed
          compute_taxes = account_invoice_tax.compute(inv.with_context(lang=inv.partner_id.lang))
          #inv.check_tax_lines(compute_taxes)

          # I disabled the check_total feature
          #MZ######################
          self.button_compute(True)
          if self.env['res.users'].has_group('account.group_supplier_inv_check_total'):
             if inv.type in ('in_invoice', 'in_refund') and abs(inv.check_total - inv.amount_total) >= (inv.currency_id.rounding / 2.0):
                raise except_orm(_('Bad Total!'), _('Please verify the price of the invoice!\nThe encoded total does not match the computed total.'))

          if inv.payment_term_id:
             total_fixed = total_percent = 0
             for line in inv.payment_term_id.line_ids:
                 if line.value == 'fixed':
                    total_fixed += line.value_amount
                 if line.value == 'procent':
                    total_percent += line.value_amount
             total_fixed = (total_fixed * 100) / (inv.amount_total or 1.0)
             if (total_fixed + total_percent) > 100:
                raise except_orm(_('Error!'), _("Cannot create the invoice.\nThe related payment term is probably misconfigured as it gives a computed amount greater than the total invoiced amount. In order to avoid rounding issues, the latest line of your payment term must be of type 'balance'."))

          # one move line per tax line
          iml += account_invoice_tax.move_line_get(inv.id)

          if inv.type in ('in_invoice', 'in_refund'):
             ref = inv.reference
          else:
             ref = inv.number

          diff_currency = inv.currency_id != company_currency
          # create one move line for the total and possibly adjust the other lines amount
          total, total_currency, iml = inv.with_context(ctx).compute_invoice_totals(company_currency, ref, iml)

          name = inv.supplier_invoice_number or inv.name or '/'
          totlines = []
          if inv.payment_term_id:
             totlines = inv.with_context(ctx).payment_term_id.compute(total, date_invoice)[0]
          if totlines:
             res_amount_currency = total_currency
             ctx['date'] = date_invoice
             for i, t in enumerate(totlines):
                 if inv.currency_id != company_currency:
                    amount_currency = company_currency.with_context(ctx).compute(t[1], inv.currency_id)
                 else:
                    amount_currency = False

                 # last line: add the diff
                 res_amount_currency -= amount_currency or 0
                 if i + 1 == len(totlines):
                    amount_currency += res_amount_currency

                 iml.append({
                    'type': 'dest',
                    'name': name,
                    'price': t[1],
                    'account_id': inv.account_id.id,
                    'date_maturity': t[0],
#                    'date_treasury':inv.prevision_date,
                    'amount_currency': diff_currency and amount_currency,
                    'currency_id': diff_currency and inv.currency_id.id,
                    'ref': ref,
                 })
          else:
            iml.append({
                'type': 'dest',
                'name': name,
                'price': total,
                'account_id': inv.account_id.id,
                'date_maturity': inv.date_due,
#                'date_treasury':inv.prevision_date,
                'amount_currency': diff_currency and total_currency,
                'currency_id': diff_currency and inv.currency_id.id,
                'ref': ref
            })
          print 'rrrrrrrr',iml
          date = date_invoice

          part = self.env['res.partner']._find_accounting_partner(inv.partner_id)

          line = [(0, 0, self.line_get_convert(l, part.id, date)) for l in iml]
          line = inv.group_lines(iml, line)

          journal = inv.journal_id.with_context(ctx)
          if journal.centralisation:
             raise except_orm(_('User Error!'),
                    _('You cannot create an invoice on a centralized journal. Uncheck the centralized counterpart box in the related journal from the configuration menu.'))

          line = inv.finalize_invoice_move_lines(line)

          move_vals = {
            'ref': inv.reference or inv.name,
            'line_id': line,
            'journal_id': journal.id,
            'date': inv.date_invoice,
            'narration': inv.comment,
#            'date_treasury':inv.prevision_date,
            'company_id': inv.company_id.id,
          }
          ctx['company_id'] = inv.company_id.id
          period = inv.period_id
          if not period:
             period = period.with_context(ctx).find(date_invoice)[:1]
          if period:
             move_vals['period_id'] = period.id
             for i in line:
                 i[2]['period_id'] = period.id

          ctx['invoice'] = inv
          ctx_nolang = ctx.copy()
          ctx_nolang.pop('lang', None)
          move = account_move.with_context(ctx_nolang).create(move_vals)
          #invoice ref to account move
          move.write({'invoice_id':inv.id})
          #invoice ref to account move


          # make the invoice point to that move
          vals = {
            'move_id': move.id,
            'period_id': period.id,
            'move_name': move.name,
          }
          inv.with_context(ctx).write(vals)
          # Pass invoice in context in method post: used if you want to get the same
          # account move reference when creating the same invoice after a cancelled one:
          move.post()
      self._log_event()
      return True
      # return super(account_invoice, self).action_move_create(
      #   cr, uid, ids, context=context)

account_invoice()

from openerp.osv import osv, fields
class res_partner(osv.Model):
    # Inherits partner and adds invoice information in the partner form
    _inherit = 'res.partner'
    #MZ######################
    #invoice_ids = fields.One2many('account.invoice', 'partner_id', string='Invoices',
     #   readonly=True, copy=False)

    def _commercial_partner_compute(self, cr, uid, ids, name, args, context=None):
        """ Returns the partner that is considered the commercial
        entity of this partner. The commercial entity holds the master data
        for all commercial fields (see :py:meth:`~_commercial_fields`) """
        result = dict.fromkeys(ids, False)
        for partner in self.browse(cr, uid, ids, context=context):
            current_partner = partner
            while not current_partner.is_company and current_partner.parent_id:
                current_partner = current_partner.parent_id
            result[partner.id] = current_partner.id
        return result

    _commercial_partner_id = lambda self, *args, **kwargs: self._commercial_partner_compute(*args, **kwargs)

    _commercial_partner_store_triggers = {
        'res.partner': (lambda self, cr, uid, ids, context=None: self.search(cr, uid, [('id', 'child_of', ids)],
                                                                             context=dict(active_test=False)),
                        ['parent_id', 'is_company'], 10)
    }

    _columns = {
    'invoice_ids' : fields.one2many('account.invoice', 'partner_id', string='Invoices', readonly=True, copy=False),
    'commercial_partner_id': fields.function(_commercial_partner_id, type='many2one', relation='res.partner',
                                             string='Commercial Entity', store=_commercial_partner_store_triggers)
    }

    def _find_accounting_partner(self, partner):
        '''
        Find the partner for which the accounting entries will be created
        '''
        return partner.commercial_partner_id
