# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _

class sale_order_analysis(models.Model):
    """ 
    Sale analysis module 
    """
    _name = 'sale.order.analysis'
    _description = 'Sale analysis module '
    
    
    @api.one
    @api.depends('date_from', 'date_to', 'family_id', 'salesperson_id')
    def _compute_sales_amounts(self):
        """
            Fonction permettant de calculer le montant des ventes validées, des factures générées,
            et des paiements entre deux dates 
        """
        if self.date_from and self.date_to:
            args_sales = []
            sale_amount = []
            #Prise en compte de la famille de statistique du produit
            if self.family_id:
                args_sales += [('product_id.sale_family_id', '=', self.family_id.id)]
            elif self.salesperson_id:
                args_sales += [('sale_order_id.seller_id', '=', self.salesperson_id.id)]
             
            #On recherche et récupère le montant des ventes validées
            args_sales += [('sale_state', 'not in', ('draft', 'waiting', 'cancel')), 
                           ('sale_order_id.confirmation_date', '>=', self.date_from), 
                           ('sale_order_id.confirmation_date', '<=', self.date_to)]
            sale_amount = self.env['sale.order.line'].search_group(fields=['total_price_currency'], 
                                         without_order=True,
                                         args=args_sales,
                                         sum='total_price_currency',
                                         return_dict=False)
             
            self.sale_amount = sale_amount and sale_amount[0] or 0
        else:
            self.sale_amount = 0
                
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Name', size=128, required=True)
    date_from = fields.Date(string='Date from', required=True)
    date_to = fields.Date(string='Date to', required=True)
    family_id = fields.Many2one('sale.family', string='Product family', required=False, ondelete='restrict')
    forecast = fields.Integer(string='Forecast', default=0, required=False)
    target = fields.Integer(string='Target', default=0, required=False)
    is_active = fields.Boolean(string='Active', default=True)
    color = fields.Integer(string='Color', default=0, required=False)
    sale_amount = fields.Float(string='Validate sale amount', default=0.0, required=False, compute='_compute_sales_amounts')
    salesperson_id = fields.Many2one('res.users', string='Salesperson', required=False, ondelete='restrict')
    
    _sql_constraints = [
        ('search_check', "CHECK((salesperson_id IS NULL AND family_id IS NULL) OR (salesperson_id IS NOT NULL AND family_id IS NULL) OR "
        "(salesperson_id IS NULL AND family_id IS NOT NULL))", "You can't choose a family AND a salesperson for the analyse"),
    ]
    
    @api.one
    def onchange_forecast(self, value):
        """
        """
        return self.write({'forecast': round(float(value))})



class sale_order_invoice_analysis(models.Model):
    """ 
    Invoice analysis for module 
    """
    _name = 'sale.order.invoice.analysis'
    _description = 'Sale invoice analysis module '
     
     
    @api.one
    @api.depends('date_from', 'date_to')
    def _compute_sales_amounts(self):
        """
            Fonction permettant de calculer le montant des factures générées et des paiements entre deux dates 
        """
        payment_amount = 0
        total_invoice_amount = 0
        if self.date_from and self.date_to:
            #On recherche et récupère le montant des factures générées (uniquement les factures non brouillon et
            #non cancel)
            args_invoices = [('invoice_id.state', 'in', ('open', 'paid')), 
                              ('invoice_id.date_invoice', '>=', self.date_from), 
                              ('invoice_id.date_invoice', '<=', self.date_to),
                              ('invoice_id.type', '=', 'out_invoice')]
            invoice_amount_list = self.env['account.invoice.line'].search_group(fields=['total_price_currency'], 
                                         without_order=True,
                                         args=args_invoices,
                                         sum='total_price_currency',
                                         return_dict=False)
            invoice_amount = invoice_amount_list and invoice_amount_list[0] or 0
            #On recherche et récupère le montant des avoirs non brouillon et non cancel générés pour le soustraire au montant
            #des factures
            args_invoices = [('invoice_id.state', 'in', ('open', 'paid')), 
                              ('invoice_id.date_invoice', '>=', self.date_from), 
                              ('invoice_id.date_invoice', '<=', self.date_to),
                              ('invoice_id.type', '=', 'out_refund')]
            refund_amount_list = self.env['account.invoice.line'].search_group(fields=['total_price_currency'], 
                                         without_order=True,
                                         args=args_invoices,
                                         sum='total_price_currency',
                                         return_dict=False)
            refund_amount = refund_amount_list and refund_amount_list[0] or 0
            total_invoice_amount = invoice_amount - refund_amount
            
            #On recherche tous les paiements clients validés de la période
            company_currency = self.company_id.currency_id
            company_currency_id = company_currency.id
            args_payment = [('state', '=', 'posted'), 
                            ('date', '>=', self.date_from), 
                            ('date', '<=', self.date_to),
                            ('type', '=', 'receipt')]
            payment_amount_list = self.env['account.voucher'].search(args_payment)
            for payment in payment_amount_list:
                if payment.currency_id == company_currency_id:
                    payment_amount += payment.amount
                else:
                    from_currency = payment.currency_id
                    payment_amount += from_currency.compute(payment.amount, company_currency)
                    
        self.invoice_amount = total_invoice_amount
        self.payment_amount = payment_amount
                 
     
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Name', size=128, required=True)
    date_from = fields.Date(string='Date from', required=True)
    date_to = fields.Date(string='Date to', required=True)
    forecast = fields.Integer(string='Forecast', default=0, required=False)
    target = fields.Integer(string='Target', default=0, required=False)
    is_active = fields.Boolean(string='Active', default=True)
    color = fields.Integer(string='Color', default=0, required=False)
    invoice_amount = fields.Float(string='Generate invoices amount', default=0.0, required=False, compute='_compute_sales_amounts')
    payment_amount = fields.Float(string='Payment amount', default=0.0, required=False, compute='_compute_sales_amounts')
    company_id = fields.Many2one('res.company', string='Company', required=True, ondelete='restrict', 
                                 default=lambda self: self.env.user.company_id)
     
