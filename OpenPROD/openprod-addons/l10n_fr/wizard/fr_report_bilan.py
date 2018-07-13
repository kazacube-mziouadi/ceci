# -*- coding: utf-8 -*-


from openerp.osv import fields, osv


class account_bilan_report(osv.osv_memory):
    _name = 'account.bilan.report'
    _description = 'Account Bilan Report'

    def _get_default_fiscalyear(self, cr, uid, context=None):
        fiscalyear_id = self.pool.get('account.fiscalyear').find(cr, uid)
        return fiscalyear_id

    _columns = {
        'fiscalyear_id': fields.many2one('account.fiscalyear', 'Fiscal Year', required=True),
    }

    _defaults = {
        'fiscalyear_id': _get_default_fiscalyear
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
