# -*- coding: utf-8 -*-

from openerp.osv import fields, osv
from openerp.tools.translate import _

class project_account_analytic_line(osv.osv_memory):
    _name = "project.account.analytic.line"
    _description = "Analytic Entries by line"
    _columns = {
        'from_date': fields.date('From'),
         'to_date': fields.date('To'),
    }

    def action_open_window(self, cr, uid, ids, context=None):
        mod_obj =self.pool.get('ir.model.data')
        domain = []
        data = self.read(cr, uid, ids, [])[0]
        from_date = data['from_date']
        to_date = data['to_date']
        if from_date and to_date:
            domain = [('date','>=',from_date), ('date','<=',to_date)]
        elif from_date:
            domain = [('date','>=',from_date)]
        elif to_date:
            domain = [('date','<=',to_date)]
        result = mod_obj.get_object_reference(cr, uid, 'account', 'view_account_analytic_line_filter')
        id = result and result[1] or False
        return {
              'name': _('Analytic Entries by line'),
              'view_type': 'form',
              "view_mode": 'tree,form',
              'res_model': 'account.analytic.line',
              'type': 'ir.actions.act_window',
              'domain': domain,
              'search_view_id': id['res_id'],
              }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
