# -*- coding: utf-8 -*-
from openerp import models, api, fields, _
from openerp.exceptions import except_orm


class show_warehouse_stock_level(models.TransientModel):
    """ 
        Show warehouse stock level 
    """
    _name = 'show.warehouse.stock.level'
    _description = 'Show warehouse stock level'

    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    line_ids = fields.One2many('show.warehouse.stock.level.line', 'wizard_id',  string='Lines')


class show_warehouse_stock_level_line(models.TransientModel):
    """ 
        Show warehouse stock level line
    """
    _name = 'show.warehouse.stock.level.line'
    _description = 'Show warehouse stock level line'

    wizard_id = fields.Many2one('show.warehouse.stock.level', string='Wizard', required=True, ondelete='cascade')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True, ondelete='cascade')
    available_stock = fields.Float(string='Stock (T0)')
    virtual_stock = fields.Float(string='Stock (T inf)')
