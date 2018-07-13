# coding: utf-8

from openerp import models, fields, api

class create_configure_sol(models.TransientModel):
    """ 
    Create and configure a Sale Order Line 
    """
    _name = 'create.configure.sol'
    _description = 'Create and configure a Sale Order Line'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    sale_order_id = fields.Many2one('sale.order', string='Sale order', required=False, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    quantity = fields.Float(string="Quantity", default=0.0, required=True)
    requested_date = fields.Date(string='Requested date', required=True)
    sale_partner_id = fields.Many2one(related="sale_order_id.partner_id")
    
    @api.multi
    def create_configure(self):
        sol_obj = self.env['sale.order.line']
        sale_order_line_id = sol_obj.create_sale_order_line(self.sale_order_id, 
                                                            self.product_id, {
                                                                              'sec_uom_qty':self.quantity,
                                                                              'requested_date': self.requested_date,
                                                                              })
        self.sale_order_id._onchange_order_line_ids()
        action_config = {
                'type':'ir.actions.act_window',
                'res_model':'fill.questionnaire',
                'target':'new',
                'views': [[False, 'form']],
                'context': {
                            'default_sale_order_line_id': sale_order_line_id.id,
                            }
                }
        return action_config