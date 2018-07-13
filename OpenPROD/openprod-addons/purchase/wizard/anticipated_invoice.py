# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.addons.base_openprod.common import get_form_view

class purchase_anticipated_invoice(models.TransientModel):
    """ 
        Wizard to create an anticipated invoice from the purchase
    """
    _name = 'purchase.anticipated.invoice'
    _description = 'Wizard to create an anticipated invoice from the purchase'
    
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
    purchase_id = fields.Many2one('purchase.order', string='Purchase', required=False, ondelete='set null')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='set null',
                                 domain=[('state', 'in', ('lifeserie', 'endlife')), ('purchase_ok', '=', True),
                                         ('free_purchase', '=', True)])
    taxes_ids = fields.Many2many('account.tax', 'account_anticipated_purchase_tax_rel', 'purchase_order_id', 'tax_line_id', 
                                 string='Taxes', domain=[('type_tax_use', '!=', 'sale'), ('parent_id', '=', False)])
    amount_without_tax = fields.Float(string='Amount without taxes', default=0.0, required=True)
    tax_amount = fields.Float(string='Taxes amount', default=0.0, required=False, readonly=True)
    amount_with_tax = fields.Float(string='Amount with taxes', default=0.0, required=False, 
                                   compute='_compute_amount_with_tax', store=True)
    
    
    @api.model
    def default_get(self, fields_list):
        """
            Surcharge afin de récupérer l'achat pour lequel on effectue la facture anticipée
        """
        res = super(purchase_anticipated_invoice, self).default_get(fields_list=fields_list)
        purchase_id = self.env.context.get('active_id')
        if purchase_id and self.env.context.get('active_model') == 'purchase.order':
            res['purchase_id'] = purchase_id
                
        return res
    
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
            Au changement du produit, on va récupérer les taxes d'achat configurées
        """
        taxes_list = []
        if self.product_id and self.purchase_id:
            fiscal_position = self.purchase_id.purchase_account_system_id
            taxes_list = fiscal_position and fiscal_position.map_tax(self.product_id.purchase_taxes_ids) or []
        
        self.taxes_ids = taxes_list
        
        
    @api.onchange('taxes_ids', 'amount_without_tax')
    def _onchange_taxes_ids(self):
        """
            A la modification des taxes, on va recalculer leur montant ainsi que le montant total
        """
        tax_amount = 0
        if self.product_id and self.purchase_id:
            taxes = self.taxes_ids.compute_all(self.amount_without_tax, self.purchase_id.currency_id, 1, 
                                               self.product_id, self.purchase_id.partner_id)['taxes']
            tax_amount_list = [tax['amount'] for tax in taxes]
            tax_amount = sum(tax_amount_list)
        
        self.tax_amount = tax_amount
        self.amount_with_tax = tax_amount + self.amount_without_tax
    
    
    @api.multi
    def create_anticipated_invoice(self):
        """
            Fonction permettant de créer une facture anticipée pour l'achat et de l'afficher
        """
        purchase = self.purchase_id
        product = self.product_id
        if purchase and purchase.purchase_order_line_ids and product:
            context2 = {'force_invoice_price': True}
            context2.update(self.env.context)
            invoice_line_obj = self.env['account.invoice.line']
            other_data = {
                          'fiscal_position_id': purchase.purchase_account_system_id.id,
                          'currency_id': purchase.currency_id.id,
                          'company_id': purchase.company_id.id,
                          'delivery_partner_id': purchase.delivered_by_id.id,
                          'partner_order_id': purchase.partner_id.id,
                          'address_id': purchase.delivered_address_id.id,
                          'payment_term_id': purchase.payment_term_id.id,
                          'discount_management': purchase.discount,
                          'discount_value': purchase.discount_value,
                          'max_delay': purchase.max_delay,
                          'payment_method_id': purchase.payment_id.id,
                          'paid_by_id': purchase.paid_to_id.id,
                          'anticipated': True,
                          'origin': purchase.name_get()[0][1],
                          }
            
            journal_purchase_rcs = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)
            if journal_purchase_rcs:
                other_data['journal_id'] = journal_purchase_rcs.id
            
            invoice = self.env['account.invoice'].create_invoice(purchase.invoiced_by_id, purchase.invoiced_by_id.address_id, 'in_invoice', other_data)
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
                        'purchase_order_line_id': purchase.purchase_order_line_ids[0].id,
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
        
        
