# -*- coding: utf-8 -*-


from openerp.osv import fields, osv

# Redéfinit en nouvelle API 
# class account_analytic_journal(osv.osv):
#     _name = 'account.analytic.journal'
#     _description = 'Analytic Journal'
#     _columns = {
#         'name': fields.char('Journal Name', required=True),
#         'code': fields.char('Journal Code', size=8),
#         'active': fields.boolean('Active', help="If the active field is set to False, it will allow you to hide the analytic journal without removing it."),
#         'type': fields.selection([('sale','Sale'), ('purchase','Purchase'), ('cash','Cash'), ('general','General'), ('situation','Situation')], 'Type', required=True, help="Gives the type of the analytic journal. When it needs for a document (eg: an invoice) to create analytic entries, Odoo will look for a matching journal of the same type."),
#         'line_ids': fields.one2many('account.analytic.line', 'journal_id', 'Lines', copy=False),
#         'company_id': fields.many2one('res.company', 'Company', required=True),
#     }
#     _defaults = {
#         'active': True,
#         'type': 'general',
#         'company_id': lambda self,cr,uid,c: self.pool.get('res.users').browse(cr, uid, uid, c).company_id.id,
#     }


class account_journal(osv.osv):
    _inherit="account.journal"

    _columns = {
        'analytic_journal_id':fields.many2one('account.analytic.journal','Analytic Journal', help="Journal for analytic entries"),
    }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
