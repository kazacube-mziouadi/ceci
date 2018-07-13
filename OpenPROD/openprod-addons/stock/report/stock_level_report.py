# -*- coding: utf-8 -*-

from openerp import models, api, fields, tools, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm

class stock_level_report(models.Model):
    _name = 'stock.level.report'
    _description = "Stock level tracability report"
    _auto = False
    _rec_name = 'product_id'
    
    @api.one
    def _compute_different(self):
        self.different = False
    
    
    def _search_different(self, operator, value):
        self.env.cr.execute('SELECT id FROM stock_level_report WHERE static_qty <> dynamic_qty OR (track_label AND label_qty <> dynamic_qty) ORDER BY id')
        res_ids = self.env.cr.fetchall()          
        return [('id', 'in', res_ids)]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    product_id = fields.Many2one('product.product', string='Product')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    static_qty = fields.Float(digits=dp.get_precision('Product UoM'), help='Quantity from stock_level table')
    dynamic_qty = fields.Float(digits=dp.get_precision('Product UoM'), help='Quantity from move dynamic compute')
    label_qty = fields.Float(digits=dp.get_precision('Product UoM'), help='Quantity from label dynamic compute')
    sl_id = fields.Many2one('stock.level', string='Stock level line', ondelete='cascade')
    different = fields.Float(compute='_compute_different', search='_search_different')
    track_label = fields.Boolean(default=False)

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'stock_level_report')
        cr.execute("""
            create or replace view stock_level_report as (
             SELECT ROW_NUMBER() OVER (ORDER BY y.p_id ASC) AS "id", y.track_label as "track_label", y.sl_id as "sl_id", y.p_id AS "product_id", y.w_id AS "warehouse_id", COALESCE(y.static_qty, 0.0) AS "static_qty", COALESCE(y.move_qty, 0.0) AS "dynamic_qty", COALESCE(y.label_qty, 0.0) AS "label_qty" FROM
                (SELECT p.id AS p_id,   w.id AS w_id, 
                 p.track_label AS track_label, 
                (SELECT sum(l.uom_qty) FROM stock_label l JOIN stock_location loc ON loc.id = l.location_id WHERE l.product_id = p.id and l.is_active = true AND loc.warehouse_id = w.id)::float AS label_qty, 
                (SELECT sum(sl.uom_qty) FROM stock_level sl WHERE sl.product_id = p.id AND sl.warehouse_id = w.id)::float AS static_qty, 
                (SELECT sl.id FROM stock_level sl WHERE sl.product_id = p.id  AND sl.warehouse_id = w.id)::float AS sl_id, 
                (SELECT sum(x.q) FROM 
                    (SELECT sm.product_id as smp_id, sm.warehouse_id as w_id, sum(sm.uom_qty * (pt_uom.factor / sm_uom.factor)) AS q
                          FROM stock_move sm, product_uom sm_uom, product_uom pt_uom, product_product pp
                        WHERE sm.state = 'done' AND
                            sm.product_id = pp.id AND
                            pt_uom.id = pp.uom_id AND
                            sm_uom.id = sm.uom_id AND
                            sm.location_id NOT IN (SELECT id FROM stock_location WHERE usage in ('internal', 'view') AND active = true) AND
                            sm.location_dest_id IN (SELECT id FROM stock_location WHERE usage in ('internal', 'view') AND active = true) AND 
                            sm.product_id = p.id AND 
                            sm.warehouse_id = w.id
                          GROUP BY sm.product_id, sm.warehouse_id
            
                        UNION ALL
            
                        SELECT sm.product_id as smp_id, sm.warehouse_id as w_id, -sum(sm.uom_qty * (pt_uom.factor / sm_uom.factor)) AS q
                          FROM stock_move sm, product_uom sm_uom, product_uom pt_uom, product_product pp
                        WHERE sm.state = 'done' AND
                            sm.product_id = pp.id AND
                            pt_uom.id = pp.uom_id AND
                            sm_uom.id = sm.uom_id AND
                            sm.location_id IN (SELECT id FROM stock_location WHERE usage in ('internal', 'view') AND active = true) AND
                            sm.location_dest_id NOT IN (SELECT id FROM stock_location WHERE usage in ('internal', 'view') AND active = true) AND
                            sm.product_id = p.id AND 
                            sm.warehouse_id = w.id
                          GROUP BY sm.product_id, sm.warehouse_id) x
                   GROUP BY x.smp_id, x.w_id)::float AS "move_qty"
                          
               FROM product_product p, stock_warehouse w) y) """)
    
    @api.multi
    def do_rectification(self):
        for report in self:
            if report.product_id:
                report.product_id.stock_level_rectification()
                
        return True
    
    
    def unlink(self, cr, uid, ids, context={}):
        raise except_orm(_('Error !'), _('You cannot delete any record!'))
    