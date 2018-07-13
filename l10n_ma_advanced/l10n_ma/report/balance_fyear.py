# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#DT
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time,datetime as DT

from openerp.report import report_sxw
from common_report_header import common_report_header
from openerp.osv import orm

class balance_fyear(report_sxw.rml_parse, common_report_header):
    _name = 'report.balance.fyear'

    def __init__(self, cr, uid, name, context=None):
        super(balance_fyear, self).__init__(cr, uid, name, context=context)
        self.sum_debit = 0.00
        self.sum_credit = 0.00
        self.date_lst = []
        self.date_lst_string = ''
        self.result_acc = []
        self.localcontext.update({
            'time': time,
            'lines': self.lines,
            'sum_debit': self._sum_debit,
            'sum_credit': self._sum_credit,
            'get_fiscalyear':self._get_fiscalyear,
            'get_fiscalyear_prec':self._get_fiscalyear_prec,
            'get_filter': self._get_filter,
            'get_start_period': self.get_start_period,
            'get_end_period': self.get_end_period ,
            'get_account': self._get_account,
            'get_journal': self._get_journal,
            'get_start_date':self._get_start_date,
            'get_end_date':self._get_end_date,
            'get_target_move': self._get_target_move,
        })
        self.context = context
    def _get_fiscalyear_prec(self,data):
        return data['form']['fiscalyear_prec'][1]

    def set_context(self, objects, data, ids, report_type=None):
        new_ids = ids
        if (data['model'] == 'ir.ui.menu'):
            new_ids = 'chart_account_id' in data['form'] and [data['form']['chart_account_id']] or []
            objects = self.pool.get('account.account').browse(self.cr, self.uid, new_ids)
        return super(balance_fyear, self).set_context(objects, data, new_ids, report_type=report_type)

    #def _add_header(self, node, header=1):
    #    if header == 0:
    #        self.rml_header = ""
    #    return True

    def _get_account(self, data):
        if data['model']=='account.account':
            return self.pool.get('account.account').browse(self.cr, self.uid, data['form']['id']).company_id.name
        return super(balance_fyear ,self)._get_account(data)

    def lines(self, form, ids=None, done=None):
        def _process_child(accounts,form,disp_acc, parent,fyear_prec):
                account_rec = [acct for acct in accounts if acct['id']==parent][0]
                currency_obj = self.pool.get('res.currency')
                acc_id = self.pool.get('account.account').browse(self.cr, self.uid, account_rec['id'])
                currency = acc_id.currency_id and acc_id.currency_id or acc_id.company_id.currency_id
                l=len(fyear_prec.period_ids)
                tab=[]
                for p in fyear_prec.period_ids :
                    tab.append(p.id)
                DATETIME_FORMAT = "%Y-%m-%d"
                if form['filter']=="filter_no":
                    query="l.period_id in (%s)"%(tab[0])
                if form['filter']=='filter_period' :
                    
                    period_obj=self.pool.get("account.period")
                    month_from=DT.datetime.strptime(period_obj.browse(self.cr,self.uid,form['period_from']).date_start, DATETIME_FORMAT).month
                    month_to=DT.datetime.strptime(period_obj.browse(self.cr,self.uid,form['period_to']).date_start, DATETIME_FORMAT).month
                    for period in fyear_prec.period_ids :
                        if DT.datetime.strptime(period.date_start,DATETIME_FORMAT).month==month_from :
                            period_from=period.id
                        if DT.datetime.strptime(period.date_start,DATETIME_FORMAT).month==month_to :
                            period_to=period.id
                    if  (period_to and period_from) :
                        query="l.period_id between %s and %s"%(period_from,period_to)
                    else :
                        raise orm.except_orm(_('Configuration Error!'),
                     _('Types de periodes ne sont pas identiques pour les deux exercices.'))
                if form['filter']=='filter_date' : 
                   
                    #date_from=DT.datetime.strptime(form['date_from'],DATETIME_FORMAT).strftime(DATETIME_FORMAT)
                    #date_to=DT.datetime.strptime(form['date_to'],DATETIME_FORMAT).strftime(DATETIME_FORMAT)
                    #print "fffffffffffffffff",type(date_from),date_to
                    query="l.date>='%s'::date  and  l.date<='%s'::date and l.period_id in (%s) "%(form['date_from'],form['date_to'],tab[0])
                balance_init=self.pool.get('account.account')._account_account__compute(self.cr,self.uid,[acc_id.id],['balance'],None,None,query)
                res = {
                    'id': account_rec['id'],
                    'type': account_rec['type'],
                    'code': account_rec['code'],
                    'name': account_rec['name'],
                    'level': account_rec['level'],
                    'debit': account_rec['debit'],
                    'credit': account_rec['credit'],
                    #'balance': account_rec['balance'],
                    'balance_init':balance_init[ acc_id.id ]['balance'],
                    'parent_id': account_rec['parent_id'],
                    'bal_type': '',
                }

                if account_rec['code'][0] == '6' or account_rec['code'][0] == '7' :
                    res['balance'] = account_rec['balance']
                else :
                    res['balance'] = account_rec['balance']+balance_init[acc_id.id]['balance']

                self.sum_debit += account_rec['debit']
                self.sum_credit += account_rec['credit']
                condition=True
                if form['level_operator'] and form['level'] :
                    condition=eval( str(len(account_rec['code']))+str(form['level_operator'])+str(int(form['level'])) ) 
                #print "llllllllllllllllllllllllll",condition
                if disp_acc == 'movement' and condition :
                    if not currency_obj.is_zero(self.cr, self.uid, currency, res['credit']) or not currency_obj.is_zero(self.cr, self.uid, currency, res['debit']) or not currency_obj.is_zero(self.cr, self.uid, currency, res['balance']):
                        self.result_acc.append(res)
                elif disp_acc == 'not_zero' and condition :
                    if not currency_obj.is_zero(self.cr, self.uid, currency, res['balance']):
                        self.result_acc.append(res)
                else:
                    if condition :
                        self.result_acc.append(res)
                if account_rec['child_id'] :
                    for child in account_rec['child_id']:
                        _process_child(accounts,form,disp_acc,child,fyear_prec)

        obj_account = self.pool.get('account.account')
        if not ids:
            ids = self.ids
        if not ids:
            return []
        if not done:
            done={}

        ctx = self.context.copy()
        ctx['fiscalyear'] = form['fiscalyear_id']
        if form['filter'] == 'filter_period':
            ctx['period_from'] = form['period_from']
            ctx['period_to'] = form['period_to']
        elif form['filter'] == 'filter_date':
            ctx['date_from'] = form['date_from']
            ctx['date_to'] =  form['date_to']
        ctx['state'] = form['target_move']
        parents = ids
        child_ids = obj_account._get_children(self.cr, self.uid, ids, ctx)
        if child_ids:
            ids = child_ids
        accounts = obj_account.read(self.cr, self.uid, ids, ['type','code','name','debit','credit','balance','parent_id','level','child_id'], ctx)
        fisc_prec_obj=self.pool.get("account.fiscalyear").browse(self.cr,self.uid,form['fiscalyear_prec'][0])
        for parent in parents:
                if parent in done:
                    continue
                done[parent] = 1
                _process_child(accounts,form,form['display_account'],parent,fisc_prec_obj)
        return self.result_acc

report_sxw.report_sxw('report.balance.fyear', 'account.account', 'addons/l10n_ma/report/balance_fyear.rml', parser=balance_fyear, header="internal")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
