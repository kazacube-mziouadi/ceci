# -*- coding: utf-8 -*-
from openerp import models, api, fields, _
from openerp.exceptions import except_orm
from openerp.addons.base_openprod.common import get_form_view


class document_openprod(models.Model):
    _inherit = 'document.openprod'
    
    
    def find_partner_ids(self):
        """
            Fonction qui permet de chercher les ids des partenaires liés au document
        """
        partner_ids = self.env['res.partner'].search([('partner_doc_ids', 'in', self.id)]).ids
        return partner_ids
    
    
    @api.multi
    def show_partner_from_document(self):
        """
            Fonction qui cherche et retourne les partenaires liés à ce document
        """
        action_struc = {}
        for document in self:
            action_dict = get_form_view(self, 'partner_openprod.action_see_all_partners')
            partner_ids = document.find_partner_ids()
            partner_ids = list(set(partner_ids))
            if action_dict and action_dict.get('id') and action_dict.get('type'):
                action = self.env[action_dict['type']].browse(action_dict['id'])
                action_struc = action.read()
                action_struc[0]['domain'] = [('id', 'in', partner_ids)]
                action_struc = action_struc[0]
              
        return action_struc
    
    
    def update_link_objects(self, new_document_id=False, datas=False):
        """
            On recherche tous les documents de partenaire liés à l'ancienne version du document
             et on remplace par la nouvelle version
        """
        partner_rcs = False
        super(document_openprod, self).update_link_objects(new_document_id=new_document_id, datas=datas)
        if datas and datas.get('partner_ids'):
            partner_rcs = datas['partner_ids']
        else:
            partner_rcs = self.env['res.partner'].search([('partner_doc_ids', 'in', self.id)])
        
        if partner_rcs:
            partner_rcs.write({'partner_doc_ids': [(3, self.id), (4, new_document_id)]})
            
        return True
    