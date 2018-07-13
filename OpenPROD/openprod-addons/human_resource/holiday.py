# -*- coding: utf-8 -*-
from openerp import models, api, fields, _
from openerp.exceptions import except_orm
from openerp.addons.base_openprod.common import roundingUp
from openerp.exceptions import Warning


class resource_holiday_type(models.Model):
    """ 
        Holiday's type
    """
    _name = 'resource.holiday.type'
    _description = "Holiday's type"
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Name', required=True, size=128, translate=True)
    need_validation = fields.Boolean(string='Need a validation', default=False)
    allow_override = fields.Boolean(string='Allow to Override Limit', default=False, 
                                    help="If you select this check box, the system allows the employees to take more leaves than the available ones for this type")
    duration = fields.Float(string='Initial default balance', required=True)
    group_id = fields.Many2one('res.groups', string='Validation group', required=False, ondelete='restrict', 
                               help="If the holiday type need a validation, chose here the user group allowed to confirm the holiday")
    
    
    
class resource_holiday(models.Model):
    """ 
        Holiday's resource
        (Congés initialement faits sur les ressources et non sur les employés)
    """
    _name = 'resource.holiday'
    _description = 'Holidays for resources'
    _inherit = 'workflow.base'
    
    @api.model
    def _giving_type_get(self):
        return [
                ('giving', _('Giving')),
                ('demand', _('Demand')),
                       ]
    
    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('to_approved', _('To approved')),
                ('confirmed', _('Confirmed')),
                ('cancelled', _('Cancelled')),
                       ]
    
    
    @api.one
    @api.depends('giving_type', 'demand_time', 'giving_time')
    def _compute_total_duration(self):
        total_duration = 0
        if self.giving_type == 'giving':
            total_duration = self.giving_time
        elif self.giving_type == 'demand':
            total_duration = - self.demand_time
            
        self.total_duration = total_duration
    
    
    @api.one
    @api.depends('employee_id')
    def _compute_my_holidays(self):
        self.my_holiday = True
    
    
    def _default_employee_id(self):
        """
            Par défaut: employé de la resource de l'utilisateur
        """
        employee_id = self.env['employee']
        user = self.env['res.users'].browse(self.env.uid)
        resource_id = user.resource_id and user.resource_id.id or False 
        if resource_id:
            employee_id = self.env['employee'].search([('resource_id', '=', resource_id)], limit=1)
             
        return employee_id
    
    
    def _search_my_holidays(self, operator, value):
        """
            Fonction search qui permet de retrouver tous les congés de l'utilisateur
        """
        res_ids = []
        employee_rcs= False
        user = self.env['res.users'].browse(self.env.uid)
        resource_id = user.resource_id and user.resource_id.id or False
        if resource_id:
            employee_rcs = self.env['employee'].search([('resource_id', '=', resource_id)], limit=1)
            
        if employee_rcs:
            request = """
                SELECT 
                    id 
                FROM 
                    resource_holiday
                WHERE
                    employee_id=%s
                    """%employee_rcs.id
            self.env.cr.execute(request)
            res_ids = self.env.cr.fetchall()
            
        return [('id', 'in', res_ids)]
    
    
    def _get_states(self):
        return {'draft': [('readonly', False)]} 
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Description', required=True, size=256, readonly=True, states=_get_states)
    holiday_type_id = fields.Many2one('resource.holiday.type', string='Holiday type', required=True, ondelete='restrict', 
                                      readonly=True, states=_get_states)
    giving_type = fields.Selection('_giving_type_get', string='Type', readonly=True, states=_get_states)
    giving_id = fields.Many2one('resource.holiday.giving', string='Holiday giving', required=False, ondelete='cascade', 
                                readonly=True, states=_get_states, copy=False)
    employee_id = fields.Many2one('employee', string='Employee', default=_default_employee_id, required=True, ondelete='restrict', 
                                  readonly=True, states=_get_states)
    start_date = fields.Datetime(string='Start date', readonly=True, states=_get_states)
    end_date = fields.Datetime(string='End date', readonly=True, states=_get_states)
    demand_time = fields.Float(string='Duration (in days)', default=0.0, required=False, readonly=True, states=_get_states)
    giving_time = fields.Float(string='Duration (in days)', default=0.0, required=False, readonly=True, states=_get_states)
    total_duration = fields.Float(string='Duration (in days)', compute='_compute_total_duration', store=True)
    state = fields.Selection('_state_get', string='State', default='draft', readonly=True)
    my_holiday = fields.Boolean(string='My holidays', compute='_compute_my_holidays', search='_search_my_holidays')
    
    @api.onchange('start_date', 'end_date', 'employee_id')
    def _onchange_demand_time(self):
        """
            Aide à la saisie : calcul du nombre de jours pris en fonction des dates entrées
            Arrondi à 0.5
        """
        computed_duration = 0.0
        employee_rs = self.employee_id
        # On recherche le nombre moyen que doit faire l'employé de la ressource
        if employee_rs and employee_rs.calendar_id:
            #Si on a pas d'info sur le nombre d'heures, on prend 8 par défaut
            avg_hour = employee_rs and employee_rs.avg_hour or 8.0
            if not avg_hour:
                avg_hour = 8.0
            
            calendar_line_rs = employee_rs.calendar_id.get_all_lines_interval(self.start_date, self.end_date)
            time_dict = calendar_line_rs._get_line_time(self.start_date, self.end_date)
            if time_dict:
                total_hour = sum(time_dict.values())
                computed_duration = roundingUp((total_hour / avg_hour), 0.5)
            
        self.demand_time = computed_duration
        
    
    @api.multi
    def resource_holiday_to_approve(self):
        """
            Fonction qui passe le congé à "À approuver"
        """
        self.write({'state': 'to_approved'})
        return True
    
    
    @api.multi
    def confirm_resource_holiday(self):
        """
            Fonction qui confirme le congé et va ajouter des exceptions dans le calendrier de l'employé
        """
        for holiday_rs in self:
            #Si le type de congés nécessite une validation et que l'utilisateur ne fait pas partie
            #du groupe, on empêche la confirmation
            holiday_type_rs = holiday_rs.holiday_type_id
            if holiday_type_rs and holiday_type_rs.need_validation:
                user_ids = holiday_type_rs.group_id and holiday_type_rs.group_id.users.ids or []
                if self.env.uid not in user_ids:
                    raise Warning(_("You haven't the necessary rights to confirm this holiday type"))
                
            holiday_rs.write({'state': 'confirmed'})
            if holiday_rs.giving_type == 'demand' and holiday_rs.start_date and holiday_rs.end_date:
                calendar = self.employee_id.calendar_id
                if calendar:
                    calendar_line_rs = calendar.get_all_lines_interval(holiday_rs.start_date, holiday_rs.end_date)
                    holiday_rs.write_calendar_line_except(calendar_line_rs, holiday_rs.start_date, holiday_rs.end_date)
            
        return True
    

    @api.multi
    def cancel_resource_holiday(self):
        """
            Fonction qui annule le congés et retire les exceptions générées
        """
        for holiday_rs in self:
            holiday_rs.write({'state': 'cancelled'})
            if holiday_rs.giving_type == 'demand' and holiday_rs.start_date and holiday_rs.end_date:
                calendar = holiday_rs.employee_id.calendar_id
                if calendar:
                    calendar_line_rs = calendar.get_all_lines_interval(holiday_rs.start_date, holiday_rs.end_date)
                    calendar_line_rs.write({'hour_exception': -1, 'start_date_exception': False, 'end_date_exception': False})
                
        return True
    
    
    @api.multi
    def put_in_draft_resource_holiday(self):
        """
            Fonction qui passe le congé en brouillon
        """
        self.write({'state': 'draft'})
        return True
    
    
    def write_calendar_line_except(self, calendar_line_rs, start_date, end_date):
        """
            Fonction qui va créer les exceptions sur les lignes de calendrier à partir d'une
            date de fin et d'une date de début
            :type self: resource.holiday
            :param calendar_line_rs: Recordset des lignes de calendrier
            :type calendar_line_rs: recordset: calendar.line
            :param start_date: Date de début
            :type start_date: char format datetime
            :param end_date: Date de fin
            :type end_date: char format datetime
            :return: True
            :rtype: boolean
        """
        for calendar_line in calendar_line_rs:
            write_vals = {}
            new_start_date = False
            hour_exception_seconds = 0
            start_date_line = calendar_line.start_date_related
            end_date_line = calendar_line.end_date_related
            # Lignes qui sont entre la date de début et de fin
            if not (start_date_line <= start_date <= end_date_line) and not (start_date_line <= end_date <= end_date_line):
                write_vals = {'start_date_exception': start_date_line,
                              'end_date_exception': start_date_line,
                              'hour_exception': 0}
            else:
                # Lignes correspondant à la date de début
                if start_date_line <= start_date <= end_date_line:
                    write_vals = {'start_date_exception': start_date_line,
                                  'end_date_exception': start_date}
                    if start_date_line < start_date:
                        new_start_date = True
                
                # Lignes correspondant à la date de fin
                if start_date_line <= end_date <= end_date_line and not new_start_date:
                    write_vals = {'start_date_exception': end_date,
                                  'end_date_exception': end_date_line}
                    
                # Calcul des heures d'exception des lignes correspondant à la date de début et/ou de fin
                if write_vals.get('start_date_exception') and write_vals.get('end_date_exception'):
                    hour_exception_seconds = (fields.Datetime.from_string(write_vals['end_date_exception']) - fields.Datetime.from_string(write_vals['start_date_exception'])).seconds
                
                write_vals['hour_exception'] = hour_exception_seconds / 3600.0 
            
            calendar_line.write(write_vals)
            
        return True
    
    
    @api.one
    @api.constrains('state', 'holiday_type_id')
    def _check_holiday_balance(self):
        """
            À la confirmation du congé, on vérifie le solde total de la ressource
            pour le type de congé. Si il est négatif et que le type de congé n'autorise
            pas le dépassement, on bloque la validation
        """
        if ((self.giving_type =='demand' and self.state == 'confirmed') or \
        (self.giving_type =='giving' and self.state == 'cancelled')) and \
        not self.holiday_type_id.allow_override:
            args_resource_holiday = [('holiday_type_id', '=', self.holiday_type_id.id),
                                     ('employee_id', '>=', self.employee_id.id),
                                     ('state', '=', 'confirmed')]
            holiday_balance_group = self.search_group(fields=['total_duration'], 
                                         without_order=True,
                                         args=args_resource_holiday,
                                         sum='total_duration',
                                         return_dict=False)
                 
            holiday_balance = holiday_balance_group and holiday_balance_group[0] or 0
            if holiday_balance < 0:
                raise Warning(_("This holiday type don't allow balance override"))
    
    
    @api.multi
    def copy(self, default=None):
        """
            On vide les champs de date et de durée
        """
        if not default:
            default = {}
        
        new_default = {
                       'start_date' : False,
                       'end_date' : False,
                       'demand_time' : 0,
                       'giving_time' : 0,
                       }
        default.update(new_default)
        return super(resource_holiday, self).copy(default=default)
    
    
    @api.multi
    def unlink(self):
        """
            On ne peut pas supprimer une demande de congés qui n'est pas annulée ou en brouillon
        """
        for giving in self:
            if giving.state not in ['draft','cancelled']:
                raise Warning(_("You can't delete an holiday which isn't in draft or cancelled"))
            
        return super(resource_holiday, self).unlink()
    
    
    
