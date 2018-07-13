# -*- encoding: utf-8 -*-

import time
from openerp.osv import osv
from openerp.report import report_sxw
from common_report_header import common_report_header

class list_not_rapproched(report_sxw.rml_parse,common_report_header):
    
    _name = 'report.bank_reconcile.move.line.not.rapproched'


    def __init__(self, cursor, uid, name, context=None):
        if context is None:
            context = {}
        super(list_not_rapproched, self).__init__(cursor, uid, name, context=context)
#         self.pool = pooler.get_pool(self.cr.dbname)
#         self.cursor = self.cr
#         
#         company = self.pool.get('res.users').browse(self.cr, uid, uid, context=context).company_id
#         header_report_name = ""
#         footer_date_time = self.formatLang(str(datetime.today()), date_time=True)
        
        self.localcontext.update( {
             'time': time,
#             'cr': cursor,
#             'uid': uid,
#             'report_name': _('SITUATION RAPPROCHEMENT BANCAIRE'),
            'move_lines':self._move_lines,
            'bank_statement_lines':self._bank_statement_lines,
            'account':self._get_account,
            'bank':self._get_bank,
            'bank_stat':self._get_bank_stat,
            'move_line_debit':self._get_somme_move_lines_debit_rapproched,
            'move_line_credit':self._get_somme_move_lines_credit_rapproched,
            'bank_statement_lines_rapproched':self._bank_statement_lines_rapproched,
            'period':self._get_period,
            'sum_debit':self._sum_debit_account,
            'sum_credit':self._sum_credit_account,
            'get_lines':self._get_lines,
            'get_debit':self._get_debit,
            'get_credit':self._get_credit,
            'get_bank_debit':self._get_bank_debit,
            'get_bank_credit':self._get_bank_credit,
            'get_bank_rapp_debit':self._get_bank_rapp_debit,
            'get_bank_rapp_credit':self._get_bank_rapp_credit,
            'get_solde_debit':self._get_solde_debit,
            'get_solde_credit':self._get_solde_credit,
            'get_solde_bank_debit':self._get_solde_bank_debit,
            'get_solde_bank_credit':self._get_solde_bank_credit,
            'get_nouveau_solde_debit':self._get_nouveau_solde_debit,
            'get_nouveau_solde_credit':self._get_nouveau_solde_credit,
            'get_line_debit':self._get_line_debit,
            'get_line_credit':self._get_line_credit,
	        'solde_comptable_debit':self._get_nouveau_solde_comptable_debit,
	        'solde_comptable_credit':self._get_nouveau_solde_comptable_credit,
        })
    
    
    def _sum_debit_account(self,data):
         sum_debit = 0
         self.cr.execute('select sum(debit) from account_move_line as aml,account_move am,account_account aa where aa.id = aml.account_id and am.id = aml.move_id and am.state = %s and aml.period_id <= %s and aa.id = %s',('posted',data['form']['period_id'],data['form']['account_id'],))
         sum_debit = self.cr.fetchone()[0] or 0.0
         return sum_debit
