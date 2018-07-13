# -*- coding: utf-8 -*-
from openerp import models, api, fields, _
from openerp.exceptions import except_orm
from openerp.addons.base_openprod.common import get_form_view


class document_openprod(models.Model):
    _inherit = 'document.openprod'
    
    
    def find_product_ids(self):
        """
            Fonction qui permet de chercher les ids des produits liés au document
        """
        #On récupère les ids des produits liés à ce document via les plans internes
        product_ids = self.env['product.product'].search([('internal_plan_ids', 'in', self.id)]).ids
        return product_ids
    
    
    @api.multi
    def show_product_from_document(self):
        """
            Fonction qui cherche et retourne les produits liés à ce document
        """
        action_struc = {}
        for document in self:
            action_dict = get_form_view(self, 'product.action_see_all_product')
            product_ids = document.find_product_ids()
            product_ids = list(set(product_ids))
            if action_dict and action_dict.get('id') and action_dict.get('type'):
                action = self.env[action_dict['type']].browse(action_dict['id'])
                action_struc = action.read()
                action_struc[0]['domain'] = [('id', 'in', product_ids)]
                action_struc = action_struc[0]
              
        return action_struc
    
    
    def update_link_objects(self, new_document_id=False, datas=False):
        """
            On recherche tous les plans internes liés à l'ancienne
            version du document et on remplace par la nouvelle version
        """
        product_rcs = False
        super(document_openprod, self).update_link_objects(new_document_id=new_document_id, datas=datas)
        if datas and datas.get('product_ids'):
            product_rcs = datas['product_ids']
        else:
            product_rcs = self.env['product.product'].search([('internal_plan_ids', 'in', self.id)])
        
        if product_rcs:
            product_rcs.write({'internal_plan_ids': [(3, self.id), (4, new_document_id)]})
            
        return True
    