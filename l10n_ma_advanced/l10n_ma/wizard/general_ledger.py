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
##############################################################################
from openerp.osv import fields, osv
from cStringIO import StringIO
import base64
import xlwt
from xlwt import *
#from PIL import Image
#import Image
from datetime import datetime
import time
import os
from openerp.tools.translate import _


class account_general_ledger_export(osv.osv_memory):
    _name = "account.general.ledger.export"
    _description = "General Ledger Export"

    _columns = {
        'name': fields.char('Filename',256, readonly=True),
        'data': fields.binary('File', readonly=True),
        'state': fields.selection( [ ('choose','choose'),('get','get')],'state', readonly=True),
    }
    _defaults = { 
        'state':'choose',
    }
account_general_ledger_export()

class account_report_general_ledger(osv.osv_memory):
    _inherit = "account.report.general.ledger"
    _description = "General Ledger Report"

    _columns = {
        'type_report':fields.selection([('excel','Excel'),],'Type de Rapport',required = True, _defaults='Excel', readonly=True),
    }
    
    
    _defaults = { 
        'type_report':'excel',
    }

    def get_journaux(self,journaux):
        jrnx = ''
        for j in journaux :
            if jrnx :
                if len(jrnx)%3 == 0 :
                    jrnx = jrnx+','+j.code+'\n'
                else :
                    jrnx = jrnx+','+j.code
            else :
                jrnx = j.code
        return jrnx
    
    def get_content_header_p(self):
        tab = []
        jrs = self.get_journaux(self._journal_ids)
        if self._display_account == 'movement':
            self._display_account = 'Avec mouvements'
        elif self._display_account == 'all':
            self._display_account = 'Tous'
        else :
            self._display_account = unicode('Avec la balance qui n\'est pas égale à 0', "utf8")
        
        if self._target_move == 'posted':
            self._target_move = unicode('Toutes les écritures passées', "utf8")
        else :
            self._target_move = unicode('Toutes les écritures', "utf8")
        
        if self._sortby == 'sort_date' :
            self._sortby = 'Date'
        else :
           self._sortby = 'Journal et partenaire'
        if self._filter == 'filter_no' :
            self._filter = ''
        elif self._filter == 'date':
            self._filter = 'Date'
        else :
            self._filter = unicode('Périodes', "utf8") 
        
        tab = [self._chart_account_id.name,self._fiscalyear_id.name,jrs,self._display_account,self._filter,self._sortby,self._target_move]
        return tab
    
    def _sum_debit_account(self, account):
        if account.type == 'view':
            return account.debit
        move_state = ['draft','posted']
        if self._target_move == 'posted':
            move_state = ['posted','']
        self.cr.execute('SELECT sum(debit) \
                FROM account_move_line l \
                JOIN account_move am ON (am.id = l.move_id) \
                WHERE (l.account_id = %s) \
                AND (am.state IN %s) \
                AND '+ self.query +' '
                ,(account.id, tuple(move_state)))
        sum_debit = self.cr.fetchone()[0] or 0.0
        if self._init_balance:
            self.cr.execute('SELECT sum(debit) \
                    FROM account_move_line l \
                    JOIN account_move am ON (am.id = l.move_id) \
                    WHERE (l.account_id = %s) \
                    AND (am.state IN %s) \
                    AND '+ self.query +' '
                    ,(account.id, tuple(move_state)))
            # Add initial balance to the result
            sum_debit += self.cr.fetchone()[0] or 0.0
        return sum_debit

    
    def _sum_credit_account(self, account):
        if account.type == 'view':
            return account.credit
        move_state = ['draft','posted']
        if self._target_move == 'posted':
            move_state = ['posted','']
        self.cr.execute('SELECT sum(credit) \
                FROM account_move_line l \
                JOIN account_move am ON (am.id = l.move_id) \
                WHERE (l.account_id = %s) \
                AND (am.state IN %s) \
                AND '+ self.query +' '
                ,(account.id, tuple(move_state)))
        sum_credit = self.cr.fetchone()[0] or 0.0
        if self._init_balance:
            self.cr.execute('SELECT sum(credit) \
                    FROM account_move_line l \
                    JOIN account_move am ON (am.id = l.move_id) \
                    WHERE (l.account_id = %s) \
                    AND (am.state IN %s) \
                    AND '+ self.query +' '
                    ,(account.id, tuple(move_state)))
            # Add initial balance to the result
            sum_credit += self.cr.fetchone()[0] or 0.0
        return sum_credit


    def _sum_balance_account(self, account):
        if account.type == 'view':
            return account.balance
        move_state = ['draft','posted']
        if self._target_move == 'posted':
            move_state = ['posted','']
        self.cr.execute('SELECT (sum(debit) - sum(credit)) as tot_balance \
                FROM account_move_line l \
                JOIN account_move am ON (am.id = l.move_id) \
                WHERE (l.account_id = %s) \
                AND (am.state IN %s) \
                AND '+ self.query +' '
                ,(account.id, tuple(move_state)))
        sum_balance = self.cr.fetchone()[0] or 0.0
        if self._init_balance:
            self.cr.execute('SELECT (sum(debit) - sum(credit)) as tot_balance \
                    FROM account_move_line l \
                    JOIN account_move am ON (am.id = l.move_id) \
                    WHERE (l.account_id = %s) \
                    AND (am.state IN %s) \
                    AND '+ self.query +' '
                    ,(account.id, tuple(move_state)))
            # Add initial balance to the result
            sum_balance += self.cr.fetchone()[0] or 0.0
        return sum_balance


    def get_children_accounts(self, account):
        res = []
        currency_obj = self.pool.get('res.currency')
        ids_acc = self.pool.get('account.account')._get_children(self.cr, self.uid, account.id)
        currency = account.currency_id and account.currency_id or account.company_id.currency_id
        for child_account in self.pool.get('account.account').browse(self.cr, self.uid, ids_acc, context=self.context):
            sql = """
                SELECT count(id)
                FROM account_move_line AS l
                WHERE %s AND l.account_id = %%s
            """ % (self.query)
            self.cr.execute(sql, (child_account.id,))
            num_entry = self.cr.fetchone()[0] or 0
            sold_account = self._sum_balance_account(child_account)
            self._sold_accounts[child_account.id] = sold_account
            if self._display_account == 'movement':
                if child_account.type != 'view' and num_entry <> 0:
                    res.append(child_account)
            elif self._display_account == 'not_zero':
                if child_account.type != 'view' and num_entry <> 0:
                    if not currency_obj.is_zero(self.cr, self.uid, currency, sold_account):
                        res.append(child_account)
            else:
                res.append(child_account)
        if not res:
            return [account]
        return res
    

    def lines(self, account):
        """ Return all the account_move_line of account with their account code counterparts """
        move_state = ['draft','posted']
        if self._target_move == 'posted':
            move_state = ['posted', '']
        # First compute all counterpart strings for every move_id where this account appear.
        # Currently, the counterpart info is used only in landscape mode
        sql = """
            SELECT m1.move_id,
                array_to_string(ARRAY(SELECT DISTINCT a.code
                                          FROM account_move_line m2
                                          LEFT JOIN account_account a ON (m2.account_id=a.id)
                                          WHERE m2.move_id = m1.move_id
                                          AND m2.account_id<>%%s), ', ') AS counterpart
                FROM (SELECT move_id
                        FROM account_move_line l
                        LEFT JOIN account_move am ON (am.id = l.move_id)
                        WHERE am.state IN %s and %s AND l.account_id = %%s GROUP BY move_id) m1
        """% (tuple(move_state), self.query)
        self.cr.execute(sql, (account.id, account.id))
        counterpart_res = self.cr.dictfetchall()
        counterpart_accounts = {}
        for i in counterpart_res:
            counterpart_accounts[i['move_id']] = i['counterpart']
        del counterpart_res

        # Then select all account_move_line of this account
        if self._sortby == 'sort_journal_partner':
            sql_sort='j.code, p.name, l.move_id'
        else:
            sql_sort='l.date, l.move_id'
        sql = """
            SELECT l.id AS lid, l.date AS ldate, j.code AS lcode, l.currency_id,l.amount_currency,l.ref AS lref, l.name AS lname, COALESCE(l.debit,0) AS debit, COALESCE(l.credit,0) AS credit, l.period_id AS lperiod_id, l.partner_id AS lpartner_id,
            m.name AS move_name, m.id AS mmove_id,per.code as period_code,
            c.symbol AS currency_code,
            i.id AS invoice_id, i.type AS invoice_type, i.number AS invoice_number,
            p.name AS partner_name
            FROM account_move_line l
            JOIN account_move m on (l.move_id=m.id)
            LEFT JOIN res_currency c on (l.currency_id=c.id)
            LEFT JOIN res_partner p on (l.partner_id=p.id)
            LEFT JOIN account_invoice i on (m.id =i.move_id)
            LEFT JOIN account_period per on (per.id=l.period_id)
            JOIN account_journal j on (l.journal_id=j.id)
            WHERE %s AND m.state IN %s AND l.account_id = %%s ORDER by %s
        """ %(self.query, tuple(move_state), sql_sort)
        self.cr.execute(sql, (account.id,))
        res_lines = self.cr.dictfetchall()
        res_init = []
        if res_lines and self._init_balance:
            #FIXME: replace the label of lname with a string translatable
            sql = """
                SELECT 0 AS lid, '' AS ldate, '' AS lcode, COALESCE(SUM(l.amount_currency),0.0) AS amount_currency, '' AS lref, 'Initial Balance' AS lname, COALESCE(SUM(l.debit),0.0) AS debit, COALESCE(SUM(l.credit),0.0) AS credit, '' AS lperiod_id, '' AS lpartner_id,
                '' AS move_name, '' AS mmove_id, '' AS period_code,
                '' AS currency_code,
                NULL AS currency_id,
                '' AS invoice_id, '' AS invoice_type, '' AS invoice_number,
                '' AS partner_name
                FROM account_move_line l
                LEFT JOIN account_move m on (l.move_id=m.id)
                LEFT JOIN res_currency c on (l.currency_id=c.id)
                LEFT JOIN res_partner p on (l.partner_id=p.id)
                LEFT JOIN account_invoice i on (m.id =i.move_id)
                JOIN account_journal j on (l.journal_id=j.id)
                WHERE %s AND m.state IN %s AND l.account_id = %%s
            """ %(self.query, tuple(move_state))
            self.cr.execute(sql, (account.id,))
            res_init = self.cr.dictfetchall()
        res = res_init + res_lines
        account_sum = 0.0
        for l in res:
            l['move'] = l['move_name'] != '/' and l['move_name'] or ('*'+str(l['mmove_id']))
            l['partner'] = l['partner_name'] or ''
            account_sum += l['debit'] - l['credit']
            l['progress'] = account_sum
            l['line_corresp'] = l['mmove_id'] == '' and ' ' or counterpart_accounts[l['mmove_id']].replace(', ',',')
            # Modification of amount Currency
            if l['credit'] > 0:
                if l['amount_currency'] != None:
                    l['amount_currency'] = abs(l['amount_currency']) * -1
            if l['amount_currency'] != None:
                self._tot_currency = self._tot_currency + l['amount_currency']
        return res

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
        
    def export_balance(self, cr, uid, ids,data,fp, context=None):
        header_p = ['Plan Comptable','Exercice Fiscal','Journaux','Afficher le compte',unicode('Filtré par Pas de filtre', "utf8"),unicode('Écritures triés par',"utf8"),'Mouvements Cibles']
        header = ['Compte','Date',unicode('Période', "utf8"),'JRNL','Partenaire',unicode('Réf.',"utf8"),unicode('N° d\'écriture',"utf8"),unicode('Libellé de la pièce comptable',"utf8"),unicode('Débit',"utf8"),unicode('Crédit',"utf8"),'Solde de la balance','Devises','Type de Compte']
        
        data_header_p = self.get_content_header_p()
        
        font0 = xlwt.Font()
        font0.name = 'Arial'
        font0.colour_index = 2
        font0.bold = True
        font0.height = 350

        

        
        font1 = xlwt.Font()
        font1.name = 'Arial'
        font1.colour_index = 0
        font1.bold = True
        
        font2 = xlwt.Font()
        font2.name = 'Arial'
        font2.colour_index = 2
        font2.bold = True
        font2.height = 280
        
        font3 = xlwt.Font()
        font3.name = 'Arial'
        font3.colour_index = 2
        font3.bold = True
        font3.height = 200
        
        font4 = xlwt.Font()
        font4.name = 'Arial'
        font4.colour_index = 63
        font4.bold = True
        
        font5 = xlwt.Font()
        font5.name = 'Arial'
        font0.colour_index = 2

        style0 = xlwt.XFStyle()
        style0.font = font0
        
        style1 = xlwt.XFStyle()
        style1.font = font2
        
        alignement = xlwt.Alignment()
        alignement.horz = xlwt.Alignment.HORZ_RIGHT
        
        style2 = xlwt.XFStyle()
        style2.num_format_str = '#,##0.00'
        style2.font = font1
        style2.alignment = alignement
        
        borders = Borders()
        borders.left = 1
        borders.right = 1
        borders.top = 1
        borders.bottom = 1
        
        style3 = xlwt.XFStyle()
        style3.font = font4
        style3.borders = borders
        
        style4 = xlwt.XFStyle()
        style4.font = font5
        style4.alignment = alignement
        
        style5 = xlwt.XFStyle()
        style5.font = font5
        style5.num_format_str = '#,##0.00'
        
        style6 = xlwt.XFStyle()
        style6.font = font3
        
        style7 = xlwt.XFStyle()
        style7.font = font1
        style7.borders = borders
        
        style8 = xlwt.XFStyle()
        style8.font = font1
        
        style9 = xlwt.XFStyle()
        style9.font = font5

        date_edit = time.strftime('%d/%m/%y %H:%M',time.localtime())

        wb = xlwt.Workbook()
        ws = wb.add_sheet('grand_livre')
        
        ws.write(0, 0, 'GRAND LIVRE', style0)
        ws.write(1, 0, unicode('Société : ',"utf8")+data[0].company_id.name, style1)
        ws.write(2, 0, unicode('Date d\'édition : ',"utf8")+date_edit, style6)
        
        ws.row(0).height = 500
        ws.row(1).height = 500
        ws.row(2).height = 400
        ws.row(5).height = 2000
        
        ws.col(0).width = 21000
        ws.col(1).width = 5000
        ws.col(2).width = 2500
        ws.col(3).width = 5500
        ws.col(4).width = 5500
        ws.col(5).width = 5000
        ws.col(6).width = 6500
        ws.col(7).width = 7500
        ws.col(8).width = 4000
        ws.col(9).width = 4000
        ws.col(10).width = 4100
        ws.col(11).width = 4000
        ws.col(12).width = 4000

        

        for i in range(len(header_p)) :
            ws.write(4,i,header_p[i], style3)
            ws.write(5,i,data_header_p[i],style3)
        for i in range(len(header)) :
            ws.write(7,i,header[i],style7)
        ws.write(4,7,'Devise', style3)
        ws.write(5,7,data[0].company_id.currency_id.symbol,style3)
        position = 0
        for j in range(len(data)) :
            type_compte = self._traduction_type(data[j].type)
            ws.write(j+position+8,0,data[j].code+' '+data[j].name ,style8)
            ws.write(j+position+8,8,self._sum_debit_account(data[j]), style2)
            ws.write(j+position+8,9,self._sum_credit_account(data[j]), style2)
            ws.write(j+position+8,10,self._sum_balance_account(data[j]), style2)
            data_by_account = self.lines(data[j])
            for k in range(len(data_by_account)) :
                if data_by_account[k]['ldate'] :
                    d = datetime.strptime(data_by_account[k]['ldate'],'%Y-%m-%d')
                    d = datetime.strftime(d,'%d/%m/%Y')
                    ws.write(j+k+position+9,1,d,style9)
                else :
                    ws.write(j+k+position+9,1,'')
                ws.write(j+k+position+9,0,data[j].code+' '+data[j].name,style9)
                ws.write(j+k+position+9,2,data_by_account[k]['period_code'],style9)
                ws.write(j+k+position+9,3,data_by_account[k]['lcode'],style9)
                ws.write(j+k+position+9,4,data_by_account[k]['partner_name'],style9)
                ws.write(j+k+position+9,5,data_by_account[k]['lref'],style9)
                ws.write(j+k+position+9,6,data_by_account[k]['move'],style9)
                ws.write(j+k+position+9,7,data_by_account[k]['lname'],style9)
                ws.write(j+k+position+9,8,data_by_account[k]['debit'], style5)
                ws.write(j+k+position+9,9,data_by_account[k]['credit'], style5)
                ws.write(j+k+position+9,10,data_by_account[k]['progress'], style5)
                ws.write(j+k+position+9,11,self._tot_currency, style5)
                ws.write(j+k+position+9,12,unicode(type_compte,"utf8"), style9)
            position += len(data_by_account)
                
        wb.save(fp)

    def _print_report(self, cr, uid, ids, data, context=None):
        this = self.browse(cr,uid,ids)[0]
        
        if this.type_report == 'pdf' :
            if context is None:
                context = {}
            data = self.pre_print_report(cr, uid, ids, data, context=context)
            data['form'].update(self.read(cr, uid, ids, ['landscape',  'initial_balance', 'amount_currency', 'sortby'])[0])
            if not data['form']['fiscalyear_id']:# GTK client problem onchange does not consider in save record
                data['form'].update({'initial_balance': False})
    
            if data['form']['landscape'] is False:
                data['form'].pop('landscape')
            return self.pool['report'].get_action(cr, uid, [], 'account.report_generalledger', data=data, context=context)

        if this.type_report == 'excel' :
            self._chart_account_id = this.chart_account_id
            self._fiscalyear_id = this.fiscalyear_id
            self._journal_ids = this.journal_ids
            self._display_account = this.display_account
            self._filter = this.filter
            self._sortby = this.sortby
            self._target_move = this.target_move
            self._init_balance = this.initial_balance
            self._tot_currency = 0.0
            self._sold_accounts = {}
            self.cr = cr
            self.uid = uid
            self.context = context
            obj_move = self.pool.get('account.move.line')
            data = self.pre_print_report(cr, uid, ids, data, context=context)
            self.query = obj_move._query_get(self.cr, self.uid, obj='l',context=data['form'].get('used_context',{}))
            data1 = self.get_children_accounts(this.chart_account_id)
            buf=StringIO()
            self.export_balance(cr, uid, ids,data1,buf,context)
            out=base64.encodestring(buf.getvalue())
            buf.close()
            #date_day = datetime.now()
            date_day = time.strftime('%d/%m/%y_%H-%M-%S',time.localtime())
            fichier="grand_livre_"+str(date_day)+".xls"
            wizard_id = self.pool.get('account.general.ledger.export').create(cr, uid, {'data':out,'name':fichier,'state':'get'}, context=dict(context, active_ids=ids))
            return {
                    'name':"Export Excel",
                    'view_mode': 'form',
                    'view_id':False,
                    'view_type': 'form',
                    'res_model': 'account.general.ledger.export',
                    'res_id': wizard_id,
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'domain': '[]',
                    'context': dict(context, active_ids=ids)
                }


account_report_general_ledger()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
