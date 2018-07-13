# -*- coding: utf-8 -*-
from operator import itemgetter
import time

from openerp.osv import fields, osv
from openerp import api

class res_partner(osv.osv):
    _name = 'res.partner'
    _inherit = 'res.partner'
    _description = 'Partner'
    
    
    def _get_property_account_payable_id(self, cr, uid, ids, name, arg, context=None):
        res = {}
        mcpap_obj = self.pool.get('multi.company.partner.acc.payable')
        user_obj = self.pool.get ('res.users')
        for id in ids:
            user = user_obj.browse(cr, uid, uid, context=context)
            mcpap_ids = mcpap_obj.search(cr, uid, [('partner_id', '=', id), ('company_id', '=', user.company_id.id)], limit=1, context=context)
            if mcpap_ids:
                mcpap = mcpap_obj.browse(cr, uid, mcpap_ids[0], context=context)
                res[id] = mcpap.account_id.id
            else:
                res[id] = False
                
        return res
    
    
    def _get_property_account_receivable_id(self, cr, uid, ids, name, arg, context=None):
        res = {}
        mcpar_obj = self.pool.get('multi.company.partner.acc.receivable')
        user_obj = self.pool.get ('res.users')
        for id in ids:
            user = user_obj.browse(cr, uid, uid, context=context)
            mcpar_ids = mcpar_obj.search(cr, uid, [('partner_id', '=', id), ('company_id', '=', user.company_id.id)], limit=1, context=context)
            if mcpar_ids:
                mcpar = mcpar_obj.browse(cr, uid, mcpar_ids[0], context=context)
                res[id] = mcpar.account_id.id
            else:
                res[id] = False
                
        return res
    
    
    def _get_property_account_position_id(self, cr, uid, ids, name, arg, context=None):
        res = {}
        mcpfps_obj = self.pool.get('multi.company.partner.fiscal.position.sale')
        user_obj = self.pool.get ('res.users')
        for id in ids:
            user = user_obj.browse(cr, uid, uid, context=context)
            mcpfps_ids = mcpfps_obj.search(cr, uid, [('partner_id', '=', id), ('company_id', '=', user.company_id.id)], limit=1, context=context)
            if mcpfps_ids:
                mcpfps = mcpfps_obj.browse(cr, uid, mcpfps_ids[0], context=context)
                res[id] = mcpfps.account_position_id.id
            else:
                res[id] = False
                
        return res
    
    
    _columns = {
        'property_account_payable_id': fields.function(_get_property_account_payable_id, type='many2one',
           relation='account.account', string='Account Payable',  store=False,
            help="This account will be used instead of the default one as the payable account for the current partner"),
        'property_account_receivable_id': fields.function(_get_property_account_receivable_id, type='many2one',
           relation='account.account', string='Account Receivable', store=False,
            help="This account will be used instead of the default one as the receivable account for the current partner"),
                
        'property_account_position_id': fields.function(_get_property_account_position_id,
           relation='account.fiscal.position', type='many2one', string='Fiscal Position',  store=False,
            help="The fiscal position will determine taxes and accounts used for the partner.",
            oldname="property_account_position"),

    }