# -*- coding: utf-8 -*-

from openerp import models, api, fields

class update_variants_categories(models.TransientModel):
    """ 
    Add a new variant category to existing variants of a product 
    """
    _name = 'update.variants.categories'
    _description = 'Add a new variant category to existing variants of a product'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    parent_id = fields.Many2one('product.product', string='Parent', required=True, ondelete='cascade')
    category_in_use_ids = fields.Many2many(related="parent_id.variant_category_ids")
    variant_category_id = fields.Many2one('variant.category', string='Category', required=True, ondelete='cascade')
    variant_to_modify_ids = fields.One2many('variants.modified', 'wizard_id', string='Variants')
    
    @api.multi
    def update_products(self):
        for variant in self.variant_to_modify_ids:
            variant.product_id.write({
                'variant_values_ids': [(4, variant.value_id.id, 0)]
            })
        self.parent_id.with_context(update_variant_categories=True).write({
                'variant_category_ids': [(4, self.variant_category_id.id, 0)]
            })
        return

    @api.model
    def default_get(self, fields_list):
        res = super(update_variants_categories, self).default_get(fields_list)
        variant_ids = self.env['product.product'].browse(self.env.context['default_parent_id']).variant_ids
        res['variant_to_modify_ids'] = [(0, 0, {'product_id':x.id}) for x in variant_ids]
        return res


class variants_modified(models.TransientModel):
    """ 
    Variant +  valeur à donner pour la nouvelle catégorie
    """
    _name = 'variants.modified'
    _description = 'Variant +  valeur à donner pour la nouvelle categorie'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wizard_id = fields.Many2one('update.variants.categories', string='Wizard', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Variant', required=True, ondelete='cascade')
    value_id = fields.Many2one(
        'variant.category.value',
        string='Value',
        required=True,
        ondelete='cascade',
        domain="[('variant_category_id', '=', parent.variant_category_id)]")
