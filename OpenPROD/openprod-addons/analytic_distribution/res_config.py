# -*- coding: utf-8 -*-
import openerp
from openerp.tools.translate import _
from openerp.osv import fields, osv


class account_config_settings(osv.osv_memory):
    _inherit = 'account.config.settings'
    
    _columns = {
                'check_analytic_amount': fields.related('company_id', 'check_analytic_amount', type='boolean',
                string='Check analytic amount',help="Check this field if you want to check if the total analytic "
                "amount is equal to the total without taxes of the invoice when you validate an invoice"),
                }
    
    
    def onchange_company_id(self, cr, uid, ids, company_id, context=None):
        res = super(account_config_settings, self).onchange_company_id(cr, uid, ids, company_id=company_id, context=context)
        if not res.get('value'):
            res['value'] = {}
            
        if company_id:
            company = self.pool.get('res.company').browse(cr, uid, company_id, context=context)
            res['value']['check_analytic_amount'] = company.check_analytic_amount

        return res
    
