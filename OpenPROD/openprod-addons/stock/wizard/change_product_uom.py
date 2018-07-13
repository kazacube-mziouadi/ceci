# coding: utf-8
from openerp import models, fields

class change_product_uom(models.TransientModel):
    _inherit = 'change.product.uom'
    
    copy_orderpoint = fields.Boolean(string='Copy stock rules', default=True)
    copy_attributes = fields.Boolean(string='Copy attributes', default=True)
    copy_plan = fields.Boolean(string='Copy printed documents', default=True)
    
    def copy_from_product(self, product, new_product_id):
        """
            Surcharge de la fonction afin de prendre en compte la copie éventuelle du référencement
            fournisseur, client, des contrôles et plans et des règles de stock
        """
        res = super(change_product_uom, self).copy_from_product(product=product, 
                                                                     new_product_id=new_product_id)
        default = {'product_id': new_product_id}
        
        #Copie des documents imprimés
        if self.copy_plan and not product.printed_doc_categ_syncro:
            product.plan_control_ids.copy(default)
        
        #Copie des règles de stock
        if self.copy_orderpoint:
            product.orderpoint_ids.copy(default)
            
        #Copie des attributes
        if self.copy_attributes:
            product.common_attribute_ids.copy(default)
            
        return res