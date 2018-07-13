# -*- coding: utf-8 -*-
from openerp import models, api, fields
from collections import Counter
from openerp.tools.translate import _


class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
    
    variant_category_value_ids = fields.Many2many('variant.category.value', string='Values', required=False)
    
    @api.one
    @api.constrains('variant_category_value_ids')
    def _check_variant_value_ids(self):
        dup = Counter([x.variant_category_id for x in self.variant_category_value_ids])
        for x in dup.values():
            if x > 1:
                raise Warning(_('Multiple values for the same category selected'))
    
    
    @api.onchange('sec_uom_qty', 'sec_uom_id', 'property_ids', 'parameter_ids', 'option_lines_ids', 'variant_category_value_ids')
    def _onchange_sec_uom_qty(self, with_warning=True):
        """
            Au changement de la qty, changement des autres qty
        """
        return super(sale_order_line, self)._onchange_sec_uom_qty(with_warning=with_warning)