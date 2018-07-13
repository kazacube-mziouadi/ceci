# coding: utf-8

from openerp import models, fields

class product_product(models.Model):
    _inherit = 'product.product'
    
    def copy_characteristics_variant(self, new_product_id):
        res = super(product_product, self).copy_characteristics_variant(new_product_id)
        for characteristic in self.characteristics_ids:
            characteristic.copy({'product_id': new_product_id, 'model_id': characteristic.id})
        
        
        return res
    
    
    def update_characteristics_variant(self, new_product_id):
        res = super(product_product, self).update_characteristics_variant(new_product_id)
        update_var_obj = self.env['update.variants']
        for characteristic in self.characteristics_ids:
            characteristic_child = self.env['characteristic'].search([('product_id', '=', new_product_id), ('model_id', '=', characteristic.id)])
            if not characteristic_child:
                characteristic_child = self.env['characteristic'].search([('product_id', '=', new_product_id), ('characteristic_type_id', '=', characteristic.characteristic_type_id.id)])
                
            if len(characteristic_child):
                vals = update_var_obj._get_update_vals(characteristic, ['product_id'])
                characteristic_child.write(vals)
            else:
                characteristic.copy({'product_id': new_product_id, 'model_id': characteristic.id})
            
        return res