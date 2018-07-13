# coding: utf-8
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp


class change_simulation_line(models.TransientModel):
    """ 
    Change product and quantity of a simulation line 
    """
    _name = 'change.simulation.line'
    _description = 'Change product and quantity of a simulation line'
    
    def _get_product_id(self):
        line_id = self.env['simulation.line'].browse(self.env.context['active_id'])
        return line_id.product_id
    
    def _get_quantity(self):
        line_id = self.env['simulation.line'].browse(self.env.context['active_id'])
        return line_id.quantity
    
    def _get_supplier_id(self):
        line_id = self.env['simulation.line'].browse(self.env.context['active_id'])
        return line_id.supplier_id
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    simulation_line_id = fields.Many2one('simulation.line', string='Line', required=True, default=lambda self:self.env.context['active_id'], ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, domain=[('supply_method', '=', 'buy')], default=_get_product_id)
    quantity = fields.Float(string='Quantity', digits=dp.get_precision('Product quantity'), required=True, default=_get_quantity)
    unit_price = fields.Float(string='Unit price', digits=dp.get_precision('Account'), required=False)
    supplier_id = fields.Many2one('res.partner', string='Supplier', required=False, ondelete='restrict', domain="[('is_supplier', '=', True), ('supplierinfo_product_search', '=', product_id)]", default=_get_supplier_id)
    
    @api.multi
    def update_line(self):
        for line in self:
            change_supplier = self.supplier_id != line.simulation_line_id.supplier_id
            line.simulation_line_id.write({
                                            'product_id': self.product_id.id,
                                            'quantity': self.quantity,
                                            'unit_price':self.unit_price,
                                            'total_price':self.unit_price * self.quantity,
                                            'supplier_id':self.supplier_id.id,
                                           })
            if change_supplier:
                line.simulation_line_id._onchange_supplier_id()
            specific_offer_id = line.simulation_line_id.specific_offer_id
            total_price = sum([x['total_price'] for x in specific_offer_id.simulation_line_ids])
            specific_offer_id.write({'total_price':total_price, 'unit_price':total_price / specific_offer_id.quantity})
            line.simulation_line_id.update_parents()
            specific_offer_id.compute_critical_path()
        return {'type': 'ir.actions.client', 'tag': 'reload', }
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        bom_obj = self.env['mrp.bom']
        self.unit_price = bom_obj.compute_price_component_buy(self.product_id, self.quantity, self.product_id.uom_id, self.env.user.company_id.currency_id)
        