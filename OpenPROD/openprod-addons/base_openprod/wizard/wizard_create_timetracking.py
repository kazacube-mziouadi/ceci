# -*- coding: utf-8 -*-
from openerp import models, fields, api, tools, _
from datetime import datetime, timedelta
from openerp.addons.base_openprod.common import get_form_view

class wizard_create_timetracking(models.TransientModel):
    """ 
        Create a timetracking entry, or edit similar entries 
    """
    _name = 'wizard.create.timetracking'
    _description = 'Create a timetracking entry, or edit similar entries'
    
    _sql_constraints = [
                        ('check_dates', 'check (end_date > start_date)', 'End date is before start date'),
                        ]
    
    @api.model
    def _target_type_get(self):
        return [
                ('action', 'Action'),
                       ]
    
    
    @api.model
    def _activity_get(self):
        return [
                ('waiting', _('Waiting')),
                ('setting', _('Setting')),
                ('production', _('Production')),
                ('cleaning', _('Cleaning'))
                       ]
    
    
    def compute_search_args(self):
        """
            Fonction permettant de ramener les 20 derniers temps avant la date de fin pour les actions
        """
        search_args = []
        if self.target_type == 'action':
            search_args = [('action_id', '!=', False)]
            
        return search_args
    
    
    @api.one
    @api.depends('resource_id', 'end_date')
    def _compute_last_times(self):
        """
            Fonction permettant de ramener les 20 derniers temps avant la date de fin
        """
        search_args = [('end_date', '<=', self.end_date), ('resource_id', '=', self.resource_id.id)]
        search_args.extend(self.compute_search_args())
        self.previous_time_ids = self.env['resource.timetracking'].search(search_args, limit=20).ids
    

    @api.onchange('end_date', 'duration', 'day_only')
    def _onchange_dates(self):
        """
            Fonction permettant de calculer la date de départ à partir de la date de fin,
            de la durée et du calendrier de la ressource
        """
        calendar = self.resource_id.calendar_id or self.env.user.company_id.partner_id.calendar_id
        if self.duration and self.end_date and self.resource_id:
            if not self.day_only:
                if calendar:
                    res = calendar.get_dates_inverse(self.end_date, self.duration)
                    self.start_date = res.get('start_date')
            else:
                calendar_line_id = self.env['calendar.line'].search([
                                          ('calendar_id', '=', calendar.id),
                                          ('real_end_date', '>=', self.end_date),
                                          ('start_date', '<=', self.end_date),
                                          ], limit=1)
                self.start_date = max(calendar.get_dates_inverse(self.end_date, self.duration or 1).get('start_date'), calendar_line_id.real_start_date)
        else:
            self.start_date = calendar.get_dates_inverse(self.end_date, self.duration or 1).get('start_date')
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=False, size=164)
    resource_id = fields.Many2one('mrp.resource', string='Resource', required=True, ondelete='set null',
                                  default=lambda self:self.env.user.resource_id)
    start_date = fields.Datetime(string='Start Date')
    end_date = fields.Datetime(string='End Date', required=True, default=lambda self: fields.Datetime.now())
    activity = fields.Selection('_activity_get', string='Activity', select=True, default='production')
    duration = fields.Float(string="Duration", required=True, default=1)
    previous_time_ids = fields.One2many('resource.timetracking', string='Last times', compute='_compute_last_times', 
                                        store=False)
    action_id = fields.Many2one('calendar.event', string='Action', required=False, ondelete='set null')
    target = fields.Char(string="Target")
    sibling_ids = fields.Many2many('resource.timetracking', 'sibling_timetracking_rel', 'create_timetracking_id', 
                                   'sibling_timetracking_id', string='Sibling')
    target_type = fields.Selection('_target_type_get', string='Target type')
    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='set null',
                                  default=lambda self:self.env.user)
    day_only = fields.Boolean(string='Day only', default=True)
    
    
    @api.model
    def default_get(self, fields_list):
        """
            Surcharge du default_get pour calculer le domaine du M2M sibling_ids
        """
        res = super(wizard_create_timetracking, self).default_get(fields_list=fields_list)
        #On récupère la resource envoyée par défaut ou celle de la feuille de temps
        context = self.env.context
        resource_rcs = self.find_resource_rcs(context)
        if not res.get('start_date', False) or not resource_rcs:
            return res
        
        #Dans le cas où on aurait cliqué directement sur le nombre d'heure du résumé,
        #On va aller chercher la date de fin du calendrier de la ligne pour le jour sélectionné
        start_date = datetime.strptime(res['start_date'], tools.DEFAULT_SERVER_DATETIME_FORMAT)
        end_date = start_date + timedelta(days=1)
        res['end_date'] = resource_rcs.calendar_id.get_dates(res['start_date'], 1).get('end_date')
        res['duration'] = 1
        #Calcule du domaine du M2M sibling_ids
        #On prend toutes les lignes de temps avec la même target dont la date de début et/ou de fin est compris entre
        #start_date et end_date
        domain = [
                  '|',
                      '|',
                          '&',
                              ('start_date', '>=', start_date.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)),
                              ('start_date', '<=', end_date.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)),
                          '&',
                              ('end_date', '>=', start_date.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)),
                              ('end_date', '<=', end_date.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)),
                      '&',
                          ('start_date', '<=', start_date.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)),
                          ('end_date', '>=', end_date.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)),
                  ]
        if context.get('add_line'):
            target_id, target_model = self.find_target(self.target_type)
        elif context.get('target', False):
            target_id, target_model = context['target'].split('|')
            res['target_type'] = self.find_target_inverse(target_model)
        else:
            return res
        
        new_domain = self.extend_sibling_domain(target_model, target_id)
        if new_domain:
            domain.append(new_domain)
            res[new_domain[0]] = new_domain[2]
        
        sibling_ids = self.env['resource.timetracking'].search(domain)
        if len(sibling_ids):
            res['sibling_ids'] = [(6, 0, sibling_ids.ids)]
            
        return res
    
    
    def find_resource_rcs(self, context):
        """
            Fonction qui permet de récupérer la ressource
        """
        resource_rcs = False
        if context.get('resource_id'):
            if isinstance(context['resource_id'],list):
                resource_id = context['resource_id'][0]
            else:
                resource_id = context['resource_id']

            resource_rcs = self.env['mrp.resource'].browse(resource_id)
        
        return resource_rcs
    
    
    def extend_sibling_domain(self, target_model, target_id):
        """
            Fonction qui permet d'affiner le domaine du M2M sibling_ids en fonction
            du type de saisie
        """
        new_domain = False
        if target_model == 'calendar.event':
            new_domain = ('action_id', '=', int(target_id))
            
        return new_domain
    
    
    def find_target(self, target_type):
        """
            Fonction qui recherche et retourne le modèle et l'id de l'objet sélectionné en fonction
            du type de saisie
        """
        target_id = False
        target_model = ''
        if target_type == 'action':
            target_id = self.action_id.id
            target_model = 'calendar.event'
                
        return target_id, target_model
    
    
    def find_target_inverse(self, target_model):
        """
            Fonction qui retourne le target_type en fonction du modèle
            du type de saisie
        """
        if target_model == 'calendar.event':
            return 'action'
                
        return ''
    
    
    def update_create_vals(self, vals_all):
        """
            Fonction qui permet d'ajouter des champs à la création de la ligne de temps
        """
        vals = {}
        if self.target_type == 'action' and self.action_id:
            vals['action_id'] = self.action_id.id
        
        vals['hourly_cost'] = self.resource_id and self.resource_id.hourly_rate or 0.0
        
        return vals
    
    
    @api.multi
    def create_timetracking(self):
        """
            Fonction permettant de créer la ligne de suivi des temps et de rouvrir ou de 
            fermer le wizard en fonction du context
        """
        timetracking_obj = self.env['resource.timetracking']
        for wizard in self:
            context = self.env.context
            vals = {
                    'resource_id': wizard.resource_id.id,
                    'name': wizard.name,
                    'start_date': wizard.start_date,
                    'end_date': wizard.end_date,
                    'activity': wizard.activity,
                    'user_id': self.env.uid,
                    'time': wizard.duration,
                    'time_spent': wizard.duration,
                    }
            vals.update(wizard.update_create_vals(vals))
            timetracking_obj.create(vals)
            if not context.get('close_wizard'):
                action_struc = {}
                action_dict = get_form_view(self, 'base_openprod.act_wizard_create_timetracking_action')
                if action_dict and action_dict.get('id') and action_dict.get('type'):
                    action = self.env[action_dict['type']].browse(action_dict['id'])
                    action_struc = action.read()
                    action_struc[0]['context'] = context
                    action_struc = action_struc[0]
                      
                return action_struc
            else:
                return {'type':'ir.actions.act_window_view_reload'}
    
    
    @api.multi
    def save_and_close(self):
        return {'type':'ir.actions.act_window_view_reload'}


    @api.onchange('resource_id' ,'action_id')
    def _onchange_resource_id(self):
        """
            Au changement de l'action ou de la ressource, on récupère leur nom pour les inscrire dans le champs "name"
        """
        if self.target_type == 'action' and self.action_id and self.resource_id:
            self.name = '%s - %s - %s'%(self.resource_id.name, self.action_id.name, fields.Datetime.now())
            
            


class udpate_timetracking_state(models.TransientModel):
    """ 
        Wizard which allow to update the state of the times
    """
    _name = 'udpate.timetracking.state'
    _description = 'Wizard which allow to update the state of the times'
    _rec_name = 'state'
    
    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('validated', _('Validated')),
                ('error', _('In error')),
                ('cancel', _('Cancelled')),
                       ]
        
            
    #===========================================================================
    # COLUMNS
    #===========================================================================
    state = fields.Selection('_state_get', string='State', default='draft', required=True)
    
    @api.multi
    def update_state(self):
        """
            Mise à jour des états des lignes de temps sélectionnées
        """
        for wizard in self:
            if self.env.context.get('active_ids') and wizard.state:
                for time in self.env['resource.timetracking'].browse(self.env.context['active_ids']):
                    time.write({'state': wizard.state})
                
        return {'type': 'ir.actions.act_window_close'}
