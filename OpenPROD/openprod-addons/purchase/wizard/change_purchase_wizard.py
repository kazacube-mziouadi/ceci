# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm
from openerp.addons.base_openprod.common import get_form_view

    
class change_purchase_line_information(models.TransientModel):
    """ 
        Wizard to change the purchase line information
    """
    _name = 'change.purchase.line.information'
    _description = 'Modification of the purchase line information'
    
    @api.model
    def default_get(self, fields_list):
        res = super(change_purchase_line_information, self).default_get(fields_list=fields_list)
        purchase_line_id = self.env.context.get('purchase_line_id')
        if purchase_line_id and self.env.context.get('active_model') == 'purchase.order.line':
            purchase_line = self.env['purchase.order.line'].browse(purchase_line_id)
            if purchase_line:
                res = {
                       'purchase_line_id': purchase_line.id,
                       'expected_date': purchase_line.expected_date,
                       'confirmed_date': purchase_line.confirmed_date,
                       'name': purchase_line.name,
                       'price_unit': purchase_line.price_unit,
                       'internal_note': purchase_line.internal_note,
                       'receipt_printed_note': purchase_line.receipt_printed_note,
                       'invoice_printed_note': purchase_line.invoice_printed_note,
                       'order_printed_note': purchase_line.order_printed_note,
                       }
                
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    purchase_line_id = fields.Many2one('purchase.order.line', string='Purchase line', required=False, ondelete='set null')
    expected_date = fields.Date(string='Expected date', required=True)
    confirmed_date = fields.Date(string='Confirmed date', required=False)
    name = fields.Text(string='Description', required=True)
    price_unit = fields.Float(string='Price unit', default=0.0, digits=dp.get_precision('Product price'), 
                              required=True)
    internal_note = fields.Text(string='Internal note')
    receipt_printed_note = fields.Text(string='Note printed on the receipt note line')
    invoice_printed_note = fields.Text(string='Note printed on the invoice line')
    order_printed_note = fields.Text(string='Product note printed on order')

    
    #===========================================================================
    # FUNCTION et BOUTON
    #===========================================================================
    def prepar_sale_line_vals(self):
        return {
                'expected_date': self.expected_date,
                'confirmed_date': self.confirmed_date,
                'name': self.name,
                'price_unit': self.price_unit,
                'internal_note': self.internal_note,
                'receipt_printed_note': self.receipt_printed_note,
                'invoice_printed_note': self.invoice_printed_note,
                'order_printed_note': self.order_printed_note,
              }
    
    
    def prepar_invoice_line_vals(self):
        return {
                  'name': self.name,
                  'price_unit': self.price_unit,
                  'note_invoice_header': self.invoice_printed_note,
                  'note_invoice_intern': self.internal_note,
                  }
        
        
    @api.multi
    def change_line_information(self):
        """
            Fonction permettant de modifier les informations d'une ligne d'achat
        """
        purchase_line = self.purchase_line_id
        invoice_list = self.env['account.invoice']
        if purchase_line:
            purchase_line_vals = self.prepar_sale_line_vals()
            purchase_line.write(purchase_line_vals)
            purchase_line.purchase_order_id._onchange_purchase_order_line_ids()
            move_rs = purchase_line.stock_move_ids
            date = purchase_line.confirmed_date or purchase_line.expected_date
            move_rs.write({
                            'name': self.name,
                            'date_expected': date,
                            'date': date,
                            'priority_date': date,
                            'partner_price': self.price_unit,
                            'note': self.internal_note,
                            })
            
            move_label_rcs = self.env['stock.move.label']
            for move in move_rs:
                if move.state == 'done':
                    move_label_rcs |= move.move_label_ids
            
            if move_label_rcs:
                move_label_rcs.write({'done_date': date})
            
            
            for invoice_line in purchase_line.invoice_line_ids:
                if invoice_line.invoice_id not in invoice_list:
                    invoice_list += invoice_line.invoice_id
                
                invoice_line_vals = self.prepar_invoice_line_vals()
                invoice_line.write(invoice_line_vals)

            for invoice in invoice_list:    
                invoice._onchange_invoice_line_ids()
            
        return {'type':'ir.actions.act_window_view_reload'}
        
        
