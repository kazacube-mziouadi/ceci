# -*- coding: utf-8 -*-

from openerp import models, fields, api, _


class res_partner(models.Model):
    _inherit = 'res.partner'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    rate_ids = fields.One2many(
        comodel_name='commission.rate',
        inverse_name='partner_id'
    )
    is_agent = fields.Boolean(string='Agent', default=False , help='res_partner.is_agent.help')
    
    
    
    @api.onchange('is_agent')
    def onchange_is_agent(self):
        if self.is_agent:
            self.is_supplier = True