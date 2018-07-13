# -*- coding: utf-8 -*-
from openerp import models, api, fields
from openerp.exceptions import ValidationError
from openerp.tools.translate import _
from decimal import Decimal

class purchase_order_line(models.Model):
    _inherit = 'purchase.order.line'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    analytic_distribution_ids = fields.One2many('purchase.sale.analytic.distribution', 'analytic_purchase_order_line_id',  
                                                string='Analytic distribution', copy=True)
    
    
    @api.onchange('product_id', 'property_ids')
    def _onchange_product_id(self):
        """
            Surcharge du onchange du produit afin d'ajouter les lignes de distribution analytique
        """
        res = super(purchase_order_line, self)._onchange_product_id()
        if self.product_id and self.product_id.purchase_pad_id:
            pad = self.product_id.purchase_pad_id
            list_line = []
            for line in pad.distribution_ids:
                vals = {
                        'company_id': pad.company_id.id,
                        'type': line.type,
                        'value': line.value,
                        'account_id': line.account_id.id,
                        }
                list_line.append((0, 0, vals))
            
            self.analytic_distribution_ids = list_line
        else:
            self.analytic_distribution_ids = []
        
        return res
    
    
    def create_purchase_order_line(self, purchase=False, product=None, values=None, first_qty=False, forced_qty=False, not_need_qty=False):
        """
            Surcharge de la méthode de création des lignes d'achat afin de prendre
            en compte la distribution analytique
        """
        res = super(purchase_order_line, self).create_purchase_order_line(purchase=purchase, product=product, 
                                                                          values=values, first_qty=first_qty, 
                                                                          forced_qty=forced_qty, not_need_qty=not_need_qty)
        if not 'analytic_distribution_ids' in values:
            if res.product_id and res.product_id.purchase_pad_id:
                pad = res.product_id.purchase_pad_id
                list_line = []
                for line in pad.distribution_ids:
                    vals = {
                            'analytic_purchase_order_line_id': res.id,
                            'company_id': pad.company_id.id,
                            'type': line.type,
                            'value': line.value,
                            'account_id': line.account_id.id,
                            }
                    list_line.append([0, False, vals])
                
                res.write({'analytic_distribution_ids': list_line})
        
        return res



class purchase_order(models.Model):
    _inherit = 'purchase.order'
    
    @api.multi
    def action_progress_purchase(self):
        """
            Surcharge de la fonction de validation de l'achat afin de vérifier 
            le montant analytique total avec le montant HT de l'achat dans 
            le cas où on a coché la case check_analytic_total dans la configuration 
        """
        res = super(purchase_order, self).action_progress_purchase()
        check_analytic_total = self.env['purchase.config.settings'].get_param('check_analytic_total')
        if check_analytic_total:
            for purchase in self:
                check_analytic_amount = 0
                for line in purchase.purchase_order_line_ids:
                    if line.analytic_distribution_ids:
                        for distribution_line in line.analytic_distribution_ids:
                            check_analytic_amount += distribution_line.total
                            
                if Decimal(str(check_analytic_amount)) != Decimal(str(purchase.amount_ex_taxes)):
                    raise ValidationError(_('The amount of the analytic lines are not equal to the total without taxes of the purchase %s')%(purchase.name))
            
        return res
    
    
