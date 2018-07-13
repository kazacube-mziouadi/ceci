# -*- coding: utf-8 -*-

from openerp import models, api, fields, tools, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm


class stock_synthesis_valuation_report(models.Model):
    """ 
        Synthesis valuation report
    """
    _name = 'stock.synthesis.valuation.report'
    _description = 'Synthesis valuation report'
    _auto = False
    _rec_name = 'product_id'
    
    
    @api.model
    def _month_get(self):
        return [
                    ('01', _('January')), 
                    ('02', _('February')), 
                    ('03', _('March')), 
                    ('04', _('April')), 
                    ('05', _('May')), 
                    ('06', _('June')), 
                    ('07', _('July')), 
                    ('08', _('August')), 
                    ('09', _('September')), 
                    ('10', _('October')), 
                    ('11', _('November')), 
                    ('12', _('December'))
           ]
    
    
    @api.model
    def _inventory_valuation_get(self):
        return [
                ('lot', _('Lot')),
                ('average', _('Weighted average price')),
                       ]
    
    
    @api.model
    def _type_valuation_get(self):
        return [
                ('real', _('Real')),
                ('theoretical', _('Theoretical')),
                       ]

    #===========================================================================
    # COLUMNS
    #===========================================================================
    month = fields.Selection('_month_get', string='Month', required=True, readonly=True)
    year = fields.Char(string='Year', size=4, required=True, readonly=True)
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='restrict', readonly=True)
    qty_in_stock = fields.Float(digits=dp.get_precision('Product quantity'), default=0.0, readonly=True)
    valuation = fields.Float(string='Valuation', default=0.0, digits=dp.get_precision('Valuation'), required=True, readonly=True)
    deprecated_valuation = fields.Float(string='Deprecated Valuation', default=0.0, digits=dp.get_precision('Valuation'), required=True, readonly=True)
    inventory_valuation = fields.Selection('_inventory_valuation_get', string='Inventory valuation', help="", readonly=True)
    type_valuation = fields.Selection('_type_valuation_get', string='Type valuation', help="", readonly=True)


    def init(self, cr):
        tools.drop_view_if_exists(cr, 'stock_synthesis_valuation_report')
        cr.execute("""
            create or replace view stock_synthesis_valuation_report as (
            (Select 
                ('666'::text||stock_valuation.id::text)::integer as id,
                stock_valuation.month,
                stock_valuation.year,
                stock_valuation.product_id,
                stock_valuation.qty_in_stock,
                (case 
                    when  (product_product.supply_method = 'produce' and product_product.type_valuation_production = 'real') or (product_product.supply_method = 'buy' and product_product.type_valuation_purchase = 'real')
                        then stock_valuation.valuation
                    else stock_valuation.valuation_theo
                end) valuation,
                (case 
                    when  (product_product.supply_method = 'produce' and product_product.type_valuation_production = 'real') or (product_product.supply_method = 'buy' and product_product.type_valuation_purchase = 'real')
                        then stock_valuation.deprecated_valuation
                    else stock_valuation.deprecated_valuation_theo
                end) deprecated_valuation,
                product_product.inventory_valuation,
                (case 
                    when product_product.supply_method = 'produce' then product_product.type_valuation_production
                    else product_product.type_valuation_purchase
                end) type_valuation
            From
                stock_valuation,
                product_product
            
            where
                product_product.id = stock_valuation.product_id and
                product_product.inventory_valuation = 'average'
            
            order by
                product_product.id asc, stock_valuation.year asc, stock_valuation.month asc)
            
            union all
            
            
            (Select 
                ('999'::text||max(stock_valuation_lot.id)::text)::integer as id,
                stock_valuation_lot.month,
                stock_valuation_lot.year,
                product_product.id as product_id,
                sum(stock_valuation_lot.qty_in_stock) qty_in_stock,
                sum(case 
                    when  ((select p1.supply_method from product_product p1 where p1.id = product_product.id) = 'produce' and (select p1.type_valuation_production from product_product p1 where p1.id = product_product.id) = 'real') 
                          or ((select p1.supply_method from product_product p1 where p1.id = product_product.id) = 'buy' and (select p1.type_valuation_purchase from product_product p1 where p1.id = product_product.id) = 'real')
                            then stock_valuation_lot.valuation
                    else stock_valuation_lot.valuation_theo
                end) valuation,
                sum(case 
                    when  ((select p1.supply_method from product_product p1 where p1.id = product_product.id) = 'produce' and (select p1.type_valuation_production from product_product p1 where p1.id = product_product.id) = 'real') 
                          or ((select p1.supply_method from product_product p1 where p1.id = product_product.id) = 'buy' and (select p1.type_valuation_purchase from product_product p1 where p1.id = product_product.id) = 'real')
                            then stock_valuation_lot.deprecated_valuation
                    else stock_valuation_lot.deprecated_valuation_theo
                end) deprecated_valuation,
                product_product.inventory_valuation,
                max(case 
                    when (select p1.supply_method from product_product p1 where p1.id = product_product.id) = 'produce' then product_product.type_valuation_production
                    else product_product.type_valuation_purchase
                end) type_valuation
            From
                stock_valuation_lot,
                product_product
            
            where
                product_product.id = stock_valuation_lot.product_id and
                product_product.inventory_valuation = 'lot'
            
            group by product_product.id, stock_valuation_lot.year, stock_valuation_lot.month
            
            order by
                product_product.id asc, stock_valuation_lot.year asc, stock_valuation_lot.month asc)) """)
                
    def unlink(self, cr, uid, ids, context={}):
        raise except_orm(_('Error !'), _('You cannot delete any record!'))
    