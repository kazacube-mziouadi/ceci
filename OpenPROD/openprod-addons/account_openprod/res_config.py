# -*- coding: utf-8 -*-
import openerp
from openerp.tools.translate import _
from openerp.osv import fields, osv


class account_config_settings(osv.osv_memory):
    _inherit = 'account.config.settings'
    
    _columns = {
                'print_delivered_address': fields.related('company_id', 'print_delivered_address', type='boolean',
                string='Print delivered address on invoices'),
                'us_accounting': fields.related('company_id', 'us_accounting', type='boolean',
                string='Canada accounting'),
                }
    
    
    def onchange_company_id(self, cr, uid, ids, company_id, context=None):
        res = super(account_config_settings, self).onchange_company_id(cr, uid, ids, company_id=company_id, context=context)
        if not res.get('value'):
            res['value'] = {}
            
        if company_id:
            company = self.pool.get('res.company').browse(cr, uid, company_id, context=context)
            res['value']['print_delivered_address'] = company.print_delivered_address
            res['value']['us_accounting'] = company.us_accounting

        return res
    