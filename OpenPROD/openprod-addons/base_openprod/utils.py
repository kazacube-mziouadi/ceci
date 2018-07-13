# -*- coding: utf-8 -*-
##############################################################################
#
#    base_openprod module for OpenERP, Allows managing barcode readers with simple scenarios
#    Copyright (C) 2015 Objectif-PI (<http://www.objectif-pi.com>).
#       Damien CRIER <damien.crier@objectif-pi.com>
#
#    This file is a part of base_openprod
#
#    base_openprod is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    base_openprod is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields

def transform_to_ids(obj_ref, vals):
    """
    
    """
    for k,v in vals.iteritems():
        if issubclass(type(obj_ref), models.Model):
            if isinstance(obj_ref._fields[k], fields.Many2one) and not isinstance(v, int):
                vals[k] = v.id
            elif isinstance(obj_ref._fields[k], (fields.Many2many, fields.One2many)) and issubclass(type(v), models.Model):
                vals[k] = [(4, field.id) for field in v]
        
    return vals


def create_from_newid(self, newid_object):
    """
        Fonction permettant de créer un nouvel enregistrement à partir
        d'un nouvel id
    """
    new_object = False
    model = newid_object._name
    if model:
        model_obj = self.env[model]
        vals = {}
        for field in newid_object._fields.keys():
            vals[field] = newid_object[field]
        
        vals = transform_to_ids(model_obj, vals)
        vals['active'] = True
        new_object = model_obj.create(vals)
            
    return new_object

