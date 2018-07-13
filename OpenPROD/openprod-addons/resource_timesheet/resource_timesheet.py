# -*- coding: utf-8 -*-
from openerp import models, fields, api, tools
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
from openerp.addons.base_openprod.common import get_form_view
from datetime import timedelta

class resource_timesheet(models.Model):
    """ 
        Timesheet for resource
    """
    _name = 'resource.timesheet'
    _description = 'Timesheet for resource'
    
    @api.multi
    @api.depends('name')
    def name_get(self):
        """
            On affiche 'nom ressource - Date début / Date fin'
        """
        result = []
        for timesheet in self:
            if timesheet.date_from and timesheet.date_to and timesheet.resource_id:
                name = '%s - %s / %s'%(timesheet.resource_id.name, timesheet.date_from, timesheet.date_to)
            else:
                name = ''
                 
            result.append((timesheet.id, name))
             
        return result
    
    
    @api.one   
    @api.depends('date_from', 'date_to', 'resource_id')
    def _compute_resource_timetracking_ids(self):
        """
            On récupère toutes les lignes de temps de la ressource ayant les champs 
            de la fonction _timesheet_fields_list remplis 
        """
        timetracking_list = []
        if self.date_from and self.date_to and self.resource_id:
            timetracking_obj = self.env['resource.timetracking']
            #Récupération des champs qui doivent être remplis pour le search
            fields_list = timetracking_obj._timesheet_fields_list()
            search_args = ['&', ]
            for i in range((len(fields_list)-1)):
                search_args.append('|')
                
            for field in fields_list:
                search_args.append((field, '!=', False))
            
            #Recherche: lignes qui ont la même ressource
            #ET (date début ligne comprise entre date début et fin timesheet 
            #    OU date fin ligne comprise entre date début et fin timesheet 
            #    OU date début ligne inférieure à date début timesheet et date fin ligne supérieur date fin timesheet)  
            args = ['&',('resource_id', '=', self.resource_id.id),
                    '|', '|',
                    '&', ('start_date', '>=', self.date_from), ('start_date', '<=', self.date_to),
                    '&', ('end_date', '>=', self.date_from), ('end_date', '<=', self.date_to),
                    '&', ('start_date', '<=', self.date_from), ('end_date', '>=', self.date_to)]
            search_args.extend(args)
            timetracking_list = timetracking_obj.search(search_args).ids
        
        self.resource_timetracking_ids = timetracking_list
    
    
    @api.one   
    @api.depends('attendance_ids')
    def _compute_actual_attendance(self):
        """
            On récupère la dernière ligne de pointage pour connaitre le statut de la resource
        """
        state = 'out'
        if self.id:
            last_attendance_read = self.env['attendance.list'].search_read([('timesheet_id', '=', self.id)], 
                                                                           ['attendance_type'], limit=1, order='date desc')
            state = last_attendance_read and last_attendance_read[0]['attendance_type'] or 'out'
            
        self.actual_attendance_state = state
    
    
    @api.one   
    def _compute_total_input_hours(self):
        """
            On fait la somme de toutes les heures saisies de la feuille de temps
        """
        total_input_hours = 0
        #Dates de la timesheet en format datetime pour comparer aux lignes de temps
        sheet_date_from = fields.Datetime.to_string(fields.Datetime.from_string(self.date_from))
        sheet_date_to = fields.Datetime.to_string(fields.Datetime.from_string(self.date_to) + timedelta(days=1))
        if self.resource_id and sheet_date_from and sheet_date_to:
            calendar_line_obj = self.env['calendar.line']
            calendar_id = self.resource_id.calendar_id.id
            for timetracking_line in self.resource_timetracking_ids:
                track_date_start = timetracking_line.start_date
                track_date_end = timetracking_line.end_date
                track_hours = timetracking_line.time
                #Si date de début et de fin de la ligne sont comprise entre date de début et de fin timesheet on ajoute le temps de la ligne
                if sheet_date_from <= track_date_start <= sheet_date_to and sheet_date_from <= track_date_end <= sheet_date_to:
                    total_input_hours += track_hours
                else:
                    #Sinon on fait le prorata de la quantité d'heures travaillées sur la timesheet par rapport au nombre de jours travaillés
                    #de la timesheet et le nombre de jours total de la ligne 
                    total_length_day = len(calendar_line_obj.search([('real_end_date', '>=', track_date_start), 
                                                                 ('real_start_date', '<=', track_date_end), 
                                                                 ('calendar_id', '=', calendar_id)]))
                    if total_length_day > 0:
                        comp_date_start = track_date_start
                        comp_date_end = track_date_end
                        if track_date_start < sheet_date_from:
                            comp_date_start = sheet_date_from
                        
                        if comp_date_end > sheet_date_to:
                            comp_date_end = sheet_date_to
                        
                        timesheet_length_day = len(calendar_line_obj.search([('real_end_date', '>=', comp_date_start), 
                                                                         ('real_start_date', '<=', comp_date_end), 
                                                                         ('calendar_id', '=', calendar_id)]))
                        total_input_hours += (track_hours*(timesheet_length_day/float(total_length_day)))
                        
        self.total_input_hours = total_input_hours
    
    
    @api.one   
    def _compute_theoretical_attendance_hours(self):
        """
            Total des heures de présence théorique (provient du calendrier de la resource)
        """
        theoretical_attendance_hours = 0
        if self.resource_id and self.date_from and self.date_to:
            resource_calendar_id = self.resource_id.calendar_id.id
            args_calendar_line = [('calendar_id', '=', resource_calendar_id),
                                  ('real_start_date', '>=', self.date_from),
                                  ('real_end_date', '<=', self.date_to)]
            total_hours = self.env['calendar.line'].search_group(fields=['real_hour'], 
                                         without_order=True,
                                         args=args_calendar_line,
                                         sum='real_hour',
                                         return_dict=False)
                 
            theoretical_attendance_hours = total_hours and total_hours[0] or 0
                
        self.theoretical_attendance_hours = theoretical_attendance_hours
    
    
    @api.one
    def _compute_total_attendance_hours(self):
        """
            Total des heures de présence pointées
        """
        total_attendance_hours = 0
        last_hour = False
        attendance_hours_read = self.env['attendance.list'].search_read([('timesheet_id', '=', self.id)], 
                                                                       ['date', 'attendance_type'], order='date asc')
        for attendance in attendance_hours_read:
            if attendance['attendance_type'] == 'in':
                last_hour = fields.Datetime.from_string(attendance['date'])
            elif last_hour and attendance['attendance_type'] == 'out':
                compare_date = fields.Datetime.from_string(attendance['date'])
                total_attendance_hours += (compare_date - last_hour).total_seconds()
                
        self.total_attendance_hours = total_attendance_hours / 3600.0
    
    
    @api.one   
    def _compute_difference_hours(self):
        """
            Différence heures pointées/heures saisies
            et différence heures théoriques/heures pointées
        """
        self.diff_input_hours = self.total_input_hours - self.total_attendance_hours 
        self.diff_theoritical_hours = self.total_attendance_hours - self.theoretical_attendance_hours 
    
    
    @api.one
    @api.depends('date_from')
    def _compute_date(self):
        """
            Fonction qui calcule la semaine de la timesheet à partir de sa date de début
        """
        date = fields.Date.from_string(self.date_from)
        if date:
            isocal = date.isocalendar()
            if len(str(isocal[1])) == 1:
                self.week_number = '0%s'%(str(isocal[1]))
            else:
                self.week_number = str(isocal[1])
    
    
    @api.one   
    def _compute_search_my_timesheet(self):
        """
            Fonction non utile, on utilise que la fonction search
        """
        self.search_my_timesheet = True
    
    
    def _search_search_my_timesheet(self, operator, value):
        """
            Retourne l'id de la timesheet actuelle de la ressource de l'utilisateur
        """
        resource_id = self.env.user.resource_id and self.env.user.resource_id.id or False
        if resource_id:
            query = """
                SELECT 
                  id 
                FROM 
                  resource_timesheet
                WHERE
                    resource_id = %s
                AND
                    date_from <= current_date
                AND
                    date_to >= current_date
                """%(resource_id)
            self.env.cr.execute(query)
            res_ids = self.env.cr.fetchall()
            if res_ids:
                res = [x[0] for x in res_ids]
            else:
                res = []
                
            return [('id', 'in', res)]
    
    
    @api.model
    def _state_get(self):
        return [
                ('new', _('New')),
                ('open', _('Opened')),
                ('confirm', _('Waiting Approval')),
                ('done', _('Approved')),
                       ]
    
    
    @api.model
    def _attendance_state_get(self):
        return [
                ('in', _('Present')),
                ('out', _('Absent')),
                       ]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    state = fields.Selection('_state_get', string='State', default='new')
    actual_attendance_state = fields.Selection('_attendance_state_get', string='Actual state', compute='_compute_actual_attendance')
    resource_id = fields.Many2one('mrp.resource', string='Resource', required=True, ondelete='restrict', 
                                  default=lambda self:self.env.user.resource_id)
    date_from = fields.Date(string='Date from', required=True, default=lambda self: fields.Date.today())
    date_to = fields.Date(string='Date to', required=True, default=lambda self: fields.Date.today())
    resource_timetracking_ids = fields.One2many('resource.timetracking', string='Time lines', compute='_compute_resource_timetracking_ids')
    company_id = fields.Many2one('res.company', string='Company', required=False, ondelete='restrict', 
                                 default=lambda self:self.env.user.company_id)
    attendance_ids = fields.One2many('attendance.list', 'timesheet_id',  string='Attendances', readonly=False)
    total_input_hours = fields.Float(string='Total input hours', compute='_compute_total_input_hours', store=True)
    theoretical_attendance_hours = fields.Float(string='Theoretical attendance hours', compute='_compute_theoretical_attendance_hours', 
                                                store=True)
    total_attendance_hours = fields.Float(string='Total attendance hours', compute='_compute_total_attendance_hours', 
                                                store=True)
    diff_input_hours = fields.Float(string='Difference attendance/input hours', compute='_compute_difference_hours', 
                                                store=True, help="Total input hours - total attendance hours")
    diff_theoritical_hours = fields.Float(string='Difference attendance/theoretical hours', compute='_compute_difference_hours', 
                                                store=True, help="Total attendance hours - Total theoretical attendance hours")
    search_my_timesheet = fields.Boolean(string='Search my timesheet', compute='_compute_search_my_timesheet', search='_search_search_my_timesheet')
    week_number = fields.Char(string='Week number', size=2, compute='_compute_date', store=True)
    calendar_id = fields.Many2one('calendar', related="resource_id.calendar_id")
    
    
    @api.one   
    @api.constrains('date_from', 'date_to')
    def _check_attendance_ids_date(self):
        """
            Verifie que la date des pointages est bien comprise entre les deux dates de la timesheet
        """
        date_from = self.date_from
        date_to = self.date_to
        search_args = [('timesheet_id', '=', self.id),
                        '|', ('date', '<', date_from),
                        ('date', '>', date_to)]
        if self.env['attendance.list'].search(search_args, limit=1):
            raise Warning(_('Error ! Your attendance line must be included in the timesheet dates'))
        
    
    @api.one
    @api.constrains('resource_id', 'date_from', 'date_to')    
    def _check_unique_timesheet_date(self):
        """
            Verifie qu'il n'y ai pas de feuilles de temps qui se chevauchent pour une même ressource
        """
        query = """
            SELECT 
                id
            FROM 
                resource_timesheet
            WHERE 
                (date_from <= '%s' 
            AND 
                '%s' <= date_to) 
            AND 
                resource_id = %s 
            AND 
                id <> %s
            """%(self.date_to, self.date_from, self.resource_id.id, self.id)
        self.env.cr.execute(query)
        if self.env.cr.fetchall():
            raise Warning(_('Error ! You cannot have two timesheets that overlap for the same resource'))
    
    
    @api.multi
    def clock_in(self):
        """
            Fonction de pointage de l'entrée
        """
        now = fields.Datetime.now()
        attendance_obj = self.env['attendance.list']
        for timesheet in self:
            attendance_obj._create_attendance_line(now, timesheet.id, 'in')
        
        return True
    
    
    @api.multi
    def clock_out(self):
        """
            Fonction de pointage de la sortie
        """
        now = fields.Datetime.now()
        attendance_obj = self.env['attendance.list']
        for timesheet in self:
            attendance_obj._create_attendance_line(now, timesheet.id, 'out')
        
        return True
    
    @api.multi
    def open_timetracking_lines(self):
        domain = [('id', 'in', self.resource_timetracking_ids.ids)]
        return {
              'name': _('Timetracking Lines'),
              'view_type': 'form',
              "view_mode": 'tree',
              'res_model': 'resource.timetracking',
              'type': 'ir.actions.act_window',
              'domain': domain,
              }
        
    @api.multi
    def write(self, vals):
        ret = super(resource_timesheet, self).write(vals)
        if not self.env.context.get('no_function'):
            self.with_context({'no_function': True})._compute_theoretical_attendance_hours()
            self.with_context({'no_function': True})._compute_total_input_hours()
            self.with_context({'no_function': True})._compute_total_attendance_hours()
            self.with_context({'no_function': True})._compute_difference_hours()
        return ret
    


