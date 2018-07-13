# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp.osv import fields, osv
from openerp import api
from openerp.tools.translate import _

class account_account_type(osv.osv):
    _inherit="account.account.type"
    _columns = {
        'code': fields.char('Code'),
        'close_method': fields.selection(
            [('none', 'None'), ('balance', 'Balance'), ('detail', 'Detail'), ('unreconciled', 'Unreconciled')],
            'Deferral Method', required=True, help="""Set here the method that will be used to generate the end of year journal entries for all the accounts of this type.

     'None' means that nothing will be done.
     'Balance' will generally be used for cash accounts.
     'Detail' will copy each existing journal item of the previous year, even the reconciled ones.
     'Unreconciled' will copy only the journal items that were unreconciled on the first day of the new fiscal year."""),
    }
    _defaults = {
        'close_method': 'none',
    }
account_account_type()

class account_account(osv.osv):
    _inherit="account.account"

    @api.onchange('user_type')
    def change_close(self):
        self.close_method = self.user_type.close_method

    _columns = {
        'user_type': fields.many2one('account.account.type', 'Account Type', required=True),
    }

    def __compute_init(self, cr, uid, ids, field_names, arg=None, context=None,
                  query='', query_params=()):
        """ compute the balance, debit and/or credit for the provided
        account ids
        Arguments:
        `ids`: account ids
        `field_names`: the fields to compute (a list of any of
                       'balance', 'debit' and 'credit')
        `arg`: unused fields.function stuff
        `query`: additional query filter (as a string)
        `query_params`: parameters for the provided query string
                        (__compute will handle their escaping) as a
                        tuple
        """
        mapping = {
            'balance': "COALESCE(SUM(l.debit),0) - COALESCE(SUM(l.credit), 0) as balance",
            'debit': "COALESCE(SUM(l.debit), 0) as debit",
            'credit': "COALESCE(SUM(l.credit), 0) as credit",
            # by convention, foreign_balance is 0 when the account has no secondary currency, because the amounts may be in different currencies
            'foreign_balance': "(SELECT CASE WHEN currency_id IS NULL THEN 0 ELSE COALESCE(SUM(l.amount_currency), 0) END FROM account_account WHERE id IN (l.account_id)) as foreign_balance",
        }
        #get all the necessary accounts
        children_and_consolidated = self._get_children(cr, uid, ids, context=context)
        #compute for each account the balance/debit/credit from the move lines
        accounts = {}
        res = {}
        null_result = dict((fn, 0.0) for fn in field_names)
        if children_and_consolidated:
            aml_query = self.pool.get('account.move.line')._query_get(cr, uid, context=context)

            wheres = [""]
            if query.strip():
                wheres.append(query.strip())
            if aml_query.strip():
                wheres.append(aml_query.strip())
            filters = " AND ".join(wheres)
            # IN might not work ideally in case there are too many
            # children_and_consolidated, in that case join on a
            # values() e.g.:
            # SELECT l.account_id as id FROM account_move_line l
            # INNER JOIN (VALUES (id1), (id2), (id3), ...) AS tmp (id)
            # ON l.account_id = tmp.id
            # or make _get_children_and_consol return a query and join on that
            request = ("SELECT l.account_id as id, " +\
                       ', '.join(map(mapping.__getitem__, field_names)) +
                       " FROM account_move_line l,account_journal aj" \
                       " WHERE l.account_id IN %s " \
                            + filters +
                       " GROUP BY l.account_id")
            params = (tuple(children_and_consolidated),) + query_params
            cr.execute(request, params)

            for row in cr.dictfetchall():
                accounts[row['id']] = row

            # consolidate accounts with direct children
            children_and_consolidated.reverse()
            brs = list(self.browse(cr, uid, children_and_consolidated, context=context))
            sums = {}
            currency_obj = self.pool.get('res.currency')
            while brs:
                current = brs.pop(0)
#                can_compute = True
#                for child in current.child_id:
#                    if child.id not in sums:
#                        can_compute = False
#                        try:
#                            brs.insert(0, brs.pop(brs.index(child)))
#                        except ValueError:
#                            brs.insert(0, child)
#                if can_compute:
                for fn in field_names:
                    sums.setdefault(current.id, {})[fn] = accounts.get(current.id, {}).get(fn, 0.0)
                    for child in current.child_id:
                        if child.company_id.currency_id.id == current.company_id.currency_id.id:
                            sums[current.id][fn] += sums[child.id][fn]
                        else:
                            sums[current.id][fn] += currency_obj.compute(cr, uid, child.company_id.currency_id.id, current.company_id.currency_id.id, sums[child.id][fn], context=context)

                # as we have to relay on values computed before this is calculated separately than previous fields
                if current.currency_id and current.exchange_rate and \
                            ('adjusted_balance' in field_names or 'unrealized_gain_loss' in field_names):
                    # Computing Adjusted Balance and Unrealized Gains and losses
                    # Adjusted Balance = Foreign Balance / Exchange Rate
                    # Unrealized Gains and losses = Adjusted Balance - Balance
                    adj_bal = sums[current.id].get('foreign_balance', 0.0) / current.exchange_rate
                    sums[current.id].update({'adjusted_balance': adj_bal, 'unrealized_gain_loss': adj_bal - sums[current.id].get('balance', 0.0)})

            for id in ids:
                res[id] = sums.get(id, null_result)
        else:
            for id in ids:
                res[id] = null_result
        return res


