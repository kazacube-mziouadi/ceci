# -*- coding: utf-8 -*-
from openerp import models, fields, api, tools, _

class wizard_create_timetracking(models.TransientModel):
    _inherit = 'wizard.create.timetracking'
    
    @api.model
    def _target_type_get(self):
        """
            Ajout du workorder dans le champ sélection
        """
        res = super(wizard_create_timetracking, self)._target_type_get()
        res.append(('wo', _('Workorder')))
        return res
    
    
    def compute_search_args(self):
        """
            Si le temps est enregistré pour un workorder, on recherche les derniers temps de cette
            ressource sur les wo
        """
        search_args = super(wizard_create_timetracking, self).compute_search_args()
        if self.target_type == 'wo':
            search_args = [('wo_id', '!=', False)]
            
        return search_args
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wo_id = fields.Many2one('mrp.workorder', string='WO', required=False, ondelete='set null')
    wo_group_ids = fields.Many2many('mrp.workorder', 'wizard_create_timetracking_wo_rel', 'wiz_id', 'wo_id', string='List WOs' )
    group_wo_id = fields.Many2one('mrp.group.wo', 'Group wo')
    
    def extend_sibling_domain(self, target_model, target_id):
        """
            Prise en compte du wo pour la recherche de lignes de temps parentes
        """
        new_domain = super(wizard_create_timetracking, self).extend_sibling_domain(target_model, target_id)
        if target_model == 'mrp.workorder':
            new_domain = ('wo_id', '=', int(target_id))
            
        return new_domain
    
    
    def find_target(self, target_type):
        """
            Prise en compte du wo pour la recherche de lignes de temps parentes
        """
        target_id, target_model = super(wizard_create_timetracking, self).find_target(target_type)
        if target_type == 'wo':
            target_id = self.wo_id.id
            target_model = 'mrp.workorder'
                
        return target_id, target_model
    
    
    def find_target_inverse(self, target_model):
        """
            Fonction qui retourne le target_type en fonction du modèle
            du type de saisie
        """
        if target_model == 'mrp.workorder':
            return 'wo'
                
        return super(wizard_create_timetracking, self).find_target_inverse(target_model)
    
    
    def update_create_vals(self, vals_all):
        """
            Prise en compte du wo pour la création de la ligne de temps
        """
        vals = super(wizard_create_timetracking, self).update_create_vals(vals_all)
        if self.target_type == 'wo' and self.wo_id:
            vals['wo_id'] = self.wo_id.id
            vals['time_spent'] = vals_all['time']
            if self.wo_group_ids:
                time_total_theo = self.wo_id.total_time_theo
                for wo in self.wo_group_ids:
                    time_total_theo += wo.total_time_theo
                
                time_spent = time_total_theo and vals_all['time'] * self.wo_id.total_time_theo / time_total_theo or 0
                vals['time_spent'] = time_spent
                vals['group_wo_id'] = self.group_wo_id and self.group_wo_id.id or False
                if self.resource_id == self.wo_id.first_resource_id:
                    vals['is_first_resource'] = True
                    
                timetracking_obj = self.env['resource.timetracking']
                for wo in self.wo_group_ids:
                    vals_temp = vals_all.copy()
                    time_spent = time_total_theo and vals_all['time'] * wo.total_time_theo / time_total_theo or 0
                    vals_temp['time_spent'] = time_spent
                    vals_temp['wo_id'] = wo.id
                    vals_temp['name'] = '%s - %s - %s'%(self.resource_id.name, wo.name, fields.Datetime.now())
                    vals_temp['group_wo_id'] = self.group_wo_id and self.group_wo_id.id or False
                    if self.resource_id == wo.first_resource_id:
                        vals_temp['is_first_resource'] = True
                        
                    timetracking_obj.create(vals_temp)
            
        return vals
    
    
    @api.onchange('resource_id' ,'action_id', 'wo_id')
    def _onchange_resource_id(self):
        """
            Au changement du wo, de l'action ou de la ressource, on récupère leur nom pour les inscrire dans le champs "name"
        """
        super(wizard_create_timetracking, self)._onchange_resource_id()
        if self.target_type == 'wo':
            if self.wo_id and self.resource_id:
                self.name = '%s - %s - %s'%(self.resource_id.name, self.wo_id.name, fields.Datetime.now())
                
            if self.wo_id and self.wo_id.group_wo_id and self.wo_id.group_wo_id.wo_ids and len(self.wo_id.group_wo_id.wo_ids.ids) > 1 and self.wo_id.id in self.wo_id.group_wo_id.wo_ids.ids:
                self.wo_group_ids = [(6, 0, list(set(self.wo_id.group_wo_id.wo_ids.ids) - set(self.wo_id.ids)))]
                self.group_wo_id = self.wo_id.group_wo_id.id
                
    