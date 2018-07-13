# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2008 JAILLET Simon - CrysaLEAD - www.crysalead.fr
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################
from openerp.osv import fields,osv
from openerp.tools.translate import _
import time

class bilan(osv.osv_memory):
   
    _name = 'bilan'
    _description = 'Bilan Report'
    _columns = {
        'fiscalyear':fields.many2one('account.fiscalyear','Exercice Fiscal',required=True),
        'fiscalyear2':fields.many2one('account.fiscalyear','Exercice de reference',required=True)
        }

    def _get_default_fiscalyear(self, cr, uid, context=None):
        fiscalyear = self.pool.get('account.fiscalyear').find(cr, uid)
        return fiscalyear

	_defaults = {
        'fiscalyear':_get_default_fiscalyear,
		
    }


    def print_bilan_report(self, cr, uid, ids, context=None):
        active_ids = context.get('active_ids', [])
        data = {}
        data['form'] = {}
        data['ids'] = active_ids
        data['form']['fiscalyear'] = self.browse(cr, uid, ids)[0].fiscalyear.id
        data['form']['fiscalyear2'] = self.browse(cr, uid, ids)[0].fiscalyear2.id
		
        return {'type': 'ir.actions.report.xml', 'report_name': 'l10n.ma.bilan', 'datas': data}
bilan()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

