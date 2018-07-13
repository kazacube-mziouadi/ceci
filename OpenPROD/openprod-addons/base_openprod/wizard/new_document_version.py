# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import except_orm
from openerp.addons.base_openprod.common import get_form_view

class new_document_version_wizard(models.TransientModel):
    """ 
        Wizard for new document version creation
    """
    _name = 'new.document.version.wizard'
    _description = 'Wizard for new document version creation'
    _rec_name = 'version'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    version = fields.Char(string='Version', size=24, required=True)
    
    @api.multi
    def create_new_version(self):
        """
            Fonction permettant d'appeler la fonction de création de la nouvelle
            version et de renvoyer sur la vue de cette version
        """
        context = self.env.context
        if context.get('active_id', False) and self.version:
            document = self.env['document.openprod'].browse(context['active_id'])
            if document:
                new_version_id = document.create_new_version(self.version)
                if new_version_id:
                    action_dict = get_form_view(self, 'base_openprod.document_openprod_see_form')
                    if action_dict and action_dict.get('id') and action_dict.get('type'):
                        action = self.env[action_dict['type']].browse(action_dict['id'])
                        action_struc = action.read()
                        action_struc[0]['res_id'] = new_version_id.id
                        action_struc = action_struc[0]
                          
                    return action_struc
                else:
                    return  {'type': 'ir.actions.act_window_close'}
        else:
            return  {'type': 'ir.actions.act_window_close'}
    