# coding: utf-8
from openerp import models, fields

class change_product_uom(models.TransientModel):
    _inherit = 'change.product.uom'
    
    copy_characteristics = fields.Boolean(string='Copy characteristics', default=True)
    
    def copy_from_product(self, product, new_product_id):
        """
            Surcharge de la fonction afin de prendre en compte la copie éventuelle du référencement
            fournisseur, client, des contrôles et plans et des règles de stock
        """
        res = super(change_product_uom, self).copy_from_product(product=product, 
                                                                     new_product_id=new_product_id)
            
        default = {'product_id': new_product_id}
        #Copie des caractéristiques
        if self.copy_characteristics:
            product.characteristics_ids.copy(default)
            
        return res