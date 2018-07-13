# -*- coding: utf-8 -*-
from openerp import models, fields, api
from collections import Counter
from openerp.tools.translate import _

class mrp_bom(models.Model):
    _inherit = 'mrp.bom'
    
    @api.one
    @api.depends('variant_category_ids')
    def _compute_categories_str(self):
        self.categories_str = ', '.join([x.name for x in self.variant_category_ids])
        
    @api.one
    @api.depends('product_id')
    def _compute_has_parent_variant_categories(self):
        self.has_parent_variant_categories = len(self.product_id.variant_category_ids) > 0
            
    #===========================================================================
    # COLUMNS
    #===========================================================================
    variant_category_ids = fields.Many2many('variant.category', string='Categories') # ne devrait être rempli que pour les lignes de nomenclature
            
    categories_str = fields.Char(string='Categories', size=24, compute='_compute_categories_str')
    has_parent_variant_categories = fields.Boolean(string='Has parent_categories', compute='_compute_has_parent_variant_categories')

    
    def _bom_find(self, product_id, product_uom, options=None, no_active=False, date=False):
        """
            Cherche le BoM du produit modèle
        """
        product = self.env['product.product'].browse(product_id)
        if product and product.model_id:
            product_id = product.model_id.id
        return super(mrp_bom, self)._bom_find(product_id, product_uom, options, no_active, date)

    @api.onchange('product_id', 'prod_family_id', 'type')
    def _onchange_product_id(self):
        self.variant_category_ids = [(6,0,[x.id for x in self.product_id.variant_category_ids])]
        super(mrp_bom, self)._onchange_product_id()
    
            
class mrp_manufacturingorder(models.Model):
    _inherit = 'mrp.manufacturingorder'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    variant_value_ids = fields.Many2many('variant.category.value', string='Variant values', domain="[('uniq', 'variant_value_ids', variant_value_ids)]")
    @api.one
    @api.constrains('variant_value_ids')
    def _check_variant_value_ids(self):
        dup = Counter([x.variant_category_id for x in self.variant_value_ids])
        for x in dup.values():
            if x > 1:
                raise Warning(_('Multiple values for the same category selected'))
    
    @api.onchange('variant_value_ids', 'product_id')
    def _onchange_variant_value_ids(self):
        """
            Met à jour le produit en fonction des paramètres de variante choisis
        """
        if not len(self.variant_value_ids):
            if not self.product_id.is_model and self.product_id.model_id:
                self.product_id = self.product_id.model_id
            return
        dup = Counter([x.variant_category_id for x in self.variant_value_ids])
        for x in dup.values():
            if x > 1:
                return {'warning' : {'title': _('Warning'), 'message':'Multiple values for the same category selected'}}
        product_obj = self.env['product.product']
        product_ids = product_obj.search([('model_id', '=', self.product_id.id)])
        variant_value_ids = set([x.id for x in self.variant_value_ids])
        for product_id in product_ids:
            if not len(product_id.variant_values_ids):
                continue
            value_ids = set([x.id for x in product_id.variant_values_ids])
            if value_ids.issubset(variant_value_ids):
                self.product_id = product_id
                break
            
class mrp_workorder(models.Model):
    _inherit = 'mrp.workorder'
    
    def _get_product(self, bom_id, variant_value_ids, product=None):
        """
            Sélectionne la variante en fonction des paramètres de variante et des catégories de variante de la nomenclature
        """
        product_id = product
        if bom_id:
            variant_value_ids = [x for x in variant_value_ids if x.variant_category_id in bom_id.variant_category_ids]
            if not product:
                product_id = bom_id.product_id
            
        if not variant_value_ids or (bom_id and bom_id.type == 'family'):
            return product_id
        
        product_obj = self.env['product.product']
        product_ids = product_obj.search([('model_id', '=', product_id.id)])
        variant_value_ids = set([x.id for x in variant_value_ids])
        for product in product_ids:
            if not len(product.variant_values_ids):
                continue
            
            value_ids = set([x.id for x in product.variant_values_ids])
            if value_ids.issubset(variant_value_ids):
                return product
            
        return product_id
    
    
class mrp_option(models.Model):
    _inherit = 'mrp.option'
    
    @api.model
    def search(self, args=None, offset=0, limit=None, order=None, count=None):
        
        """
            in_question permet de filtrer les résultats parmis les choix proposés par une question
        """
        for i, arg in enumerate(args):
            if isinstance(arg, unicode) or (isinstance(arg, list) and arg[0] in ('!', '|', '&')):
                continue
            elif arg[1] == 'in_question':
                fill_questionnaire_id, question_id = arg[2]
                new_arg = ['id', 'in']
                question_id = self.env['variants.question'].browse(question_id)
                fill_questionnaire_id = self.env['fill.questionnaire'].browse(fill_questionnaire_id)
                
                option_ids = []
                for answer_id in fill_questionnaire_id.answer_ids:
                    if answer_id.value_option:
                        option_ids += answer_id.value_option.ids
                incompatible_option_ids = [x.second_value_id.id for x in question_id.option_incompatibility_ids if x.first_value_id.id in option_ids]
                
                if len(question_id.option_group_value_ids):
                    mrp_option_ids = question_id.option_group_value_ids
                else:
                    mrp_option_ids = self.search([('group_id', '=', question_id.option_group_id.id)])
                    
                
                mrp_option_ids = list(set(mrp_option_ids.ids) - set(incompatible_option_ids))
                new_arg.append(mrp_option_ids)
                args[i] = new_arg
        return super(mrp_option, self).search(args=args, offset=offset, limit=limit, order=order, count=count)
    