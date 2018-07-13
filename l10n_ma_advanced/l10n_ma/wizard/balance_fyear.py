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
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import base64
from openerp.osv import fields,osv
from openerp.tools.translate import _
import time
import datetime as DT
from datetime import datetime
from dateutil.relativedelta import relativedelta
from operator import itemgetter
from openerp import netsvc
from openerp import pooler
import openerp.addons.decimal_precision as dp
import cStringIO
import xlwt
from cStringIO import StringIO

class balance_fyear_export(osv.osv_memory):
    _name="balance.fyear.export"
    _columns = {
                 'name': fields.char('Filename', 256, readonly=True),
                 'data': fields.binary('File', readonly=True),
             }
balance_fyear_export()

class balance_fyear(osv.osv_memory):
    _inherit = "account.common.account.report"
    _name = 'balance.fyear'
    _description = 'Fiscal Year Balance Report with n-1 fyear'

    _columns = {
        'level_operator':fields.selection([('==','='),('>=','>='),('<=','<=')],required=False,string="Level condition"),
        'level':fields.selection([('0','0'),('1','1'),('2','2'),('3','3'),('4','4'),('5','5'),('6','6'),('7','7')],required=False,string="Level"),
        'type_report':fields.selection([('xls','excel')],required=True,string="Type rapport",_default="excel"),
        'journal_ids': fields.many2many('account.journal', 'account_balance_report_journal_rel', 'account_id', 'journal_id', 'Journals', required=True),
        'fiscalyear_prec':fields.many2one('account.fiscalyear','Exercice Fiscal prec'),
        'type_compte':fields.selection([('vue','Comptes de regroupement'),('normal','Comptes Normaux'),('tous','Tous les comptes')],required=False,string="Type de Compte"),
    }

    _defaults = {
        'journal_ids': [],
        'type_compte':'normal',
        'type_report':'xls'
    }
    
    def _get_query(self,cr,uid,ids,type):
        query=""
        this = self.browse(cr, uid, ids)[0]
        fyear_prec=self.pool.get("account.fiscalyear").browse(cr,uid,this.fiscalyear_prec.id)
        fyear=self.pool.get("account.fiscalyear").browse(cr,uid,this.fiscalyear_id.id)
        DATETIME_FORMAT = "%Y-%m-%d"
        l=len(fyear_prec.period_ids)
        tab=[]
        if type=='old':
            fiscalyear=fyear_prec
        if type=="now":
             fiscalyear=fyear
             
        for p in fiscalyear.period_ids :
                    tab.append(p.id)
        p_ids=tuple(x for x in tab)
      
        if this.filter=="filter_no":
                    query="l.period_id in %s"%str(p_ids)
        if this.filter=='filter_period' :
                    period_obj=self.pool.get("account.period")
                    month_from=DT.datetime.strptime(period_obj.browse(cr,uid,[this.period_from.id])[0].date_start, DATETIME_FORMAT).month
                    month_to=DT.datetime.strptime(period_obj.browse(cr,uid,[this.period_to.id])[0].date_start, DATETIME_FORMAT).month
                    for period in fiscalyear.period_ids :
                        if DT.datetime.strptime(period.date_start,DATETIME_FORMAT).month==month_from :
                            period_from=period.id
                        if DT.datetime.strptime(period.date_start,DATETIME_FORMAT).month==month_to :
                            period_to=period.id
                    if  (period_to and period_from) :
                        query="l.period_id between %s and %s"%(period_from,period_to)
                    else :
                        raise orm.except_orm(_('Configuration Error!'),
                     _('Types de periodes ne sont pas identiques pour les deux exercices.'))
        if this.filter=='filter_date' : 
                   query="l.date>='%s'::date  and  l.date<='%s'::date and l.period_id in %s "%(this.date_from,this.date_to,str(p_ids))
        return query
    
    def _balance_init(self,cr,uid,ids,account_id,sql=""):
        account_obj=self.pool.get('account.account')
        query=self._get_query(cr, uid, ids,'old')
        res=account_obj._account_account__compute(cr,uid,[account_id],['balance'],None,None,query)
        return res[account_id]['balance']
        
    def _sum_credit_debit(self,cr,uid,ids,account_id):
            account_obj=self.pool.get('account.account')
            query="aj.type not in ('situation') and aj.id=l.journal_id and " +self._get_query(cr, uid, ids,'now')
            res=account_obj._account_account__compute_init(cr,uid,[account_id],['credit','debit'],None,None,query)
            return res[account_id]
    
    def _sum_balance(self,cr,uid,ids,account_id):
            account_obj=self.pool.get('account.account')
            query=self._get_query(cr, uid, ids,'now')
            res=account_obj._account_account__compute(cr,uid,[account_id],['balance'],None,None,query)
            return res[account_id]['balance']
        
    def _sum_balance_account(self, account):
        if account.type == 'view':
            return account.balance
        move_state = ['draft','posted']
        if self.target_move == 'posted':
            move_state = ['posted','']
        self.cr.execute('SELECT (sum(debit) - sum(credit)) as tot_balance \
                FROM account_move_line l \
                JOIN account_move am ON (am.id = l.move_id) \
                WHERE (l.account_id = %s) \
                AND (am.state IN %s) \
                AND '+ self.query +' '
                ,(account.id, tuple(move_state)))
        sum_balance = self.cr.fetchone()[0] or 0.0
        return sum_balance


    def _traduction_type(self,type):
        if type == 'view':
            return 'Vue'
        elif type == 'other':
            return 'Normal'
        elif type == 'receivable':
            return 'Créditeurs'
        elif type == 'payable':
            return 'A payer'
        elif type == 'liquidity':
            return 'Liquidités'
        elif type == 'consolidation':
            return 'Consolidation'
        else :
            return 'Cloturé'

    
    def pre_print_report(self, cr, uid, ids, data, context=None):
        if context is None:
            context = {}
        data['form'].update(self.read(cr, uid, ids, ['name','data','type_report','company_id','level_operator','level','display_account','fiscalyear_prec'], context=context)[0])
        return data
    
