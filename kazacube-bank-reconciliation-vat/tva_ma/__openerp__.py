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
{
    'name': 'Gestion de la TVA',
    'version': '0.1',
    'category': 'Accounting',
    'description': """
        Gestion TVA sur les encaissements;
        Module développé pour gérer la TVA sur les encaissements, incluant le suivi de la TVA collectée et le pointage de la TVA déductible par taux de TVA, le tout par période de déclaration (mensuelle ou trimestrielle)
        Permet de générer des rapports aux normes marocaines en format excel
    """,
    'author': 'Kazacube',
    'website': 'http://www.kazacube.com',
    'depends': ['account','l10n_ma','bank_reconcile','report_xls'],
    'init_xml': [],
    'update_xml': [
        "security/ir.model.access.csv",
        'views/account_invoice_tva_reglemnt_view.xml',
        'views/account_voucher_view.xml',
        'views/vat_statement_view.xml',
        'wizard/vat_period/period_tva_view.xml',
        'wizard/vat_report/vat_report_wizard_view.xml',
        'wizard/bank_lines_tax_edit/bank_lines_tax_edit_wizard_view.xml',
        'wizard/move_lines_tax_edit/move_lines_tax_edit_wizard_view.xml',
        'wizard/get_vat_from_move_lines/move_lines_vat_wizard_view.xml',
        'wizard/wizard_tva_xml/xml_wizard_view.xml',
        'wizard/wizard_tva_xml/template_wizard_xml.xml',
        'data/tva_data.xml',


    ],
    'demo_xml': [
     
    ],
    'test':[
    
    ],
    'installable': True,
    'certificate': '',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
