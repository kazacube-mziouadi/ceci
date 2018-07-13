# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.translate import _


class account_move(models.Model):
    _inherit = 'account.move'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    stock_val_id = fields.Many2one('stock.valuation.account.move', string='Accounting for inventory valuation', required=False, ondelete='cascade')
    


class account_move_line(models.Model):
    _inherit = 'account.move.line'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    stock_val_id = fields.Many2one('stock.valuation.account.move', string='Accounting for inventory valuation', required=False, ondelete='cascade')
    mo_id = fields.Many2one('mrp.manufacturingorder', string='MO', required=False, ondelete='cascade')
    is_wo_rm = fields.Boolean(string='WO RM', default=False)