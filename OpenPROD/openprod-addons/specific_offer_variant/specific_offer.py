# coding: utf-8
from openerp import models, api, fields

class specific_offer(models.Model):
    _inherit = 'specific.offer'
    
    variant_value_ids = fields.Many2many('variant.category.value', string='Variant values')
    parameter_ids = fields.One2many('parameter.dimension', 'specific_offer_id', string='Parameters', copy=True)
    model_id = fields.Many2one('product.product', string='Model', required=False, ondelete='cascade', domain=[('supply_method', '=', 'produce'), ('model_id', '=', None)])
    
    
    @api.multi
    def create_specific_product(self):
        ret = super(specific_offer, self).create_specific_product()
        for offer in self:
            offer.parameter_ids.copy({'specific_offer_id': False, 
                                            'product_id': offer.product_id.id})
        return ret