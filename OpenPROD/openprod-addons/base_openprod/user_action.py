# -*- coding: utf-8 -*-
from openerp import models, api, fields, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm


class action_type(models.Model):
    """ 
        Actions type 
    """
    _name = 'action.type'
    _description = 'Actions type'
    
    
    @api.model
    def _type_get(self):
        return [
                ('do_list', _('Do list')),
                ('plan', _('Planned action')),
                       ]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Name', size=64, required=True, translate=True)
    type = fields.Selection('_type_get', string='Type', required=True)
    
    

class action_state(models.Model):
    """ 
        Actions state 
    """
    _name = 'action.state'
    _description = 'Actions state'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Name', size=64, required=True, translate=True)
    is_default = fields.Boolean(string='Is default', default=False)
    not_display_state = fields.Boolean(string='Display state', default=False, help="If this field is checked, the state will not "
                                   "be take into the computation of lateness actions")
    to_do_state = fields.Boolean(string='State to do', default=False)
    end_state = fields.Boolean(string='End do', default=False)
    
    @api.one
    @api.constrains('is_default')
    def _check_unique_is_default(self):
        """
            On vérifie qu'il n'y ai pas d'autres enregistrements ayant is_default de coché
        """
        if self.is_default:
            other_rs = self.search([('is_default', '=', True), ('id', '!=', self.id)], limit=1)
            if other_rs:
                raise except_orm('Error', 'You cannot have two state action with the field "is default" checked')
            
            
            
