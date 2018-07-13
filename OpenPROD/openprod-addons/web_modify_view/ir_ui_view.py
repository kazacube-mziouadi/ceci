# coding: utf-8

from openerp import models, fields, api

class ir_ui_view(models.Model):
    _inherit = 'ir.ui.view'
    
    is_override = fields.Boolean(string='Is override', default=False)
    
    @api.model
    def search(self, args=None, offset=0, limit=None, order=None, count=False):
        res = super(ir_ui_view, self).search(args, offset=offset, limit=limit, order=order, count=count)
        
        if self.env.context.get('search_override') and len(res.ids):
            self.env.cr.execute(
                '''select distinct(view_id)
                from res_groups_users_rel res
                join ir_ui_view_group_rel view
                on res.gid = view.group_id
                where uid=%s
                and view.view_id in %s''',
                (self.env.uid, tuple(res.ids)))
            view_ids = [x[0] for x in self.env.cr.fetchall()]
            return self.browse(view_ids)
            
        return res