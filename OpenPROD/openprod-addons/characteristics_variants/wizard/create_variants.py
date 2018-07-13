# -*- coding: utf-8 -*-
from openerp import models, api, fields


class create_variants(models.TransientModel):
    _inherit = 'create.variants'
    
    @api.multi
    def generate_products(self):
        res = super(create_variants, self).generate_products(ret=True)
        # on créé des characteristic pour chaque critère associé au produit
        for product in res:
            for variant_value in product.variant_values_ids:
                charac_value_id = self.env['characteristic.value'].search([('comes_from', '=', variant_value.id)])
                self.env['characteristic'].create({
                    'characteristic_type_id': charac_value_id.type_id.id,
                    'value': charac_value_id.id,
                    'product_id': product.id,
                    'variant_value_id': variant_value.id,
                })
        
        return res