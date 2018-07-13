# -*- coding: utf-8 -*-
from openerp import models, api, fields, _
from openerp.exceptions import except_orm

class account_analytic_line(models.Model):
    _inherit = 'account.analytic.line'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    erl_id = fields.Many2one('expense.report.line', string='Expense report line', required=False, ondelete='restrict')
    
    

class account_invoice(models.Model):
    _inherit = 'account.invoice'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    expense_report_id = fields.Many2one('expense.report', string='Expense report', required=False, ondelete='restrict')
    


class account_voucher(models.Model):
    _inherit = 'account.voucher'
    
    @api.model
    def proforma_voucher(self):
        """
            Surcharge pour lier l'écriture comptable du paiement à la note de frais
        """
        expense_obj = self.env['expense.report']
        move_obj = self.env['account.move']
        res = super(account_voucher, self).proforma_voucher()
        expense_rcs = expense_obj.search([('pay_voucher_id', '=', self.id)])
        if expense_rcs:
            move_rcs = move_obj.sudo().search([('voucher_id', '=', self.id)], limit=1)
                
            if move_rcs:
                expense_rcs.write({'pay_move_id': move_rcs.id})
                expense_rcs.signal_workflow('paid')
                
        return res
    
    
    @api.multi
    def unlink(self):
        expense_obj = self.env['expense.report']
        for voucher in self:
            expense_rcs = expense_obj.search([('pay_voucher_id', '=', voucher.id)], limit=1)
            if not self._context.get('ok_delete', False) and expense_rcs:
                raise except_orm(_('Error!'), 
                                 _("You can not delete this writing because it is related to an expense report, please cancel the expense report to be able to remove (%s)!") % (expense_rcs.name))
            
        return super(account_voucher, self).unlink()



class account_move(models.Model):
    _inherit = 'account.move'    
    
    
    @api.multi
    def unlink(self):
        expense_obj = self.env['expense.report']
        for move in self:
            expense_rcs = expense_obj.search(['|', ('valid_move_id', '=', move.id), ('pay_move_id', '=', move.id)], limit=1)
            if not self._context.get('ok_delete', False) and expense_rcs:
                raise except_orm(_('Error!'),
                                 _("You can not delete this writing because it is related to an expense report, please cancel the expense report to be able to remove (%s)!") % (expense_rcs.name))
            
        return super(account_move, self).unlink()
