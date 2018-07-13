# -*- encoding: utf-8 -*-

from openerp import models, fields, api, exceptions, _
import datetime
import os

class move_lines_tax_edit_wizard(models.TransientModel):
    _name = 'move.lines.tax.edit.wizard'

    def _default_nb_lines(self):
        if 'active_ids' in self._context:
            return len(self._context.get('active_ids'))
        else:
            return 0

    tax_id = fields.Many2one(comodel_name="account.tax", string="Taxe")
    nb_lines = fields.Integer(string="Nombre de lignes à modifier", required=False, default=_default_nb_lines)

    @api.multi
    def action_edit(self):
        lines = self.env['account.vat.move.line'].search([('id','in',self._context['active_ids'])])
        for l in lines:
            l.tax_id = self.tax_id.id
            l.onchange_tax_id()

        return True

move_lines_tax_edit_wizard()