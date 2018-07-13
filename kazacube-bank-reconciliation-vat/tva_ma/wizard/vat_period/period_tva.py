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

from openerp.osv import fields, osv
from openerp.tools.translate import _
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

class period_tva_inv(osv.osv_memory):
    _name = "period.tva.inv"
    _description = "Creation des Periodes TVA"
    _columns = {
       'date_start': fields.date('Start of Period', required=True),
       'date_stop': fields.date('End of Period', required=True),
       'fiscalyear_id': fields.many2one('account.fiscalyear', 'Fiscal Year', required=True, select=True),
    }
    
    def onchange_fiscalyear_id(self, cr, uid, ids, fiscalyear_id):
        v = {}
        if fiscalyear_id:
            fiscalyear = self.pool.get('account.fiscalyear').browse(cr, uid,fiscalyear_id)
            v['date_start'] = fiscalyear.date_start
            v['date_stop'] = fiscalyear.date_stop
        return {'value': v}
    
    def transformer_number(self,number,interval):
        if interval == 3:
            if number == 1 :
                return 'Premier trimestre'
            if number == 2 :
                return 'Deuxième trimestre'
            if number == 3 :
                return 'Troisième trimestre'
            if number == 4 :
                return 'Quatrième trimestre'
            if number == 5 :
                return 'Cinquième trimestre'
            if number == 6 :
                return 'Sixième trimestre'
            if number == 7 :
                return 'Septième trimestre'
            if number == 8 :
                return 'Huitième trimestre'
            if number == 9 :
                return 'Neuvième trimestre'
            if number == 10 :
                return 'Dixième trimestre'
            if number == 11 :
                return 'Onzième trimestre'
            if number == 12 :
                return 'Douzième trimestre'
        else:
            if number == 1 :
                return 'Janvier'
            if number == 2 :
                return 'Février'
            if number == 3 :
                return 'Mars'
            if number == 4 :
                return 'Avril'
            if number == 5 :
                return 'Mai'
            if number == 6 :
                return 'Juin'
            if number == 7 :
                return 'Juillet'
            if number == 8 :
                return 'Août'
            if number == 9 :
                return 'Septembre'
            if number == 10 :
                return 'Octobre'
            if number == 11 :
                return 'Novembre'
            if number == 12 :
                return 'Décembre'

        
    def create_period3(self,cr, uid, ids, context=None):
        return self.create_t_period(cr, uid, ids, context, 3)
    
    def create_period1(self,cr, uid, ids, context=None):
        return self.create_m_period(cr, uid, ids, context, 1)


    def create_m_period(self,cr, uid, ids, context=None, interval=1):
        print 'interval',interval
        period_tva_obj = self.browse(cr, uid, ids[0], context=context)
        obj_period_tva = self.pool.get('account.period.tva')  
              
        ds = datetime.strptime(period_tva_obj.date_start, '%Y-%m-%d')
        num_period = 1
        while ds.strftime('%Y-%m-%d')< period_tva_obj.date_stop:
            print num_period
            de = ds + relativedelta(months=interval, days=-1)
            if de.strftime('%Y-%m-%d') > period_tva_obj.date_stop:
                de = datetime.strptime( period_tva_obj.date_stop, '%Y-%m-%d')
            obj_period_tva.create(cr, uid, {
                    'name': str(num_period)+'/'+ds.strftime('%Y'),
                    'code': 'M'+str(num_period),
                    'date_start': ds.strftime('%Y-%m-%d'),
                    'date_stop': de.strftime('%Y-%m-%d'),
                    'fiscalyear_id': period_tva_obj.fiscalyear_id.id,
                    'description':self.transformer_number(num_period,interval)+' '+ds.strftime('%Y'),
                    'title1':'CA_imposable'+' '+str(num_period)+'-'+ds.strftime('%Y'),
                    'title2':'TVA_deductible'+' '+str(num_period)+'-'+ds.strftime('%Y'),
                    'type' :interval,
                })
            ds = ds + relativedelta(months=interval)
            num_period = num_period + 1

    def create_t_period(self,cr, uid, ids, context=None, interval=1):
        print 'interval',interval
        period_tva_obj = self.browse(cr, uid, ids[0], context=context)
        obj_period_tva = self.pool.get('account.period.tva')

        ds = datetime.strptime(period_tva_obj.date_start, '%Y-%m-%d')
        num_period = 1
        while ds.strftime('%Y-%m-%d')< period_tva_obj.date_stop:
            print num_period
            de = ds + relativedelta(months=interval, days=-1)
            if de.strftime('%Y-%m-%d') > period_tva_obj.date_stop:
                de = datetime.strptime( period_tva_obj.date_stop, '%Y-%m-%d')
            obj_period_tva.create(cr, uid, {
                    'name': 'T'+str(num_period)+'/'+ds.strftime('%Y'),
                    'code': 'T'+str(num_period),
                    'date_start': ds.strftime('%Y-%m-%d'),
                    'date_stop': de.strftime('%Y-%m-%d'),
                    'fiscalyear_id': period_tva_obj.fiscalyear_id.id,
                    'description':self.transformer_number(num_period,interval)+' '+ds.strftime('%Y'),
                    'title1':'CA_imposable'+' '+'T'+str(num_period)+'-'+ds.strftime('%Y'),
                    'title2':'TVA_deductible'+' '+'T'+str(num_period)+'-'+ds.strftime('%Y'),
                    'type' :interval,
                })
            ds = ds + relativedelta(months=interval)
            num_period = num_period + 1
            
        
        return {'type': 'ir.actions.act_window_close'}

period_tva_inv()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: