# coding: utf-8

from openerp import models, fields, api

class fill_questionnaire(models.Model):
    _inherit = 'fill.questionnaire'
    
    specific_offer_id = fields.Many2one('specific.offer', string='Specific offer', required=False, ondelete='cascade')
    
    def save_all_answers(self):
        if self.specific_offer_id:
            options, variants, dimensions = self.get_save_values()
            self.specific_offer_id.parameter_ids.unlink()
            self.specific_offer_id.option_ids.unlink()
            self.specific_offer_id.write({
                                           'option_ids': [(0, 0, {'option_id':opt.id, 'price_unit':opt.price_unit}) for opt in options],
                                           'variant_value_ids': [(6, 0, [variant.id for variant in variants])],
                                           'parameter_ids': [(0,0,vals) for vals in dimensions],
                                           })
        else:
            super(fill_questionnaire, self).save_all_answers()