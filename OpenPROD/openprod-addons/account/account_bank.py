# -*- coding: utf-8 -*-


from openerp.tools.translate import _
from openerp.osv import fields, osv

class bank(osv.osv):
    _inherit = "res.partner.bank"
    _columns = {
        'journal_id': fields.many2one('account.journal', 'Account Journal', help="This journal will be created automatically for this bank account when you save the record"),
    }

    def _prepare_name_get(self, cr, uid, bank_dicts, context=None):
        """Add ability to have %(currency_name)s in the format_layout of res.partner.bank.type"""
        currency_ids = list(set(data['currency_id'][0] for data in bank_dicts if data.get('currency_id')))
        currencies = self.pool.get('res.currency').browse(cr, uid, currency_ids, context=context)
        currency_name = dict((currency.id, currency.name) for currency in currencies)

        for data in bank_dicts:
            data['currency_name'] = data.get('currency_id') and currency_name[data['currency_id'][0]] or ''
        return super(bank, self)._prepare_name_get(cr, uid, bank_dicts, context=context)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
