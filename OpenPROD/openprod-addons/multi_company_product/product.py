# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, ValidationError, UserError


class product_product(models.Model):
    _inherit = "product.product"
    
    @api.one
    def _compute_supply_method(self):
        supply_method = 'buy'        
        mcpsm_rcs = self.env['multi.company.product.supply.method'].search([('company_id', '=', self.env.user.company_id.id), ('product_id', '=', self.id)], limit=1)
        if mcpsm_rcs:
            supply_method = mcpsm_rcs.supply_method
            
        self.supply_method = supply_method
    
    
    def _supply_method_get(self):
        return [
            ('buy', _('Buy')),
            ('produce', _('Produce')),
        ]
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    supply_method = fields.Selection('_supply_method_get', string='Supply method', compute='_compute_supply_method')
    mcpsm_ids = fields.One2many('multi.company.product.supply.method', 'product_id',  string='Supply method')
    
    
    
    @api.multi
    def write(self, vals=None):
        """
            Interdiction de changer de catégorie
        """
                
        res = super(product_product, self).write(vals=vals)
        mcpsm_obj = self.env['multi.company.product.supply.method']
        company = self.env.user.company_id
        for product in self:
            mcpsm_rcs = mcpsm_obj.search([('product_id', '=', product.id), ('company_id', '=', company.id)], limit=1)
            if not mcpsm_rcs:
                raise except_orm(_('Error'), _("You need a default supply method for this company '% s' in this product '%s'."%(company.name, product.code)))
            
        return res
    
    
    
class multi_company_product_supply_method(models.Model):
    """ 
    Multi company product supply method
    """
    _name = 'multi.company.product.supply.method'
    _description = 'Multi company partner supply method'
    _rec_name = 'product_id'
    
    
    def _supply_method_get(self):
        return [
            ('buy', _('Buy')),
            ('produce', _('Produce')),
        ]
        
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    supply_method = fields.Selection('_supply_method_get', string='Supply method', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='Company', required=True, ondelete='restrict')



    
    
    