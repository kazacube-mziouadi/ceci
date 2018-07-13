# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError

class res_users(models.Model):
    _inherit = 'res.users'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    resource_id = fields.Many2one('mrp.resource', string='Resource', required=False, ondelete='restrict')
    
    
    def find_user_calendar(self):
        """
            Fonction permettant de trouver le calendrier lié à la ressource d'un utilisateur
        """
        if self.resource_id:
            calendar = self.resource_id.calendar_id
        else:
            calendar = self.company_id.partner_id and self.company_id.partner_id.calendar_id or False
            
        return calendar
    
    
    def user_has_group(self, g_id, u_id=False):
        """
            Retourne si oui ou non l'utilisateur appartient à un groupe
        """
        self.env.cr.execute("""SELECT 1 FROM res_groups_users_rel WHERE uid=%s AND gid =%s""", (u_id or self.id, g_id))
        return bool(self.env.cr.fetchone())