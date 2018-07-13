# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.translate import _


class wizard_create_timetracking(models.TransientModel):
    _inherit = 'wizard.create.timetracking'

    @api.model
    def _target_type_get(self):
        res = super(wizard_create_timetracking, self)._target_type_get()
        res.append((self._get_target_type(), self._get_target_string()))
        return res

    @api.model
    def default_get(self, fields_list):
        """
            Surcharge du default_get pour calculer le domaine du M2M sibling_ids
        """
        res = super(wizard_create_timetracking, self).default_get(fields_list=fields_list)
        if self.env.context.get('active_model') in (
            self._get_target_model(), 'resource.timesheet'
        ):
            res['target_type'] = self._get_target_type()
        return res

    def compute_search_args(self):
        search_args = super(wizard_create_timetracking, self).compute_search_args()
        if self.target_type == self._get_target_type():
            search_args = [(self._get_target_field(), '!=', False)]
        return search_args

    issue_id = fields.Many2one(
        comodel_name='tracker.issue', required=False,
        ondelete='set null', string='Issue'
    )

    def update_create_vals(self, vals_all):
        """
            Prise en compte de la distribution analytique pour la création de la ligne de temps
        """
        vals = super(wizard_create_timetracking, self).update_create_vals(vals_all)
        if self.target_type == self._get_target_type() and getattr(self, self._get_target_field()):
            vals[self._get_target_field()] = getattr(self, self._get_target_field()).id
        return vals

    def extend_sibling_domain(self, target_model, target_id):
        """
            Prise en compte de la distribution analytique pour la recherche de lignes de temps parentes
        """
        new_domain = super(wizard_create_timetracking, self).extend_sibling_domain(target_model, target_id)
        if target_model == self._get_target_model():
            new_domain = (self._get_target_field(), '=', int(target_id))

        return new_domain

    def find_target(self, target_type):
        """
            Prise en compte de la distribution analytique pour la recherche de lignes de temps parentes
        """
        target_id, target_model = super(wizard_create_timetracking, self).find_target(target_type)
        if target_type == self._get_target_type():
            target_id = getattr(self, self._get_target_field()).id
            target_model = self._get_target_model()

        return target_id, target_model

    def find_target_inverse(self, target_model):
        """
            Fonction qui retourne le target_type en fonction du modèle
            du type de saisie
        """
        if target_model == self._get_target_model():
            return self._get_target_type()

        return super(wizard_create_timetracking, self).find_target_inverse(target_model)

    @api.onchange('issue_id')
    def _onchange_issue_id(self):
        """
            Au changement de la distribution analytique ou de la ressource,
            on récupère leur nom pour les inscrire dans le champs "name"
        """
        if self.target_type == self._get_target_type():
            if getattr(self, self._get_target_field()) and self.resource_id:
                self.name = '%s - %s - %s' % (
                    self.resource_id.name,
                    getattr(self, self._get_target_field()).name_get()[0][1],
                    fields.Datetime.now()
                )

    def _get_target_field(self):
        return 'issue_id'

    def _get_target_model(self):
        return 'tracker.issue'

    def _get_target_type(self):
        return 'tracker_issue'

    def _get_target_string(self):
        return _('Issue')
