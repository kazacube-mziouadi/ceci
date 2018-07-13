# -*- coding: utf-8 -*-
from openerp import models, api, fields, _


class account_analytic_line(models.Model):
    _inherit = 'account.analytic.line'
    
    @api.one
    @api.depends('date')
    def _compute_period_analytic(self):
        """
            Fonction permettant de calculer la période correspondant à la date de la ligne
            d'écriture analytique
        """
        period_id = False
        year = 0
        if self.date:
            year = fields.Date.from_string(self.date).year
            period = self.env['account.period'].search([('company_id', '=', self.company_id.id), 
                                                        ('date_start', '<=', self.date),
                                                        ('date_stop', '>=', self.date)], limit=1)
            if period:
                period_id = period.id
        
        self.period_id = period_id
        self.year = year

    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    period_id = fields.Many2one('account.period', string='Period', compute='_compute_period_analytic',
                                store=True)
    year = fields.Integer(string='Year', compute='_compute_period_analytic', store=True)
    
    
    
class account_analytic_account(models.Model):
    _inherit = 'account.analytic.account'
    
    @api.one
    @api.depends('analytic_line_ids.account_id', 'analytic_line_ids.amount')
    def _compute_total_analytic_amount(self):
        """
            Fonction permettant de calculer le montant total des lignes analytiques
            par compte
        """
        total = 0
        line_ids = self.env['account.analytic.line'].search([('account_id', '=', self.id)])
        for line in line_ids:
            if line.journal_id.type == 'purchase':
                total += (line.amount / -1.0)
            else:
                total += line.amount
        
        self.amount = total
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    budget = fields.Float(string='Budget', default=0.0, required=False)
    amount = fields.Float(string='Amount', default=0.0, required=False, compute='_compute_total_analytic_amount',
                                store=True)
    analytic_line_ids = fields.One2many('account.analytic.line', 'account_id',  string='Analytic lines')
    