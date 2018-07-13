# coding: utf-8

from openerp import api, models, fields

class search_characteristics(models.TransientModel):
    _inherit = 'search.characteristics'
    
    variant_ids = fields.One2many('search.variant.line', 'wizard_id', string='Variants')
    
    def get_domain(self):
        res = super(search_characteristics, self).get_domain()
        
        for variant in self.variant_ids:
            variants_str = u'%{}%'.format(variant.value_id.name)
            res.append(('variant_values_ids.name', '=like', variants_str))
        return res
    
class search_variant_line(models.TransientModel):
    _name = "search.variant.line"
    
    wizard_id = fields.Many2one('search.characteristics', ondelete="cascade")
    value_id = fields.Many2one('variant.category.value', string="Value", ondelete="cascade", required=True)
    category_id = fields.Many2one('variant.category', string="Category", ondelete="cascade", required=True)

class characteristic_type(models.Model):
    _inherit = 'characteristic.type'
    
    comes_from = fields.Many2one('variant.category', ondelete='restrict', string='Variant categ')
    
    
    @api.multi
    def write(self, vals):
        res = super(characteristic_type, self).write(vals)
        context = self.env.context.copy()
        context['write_carat_type'] = True
        if 'active' in vals and not context.get('write_variant_categ'):
            variant_categ_rcs = self.env['variant.category'].search([('characte_type_id', 'in', self.ids)])
            if variant_categ_rcs:
                variant_categ_rcs.with_context(context).write({'active': vals['active']})
        
        return res



class characteristic_value(models.Model):
    _inherit = 'characteristic.value'
    
    comes_from = fields.Many2one('variant.category.value', ondelete='restrict')

class variant_category_value(models.Model):
    _inherit = 'variant.category.value'
    
    characte_value_id = fields.Many2one('characteristic.value', ondelete='restrict')
    
    @api.model
    def create(self, vals):
        res = super(variant_category_value, self).create(vals)
        charac_type_id = self.env['characteristic.type'].search([
            ('comes_from', '=', res.variant_category_id.id),
        ], order="id desc", limit=1)
        if charac_type_id:
            caract_value_id = self.env['characteristic.value'].create({
                'name': res.value,
                'type_id': charac_type_id.id,
                'comes_from': res.id,
            })
            res.write({'characte_value_id': caract_value_id.id})
        return res



class variant_category(models.Model):
    _inherit = 'variant.category'
    
    characte_type_id = fields.Many2one('characteristic.type', ondelete='restrict')
    
    @api.model
    def create(self, vals):
        charac = self.env['characteristic.type'].create({
            'name': vals['name'],
            'format': 'string',
            'active': vals['active'],
        })
        vals['characte_type_id'] = charac.id
        res = super(variant_category, self).create(vals)
        charac.comes_from = res.id
        return res
    
    
    @api.multi
    def write(self, vals):
        res = super(variant_category, self).write(vals)
        context = self.env.context.copy()
        context['write_variant_categ'] = True
        if 'active' in vals and not context.get('write_carat_type'):
            characte_type_rcs = self.env['characteristic.type'].search([('comes_from', 'in', self.ids), '|', ('active', '=', False), ('active', '=', True)])
            if characte_type_rcs:
                characte_type_rcs.with_context(context).write({'active': vals['active']})
        
        return res
    
    
    
    