class attendance_list(models.Model):
    """ 
        List of attendances for a timesheet
    """
    _name = 'attendance.list'
    _description = 'List of attendances for a timesheet'
    _rec_name = 'date'
    _order= 'date desc'
    
    @api.model
    def _type_get(self):
        return [
                ('in', _('In')),
                ('out', _('Out')),
                       ]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    timesheet_id = fields.Many2one('resource.timesheet', string='Timesheet', required=False, ondelete='cascade')
    attendance_type = fields.Selection('_type_get', string='Type', required=True)
    date = fields.Datetime(string='Date', required=True)
    
    
    @api.one
    @api.constrains('date', 'attendance_type', 'timesheet_id')
    def _check_attendance_type(self):
        """
            Verifie que la date du pointage est bien comprise entre les deux dates de la timesheet
            et qu'il n'y ai pas deux lignes 'in' ou deux lignes 'out' l'une après l'autre
        """
        #Vérification cohérence des dates
        timesheet_date_read = self.timesheet_id.read(['date_from', 'date_to'])
        line_date = self.date
        if timesheet_date_read and (line_date < timesheet_date_read[0]['date_from'] or line_date > timesheet_date_read[0]['date_to']):
            raise Warning(_('Error ! Your attendance line must be included in the timesheet dates'))
        
        #Vérification du in/out à la suite
        last_attendance = False
        attendance_type_read = self.env['attendance.list'].search_read([('timesheet_id', '=', self.timesheet_id.id)], 
                                                                           ['attendance_type'], order='date desc')
        attendance_type_list = [x['attendance_type'] for x in attendance_type_read]
        for att_type in attendance_type_list:
            if not last_attendance:
                last_attendance = att_type
            else:
                if att_type == last_attendance:
                    raise Warning(_('Error ! You cannot have two attendance line one after the other with the same type'))
            
                last_attendance = att_type
    
    
    def _create_attendance_line(self, date, timesheet_id, attendance_type='in'):
        """
            Permet de créer une ligne de présence
            :type self: purchase.order.line
            :param date: Date du pointage
            :type date: Datetime
            :param timesheet_id: ID de la timesheet sur laquelle on pointe
            :type timesheet_id: integer
            :param attendance_type: Type de ligne (in ou out)
            :type attendance_type: char
            :return: True
            :rtype: Boolean
        """
        create_vals = {'timesheet_id': timesheet_id,
                       'attendance_type': attendance_type,
                       'date': date}
        self.create(create_vals)
        return True
    
    
    
    
