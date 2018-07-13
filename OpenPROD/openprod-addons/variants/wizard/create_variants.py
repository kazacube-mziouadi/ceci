# -*- coding: utf-8 -*-
from openerp import models, fields, api
import itertools

class create_variants(models.TransientModel):
    """ 
    Create variants 
    """
    _name = 'create.variants'
    _description = 'Create variants'
    
    def compute_default_values(self):
        if not len(self.env.context['default_variant_category_ids']):
            return []
        ids = []
        for cat in self.env['variant.category'].browse(self.env.context['default_variant_category_ids'][0][2]):
            ids.extend([x.id for x in cat.value_ids])
        return [(6,0,ids)]
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    model_id = fields.Many2one('product.product', string='Model', required=False)
    
    variant_category_ids = fields.Many2many('variant.category',  string='Variant Categories', copy=False,)
    variant_ids = fields.One2many('variant', 'model_id',  string='Variants')
    value_ids = fields.Many2many('variant.category.value',  string='Values', default=compute_default_values)
    
    copy_customer_ref = fields.Boolean(string='Customer ref')
    copy_supplier_ref = fields.Boolean(string='Supplier ref')
    copy_stock_rule = fields.Boolean(string='Stock rule')
    copy_plan_ctrl = fields.Boolean(string='Plan and control')
    copy_internal_plans = fields.Boolean(string='Internal documents')
    copy_quality_control = fields.Boolean(string='Quality control')
    copy_attributes = fields.Boolean(string='Attributes')
    copy_parameters = fields.Boolean(string='Parameters')
    copy_characteristics = fields.Boolean(string='Characteristics')
    
    @api.multi
    def generate_variants(self):
        variant_obj = self.env['variant']
        self.variant_ids.unlink()
        values_by_categories = [[y for y in self.value_ids if y.variant_category_id == x] for x in self.variant_category_ids]
        for p in itertools.product(*values_by_categories):
            values = [x.id for x in p]
            name_add = ''.join([x.name_suffix for x in p])
            code_add = ''.join([x.code_suffix for x in p])
            vals = {'name':self.model_id.name,
                    'model_id':self.id,
                    'code':self.model_id.code,
                    'name_add':name_add,
                    'code_add':code_add,
                    'value_ids':[(6,0,values)]}
            variant_obj.create(vals)
        return {
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'create.variants', # your current model
            'res_id':self.id,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
        }
    
    @api.multi
    def generate_products(self, ret=False):
        generated_variants = []
        for v in self.variant_ids:
            if not (v.name_add and v.code_add):
                raise Exception('Name or code empty')
            vals = {
                    'name':v.name + v.name_add,
                    'is_model':False,
                    'model_id':self.model_id.id,
                    'variant_values_ids':[(6,0,[x.id for x in v.value_ids])],
                    'state':self.model_id.state,
            }
            if not self.env['ir.sequence'].search([('code', '=', 'product.product')]):
                vals['code'] = v.code + v.code_add
            vals['cinfo_ids'] = None
            
            
            context2 = {'copy_by_button': True}
            context2.update(self.env.context)          
            new_variant = self.with_context(context2).model_id.copy(vals)
            if self.copy_customer_ref:
                for cinfo in self.model_id.cinfo_ids:
                    cinfo_child = cinfo.copy({'product_id':new_variant.id, 'model_id':cinfo.id, 'pricelist_ids': None})
                    for price in cinfo.pricelist_ids:
                        price.copy({'cinfo_id':cinfo_child.id, 'model_id':price.id})
            if self.copy_supplier_ref:
                for sinfo in self.model_id.sinfo_ids:
                    sinfo_child = sinfo.copy({'product_id':new_variant.id, 'model_id':sinfo.id, 'pricelist_ids': None})
                    for price in sinfo.pricelist_ids:
                        price.copy({'sinfo_id':sinfo_child.id, 'model_id':price.id})
            if self.copy_stock_rule:
                for op in self.model_id.orderpoint_ids:
                    op.copy({'product_id':new_variant.id, 'model_id':op.id})
            if self.copy_plan_ctrl:
                for pc in self.model_id.plan_control_ids:
                    pc.copy({'product_id':new_variant.id, 'model_id':pc.id})
            if self.copy_quality_control:
                for qc in self.model_id.quality_control_ids:
                    qc.copy({'product_id':new_variant.id, 'model_id':qc.id})
            if self.copy_internal_plans:
                new_variant.write({'internal_plan_ids': [(4, plan.id) for plan in self.model_id.internal_plan_ids]})
            if self.copy_attributes:
                for attr in self.model_id.common_attribute_ids:
                    attr.copy({'product_id':new_variant.id, 'model_id':attr.id})
            if self.copy_parameters:
                for param in self.model_id.parameter_ids:
                    param.copy({'product_id':new_variant.id, 'model_id':param.id})
            if self.copy_characteristics:
                self.model_id.copy_characteristics_variant(new_variant.id)
            generated_variants.append(new_variant)
        if ret:
            return generated_variants
            
    
class variant(models.TransientModel):
    """
        Vue temporaire d'une variante servant à générer des produits
    """
    _name = 'variant'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    model_id = fields.Many2one('create.variants', required=True, ondelete='cascade')
    name = fields.Char(string='Name', size=20)
    code = fields.Char(string='Code', size=32, help='The code must be unique')
    
    name_add = fields.Char(string='Name add', size=20)
    code_add = fields.Char(string='Code add', size=32)
    
    value_ids = fields.Many2many('variant.category.value')
    