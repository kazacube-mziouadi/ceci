# -*- encoding: utf-8 -*-

from openerp import models, fields, api,exceptions, _
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from dateutil import parser
import time
from openerp import workflow
from openerp.exceptions import except_orm, Warning, RedirectWarning

class account_move_line(models.Model):

    _inherit = 'account.move.line'


    visible=fields.Boolean(string="Visible",default=True)
    reconciliation_id = fields.Many2one(comodel_name='reconcile.bank', string='Rapprochement')
    already_reconcilied = fields.Boolean(string='Rapproché',default=False)
    reconcilied_letter = fields.Char(string='Lettre de réconciliation')
    rapprocher = fields.Boolean(string='Rapprocher')
    exception = fields.Boolean(string='Exception')
    active = fields.Boolean(string='Active',default=True)
    move_stat_id = fields.Many2one(comodel_name='move.statement.relation',string='Relation Ecriture-Relvé',required=False)
    state1 = fields.Selection( [('normal','Normal'),('exception','Exception') ],string='Status', required=False,default='normal')

    @api.v7
    def onchange_rapprocher_move(self, cr, uid, ids, rapprocher, context=None):
        """
        :param cr:
        :param uid:
        :param ids:
        :param rapprocher: boolean
        :param context:
        :return: if rapprocher is True create a new line in move_statement_relation and set rapprocher of account move line to True,
                 if False delete this line and set rapprocher of account move line to False
        """
        res = {}
        move_line = self.browse(cr, uid, ids)
        relation_obj = self.pool.get('move.statement.relation')
        if context['reconciliation_id']:
            domain = [('account_move_line_id', '=', move_line.id),
                      ('reconciliation_id', '=', context['reconciliation_id'])]
            if rapprocher:
                if not relation_obj.search(cr, uid, domain):
                    relation_ids = relation_obj.search(cr, uid,
                                                       [('reconciliation_id', '=', context['reconciliation_id']),
                                                        ('state', '=', 'draft')])
                    if not relation_ids:
                        relation_obj.create(cr, uid, {'account_move_line_id': move_line.id,
                                                      'reconciliation_id': context['reconciliation_id']})
                    else:
                        relation = relation_obj.browse(cr, uid, relation_ids[0])
                        relation_obj.create(cr, uid, {'account_move_line_id': move_line.id,
                                                      'reconciliation_id': context['reconciliation_id'],
                                                      'bank_statement_line_ids': [
                                                          (6, 0, [bsl.id for bsl in relation.bank_statement_line_ids]) if relation.bank_statement_line_ids else (5,)],
                                                      'bank_statement_line_id': relation.bank_statement_line_id.id,
                                                      'name':relation.name})
                self.write(cr, uid, ids, {'rapprocher': True})
            else:
                relation_ids = relation_obj.search(cr, uid, domain)
                if relation_ids:
                    for rel in relation_ids:
                        req = "delete from  move_statement_relation where id = %s" % rel
                        cr.execute(req)
                    self.write(cr, uid, ids, {'rapprocher': False})
        else:

            raise except_orm(_(
                "Veuillez enregistrer l'opération avant de démarrer le traitement (Veuillez décocher la ligne déjà selectionnée)"),
                             _(""))
        return res




account_move_line()