account_account()


class account_account_template(osv.osv):
    _inherit = "account.account.template"

    @api.onchange('user_type')
    def change_close(self):
        self.close_method = self.user_type.close_method

    _columns = {
        'user_type': fields.many2one('account.account.type', 'Account Type', required=True),
    }
    def generate_account(self, cr, uid, chart_template_id, tax_template_ref, acc_template_ref, code_digits, company_id, context=None):
        """
        This method for generating accounts from templates.

        :param chart_template_id: id of the chart template chosen in the wizard
        :param tax_template_ref: Taxes templates reference for write taxes_id in account_account.
        :paramacc_template_ref: dictionary with the mappping between the account templates and the real accounts.
        :param code_digits: number of digits got from wizard.multi.charts.accounts, this is use for account code.
        :param company_id: company_id selected from wizard.multi.charts.accounts.
        :returns: return acc_template_ref for reference purpose.
        :rtype: dict
        """
        if context is None:
            context = {}
        obj_acc = self.pool.get('account.account')
        company_name = self.pool.get('res.company').browse(cr, uid, company_id, context=context).name
        template = self.pool.get('account.chart.template').browse(cr, uid, chart_template_id, context=context)
        #deactivate the parent_store functionnality on account_account for rapidity purpose
        ctx = context.copy()
        ctx.update({'defer_parent_store_computation': True})
        level_ref = {}
        children_acc_criteria = [('chart_template_id','=', chart_template_id)]
        if template.account_root_id.id:
            children_acc_criteria = ['|'] + children_acc_criteria + ['&',('parent_id','child_of', [template.account_root_id.id]),('chart_template_id','=', False)]
        children_acc_template = self.search(cr, uid, [('nocreate','!=',True)] + children_acc_criteria, order='id')
        for account_template in self.browse(cr, uid, children_acc_template, context=context):
            # skip the root of COA if it's not the main one
            if (template.account_root_id.id == account_template.id) and template.parent_id:
                continue
            tax_ids = []
            for tax in account_template.tax_ids:
                tax_ids.append(tax_template_ref[tax.id])

            code_main = account_template.code and len(account_template.code) or 0
            code_acc = account_template.code or ''
            if code_main > 0 and code_main <= code_digits and account_template.type != 'view':
                code_acc = str(code_acc) + (str('0'*(code_digits-code_main)))
            parent_id = account_template.parent_id and ((account_template.parent_id.id in acc_template_ref) and acc_template_ref[account_template.parent_id.id]) or False
            #the level as to be given as well at the creation time, because of the defer_parent_store_computation in
            #context. Indeed because of this, the parent_left and parent_right are not computed and thus the child_of
            #operator does not return the expected values, with result of having the level field not computed at all.
            if parent_id:
                level = parent_id in level_ref and level_ref[parent_id] + 1 or obj_acc._get_level(cr, uid, [parent_id], 'level', None, context=context)[parent_id] + 1
            else:
                level = 0
            vals={
                'name': (template.account_root_id.id == account_template.id) and company_name or account_template.name,
                'currency_id': account_template.currency_id and account_template.currency_id.id or False,
                'code': code_acc,
                'type': account_template.type,
                'reconcile': account_template.reconcile,
                'shortcut': account_template.shortcut,
                'note': account_template.note,
                'financial_report_ids': account_template.financial_report_ids and [(6,0,[x.id for x in account_template.financial_report_ids])] or False,
                'parent_id': parent_id,
                'tax_ids': [(6,0,tax_ids)],
                'company_id': company_id,
                'user_type': account_template.user_type and account_template.user_type.id or False,
                'close_method': account_template.close_method or 'none',
                'level': level,
            }
            new_account = obj_acc.create(cr, uid, vals, context=ctx)
            acc_template_ref[account_template.id] = new_account
            level_ref[new_account] = level

        #reactivate the parent_store functionnality on account_account
        obj_acc._parent_store_compute(cr)
        return acc_template_ref
