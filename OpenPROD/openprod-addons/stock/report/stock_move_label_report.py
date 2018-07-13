# -*- coding: utf-8 -*-

from openerp import models, api, fields, tools, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm

class stock_move_label_report(models.Model):
    _name = 'stock.move.label.report'
    _description = "Stock level tracability report"
    _auto = False
    _rec_name = 'label_id'


    @api.model
    def _state_get(self):
        return [
                ('draft', 'Draft'),
                ('waiting', 'Waiting'),
                ('done', 'Done'),
                ('cancel', 'Cancel'),
                       ]

    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    label_id = fields.Many2one('stock.label', string='Label', readonly=True)
    move_id = fields.Many2one('stock.move', string='Move', readonly=True)
    location_id = fields.Many2one('stock.location', string='Src location', readonly=True)
    location_dest_id = fields.Many2one('stock.location', string='Dest location', readonly=True)
    state = fields.Selection('_state_get', string='State', readonly=True)
    move_qty = fields.Float(digits=dp.get_precision('Product UoM'), readonly=True, help='Stock move quantity')
    label_qty = fields.Float(digits=dp.get_precision('Product UoM'), readonly=True, help='Stock Move label line quantity')
    move_uom_id = fields.Many2one('product.uom', string='Move UoM', readonly=True)
    product_uom_id = fields.Many2one('product.uom', string='Product UoM', readonly=True)
    date = fields.Datetime(readonly=True)

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'stock_move_label_report')
        cr.execute("""
            create or replace view stock_move_label_report as (
            SELECT ml.id as "id",
                   p.id as "product_id", 
                   ml.label_id as "label_id", 
                   m.id as "move_id", 
                   m.location_id as "location_id", 
                   m.location_dest_id as "location_dest_id", 
                   m.state as "state",
                   m.uom_qty as "move_qty",
                   ml.uom_qty as "label_qty",
                   m.uom_id as "move_uom_id",
                   p.uom_id as "product_uom_id",
                   m.date as "date"
              FROM stock_move_label ml, 
                   stock_move m,
                   product_product p
                WHERE ml.move_id = m.id
                  AND m.product_id = p.id
                ORDER BY m.date ASC) """)
                
    def unlink(self, cr, uid, ids, context={}):
        raise except_orm(_('Error !'), _('You cannot delete any record!'))
    