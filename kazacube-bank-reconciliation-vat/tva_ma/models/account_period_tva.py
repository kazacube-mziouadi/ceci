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

from openerp.osv import osv
from openerp.osv import fields
from openerp.tools.translate import _
import time

class account_period_tva(osv.osv):
    _name = "account.period.tva"
    _rec_name = "description"
    _description = "Account period tva"
    _columns = {
        'name': fields.char('Période', size=64, required=True),
        'code': fields.char('Code', size=12),
        'special': fields.boolean('Opening/Closing Period', size=12,
            help="These periods can overlap."),
        'date_start': fields.date('Début de periode', required=True, states={'done':[('readonly',True)]}),
        'date_stop': fields.date('Fin de periode', required=True, states={'done':[('readonly',True)]}),
        'fiscalyear_id': fields.many2one('account.fiscalyear', 'Fiscal Year', required=True, states={'done':[('readonly',True)]}, select=True),
        'state': fields.selection([('draft','Open'), ('done','Closed')], 'Status', readonly=True,
                                  help='When monthly periods are created. The state is \'Draft\'. At the end of monthly period it is in \'Done\' state.'),
        'company_id': fields.related('fiscalyear_id', 'company_id', type='many2one', relation='res.company', string='Company', store=True, readonly=True),
        'description': fields.char('Description', size=512),
        'title1': fields.char('Title CA Imposable', size=512),
        'title2': fields.char('Title TVA Deductible', size=512),
        'type':fields.integer('Type of TVA',readonly=True),
    }
    _defaults = {
        'state': 'draft',
    }
    _order = "date_start"

account_period_tva()




# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


