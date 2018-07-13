# -*- coding: utf-8 -*-
from openerp import models, api, fields, _

class res_currency(models.Model):
    _inherit = 'res.currency'
    
    
    @api.one
    @api.depends('rate',)
    def _compute_help(self):
        """
            Champ fonction permettant d'afficher une aide de conversion : "1 euros = 0.8 USD"
        """
        help = ""
        company = self.env.user.company_id
        if company and self.name and self.rate:
            help = "1 %s = %s %s"%(company.currency_id.name, self.rate, self.name)
            
        self.conversion_help = help
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    conversion_help = fields.Char(string=_('Conversion help'), size=32, required=False, compute='_compute_help')
    