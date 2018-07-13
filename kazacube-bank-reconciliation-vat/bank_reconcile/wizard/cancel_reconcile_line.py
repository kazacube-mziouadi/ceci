# -*- encoding: utf-8 -*-

from openerp import netsvc ,models, fields, api, exceptions, _
from datetime import datetime
from openerp.osv import osv
import psycopg2
from openerp.exceptions import except_orm, Warning, RedirectWarning
import openerp
import base64
import re
import time

class cancel_reconcile_line(models.TransientModel):
    _name = 'cancel.reconcile.line'

    @api.multi
    def action_cancel_reconcile(self):
        active_ids = self._context.get('active_ids',False)
        statment_line_ids=self.env["account.bank.statement.line"].search([('id','in',active_ids)])
        vat_obj=self.env['account.vat.statement']
        relation_obj=self.env["move.statement.relation"]
        for line in  statment_line_ids :
            if not line.rapprocher :
                 raise except_orm(_('Attention' ),_(("La ligne %s n'est pas rapprochée ")%(line.name)))
            is_vat_posted=vat_obj._check_if_bank_statement_line_is_vat_posted(line.id)
            if is_vat_posted :
                raise except_orm(_('Attention' ),_(("La ligne %s a été Déclaré TVA ")%(line.name)))
            line.rapprocher=False
            line.visible=True
            line.state='normal'
            line.move_stat_id=None
            line.reconciliation_id=None
            rel_ids=relation_obj.search([('bank_statement_line_id','=',line.id)])
            for rel in rel_ids :
                move_id=rel.account_move_line_id
                move_id.rapprocher=False
                move_id.visible=True
                move_id.state1='normal'
                move_id.move_stat_id=None
                move_id.reconciliation_id=None
                rel.unlink()
            #Mettre à jour le status du relevé
            line.statement_id._set_to_unreconciled()
        return True


cancel_reconcile_line()

