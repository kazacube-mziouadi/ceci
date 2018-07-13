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


@api.one
def _compute_factor_inv(self):
    attachment_obj = self.env['ir.attachment']
    self.factor_inv = self.factor_inv_compute(self.factor)
    
@api.one
def _write_factor_inv(self):
    self.write({'factor': self.factor_inv_compute(self.factor_inv)})


@api.one
def _get_binary_filesystem(self, name, arg):
    """ Display the binary from ir.attachment, if already exist """
    res = {}
    attachment_obj = self.pool.get('ir.attachment')

    for record in self.browse(cr, uid, ids, context=context):
        res[record.id] = False
        attachment_ids = attachment_obj.search(cr, uid, [('res_model','=',self._name),('res_id','=',record.id),('binary_field','=',name)], context=context)
        import logging
        _logger = logging.getLogger(__name__)
        _logger.info('res %s', attachment_ids)
        if attachment_ids:
            img  = attachment_obj.browse(cr, uid, attachment_ids, context=context)[0].datas
            _logger.info('res %s', img)
            res[record.id] = img
    return res

@api.one
def _set_binary_filesystem(self, name, value, arg):
    """ Create or update the binary in ir.attachment when we save the record """
    attachment_obj = self.pool.get('ir.attachment')

    attachment_ids = attachment_obj.search(cr, uid, [('res_model','=',self._name),('res_id','=',id),('binary_field','=',name)], context=context)
    if value:
        if attachment_ids:
            attachment_obj.write(cr, uid, attachment_ids, {'datas': value}, context=context)
        else:
            attachment_obj.create(cr, uid, {'res_model': self._name, 'res_id': id, 'name': 'Marketplace picture', 'binary_field': name, 'datas': value, 'datas_fname':'picture.jpg'}, context=context)
    else:
        attachment_obj.unlink(cr, uid, attachment_ids, context=context)