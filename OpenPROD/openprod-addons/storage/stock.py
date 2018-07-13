# coding: utf-8

from openerp import fields, models, api, _
from openerp.addons.base_openprod.common import get_form_view


class stock_move(models.Model):
    _inherit = 'stock.move'
    
    #===========================================================================
    # COLUMNS
    #=========================================================================== 
    is_stored = fields.Boolean(string='Is stored', default=False, help="Checked if the product has been stored from the storage wizard")
    
