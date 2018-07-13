# -*- coding: utf-8 -*-
from openerp import models, fields, api


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    maintenance_contract_id = fields.Many2one('maintenance.contract', string='Maintenance contract', required=False, ondelete='restrict')


class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    maintenance_contract_id = fields.Many2one('maintenance.contract', string='Maintenance contract', required=False, ondelete='restrict')