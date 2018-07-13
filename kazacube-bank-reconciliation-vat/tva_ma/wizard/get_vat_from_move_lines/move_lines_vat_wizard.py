# -*- encoding: utf-8 -*-

from openerp import models, fields, api, exceptions, _
import datetime

class move_lines_vat_wizard(models.TransientModel):
    _name = 'move.lines.vat.wizard'

    vat_statement_id = fields.Many2one(comodel_name="account.vat.statement", string="Déclaration TVA", required=False, )
    line_ids1 = fields.One2many(comodel_name="move.lines.vat.line", inverse_name="wizard_id", string="Lignes lettrées sans facture", required=False, domain=[('move_type','=','isolated_reconciled')] )
    line_ids2 = fields.One2many(comodel_name="move.lines.vat.line", inverse_name="wizard_id", string="Lignes isolées", required=False, domain=[('move_type','=','isolated')])

    @api.one
    def _reconciled_move_lines_processing(self):
        for line in self.line_ids1:
            if line.state == 'to_add':
                vals = {
                    'vat_statement_id':self.vat_statement_id.id,
                    'name':line.name,
                    'ref':line.ref,
                    'date':line.date,
                    'bank_move_line_id':line.bank_move_line_id.id,
                    'payment_move_line_id':line.payment_move_line_id.id,
                    'tax_id':line.tax_id.id,
                    'vat_type':self.vat_statement_id.tva_sale and 'sale' or 'purchase',
                    'move_type':line.move_type,
                }

                if vals['vat_type'] == 'sale':
                    vals['amount'] = line.debit
                else:
                     vals['amount'] = line.credit

                vals['amount_tax'] = vals['amount']-(vals['amount']/(1+ line.tax_id.amount))
                vals['amount_untaxed'] = vals['amount'] - vals['amount_tax']

                lines_already_picked = self.env['account.vat.move.line'].search([('vat_statement_id','=',self.vat_statement_id.id),('bank_move_line_id','=',line.bank_move_line_id.id)])
                if lines_already_picked:
                    for l in lines_already_picked:
                        l.write(vals)
                else:
                    self.env['account.vat.move.line'].create(vals)

        return True

    @api.one
    def _isolated_move_lines_processing(self):
        for line in self.line_ids2:
            if line.state == 'to_add':
                vals = {
                    'vat_statement_id':self.vat_statement_id.id,
                    'name':line.name,
                    'ref':line.ref,
                    'date':line.date,
                    'bank_move_line_id':line.bank_move_line_id.id,
                    'payment_move_line_id':False,
                    'tax_id':line.tax_id.id,
                    'vat_type':self.vat_statement_id.tva_sale and 'sale' or 'purchase',
                    'move_type':line.move_type,
                }

                if vals['vat_type'] == 'sale':
                    vals['amount'] = line.debit
                else:
                     vals['amount'] = line.credit

                vals['amount_tax'] = vals['amount']-(vals['amount']/(1+ line.tax_id.amount))
                vals['amount_untaxed'] = vals['amount'] - vals['amount_tax']

                lines_already_picked = self.env['account.vat.move.line'].search([('vat_statement_id','=',self.vat_statement_id.id),('bank_move_line_id','=',line.bank_move_line_id.id)])
                if lines_already_picked:
                    for l in lines_already_picked:
                        l.write(vals)
                else:
                    self.env['account.vat.move.line'].create(vals)

        return True


    @api.one
    def action_validate(self):
        self._reconciled_move_lines_processing()
        self._isolated_move_lines_processing()
        return True

move_lines_vat_wizard()

class move_lines_vat_line(models.TransientModel):
    _name = 'move.lines.vat.line'

    wizard_id = fields.Many2one(comodel_name="move.lines.vat.wizard", string="Wizard", required=False, )
    date = fields.Date(string="Date", required=False, )
    payment_move_line_id = fields.Many2one(comodel_name="account.move.line", string="Ecriture comptable tiers associée au règlement", required=False, )
    bank_move_line_id = fields.Many2one(comodel_name="account.move.line", string="Ecriture comptable de banque associée au règlement", required=False, )
    name = fields.Char(string="Libellé", required=False, )
    ref = fields.Char(string="Référence", required=False, )
    journal_id = fields.Many2one(comodel_name="account.journal", string="Journal", required=False, )
    account_id = fields.Many2one(comodel_name="account.account", string="Compte", required=False, )
    partner_id = fields.Many2one(comodel_name="res.partner", string="Partenaire", required=False, )
    debit = fields.Float(string="Débit",  required=False, )
    credit = fields.Float(string="Crédit",  required=False, )
    tax_id = fields.Many2one(comodel_name="account.tax", string="Taxe", required=False, )
    move_type = fields.Selection(string="Type", selection=[('isolated_reconciled', 'Lettrées sans facture'), ('isolated', 'Isolées') ])
    state = fields.Selection(string="Etat", selection=[('draft', 'Brouillon'), ('to_add', 'A rajouter'), ], required=False, default='to_add' )

    @api.multi
    def to_add(self):
        self.state = 'to_add'
        return {
            'name':_("Séléction des lignes à déclarer"),
            'view_mode': 'form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'move.lines.vat.wizard',
            'res_id':self.wizard_id.id,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            }

    @api.multi
    def draft(self):
        self.state = 'draft'
        return {
            'name':_("Séléction des lignes à déclarer"),
            'view_mode': 'form',
            'view_id': False,
            'view_type': 'form',
            'res_model': 'move.lines.vat.wizard',
            'res_id':self.wizard_id.id,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            }




move_lines_vat_line()