# -*- coding: utf-8 -*-

from openerp import models, fields, tools, _, api
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm

class location_label_report(models.Model):
    _name = 'location.label.report'
    _description = "Stock level by product by location report"
    _auto = False
    _rec_name = 'label_id'
    
    
    @api.model
    def _usage_get(self):
        self.env['stock.location']._usage_get()
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    uom_qty = fields.Float(digits=dp.get_precision('Product UoM'))
    product_id = fields.Many2one('product.product', string='Product')
    location_id = fields.Many2one('stock.location', string='Location')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    label_id = fields.Many2one('stock.label', string='Label')
    uom_id = fields.Many2one('product.uom', string='UoM')
    usage = fields.Selection('_usage_get', string='Type')
    date = fields.Datetime()
    is_active = fields.Boolean()


    def init(self, cr):
        tools.drop_view_if_exists(cr, 'location_label_report')
        cr.execute("""
            create or replace view location_label_report as (
SELECT 
    sum(x.qty) as "uom_qty", 
    x.product_id as "product_id", 
    'la' || x.label_id || 'lo' || x.location_id || 'p' || x.product_id as "id", 
    x.location_id as "location_id", 
    x.warehouse_id as "warehouse_id", 
    x.uom_id as "uom_id", 
    x.label_id as "label_id",
    x.usage AS "usage",
    max(x.date) AS "date",
    bool(sum(x.qty)>0) as "is_active"

FROM 
    (
    SELECT 
        p.id as "product_id", 
        l.id as "location_id",
        l.warehouse_id as "warehouse_id",
        sum(ml.uom_qty * (p_uom.factor / sm_uom.factor)) as "qty", 
        p.uom_id as "uom_id", 
        ml.label_id as "label_id",
        l.usage as "usage",
        max(sm.date) as "date"
    FROM
        stock_move sm
        LEFT JOIN stock_move_label ml ON ml.move_id = sm.id
        LEFT JOIN stock_label label ON ml.label_id = label.id
        LEFT JOIN product_product p ON label.product_id = p.id
        LEFT JOIN product_uom p_uom ON p_uom.id = p.uom_id
        LEFT JOIN product_uom sm_uom ON sm.uom_id = sm_uom.id
        LEFT JOIN stock_location l ON l.id = sm.location_dest_id
    WHERE
        ml.label_id is not null AND
        sm.state = 'done'
    GROUP BY p.id, sm.location_id, l.id, p.uom_id, ml.label_id
       
    UNION ALL
       
    SELECT 
        p.id as "product_id", 
        l.id as "location_id",
        l.warehouse_id as "warehouse_id",
        -sum(ml.uom_qty * (p_uom.factor / sm_uom.factor)) as "qty", 
        p.uom_id as "uom_id", 
        ml.label_id as "label_id",
        l.usage as "usage",
        max(sm.date) as "date"
    FROM
        stock_move sm
        LEFT JOIN stock_move_label ml ON ml.move_id = sm.id
        LEFT JOIN stock_label label ON ml.label_id = label.id
        LEFT JOIN product_product p ON label.product_id = p.id
        LEFT JOIN product_uom p_uom ON p_uom.id = p.uom_id
        LEFT JOIN product_uom sm_uom ON sm.uom_id = sm_uom.id
        LEFT JOIN stock_location l ON l.id = sm.location_id
    WHERE
        ml.label_id is not null AND
        sm.state = 'done'
    GROUP BY p.id, l.id, sm.location_dest_id, p.uom_id, ml.label_id

    ) x
WHERE
    x.usage = 'internal'
    
GROUP BY product_id, location_id, uom_id, label_id, x.usage, warehouse_id
ORDER BY label_id) """)
                
                
    def unlink(self, cr, uid, ids, context={}):
        raise except_orm(_('Error !'), _('You cannot delete any record!'))
    