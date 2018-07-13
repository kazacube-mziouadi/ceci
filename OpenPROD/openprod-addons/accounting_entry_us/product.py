# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from operator import itemgetter
import openerp.addons.decimal_precision as dp
from openerp.addons.base_openprod.common import _get_month_start, _get_month_stop
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm
import math
import re


class product_category(models.Model):
    _inherit = "product.category"
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    #Valo
    #Matière acheté
    account_stock_out_id = fields.Many2one('account.account', string='Account stock out', required=False, ondelete='restrict')
    account_stock_in_id = fields.Many2one('account.account', string='Account stock in', required=False, ondelete='restrict')
    account_stock_value_in_id = fields.Many2one('account.account', string='Account stock in variation', required=False, ondelete='restrict')
    account_stock_value_out_id = fields.Many2one('account.account', string='Account stock out variation', required=False, ondelete='restrict')
    #Matière produite
    account_finish_good_inv_id = fields.Many2one('account.account', string='Account finished goods inventory', required=False, ondelete='restrict')
    account_work_in_progress_id = fields.Many2one('account.account', string='Account work in progress', required=False, ondelete='restrict')
    account_applied_overhead_id = fields.Many2one('account.account', string='Account applied overhead', required=False, ondelete='restrict')
    account_material_purchase_id = fields.Many2one('account.account', string='Account material purchase', required=False, ondelete='restrict')
    
    

class product_product(models.Model):
    _inherit = 'product.product'
    _description = 'Product'

    
    #===========================================================================
    # COLUMNS
    #=========================================================================== 
    #Valo
    #Matière acheté
    account_stock_out_id = fields.Many2one('account.account', string='Account stock out', required=False, ondelete='restrict')
    account_stock_in_id = fields.Many2one('account.account', string='Account stock in', required=False, ondelete='restrict')
    account_stock_value_in_id = fields.Many2one('account.account', string='Account stock in variation', required=False, ondelete='restrict')
    account_stock_value_out_id = fields.Many2one('account.account', string='Account stock out variation', required=False, ondelete='restrict')
    #Matière produite
    account_finish_good_inv_id = fields.Many2one('account.account', string='Account finished goods inventory', required=False, ondelete='restrict')
    account_work_in_progress_id = fields.Many2one('account.account', string='Account work in progress', required=False, ondelete='restrict')
    account_applied_overhead_id = fields.Many2one('account.account', string='Account applied overhead', required=False, ondelete='restrict')
    account_material_purchase_id = fields.Many2one('account.account', string='Account material purchase', required=False, ondelete='restrict')
