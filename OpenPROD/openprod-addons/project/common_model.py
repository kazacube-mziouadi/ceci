# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.addons.base_openprod.common import get_form_view

class document_openprod(models.Model):
    _inherit = 'document.openprod'
    
    
    def find_project_ids(self):
        """
            Fonction qui permet de chercher les ids des projets liés au document
        """
        #On récupère les ids des enregistrements des projets liés à ce document
        project_ids = self.env['project.phase'].search([('phase_document_ids', 'in', self.id)]).ids
        return project_ids
    
    
    @api.multi
    def show_project_from_document(self):
        """
            Fonction qui cherche et retourne les projets liés à ce document
        """
        action_struc = {}
        for document in self:
            action_dict = get_form_view(self, 'project.act_project_phase')
            project_ids = document.find_project_ids()
            project_ids = list(set(project_ids))
            if action_dict and action_dict.get('id') and action_dict.get('type'):
                action = self.env[action_dict['type']].browse(action_dict['id'])
                action_struc = action.read()
                action_struc[0]['domain'] = [('id', 'in', project_ids)]
                action_struc = action_struc[0]
              
        return action_struc