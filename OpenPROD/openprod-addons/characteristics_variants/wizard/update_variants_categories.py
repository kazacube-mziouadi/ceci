# -*- coding: utf-8 -*-

from openerp import models, api, fields

class update_variants_categories(models.TransientModel):
    _inherit = 'update.variants.categories'
    @api.multi
    def update_products(self):
        res = super(update_variants_categories, self).update_products()
        
        for variant in self.variant_to_modify_ids:
            variant_value = variant.value_id
            charac_value_id = self.env['characteristic.value'].search([('comes_from', '=', variant_value.id)])
            if charac_value_id:
                self.env['characteristic'].create({
                    'characteristic_type_id': charac_value_id.type_id.id,
                    'value': charac_value_id.id,
                    'product_id': variant.product_id.id,
                    'variant_value_id': variant.value_id.id,
                })
        return res
