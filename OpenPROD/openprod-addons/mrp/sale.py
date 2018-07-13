# -*- coding: utf-8 -*-
from openerp import models, api, fields
import openerp.addons.decimal_precision as dp


class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
    
    option_lines_ids = fields.One2many('sale.order.line.option', 'sol_id', string='Options lines', copy=True)
    
    @api.onchange('sec_uom_qty', 'sec_uom_id', 'property_ids', 'parameter_ids', 'option_lines_ids')
    def _onchange_sec_uom_qty(self, with_warning=True):
        """
            Au changement de la qty, changement des autres qty
        """
        return super(sale_order_line, self)._onchange_sec_uom_qty(with_warning=with_warning)
    
class sale_order_line_option(models.Model):
    """ 
    Sale order line option 
    """
    _name = 'sale.order.line.option'
    _description = 'Sale order line option'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    sol_id = fields.Many2one('sale.order.line', string='Sale order line', required=True, ondelete='cascade')
    option_id = fields.Many2one('mrp.option', string='Option', required=True, ondelete='cascade')
    price_unit = fields.Float(string='Price unit', default=0.0, digits=dp.get_precision('Product price'))
    
    @api.onchange('option_id')
    def _onchange_option_id(self):
        self.price_unit = self.option_id.price_unit