# 
#     
    def _sum_credit_account(self,data):
         sum_credit = 0
         self.cr.execute('select sum(credit) from account_move_line as aml,account_move am,account_account aa where aa.id = aml.account_id and am.id = aml.move_id and am.state = %s and aml.period_id = %s and aa.id = %s',('posted',data['form']['period_id'],data['form']['account_id'],))
         sum_credit = self.cr.fetchone()[0] or 0.0
         return sum_credit
    
    def _get_account(self,data):
        account = self.pool.get('account.account').browse(self.cr,self.uid,data['form']['account_id'])
        return account
    
    def _get_bank(self,data):
        bank = self.pool.get('res.bank').browse(self.cr,self.uid,data['form']['bank_id'])
        return bank

    def _get_period(self,data):
        period = self.pool.get('account.period').browse(self.cr,self.uid,data['form']['period_id'])
        return period

    def _move_lines(self,data):
        move_lines = self.pool.get('account.move.line').browse(self.cr,self.uid,data['form']['move_line_ids'])
        return move_lines
    
    def _get_somme_move_lines_debit_rapproched(self,data):
        debit_rapproched = 0
        period=self._get_period(data)
        date_end=period.date_stop
        account_id=data['form']['account_id']
        domain=[('state','=','valid'),('account_id','=',account_id),
                ('rapprocher','=',True),('date','<=',date_end),('state1','=','normal'),('move_stat_id','!=',None)]
        account_move_line_ids = self.pool.get('account.move.line').search(self.cr,self.uid,domain)
        for line in account_move_line_ids :
                    line_id=self.pool.get('account.move.line').browse(self.cr,self.uid,line)
                    debit_rapproched = debit_rapproched + line_id.debit
        return debit_rapproched
    
    def _get_somme_move_lines_credit_rapproched(self,data):
        credit_rapproched = 0
        period=self._get_period(data)
        date_end=period.date_stop
        account_id=data['form']['account_id']
        domain=[('state','=','valid'),('account_id','=',account_id),
                ('rapprocher','=',True),('date','<=',date_end),('state1','=','normal'),('move_stat_id','!=',None)]
        account_move_line_ids = self.pool.get('account.move.line').search(self.cr,self.uid,domain)
        for line in account_move_line_ids :
            line_id=self.pool.get('account.move.line').browse(self.cr,self.uid,line)
            credit_rapproched = credit_rapproched + line_id.credit
        return credit_rapproched
    
    def _get_bank_stat(self,data):
        reconcile_bank = self.pool.get('account.bank.statement').browse(self.cr,self.uid,data['form']['bank_stat_encours_ids'][0])
        return reconcile_bank

    def _bank_statement_lines_rapproched(self,data):
        bank_stat_line_rapp_ids = self.pool.get('account.bank.statement.line').search(self.cr,self.uid,[('statement_id','in',data['form']['bank_stat_ids']),('state','=','normal'),('move_stat_id','!=',None)])
        bank_stat_rapp_lines = self.pool.get('account.bank.statement.line').browse(self.cr,self.uid,bank_stat_line_rapp_ids)
        return bank_stat_rapp_lines

    def _bank_statement_lines(self,data):
        bank_stat_line_ids = self.pool.get('account.bank.statement.line').search(self.cr,self.uid,[('statement_id','in',data['form']['bank_stat_ids']),('state','!=','exception'),('move_stat_id','=',None)])
        bank_stat_lines = self.pool.get('account.bank.statement.line').browse(self.cr,self.uid,bank_stat_line_ids)
        return bank_stat_lines
    
    def _get_lines(self,data):
        lines = []
        record = {}
        bank_stat_lines = self._bank_statement_lines(data)
        move_lines = self._move_lines(data)
        i = len(move_lines)
        j = len(bank_stat_lines)
        if i > j :
            for ml in move_lines :
                record = {
                          'date':ml.date,
                          'name':ml.name,
                          'debit':ml.debit,
                          'credit':ml.credit,
                          'piece':ml.move_id.name,
                          }
                if j >0 :
                    bl = bank_stat_lines[j-1]
                    record['date_op_bank'] = bl.reconciliation_id.date
                    record['amount'] = bl.amount
                    record['libelle'] = bl.name
                else :
                    record['date_op_bank'] = ''
                    record['amount'] = ''
                    record['libelle'] = ''
                lines.append(record)
                j = j-1
        elif i < j :
            for bl in bank_stat_lines :
                record = {
                          'date_op_bank':bl.reconciliation_id.date,
                          'amount':bl.amount,
                          'libelle':bl.name,
                          }
                if i >0 :
                    ml = move_lines[i-1]
                    record['date'] = ml.date
                    record['name'] = ml.name
                    record['debit'] = ml.debit
                    record['credit'] = ml.credit
                    record['piece'] = ml.move_id.name
                else :
                    record['date'] = ''
                    record['name'] = ''
                    record['debit'] = ''
                    record['credit'] = ''
                    record['piece'] = ''
                lines.append(record)
                i = i-1
        else :
            for bl in bank_stat_lines :
                record = {
                          'date_op_bank':bl.reconciliation_id.date,
                          'amount':bl.amount,
                          'libelle':bl.name,
                          }
                if i >0 :
                    ml = move_lines[i-1]
                    record['date'] = ml.date
                    record['name'] = ml.name
                    record['debit'] = ml.debit
                    record['credit'] = ml.credit
                    record['piece'] = ml.move_id.name
                lines.append(record)
                i = i-1
        #for x in range(200) :
         #   lines.append(lines[1])
        return lines

    def _get_debit(self,data):
        debit = 0
        move_lines = self._move_lines(data)
        for ml in move_lines :
            debit+=ml.debit
        return debit

    def _get_credit(self,data):
        credit = 0
        move_lines = self._move_lines(data)
        for ml in move_lines :
            credit+=ml.credit
        return credit

    def _get_bank_debit(self,data):
        bank_debit = 0
        bank_stat_lines = self._bank_statement_lines(data)
        for bl in bank_stat_lines :
            if bl.amount < 0 :
                bank_debit+=bl.amount
        return abs(bank_debit)

    def _get_bank_credit(self,data):
        bank_credit = 0
        bank_stat_lines = self._bank_statement_lines(data)
        for bl in bank_stat_lines :
            if bl.amount > 0 :
                bank_credit+=bl.amount
        return bank_credit

    def _get_solde_debit(self,data):
        solde_debit = 0
        debit = self._get_debit(data)
        credit = self._get_credit(data)
        if debit - credit > 0 :
            solde_debit = debit - credit
        return solde_debit

    def _get_solde_credit(self,data):
        solde_credit = 0
        debit = self._get_debit(data)
        credit = self._get_credit(data)
        if debit - credit < 0 :
            solde_credit = debit - credit
        return abs(solde_credit)

    def _get_solde_bank_debit(self,data):
        solde_bank_debit = 0
        bank_debit = self._get_bank_debit(data)
        bank_credit = self._get_bank_credit(data)
        if  bank_debit - bank_credit > 0 :
            solde_bank_debit =  bank_debit - bank_credit
        return solde_bank_debit

    def _get_solde_bank_credit(self,data):
        solde_bank_credit = 0
        bank_debit = self._get_bank_debit(data)
        bank_credit = self._get_bank_credit(data)
        if bank_credit - bank_debit > 0 :
            solde_bank_credit = bank_credit - bank_debit
        return solde_bank_credit
    
    def _get_line_debit(self,move_line):
        line_debit = 0
        if move_line['amount'] < 0 :
            line_debit =move_line['amount']
        return line_debit


    
    def _get_line_credit(self,move_line):
        line_credit = 0
        if move_line['amount'] > 0 :
            line_credit =move_line['amount']
        return line_credit


    
    def _get_bank_rapp_debit(self,data):
        bank_rapp_debit = 0
        bank_stat_rapp_lines = self._bank_statement_lines_rapproched(data)
        for bl in bank_stat_rapp_lines :
            if bl.amount < 0 :
                bank_rapp_debit+=bl.amount
        return abs(bank_rapp_debit)

    def _get_bank_rapp_credit(self,data):
        bank_rapp_credit = 0
        bank_stat_rapp_lines = self._bank_statement_lines_rapproched(data)
        for bl in bank_stat_rapp_lines :
            if bl.amount > 0 :
                bank_rapp_credit+=bl.amount
        return abs(bank_rapp_credit)
    

    
    def _get_nouveau_solde_debit(self,data):
        nouveau_solde_debit = 0
        bank_stat = self._get_bank_stat(data)
        if bank_stat.balance_end_real < 0 :
            nouveau_solde_debit = bank_stat.balance_end_real
        return nouveau_solde_debit

    def _get_nouveau_solde_credit(self,data):
        nouveau_solde_credit = 0
        bank_stat = self._get_bank_stat(data)
        if bank_stat.balance_end_real > 0 :
            nouveau_solde_credit = bank_stat.balance_end_real
        return nouveau_solde_credit


    def _get_nouveau_solde_comptable_debit(self,data):
        nouveau_solde_comptable_debit = 0
        move_line_debit_rapp = self._get_somme_move_lines_debit_rapproched(data)
        move_line_credit_rapp = self._get_somme_move_lines_credit_rapproched(data)
        debit = self._get_debit(data)
        credit = self._get_credit(data)
        if (move_line_debit_rapp + debit) - (move_line_credit_rapp+credit) > 0 :
            nouveau_solde_comptable_debit = (move_line_debit_rapp + debit) - (move_line_credit_rapp+credit)
        return nouveau_solde_comptable_debit

    def _get_nouveau_solde_comptable_credit(self,data):
        nouveau_solde_comptable_credit = 0
        move_line_debit_rapp = self._get_somme_move_lines_debit_rapproched(data)
        move_line_credit_rapp = self._get_somme_move_lines_credit_rapproched(data)
        debit = self._get_debit(data)
        credit = self._get_credit(data)
        if (move_line_debit_rapp + debit) - (move_line_credit_rapp+credit) < 0 :
            nouveau_solde_comptable_credit = (move_line_debit_rapp + debit) - (move_line_credit_rapp+credit)
        return nouveau_solde_comptable_credit
   
class report_situation_rapprochement(osv.AbstractModel):
    
    _name = 'report.bank_reconcile.report_situation_rapprochement'
    _inherit = 'report.abstract_report'

    _template = 'bank_reconcile.report_situation_rapprochement'
    _wrapped_report_class = list_not_rapproched
