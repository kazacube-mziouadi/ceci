# -*- coding: utf-8 -*-
from openerp import fields, models, api, _


class res_company(models.Model):
    _inherit = 'res.company'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    country_fiscal_position = fields.Many2one('account.fiscal.position', string='Country fiscal position', ondelete='restrict')
    free_exchange_area_fiscal_position = fields.Many2one('account.fiscal.position', string='Free exchange area fiscal position (CEE)', ondelete='restrict')
    free_exchange_area_service_fiscal_position = fields.Many2one('account.fiscal.position', string='Free exchange area fiscal position (CEE) service', ondelete='restrict')
    high_export_fiscal_position = fields.Many2one('account.fiscal.position', string='High export fiscal position', ondelete='restrict')
    high_export_service_fiscal_position = fields.Many2one('account.fiscal.position', string='High export fiscal position service', ondelete='restrict')