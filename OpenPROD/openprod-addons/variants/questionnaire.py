# coding: utf-8

from openerp import models, api, fields, _

class variants_questionnaire(models.Model):
    """ 
    Questionnaire for variants configuration 
    """
    _name = 'variants.questionnaire'
    _description = 'Questionnaire for variants configuration'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    question_ids = fields.One2many('variants.question', 'questionnaire_id',  string='Questions')
    
class variants_question(models.Model):
    """ 
    Question of variant questionnaire 
    """
    _name = 'variants.question'
    _description = 'Question of variant questionnaire'
    _rec_name = 'label'
    _order = 'sequence'
    
    @api.model
    def _type_get(self):
        return [
                ('variant', _('Variant')),
                ('option', _('Option')),
                ('dimension', _('Dimension')),
                ('boolean', _('Boolean')),
                       ]
    
    @api.model
    def _dimension_limit_type_get(self):
        return [
                ('free', _('Free')),
                ('between', _('Min/max values')),
                ('selection', _('Selection')),
                       ]
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    questionnaire_id = fields.Many2one('variants.questionnaire', string='Questionnaire', ondelete='cascade')
    label = fields.Char(required=True)
    sequence = fields.Integer(string='Sequence', default=0, required=True)
    help_text = fields.Char(string="Help text")
    type = fields.Selection('_type_get', string='Question type', required=True)
    
    # condition d'application
    condition_question = fields.Many2one('variants.question', string="Applicability depends on", required=False, ondelete='restrict')
    condition_operator = fields.Char(size=6, string="Applicability operator", required=False,
                                     help="""Possible operators are '<', '>', '=' and '!=' for dimension, '=' for boolean, in and not in for variants and options
Example : 'Length' '>' '3' """)
    condition_value_bool = fields.Boolean(size=2, string="Applicability value", required=False)
    condition_value_dimension = fields.Float(string="Applicability value", required=False)
    condition_value_variant = fields.Many2one('variant.category.value', string="Applicability value", required=False)
    condition_value_option = fields.Many2one('mrp.option',string="Applicability value",  required=False)
    condition_question_type = fields.Selection('_type_get', related="condition_question.type")
    
    # sous-sélecteurs
    variant_category_id = fields.Many2one('variant.category', string='Variant category', required=False, ondelete='restrict')
    variant_category_value_ids = fields.Many2many('variant.category.value', string='Variant category values', required=False, ondelete='restrict')
    option_group_id = fields.Many2one('mrp.option.group', string='Option group')
    option_group_value_ids = fields.Many2many('mrp.option', string='Options')
    dimension_type = fields.Many2one('parameter.dimension.type', string='Parameter', required=False, ondelete='restrict')
    
    variant_incompatibility_ids = fields.One2many('variants.incompatibility', 'question_id',  string='Incompatibilities', help="When 'first value' has been selected in a previous answer, 'second value' won't be a possible answer")
    option_incompatibility_ids = fields.One2many('option.incompatibility', 'question_id',  string='Incompatibilities', help="When 'first value' has been selected in a previous answer, 'second value' won't be a possible answer")
    # limiteur dimensions
    dimension_limit_type = fields.Selection('_dimension_limit_type_get', string="Limit type", required=False)
    dimension_limit_min = fields.Float(string='Min', required=False)
    dimension_limit_max = fields.Float(string='Max', required=False)
    dimension_possible_values = fields.One2many('dimension.value', 'question_id', string="Possible values", required=False)
    
    def get_condition_value(self):
        question_type = self.condition_question.type
        if question_type == 'boolean':
            return self.condition_value_bool
        elif question_type == 'dimension':
            return self.condition_value_dimension
        elif question_type == 'variant':
            return self.condition_value_variant
        elif question_type == 'option':
            return self.condition_value_option
    
    @api.multi
    def name_get(self):
        res = []
        for question in self:
            res.append((question.id, u'[{}] {}'.format(question.sequence, question.label)))
        return res

class variants_incompatibility(models.Model):
    """ 
    Variants incompatibility
    """
    _name = 'variants.incompatibility'
    _description = 'Variants incompatibility'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    question_id = fields.Many2one('variants.question', required=True)
    first_value_id = fields.Many2one('variant.category.value', string='First value', required=True, ondelete='restrict')
    second_value_id = fields.Many2one('variant.category.value', string='Second value', required=True, ondelete='restrict')

class option_incompatibility(models.Model):
    """ 
    Option incompatibility
    """
    _name = 'option.incompatibility'
    _description = 'Option incompatibility'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    question_id = fields.Many2one('variants.question', required=True)
    first_value_id = fields.Many2one('mrp.option', string='First value', required=True, ondelete='restrict')
    second_value_id = fields.Many2one('mrp.option', string='Second value', required=True, ondelete='restrict')

class dimension_value(models.Model):
    """ 
    Dimension value 
    """
    _name = 'dimension.value'
    _description = 'Dimension value'
    _rec_name = 'value'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    value = fields.Float(required=True)
    question_id = fields.Many2one('variants.question', string='Question', required=True, ondelete='cascade')
