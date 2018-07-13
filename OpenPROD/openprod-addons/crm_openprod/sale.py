# coding: utf-8

from openerp import fields, models


class sale_order(models.Model):
    _inherit = 'sale.order'
    #===========================================================================
    # COLUMNS
    #===========================================================================
    crm_id = fields.Many2one('crm', string='CRM', required=False, ondelete='set null')
