# -*- coding: utf-8 -*-

from openerp import models, fields

class lang(models.Model):
    _inherit = 'res.lang'
    
    editable_in_interface = fields.Boolean('Editable in interface', default=True)