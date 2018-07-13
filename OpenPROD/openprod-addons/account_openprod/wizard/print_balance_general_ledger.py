# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm

class print_balance_general_ledger(models.TransientModel):
    """ 
        Wizard to print trial balance and general ledger
    """
    _name = 'print.balance.general.ledger'
    _description = 'Wizard to print trial balance and general ledger'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    @api.model
    def _report_type_get(self):
        return [
                ('ledger', _('General ledger')),
                ('partner_ledger', _('Partner general ledger')),
                ('balance', _('Balance')),
                ('partner_balance', _('Partner balance')),
                       ]
        
    @api.model
    def _ledger_partner_print(self):
        return [
                ('all', _('All partners')),
                ('list', _("Partner'list")),
                       ]
    
    report_type = fields.Selection('_report_type_get', string='Report type', required=True, default='ledger')
    ledger_partner_print = fields.Selection('_ledger_partner_print', string='Report type', required=False, default='all')
    fiscal_year_id = fields.Many2one('account.fiscalyear', string='Fiscal year', required=True, ondelete='set null')
    start_date = fields.Date(string='Start date', required=True)
    end_date = fields.Date(string='End date', required=True)
    start_account_id = fields.Many2one('account.account', string='Start account', required=True, ondelete='set null')
    end_account_id = fields.Many2one('account.account', string='End account', required=True, ondelete='set null')
    include_journal_ids = fields.Many2many('account.journal', 'include_journal_rel', 'include_id', 'journal_id', string='Journals')
    ledger_partner_ids = fields.Many2many('res.partner', 'include_partner_rel', 'include_id', 'partner_id', string='Partners')
    is_customer = fields.Boolean(string='Customer', default=True)
    is_supplier = fields.Boolean(string='Supplier', default=True)
    is_letter = fields.Boolean(string='Letter', default=True)
    is_no_letter = fields.Boolean(string='No letter', default=True)
    
    
    @api.model
    def default_get(self, fields_list):
        """
            Par défaut on prend l'exercice de l'année en cours,
            la date de début et de fin de cet exercice, le premier et de dernier compte du plan comptable,
            et l'ensemble des journaux
        """
        res = super(print_balance_general_ledger, self).default_get(fields_list=fields_list)
        company_id = self.env.user.company_id and self.env.user.company_id.id or False 
        fy_obj = self.env['account.fiscalyear']
        account_obj = self.env['account.account']
        fy_id = fy_obj.find(exception=False)
        fiscal_year = fy_id and fy_obj.browse(fy_id) or False
        if fiscal_year:
            start_date = fiscal_year.date_start
            end_date = fiscal_year.date_stop
        else:
            start_date = False
            end_date = False
        
        #Recherche du premier compte du plan comptable
        first_account_id = account_obj.search([('company_id', '=', company_id), 
                                               ('code', 'not like', 'Classe')], limit=1, order='code asc').id
        #Recherche du dernier compte du plan comptable
        last_account_id = account_obj.search([('company_id', '=', company_id), 
                                              ('code', 'not like', 'Classe')], limit=1, order='code desc').id
        #Recherche de tous les journaux de la société
        journal_rs = self.env['account.journal'].search([('company_id', '=', company_id)])
        res.update({'fiscal_year_id': fy_id,
                    'start_date': start_date,
                    'end_date': end_date,
                    'include_journal_ids': journal_rs.ids,
                    'start_account_id': first_account_id,
                    'end_account_id': last_account_id})
        return res
    
    
    @api.multi
    def print_report(self):
        """
            Fonction permettant d'imprimer le grand livre ou la balance à partir
            d'une date de début, de fin, d'une liste de journaux et d'un partenaire (non obligatoire)
        """
        period_obj = self.env['account.period']
        report_type_dict = {'ledger': 'account_general_ledger',
                            'partner_ledger': 'account_partner_general_ledger',
                            'balance': 'account_trial_balance',
                            'partner_balance': 'account_trial_balance'}
        for wizard in self:
            fy_id = wizard.fiscal_year_id.id
            if fy_id and wizard.start_date and wizard.end_date and wizard.end_date > wizard.start_date:
                #Obligatoire d'avoir au moins un journal dans la liste
                if not wizard.include_journal_ids:
                    raise except_orm(_("Error"), _('You must choose at least one journal to print the report!'))
                    
                journal_ids = wizard.include_journal_ids.ids or [0]
                period_ids = period_obj.search([('date_start', '>=', wizard.start_date), 
                                                ('date_stop', '<=', wizard.end_date), 
                                                ('fiscalyear_id', '=', fy_id)]).ids
                if not period_ids:
                    raise except_orm(_("Error"), _('There is no accouting period for this dates and this fiscal year!'))
                
                data = {'jasper': {}}
                #Si on souhaite avoir le grand livre des tiers
                if wizard.report_type == 'partner_ledger':
                    #On passe une liste des ids des partenaires sélectionnés
                    if wizard.ledger_partner_print == 'list':
                        if wizard.ledger_partner_ids:
                            data['jasper']['partner_ids'] = ",".join([str(part_id) for part_id in wizard.ledger_partner_ids.ids])
                        else:
                            raise except_orm(_("Error"), _('You must choose at least one partner to print the report!'))
                    else:
                        #Ou on recherche tous les ids des partenaires qui ont des éritures comptables
                        period_ids_query = ()
                        for period_id in period_ids:
                            period_ids_query += (period_id,)
                            
                        journal_ids_query = ()
                        for journal_id in journal_ids:
                            journal_ids_query += (journal_id,)
                            
                        query = """SELECT partner.id 
                                 FROM res_partner partner
                                 WHERE (SELECT count(id) FROM account_move_line
                                    WHERE period_id in %s AND journal_id IN %s
                                    AND partner_id = partner.id
                                    AND (SELECT code FROM account_account WHERE id=account_id) >= '%s'
                                    AND (SELECT code FROM account_account WHERE id=account_id) <= '%s'
                                    LIMIT 1) > 0"""%(period_ids_query, journal_ids_query, 
                                                     wizard.start_account_id and wizard.start_account_id.code or '', 
                                                     wizard.end_account_id and wizard.end_account_id.code or '')
                        
                        if wizard.is_customer and wizard.is_supplier:
                            query = '%s AND (is_customer = true or is_supplier = true)'%(query)
                        else:
                            if wizard.is_customer:
                                query = '%s AND is_customer = true'%(query)
                            else:
                                query = '%s AND is_customer = false'%(query)
                                
                            if wizard.is_supplier:
                                query = '%s AND is_supplier = true'%(query)
                            else:
                                query = '%s AND is_supplier = false'%(query)
                            
                        self.env.cr.execute(query)
                        res_ids = self.env.cr.fetchall()
                        if res_ids:
                            data['jasper']['partner_ids'] = ",".join([str(x[0]) for x in res_ids])
                            data['jasper']['is_letter'] = wizard.is_letter
                            data['jasper']['is_no_letter'] = wizard.is_no_letter
                            data['jasper']['is_customer'] = wizard.is_customer
                            data['jasper']['is_supplier'] = wizard.is_supplier
                        else:
                            raise except_orm(_("Error"), _('There is no partner with account move line for this information!'))
                        
                #Si on souhaite avoir la balance des tiers
                elif wizard.report_type == 'partner_balance':
                    #On passe une liste des ids des partenaires sélectionnés
                    if wizard.ledger_partner_print == 'list':
                        if wizard.ledger_partner_ids:
                            data['jasper'].update({'partner_ids' : ",".join([str(part_id) for part_id in wizard.ledger_partner_ids.ids]),
                                                   'partner_balance': True})
                        else:
                            raise except_orm(_("Error"), _('You must choose at least one partner to print the report!'))
                    else:
                        #Ou on recherche tous les ids des partenaires qui ont des éritures comptables
                        period_ids_query = ()
                        for period_id in period_ids:
                            period_ids_query += (period_id,)
                            
                        journal_ids_query = ()
                        for journal_id in journal_ids:
                            journal_ids_query += (journal_id,)
                            
                        query = """SELECT partner.id 
                                 FROM res_partner partner
                                 WHERE (SELECT count(id) FROM account_move_line
                                    WHERE period_id in %s AND journal_id IN %s
                                    AND partner_id = partner.id
                                    AND (SELECT code FROM account_account WHERE id=account_id) >= '%s'
                                    AND (SELECT code FROM account_account WHERE id=account_id) <= '%s'
                                    LIMIT 1) > 0"""%(period_ids_query, journal_ids_query, 
                                                     wizard.start_account_id and wizard.start_account_id.code or '', 
                                                     wizard.end_account_id and wizard.end_account_id.code or '')
                
                        self.env.cr.execute(query)
                        res_ids = self.env.cr.fetchall()
                        if res_ids:
                            data['jasper'].update({'partner_ids' : ",".join([str(x[0]) for x in res_ids]),
                                                   'partner_balance': True})
                        else:
                            raise except_orm(_("Error"), _('There is no partner with account move line for this information!'))
                        
                elif wizard.report_type == 'balance':
                    data['jasper']['partner_balance'] = False
                            
                data['jasper'].update({
                    'journal_ids': ",".join([str(journal_id) for journal_id in journal_ids]),
                    'period_ids': ",".join([str(period_id) for period_id in period_ids]),
                    'exercice_id': fy_id,
                    'start_account': wizard.start_account_id and wizard.start_account_id.code or '',
                    'last_account': wizard.end_account_id and wizard.end_account_id.code or '',
                    'start_date': wizard.start_date,
                    'end_date': wizard.end_date,
                })
                report_rcs = self.env['jasper.document'].search([('report_unit' ,'=', report_type_dict[wizard.report_type])], limit=1)
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