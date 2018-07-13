# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.addons.base_openprod.common import get_form_view
from openerp.addons.base_openprod import utils
from openerp.tools.translate import _

class note_openprod(models.Model):
    _inherit = 'note.openprod'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    affair_id = fields.Many2one('affair', string='Affair', required=False, ondelete='cascade')



class document_openprod(models.Model):
    _inherit = 'document.openprod'
    
    
    def find_affair_ids(self):
        """
            Fonction qui permet de chercher les ids des affaires liées au document
        """
        affair_ids = []
        #On récupère les ids des enregistrements d'affaires liés à ce document
        affair_ids = self.env['affair'].search([('document_ids', 'in', self.id)]).ids
        return affair_ids
    
    
    @api.multi
    def show_affair_from_document(self):
        """
            Fonction qui cherche et retourne les affaires liées à ce document
        """
        action_struc = {}
        for document in self:
            action_dict = get_form_view(self, 'affair.action_see_all_affair')
            affair_ids = document.find_affair_ids()
            affair_ids = list(set(affair_ids))
            if action_dict and action_dict.get('id') and action_dict.get('type'):
                action = self.env[action_dict['type']].browse(action_dict['id'])
                action_struc = action.read()
                action_struc[0]['domain'] = [('id', 'in', affair_ids)]
                action_struc = action_struc[0]
              
        return action_struc