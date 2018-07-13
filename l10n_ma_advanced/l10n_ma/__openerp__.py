# -*- encoding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

    'name' : ' Maroc - Plan Comptable Général',
    'version' : '1.0',
    'author' : 'kazacube',
    'category' : 'Localization/Account Charts',
    'description': """
This is the base module to manage the accounting chart for Maroc.
==================================================================================
Ce Module charge le modèle du plan de comptes standard Marocain et permet de
générer les états comptables aux normes marocaines (Bilan, CPC (comptes de
produits et charges), balance générale à 6 colonnes, Grand livre cumulatif...).
L'intégration comptable a été validé avec l'aide du Cabinet d'expertise comptable
Seddik au cours du troisième trimestre 2010.

Dates des mises à jour : 
* 16/06/2016 : adaptation des rapprots , menus , vues
* 15/08/2016 : ajout du module account_voucher comme dependance""",


    'website': 'http://www.kazacube.com',
    'depends' : ['base','account','account_openprod'],
    'data' : [
                    'security/compta_security.xml',
                    'security/ir.model.access.csv',
                    'account_type.xml',
                    'account.xml',
                    'account_pcg_morocco.xml',
                    'l10n_ma_tax.xml',
                    'l10n_ma_wizard.xml',
                    'accounts_templates.xml',
                    'l10n_ma_journal.xml',
                    'wizard/balance_fyear.xml',    
                    'wizard/bilan.xml',
                    'wizard/cdr.xml',
                    'wizard/general_ledger_view.xml',
                    'export_report.xml'
    ],
    'demo' : [],
    'auto_install': False,
    'installable': True,
     "active": True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

