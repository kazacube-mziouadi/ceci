
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


class prepare_reconcile_wizard(osv.osv_memory):
    
    _name = 'prepare.reconcile.wizard'
    
   
    
    _columns = {
                
                'fiscalyear_id':fields.many2one('account.fiscalyear', 'Exercice comptable', required=True), 
                'period_ids':fields.many2many('account.period', 'prepare_wizard_period_rel', 'prepare_wizard_id', 'period_id', 'Périodes'), 
                #'journal_ids':fields.many2many('account.journal', 'prepare_wizard_journal_rel', 'prepare_wizard_id', 'journal_id', 'Journaux'), 
                'bank_ids':fields.many2many('res.bank', 'prepare_wizard_bank_rel', 'prepare_wizard_id', 'bank_id', 'Banques'),

            
                    }
    
    def onchange_fiscalyear(self, cr, uid, ids, fiscalyear_id, context=None):
          
          period_ids = self.pool.get('account.period').search(cr,uid,[('fiscalyear_id','=',fiscalyear_id),('special','=',False)])
          #journal_ids = self.pool.get('account.journal').search(cr,uid,[('type','=','bank')])
          val={'period_ids':period_ids}
          return {'value': val}
      
    def _default_journal_id(self, cr, uid, context=None):
        if context is None:
            context = {}
        journal_pool = self.pool.get('account.journal')
        journal_type = 'bank'
        company_id = self.pool.get('res.company')._company_default_get(cr, uid, 'account.bank.statement',context=context)
        if journal_type:
            ids = journal_pool.search(cr, uid, [('type', '=', journal_type),('company_id','=',company_id)])
            if ids:
                return ids[0]
        return False

    
    def action_create_bank_statement(self, cr, uid, ids, context=None):
       
        if context is None:
            context = {}
        fiscalyear_id = self.browse(cr,uid,ids[0]).fiscalyear_id
        period_ids = self.browse(cr,uid,ids[0]).period_ids
        bank_ids = self.browse(cr,uid,ids[0]).bank_ids
        user = self.browse(cr,uid,uid,context)
        for period in period_ids:
            res = {}
            res['period_id'] = period.id
            res['journal_id'] = self._default_journal_id(cr, uid, context)
            res['company_id'] = self.pool.get('res.company')._company_default_get(cr, uid, 'account.bank.statement',context=context)
            for bank in bank_ids:
                res['bank_id'] = bank.id
                #res['name'] = bank.bic and bank.bic or bank.name+'_'+period.code
                res['name'] = bank.name + '_' + bank.bic + '_' + period.code
                print(res['name'])
                self.pool.get('account.bank.statement').create(cr, uid, res, context=context)
        return True
    

prepare_reconcile_wizard()