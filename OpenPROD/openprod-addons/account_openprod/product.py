# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, ValidationError, UserError


class product_product(models.Model):
    _inherit = "product.product"
    
    @api.model
    def _inventory_valuation_get(self):
        return [
                ('lot', _('Lot')),
                ('average', _('Weighted average price')),
                       ]
    
    
    @api.model
    def _type_valuation_purchase_get(self):
        return [
                ('real', _('Real')),
                ('theoretical', _('Theoretical')),
                       ]
        
        
    @api.model
    def _type_valuation_production_get(self):
        return [
                ('real', _('Real')),
                ('theoretical', _('Theoretical')),
                ('manual', _('Manual')),
                ('pourcent_sale', _('% Sale price'))
                       ]
        
        
    @api.multi
    def _get_product_accounts(self):
        return {
            'income': self.property_account_income_id or self.categ_id.property_account_income_categ_id,
            'expense': self.property_account_expense_id or self.categ_id.property_account_expense_categ_id
        }


    @api.multi
    def get_product_accounts(self, fiscal_pos=None):
        accounts = self._get_product_accounts()
        if not fiscal_pos:
            fiscal_pos = self.env['account.fiscal.position']
        return fiscal_pos.map_accounts(accounts)
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    # Prix
    inventory_valuation = fields.Selection('_inventory_valuation_get', string='Inventory valuation', help="")
    type_valuation_purchase = fields.Selection('_type_valuation_purchase_get', string='Type valuation purchase', help="")
    type_valuation_production = fields.Selection('_type_valuation_production_get', string='Type valuation production', help="")
    price_theo_manual = fields.Float(string='Price theo manual', default=0.0, required=False)
    pourcent_sale_price = fields.Float(string='% Sale price', default=0.0, required=False)
    # Note imprimée sur la facture
    description_invoice = fields.Text(string='Note printed on demand invoice')
        
    # Compte comptable
    property_account_income_id = fields.Many2one('account.account', string='Income Account', ondelete='restrict', 
        help="This account will be used for invoices instead of the default one to value sales for the current product.")
    property_account_expense_id = fields.Many2one('account.account', string='Expense Account', ondelete='restrict', 
        help="This account will be used for invoices instead of the default one to value expenses for the current product.")
        
    # Taxes sur les ventes et les achats
    sale_taxes_ids = fields.Many2many('account.tax',
        'product_product_taxes_rel', 'prod_id', 'tax_id',
        string='Sales Taxes', domain=[('type_tax_use','in',['sale','all']), ('parent_id', '=', False)])
    purchase_taxes_ids = fields.Many2many('account.tax',
        'product_product_supplier_taxes_rel', 'prod_id', 'tax_id',
        string='Purchase Taxes', domain=[('type_tax_use','in',['purchase','all']), ('parent_id', '=', False)])
    
    
    @api.onchange('categ_id')
    def _onchange_categ_id(self):
        """
            Si la catégorie sélectionnée a un compte de revenu et un compte de dépenses, 
            on rempli le produit avec
        """
        if self.categ_id:
            if self.categ_id.property_account_expense_categ_id:
                self.property_account_expense_id = self.categ_id.property_account_expense_categ_id.id
            
            if self.categ_id.property_account_income_categ_id:
                self.property_account_income_id = self.categ_id.property_account_income_categ_id.id
                
        else:
            self.property_account_expense_id = False
            self.property_account_income_id = False
            
    
    @api.multi
    def write(self, vals=None):
        """
            Interdiction de changer de catégorie
        """
                
        res = super(product_product, self).write(vals=vals)
        for product in self:
            if product.inventory_valuation == 'lot' and not product.track_label and product.type != 'service':
                raise except_orm(_('Error'), _("The valuation type can not be 'lot' if the product is not track label"))
            
        return res
    
    
    @api.model
    def create(self, vals):
        if not vals:
            vals = {}
        
        res = super(product_product, self).create(vals=vals)
        if res.inventory_valuation == 'lot' and not res.track_label and res.type != 'service':
                raise except_orm(_('Error'), _("The valuation type can not be 'lot' if the product is not track label"))
            
        return res
            