# -*- coding: utf-8 -*-
from openerp import models, api, fields
from openerp.exceptions import except_orm, ValidationError


class mrp_change_resource_wo(models.TransientModel):
    """ 
        Wizard qui permet de changer les ressources dans les wo 
    """
    _name = 'mrp.change.resource.wo'
    _description = 'Wizard qui permet de changer les ressources dans les wo'
    _rec_name = 'wo_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wo_id = fields.Many2one('mrp.workorder', string='WO', required=False, ondelete='cascade')
    resource_category_id = fields.Many2one('mrp.resource.category', string='Resource Category', required=False, ondelete='cascade')
    wo_resource_id = fields.Many2one('mrp.wo.resource', string='WO Resource', required=False, ondelete='cascade')
    resource_id = fields.Many2one('mrp.resource', string='Resource', required=True, ondelete='cascade')
    rl_resource_category_id = fields.Many2one('mrp.rl.resource.category', string='RL Resource Category', required=False, ondelete='cascade')
    
    @api.model
    def default_get(self, fields_list):
        res = super(mrp_change_resource_wo, self).default_get(fields_list=fields_list)
        if self.env.context.get('active_model', '') == 'mrp.workorder':
            wo = self.env['mrp.workorder'].browse(self.env.context.get('active_id'))
            wo_resource = wo.wo_resource_ids and wo.wo_resource_ids[0] or False
        else:
            wo_resource = self.env['mrp.wo.resource'].browse(self.env.context.get('active_id'))
            
        if wo_resource:
            vals = {
                'wo_resource_id': wo_resource.id,
                'resource_id': wo_resource.resource_id.id,
                'resource_category_id': wo_resource.resource_category_id.id,
                'wo_id': wo_resource.wo_id.id,
                'rl_resource_category_id': wo_resource.rl_resource_category_id and wo_resource.rl_resource_category_id.id or False
            }
            res.update(vals)
        return res
    
    #===========================================================================
    # Fonctions
    #===========================================================================
    

    @api.multi
    def action_change_res(self):
        """
            Fonction qui récupère le produit et l'UdM dans l'OT
        """
        for wiz in self:
            wiz.wo_id.change_resource(wiz.wo_resource_id, wiz.resource_id, wiz.rl_resource_category_id)
        return {'type': 'ir.actions.client', 'tag': 'reload', } 



class mrp_add_resource_wo(models.TransientModel):
    """ 
        Ajouter une ressource dans le wo 
    """
    _name = 'mrp.add.resource.wo'
    _description = 'Ajouter une ressource dans le wo'
    _rec_name = 'wo_id'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wo_id = fields.Many2one('mrp.workorder', string='WO', required=False, ondelete='cascade')
    resource_category_id = fields.Many2one('mrp.resource.category', string='Resource Category', required=False, ondelete='cascade')
    wo_resource_id = fields.Many2one('mrp.wo.resource', string='WO Resource', required=False, ondelete='cascade')
    resource_id = fields.Many2one('mrp.resource', string='Resource', required=True, ondelete='cascade')
    rl_resource_category_id = fields.Many2one('mrp.rl.resource.category', string='RL Resource Category', required=False, ondelete='cascade')
    spreading_routing = fields.Boolean(string='Routing', default=True)
    
    @api.model
    def default_get(self, fields_list):
        res = super(mrp_add_resource_wo, self).default_get(fields_list=fields_list)
        wo_resource_obj = self.env['mrp.wo.resource']
        wo_resource = wo_resource_obj.browse(self._context.get('active_id'))
        if wo_resource:
            vals = {
                'wo_resource_id': wo_resource.id,
                'resource_id': wo_resource.resource_id.id,
                'resource_category_id': wo_resource.resource_category_id.id,
                'wo_id': wo_resource.wo_id.id,
                'rl_resource_category_id': wo_resource.rl_resource_category_id and wo_resource.rl_resource_category_id.id or False
            }
            res.update(vals)
        return res
    
    @api.multi
    def action_add_res(self):
        """
            Bouton de validation
        """
        self.wo_id.change_resource(self.wo_resource_id, self.resource_id, self.rl_resource_category_id, add_resource_rl=self.spreading_routing)
        return True
    


