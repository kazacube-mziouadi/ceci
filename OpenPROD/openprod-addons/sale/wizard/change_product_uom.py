# coding: utf-8
from openerp import models, fields

class change_product_uom(models.TransientModel):
    _inherit = 'change.product.uom'
    
    copy_customer_ref = fields.Boolean(string='Copy customer reference', default=True)
    
    def copy_from_product(self, product, new_product_id):
        """
            Surcharge de la fonction afin de prendre en compte la copie éventuelle du référencement
            fournisseur, client, des contrôles et plans et des règles de stock
        """
        res = super(change_product_uom, self).copy_from_product(product=product, 
                                                                     new_product_id=new_product_id)
        default = {'product_id': new_product_id}
        #Copie du référencement client
        if self.copy_customer_ref:
            default2 = default.copy()
            #Si on ne change que la première unité on remplace les unités du référencement
            #client par l'unité saisie 
            if self.change_unit and not self.dual_unit:
                default2.update({'uos_id': self.uom_id.id,
                                'uoi_id': self.uom_id.id})
            #Si on choisi une double unité variable, on remplace les unités du référencement
            #client par la double unité saisie 
            elif self.dual_unit and self.dual_unit_type == 'variable':
                default2.update({'uos_id': self.sec_uom_id.id,
                                'uoi_id': self.sec_uom_id.id})
            
            #On force l'état du référencement client à la copie
            #car mauvaise gestion des sélection avec un default
            for cinfo in product.cinfo_ids:
                default2.update({'state': cinfo.state})
                cinfo.copy(default2)
            
        return res