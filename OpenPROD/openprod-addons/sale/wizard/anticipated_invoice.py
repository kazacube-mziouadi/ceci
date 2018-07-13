# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.addons.base_openprod.common import get_form_view

class sale_anticipated_invoice(models.TransientModel):
    """ 
        Wizard to create an anticipated invoice from the sale
    """
    _name = 'sale.anticipated.invoice'
    _description = 'Wizard to create an anticipated invoice from the sale'
    
    @api.one
    @api.depends('amount_without_tax', 'tax_amount', 'taxes_ids')
    def _compute_amount_with_tax(self):
        """
            Calcul du montant total avec les taxes
        """
        tax_amount = 0
        self.tax_amount = tax_amount
        self.amount_with_tax = self.amount_without_tax + tax_amount
        
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    sale_id = fields.Many2one('sale.order', string='Sale', required=False, ondelete='set null')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='set null',
                                 domain=[('state', 'in', ('lifeserie', 'endlife')), ('sale_ok', '=', True),
                                         ('free_sale', '=', True)])
    taxes_ids = fields.Many2many('account.tax', 'account_anticipated_tax_rel', 'sale_order_id', 'tax_line_id', 
                                 string='Taxes', domain=[('type_tax_use', '!=', 'purchase'), ('parent_id', '=', False)])
    amount_without_tax = fields.Float(string='Amount without taxes', default=0.0, required=True)
    tax_amount = fields.Float(string='Taxes amount', default=0.0, required=False, readonly=True)
    amount_with_tax = fields.Float(string='Amount with taxes', default=0.0, required=False, 
                                   compute='_compute_amount_with_tax', store=True)
    
    
    @api.model
    def default_get(self, fields_list):
        """
            Surcharge afin de récupérer la vente pour laquelle on effectue la facture anticipée
        """
        res = super(sale_anticipated_invoice, self).default_get(fields_list=fields_list)
        sale_id = self.env.context.get('active_id')
        if sale_id and self.env.context.get('active_model') == 'sale.order':
            res['sale_id'] = sale_id
                
        return res
    
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
            Au changement du produit, on va récupérer les taxes de vente configurées
        """
        taxes_list = []
        if self.product_id and self.sale_id:
            fiscal_position = self.sale_id.sale_account_system_id
            taxes_list = fiscal_position and fiscal_position.map_tax(self.product_id.sale_taxes_ids) or []
        
        self.taxes_ids = taxes_list
        
        
    @api.onchange('taxes_ids', 'amount_without_tax')
    def _onchange_taxes_ids(self):
        """
            A la modification des taxes, on va recalculer leur montant ainsi que le montant total
        """
        tax_amount = 0
        if self.product_id and self.sale_id:
            taxes = self.taxes_ids.compute_all(self.amount_without_tax, self.sale_id.currency_id, 1, 
                                               self.product_id, self.sale_id.partner_id)['taxes']
            tax_amount_list = [tax['amount'] for tax in taxes]
            tax_amount = sum(tax_amount_list)
        
        self.tax_amount = tax_amount
        self.amount_with_tax = tax_amount + self.amount_without_tax
    
    
    @api.multi
    def create_anticipated_invoice(self):
        """
            Fonction permettant de créer une facture anticipée pour la vente et de l'afficher
        """
        sale = self.sale_id
        product = self.product_id
        if sale and sale.order_line_ids and product:
            context2 = {'force_invoice_price': True}
            context2.update(self.env.context)
            invoice_line_obj = self.env['account.invoice.line']
            invoiced_partner = sale.invoiced_customer_id
            other_data = {
                          'fiscal_position_id': sale.sale_account_system_id.id,
                          'currency_id': sale.currency_id.id,
                          'company_id': sale.company_id.id,
                          'delivery_partner_id': sale.delivered_customer_id.id,
                          'partner_order_id': sale.partner_id.id,
                          'address_id': sale.invoicing_address_id.id,
                          'lock_invoice': sale.locked_invoice,
                          'group_invoices': sale.group_invoices,
                          'invoices_period': sale.invoices_period,
                          'declaration_deb': sale.subject_deb,
                          'tva_number': sale.tva_number,
                          'note_invoice_intern': sale.inter_note,
                          'note_invoice_header': sale.invoice_note,
                          'payment_term_id': sale.payment_term_id.id,
                          'discount_management': sale.discount,
                          'discount_value': sale.discount_value,
                          'max_delay': sale.max_delay,
                          'payment_method_id': sale.payment_id.id,
                          'paid_by_id': sale.paid_customer_id.id,
                          'contact_ids': [(4, contact_id) for contact_id in invoiced_partner.invoicing_contact_ids.ids],
                          'communication_method': invoiced_partner.accounting_communication_method,
                          'anticipated': True,
                          'origin': sale.name_get()[0][1],
                          }
            invoice = self.env['account.invoice'].create_invoice(invoiced_partner, sale.order_address_id, 'out_invoice', other_data)
            other_data = {
                        'sec_uom_qty': 1,
                        'sec_uom_id': product.uom_id.id,
                        'uom_qty': 1,
                        'uom_id': product.uom_id.id,
                        'quantity': 1,
                        'uoi_id': product.uom_id.id,
                        'price_unit': self.amount_without_tax,
                        'invoice_line_tax_ids': [(6, 0, [x.id for x in self.taxes_ids])],
                        'name': product.name,
                        'sale_order_line_id': sale.order_line_ids[0].id,
                          }
            invoice_line_obj.with_context(context2).create_invoice_line(invoice.id, product, True, other_data)
            invoice._onchange_invoice_line_ids()
            #On affiche la facture qui vient d'être créée
            action_dict = get_form_view(self, 'account_openprod.action_see_one_invoice')
            if action_dict and action_dict.get('id') and action_dict.get('type'):
                action = self.env[action_dict['type']].browse(action_dict['id'])
                action_struc = action.read()
                action_struc[0]['res_id'] = invoice.id
                action_struc = action_struc[0]
                  
            return action_struc
        else:
            return  {'type': 'ir.actions.act_window_close'}
        