account_account_template()

class account_add_tmpl_wizard(osv.osv_memory):
    _inherit = 'account.addtmpl.wizard'

    def action_create(self,cr,uid,ids,context=None):
        if context is None:
            context = {}
        acc_obj = self.pool.get('account.account')
        tmpl_obj = self.pool.get('account.account.template')
        data = self.read(cr, uid, ids)[0]
        company_id = acc_obj.read(cr, uid, [data['cparent_id'][0]], ['company_id'])[0]['company_id'][0]
        account_template = tmpl_obj.browse(cr, uid, context['tmpl_ids'])
        vals = {
            'name': account_template.name,
            'currency_id': account_template.currency_id and account_template.currency_id.id or False,
            'code': account_template.code,
            'type': account_template.type,
            'user_type': account_template.user_type and account_template.user_type.id or False,
            'reconcile': account_template.reconcile,
            'shortcut': account_template.shortcut,
            'note': account_template.note,
            'parent_id': data['cparent_id'][0],
            'company_id': company_id,
            }
        acc_obj.create(cr, uid, vals)
        return {'type':'state', 'state': 'end' }
account_add_tmpl_wizard()

class wizard_multi_charts_accounts(osv.osv_memory):
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
            ('property_account_receivable_id', 'res.partner', 'account.account'),
            ('property_account_payable_id', 'res.partner', 'account.account'),
            ('property_account_expense_categ_id', 'product.category', 'account.account'),
            ('property_account_income_categ_id', 'product.category', 'account.account'),
            ('property_account_expense', 'product.product', 'account.account'),
            ('property_account_income', 'product.product', 'account.account'),
        ]
        template = self.pool.get('account.chart.template').browse(cr, uid, chart_template_id, context=context)
        for record in todo_list:
            account = getattr(template, record[0])
            value = account and 'account.account,' + str(acc_template_ref[account.id]) or False
            if value:
                field = field_obj.search(cr, uid, [('name', '=', record[0]), ('model', '=', record[1]),
                                                   ('relation', '=', record[2])], context=context)
                if field :
                    vals = {
                        'name': record[0],
                        'company_id': company_id,
                        'fields_id': field[0],
                        'value': value,
                    }
                    property_ids = property_obj.search(cr, uid, [('name', '=', record[0]), ('company_id', '=', company_id)],
                                                       context=context)
                    if property_ids:
                        # the property exist: modify it
                        property_obj.write(cr, uid, property_ids, vals, context=context)
                    else:
                        # create the property
                        property_obj.create(cr, uid, vals, context=context)
        return True

    def _prepare_bank_account(self, cr, uid, line, new_code, acc_template_ref, ref_acc_bank, company_id, context=None):
        '''
        This function prepares the value to use for the creation of the default debit and credit accounts of a
        bank journal created through the wizard of generating COA from templates.

        :param line: dictionary containing the values encoded by the user related to his bank account
        :param new_code: integer corresponding to the next available number to use as account code
        :param acc_template_ref: the dictionary containing the mapping between the ids of account templates and the ids
            of the accounts that have been generated from them.
        :param ref_acc_bank: browse record of the account template set as root of all bank accounts for the chosen
            template
        :param company_id: id of the company for which the wizard is running
        :return: mapping of field names and values
        :rtype: dict
        '''
        data_obj = self.pool.get('ir.model.data')
        vals = {'name': line['acc_name'],
                'currency_id': line['currency_id'],
                'code': new_code,
                'type': 'liquidity',
                'parent_id': acc_template_ref[ref_acc_bank.id] or False,
                'close_method': 'balance',
                'company_id': company_id}
        # Recherche du type de compte "Disponibilité"
        object_model, object_id = data_obj.get_object_reference(cr, uid, 'account', 'data_account_type_cash_flow')
        if object_model and object_model == 'account.account.type':
            vals['user_type'] = object_id
        return vals
wizard_multi_charts_accounts()

class res_partner(osv.osv):
    _inherit = 'res.partner'
    _columns = {
        'currency_id': fields.many2one('res.currency', string='Currency', required=True, ondelete='restrict',
                                  default=lambda self: self.env.ref('base.MAD'), readonly=False, compute=False),
        'siret_number' : fields.char(string='Registre de commerce', size=32, required=False),
        'ice_number' : fields.char(string='ICE', size=32, required=False),
        'capital' : fields.char(string='Capital', size=32, required=False),
        'rc' : fields.char(string='R.C.', size=32, required=False),
        'patente' : fields.char(string='Patente', size=32, required=False),
        'cnss' : fields.char(string='CNSS', size=32, required=False),
        'num_if' : fields.char(string='N° IF', size=32, required=False),
    }
res_partner()