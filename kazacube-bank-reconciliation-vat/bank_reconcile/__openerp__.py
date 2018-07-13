# -*- coding: utf-8 -*-
##############################################################################
#
#    printers_kazacube module for OpenERP, Specific changes for Kazacube
#    Copyright (C) 2013 SYLEAM Info Services (<http://www.Syleam.fr/>)
#              Sylvain Garancher <sylvain.garancher@syleam.fr>
#
#    This file is a part of printers_kazacube
#
#    printers_kazacube is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    printers_kazacube is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Bank Reconcile',
    'version': '1.0',
    'category': 'Custom',
    'description': """Specific changes for Kazacube""",
    'author': 'KAZACUBE',
    'website': 'http://www.kazacube.com/',
    'depends': ["account","account_payment","account_voucher","web","product"],
    'init_xml': [],
    'images': [],
    'update_xml': [
        'report/account_bank_reconcile_report.xml',
        'report/report_situation_rapprochement.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/bank_statement_view.xml',
        'views/bank_reconcile_view.xml',
        'views/account_move_line_view.xml',
        'views/bank_operation.xml',
        'wizard/wizard_view.xml',
        'sequences/statement_reconciliation_sequence.xml',
        'wizard/mette_ecritures_exception_view.xml',
        'wizard/open_ecritures_exception_view.xml',
        'wizard/correction_bank_line_exception_view.xml',
        'wizard/list_not_rapproched_view.xml',
        'wizard/cancel_reconcile_line_view.xml',
       ],
    'demo_xml': [],
    'test': [],
    'css':['static/src/css/bank_reconcile.css'],
    #'external_dependancies': {'python': ['kombu'], 'bin': ['which']},
    'installable': True,
    'active': True,
    'license': 'AGPL-3',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
