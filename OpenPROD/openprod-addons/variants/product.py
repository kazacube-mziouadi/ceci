# coding: utf8
from openerp import models, fields, api
from openerp.exceptions import ValidationError, except_orm
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _

class product_product(models.Model):
    _inherit = 'product.product'
    
    @api.one
    @api.constrains('variant_category_ids')
    def _check_variant_category_ids(self):
        if len(self.variant_ids) > 0 and not self.env.context.get('update_variant_categories'):
            raise ValidationError(_('Can\'t change variant categories. Variants already have been generated'))
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    is_model = fields.Boolean(string='Is Model', default=False)
    model_id = fields.Many2one('product.product', string='Model', required=False)
    
    variant_category_ids = fields.Many2many('variant.category',  string='Variant Categories', copy=False)
    variant_ids = fields.One2many('product.product', 'model_id',  string='Variants')
    variant_values_ids = fields.Many2many('variant.category.value',  string='Variant values')
    bom_ids = fields.One2many('mrp.bom', 'product_id',  string='BoM')
    
    @api.onchange('variant_category_ids')
    def _onchange_variant_category_ids(self):
        """
            Les catégories de variantes sont répercutées sur les lignes de nomenclatures
        """
        if self.is_model:
            ids = [x.id for x in self.variant_category_ids]
            for bom in self.bom_ids:
                bom.write({'variant_category_ids' : [(6,0,ids)]})
    
    
    def fonction_extra_price(self, price, sale_line_rcs):
        """
            Fonction qui permet de d'ajouter au prix unitaire des prix additionnels
            :param price: prix
            :type price: flaot
            :param sale_line_rcs: recordset d'une ligne de vente
            :type sale_line_rcs: recordset
            :return le prix
            :rtype: float
        """
        price = super(product_product, self).fonction_extra_price(price, sale_line_rcs)
        if sale_line_rcs:
            for variant_category_value in sale_line_rcs.variant_category_value_ids:
                if variant_category_value.price_unit:
                    price += variant_category_value.price_unit
        
        return price
    
    def copy_characteristics_variant(self, new_product_id):
        return True
    
    def update_characteristics_variant(self, new_product_id):
        return True
               
class product_customerinfo(models.Model):
    _inherit = 'product.customerinfo'
    
    model_id = fields.Many2one('product.customerinfo', required=False, ondelete='cascade')
                
class product_supplierinfo(models.Model):
    _inherit = 'product.supplierinfo'
    
    model_id = fields.Many2one('product.supplierinfo', required=False, ondelete='cascade')
    
class pricelist_supplierinfo(models.Model):
    _inherit = 'pricelist.supplierinfo'
    
    model_id = fields.Many2one('pricelist.supplierinfo', required=False, ondelete='cascade')
    
class pricelist_customerinfo(models.Model):
    _inherit = 'pricelist.customerinfo'
    
    model_id = fields.Many2one('pricelist.customerinfo', required=False, ondelete='cascade')
    
class common_attribute_model(models.Model):
    _inherit = 'common.attribute.model'
    
    model_id = fields.Many2one('common.attribute.model', required=False, ondelete='cascade')
    
class quality_control_product(models.Model):
    _inherit = 'quality.control.product'
    
    model_id = fields.Many2one('quality.control.product', required=False, ondelete='cascade')
    
class variant_category(models.Model):
    """
        Catégorie de variantes, liée à une catégorie de produits
    """
    _name = 'variant.category'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Name', required=True)
    value_ids = fields.One2many('variant.category.value', 'variant_category_id',  string='Values')
    price_unit = fields.Float(string='Price unit', default=0.0, digits=dp.get_precision('Product price'))
    old_price_unit = fields.Float(string='Price unit', default=0.0, digits=dp.get_precision('Product price'))
    active = fields.Boolean(string='Active', default=True)
    
    
    _sql_constraints = [
            ('name_uniq', 'unique (name)', "Category of variant name already exists !"),
    ]
    
    
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """
            Permet de filtrer les résultats par rapport à une autre liste d'IDs
        """
        if args and len(args) > 0 and len(args[0]) > 1 and args[0][1] == 'in' and isinstance(args[0][2][0], list):
            domain = [('id', 'in', args[0][2][0][2])]
            if name:
                domain.append(('name', operator, name))
            return self.search(domain).name_get()
        else:
            return super(variant_category, self).name_search(name=name, args=args, operator=operator, limit=limit)
            
            
    @api.onchange('price_unit')
    def _onchange_variant_category_ids(self):
        """
            Les catégories de variantes sont répercutées sur les lignes de nomenclatures
        """
        for value in self.value_ids:
            if value.price_unit == self.old_price_unit:
                value.price_unit = self.price_unit
                
        self.old_price_unit = self.price_unit

    @api.multi
    def unlink(self):
        for cat in self:
            self.env.cr.execute("select count(*) "
                                "from product_product_variant_category_value_rel m2m "
                                "join variant_category_value cat on m2m.variant_category_value_id = cat.id "
                                "where cat.variant_category_id = %s;", (cat.id,))
            if self.env.cr.fetchone()[0] > 0:
                raise ValidationError('This category is already in use')
        return super(variant_category, self).unlink()

    
