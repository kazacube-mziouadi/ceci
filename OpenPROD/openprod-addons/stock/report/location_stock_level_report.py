# -*- coding: utf-8 -*-

from openerp import models, fields, tools, _, api
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm

class location_stock_level_report(models.Model):
    _name = 'location.stock.level.report'
    _description = "Stock level by product by location report"
    _auto = False
    _rec_name = 'product_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    uom_qty = fields.Float(digits=dp.get_precision('Product UoM'))
    product_id = fields.Many2one('product.product', string='Product')
    location_id = fields.Many2one('stock.location', string='Location')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    uom_id = fields.Many2one('product.uom', string='UoM')


    def init(self, cr):
        tools.drop_view_if_exists(cr, 'location_stock_level_report')
        cr.execute("""
            create or replace view location_stock_level_report as (
            SELECT ROW_NUMBER() OVER (ORDER BY x.l_id ASC) AS "id", sum(x.q) as "uom_qty", x.p_id as "product_id", x.l_id as "location_id", x.uom_id as "uom_id", x.w_id as "warehouse_id"
              FROM (
                SELECT pp.id as p_id, pp.uom_id as uom_id, l.id as l_id, l.warehouse_id as w_id, sum(sm.uom_qty * (pt_uom.factor / sm_uom.factor)) AS q
                      FROM stock_move sm, product_uom sm_uom, product_uom pt_uom, product_product pp, stock_location l
                        WHERE sm.state = 'done' AND
                              sm.product_id = pp.id AND
                              sm.location_dest_id = l.id AND
                              pt_uom.id = pp.uom_id AND
                              sm_uom.id = sm.uom_id AND
                              --sm.location_id NOT IN (SELECT id FROM stock_location WHERE usage = 'internal' AND active = true) AND
                              --sm.location_dest_id IN (SELECT id FROM stock_location WHERE usage = 'internal' AND active = true) AND
                              pp.track_label = false
                           GROUP BY p_id, l_id, pp.uom_id
                       
                     UNION ALL
                       
                 SELECT pp.id as p_id, pp.uom_id as uom_id, l.id as l_id, l.warehouse_id as w_id, -sum(sm.uom_qty * (pt_uom.factor / sm_uom.factor)) AS q
                   FROM stock_move sm, product_uom sm_uom, product_uom pt_uom, product_product pp, stock_location l
                     WHERE sm.state = 'done' AND
                           sm.product_id = pp.id AND
                           sm.location_id = l.id AND
                           pt_uom.id = pp.uom_id AND
                           sm_uom.id = sm.uom_id AND
                           --sm.location_id IN (SELECT id FROM stock_location WHERE usage = 'internal' AND active = true) AND
                           --sm.location_dest_id NOT IN (SELECT id FROM stock_location WHERE usage = 'internal' AND active = true) AND
                           pp.track_label = false
                       GROUP BY p_id, l_id, pp.uom_id
            
                UNION ALL
            
                 SELECT l.product_id as p_id, pp.uom_id as uom_id, sl.id as l_id, sl.warehouse_id as w_id, sum(l.uom_qty) as q
                    FROM stock_label l,
                         product_product pp,
                         stock_location sl
                      WHERE l.product_id = pp.id AND
                            l.location_id = sl.id AND
                            pp.track_label = true AND
                            l.type = 'uc' AND 
                            l.is_active = true 
                        GROUP BY l.product_id, sl.id, pp.uom_id) x
                GROUP BY p_id, l_id, uom_id, w_id) """)
                
    
    @api.multi
    def balancing(self):
        if self.uom_qty < 0:
            action = self.env.ref('stock.act_stock_product_storage_out')
            default_values = {'default_location_dest_id': self.location_id.id, 'default_uom_qty': -self.uom_qty}
        else:
            action = self.env.ref('stock.act_stock_product_storage_in')
            default_values = {'default_location_id': self.location_id.id, 'default_uom_qty': self.uom_qty}
            
        if action:
            action = action.read()[0]
            default_values['default_product_id'] = self.product_id.id
            if not action['context']:
                action['context'] = default_values
            else:
                action['context'] = eval(action['context'])
                action['context'].update(default_values)

        return action
    
                
    def unlink(self, cr, uid, ids, context={}):
        raise except_orm(_('Error !'), _('You cannot delete any record!'))
    