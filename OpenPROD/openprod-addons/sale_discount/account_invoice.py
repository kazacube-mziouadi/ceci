# -*- coding: utf-8 -*-
from openerp import models, api, fields
import openerp.addons.decimal_precision as dp


class account_invoice_line(models.Model):
    _inherit = 'account.invoice.line'

    @api.one
    @api.depends('price_unit_without_discount', 'fixed_discount', 'variable_discount', 'quantity')
    def _compute_price_unit_discount(self):
        """
            Fonction qui permet de calculer le prix par rapport aux remise
        """
        if self.price_unit_without_discount > 0:
            price_unit = self.price_unit_without_discount - self.fixed_discount - self.variable_discount*self.price_unit_without_discount/100
            if price_unit < 0:
                price_unit = 0.0
        else:
            price_unit = self.price_unit_without_discount
            
        self.price_unit = price_unit
        
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    price_unit = fields.Float(string='Price unit', digits=dp.get_precision('Product price'), compute='_compute_price_unit_discount', store=True)
    

    def fonction_discount_invoice(self, sale_order_line_id):
        """
            Fonction permettant de recopier dans la facture les remises faites dans la vente
        """
        discount_vals = super(account_invoice_line, self).fonction_discount_invoice(sale_order_line_id)
        sale_line = self.env['sale.order.line'].browse(sale_order_line_id)
        if sale_line.fixed_discount_ids:
            discount_vals['fixed_discount_ids'] = []
            for fixed_discount in sale_line.fixed_discount_ids:
                vals_fixed_discount = {
                                        'sequence': fixed_discount.sequence,
                                        'descriptive': fixed_discount.descriptive,
                                        'amount': fixed_discount.amount,
                                      }
                
                discount_vals['fixed_discount_ids'].append((0, 0, vals_fixed_discount))
        
        if sale_line.variable_discount_ids:   
            discount_vals['variable_discount_ids'] = [] 
            for variable_discount in sale_line.variable_discount_ids:
                vals_variable_discount = {
                                        'sequence': variable_discount.sequence,
                                        'descriptive': variable_discount.descriptive,
                                        'amount': variable_discount.amount,
                                        'type': variable_discount.type,
                                      }
                
                discount_vals['variable_discount_ids'].append((0, 0, vals_variable_discount))
        
        discount_vals['price_unit_without_discount'] = sale_line.price_unit_without_discount
        discount_vals['is_print_discount'] = sale_line.is_print_discount

        return discount_vals
    
    
    def fonction_discount_invoice_refund(self):
        """
            Fonction permettant de recopier dans l'avoir les remises faites dans la facture
        """
        discount_vals = super(account_invoice_line, self).fonction_discount_invoice_refund()
        if self.fixed_discount_ids:
            discount_vals['fixed_discount_ids'] = []
            for fixed_discount in self.fixed_discount_ids:
                vals_fixed_discount = {
                                        'sequence': fixed_discount.sequence,
                                        'descriptive': fixed_discount.descriptive,
                                        'amount': fixed_discount.amount,
                                      }
                
                discount_vals['fixed_discount_ids'].append((0, 0, vals_fixed_discount))
        
        if self.variable_discount_ids:   
            discount_vals['variable_discount_ids'] = [] 
            for variable_discount in self.variable_discount_ids:
                vals_variable_discount = {
                                        'sequence': variable_discount.sequence,
                                        'descriptive': variable_discount.descriptive,
                                        'amount': variable_discount.amount,
                                        'type': variable_discount.type,
                                      }
                
                discount_vals['variable_discount_ids'].append((0, 0, vals_variable_discount))
        
        discount_vals['price_unit_without_discount'] = self.price_unit_without_discount
        discount_vals['is_print_discount'] = self.is_print_discount

        return discount_vals
    
    
    @api.multi
    def write(self, vals=None):
        """
            Surcharge du write afin de remplir le champ price_unit_without_discount s'il est vide 
        """
        line_modif_price = self.env['account.invoice.line']
        for line in self:
            if 'price_unit' in vals and ('price_unit_without_discount' not in vals or not vals['price_unit_without_discount']) and not line.price_unit_without_discount:
                line_modif_price += line
        
        res = super(account_invoice_line, self).write(vals=vals)
        if line_modif_price:
            line_modif_price.write({'price_unit_without_discount': vals['price_unit']})
        
        return res
    
    @api.model
    def create(self, vals):
        """
            Surcharge du create afin de remplir le champ price_unit_without_discount s'il est vide 
        """
        if 'price_unit' in vals and ('price_unit_without_discount' not in vals or not vals['price_unit_without_discount']):
            vals['price_unit_without_discount'] = vals['price_unit']
        
        return super(account_invoice_line, self).create(vals)
    
    
    