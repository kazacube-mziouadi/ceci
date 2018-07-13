# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _

class wizard_create_timetracking(models.TransientModel):
    _inherit = 'wizard.create.timetracking'
    
    @api.model
    def _target_type_get(self):
        """
            Ajout de l'intervention dans le champ sélection
        """
        res = super(wizard_create_timetracking, self)._target_type_get()
        res.append(('intervention', _('Intervention')))
        return res
    
    
    def compute_search_args(self):
        """
            Si le temps est enregistré pour une intervention, on recherche les derniers temps de cette
            ressource sur les interventions
        """
        search_args = super(wizard_create_timetracking, self).compute_search_args()
        if self.target_type == 'intervention':
            search_args = [('intervention_id', '!=', False)]
            
        return search_args
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    intervention_id = fields.Many2one('intervention', string='Intervention', required=False, ondelete='set null')
    
    
    @api.model
    def default_get(self, fields_list):
        """
            Surcharge du default_get pour calculer le domaine du M2M sibling_ids
        """
        res = super(wizard_create_timetracking, self).default_get(fields_list=fields_list)
        if self.env.context.get('active_model') == 'intervention':
            res['target_type'] = 'intervention'
            
        return res
    
    
    def extend_sibling_domain(self, target_model, target_id):
        """
            Prise en compte de l'intervention pour la recherche de lignes de temps parentes
        """
        new_domain = super(wizard_create_timetracking, self).extend_sibling_domain(target_model, target_id)
        if target_model == 'intervention':
            new_domain = ('intervention_id', '=', int(target_id))
            
        return new_domain
    
    
    def find_target(self, target_type):
        """
            Prise en compte de l'intervention pour la recherche de lignes de temps parentes
        """
        target_id, target_model = super(wizard_create_timetracking, self).find_target(target_type)
        if target_type == 'intervention':
            target_id = self.intervention_id.id
            target_model = 'intervention'
                
        return target_id, target_model
    
    
    def update_create_vals(self, vals_all):
        """
            Prise en compte de l'intervention pour la création de la ligne de temps
        """
        vals = super(wizard_create_timetracking, self).update_create_vals(vals_all)
        if self.target_type == 'intervention' and self.intervention_id:
            vals['intervention_id'] = self.intervention_id.id
        
        elif self.target_type == 'wo' and self.wo_id and self.wo_id.intervention_id:
            vals['intervention_id'] = self.wo_id.intervention_id.id
            
        return vals
    
    
    @api.onchange('resource_id' ,'intervention_id')
    def _onchange_intervention_id(self):
        """
            Au changement de l'intervention, de l'action ou de la ressource, on récupère leur nom pour les inscrire dans le champs "name"
        """
        super(wizard_create_timetracking, self)._onchange_resource_id()
        if self.target_type == 'intervention':
            if self.intervention_id and self.resource_id:
                self.name = '%s - %s - %s'%(self.resource_id.name, self.intervention_id.name, fields.Datetime.now())
    