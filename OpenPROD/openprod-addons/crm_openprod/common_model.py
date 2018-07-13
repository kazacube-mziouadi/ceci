# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.addons.base_openprod import utils
from openerp.addons.base_openprod.common import get_form_view
from openerp.tools.translate import _

class note_openprod(models.Model):
    _inherit = 'note.openprod'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    crm_id = fields.Many2one('crm', string='CRM', required=False, ondelete='cascade')



class document_openprod(models.Model):
    _inherit = 'document.openprod'
    
    
    def find_crm_ids(self):
        """
            Fonction qui permet de chercher les ids des enregistrements de CRM liés au document
        """
        #On récupère les ids des enregistrements de CRM liés à ce document
        crm_ids = self.env['crm'].search([('document_ids', 'in', self.id)]).ids
        return crm_ids
    
    
    @api.multi
    def show_crm_from_document(self):
        """
            Fonction qui cherche et retourne les enregistrements de CRM liés à ce document
        """
        action_struc = {}
        for document in self:
            action_dict = get_form_view(self, 'crm_openprod.action_see_all_crm')
            crm_ids = document.find_crm_ids()
            crm_ids = list(set(crm_ids))
            if action_dict and action_dict.get('id') and action_dict.get('type'):
                action = self.env[action_dict['type']].browse(action_dict['id'])
                action_struc = action.read()
                action_struc[0]['domain'] = [('id', 'in', crm_ids)]
                action_struc = action_struc[0]
              
        return action_struc
    