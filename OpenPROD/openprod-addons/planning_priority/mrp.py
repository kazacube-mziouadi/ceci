# -*- coding: utf-8 -*-
from openerp import models, fields, api


class mrp_workorder(models.Model):
    """ 
        Workorder 
    """
    _inherit = 'mrp.workorder'


    planning_priority = fields.Integer(string='Planning priority', default=0, required=False)
    