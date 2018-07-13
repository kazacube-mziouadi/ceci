# -*- coding: utf-8 -*-
from openerp import models, fields, api, _

class wizard_create_timetracking(models.TransientModel):
    _inherit = 'wizard.create.timetracking'
    
    @api.model
    def _target_type_get(self):
        """
            Ajout de la distribution analytique dans le champ sélection
        """
        res = super(wizard_create_timetracking, self)._target_type_get()
        res.append(('analytic_distribution', _("Analytic distribution")))
        return res
    
    
    def compute_search_args(self):
        """
            Si le temps est enregistré pour une distribution analytique, on recherche les derniers temps de cette
            ressource sur les distributions analytiques
        """
        search_args = super(wizard_create_timetracking, self).compute_search_args()
        if self.target_type == 'analytic_distribution':
            search_args = [('analytic_distribution_id', '!=', False)]
            
        return search_args
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    analytic_distribution_id = fields.Many2one('product.analytic.distribution', string='Analytic distribution', required=False, ondelete='set null')
    
    @api.model
    def default_get(self, fields_list):
        """
            Surcharge du default_get pour calculer le domaine du M2M sibling_ids
        """
        res = super(wizard_create_timetracking, self).default_get(fields_list=fields_list)
        if self.env.context.get('active_model') == 'product.analytic.distribution' or self.env.context.get('active_model') == 'resource.timesheet':
            res['target_type'] = 'analytic_distribution'
            
        return res
    
    
    def update_create_vals(self, vals_all):
        """
            Prise en compte de la distribution analytique pour la création de la ligne de temps
        """
        vals = super(wizard_create_timetracking, self).update_create_vals(vals_all)
        if self.target_type == 'analytic_distribution' and self.analytic_distribution_id:
            vals['analytic_distribution_id'] = self.analytic_distribution_id.id
            
        return vals
    
    
    def extend_sibling_domain(self, target_model, target_id):
        """
            Prise en compte de la distribution analytique pour la recherche de lignes de temps parentes
        """
        new_domain = super(wizard_create_timetracking, self).extend_sibling_domain(target_model, target_id)
        if target_model == 'product.analytic.distribution':
            new_domain = ('analytic_distribution_id', '=', int(target_id))
            
        return new_domain
    
    
    def find_target(self, target_type):
        """
            Prise en compte de la distribution analytique pour la recherche de lignes de temps parentes
        """
        target_id, target_model = super(wizard_create_timetracking, self).find_target(target_type)
        if target_type == 'analytic_distribution':
            target_id = self.analytic_distribution_id.id
            target_model = 'product.analytic.distribution'
                
        return target_id, target_model
    
    
    def find_target_inverse(self, target_model):
        """
            Fonction qui retourne le target_type en fonction du modèle
            du type de saisie
        """
        if target_model == 'product.analytic.distribution':
            return 'analytic_distribution'
                
        return super(wizard_create_timetracking, self).find_target_inverse(target_model)
    
    
    @api.onchange('analytic_distribution_id')
    def _onchange_analytic_distribution_id(self):
        """
            Au changement de la distribution analytique ou de la ressource, on récupère leur nom pour les inscrire dans le champs "name"
        """
        if self.target_type == 'analytic_distribution':
            if self.analytic_distribution_id and self.resource_id:
                self.name = '%s - %s - %s'%(self.resource_id.name, self.analytic_distribution_id.name_get()[0][1], fields.Datetime.now())
    