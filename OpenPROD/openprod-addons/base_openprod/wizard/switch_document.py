# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import except_orm
from openerp.addons.base_openprod.common import get_form_view
from openerp.osv import fields as f

class switch_document_wizard(models.Model):
    """ 
        Wizard to switch the openprod document 
    """
    _name = 'switch.document.wizard'
    _description = 'Wizard to switch the openprod document'
    _rec_name = 'version'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    version = fields.Char(string='Version', size=24, required=True)
    
    
    @api.multi
    def switch_document_version(self):
        """
            Fonction permettant d'appeler la fonction de création d'un nouveau document et
            d'afficher ce nouveau document
        """
        context = self.env.context
        datas = {}
        if context.get('active_id', False) and self.version:
            document = self.env['document.openprod'].browse(context['active_id'])
            if document:
                #On récupère les valeurs des M2M
                for field in self._columns:
                    if isinstance(self._columns[field], f.many2many):
                        datas[field] = self[field]
                
                new_document_id = document.create_new_document(datas, self.version)
                if new_document_id:
                    action_dict = get_form_view(self, 'base_openprod.document_openprod_see_form')
                    if action_dict and action_dict.get('id') and action_dict.get('type'):
                        action = self.env[action_dict['type']].browse(action_dict['id'])
                        action_struc = action.read()
                        action_struc[0]['res_id'] = new_document_id.id
                        action_struc = action_struc[0]
                          
                    return action_struc
                else:
                    return  {'type': 'ir.actions.act_window_close'}
        else:
            return  {'type': 'ir.actions.act_window_close'}
    