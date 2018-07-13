# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.addons.base_openprod import utils
from openerp.exceptions import ValidationError


class account_voucher(models.Model):
    _inherit = 'account.voucher'
    
    @api.model
    def default_get(self, fields_list):
        """
            Surcharge afin de récupérer le payeur de la facture
        """
        res = super(account_voucher, self).default_get(fields_list=fields_list)
        context = self.env.context
        if context.get('active_id') and self.env.context.get('active_model') == 'account.invoice':
            invoice_id = context['active_id']
            invoice_rs = self.env['account.invoice'].browse(invoice_id)
            res['partner_id'] = invoice_rs.paid_by_id.id
                
        return res
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    invoice_id = fields.Many2one('account.invoice', string='Invoice', required=False, ondelete='set null')
    
    @api.one
    def unreconcile_payment(self):
        """
            Fonction permettant de rechercher et de supprimer tous les lettrages liés aux paiements
        """
        reconcile_dict = {}
        partial_reconcile_dict = {}
        reconcile_list = self.env['account.move.reconcile']
        to_partial_reconcile = {}
        for account_move in self.account_move_ids:
            for line in account_move.line_id:
                if line.reconcile_id:
                    if not line.reconcile_id in reconcile_dict:
                        reconcile_dict[line.reconcile_id] = []
                    
                    reconcile_dict[line.reconcile_id].append(line)
                
                elif line.reconcile_partial_id:
                    if not line.reconcile_partial_id in partial_reconcile_dict:
                        partial_reconcile_dict[line.reconcile_partial_id] = []
                    
                    partial_reconcile_dict[line.reconcile_partial_id].append(line)
                    
        for reconcile, line_list in reconcile_dict.items():
            reconcile_list += reconcile
            to_partial_reconcile[reconcile.id] = self.env['account.move.line']
            for move_line in reconcile.line_id:
                if move_line not in line_list and move_line.reconcile_origin_id != reconcile:
                    to_partial_reconcile[reconcile.id] += move_line
                
        for reconcile, line_list in partial_reconcile_dict.items():
            reconcile_list += reconcile
            to_partial_reconcile[reconcile.id] = self.env['account.move.line']
            for move_line in reconcile.line_id:
                if move_line not in line_list and move_line.reconcile_origin_id != reconcile:
                    to_partial_reconcile[reconcile.id] += move_line
                
        reconcile_list.unlink()
        for partial_value in to_partial_reconcile.values():
            if len(partial_value) >= 2:
                partial_value.reconcile_partial('auto')
            
        return True
    
    
    @api.multi
    def create_voucher_line(self, move_line_list=False, invoice_rs=False, pay_amount_to_reconcile=False):
        """
            Fonction permettant de créer une ligne de paiement reliant une ou des facture(s)
            à un paiement en passant par les écritures comptables des factures ou par une seule facture.
            On envoie soit une liste d'écritures comptable de facture, soit une facture avec un
            montant à lettrer
            :type self: account.voucher
            :param move_line_list: Liste de recordset de account.move.line liés à des factures
            :type move_line_list: List
            :param invoice_rs: recordset de la facture
            :type invoice_rs: recordset : account.invoice
            :param pay_amount_to_reconcile: Dictionnaire contenant le montant à lettrer pour chaque paiement
            :type pay_amount_to_reconcile: dictionnaire
            :return: True
            :rtype: boolean
        """
        move_line_dict = {}
        today_date = fields.Date.today()
        voucher_line_obj = self.env['account.voucher.line']
        #On crée un dictionnaire contenant l'écriture comptable ainsi que le montant restant à lettrer de chacune
        # Wizard
        if invoice_rs and invoice_rs.move_id:
            #On recherche l'écriture comptable non lettrée de la facture
            args = [('account_id.reconcile','=',True), ('move_id', '=', invoice_rs.move_id.id)]
            move_line_list = self.env['account.move.line'].search(args)
            
        if move_line_list:
            #On récupère le montant de chaque écriture
            for move_line in move_line_list:
                #S'il existe déjà une ligne de paiement avec la même écriture comptable, on récupère le montant déjà lettré
                #que l'on soustrait au montant à lettrer de l'écriture
                amount = move_line.debit or move_line.credit
                move_line_dict[move_line] = {'amount': amount}
                if amount > 0:
                    voucher_line_rs = voucher_line_obj.search([('move_line_id', '=', move_line.id)])
                    for voucher_line in voucher_line_rs:
                        move_line_dict[move_line]['amount'] -= voucher_line.amount
                        move_line_dict[move_line]['voucher_id'] = voucher_line.voucher_id.id
                
        if move_line_dict:
            for payment in self:
                #On récupère le montant restant du paiement afin de répartir le montant à lettrer
                #en cas de lettrage avec plusieurs factures
                residual_amount = payment.writeoff_amount
                vals = {'voucher_id': payment.id}
                partner_id = payment.partner_id.id
                journal_id = payment.journal_id.id
                amount = payment.amount
                currency_id = payment.currency_id.id
                for line in move_line_dict:
                    voucher_line_write = False
                    if not move_line_dict.get('voucher_id') or move_line_dict['voucher_id'] != payment.id: 
                        #Récupération et modification du context afin de créer des lignes de paiement liées
                        #à la facture 
                        context2 = {'account_id': line.account_id.id,
                                    'move_line_ids': [line.id]}
                        context2.update(self.env.context)
                        #On récupère les principales valeurs de l'enregistrement grâce à la fonction recompute_voucher_lines 
                        result = payment.with_context(context2).recompute_voucher_lines(partner_ids=partner_id, journal_id=journal_id, 
                                                            price=amount, currency_id=currency_id,
                                                            ttype=line.account_id.type, date=today_date)
                        if result.get('value') and (result['value'].get('line_dr_ids') or result['value'].get('line_cr_ids')):
                            data = False
                            if result['value'].get('line_dr_ids', False): 
                                for result_data in result['value']['line_dr_ids']:
                                    if isinstance(result_data, dict):
                                        data = True
                                        vals.update(result_data)
                                        
                            if not data and result['value'].get('line_cr_ids', False):
                                for result_data in result['value']['line_cr_ids']:
                                    if isinstance(result_data, dict):
                                        vals.update(result_data)
                                    
                            #Si on a passé un montant à lettrer on récupère celui-ci, sinon on va ajouter le montant de
                            #l'écriture comptable en la déduisant 
                            if pay_amount_to_reconcile and payment.id in pay_amount_to_reconcile:
                                vals['amount'] = pay_amount_to_reconcile[payment.id]
                            else:
                                #Cas des lignes d'ajustement
                                if not (line.is_adjustment and line.move_id.voucher_id != payment):
                                    line_amount = move_line_dict[line]['amount']
                                    write_amount = 0
                                    if residual_amount > 0:
                                        if residual_amount - line_amount >= 0:
                                            write_amount = line_amount
                                        else:
                                            write_amount = line_amount + (residual_amount - line_amount)
                                    
                                    else:
                                        write_amount = 0
                                        
                                    vals['amount'] = write_amount
                                    residual_amount -= write_amount
                                    move_line_dict[line]['amount'] -= write_amount
                        
                        #Si la ligne est déjà présente dans le paiement, on vient seulement la modifier
                        for cr_line in payment.line_cr_ids:
                            if cr_line.move_line_id == line:
                                voucher_line_write = cr_line
                                break
                            
                        for dr_line in payment.line_dr_ids:
                            if dr_line.move_line_id == line:
                                voucher_line_write = dr_line
                                break
                            
                        #Création de la ligne de paiement
                        if vals and not voucher_line_write:
                            voucher_line_obj.create(vals)
                        else:
                            voucher_line_write.write(vals)
            
        return True
    
    
    @api.multi
    def cancel_voucher(self):
        """
            On écrase la fonction Odoo pour prendre en compte les écritures d'ajustement
        """
        vat_return_obj = self.env['account.vat.return']
        if not self.env.context.get('vat_payement_cancel') and vat_return_obj.search([('payment_id', 'in', self.ids)], limit=1):
            raise ValidationError(_('Unable to manually cancel a payment linked to a VAT return.'))
        
        for voucher in self:
            self.unreconcile_payment()
            for move in voucher.account_move_ids:
                move.button_cancel()
                move.unlink()
                
        res = {
            'state':'cancel',
            'account_move_ids':[(5, 0)],
        }
        self.write(res)
        return True
