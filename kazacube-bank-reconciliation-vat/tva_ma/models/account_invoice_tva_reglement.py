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

class account_invoice_tva_reglement(osv.osv):
    _name = "account.invoice.tva.reglement"
    _description = ""
    _columns = {
        'name': fields.char('Methode de reglement', size=256, required=True),
        'id_xml': fields.integer(' ID XML',  required=True),
    }
 
account_invoice_tva_reglement()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


