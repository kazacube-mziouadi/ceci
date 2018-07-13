# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import except_orm
from openerp.addons.base_openprod.common import get_form_view
from openerp.osv import fields as f

class copy_access_user(models.Model):
    """ 
        Wizard copy access user
    """
    _name = 'copy.access.user'
    _description = 'Wizard copy access user'
    _rec_name = 'original_user_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    user_ids = fields.Many2many('res.users', 'copy_access_user_res_users_rel', 'wiz_id', 'user_id', string='Users')
    original_user_id = fields.Many2one('res.users', string='Original user', required=True, ondelete='cascade')
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(copy_access_user, self).default_get(fields_list=fields_list)
        #Fonction permettant de passer par défaut l'id de l'OT ouvert
        vals = {
            'user_ids': self._context.get('active_ids'),
        }
        
        res.update(vals)
        return res
    
    
    @api.multi
    def validate(self):
        user_obj = self.env['res.users']
        for wiz in self:
            group_ids = [u.id for u in wiz.original_user_id.groups_id]
            admin_id = user_obj.search([('login', '=', 'admin')])
            if admin_id and len(admin_id) == 1:
                admin_id = admin_id[0]
            else:
                raise except_orm(_('Error'), _('Unable to find a user with login=\'admin\''))
    
            vals = {'groups_id': [(6, 0, group_ids)]}
            wiz.user_ids.write(vals)

        return {'type': 'ir.actions.act_window_close'}

    