# -*- coding: utf-8 -*-
from openerp import models, api, fields, _
from openerp.exceptions import except_orm
from openerp.addons.base_openprod.common import get_form_view


class document_openprod(models.Model):
    _inherit = 'document.openprod'
    
    
    def find_routing_ids(self, return_line=False):
        """
            Fonction qui permet de chercher les ids des gammes liées au document
        """
        routing_line_rcs = self.env['mrp.routing.line'].search([('document_ids', 'in', self.id)])
        if return_line:
            return routing_line_rcs.ids
        
        routing_read = routing_line_rcs.read(['routing_id'])
        routing_ids = routing_read and [x['routing_id'][0] for x in routing_read] or []
        return routing_ids
    
    
    @api.multi
    def show_routing_from_document(self):
        """
            Fonction qui cherche et retourne les gammes liées à ce document
        """
        action_struc = {}
        for document in self:
            action_dict = get_form_view(self, 'mrp.action_see_all_routing')
            routing_ids = document.find_routing_ids(return_line=False)
            routing_ids = list(set(routing_ids))
            if action_dict and action_dict.get('id') and action_dict.get('type'):
                action = self.env[action_dict['type']].browse(action_dict['id'])
                action_struc = action.read()
                action_struc[0]['domain'] = [('id', 'in', routing_ids)]
                action_struc = action_struc[0]
              
        return action_struc
    
    
    def update_link_objects(self, new_document_id=False, datas=False):
        """
            On recherche tous les documents de ligne de gamme liés à l'ancienne
            version du document et on remplace par la nouvelle version
        """
        super(document_openprod, self).update_link_objects(new_document_id=new_document_id, datas=datas)
        mrp_document_rcs = False
        if datas and datas.get('routing_ids'):
            mrp_document_rcs = datas['routing_ids']
        else:
            mrp_document_rcs = self.env['mrp.routing.line'].search([('document_ids', 'in', self.id)])
        
        if mrp_document_rcs: 
            mrp_document_rcs.write({'document_ids': [(3, self.id), (4, new_document_id)]})
            
        return True
    
    
    def find_workorder_ids(self):
        """
            Fonction qui permet de chercher les ids des OT liés au document
        """
        wo_ids = self.env['mrp.workorder'].search([('rl_document_ids', 'in', self.id)]).ids
        return wo_ids
    
    
    @api.multi
    def show_wo_from_document(self):
        """
            Fonction qui cherche et retourne les OT liés à ce document
        """
        action_struc = {}
        for document in self:
            action_dict = get_form_view(self, 'mrp.action_see_all_workorder')
            wo_ids = document.find_workorder_ids()
            wo_ids = list(set(wo_ids))
            if action_dict and action_dict.get('id') and action_dict.get('type'):
                action = self.env[action_dict['type']].browse(action_dict['id'])
                action_struc = action.read()
                action_struc[0]['domain'] = [('id', 'in', wo_ids)]
                action_struc = action_struc[0]
              
        return action_struc
    
    
    def find_mo_ids(self):
        """
            Fonction qui permet de chercher les ids des OF liés au document
        """
        mo_ids = self.env['mrp.manufacturingorder'].search([('internal_plan_ids', 'in', self.id)]).ids
        return mo_ids
    
    
    @api.multi
    def show_mo_from_document(self):
        """
            Fonction qui cherche et retourne les OF liés à ce document
        """
        action_struc = {}
        for document in self:
            action_dict = get_form_view(self, 'mrp.action_see_all_mo')
            mo_ids = document.find_mo_ids()
            mo_ids = list(set(mo_ids))
            if action_dict and action_dict.get('id') and action_dict.get('type'):
                action = self.env[action_dict['type']].browse(action_dict['id'])
                action_struc = action.read()
                action_struc[0]['domain'] = [('id', 'in', mo_ids)]
                action_struc = action_struc[0]
              
        return action_struc


    def find_product_search_args(self):
        search_args = [('pdf_file', '=', self.id), ('type', 'in', ('pdf_receipt', 'pdf_delivery', 'pdf_production'))]
        return search_args
    
    
