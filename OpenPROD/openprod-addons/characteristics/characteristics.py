# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
from openerp.exceptions import except_orm

class characteristic(models.Model):
    _name = 'characteristic'
    
    @api.one
    @api.depends('characteristic_type_id', 'value')
    def _compute_name(self):
        self.name = u'{}|||{}'.format(self.characteristic_type_id.name, self.value.name)
        
        
    @api.one
    @api.depends('value', 'uom_id')
    def _compute_uom_value(self):
        if self.parent_uom_id and self.uom_id:
            self.uom_value = self.env['product.uom']._compute_qty_obj(self.uom_id, float(self.parent_value), self.parent_uom_id)
        else:
            self.uom_value = self.parent_value
            
            
    characteristic_type_id = fields.Many2one('characteristic.type', string="Type", ondelete='cascade', required=True)
    value = fields.Many2one('characteristic.value', string="Value", ondelete="cascade", required=False)
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='cascade')
    label_id = fields.Many2one('stock.label', string='Label', required=False, ondelete='cascade', select=True)
    category_id = fields.Many2one('characteristics.categories', string='Category', required=False, ondelete='cascade')
    name = fields.Char(string='Name', compute='_compute_name', store=True)
    model_id = fields.Many2one('characteristic', string='Model', required=False, ondelete='cascade')
    uom_id = fields.Many2one('product.uom', string='UoM', required=False, ondelete='restrict')
    parent_uom_category_id = fields.Many2one(related="characteristic_type_id.uom_id.category_id")
    parent_uom_id = fields.Many2one(related="characteristic_type_id.uom_id")
    parent_value = fields.Char(related="value.name", stored=True)
    uom_value = fields.Char(string='Value', compute='_compute_uom_value')
    is_created = fields.Boolean(string='Is created', default=False)
    characteristic_format = fields.Selection(related="characteristic_type_id.format")

    
    @api.model
    def create(self, vals):
        if vals.get('product_id'):
            product_id = self.env['product.product'].browse(vals['product_id'])
            # stop la création si le produit a déjà une caractéristique avec le même type
            for charac in product_id.characteristics_ids:
                if charac.characteristic_type_id.id == vals['characteristic_type_id']:
                    raise except_orm('Error', _("You can't have the same characteristic type twice"))
            
            # lie la caractéristique à celle équivalente de la catégorie
            categ_id = self.env['characteristics.categories'].search([('type_id', '=', vals['characteristic_type_id']), ('category_id', '=', product_id.categ_id.id)])
            if categ_id and 'category_id' not in vals:
                vals['category_id'] = categ_id.id
                
            vals['is_created'] = True
            
        return super(characteristic, self).create(vals)
    
    @api.multi
    def delete(self):
        self.unlink()
        return {'type': 'ir.actions.act_window_view_reload'}
    
    
    
class characteristic_type(models.Model):
    """ 
    Type of characteristic 
    """
    _name = 'characteristic.type'
    _description = 'Type of characteristic'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
        
    @api.model
    def _format_get(self):
        return [
                ('numerical', 'Numerical'),
                ('string', 'String'),
                ('list', 'List'),
                       ]
        
    name = fields.Char(required=True)
    format = fields.Selection('_format_get', string='Characteristic format', required=True)
    uom_id = fields.Many2one('product.uom', string='UoM', required=False, ondelete='restrict')
    value_ids = fields.One2many('characteristic.value', 'type_id',  string='Values')
    active = fields.Boolean(string='Active', default=True)
    
    _sql_constraints = [
            ('name_uniq', 'unique (name)', "Type of characteristic name already exists !"),
    ]
    
    @api.multi
    def name_get(self):
        if self.env.context.get('from_product', False):
            return [(x.id, x.name) for x in self]
        return [(x.id, "%s [%s]" % (x.name, x.uom_id.name) if x.uom_id else x.name) for x in self]



class characteristics_for_category(models.Model):
    """ 
    Relation table between characteristics and category 
    """
    _name = 'characteristics.categories'
    _description = 'Relation table between characteristics and category'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    category_id = fields.Many2one('product.category', string='Category', required=True, ondelete='restrict')
    type_id = fields.Many2one('characteristic.type', string='Type', required=True, ondelete='restrict')
    default_value = fields.Many2one('characteristic.value', string="Value", ondelete="cascade", required=False)
    type_format = fields.Selection(related='type_id.format')
    
    @api.onchange('default_value')
    def _onchange_field(self):
        if self.type_id.format == "numerical" and self.default_value:
            try:
                float(self.default_value.name)
            except (ValueError, TypeError):
                self.default_value = None
                return {
                        'warning': {'title': _('Error'), 'message':_("Invalid format for numeric value")}
                        }
    
    
    @api.model
    def create(self, vals):
        # crée les lignes correspondantes de characteristic
        res = super(characteristics_for_category, self).create(vals)
        product_ids = self.env['product.product'].search([('categ_id', '=', vals['category_id'])])
        type_id = self.env['characteristic.type'].browse(vals['type_id'])
        product_ids.write({
                           'characteristics_ids': [(0, 0, {
                                                          'characteristic_type_id': vals['type_id'],
                                                          'value': vals.get('default_value'),
                                                          'category_id': res.id,
                                                          'uom_id': type_id.uom_id.id,
                                                          })]
                           })
        return res
    
    
    @api.multi
    def write(self, vals):
        if 'default_value' in vals:
            # on met à jour les valeurs par défaut
            charac_ids = self.env['characteristic'].search([('category_id', '=', self.id), ('value', '=', self.default_value.id)])
            charac_ids.write({'value': vals['default_value']})
            
        return super(characteristics_for_category, self).write(vals)
    


class characteristic_value(models.Model):
    """ 
    Characteristic value 
    """
    _name = 'characteristic.value'
    _description = 'Characteristic value'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True, string="Value")
    type_id = fields.Many2one('characteristic.type', string='Type', required=True, ondelete='cascade')
    @api.one
    @api.constrains('name')
    def _check_name(self):
        if self.type_id.format == 'numerical':
            try:
                float(self.name)
            except ValueError:
                raise except_orm('Error', _('Value is not numeric'))
    
    
    @api.model
    def default_get(self, fields_list):
        if self.env.context.get('from_product') and self.env['characteristic.type'].browse(self.env.context['default_type_id']).format == 'list':
            raise except_orm('Error', 'You can\'t add a new value to the list from a product')
        
        return super(characteristic_value, self).default_get(fields_list)
    