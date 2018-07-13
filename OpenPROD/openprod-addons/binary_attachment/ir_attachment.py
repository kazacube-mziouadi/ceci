# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 Objectif-PI (<http://www.objectif-pi.com>).
#       Damien CRIER <damien.crier@objectif-pi.com>
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


from openerp import models, fields, api, _
from openerp.exceptions import Warning

class ir_attachment(models.Model):
    """ Attachments """
    _inherit = 'ir.attachment'

    #===========================================================================
    # COLUMNS
    #===========================================================================
    is_binary_field = fields.Boolean(string='Is binary field', default=False, readonly=True, help="If checked, this attachment has been created from a binary field")
    binary_field = fields.Char(size=64, readonly=True, help="Name of the field in the record")


# class product_product(models.Model):
#     """ """
#     _inherit = 'product.product'
#      
#     @api.one
#     def _get_binary1_binary_filesystem(self):
#         attachment_obj = self.env['ir.attachment']
#         attachment_rs = attachment_obj.search([('res_model','=',self._name),('res_id','=',self.id),('binary_field','=','binary1')])
#         if attachment_rs:
#             self['binary1'] = attachment_rs[0].datas
#      
#     @api.one
#     def _set_binary1_binary_filesystem(self):
#         attachment_obj = self.env['ir.attachment']
#         attachment_rs = attachment_obj.search([('res_model','=',self._name),('res_id','=',self.id),('binary_field','=','binary1'),('is_binary_field','=',True)])
#         if self.binary1:
#             if attachment_rs:
#                 attachment_rs.datas = self.binary1
#             else:
#                 attachment_obj.create({'res_model': self._name, 'res_id': self.id, 'name': 'binary1 datas' , 'is_binary_field': True, 'binary_field': 'binary1', 'datas': self.binary1, 'datas_fname':'binary1 datas'})
#         else:
#             attachment_rs.unlink()
#          
#     binary1  = fields.Binary(string='BinArY 1', compute='_get_binary1_binary_filesystem', inverse='_set_binary1_binary_filesystem', help='binary11111')