class calendar_event(models.Model):
    """ 
        Actions for users 
    """
    _inherit = 'calendar.event'
    _description = 'Actions for users'
    
    
    def get_default_values(self):
        return {}
    
    
    @api.model
    def default_get(self, fields_list):
        """
            On récupère la date de début envoyée par le calendrier
        """
        res = super(calendar_event, self).default_get(fields_list=fields_list)
        res.update(self.get_default_values())
        return res
    
    
    @api.one
    @api.depends('start_datetime', 'stop_datetime')
    def _compute_end_of_week(self):
        """
            Fonction permettant de récupérer la date du dernier jour de la semaine
        """
        today = datetime.strptime(fields.Date.today(), '%Y-%m-%d')
        date = (today + relativedelta(days=(6-(today.weekday())))).strftime('%Y-%m-%d')
        self.end_of_week = date
        
        
    @api.one
    def _compute_date_color(self):
        """
            Fonction permettant de mettre l'arrière plan de la vue kanban en rouge si la
            date limite est dépassée, et en orange si la date actuelle est supérieure
            à la date limite - nombre jours d'alerte
        """
        stop_date = self.stop_datetime
        if self.state_id and not self.state_id.not_display_state and stop_date:
            today = fields.Date.today()
            if stop_date < today:
                self.color = 2
            elif today > fields.Date.to_string(fields.Date.from_string(stop_date) - relativedelta(days=self.alert_period)):
                self.color = 3
                
        else:
            self.color = 0
    
    
    def _search_date_color(self, operator, value):
        """
            Fonction search de la couleur
        """ 
        res_ids = []
        query_part = ""
        if value == 2:
            query_part = "current_date > stop_datetime"
        elif value == 3:
            query_part = "current_date > stop_datetime - alert_period * interval '1 days' AND current_date < stop_datetime"
            
        query = """
            SELECT 
                id 
            FROM 
                calendar_event 
            WHERE 
                state_id not in (select id from action_state where not_display_state=true)
            AND 
        """
        query += query_part
        if query_part:
            self.env.cr.execute(query)
            res_ids = self.env.cr.fetchall()
            
        return [('id', 'in', res_ids)]
            
            
    @api.one
    def _compute_affected_user_kanban(self):
        """
            Fonction renvoyant 1 si l'utilisateur est l'utilisateur affecté à
            l'action
        """
        if self.env.user == self.affected_user_id:
            self.affected_user_kanban = 1
        else:
            self.affected_user_kanban = 0
            
            
    @api.one
    @api.depends('type_id', 'type_id.type')
    def _compute_related_type(self):
        """
        """
        if self.type_id:
            self.related_type = self.type_id.type
        else:
            self.related_type = False
            
            
    def _search_end_of_week(self, operator, value):
        """
            Fonction search de la fin de la semaine
        """ 
        today = datetime.strptime(fields.Date.today(), '%Y-%m-%d')
        date = (today + relativedelta(days=(6-(today.weekday())))).strftime('%Y-%m-%d')
        return [('id', 'operator', date)]
        
    
    def _default_stop_datetime(self):
        """
            Fonction par défaut de la date limite (datetime). Prend la date du jour + 1
        """
        today = fields.Datetime.from_string(fields.Datetime.now())
        limit_date = today + relativedelta(days=1)
        res = fields.Datetime.to_string(limit_date)
        return res
    
    
    def _default_stop_date(self):
        """
            Fonction par défaut de la date limite (date). Prend la date du jour + 1
        """
        today = fields.Date.from_string(fields.Date.today())
        limit_date = today + relativedelta(days=1)
        res = fields.Date.to_string(limit_date)
        return res
    
    
    def _default_state_id(self):
        """
            Fonction par défaut de l'état. On prend l'état ayant le champ is_default de coché
            ou le premier état trouvé
        """
        res = self.env['action.state'].search([('is_default', '=', True)], limit=1)
        if not res:
            res = self.env['action.state'].search([], limit=1)
        
        return res
    
    
    @api.model
    def create(self, vals):
        """
        """
        if not vals:
            vals = {}
            
        vals['button_save_visible'] = False
        return super(calendar_event, self).create(vals)
    
    
    @api.model
    def _link_object_get(self):
        return [('none', 'None')]
    
    
    @api.one
    def _compute_linked_objects(self):
        """
            Fonction permettant de sélectionner l'objet à afficher (prévu pour être surchargé)
        """
        self.link_object = 'none'
    
    
    @api.model
    def _read_group_state_ids(self, present_ids, domain, **kwargs):
        folded = {}
        states_list = []
        state_search = self.env['action.state'].search([])
        for state in state_search:
            states_list.append((state.id, state.name))
            folded[state.id] = False
        
        return states_list, folded
    
    
    def _needaction_domain_get(self, cr, uid, context=None):
        """
            On écrase la fonction de base d'Odoo afin de ne pas afficher le nombre
            d'événements de l'utilisateur à côté du menu 
        """
        return []
    
    @api.model
    def _related_type_get(self):
        return [
                ('do_list', _('Do list')),
                ('plan', _('Planned action')),
                       ]
    
    
    @api.model
    def _confidentiality_get(self):
        return [
                ('user', _('User')),
                ('all', _('All')),
                ('responsible', _('Responsible')),
                       ]
    
    
    @api.one
    def _compute_timetracking_ids(self):
        """
            Fonction permettant de ramener les temps saisis pour cette action
        """
        timetracking_ids = []
        if self.id:
            timetracking_ids = self.env['resource.timetracking'].search([('action_id', '=', self.id)]).ids
            
        self.timetracking_ids = timetracking_ids                                                                      
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Name')
    affected_user_id = fields.Many2one('res.users', string='Affected to', required=True, ondelete='restrict',
                                       default=lambda self:self.env.user)
    affected_user_kanban = fields.Integer(string='Affected user', default=0, compute='_compute_affected_user_kanban')
    user_id = fields.Many2one(string='Requested by', required=True, ondelete='restrict')
    state_id = fields.Many2one('action.state', string='State', required=False, ondelete='restrict', default=_default_state_id)
    not_display_related = fields.Boolean(string='Not display state', default=False, related='state_id.not_display_state')
    end_state_related = fields.Boolean(string='End state', default=False, related='state_id.end_state')
    color = fields.Integer(string='Color', default=0, required=False, compute='_compute_date_color', search='_search_date_color')
    end_of_week = fields.Date(string='End of week', compute='_compute_end_of_week', search='_search_end_of_week')
    button_save_visible = fields.Boolean(string='button_save_visible', default=False)
    alert_period = fields.Integer(string='Alert period', default=1, required=False, help='In days')
    timetracking_ids = fields.One2many('resource.timetracking', compute='_compute_timetracking_ids', string='Times',
                                        store=False)
    start_datetime = fields.Datetime(default=datetime.now())
    link_object = fields.Selection('_link_object_get', string='Link object', compute='_compute_linked_objects', store=False)
    type_id = fields.Many2one('action.type', string='Type', required=True, ondelete='restrict')
    related_type = fields.Selection('_related_type_get', string='Related type', compute='_compute_related_type', store=True)
    duration = fields.Float(default=1)
    confidentiality = fields.Selection('_confidentiality_get', string='Confidentiality')
    auth_user_ids = fields.Many2many('res.users', 'action_user_rel', 'action_id', 'user_id', string='Authorized users')
    auth_group_ids = fields.Many2many('res.groups', 'action_group_rel', 'action_id', 'group_id', string='Authorized groups')
    
    
    _order = 'start_datetime asc'
    _group_by_full = {
        'state_id': _read_group_state_ids
    }
    
    def no_recurrency_list(self):
        """
            Permet de définir quels modèles ne doivent pas être liés à des événements récurrents
        """
        fields_list = []
        return fields_list
    
    
    def fields_to_check(self):
        """
            Permet de définir quels champs doivent être vérifiés pour la contrainte
        """
        fields_list = []
        return fields_list
    
    
    def _check_closing_date(self, cr, uid, ids, context=None):
        """
            On écrase la fonction de base pour la contrainte de date afin
            de ne pas baser la contrainte sur les champs fonctions storés
        """
        for event in self.browse(cr, uid, ids, context=context):
            if event.start_datetime > event.stop_datetime:
                return False
                
        return True
    
    
    def _check_recurrency(self, cr, uid, ids, context=None):
        """
            Empêche de créer des événements récurrents s'ils sont liés à des objets définis
            Obligation d'utilisation de l'ancienne api afin de gérer tous les
            champs qui seront ajoutés par les modules au-dessus
            
        """
        for event in self.browse(cr, uid, ids, context=context):
            if event.recurrency:
                for field in self.no_recurrency_list():
                    if event[field]:
                        return False
                
        return True
    
    
    def _check_only_one_link(self, cr, uid, ids, context=None):
        """
            On vérifie que l'événement ne soit lié qu'à un objet.
            Obligation d'utilisation de l'ancienne api afin de gérer tous les
            champs qui seront ajoutés par les modules au-dessus
        """
        for event in self.browse(cr, uid, ids, context=context):
            field_list = []
            for field in self.fields_to_check():
                if event[field]:
                    field_list.append(event[field])
                
                if len(field_list) > 1:
                    return False
                
        return True
    
    
    _constraints = [
        (_check_only_one_link, 'You can\'t have more than one link between an action and an other object', []),
        (_check_recurrency, 'You can\'t have recurrent event linked to this models', []),
        (_check_closing_date, 'Error ! End date cannot be set before start date.', ['start_datetime', 'stop_datetime'])
    ]
    
    
    @api.onchange('type_id', 'related_type')
    def _onchange_type_id(self):
        """
            Au changement du type, on passe la durée à 0 si le type d'action est do_list
        """
        if self.type_id and self.type_id.type == 'do_list':
            self.duration = 0
                
    
    @api.multi
    def save_action(self):
        return {'type': 'ir.actions.act_window_close'}
    
    
    def add_or_remove_days(self, nb_days, add=False, remove=False):
        """
            Fonction permettant d'ajouter ou de retirer un certain nombre de jours à la date de début d'une action
            (et par conséquent à la date de fin)
            :type self: calendar.event
            :param nb_days: Nombre de jours à ajouter ou à enlever
            :type infos: integer
            :param add: True si on ajoute le nombre de jours
            :type add: boolean
            :param add: True si on enlève le nombre de jours
            :type add: boolean
            :return: True
            :rtype: boolean
        """ 
        field = 'start_datetime'
        field2 = 'stop_datetime'
        start_date = self.start_datetime
        stop_date = self.stop_datetime
        if not start_date:
            start_date = fields.Datetime.now()
            stop_date = fields.Datetime.now()
            
        new_date = False
        if add:
            new_date = fields.Datetime.from_string(start_date) + relativedelta(days=nb_days)
            new_date2 = fields.Datetime.from_string(stop_date) + relativedelta(days=nb_days)
        elif remove:
            new_date = fields.Datetime.from_string(start_date) - relativedelta(days=nb_days)
            new_date2 = fields.Datetime.from_string(stop_date) - relativedelta(days=nb_days)
            self[field] = fields.Datetime.to_string(new_date)
            self[field2] = fields.Datetime.to_string(new_date2)
        
        self.write({field2: fields.Datetime.to_string(new_date2), field: fields.Datetime.to_string(new_date)})
        return True
   
    
    @api.multi
    def add_one_day(self):
        """
            Bouton permettant d'ajouter un jour à la date limite
        """
        for action in self:
            action.add_or_remove_days(1, True, False)

    
    @api.multi
    def add_seven_days(self):
        """
            Bouton permettant d'ajouter sept jours à la date limite
        """
        for action in self:
            action.add_or_remove_days(7, True, False)
    
    
    @api.multi
    def remove_one_day(self):
        """
            Bouton permettant d'enlever un jour à la date limite
        """
        for action in self:
            action.add_or_remove_days(1, False, True)
    
    
    @api.multi
    def remove_seven_days(self):
        """
            Bouton permettant d'enlever sept jours à la date limite
        """
        for action in self:
            action.add_or_remove_days(7, False, True)
    
    
    