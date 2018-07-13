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



class substitution_product_bom(models.Model):
    """ 
        Substitution product bom
    """
    _name = 'substitution.product.bom'
    _description = 'Substitution product bom'
    _rec_name = 'product_id'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    bom_id = fields.Many2one('mrp.bom', string='BoM', required=True, ondelete='cascade')
    
    
    def prepa_create_product_substitution_component(self, product_id, bom_id):
        return {'product_id': product_id, 'bom_id': bom_id}
    


class mrp_bom(models.Model):
    """ 
        MRP BoM  
    """
    _inherit = 'mrp.bom'
    
    
    @api.one
    @api.depends('product_id', 'substitution_product_ids')
    def _compute_substitution_product_used_ids(self):
        """
            Calcul des produits de substitions déjà utilisés
        """
        substitution_product_use_ids = []
        if self.product_id:
            if self.id:
                substitution_product_use_ids = self.function_return_substitution_product_used(self.product_id.id, self.id)
            else:
                if self.substitution_product_ids and isinstance(self.substitution_product_ids[0].id, int):
                    self.env.cr.execute("""select bom_id from substitution_product_bom where id in %s group by bom_id""", (tuple(self.substitution_product_ids.ids,),))
                    res_ids = self.env.cr.fetchall()
                    bom_ids = [x[0] for x in res_ids if x[0]]
                    if bom_ids:
                        substitution_product_use_ids = self.function_return_substitution_product_used(self.product_id.id, bom_ids[0])
                else:
                    substitution_product_use_ids = self.function_return_substitution_product_used(self.product_id.id, 0)
                
        self.substitution_product_used_ids = substitution_product_use_ids
    
    
    @api.one
    def _compute_nb_substitution_product(self):
        """
            Calcul le nombre de produits de substitions
        """
        substitution_product_use_ids = []
        product_ids = [x.id for x in self.substitution_product_ids if not self.product_id or x.id != self.product_id.id]
        self.nb_substitution_product = product_ids and len(product_ids) or 0
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    substitution_product_ids = fields.Many2many('product.product', 'substitution_product_bom', 'bom_id', 'product_id', string='Substitution product')
    substitution_product_used_ids = fields.One2many('product.product', compute='_compute_substitution_product_used_ids', string='Substitution product already used for the product')
    nb_substitution_product = fields.Integer(string='Nb substitution', compute='_compute_nb_substitution_product')
    
    
    @api.multi
    def button_open_choose_substitution_product(self):
        data_pool = self.env['ir.model.data']
        action_model, action_id = data_pool.get_object_reference('substitution_product', 'act_view_component_substitution_product')
        if action_model:
            action_pool = self.env[action_model]
            action = action_pool.browse(action_id).read()[0]
            action['res_id'] = self.id
            action['res_ids'] = self.ids
            action['target'] = 'new'
            res = action
            return res
        
    
    @api.multi
    def action_validate_substitution_product(self):
        return True
    
    
    
    def return_substitution_product_ids(self):
        """
            Fonction qui permet de retourner les produits contenus dans la table substitution_product_bom
        """
        return [x.id for x in self.substitution_product_ids]

    
    def function_return_substitution_product_used(self, product_id, bom_id):
        """"
            Fonction qui permet de calculeer les produits de substitutions déjà utilisés pour le produit sélectionner
        
        """
        query = """
                    select 
                        product_id
                    
                    from 
                        substitution_product_bom
                    
                    where
                        (bom_id in (select 
                                id
                                from 
                                mrp_bom
                                where
                                bom_id is not null AND
                                id != %s AND
                                product_id = %s AND
                                state != 'obsolete' AND
                                (select id from substitution_product_bom where bom_id = id limit 1) is not null) 
                         OR
                    
                         bom_id in (select bom_id from substitution_product_bom where product_id =%s) 
                         
                        ) AND
                        
                    
                        product_id not in (select product_id from substitution_product_bom where bom_id = %s) and
                        product_id != %s
                    
                    Group by
                        product_id
                    
                    
                    UNION
                    
                    (select product_id from mrp_bom where id in (select bom_id from substitution_product_bom where product_id =%s) and product_id != %s and
                        product_id not in (select product_id  from substitution_product_bom where bom_id = %s) Group by product_id)
        
                    """%(bom_id, product_id, product_id, bom_id, product_id, product_id, product_id, bom_id)
        self.env.cr.execute(query)
        res_ids = self.env.cr.fetchall()
        if res_ids:
            substitution_product_use_ids = [x[0] for x in res_ids]
            substitution_product_use_ids = list(set(substitution_product_use_ids))
        else:
            substitution_product_use_ids = []
        
        return substitution_product_use_ids
            
            

