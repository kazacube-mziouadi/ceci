# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import except_orm
from openerp.addons.base_openprod.common import get_form_view

class message_wizard(models.TransientModel):
    """ 
        Message wizard
    """
    _name = 'message.wizard'
    _description = 'Message wizard'
    _rec_name = 'name'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Name', size=256)
    
    def create_message(self, msg='', target='new'):
        """
            Fonction qui permet de créer le message et de le retourner
        """
        mess_id = self.create({'name': msg})
        return {
                'name': _('Message wizard'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'message.wizard',
                'type': 'ir.actions.act_window',
                'res_id': mess_id.id,
                'target': target,
                'nodestroy': True,
                }
    