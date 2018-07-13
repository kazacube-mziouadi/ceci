# coding: utf-8

from openerp import models, fields, api

class fill_questionnaire(models.TransientModel):
    """ 
    Fill a  questionnaire for a sale order line
    """
    _name = 'fill.questionnaire'
    _description = 'Fill a  questionnaire for a sale order line'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    questionnaire_id = fields.Many2one('variants.questionnaire', string='Questionnaire', required=True, ondelete='cascade')
    sale_order_line_id = fields.Many2one('sale.order.line', string='Sale order line', required=False, ondelete='cascade')
    mo_id = fields.Many2one('mrp.manufacturingorder', string='Manufacturing order', required=False, ondelete='cascade')
    answer_ids = fields.One2many('fill.questionnaire.answer', 'fill_questionnaire_id',  string='Answers')
    last_replied_question_stack = fields.Char(string='Previous', default='', required=False)
    
    @api.multi
    def fill(self):
        first_question = self.questionnaire_id.question_ids.sorted(key=lambda r:r.sequence)[0]
        return {
                'type':'ir.actions.act_window',
                'res_model':'fill.questionnaire.answer',
                'target':'new',
                'views': [[False, 'form']],
                'context': {
                            'default_fill_questionnaire_id': self.id,
                            'default_question_id':first_question.id,
                            'default_question_label': first_question.label,
                            'default_help_text': first_question.help_text,
                            'default_dimension_limit_type': first_question.dimension_limit_type,
                            }
                }
        
    def save_all_answers(self):
        options, variants, dimensions = self.get_save_values()
        if self.sale_order_line_id:
            self.sale_order_line_id.parameter_ids.unlink()
            self.sale_order_line_id.option_lines_ids.unlink()
            self.sale_order_line_id.write({
                                           'option_lines_ids': [(0, 0, {'option_id':opt.id, 'price_unit':opt.price_unit}) for opt in options],
                                           'variant_category_value_ids': [(6, 0, [variant.id for variant in variants])],
                                           'parameter_ids': [(0,0,vals) for vals in dimensions],
                                           })
            #Recalcule du prix par rapport aux extra price
            self.sale_order_line_id._onchange_sec_uom_qty()
            
        else:
            self.mo_id.parameter_ids.unlink()
            self.mo_id.write({
                                           'option_ids': [(6, 0, [opt.id for opt in options])],
                                           'variant_value_ids': [(6, 0, [variant.id for variant in variants])],
                                           'parameter_ids': [(0,0,vals) for vals in dimensions],
                                           })
    def get_save_values(self):
        options = []
        variants = []
        dimensions = []
        for answer in self.answer_ids:
            question_type = answer.question_id.type
            if question_type == "option":
                options.append(answer.value_option)
            elif question_type == "variant":
                variants.append(answer.value_variant)
            elif question_type == "dimension":
                dimensions.append({
                                   'name': answer.question_id.dimension_type.name,
                                   'value': answer.value_dimension, 
                                   'type_param_id': answer.question_id.dimension_type.id,
                                   'sale_order_line_id': self.sale_order_line_id
                                   })
        
        options_all = self.env['mrp.option']
        for option in options:
            options_all = options_all | option
        return (options_all, variants, dimensions)

class fill_questionnaire_answer(models.TransientModel):
    """ 
    Answer to a question 
    """
    _name = 'fill.questionnaire.answer'
    _description = 'Answer to a question'
    
    @api.model
    def default_get(self, fields_list):
        res = super(fill_questionnaire_answer, self).default_get(fields_list=fields_list)
        question_id = self.env['variants.question'].browse(self.env.context['default_question_id'])
        if question_id.type == 'dimension' and question_id.dimension_limit_type == 'between':
            res['value_dimension'] = question_id.dimension_limit_min
        return res
    #===========================================================================
    # COLUMNS
    #===========================================================================
    fill_questionnaire_id = fields.Many2one('fill.questionnaire', string='Fill questionnaire', required=True, ondelete='cascade')
    question_id = fields.Many2one('variants.question', string='Question', required=True, ondelete='cascade')
    value_bool = fields.Boolean(string='Value', required=False)
    value_option = fields.Many2many('mrp.option')
    value_variant = fields.Many2one('variant.category.value')
    value_dimension = fields.Float(string="Value")
    value_dimension_selection = fields.Many2one('dimension.value', string="Value", domain="[('question_id', '=', default_question_id)]")
    question_label = fields.Char(related='question_id.label')
    help_text = fields.Char(related='question_id.help_text')
    dimension_limit_type = fields.Selection(related="question_id.dimension_limit_type")
    
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        name_type = {
                     'variant':'view_form_fill_questionnaire_answer_variant',
                     'option':'view_form_fill_questionnaire_answer_option',
                     'dimension':'view_form_fill_questionnaire_answer_dimension',
                     'boolean':'view_form_fill_questionnaire_answer_boolean',
                     }
        question_id = self.pool['variants.question'].browse(cr, uid, context['default_question_id'])
        name_for_type = name_type[question_id.type]
        view_id = self.pool['ir.ui.view'].search(cr, uid, [('name', '=', name_for_type)])
        return super(fill_questionnaire_answer, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar, submenu)
    
    @api.multi
    def next(self):
        if self.question_id.type == 'variant' and not self.value_variant:
            raise Warning('You must fill the value')
        if len(self.fill_questionnaire_id.last_replied_question_stack):
            new_list = self.fill_questionnaire_id.last_replied_question_stack.split('|')
            new_list.append(unicode(self.id))
            self.fill_questionnaire_id.last_replied_question_stack = "|".join(new_list)
        else:
            self.fill_questionnaire_id.last_replied_question_stack = self.id
        next_question_ids = self.env['variants.question'].search([
                                                                  ('questionnaire_id', '=', self.fill_questionnaire_id.questionnaire_id.id),
                                                                  ('sequence', '>', self.question_id.sequence)
                                                                  ], order = 'sequence')
        
        def compare(a, b, op):
            if op == '=':
                return a == b
            elif op == '!=':
                return a != b
            elif op =='>':
                return b > a
            elif op == '<':
                return a < b
            elif op == 'in' and b and len(b) > 0:
                return a in b
            elif op == 'not in' and b and len(b) > 0:
                return a not in b
            else:
                return False
        
        next_question = None
        for question in next_question_ids:
            if not question.condition_question:
                next_question = question
                break
            else:
                condition_question_answer = self.env['fill.questionnaire.answer'].search([
                                                                                          ('question_id', '=', question.condition_question.id),
                                                                                          ('fill_questionnaire_id', '=', self.fill_questionnaire_id.id)])
                if compare(question.get_condition_value(), condition_question_answer.get_value(), question.condition_operator):
                    next_question = question
                    break
            
        # no next question, questionnaire is finished
        if not next_question:
            self.fill_questionnaire_id.save_all_answers()
            return {
                    'type': 'ir.actions.act_window_close',
                    }
        return {
                'type':'ir.actions.act_window',
                'res_model':'fill.questionnaire.answer',
                'target':'new',
                'views': [[False, 'form']],
                'context': {
                            'default_fill_questionnaire_id': self.fill_questionnaire_id.id,
                            'default_question_id': next_question.id,
                            'default_question_label': next_question.label,
                            'default_help_text': next_question.help_text,
                            'default_dimension_limit_type': next_question.dimension_limit_type,
                            },
                }
    
    @api.multi
    def previous(self):
        prev_reply = int(self.fill_questionnaire_id.last_replied_question_stack.split('|')[-1])
        prev_reply = self.browse(prev_reply)
        prev_question = prev_reply.question_id
        if prev_question:
            fill_questionnaire_id = self.fill_questionnaire_id
            fill_questionnaire_id.last_replied_question_stack = "|".join(fill_questionnaire_id.last_replied_question_stack.split('|')[:-1])
            prev_reply.unlink()
            self.unlink()
            return {
                    'type':'ir.actions.act_window',
                    'res_model':'fill.questionnaire.answer',
                    'target':'new',
                    'views': [[False, 'form']],
                    'context': {
                                'default_fill_questionnaire_id': fill_questionnaire_id.id,
                                'default_question_id': prev_question.id,
                                'default_question_label': prev_question.label,
                                'default_help_text': prev_question.help_text,
                                'default_dimension_limit_type': prev_question.dimension_limit_type,
                                },
                    }
        else:
            return {
                    'type':'ir.actions.act_window_noclose',
                    }
        
    def get_value(self):
        question_type = self.question_id.type
        if question_type == 'boolean':
            return self.value_bool
        elif question_type == 'dimension':
            return self.value_dimension
        elif question_type == 'variant':
            return self.value_variant
        elif question_type == 'option':
            return self.value_option
        
    @api.onchange('value_dimension')
    def _onchange_value_dimension(self):
        question = self.env['variants.question'].browse(self.env.context['default_question_id'])
        if question.dimension_limit_type == 'between' and (self.value_dimension < question.dimension_limit_min or self.value_dimension > question.dimension_limit_max):
            return {'warning':{'title':'Warning', 'message':'{} < Value < {}'.format(question.dimension_limit_min, question.dimension_limit_max)}}
        elif question.dimension_limit_type == 'selection' and self.value_dimension:
            possible_values = [x.value for x in question.dimension_possible_values]
            if self.value_dimension not in possible_values:
                return {'warning':{'title':'Warning', 'message':'Value in '.format(possible_values)}}
            else:
                return
    
    @api.onchange('value_dimension_selection')
    def _onchange_value_dimension_selection(self):
        if self.question_id.dimension_limit_type == 'selection':
            self.value_dimension = float(self.value_dimension_selection.value)
    