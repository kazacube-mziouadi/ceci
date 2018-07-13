# coding: utf-8

from openerp import models, fields

class procurement_order(models.Model):
    _inherit = 'procurement.order'
    
    def _get_product(self, proc):
        """
            :param proc: Procurement d'origine
            :type recordset
            :return: variante de produit en fonction des paramètres du proc
        """
        if len(proc.origin_wo_id):
            variant_value_ids = proc.origin_wo_id.mo_id.variant_value_ids
        else:
            variant_value_ids = proc.sol_id.variant_category_value_ids
        if not variant_value_ids:
            return proc.product_id
        product_obj = self.env['product.product']
        product_ids = product_obj.search([('model_id', '=', proc.product_id.id)])
        variant_value_ids = set([x.id for x in variant_value_ids])
        for product_id in product_ids:
            value_ids = set([x.id for x in product_id.variant_values_ids])
            if value_ids.issubset(variant_value_ids):
                return product_id
        return proc.product_id
    
    def _get_variant_value_ids(self, proc):
        if len(proc.origin_wo_id):
            return proc.origin_wo_id.mo_id.variant_value_ids
        else:
            return proc.sol_id.variant_category_value_ids
    

class stock_warehouse_orderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'
    
    model_id = fields.Many2one('stock.wharehouse.orderpoint', required=False, ondelete='cascade')
    
class stock_quality_control(models.Model):
    _inherit = 'stock.quality.control'
    
    model_id = fields.Many2one('stock.quality.control', required=False, ondelete='cascade')