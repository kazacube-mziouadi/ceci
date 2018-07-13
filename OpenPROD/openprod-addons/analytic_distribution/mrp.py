# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
from compute_amount import compute_amount
from decimal import Decimal


class mrp_manufacturingorder(models.Model):
    """ 
        Manufacturing order 
    """
    _inherit = 'mrp.manufacturingorder'
    
    
    @api.model
    def _type_compute_analytic_prod_get(self):
        return [
                ('theoretical', _('Theoretical')),
                ('real', _('Real')),
                       ]


    #===========================================================================
    # COLUMNS
    #===========================================================================
    type_compute_analytic_prod = fields.Selection('_type_compute_analytic_prod_get', string='Type compute', default='theoretical')
    analytic_distribution_ids = fields.One2many('purchase.sale.analytic.distribution', 'analytic_mo_id',  
                                                string='Analytic distribution', copy=True)
    analytic_line_ids = fields.One2many('account.analytic.line', 'mo_id',  
                                                string='Analytic lines', copy=False)


    def onchange_product_id(self, product, option_ids):
        """
            Au changement du produit, changement l'uom
        """
        res = super(mrp_manufacturingorder, self).onchange_product_id(product, option_ids)
        if product and product.prod_pad_id:
            pad = product.prod_pad_id
            list_line = []
            for line in pad.distribution_ids:
                vals = {
                        'company_id': pad.company_id.id,
                        'type': line.type,
                        'value': line.value,
                        'account_id': line.account_id.id,
                        }
                list_line.append([0, False, vals])
            
            res['analytic_distribution_ids'] = list_line
        else:
            res['analytic_distribution_ids'] = []
        
        return res
    
    
    
    @api.onchange('product_id', 'option_ids')
    def _onchange_product_id(self):
        res = super(mrp_manufacturingorder, self)._onchange_product_id()
        res_onchange = self.onchange_product_id(self.product_id,  self.option_ids)
        self.analytic_distribution_ids = res_onchange['analytic_distribution_ids'] or []
        return res
    
    
    def vals_distribution_analytique(self, res_onchange_product):
        """
            Point d'entrée si le produit à de la distribution analytique
        """
        if 'analytic_distribution_ids' in res_onchange_product and res_onchange_product['analytic_distribution_ids']:
            return {'analytic_distribution_ids': res_onchange_product['analytic_distribution_ids']}
        
        return False
    
    
    @api.multi
    def create_analytic_journal_items(self):
        """
            Permet de faire les écritures analytiques des coût de l'OF
        """
        for mo in self:
            if mo.analytic_distribution_ids:
                analytic_line_obj = self.env['account.analytic.line']
                config_obj = self.env['stock.config.settings']
                user_id = self.env.user.id
                if mo.product_id.property_account_expense_id:
                    account_id = mo.product_id.property_account_expense_id.id
                else:
                    raise except_orm(_('Error'), _('Please fill in the expense account field in the product sheet (%s)')%(mo.product_id.name))
                
                prod_anal_journal_id = config_obj.get_param('prod_anal_journal_id') or False
                rm_anal_journal_id = config_obj.get_param('rm_anal_journal_id') or False
                sub_anal_journal_id = config_obj.get_param('sub_anal_journal_id') or False
                if not prod_anal_journal_id or not rm_anal_journal_id or not sub_anal_journal_id:
                    raise except_orm(_('Error'), _('Please fill in the basic parameters the analytical journal of production, raw materials and subcontracting'))
                
                check_analytic_amount = 0
                name_prod = _('Produce cost %s')%(mo.name)
                name_rm = _('Raw material cost %s')%(mo.name)
                name_sub = _('Subcontracting cost %s')%(mo.name)
                if mo.type_compute_analytic_prod == 'real':
                    journal_dico = {prod_anal_journal_id: [mo.real_produce_cost, name_prod],rm_anal_journal_id: [mo.real_rm_cost, name_rm],sub_anal_journal_id: [mo.real_subcontracting_cost, name_sub]}
                    uoi_qty = mo.produce_total_qty
                    uoi_id = mo.uom_id.id
                else:
                    journal_dico = {prod_anal_journal_id: [mo.theo_produce_cost, name_prod],rm_anal_journal_id: [mo.theo_rm_cost, name_rm],sub_anal_journal_id: [mo.theo_subcontracting_cost, name_sub]}
                    uoi_qty = mo.quantity
                    uoi_id = mo.uom_id.id
                
                if mo.analytic_distribution_ids and uoi_qty:
                    analytic_line_rcs = analytic_line_obj.search([('mo_id', '=', mo.id)])
                    if analytic_line_rcs:
                        analytic_line_rcs.unlink()
                        
                    for journal_id, vals in journal_dico.iteritems():
                        total = vals[0]
                        name = vals[1]
                        if total:
                            for distribution_line in mo.analytic_distribution_ids:
                                if distribution_line.type == 'garbage':
                                    garbage_amount = sum([compute_amount(l.type, l.value, total) 
                                                        for l in mo.analytic_distribution_ids if l.type != 'garbage'])
                                    amount = total - garbage_amount
                                else:
                                    amount = compute_amount(distribution_line.type, distribution_line.value, total)
                                    
                                check_analytic_amount += amount
                                vals = {
                                        'name': name,
                                        'ref': mo.name,
                                        'account_id': distribution_line.account_id.id,
                                        'user_id': user_id,
                                        'amount': amount,
                                        'product_id': mo.product_id.id,
                                        'unit_amount': uoi_qty,
                                        'product_uom_id': uoi_id,
                                        'general_account_id': account_id,
                                        'mo_id': mo.id,
                                        'price_unit': total/uoi_qty,
                                        'journal_id': journal_id[0]
                                        }
                                analytic_line_obj.create(vals)
                        
                            if Decimal(str(check_analytic_amount)) != Decimal(str(total)):
                                if mo.company_id.check_analytic_amount:
                                    raise except_orm(_('Error'), _('The amount of the analytic lines are not equal to the total of the manufacturing order'))
            
        return True
    

    @api.multi
    def write(self, vals=None):
        """
        """
        is_create_analytic = False
        if vals and 'state' in vals and vals['state'] == 'done':
            is_create_analytic = True
            
        res = super(mrp_manufacturingorder, self).write(vals=vals)
        if is_create_analytic:
            self.create_analytic_journal_items()
        
        return res
        