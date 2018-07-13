# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.addons.base_openprod.common import get_form_view

class note_openprod(models.Model):
    _inherit = 'note.openprod'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    maintenance_contract_id = fields.Many2one('maintenance.contract', string='Maintenance contract', required=False, ondelete='cascade')



class document_openprod(models.Model):
    _inherit = 'document.openprod'
    
    
    def find_maintenance_contract_ids(self):
        """
            Fonction qui permet de chercher les ids des affaires liées au document
        """
        #On récupère les ids des enregistrements d'affaires liés à ce document
        maintenance_contract_ids = self.env['maintenance.contract'].search([('document_ids', 'in', self.id)]).ids
        return maintenance_contract_ids
    
    
    @api.multi
    def show_maintenance_contract_from_document(self):
        """
            Fonction qui cherche et retourne les affaires liées à ce document
        """
        action_struc = {}
        for document in self:
            action_dict = get_form_view(self, 'maintenance_contract.action_see_all_maintenance_contract')
            maintenance_contract_ids = document.find_maintenance_contract_ids()
            maintenance_contract_ids = list(set(maintenance_contract_ids))
            if action_dict and action_dict.get('id') and action_dict.get('type'):
                action = self.env[action_dict['type']].browse(action_dict['id'])
                action_struc = action.read()
                action_struc[0]['domain'] = [('id', 'in', maintenance_contract_ids)]
                action_struc = action_struc[0]
              
        return action_struc