class resource_holiday_giving(models.Model):
    """ 
        Holiday's employees giving
    """
    _name = 'resource.holiday.giving'
    _description = 'Holidays giving for employees'
    _inherit = 'workflow.base'
    
    @api.model
    def _method_get(self):
        return [
                ('employee', _('Employee')),
                ('employee_category', _('Employee category')),
                       ]
    
    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('to_approved', _('To approved')),
                ('confirmed', _('Confirmed')),
                ('cancelled', _('Cancelled')),
                       ]
    
    
    def _get_states(self):
        return {'draft': [('readonly', False)]} 
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Description', required=True, size=256, readonly=True, states=_get_states)
    holiday_type_id = fields.Many2one('resource.holiday.type', string='Holiday type', required=True, ondelete='restrict', 
                                      readonly=True, states=_get_states)
    duration = fields.Float(string='Duration (in days)', required=True, readonly=True, states=_get_states)
    method = fields.Selection('_method_get', string='Method', required=True, readonly=True, states=_get_states)
    employee_id = fields.Many2one('employee', string='Employee', required=False, ondelete='restrict', readonly=True, states=_get_states)
    employee_category_id = fields.Many2one('employee.category', string='Employee category', required=False, ondelete='restrict', 
                                           readonly=True, states=_get_states)
    comment = fields.Text(string='Comment', readonly=True, states=_get_states)
    state = fields.Selection('_state_get', string='State', default='draft', readonly=True)
    
    @api.onchange('holiday_type_id')
    def _onchange_holiday_type_id(self):
        """
            On récupère le nombre de jours par défaut
        """
        self.duration = self.holiday_type_id.duration
    
    
    @api.multi
    def holiday_giving_to_approve(self):
        """
            Fonction qui passe l'attribution à approuver
        """
        self.write({'state': 'to_approved'})
        return True
    
    
    @api.multi
    def confirm_holiday_giving(self):
        """
            Fonction qui confirme l'attribution de congés et crée autant de ligne de congé
            que de ressource
        """
        holiday_obj = self.env['resource.holiday']
        holiday_rcs = self.env['resource.holiday']
        for giving in self:
            if giving.holiday_type_id:
                vals = {'name': giving.name,
                        'holiday_type_id': giving.holiday_type_id.id,
                        'giving_type': 'giving',
                        'giving_id': giving.id,
                        'giving_time': giving.duration,
                        'state': 'draft',
                        }
                if giving.method == 'employee' and giving.employee_id:
                    vals['employee_id'] = giving.employee_id.id
                    holiday_rcs |= holiday_obj.create(vals)
                elif giving.method == 'employee_category' and giving.employee_category_id:
                    for employee in giving.employee_category_id.employee_ids:
                        vals['employee_id'] = employee.id
                        holiday_rcs |= holiday_obj.create(vals)
        
        holiday_rcs.confirm_resource_holiday()
        self.write({'state': 'confirmed'})
        return True
    

    @api.multi
    def cancel_holiday_giving(self):
        """
            Fonction qui annule l'attribution de congés
        """
        holiday_rcs = self.env['resource.holiday'].search([('giving_id', 'in', self.ids)])
        #On annule puis on supprime les congés
        holiday_rcs.cancel_resource_holiday()
        holiday_rcs.unlink()
        self.write({'state': 'cancelled'})
        return True
    

    @api.multi
    def put_in_draft_holiday_giving(self):
        """
            Fonction qui passe l'attribution en brouillon
        """
        self.write({'state': 'draft'})
        return True
    
    
    @api.multi
    def unlink(self):
        """
            On ne peut pas supprimer une demande de congés qui n'est pas annulée ou en brouillon
        """
        for giving in self:
            if giving.state not in ['draft','cancelled']:
                raise Warning(_("You can't delete an attribution which isn't in draft or cancelled"))
            
        return super(resource_holiday_giving, self).unlink()