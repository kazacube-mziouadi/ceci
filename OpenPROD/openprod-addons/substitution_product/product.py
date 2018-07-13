# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
import string
import datetime
from datetime import timedelta
from openerp.addons.base_openprod.common import get_form_view
from openerp.addons.base_openprod.common import roundingUp, rounding
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
import re



class product_product(models.Model):
    """ 
        description 
    """
    _inherit = 'product.product'
    
    @api.one
    def _compute_substitution_product_used_ids(self):
        """
            Calcul des produits de substitions déjà utilisés
        """
        substitution_product_use_ids = []
        bom_rcs = self.env['mrp.bom'].search([('bom_id', '!=', False), ('product_id', '=', self.id), ('substitution_product_ids', '!=', False), ('state', '!=', 'obsolete')])
        if bom_rcs:
            for bom in bom_rcs:
                substitution_product_ids = bom.return_substitution_product_ids()
                substitution_product_use_ids.extend(substitution_product_ids)
            
            if substitution_product_use_ids:
                substitution_product_use_ids = list(set(substitution_product_use_ids))
        
        self.substitution_product_used_ids = substitution_product_use_ids
    
    
    @api.one
    def _compute_substituent_ids(self):
        """
            Calcul de la liste des produits dans lequel il est utilisé comme produit de substitution
        """
        if isinstance(self.id, models.NewId):
            self.substituent_ids = []
            return
        substituent_ids = []
        product_query = """ select 
                                product_id 
                            from 
                                mrp_bom 
                            where 
                                id in ( select 
                                            bom_id 
                                        from 
                                            substitution_product_bom 
                                        where 
                                            product_id = %s) and
                                state != 'obsolete'
                            group by product_id"""
                
        self.env.cr.execute(product_query, (self.id,))
        res = self.env.cr.fetchall()
        if res:
            substituent_ids = [x[0] for x in res]
        
        self.substituent_ids = substituent_ids
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    substituent_ids = fields.One2many('product.product', compute='_compute_substituent_ids',  string='Substituent')
    substitution_product_used_ids = fields.One2many('product.product', compute='_compute_substitution_product_used_ids',  string='Substitution product already used for the product')
    
    
    def additional_function_domain(self, arg):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de product_product
        """
        arg0, arg1, arg_1 = super(product_product, self).additional_function_domain(arg)
        if arg[0] == 'domain_substituion_product':
            arg0 = 'id'
            arg1 = 'in'
            product_ids = []
            if arg[-1]:
                component = self.env['mrp.bom'].browse(arg[-1][0])
                product_ids = component.return_substitution_product_ids()
                if component.product_id.id != arg[-1][-1]:
                    product_ids.append(component.product_id.id)

                if arg[-1][-1] in product_ids:
                    product_ids.remove(arg[-1][-1])
                    
            arg_1 = product_ids
                
        return arg0, arg1, arg_1
    
    
    @api.multi
    def add_product_substitution_component(self):
        spb_obj = self.env['substitution.product.bom']
        for product in self:
            if self.env.context.get('bom_id', False):
                prepa_create_product_substitution_component = spb_obj.prepa_create_product_substitution_component(product.id, self.env.context.get('bom_id', False))
                spb_obj.create(prepa_create_product_substitution_component)
        
        return {'type':'ir.actions.act_window_view_reload'}
    
        