# -*- encoding: utf-8 -*-

from openerp import models, fields, api, exceptions, _
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from dateutil import parser
import time
import itertools
from collections import defaultdict
from openerp import workflow
from openerp.osv import osv
from openerp.exceptions import except_orm, Warning, RedirectWarning

import logging

_logger = logging.getLogger(__name__)


class reconcile_bank(models.Model):
    _name = 'reconcile.bank'

    @api.model
    def create(self, vals, context=None):
        vals['name'] = self.env['ir.sequence'].next_by_code('bank.reconcile')
        if 'account_move_line_ids' in vals:
            for aml in vals['account_move_line_ids']:
                if aml[0] == 1:
                    aml[0] = 4
                    aml[2] = False
        return super(reconcile_bank, self).create(vals)

    @api.multi
    def unlink(self):
        if self.state != 'draft' and self._uid != 1:
            raise except_orm(_('Suppression non autorisée !'), _("Veuillez contacter votre administrateur"))
        return super(reconcile_bank, self).unlink()

    @api.one
    def _get_move_lines_count(self):
        lines = self.account_move_line_ids.search([('reconciliation_id', '=', self.id)])
        self.move_lines_count = lines and len(lines) or 0

    @api.one
    def _get_statment_lines_count(self):
        lines = self.bank_statement_line_ids.search([('reconciliation_id', '=', self.id)])
        self.statment_lines_count = lines and len(lines) or 0

    def _get_fiscalyear(self):
        if self._context is None:
            self._context = {}
        now = time.strftime('%Y-%m-%d')
        company_id = False
        ids = self._context.get('active_ids', [])
        if ids and self.context.get('active_model') == 'account.account':
            company_id = self.env['account.account'].browse(ids[0]).company_id.id
        else:  # use current company id
            company_id = self.env['res.users'].browse(self._uid).company_id.id
        domain = [('company_id', '=', company_id), ('date_start', '<', now), ('date_stop', '>', now)]
        fiscalyears = self.env['account.fiscalyear'].search(domain, limit=1)
        return fiscalyears and fiscalyears[0] or False

    def _get_period(self):
        if self._context is None:
            self._context = {}
        now = time.strftime('%Y-%m-%d')
        company_id = False
        ids = self._context.get('active_ids', [])
        if ids and self._context.get('active_model') == 'account.period':
            company_id = self.env['account.period'].browse(ids[0]).company_id.id
        else:  # use current company id
            company_id = self.env['res.users'].browse(self._uid).company_id.id
        domain = [('company_id', '=', company_id), ('date_start', '<=', now), ('date_stop', '>=', now)]
        periods = self.env['account.period'].search(domain, limit=1)
        return periods and periods[0] or False

    def _get_account(self):
        if self._context is None:
            self._context = {}
        now = time.strftime('%Y-%m-%d')
        company_id = False
        ids = self._context.get('active_ids', [])
        if ids and self._context.get('active_model') == 'account.account':
            company_id = self.env['account.account'].browse(ids[0]).company_id.id
        else:  # use current company id
            company_id = self.env['res.users'].browse(self._uid).company_id.id
        type_ids = self.env['account.account.type'].search([('code', '=', 'bank')])
        domain = [('company_id', '=', company_id), ('user_type', 'in', type_ids._ids)]
        accounts = self.env['account.account'].search(domain, limit=1)
        print "accounts", accounts
        return accounts and accounts[0] or False

    def _default_journal_id(self):
        journal_pool = self.env['account.journal']
        journal_type = self._context.get('journal_type', False)
        company_id = self.env['res.company']._company_default_get('reconcile.bank')
        if journal_type:
            ids = journal_pool.search([('type', '=', journal_type), ('company_id', '=', company_id.id)])
            if ids:
                return ids[0]
        return False

    name = fields.Char(string='Nom', size=256, required=False, readonly=False)
    fiscalyear_id = fields.Many2one(comodel_name='account.fiscalyear', string='Exercice comptable', required=True,
                                    default=_get_fiscalyear)
    periode_id = fields.Many2one(comodel_name='account.period', string='Periode', required=False,
                                 domain=[('special', '=', False)], default=_get_period)
    journal_id = fields.Many2one(comodel_name='account.journal', string='Journal', required=True,
                                 default=_default_journal_id)
    account_id = fields.Many2one(comodel_name='account.account', string='Compte', required=True, default=_get_account)
    account_bank_statement_id = fields.Many2one(comodel_name='account.bank.statement', string='Relevé Bancaire')
    account_move_line_ids = fields.One2many(comodel_name='account.move.line', inverse_name='reconciliation_id',
                                            string='Ecritures Comptable', domain=[('visible', '=', True)])
    bank_statement_line_ids = fields.One2many(comodel_name='account.bank.statement.line',
                                              inverse_name='reconciliation_id', string='Lignes du Relevé',
                                              domain=[('visible', '=', True)])
    state = fields.Selection([('draft', 'Brouillon'), ('confirmed', 'En cours'), ('done', 'Valide'), ], string='Status',
                             readonly=True, default='draft')
    date = fields.Date(string='Date', required=True, default=lambda *a: time.strftime('%Y-%m-%d'))
    move_lines_count = fields.Integer(string="Ecritures Comptables", required=False, compute="_get_move_lines_count")
    statment_lines_count = fields.Integer(string="Lignes de relevé", required=False,
                                          compute="_get_statment_lines_count")

    @api.onchange('periode_id')
    def onchange_period_id(self):
        if not self.fiscalyear_id:
            raise except_orm(_('Veuiller choisir un Exercice Comptable'), _(""))
        bank_statement_ids = self.env['account.bank.statement'].search(
            [('period_id', '=', self.periode_id.id), ('state', 'in', ('confirm', 'nnrapproche'))])
        bank_statement_domain = [('id', 'in', bank_statement_ids.ids)]
        return {'domain': {'account_bank_statement_id': bank_statement_domain}}

    @api.onchange('fiscalyear_id')
    def onchange_fiscalyear_id(self):
        if not self.fiscalyear_id:
            return False
        period_ids = self.env['account.period'].search(
            [('fiscalyear_id', '=', self.fiscalyear_id.id), ('special', '=', False)])
        period_domain = [('id', 'in', period_ids.ids)]
        return {'domain': {'periode_id': period_domain}}

    @api.multi
    def action_confirm(self):
        lines = []
        value = {}
        recocnile_type = "daily"
        statement_bank_line_obj = self.env["account.bank.statement.line"]
        move_line_obj = self.env["account.move.line"]
        move_obj = self.env["account.move"]
        if not self.journal_id:
            raise except_orm(_('Attention '), _("Veuiller choisir un journal"))
        if not self.account_id:
            raise except_orm(_('Attention '), _("Veuiller choisir le compte comptable"))
        statment_lines_domain = [('reconciliation_id', '=', None), ('statement_id.date', '<=', self.date),
                                 ('statement_id.state', 'in', ('confirm', 'nnrapproche')),
                                 ('rapprocher', '=', False), ('state', '!=', 'exception'),
                                 ('statement_id.journal_id', '=', self.journal_id.id)]
        if self.account_bank_statement_id:
            statment_lines_domain += [('statement_id.id', '=', self.account_bank_statement_id.id)]
        statement_bank_line_ids = statement_bank_line_obj.search(statment_lines_domain)

        if not statement_bank_line_ids:
            raise except_orm(_('Il n\'y a aucune ligne pour ce relevé'), _(""))
        self.bank_statement_line_ids = statement_bank_line_ids
        move_lines_domain = [('journal_id', '=', self.journal_id.id), ('state', '=', 'valid'),
                             ('account_id', '=', self.account_id.id),
                             ('rapprocher', '=', False), ('date', '<=', self.date), ('state1', '=', 'normal')]

        # TODO : le type de rapprochement bancaire doit être configurable dans les paramétres comptables
        if recocnile_type == "mothly":
            if not self.periode_id:
                raise except_orm(_('Attention '), _("Veuiller choisir une Periode"))
            period_ids = self.env['account.period'].search(
                [('date_start', '<=', self.periode_id.date_start), ('special', '=', False)])
            move_lines_domain += [('period_id', 'in', period_ids.ids)]

        move_line_ids = move_line_obj.search(move_lines_domain)
        if not move_line_ids:
            raise except_orm(_('Il n\'y a aucune écritures pour les valeurs choisies'), _(""))
        self.account_move_line_ids = move_line_ids
        self.state = 'confirmed'

        return True

    # @api.onchange('account_bank_statement_id')
    # def onchange_bank_statement_id(self):
    #     lines=[]
    #     value={}
    #     if self.account_bank_statement_id :
    #         if not self.periode_id :
    #            raise except_orm(_('Veuiller choisir une Periode '),_(""))
    #         statement_bank_line_obj=self.env["account.bank.statement.line"]
    #         statement_bank_line_ids=statement_bank_line_obj.search([('statement_id.date','<=',self.date),('rapprocher','=',False),
    #                                                               ('statement_id.journal_id','=',self.journal_id.id)])
    #         #raise Warning(statement_bank_line_ids)
    #         if not statement_bank_line_ids:
    #             raise except_orm(_('Il n\'y a aucune ligne pour ce relevé' ),_(""))
    #         self.bank_statement_line_ids=statement_bank_line_ids
    #         self.account_id=self.account_bank_statement_id.account_id.id

    # @api.onchange('account_id')
    # def onchange_account_id(self):
    #     lines=[]
    #     value={}
    #     if self.account_id :
    #         if not self.periode_id :
    #            raise except_orm(_('Veuiller choisir une Periode '),_(""))
    #         move_line_obj = self.env["account.move.line"]
    #         move_obj = self.env["account.move"]
    #         period_ids = self.env['account.period'].search([('date_start','<=',self.periode_id.date_start),('special','=',False)])
    #         move_line_ids = move_line_obj.search([('journal_id','=',self.journal_id.id),('period_id','in',period_ids.ids),
    #                                               ('state','=','valid'),('account_id','=',self.account_id.id),('rapprocher','=',False),('date','<=',self.date)])
    #         if not move_line_ids:
    #             raise except_orm(_('Il n\'y a aucune écritures pour le compte et la periode choisies' ),_(""))
    #         self.account_move_line_ids=move_line_ids


    @api.multi
    def _somme_move_line(self, moves_line):
        somme_move_line = 0
        for ml in moves_line:
            if ml.rapprocher and not ml.move_stat_id:
                somme_move_line = somme_move_line + ml.credit + ml.debit
        return somme_move_line

    @api.multi
    def _somme_bank_line(self, banks_line):
        bank_line = 0
        for bl in banks_line:
            if bl.rapprocher:
                if bl.amount >= 0:
                    bank_line = bank_line + bl.amount
                else:
                    bank_line = bank_line + (-bl.amount)
        return bank_line

    def find_sum_tuple(self, numbers, s, n):
        numbers.sort(reverse=True)
        for triplet in itertools.combinations(numbers, n):
            if sum(triplet) == s:
                return list(triplet)
        return []

    @api.multi
    def auto_reconcile_action(self,cron=False):
        exception_obj = self.env['report.exception']
        context = {}
        context['reconciliation_id'] = self._ids
        statment_ids = {}
        _logger.warning("demarrage du rapprochement bancaire automatique")
        for statment_line in self.bank_statement_line_ids:
            statment_ids[statment_line.id] = statment_line.name
        if statment_ids:
            # groupement des lignes de relevé par nom
            stat_by_label = defaultdict(list)
            for key, value in sorted(statment_ids.iteritems()):
                stat_by_label[value].append(key)
            # calcul cumul d'un lot bancaire du meme remise et le comparer avec le cumul
            # des ecritures ayants le meme numéro. Si les deux cumuls sont égaux ==> rapprochement de tte les lignes
            # si non => rapprochement basé sur les monatant et  le reste sera à faire manuellement
            for line in stat_by_label:
                customer_stat_total = 0
                supplier_stat_total = 0
                customer_move_lines = []
                supplier_move_lines = []
                total_debit = 0
                total_credit = 0
                context = {}
                context['reconciliation_id'] = self._ids
                # In and out statement lines
                for statement_line in stat_by_label[line]:
                    stat_line_id = self.bank_statement_line_ids.browse(statement_line)
                    if stat_line_id.bank_operation_id.type == 'C':
                        customer_stat_total += stat_line_id.amount
                    elif stat_line_id.bank_operation_id.type == 'D':
                        supplier_stat_total += abs(stat_line_id.amount)
                    else:
                        exception_type = 'etebac'
                        output = "%s : type opération non introruit au systéme" % (stat_line_id.bank_operation_id.code)
                        code = 'bank_reconcile_create_error'
                        exception_obj.set_exception(code, output, exception_type)
                # In and out account move  lines
                for move in self.account_move_line_ids:
                    #if move.ref == line or move.reference_delivery == line:
                    if move.ref == line:
                        _logger.warning("reference trouve : " + str(line))
                        if move.debit > 0:
                            customer_move_lines.append(move.id)
                            total_debit += move.debit
                        if move.credit > 0:
                            supplier_move_lines.append(move.id)
                            total_credit += move.credit

                # In treatment
                if total_debit == customer_stat_total and total_debit != 0:
                    _logger.warning("rapprochement d'une ligne client en cours ...")
                    move_ids = customer_move_lines
                    statment_line_ids = self.env["account.bank.statement.line"].browse(stat_by_label[line])
                    debits = []
                    moves_to_reconcile = []
                    if len(statment_line_ids)>1:
                        _logger.warning("traitement pour nombre de ligne relevé remise superieur a 1 ...")
                    moves_to_reconcile = customer_move_lines
                    if moves_to_reconcile:
                        for move in moves_to_reconcile:
                            self.pool.get("account.move.line").onchange_rapprocher_move(self._cr, self._uid, move,
                                                                                        True, context)
                        self.pool.get("account.bank.statement.line").onchange_rapprocher_statement(self._cr,
                                                                                                   self._uid,
                                                                                                   [sl.id for
                                                                                                    sl in
                                                                                                    statment_line_ids],
                                                                                                   True, context)
                        moves_to_reconcile = self.env["account.move.line"].browse(moves_to_reconcile)
                        self.do_reconcile(statment_line_ids, moves_to_reconcile)
                        _logger.warning("rapprochement d'une ligne client effectue ...")
                else:
                    _logger.warning("inegalité pour la somme des lignes d'ecritures comptable correspondante...")
                    pass

                # Out treatment
                if total_credit == abs(supplier_stat_total) and total_credit != 0:
                    _logger.warning("rapprochement d'une ligne fournisseur en cours ...")
                    move_ids = supplier_move_lines
                    statment_line_ids = self.env["account.bank.statement.line"].browse(stat_by_label[line])
                    credits = []
                    moves_to_reconcile = []
                    if len(statment_line_ids) > 1:
                        _logger.warning("traitement pour nombre de ligne relevé remise superieur a 1 ...")
                    moves_to_reconcile = supplier_move_lines
                    if moves_to_reconcile:
                        for move in moves_to_reconcile:
                            self.pool.get("account.move.line").onchange_rapprocher_move(self._cr, self._uid, move,
                                                                                        True, context)
                        self.pool.get("account.bank.statement.line").onchange_rapprocher_statement(self._cr,
                                                                                                   self._uid,
                                                                                                   [sl.id for
                                                                                                    sl in
                                                                                                    statment_line_ids],
                                                                                                   True, context)
                        moves_to_reconcile = self.env["account.move.line"].browse(moves_to_reconcile)
                        self.do_reconcile(statment_line_ids, moves_to_reconcile)
                        _logger.warning("rapprochement d'une ligne fournisseur effectue ...")
                else:
                    _logger.warning("inegalité pour la somme des lignes d'ecritures comptable correspondante...")
                    pass
            _logger.warning("validation du rapprochement en cours ...")
            self.action_validate(cron)
            _logger.warning("validation du rapprochement effectue !")

    @api.multi
    def reconcile_lbl(self, move_ids, type='customer', statment_ids=[]):
        for move in move_ids:
            move_id = self.account_move_line_ids.browse(move)
            amount = move_id.debit
            if type == 'supplier':
                amount = move_id.credit * -1
            domain = [('amount', '=', amount)]
            if statment_ids:
                domain = [('amount', '=', amount), ('id', 'in', statment_ids)]
            statment_line_id = self.bank_statement_line_ids.search(domain, limit=1)
            if statment_line_id:
                # print "recocnile move_id :%s , state_id :%s", move_id.id, statment_line_id.id
                context = {}
                context['reconciliation_id'] = self._ids
                self.pool.get("account.move.line").onchange_rapprocher_move(self._cr, self._uid, move_id.id, True,
                                                                            context)
                self.pool.get("account.bank.statement.line").onchange_rapprocher_statement(self._cr, self._uid,
                                                                                           statment_line_id.id, True,
                                                                                           context)
                self.do_reconcile(statment_line_id, move_id)

    @api.multi
    def do_reconcile(self, statment_line_ids, move_ids):
        """
        reconcile a   account move line with a bank account statement line
        """
        relation_obj = self.env['move.statement.relation']
        somme_move_line = self._somme_move_line(move_ids)
        bank_stat_line = self._somme_bank_line(statment_line_ids)
        if somme_move_line != bank_stat_line:
            raise except_orm(_('Attention'),
                             _(
                                 "Vous ne pouvez pas valider le rapprochement,la somme des écritures %s est different de la somme des lignes de relevé %s (différence de %s)") % (
                             somme_move_line, bank_stat_line, somme_move_line - bank_stat_line))
        for move_line in move_ids:
            if move_line.rapprocher and not move_line.move_stat_id:
                move_line.write({'visible': False})
                relation_id = relation_obj.search([('account_move_line_id', '=', move_line.id), ('state', '=', 'draft'),
                                                   ('reconciliation_id', '=', self._ids[0])])
                relation_id.write({'state': 'normal'})
        for bank_stat_line in statment_line_ids:
            if bank_stat_line.rapprocher:
                bank_stat_line.write({'visible': False})
        # raise except_orm(_('Attention' ),_(("%s_%s")%(statment_line_ids,move_ids)))
        return True

    @api.multi
    def action_rapprocher(self):
        """
        reconcile a   account move line with a bank account statement line
        """
        relation_obj = self.env['move.statement.relation']
        somme_move_line = self._somme_move_line(self.account_move_line_ids)
        bank_stat_line = self._somme_bank_line(self.bank_statement_line_ids)
        if somme_move_line != bank_stat_line:
            raise except_orm(_('Attention'),
                             _(
                                 "Vous ne pouvez pas valider le rapprochement,la somme des écritures %s est different de la somme des lignes de relevé %s (différence de %s)") % (
                             somme_move_line, bank_stat_line, somme_move_line - bank_stat_line))
        for move_line in self.account_move_line_ids:
            if move_line.rapprocher and not move_line.move_stat_id:
                move_line.write({'visible': False})
                relation_id = relation_obj.search([('account_move_line_id', '=', move_line.id), ('state', '=', 'draft'),
                                                   ('reconciliation_id', '=', self._ids[0])])
                relation_id.write({'state': 'normal'})
        for bank_stat_line in self.bank_statement_line_ids:
            if bank_stat_line.rapprocher:
                bank_stat_line.write({'visible': False})
        # raise except_orm(_('Attention' ),_(self.bank_statement_line_ids))
        return True

    @api.multi
    def action_validate(self, cron=False, bank_reconcile_src=True):
        statement_ids = []
        relation_obj = self.env['move.statement.relation']
        journal_obj = self.env["account.journal"]
        journaux_ids = journal_obj.search([('type', '=', 'bank')])
        if self.periode_id:
            period_ids = self.env['account.period'].search(
                [('id', '<=', self.periode_id.id), ('fiscalyear_id', '=', self.fiscalyear_id.id),
                 ('special', '=', False)])
        move_line_rapp_ids = self.account_move_line_ids.search(
            [('visible', '=', False), ('rapprocher', '=', True), ('reconciliation_id', '=', self._ids[0])])
        move_line_not_rapp_ids = self.account_move_line_ids.search(
            [('reconciliation_id', '=', self._ids[0]), ('visible', '=', True), ('rapprocher', '=', False)])
        bank_stat_line_rapp_ids = self.bank_statement_line_ids.search(
            [('reconciliation_id', '=', self._ids[0]), ('visible', '=', False), ('rapprocher', '=', True)])
        bank_stat_line_not_rapp_ids = self.bank_statement_line_ids.search(
            [('visible', '=', True), ('rapprocher', '=', False), ('id', 'in', self.bank_statement_line_ids._ids)])
        if (not move_line_rapp_ids or not bank_stat_line_rapp_ids) and not (cron==True):
            raise Warning("Aucune ligne n'est rapprochée")
        if move_line_rapp_ids and bank_stat_line_rapp_ids:
            move_line_rapp_ids.write({'visible': True})
            bank_stat_line_rapp_ids.write({'visible': True})
            relation_ids = relation_obj.search([('reconciliation_id', '=', self.id), ('state', '=', 'normal')])
            if relation_ids:
                for rel in relation_ids:
                    rel.state = 'done'
                    rel.account_move_line_id.write({'move_stat_id': rel.id})
                    if rel.bank_statement_line_id:
                        rel.bank_statement_line_id.write({'move_stat_id': rel.id, 'state': 'normal', 'rapprocher': True})
                        if rel.bank_statement_line_id.statement_id.id not in statement_ids:
                            statement_ids.append(rel.bank_statement_line_id.statement_id.id)
                    elif rel.bank_statement_line_ids:
                        for bank_statement_line in rel.bank_statement_line_ids:
                            bank_statement_line.write(
                                {'move_stat_id': rel.id, 'state': 'normal', 'rapprocher': True})
                            if bank_statement_line.statement_id.id not in statement_ids:
                                statement_ids.append(bank_statement_line.statement_id.id)

        statement_ids = self.env['account.bank.statement'].search([('id', 'in', statement_ids)])
        for statement_id in statement_ids:
            statement_id.action_reconcile(bank_reconcile_src=bank_reconcile_src)
        # lignes de relevé non rapprochées
        if bank_stat_line_not_rapp_ids:
            for line in bank_stat_line_not_rapp_ids:
                line.write({'move_stat_id': None, 'rapprocher': False, 'reconciliation_id': None})
        # écriture comptables non rapprochées
        if move_line_not_rapp_ids:
            for ml_id in move_line_not_rapp_ids:
                rel_id = relation_obj.search(
                    [('reconciliation_id', '=', self.id), ('account_move_line_id', '=', ml_id.id)])
                rel_id.unlink()
                ml_id.write({'reconciliation_id': None})
        if (not move_line_rapp_ids or not bank_stat_line_rapp_ids) and (cron==True):
            self.unlink()
        else:
            self.write({'state': 'done'})
        return True

    @api.one
    def action_draft(self):
        self.state = 'draft'
        if self.state == 'done':
            req1 = "update account_move_line set rapprocher='false' ,visible='true' ,state1='normal' ,move_stat_id=null where reconciliation_id=%s" % \
                   self._ids[0]
            self._cr.execute(req1)
            req2 = "update account_bank_statement_line set rapprocher='false' ,visible='true',state='normal' ,move_stat_id=null where reconciliation_id=%s" % \
                   self._ids[0]
            self._cr.execute(req2)
            self._cr.execute("delete from move_statement_relation where reconciliation_id=%s" % self._ids[0])
            for statment_line in self.bank_statement_line_ids:
                check = self.env["account.bank.statement"].check_if_reconciled(statment_line.statement_id.id)
                if not check:
                    statment_line.statement_id.state = 'confirm'


reconcile_bank()






