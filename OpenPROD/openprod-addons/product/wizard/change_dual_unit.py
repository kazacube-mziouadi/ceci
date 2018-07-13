# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.addons.base_openprod.common import get_form_view

class change_dual_unit(models.TransientModel):
    """ 
        Wizard to change the product dual unit
    """
    _name = 'change.dual.unit'
    _description = 'Modification of the product dual unit'
    _rec_name = 'product_id'
    
    @api.model
    def _dual_type_get(self):
        return [
                ('fixed', _('Fixed')),
                ('variable', _('Variable')),
                       ]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    dual_unit = fields.Boolean(string='Dual unit', default=False)
    sec_uom_id = fields.Many2one('product.uom', string='Second unit of measure', required=False)
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='cascade')
    dual_unit_type = fields.Selection('_dual_type_get', string='Dual unit type', default='fixed')
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(change_dual_unit, self).default_get(fields_list=fields_list)
        context = self.env.context
        if context.get('active_model') == 'product.product' and context.get('active_id'):
            product = self.env['product.product'].browse(context['active_id'])
            res['dual_unit'] = product.dual_unit
            res['dual_unit_type'] = product.dual_unit_type
            res['product_id'] = product.id
            res['sec_uom_id'] = product.sec_uom_id.id
                
        return res
    
    
    @api.multi
    def change_dual_unit(self):
        return self.product_id.with_context(force_change_dual_unit=True).write({
                                                                         'dual_unit': self.dual_unit,
                                                                         'dual_unit_type': self.dual_unit_type,
                                                                         'sec_uom_id': self.sec_uom_id.id,
                                                                        })
    