class variant_category_value(models.Model):
    """
        Paramètre de variante
    """
    _name = 'variant.category.value'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    @api.one
    @api.depends('variant_category_id', 'value')
    def _compute_name(self):
        self.name = u'{}|||{}'.format(self.variant_category_id.name, self.value)
            
    name = fields.Char(string='name', compute='_compute_name', store=True)
    variant_category_id = fields.Many2one('variant.category', string='Category', required=True, ondelete='cascade')
    value = fields.Char(string='Value', required=True)
    name_suffix = fields.Char(required=True)
    code_suffix = fields.Char(required=True)
    price_unit = fields.Float(string='Price unit', default=0.0, digits=dp.get_precision('Product price'))
    
    
    @api.model
    def search(self, args=None, offset=0, limit=None, order=None, count=None):
        """
            uniq permet de ne pas reproposer les valeurs appartenant à des catégories dont on a déjà choisit un critère
        """
        for i, arg in enumerate(args):
            if isinstance(arg, unicode) or (isinstance(arg, list) and arg[0] in ('!', '|', '&')):
                continue
            elif arg[0] == 'uniq':
                new_arg = []
                new_arg.append('variant_category_id')
                new_arg.append('not in')
                selected_values = arg[2][0][2] if len(arg[2]) else None
                category_ids = [x.variant_category_id.id for x in self.search([('id', 'in', selected_values)])] if selected_values else []
                new_arg.append(category_ids)
                args[i] = new_arg
            elif arg[1] == 'in' and isinstance(arg[2], list) and len(arg[2]) > 0 and isinstance(arg[2][0], list) and isinstance(arg[2][0][2], list):
                arg[2] = arg[2][0][2]
        return super(variant_category_value,self).search(args=args, offset=offset, limit=limit, order=order, count=count)
    
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        for i, arg in enumerate(args):
            if isinstance(arg, unicode) or (isinstance(arg, list) and arg[0] in ('!', '|', '&')):
                continue
            if arg[1] == 'in_question':
                fill_questionnaire_id, question_id = arg[2]
                new_arg = ['id', 'in']
                question_id = self.env['variants.question'].browse(question_id)
                fill_questionnaire_id = self.env['fill.questionnaire'].browse(fill_questionnaire_id)
                
                variant_value_ids = []
                for answer_id in fill_questionnaire_id.answer_ids:
                    if answer_id.value_variant:
                        variant_value_ids.append(answer_id.value_variant.id)
                incompatible_variant_ids = [x.second_value_id.id for x in question_id.variant_incompatibility_ids if x.first_value_id.id in variant_value_ids]
                
                if len(question_id.variant_category_value_ids):
                    value_ids = question_id.variant_category_value_ids
                else:
                    value_ids = self.search([('variant_category_id', '=', question_id.variant_category_id.id)])

                value_ids = list(set(value_ids.ids) - set(incompatible_variant_ids))
                
                new_arg.append(value_ids)
                args[i] = new_arg
            elif arg[1] == 'possible_answers':
                new_arg = ['id', 'in']
                question_id = arg[2]
                question_id = self.env['variants.question'].browse(question_id)
                if len(question_id.variant_category_value_ids):
                    value_ids = question_id.variant_category_value_ids
                else:
                    value_ids = self.search([('variant_category_id', '=', question_id.variant_category_id.id)])
                new_arg.append(value_ids.ids)
                args[i] = new_arg
        return super(variant_category_value, self).name_search(name, args, operator, limit)
    
    @api.multi
    def name_get(self):
        return [(x.id, x.variant_category_id.name + ' : ' + x.value) for x in self]
    
    @api.multi
    def unlink(self):
        raise except_orm(_('Error'), _('Impossible to delete a category value.'))
    

