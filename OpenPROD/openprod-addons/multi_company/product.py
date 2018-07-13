# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, ValidationError, UserError


class product_product(models.Model):
    _inherit = "product.product"
    
    @api.one
    def _compute_property_account_income_id(self):
        property_account_income_id = False        
        mcpai_rcs = self.env['multi.company.product.acc.income'].search([('company_id', '=', self.env.user.company_id.id), ('product_id', '=', self.id)], limit=1)
        if mcpai_rcs:
            property_account_income_id = mcpai_rcs.account_id.id
            
        self.property_account_income_id = property_account_income_id
    
    
    @api.one
    def _compute_property_account_expense_id(self):
        property_account_expense_id = False        
        mcpae_rcs = self.env['multi.company.product.acc.expense'].search([('company_id', '=', self.env.user.company_id.id), ('product_id', '=', self.id)], limit=1)
        if mcpae_rcs:
            property_account_expense_id = mcpae_rcs.account_id.id
            
        self.property_account_expense_id = property_account_expense_id
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    # Compte comptable
    property_account_income_id = fields.Many2one('account.account', string='Income Account', compute='_compute_property_account_income_id', store=False,
        help="This account will be used for invoices instead of the default one to value sales for the current product.")
    property_account_expense_id = fields.Many2one('account.account', string='Expense Account', compute='_compute_property_account_expense_id', store=False,
        help="This account will be used for invoices instead of the default one to value expenses for the current product.")
    
    mcpai_ids = fields.One2many('multi.company.product.acc.income', 'product_id',  string='Account income')
    mcpae_ids = fields.One2many('multi.company.product.acc.expense', 'product_id',  string='Account expense')

    
    @api.multi
    def write(self, vals=None):
        """
            Interdiction de changer de catégorie
        """
                
        res = super(product_product, self).write(vals=vals)
        mcpae_obj = self.env['multi.company.product.acc.expense']
        mcpai_obj = self.env['multi.company.product.acc.income']
        company = self.env.user.company_id
        for product in self:
            if product.state in ('endlife', 'lifeserie'):
                if product.purchase_ok:
                    mcpae_rcs = mcpae_obj.search([('product_id', '=', product.id), ('company_id', '=', company.id)], limit=1)
                    if not mcpae_rcs:
                        raise except_orm(_('Error'), _("You need an expense account for this company '%s' in this product '%s'."%(company.name, product.code)))
                    
                    pur_error_tax = True
                    for tax in product.purchase_taxes_ids:
                        if tax.company_id.id == company.id:
                            pur_error_tax = False
                            break
                        
                    if pur_error_tax:
                        raise except_orm(_('Error'), _("There is a purchase tax for this company '%s' in this product '%s'."%(company.name, product.code)))
                
                if product.sale_ok:
                    mcpai_rcs = mcpai_obj.search([('product_id', '=', product.id), ('company_id', '=', company.id)], limit=1)
                    if not mcpai_rcs:
                        raise except_orm(_('Error'), _("You need an income account for this company '%s' in this product '%s'."%(company.name, product.code)))
                    
                    sale_error_tax = True
                    for tax in product.sale_taxes_ids:
                        if tax.company_id.id == company.id:
                            sale_error_tax = False
                            break
                        
                    if sale_error_tax:
                        raise except_orm(_('Error'), _("There is a sale tax for this company '%s' in this product '%s'."%(company.name, product.code)))
                
            
        return res
    
    
    
class multi_company_product_acc_income(models.Model):
    """ 
    Multi company product account income 
    """
    _name = 'multi.company.product.acc.income'
    _description = 'Multi company partner account income'
    _rec_name = 'account_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    account_id = fields.Many2one('account.account', string='Income Account', required=True, ondelete='restrict',
                                 help="This account will be used for invoices instead of the default one to value sales for the current product.")
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', required=True, ondelete='restrict')



class multi_company_product_acc_expense(models.Model):
    """ 
    Multi company product account expense 
    """
    _name = 'multi.company.product.acc.expense'
    _description = 'Multi company product account expense'
    _rec_name = 'account_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    account_id = fields.Many2one('account.account', string='Expense Account', required=True, ondelete='restrict', 
                                 help="This account will be used for invoices instead of the default one to value expenses for the current product.")
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', required=True, ondelete='restrict')
    
    
    
    