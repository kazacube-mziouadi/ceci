# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm

class print_balance_sheet(models.TransientModel):
    """ 
        Wizard to print balance sheet
    """
    _name = 'print.balance.sheet'
    _description = 'Wizard to print balance sheet'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    @api.model
    def _balance_type_get(self):
        return [
                ('asset', _('Asset')),
                ('liability', _('Liability')),
                ('profit_loss', _('Profit and loss')),
                       ]
    
    balance_type = fields.Selection('_balance_type_get', string='Balance type', required=True, default='asset')
    exclude_journal_ids = fields.Many2many('account.journal', 'exclude_journal_rel', 'exclude_id', 'journal_id', string='Excluding journals')
    fiscal_year_id = fields.Many2one('account.fiscalyear', string='Fiscal year', required=True, ondelete='set null')
    start_date = fields.Date(string='Start date', required=True)
    end_date = fields.Date(string='End date', required=True)
    
    @api.model
    def default_get(self, fields_list):
        """
            Par défaut on prend l'année en cours
        """
        res = super(print_balance_sheet, self).default_get(fields_list=fields_list)
        fy_obj = self.env['account.fiscalyear']
        fy_id = fy_obj.find(exception=False)
        fiscal_year = fy_id and fy_obj.browse(fy_id) or False
        if fiscal_year:
            start_date = fiscal_year.date_start
            end_date = fiscal_year.date_stop
        else:
            start_date = False
            end_date = False
            
        #On récupère les journaux d'ouverture/fermeture
        company_id = self.env.user.company_id and self.env.user.company_id.id or False 
        journal_rs = self.env['account.journal'].search([('type', '=', 'situation'), 
                                                          ('company_id', '=', company_id)])
        res.update({'fiscal_year_id': fy_id,
                    'start_date': start_date,
                    'end_date': end_date,
                    'exclude_journal_ids': journal_rs.ids})
        return res
    
    
    @api.multi
    def print_balance(self):
        """
            Fonction permettant d'imprimer le bilan à partir d'une date de début et de fin
        """
        period_obj = self.env['account.period']
        for wizard in self:
            if wizard.start_date and wizard.end_date and wizard.end_date > wizard.start_date:
                period_ids = period_obj.search([('date_start', '>=', wizard.start_date), ('date_stop', '<=', wizard.end_date)]).ids
                if not period_ids:
                    raise except_orm(_("Error"), _('There is no accouting period for this dates!'))
                
                #Le [0] permet d'éviter les erreurs dans le report s'il n'y a pas de journal à exclure
                journal_ids = wizard.exclude_journal_ids.ids or [0]
                data = {}
                start_date_str = '%s/%s/%s' %(wizard.start_date[8:10],wizard.start_date[5:7],wizard.start_date[0:4])
                end_date_str = '%s/%s/%s' %(wizard.end_date[8:10],wizard.end_date[5:7],wizard.end_date[0:4])
                data['jasper'] = {
                    'not_journal_ids': ",".join([str(journal_id) for journal_id in journal_ids]),
                    'period_ids': ",".join([str(period_id) for period_id in period_ids]),
                    'exercice_id': wizard.fiscal_year_id.id,
                    'start_date_str': start_date_str,
                    'end_date_str': end_date_str,
                }
                if wizard.balance_type == 'asset':
                    report_name = 'account_asset_balance_sheet'
                elif wizard.balance_type == 'liability':
                    report_name = 'account_liability_balance_sheet'
                elif wizard.balance_type == 'profit_loss':
                    report_name = 'account_profit_and_loss'
                    
                report_rcs = self.env['jasper.document'].search([('report_unit' ,'=', report_name)], limit=1)
                if report_rcs:
                    report = report_rcs[0]
                    if report and report.report_id:
                        return {
                                'type': 'ir.actions.report.xml',
                                'report_name': report.report_id and report.report_id.report_name or '',
                                'datas': data,
                        }
            
            else:
                raise except_orm(_("Error"), _('The end date must be superior to the start date!'))
                
        return {'type':'ir.actions.act_window_view_reload'}