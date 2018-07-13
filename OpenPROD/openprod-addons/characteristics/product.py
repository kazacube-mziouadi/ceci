# coding: utf-8

from openerp import models, fields, api, _

class product_product(models.Model):
    _inherit = 'product.product'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    characteristics_ids = fields.One2many('characteristic', 'product_id', string='Characteristics')
    characteristics_editable = fields.Boolean(related="categ_id.characteristics_editable")
    
    @api.multi
    def write(self, vals):
        if 'categ_id' in vals and 'characteristics_ids' not in vals and not self.env.context.get('copy_by_button'):
            for product in self:
                # on supprime les caractéristiques associées à l'ancienne
                characteristic_ids = self.env['characteristic'].search([
                                                                        ('product_id', '=', product.id),
                                                                        ('category_id', 'in', product.categ_id.characteristic_category_ids.ids),
                                                                        ])
                characteristic_ids.unlink()
            new_characteristics_vals = [(0, 0, {
                                                'characteristic_type_id': x.type_id.id,
                                                'value': x.default_value,
                                                'category_id': x.id,
                                                'uom_id': x.type_id.uom_id.id,
                                                }) for x in self.env['characteristics.categories']
                                                                .search([('category_id', '=', vals['categ_id'])])]
            self.write({
               'characteristics_ids': new_characteristics_vals
               })
        elif 'characteristics_ids' in vals:
            # s'assure que les suppression sont faites avant les ajouts
            # pour que le check des caractéristiques dupliquées ne
            # pète pas
            vals['characteristics_ids'].sort(key=lambda x: -1 if x[0] == 2 else x[0])
        return super(product_product, self).write(vals)
    
    @api.model
    def create(self, vals):
        if 'categ_id' in vals and not self.env.context.get('copy_by_button'):
            
            new_characteristics_vals = [(0, 0, {
                                                'characteristic_type_id': x.type_id.id,
                                                'value': x.default_value.id,
                                                'category_id': x.id,
                                                'uom_id': x.type_id.uom_id.id,
                                                }) 
                                            for x in self.env['characteristics.categories']
                                                         .search([('category_id', '=', vals['categ_id'])])
                                            if x
                                        ]
            vals['characteristics_ids'] = new_characteristics_vals
        return super(product_product, self).create(vals)
    
    @api.onchange('categ_id')
    def _onchange_categ_id(self):
        if not self.categ_id:
            return
        delete_cmds = [(2, x.id, 0) for x in self.characteristics_ids if x.category_id]
        add_cmds = [(0, 0, {
                            'characteristic_type_id': x.type_id.id,
                            'value': x.default_value,
                            'category_id': x.id,
                            'uom_id': x.type_id.uom_id.id,
                            }) for x in self.env['characteristics.categories']
                                            .search([('category_id', '=', self.categ_id.id)])]
        self.characteristics_ids = delete_cmds + add_cmds
        return {
                'warning': {'title':_('Warning'), 'message': _('Characteristics may have changed due to the change of category')}
                }
    
    
    
class product_category(models.Model):
    _inherit = 'product.category'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    characteristic_category_ids = fields.One2many('characteristics.categories', 'category_id')
    characteristics_editable = fields.Boolean(string='Editable', default=True)