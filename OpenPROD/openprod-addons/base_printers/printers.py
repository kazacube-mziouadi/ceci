# -*- coding: utf-8 -*-

from openerp import models
from openerp import fields
from openerp import api

class printers_type(models.Model):

    """
    Printer per type
    """
    _name = 'printers.type'
    _description = 'List of printers types'
    _order = 'name'

    # ===========================================================================
    # COLUMNS
    # ===========================================================================
    name = fields.Char(string='Name', size=32, required=True, translate=True, help='Name of this type')
    description = fields.Char(string='Description', size=64, help='Description of this type')