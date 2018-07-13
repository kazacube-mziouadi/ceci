# -*- coding: utf-8 -*-

{
    'name': 'France - Accounting',
    'version': '1.2',
    'author': 'Objectif-pi OpenERP SA',
    'license': 'LGPL',
    'website': 'http://www.openerp.com',
    'category': 'Localization/Account Charts',
    'description': """
This is the module to manage the accounting chart for France.
========================================================================

This module applies to companies based in France mainland. It doesn't apply to
companies based in the DOM-TOMs (Guadeloupe, Martinique, Guyane, Réunion, Mayotte).

This localisation module creates the VAT taxes of type 'tax included' for purchases
(it is notably required when you use the module 'hr_expense'). Beware that these
'tax included' VAT taxes are not managed by the fiscal positions provided by this
module (because it is complex to manage both 'tax excluded' and 'tax included'
scenarios in fiscal positions).

""",
    'depends': ['base_iban', 'account_openprod', 'account_chart', 'base_vat'],
    'data': [
        'views/report_l10nfrbilan.xml',
        'views/report_l10nfrresultat.xml',
        'fr_report.xml',
        'plan_comptable_general.xml',
        'l10n_fr_wizard.xml',
        'fr_pcg_taxes.xml',
        'fr_tax.xml',
        'fr_fiscal_templates.xml',
        'security/ir.model.access.csv',
        'wizard/fr_report_bilan_view.xml',
        'wizard/fr_report_compute_resultant_view.xml',
    ],
    'test': ['test/l10n_fr_report.yml'],
    'demo': [],
    'auto_install': False,
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
