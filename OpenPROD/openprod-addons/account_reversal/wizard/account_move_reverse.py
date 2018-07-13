# -*- coding: utf-8 -*-
from openerp import models, fields, api, _

class account_move_reversal(models.TransientModel):
    _name = 'account.move.reverse'
    _description = "Create reversal of account moves"
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    date = fields.Date(string='Reversal date', required=True, help='Enter the date of the reversal account entries. By default, OpenERP proposes the first day of the period following the period of the move to reverse.', default=lambda self: self._next_period_first_date())
    period_id = fields.Many2one('account.period', string='Reversal period', help='If empty, take the period of the date.', ondelete='cascade')
    journal_id = fields.Many2one('account.journal', string='Reversal journal', help='If empty, uses the journal of the journal entry to be reversed.', ondelete='cascade')
    move_prefix = fields.Char(string='Entries ref. prefix', help='Prefix that will be added to the \'Ref\' of the journal entry to be reversed to create the \'Ref\' of the reversal journal entry (no space added after the prefix).')
    move_line_prefix = fields.Char(string='Items name prefix', help='Prefix that will be added to the name of the journal item to be reversed to create the name of the reversal journal item (a space is added after the prefix).', default='REV -')
    reconcile = fields.Boolean(string='Reconcile', default=True)

    
    def _next_period_first_date(self):
        res = False
        period_ctx = self.env.context.copy()
        if period_ctx is None:
            period_ctx = {}
            
        period_obj = self.env['account.period']
        to_reverse_move = self.env['account.move'].browse(period_ctx['active_id'])
        next_period_rc = period_obj.next(to_reverse_move.period_id, 1)
        if next_period_rc:
            res = next_period_rc.date_start
            
        return res
    

    @api.multi
    def action_reverse(self):
        context = self.env.context.copy()
        if context is None:
            context = {}
            
        form = self.read()[0]
        move_obj = self.env['account.move']
        move_ids = context['active_ids']
        period_id = form.get('period_id') and form['period_id'][0] or False
        journal_id = form.get('journal_id') and form['journal_id'][0] or False
        reconcile = form.get('reconcile', False)
        reversed_move_ids = move_obj.browse(move_ids).create_reversals(
            form['date'],
            reversal_period_id=period_id,
            reversal_journal_id=journal_id,
            move_prefix=form['move_prefix'],
            move_line_prefix=form['move_line_prefix'],
            reconcile=reconcile
        )
        action = self.env['ir.actions.act_window'].for_xml_id('account', 'action_move_journal_line')
        action['name'] = _('Reversal Entries')
        action['context'] = unicode({'search_default_to_be_reversed': 0})
        if len(reversed_move_ids) == 1:
            action['res_id'] = reversed_move_ids[0]
            action['view_mode'] = 'form,tree'
            action['views'] = False
            action['view_id'] = False
        else:
            action['domain'] = unicode([('id', 'in', reversed_move_ids)])
            
        return action
