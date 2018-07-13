# -*- coding: utf-8 -*-
from openerp import models, fields, api, tools, _

class wizard_create_timetracking(models.TransientModel):
    _inherit = 'wizard.create.timetracking'
    
    @api.model
    def _target_type_get(self):
        """
            Ajout de la phase dans le champ sélection
        """
        res = super(wizard_create_timetracking, self)._target_type_get()
        res.append(('phase', _("Project's phase")))
        return res
    
    
    def compute_search_args(self):
        """
            Si le temps est enregistré pour une phase, on recherche les derniers temps de cette
            ressource sur les phases
        """
        search_args = super(wizard_create_timetracking, self).compute_search_args()
        if self.target_type == 'phase':
            search_args = [('phase_id', '!=', False)]
            
        return search_args
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    phase_id = fields.Many2one('project.phase', string='Phase', required=False, ondelete='set null', domain="[('is_model', '=', False)]")
    
    @api.model
    def default_get(self, fields_list):
        """
            Surcharge du default_get pour calculer le domaine du M2M sibling_ids
        """
        res = super(wizard_create_timetracking, self).default_get(fields_list=fields_list)
        if self.env.context.get('active_model') == 'project.phase':
            res['target_type'] = 'phase'
            
        return res
    
    
    def update_create_vals(self, vals_all):
        """
            Prise en compte de la phase pour la création de la ligne de temps
        """
        vals = super(wizard_create_timetracking, self).update_create_vals(vals_all)
        if self.target_type == 'phase' and self.phase_id:
            vals['phase_id'] = self.phase_id.id
            
        return vals
    
    
    def extend_sibling_domain(self, target_model, target_id):
        """
            Prise en compte de la phase pour la recherche de lignes de temps parentes
        """
        new_domain = super(wizard_create_timetracking, self).extend_sibling_domain(target_model, target_id)
        if target_model == 'project.phase':
            new_domain = ('phase_id', '=', int(target_id))
            
        return new_domain
    
    
    def find_target(self, target_type):
        """
            Prise en compte de la phase pour la recherche de lignes de temps parentes
        """
        target_id, target_model = super(wizard_create_timetracking, self).find_target(target_type)
        if target_type == 'phase':
            target_id = self.phase_id.id
            target_model = 'project.phase'
                
        return target_id, target_model
    
    
    def find_target_inverse(self, target_model):
        """
            Fonction qui retourne le target_type en fonction du modèle
            du type de saisie
        """
        if target_model == 'project.phase':
            return 'phase'
                
        return super(wizard_create_timetracking, self).find_target_inverse(target_model)
    
    
    @api.onchange('resource_id' ,'action_id', 'wo_id', 'phase_id')
    def _onchange_resource_id(self):
        """
            Au changement de la phase, du wo, de l'action ou de la ressource, on récupère leur nom pour les inscrire dans le champs "name"
        """
        super(wizard_create_timetracking, self)._onchange_resource_id()
        if self.target_type == 'phase':
            if self.phase_id and self.resource_id:
                self.name = '%s - %s - %s'%(self.resource_id.name, self.phase_id.name, fields.Datetime.now())
    