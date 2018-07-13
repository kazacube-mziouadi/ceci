# coding: utf-8

from openerp import models, fields, api

class edit_categories(models.TransientModel):
    """ 
    Edit variant categories 
    """
    _name = 'variants.wizard.edit.categories'
    _description = 'Edit variant categories'
    
    def compute_default_categories(self, context=None):
        variant_categories = self.env['mrp.bom'].search([('id', '=', self.env.context['active_id'])]).variant_category_ids
        return [(6,0,[x.id for x in variant_categories])]
    
    def compute_parent_categories(self, context=None):
        variant_categories = self.env['mrp.bom'].search([('id', '=', self.env.context['active_id'])]).product_id.variant_category_ids
        if not len(variant_categories):
            return []
        return [(6,0,[x.id for x in variant_categories])]
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    category_ids = fields.Many2many('variant.category', string='Categories', default=compute_default_categories)
    parent_category_ids = fields.Many2many('variant.category', default=compute_parent_categories)
    
    @api.multi
    def save(self):
        active_id = self.env.context['active_id']
        bom_id = self.env['mrp.bom'].search([('id', '=', active_id)])
        bom_id.write({'variant_category_ids':[(6,0,[x.id for x in self.category_ids])]})
        return {'type': 'ir.actions.client', 'tag': 'reload', }