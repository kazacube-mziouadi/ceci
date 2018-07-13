# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from mx import DateTime
import time

from openerp.osv import fields, osv


class l10n_ma_report(osv.osv):
    _name = 'l10n.ma.report'
    _description = 'Report for l10n_ma_kzc'
    _columns = {
        'code': fields.char('Code', size=64),
        'name': fields.char('Name', size=128),
        'line_ids': fields.one2many('l10n.ma.line', 'report_id', 'Lines'),
    }
    _sql_constraints = [
                ('code_uniq', 'unique (code)','The code report must be unique !')
        ]
l10n_ma_report()

class l10n_ma_line(osv.osv):
    _name = 'l10n.ma.line'
    _description = 'Report Lines for l10n_ma'
    _columns = {
        'code': fields.char('Variable Name', size=64),
        'definition': fields.char('Definition', size=512),
        'name': fields.char('Name', size=256),
        'report_id': fields.many2one('l10n.ma.report', 'Report'),
    }
    _sql_constraints = [
            ('code_uniq', 'unique (code)', 'The variable name must be unique !')
    ]
l10n_ma_line()

class account_journal(osv.osv):
    _inherit = "account.journal"

    _columns = {
        'entry_posted': fields.boolean('Autopost Created Moves',
                                   help='Check this box to automatically post entries of this journal. Note that legally, some entries may be automatically posted when the source document is validated (Invoices), whatever the status of this field.'),
    }

    _defaults = {
        'entry_posted': False,
    }

account_journal()

class res_company(osv.osv):
    _inherit = 'res.company'

    _columns = {
        'siret': fields.char('Registre de commerce', size=32),
        'ape': fields.char('ICE', size=32),
    }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: