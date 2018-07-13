# -*- encoding: utf-8 -*-

from openerp import models, fields, api,exceptions, _
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from dateutil import parser
import time
from openerp import workflow
from openerp.exceptions import except_orm, Warning, RedirectWarning

class account_bank_statement(models.Model):
    _inherit = 'account.bank.statement'

    
    journal_id= fields.Many2one(comodel_name='account.journal',string= 'Journal', required=False,readonly=True, states={'draft':[('readonly',False)]})
    account_id=  fields.Many2one(comodel_name='account.account',related='journal_id.default_debit_account_id',
                            string='Account used in this journal', required=False,readonly=True, help='used in statement reconciliation domain, but shouldn\'t be used elswhere.')
    bank_id= fields.Many2one('res.bank', 'Banque', required=False,readonly=False)
    last_balance_date=fields.Date("Date Dérnier Solde")
    state= fields.Selection([('draft', 'New'),
                   ('open','Open'), # used by cash statements
                   ('confirm', 'Confirmé'),
                   ('nnrapproche','En cours rapprochement'),
                   ('rapproche','Rapproché'),],
                   string='Status', required=True, readonly="1",
                   help='When new statement is created the status will be \'Draft\'.\n'
                        'And after getting confirmation from the bank it will be in \'Confirmed\' status.')
      

    _sql_constraints = [('name_uniq', 'unique(name)', 'Le Nom de Relevé doit etre unique !'),]

    @api.one
    def _set_to_unreconciled(self):
       if self.state=='rapproche':
           unreconciled_lines=self.line_ids.search([('rapprocher','=',False),('statement_id','in',self._ids)])
           if unreconciled_lines :
               self.state='nnrapproche'
       #raise Warning ("baaaaaaaaaaaaak statment line")

    @api.multi
    def _all_lines_reconciled(self):
        statment_line_pool=self.env['account.bank.statement.line']
        unreconciled_lines=statment_line_pool.search([('rapprocher','=',False),('statement_id','=',self.id)])
        if unreconciled_lines :
            return False
        else:
            return True
    @api.one
    def action_reconcile(self,cron=False,bank_reconcile_src=False):
        a=self._all_lines_reconciled()
        if a :
            self.write({'state': 'rapproche'})
        else :
            self.write({'state': 'nnrapproche'})
            if not cron and not bank_reconcile_src :
                raise except_orm(_('Error!'),_('Vérifier que toutes les lignes des relevés sont rapprochées'))



    def _auto_reconcile(self):
        statment_ids=self.search([('state','=','confirm')],limit=1)
        #order the lines by most old first
        #statment_ids.reverse()
        for statement_id in statment_ids :
              bank_reconcile_vals={
                    'fiscalyear_id':statement_id.period_id.fiscalyear_id.id,
                    'periode_id': statement_id.period_id.id,
                    'account_bank_statement_id':statement_id.id,
                    'account_id': statement_id.account_id.id
                                        }
        reconcile_bank_id=self.env['reconcile.bank'].create(bank_reconcile_vals)
        reconcile_bank_id.onchange_bank_statement_id()
        reconcile_bank_id.onchange_account_id()
        reconcile_bank_id.auto_reconcile_action()




    def bank_balance_check(self,context=None,cron=False):
        exception_obj=self.env['report.exception']
        exception_type='etebac'
        if (not self.journal_id.default_credit_account_id) \
                    or (not self.journal_id.default_debit_account_id):
                if cron:
                    code='journal_default_credit_account_id'+str(self.journal_id.name)
                    output="Merci de vérifier les comptes du journal "%(self.journal_id.name)
                    exception_obj.set_exception(code,output,exception_type)
                else :
                    raise except_orm(_('Configuration Error!'), _('Please verify that an account is defined in the journal.'))
        if not (abs((self.balance_end or 0.0) - self.balance_end_real) < 0.0001)   :
            if cron :
                 code='bank_statement_confirm_'+str(self.name)
                 output="Merci de vérifier les soldes de ce relevé %s "%(self.journal_id.name)
                 exception_obj.set_exception(code,output,exception_type)
            else :
                     raise except_orm(_('Error!'),
                    _('The statement balance is incorrect !\nThe expected balance (%.2f) is different than the computed one. (%.2f)') % (self.balance_end_real, self.balance_end))
        if self.balance_end==0 or self.balance_end_real==0 :
            if cron :
                code='bank_statement_confirm_'+str(self.name)
                output="Merci de vérifier les soldes de ce relevé %s "%(self.journal_id.name)
                exception_obj.set_exception(code,output,exception_type)
            else :
                raise except_orm(_('Error!'),
                    _('Merci de vérifier le solde final (%.2f) et le sole calculé (%.2f)') % (self.balance_end_real, self.balance_end))

        return True


    @api.multi
    def button_confirm(self,context=None,cron=False):
        self.bank_balance_check(context=context,cron=False)
        self.write({'state': 'confirm', 'closing_date': time.strftime("%Y-%m-%d %H:%M:%S")})

    @api.multi
    def button_draft(self,context=None,cron=False):
        return self.write({'state': 'draft'})

    @api.multi
    def button_dummy(self):
        return self.write({})

 
account_bank_statement()

class account_bank_statement_line(models.Model):
    
    _inherit = 'account.bank.statement.line'


    visible=fields.Boolean(string="Visible",default=True)
    journal_id= fields.Many2one(comodel_name='account.journal',related='statement_id.journal_id', string='Journal',
                               required=False, store=True, readonly=True)
    account_id= fields.Many2one(comodel_name='account.account',string='Account',required=False)
    bank_operation_id=fields.Many2one(comodel_name='bank.operation',string='Opération Bancaire')
    reconciliation_id=fields.Many2one(comodel_name='reconcile.bank', string='Rapprochement')
    rapprocher=fields.Boolean(string='Rapprocher')
    already_reconcilied=fields.Boolean(string='Rapproché')
    active=fields.Boolean(string='Active',default=True)
    move_stat_id=fields.Many2one(comodel_name='move.statement.relation',string='Relation Relevé-Ecriture',required=False)
    state= fields.Selection([('normal','Normal'), ('exception','Exception'), ('exceptioncorrigee','Correction')],
                            string= 'Status', required=False,default='normal')

    #_sql_constraints = [('name_uniq', 'unique(name,date,amount)', 'La ligne de relevé doit etre unique !'),]

    @api.v7
    def onchange_rapprocher_statement(self, cr, uid, ids, rapprocher, context=None):
        if not context:
            return False
        res = {}
        values = {}
        lines = []
        relation_obj = self.pool.get('move.statement.relation')
        move_line_obj = self.pool.get('account.move.line')
        bank_reconcil_obj = self.pool.get('reconcile.bank')
        bank_stat_line = self.browse(cr, uid, ids)
        if context.get('reconciliation_id', False):
            if rapprocher:
                relation_ids = relation_obj.search(cr, uid, [('reconciliation_id', '=', context['reconciliation_id']),
                                                             ('state', '=', 'draft')])
                if relation_ids:
                    bank_state_lines = self.search(cr, uid, [('rapprocher', '=', True), ('visible', '=', True),
                                                             ('move_stat_id', '=', False)])
                    if len(bank_state_lines) == 0:
                        values['name'] = self.pool.get('ir.sequence').next_by_code(cr, uid, 'move.statement.relation')
                        if len(ids) > 1:
                            values['bank_statement_line_ids'] = [(6, 0, ids)]
                        else:
                            values['bank_statement_line_id'] = bank_stat_line.id
                    else:
                        values['name'] = relation_obj.browse(cr, uid, relation_ids[0]).name
                        values['bank_statement_line_id'] = False
                        values['bank_statement_line_ids'] = [(6, 0, bank_state_lines + ids)]
                    relation_obj.write(cr, uid, relation_ids, values)
                    self.write(cr, uid, ids, {'rapprocher': True})

                else:
                    self.write(cr, uid, ids, {'rapprocher': False})
                    msg = "Veuiller sélectionner les écritures à rapprochées."
                    return {'value': {'rapprocher': False}, 'warning': {'message': msg}}
                    # raise Warning(msg)
            else:
                bank_state_lines = self.search(cr, uid, [('rapprocher', '=', True), ('visible', '=', True),
                                                         ('move_stat_id', '=', False)])
                self.write(cr, uid, ids, {'rapprocher': False})
                if len(bank_state_lines) == 1:
                    relation_ids = relation_obj.search(cr, uid, [('bank_statement_line_id', '=', bank_stat_line.id), (
                        'reconciliation_id', '=', bank_stat_line.reconciliation_id.id)])
                    if bank_stat_line.state == 'exception':
                        relation_obj.unlink(cr, uid, relation_ids.ids)
                        self.write(cr, uid, ids, {'state': 'normal'})
                    else:
                        for rel in relation_obj.browse(cr, uid, relation_ids):
                            rel.write({'bank_statement_line_id': False, 'name': False})
                else:
                    relation_ids = relation_obj.search(cr, uid,
                                                       [('reconciliation_id', '=', bank_stat_line.reconciliation_id.id),
                                                        ('state', '=', 'draft')])
                    vals = {}
                    if len(bank_state_lines) > 2:
                        vals['bank_statement_line_ids'] = [(3, ids[0])]
                    else:
                        vals['bank_statement_line_ids'] = [(5,)]
                        current_statement = bank_state_lines.index(ids[0])
                        del bank_state_lines[current_statement]
                        vals['bank_statement_line_id'] = bank_state_lines[0]
                    relation_obj.write(cr, uid, relation_ids, vals)
        else:
            raise except_orm(_(
                "Veuillez enregistrer l'opération avant de démarrer le traitement (Veuillez décocher la ligne déjà selectionnée)"),
                _(""))

        return res


account_bank_statement_line()

class move_statement_relation(models.Model):
    
    _name='move.statement.relation'
    

    name=fields.Char('Lettre de Raprochement')
    account_move_line_id=fields.Many2one(comodel_name='account.move.line',string='Ecrituree')
    bank_statement_line_id=fields.Many2one(comodel_name='account.bank.statement.line',string='Lignes du Relevé')
    bank_statement_line_ids=fields.Many2many('account.bank.statement.line','move_stat_rel_stat_rel','move_stat_rel_id','bank_stat_id',string='Lignes du Relevé relation')
    reconciliation_id=fields.Many2one(comodel_name='reconcile.bank', string='Rapprochement')
    state= fields.Selection([('draft','Brouillons'),('normal','Normal'), ('exception','Exception'), ('done','Rapproché')],
                            string= 'Status', required=True,default='draft')

    
move_statement_relation()