#    def get_children_accounts(self, account):
#        res = []
#        currency_obj = self.pool.get('res.currency')
#        ids_acc = self.pool.get('account.account')._get_children_and_consol(self.cr, self.uid, account)
#        currency = self.chart_account_id.currency_id and self.chart_account_id.currency_id or self.chart_account_id.company_id.currency_id
#        for child_account in self.pool.get('account.account').browse(self.cr, self.uid, ids_acc, context=self.context):
#            sql = """
#                SELECT count(id)
#                FROM account_move_line AS l
#                WHERE %s AND l.account_id = %%s
#            """ % (self.query)
#            self.cr.execute(sql, (child_account.id,))
#            num_entry = self.cr.fetchone()[0] or 0
#            sold_account = self._sum_balance_account(child_account)
#            #self.sold_accounts[child_account.id] = sold_account
#            if self.display_account == 'bal_movement':
#                if child_account.type != 'view' and num_entry <> 0:
#                    res.append(child_account.id)
#            elif self.display_account == 'bal_solde':
#                if child_account.type != 'view' and num_entry <> 0:
#                    if not currency_obj.is_zero(self.cr, self.uid, currency, sold_account):
#                        res.append(child_account.id)
#            else:
#                res.append(child_account.id)
#        if not res:
#            return account
#        return res
#
#
#    def get_parents(self,account_ids):
#
#        accounts = self.pool.get('account.account').browse(self.cr,self.uid,account_ids)
#        
#        for account in accounts :
#            if account.parent_id :
#                if account.parent_id.id not in self.account_parent_ids :
#                    self.account_parent_ids.append(account.parent_id.id)
#                self.get_parents([account.parent_id.id])
#        return self.account_parent_ids
            

    def _print_report(self, cr, uid, ids, data, context=None):
         
         data = self.pre_print_report(cr, uid, ids, data, context=context)
         if data['form']['type_report']=="xls":
             this = self.browse(cr, uid, ids)[0]

             account_obj=self.pool.get('account.account')
             period_obj = self.pool.get('account.period')
             child_ids = self.pool.get('account.account')._get_children(cr,uid, this.chart_account_id.id)
             child_ids.sort()
            
             if this.type_compte == 'normal':
                 account_ids=account_obj.search(cr,uid,[('id','in',child_ids),('type','!=','view')])
             elif this.type_compte == 'vue':
                 account_ids=account_obj.search(cr,uid,[('id','in',child_ids),('type','=','view')])
             else :
                account_ids=account_ids=account_obj.search(cr,uid,[('id','in',child_ids)])
             
             ncompte=account_obj.read(cr,uid,account_ids,['name','code','parent_id','type'])
             ncompte = sorted(ncompte, key=lambda record:record['id'])
             
             tab_xls=[[0 for i in range(8)] for j in range(len(ncompte))]
             k=0
             condition=False
             for i in range(0,len(ncompte)) :
                              type_compte = self._traduction_type(ncompte[i]['type'])
                              cd=self._sum_credit_debit(cr,uid,ids,ncompte[i]['id'])
                              if ncompte[i]['parent_id']:
                                  tab_xls[i][0] = str(list(ncompte[i]['parent_id'])[1].encode('utf-8'))
                              else :
                                  tab_xls[i][0] = ''
                              tab_xls[i][1] =str(ncompte[i]['code'])
                              tab_xls[i][2] =str(ncompte[i]['name'].encode('utf-8'))
                              tab_xls[i][3]=self._balance_init(cr,uid,ids,ncompte[i]['id'])
                              tab_xls[i][4]=cd['debit']
                              tab_xls[i][5]=cd['credit']
                              tab_xls[i][6]=self._sum_balance(cr,uid,ids,ncompte[i]['id'])
                              tab_xls[i][7] =str(type_compte)
                 
             wb = xlwt.Workbook()
             ws = wb.add_sheet('Balance_6_colonnes')
             font0 = xlwt.Font()
             font1= xlwt.Font()
             font0.name = font1.name='Arial'
             font0.colour_index = 2
             font1.colour_index = 4
             font0.bold = font1.bold=True
             style0=xlwt.XFStyle()
             style1=xlwt.XFStyle()
             style0.font = font0
             style1.font= font1
             style2 = xlwt.XFStyle()
             style2.num_format_str = '#,##0.00'
             
             font2 = xlwt.Font()
             font2.name = 'Arial'
             font2.colour_index = 2
             font2.bold = True
             font2.height = 350
             
             font3 = xlwt.Font()
             font3.name = 'Arial'
             font3.colour_index = 2
             font3.bold = True
             font3.height = 280
             
             font4 = xlwt.Font()
             font4.name = 'Arial'
             font4.colour_index = 2
             font4.bold = True
             font4.height = 200
             
             style3 = xlwt.XFStyle()
             style3.font = font2
             
             style4 = xlwt.XFStyle()
             style4.font = font3
             
             style5 = xlwt.XFStyle()
             style5.font = font4
             
             borders = xlwt.Borders()
             borders.left = 1
             borders.right = 1
             borders.top = 1
             borders.bottom = 1
             
             font5 = xlwt.Font()
             font5.name = 'Arial'
             font5.colour_index = 63
             font5.bold = True

             
             style6 = xlwt.XFStyle()
             style6.font = font5
             style6.borders = borders
             
             style7 = xlwt.XFStyle()
             style7.font = font0
             style7.borders = borders




             title = "Balance des comptes %s"%this.fiscalyear_id.name
             ws.write(0, 0, title, style3)
             header = ['Parent','Code' ,'Compte','Solde %s'%this.fiscalyear_prec.name,unicode('Débit',"utf8"),unicode('Crédit',"utf8"),'Solde %s'%this.fiscalyear_id.name,'Type']
             
             ws.row(0).height = 500
             ws.row(1).height = 500
             ws.row(2).height = 400
        

             taille_header=[20000,4000,13200,7000,5000,4500,5000,4000]
             table_options=['Plan compte','Filtre','Afficher le compte','Exercice Fiscal',unicode('Écritures',"utf8")]
             filter=level=""
             if this.level_operator and this.level :
                 level=str(this.level_operator)+str(this.level)
             if this.filter =='filter_date':
                 filter="Date :"+str(this.date_from)+" - "+str(this.date_to)
             if this.filter== 'filter_period':
                 filter="Périodes :"+str(this.period_from.name)+" - "+str(this.period_to.name)
             
             if this.display_account == 'movement':
                 display_account = 'Avec mouvements'
             elif this.display_account == 'all':
                 display_account = 'Tous'
             else :
                 display_account = unicode('Avec la balance qui n\'est pas égale à 0', "utf8")
             if this.target_move == 'posted':
                 target_move = unicode('Toutes les écritures passées', "utf8")
             else :
                 target_move = unicode('Toutes les écritures', "utf8")

             if this.filter == 'filter_no' :
                 filter1 = ''
             elif this.filter == 'date':
                 filter1 = 'Date'
             else :
                 filter1 = unicode('Périodes', "utf8") 

             options_value=[this.chart_account_id.name,unicode(filter1,"utf8"),display_account,this.fiscalyear_id.name,target_move]
             for i in range(len(table_options)) :  
                 ws.write(4,i,table_options[i],style6)
                 ws.write(5,i,options_value[i],style6)
             row=0
             condition=True
             for i in range(len(header)) :
                  ws.write(7,i,header[i],style7)
                  ws.col(i).width=taille_header[i]
             
             date_edit = time.strftime('%d/%m/%y %H:%M',time.localtime())
             ws.write(2, 0, unicode('Date d\'édition : ',"utf8")+date_edit,style5)
             ws.write(1, 0,this.chart_account_id.company_id.name,style4)

             ws.write(4,5,'Devise',style6)
             ws.write(5,5,this.chart_account_id.company_id.currency_id.symbol,style6)
             
             if this.display_account=="all":
                 for i in range(0,len(ncompte)):
                         for j in range(8):
                             if j == 0 or j == 1 or j == 2 or j == 7:
                                 ws.write(8+row,j,unicode(tab_xls[i][j],"utf8"))
                             else :
                                 ws.write(8+row,j,tab_xls[i][j],style2)
                         row+=1
                         
             if this.display_account=="movement":
                    for i in range(0,len(ncompte)):
                       if tab_xls[i][3] != 0.0 or  tab_xls[i][6] != 0.0  :
                            for j in range(8) :
                                 if j == 0 or j == 1 or j == 2 or j == 7:
                                     ws.write(8+row,j,unicode(tab_xls[i][j],"utf8"))
                                 else :
                                     ws.write(8+row,j,tab_xls[i][j],style2)
                            row+=1
                            
             if this.display_account=="not_zero" :
                  for i in range(0,len(ncompte)):
                       if tab_xls[i][6] != 0.0 :
                          for j in range(8) :
                                 if j == 0 or j == 1 or j == 2 or j == 7:
                                     ws.write(8+row,j,unicode(tab_xls[i][j],"utf8"))
                                 else :
                                     ws.write(8+row,j,tab_xls[i][j],style2)
                          row+=1 
             f = StringIO()
             wb.save(f)
             out=base64.encodestring(f.getvalue())
             #date_day = datetime.now()
             date_day = time.strftime('%d/%m/%y_%H-%M-%S',time.localtime())
             fichier="balance_export_%s.xls"%str(date_day)

             view_obj = self.pool.get('ir.ui.view')
             view_id = view_obj.search(cr, uid, [('model', '=', 'balance.fyear.export'), \
                                     ('name', '=', 'Balance Fiscal Year export')])
             export_id = self.pool.get('balance.fyear.export').create(cr, uid, {'data':out,'name':fichier}, context=dict(context, active_ids=ids))
             
             return {
                    'name':"Export Excel",
                    'view_mode': 'form',
                    'view_id':view_id,
                    'view_type': 'form',
                    'res_model': 'balance.fyear.export',
                    'res_id': export_id,
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                   
                }
         
         if data['form']['type_report']=="pdf":
             return {'type': 'ir.actions.report.xml', 'report_name': 'balance.fyear', 'datas': data}

balance_fyear()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
