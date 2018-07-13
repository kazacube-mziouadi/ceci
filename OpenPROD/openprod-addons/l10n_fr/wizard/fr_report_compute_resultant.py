# -*- coding: utf-8 -*-


from openerp.osv import fields, osv


class account_cdr_report(osv.osv_memory):
    _name = 'account.cdr.report'
    _description = 'Account CDR Report'

    def _get_defaults(self, cr, uid, context=None):
        fiscalyear_id = self.pool.get('account.fiscalyear').find(cr, uid)
        return fiscalyear_id

    _columns = {
        'fiscalyear_id': fields.many2one('account.fiscalyear', 'Fiscal Year', required=True),
    }

    _defaults = {
        'fiscalyear_id': _get_defaults
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
