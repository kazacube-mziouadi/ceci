# -*- coding: utf-8 -*-
from openerp import models, api, fields
from compute_amount import compute_amount
from openerp.tools.translate import _

class analytic_distribution(models.Model):
    """
   Analytic distribution
    """
    _name = 'analytic.distribution'
    _description = 'Analytic distribution'
    _rec_name = 'pad_id'

    
    @api.model
    def _type_get(self):
        return [
            ('fixed', _('Fixed')),
            ('percentage', _('Percentage')),
            ('proportional', _('Proportional')),
            ('garbage', _('Garbage collector')),
        ]
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    pad_id = fields.Many2one('product.analytic.distribution', string='PAD', required=True, ondelete='cascade')
    type = fields.Selection('_type_get', string='Type', default='percentage')
    value = fields.Float(string='Value', default=0.0, required=False)
    account_id = fields.Many2one('account.analytic.account', string='Account', required=True, ondelete='restrict')
    is_proportional = fields.Boolean(string='Proportional', default=False)
    
    
    
class product_analytic_distribution(models.Model):
    '''
   Product analytic distribution
    '''
    _name = 'product.analytic.distribution'
    _description = 'Product analytic distribution'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, ondelete='restrict')
    sale_ok = fields.Boolean(string='Authorize sale', default=False)
    purchase_ok = fields.Boolean(string='Authorize purchase', default=False)
    production_ok = fields.Boolean(string='Authorize production', default=False)
    distribution_ids = fields.One2many('analytic.distribution', 'pad_id',  string='Distribution')
    note = fields.Text(string='Note')



class purchase_sale_analytic_distribution(models.Model):
    """
       Analytic distribution for Sales and purchases
    """
    _name = 'purchase.sale.analytic.distribution'
    _description = 'Purchase sale analytic distribution'
    _rec_name = 'account_id'
    
    
    @api.model
    def _type_get(self):
        return [
            ('fixed', _('Fixed')),
            ('percentage', _('Percentage')),
            ('proportional', _('Proportional')),
            ('garbage', _('Garbage collector')),
        ]
    
    
    @api.one
    @api.depends('analytic_sale_order_line_id.price_unit', 'analytic_sale_order_line_id.sec_uom_qty', 'type', 'value',
                 'analytic_purchase_order_line_id.price_unit', 'analytic_purchase_order_line_id.sec_uom_qty', 
                 'invoice_line_id.price_unit', 'invoice_line_id.sec_uom_qty', 'analytic_mo_id', 'analytic_mo_id.type_compute_analytic_prod', 
                 'analytic_mo_id.real_total_cost', 'analytic_mo_id.theo_total_cost')
    def _compute_total_analytic_distribution(self):
        """
            Fonction permettant de calculer le montant de la ligne de distribution analytique en 
            fonction de la ligne de vente
        """
        total = 0
        total_currency = 0
        company_rs = False
        currency_rs = False
        if self.invoice_line_id:
            company_rs = self.invoice_line_id.invoice_id.company_id     
            currency_rs = self.invoice_line_id.currency_id    
            total_price = self.invoice_line_id.price_subtotal
            if self.type == 'garbage':
                total_amount = sum([compute_amount(l.type, l.value, total_price) for l in self.invoice_line_id.distribution_ids if l.type != 'garbage'])
                total = total_price - total_amount
            else:
                total = compute_amount(self.type, self.value, total_price)
        
        elif self.analytic_sale_order_line_id:
            company_rs = self.analytic_sale_order_line_id.sale_order_id.company_id     
            currency_rs = self.analytic_sale_order_line_id.currency_id    
            total_price = self.analytic_sale_order_line_id.total_price
            if self.type == 'garbage':
                total_amount = sum([compute_amount(l.type, l.value, total_price) for l in self.analytic_sale_order_line_id.analytic_distribution_ids if l.type != 'garbage'])
                total = total_price - total_amount
            else:
                total = compute_amount(self.type, self.value, total_price)
        
        elif self.analytic_purchase_order_line_id:
            company_rs = self.analytic_purchase_order_line_id.purchase_order_id.company_id
            currency_rs = self.analytic_purchase_order_line_id.currency_id    
            total_price = self.analytic_purchase_order_line_id.total_price
            if self.type == 'garbage':
                total_amount = sum([compute_amount(l.type, l.value, total_price) for l in self.analytic_purchase_order_line_id.analytic_distribution_ids if l.type != 'garbage'])
                total = total_price - total_amount
            else:
                total = compute_amount(self.type, self.value, total_price)
            
        elif self.analytic_mo_id:
            company_rs = False
            currency_rs = False    
            total_price = 0.0
            if self.analytic_mo_id.type_compute_analytic_prod == 'real':
                total_price = self.analytic_mo_id.real_total_cost
            else:
                total_price = self.analytic_mo_id.theo_total_cost
                
            if self.type == 'garbage':
                total_amount = sum([compute_amount(l.type, l.value, total_price) 
                                    for l in self.analytic_mo_id.analytic_distribution_ids if l.type != 'garbage'])
                total = total_price - total_amount
            else:
                total = compute_amount(self.type, self.value, total_price)
        
        self.total = total
        if not company_rs:
            company_rs = self.env.user.company_id
            
        company_currency_rs = company_rs and company_rs.currency_id or False
        if company_currency_rs and currency_rs and company_currency_rs != currency_rs:
            context2 = {'date': fields.Date.today()}
            context2.update(self.env.context)
            total_currency = currency_rs.with_context(context2).compute(total, company_currency_rs)
        else:
            total_currency = total
            
        self.total_currency = total_currency
                
                
    #===========================================================================
    # COLUMNS
    #===========================================================================
    analytic_sale_order_line_id = fields.Many2one('sale.order.line', string='Sale order line', required=False, ondelete='set null')
    analytic_purchase_order_line_id = fields.Many2one('purchase.order.line', string='Purchase order line', required=False, ondelete='set null')
    invoice_line_id = fields.Many2one('account.invoice.line', string='Invoice line', required=False, ondelete='set null')
    analytic_mo_id = fields.Many2one('mrp.manufacturingorder', string='MO', required=False, ondelete='set null')
    company_id = fields.Many2one('res.company', string='Company', required=False, ondelete='restrict')
    type = fields.Selection('_type_get', string='Type', default='percentage')
    value = fields.Float(string='Value', default=0.0, required=False)
    account_id = fields.Many2one('account.analytic.account', string='Account', required=True, ondelete='restrict')
    total = fields.Float(string='Total', default=0.0, required=False, compute='_compute_total_analytic_distribution', store=True)
    total_currency = fields.Float(string='Total (in company currency)', default=0.0, required=False, compute='_compute_total_analytic_distribution', store=True)



class account_analytic_line(models.Model):
    _inherit = 'account.analytic.line'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    invoice_line_id = fields.Many2one('account.invoice.line', string='Invoice line', required=False, ondelete='restrict')
    invoice_line_account_id = fields.Many2one('account.account', string='Invoice line account', related='invoice_line_id.account_id', store=True, readonly=True)
    price_unit = fields.Float(string='Price unit', default=0.0, required=False)
    amount_invoice = fields.Float(string='Amount (from the invoice)', default=0.0, required=False)
    timetracking_id = fields.Many2one('resource.timetracking', string='Timetracking', required=False, ondelete='restrict')
    mo_id = fields.Many2one('mrp.manufacturingorder', string='MO', required=False, ondelete='restrict')



class account_analytic_account(models.Model):
    _inherit = 'account.analytic.account'
    
    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.search(['|', ('code', operator, name), ('name', operator, name)] + args, limit=limit)
        return recs.name_get()
    
    