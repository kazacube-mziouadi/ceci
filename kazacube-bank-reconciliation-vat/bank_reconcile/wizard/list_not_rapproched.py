# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (http://tiny.be). All Rights Reserved
#    
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
######################################################################

from openerp.osv import osv,fields
from openerp.tools.translate import _
import time

class list_not_rapproched(osv.osv_memory):
    
    _name = 'list.not.rapproched'
    
   
    
    _columns = {
                'fiscalyear_id':fields.many2one('account.fiscalyear', 'Exercice comptable', required=True), 
                'bank_id':fields.many2one('res.bank','Banque',required=True),
                'period_id':fields.many2one('account.period','Periode',required=True,domain=[('special','=',False)]),
                'account_id':fields.many2one('account.account','Compte',required=True),
                    }
    
    def _get_fiscalyear(self, cr, uid, context=None):
        if context is None:
            context = {}
        now = time.strftime('%Y-%m-%d')
        company_id = False
        ids = context.get('active_ids', [])
        if ids and context.get('active_model') == 'account.account':
            company_id = self.pool.get('account.account').browse(cr, uid, ids[0], context=context).company_id.id
        else:  # use current company id
            company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        domain = [('company_id', '=', company_id), ('date_start', '<', now), ('date_stop', '>', now)]
        fiscalyears = self.pool.get('account.fiscalyear').search(cr, uid, domain, limit=1)
        return fiscalyears and fiscalyears[0] or False

    _defaults = {
            'fiscalyear_id': _get_fiscalyear,
    }

    
    def onchange_fiscalyear_id(self,cr,uid,ids,fiscalyear_id,context=None):
        period_ids = self.pool.get('account.period').search(cr,uid,[('fiscalyear_id','=',fiscalyear_id),('special','=',False)])
        period_domain=[('id','in',tuple(period_ids))]
        return {'value':{'period_id':period_ids[0]},'domain':{'period_id':period_domain}}
   
    def onchange_period_id(self,cr,uid,ids,fiscalyear_id,period_id,context=None):
       if not fiscalyear_id:
           raise osv.except_osv(_('Veuiller choisir un Exercice Comptable'),_(""))
       account_type_ids = self.pool.get('account.account.type').search(cr,uid,['|',('code','=','bank'),('code','=','cash'),])
       account_ids = self.pool.get('account.account').search(cr,uid,[('user_type','in',account_type_ids),])
       account_domain=[('id','in',account_ids)]
       return {'domain':{'account_id':account_domain}}
    
    def pre_print_report(self,cr,uid,ids,context=None):
        
        wizard = self.browse(cr,uid,ids,context)[0]
        data = {}

        fiscalyear_id = wizard.fiscalyear_id.id
        period_id = wizard.period_id.id
        account_id = wizard.account_id.id
        bank_id = wizard.bank_id.id

        move_line_obj = self.pool.get("account.move.line")
        move_obj = self.pool.get("account.move")
        journal_obj = self.pool.get("account.journal")
        acc_bank_stat_obj = self.pool.get("account.bank.statement")
        journaux_ids = journal_obj.search(cr,uid,[('type','=','bank')])
        period_ids = self.pool.get('account.period').search(cr,uid,[('id','<=',period_id),('fiscalyear_id','=',fiscalyear_id),('special','=',False)])
        domain_moves = [('journal_id','in',journaux_ids),('period_id','in',period_ids),('state','=','posted')]
        move_ids = move_obj.search(cr,uid,domain_moves)
        domain_move_lines = [('reconciliation_id','=',False),('move_id','in',move_ids),('period_id','in',period_ids),('state','=','valid'),
                             ('account_id','=',account_id),('rapprocher','=',False),('state','!=','exception'),('journal_id','in',journaux_ids)]
        move_line_ids = move_line_obj.search(cr,uid,domain_move_lines)
        domain_bank_stat = [('bank_id','=',bank_id),('period_id','in',period_ids)]
        bank_stat_ids = acc_bank_stat_obj.search(cr,uid,domain_bank_stat)
        domain_bank_stat_encours = [('bank_id','=',bank_id),('period_id','=',period_id)]
        bank_stat_encours_ids = acc_bank_stat_obj.search(cr,uid,domain_bank_stat_encours)
        if bank_stat_ids == [] :
            raise osv.except_osv("Attention !","Il n'y a aucun relevé bancaire pour le couple Banque/Période choisi.")
        data['form'] = self.read(cr, uid, ids, ['fiscalyear_id', 'bank_id', 'period_id', 'account_id'], context=context)[0]
        for field in ['fiscalyear_id', 'bank_id', 'period_id', 'account_id']:
            if isinstance(data['form'][field], tuple):
                data['form'][field] = data['form'][field][0]
        data['form']['move_line_ids'] = move_line_ids
        data['form']['bank_stat_ids'] = bank_stat_ids
        data['form']['bank_stat_encours_ids'] = bank_stat_encours_ids
        return data

    def print_report(self, cr, uid, ids,context=None):
        if context is None:
            context = {}
        data = self.pre_print_report(cr, uid, ids, context=context)
        return self.pool['report'].get_action(cr, uid, [], 'bank_reconcile.report_situation_rapprochement', data=data, context=context)
    
list_not_rapproched()

