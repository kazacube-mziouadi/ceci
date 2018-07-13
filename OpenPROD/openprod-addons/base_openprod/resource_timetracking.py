# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError


class resource_timetracking(models.Model):
    """ 
        Suivi des temps des ressources
    """
    _name = 'resource.timetracking'
    _description = 'Suivi des temps'
    
    @api.model
    def _activity_get(self):
        return [
                ('waiting', _('Waiting')),
                ('setting', _('Setting')),
                ('production', _('Production')),
                ('cleaning', _('Cleaning'))
                       ]


    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('validated', _('Validated')),
                ('error', _('In error')),
                ('cancel', _('Cancelled')),
                       ]
        
    
    @api.one
    @api.depends('start_date')
    def _compute_date(self):
        """
            Fonction qui calcule la semaine de la ligne de temps à partir de sa date de début
        """
        date = fields.Datetime.from_string(self.start_date)
        if date:
            isocal = date.isocalendar()
            if len(str(isocal[1])) == 1:
                self.week_number = '0%s'%(str(isocal[1]))
            else:
                self.week_number = str(isocal[1])
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    start_date = fields.Datetime(string='Start Date')
    end_date = fields.Datetime(string='End Date')
    activity = fields.Selection('_activity_get', string='Activity', select=True)
    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='restrict', select=True)
    resource_id = fields.Many2one('mrp.resource', string='Resource', required=True, ondelete='restrict', select=True)
    is_first_resource = fields.Boolean(string='First Resource', default=False)
    time = fields.Float(string='Time scrolling', default=0.0, required=False)
    time_spent = fields.Float(string='Time spent', default=0.0, required=False)
    state = fields.Selection('_state_get', string='State', default='draft')
    week_number = fields.Char(string='Week number', size=2, compute='_compute_date', store=True)
    is_to_invoice = fields.Boolean(string='To invoice', default=False)
    hourly_cost = fields.Float(string='Hourly cost', default=0.0, required=False)
    action_id = fields.Many2one('calendar.event', string='Action', required=False, ondelete='restrict')
    
    def _timesheet_fields_list(self):
        """
            Fonction uniquement destinée au module resource_timesheet, elle est surchargée
            par les autres modules afin d'obtenir la liste des champs recherchés dans la timesheet.
            Permet de garder resource_timesheet indépendant
        """
        return ['action_id']
    
    @api.multi
    def read(self, fields=None, load='_classic_read'):
        res = super(resource_timetracking, self).read(fields=fields, load=load)
        if 'timesheet_id' in self.env.context:
            ts = self.env['resource.timesheet'].browse(self.env.context['timesheet_id'])
            date_from = self.env.context.get('date_from', ts.date_from)
            date_to = self.env.context.get('date_to', ts.date_to)
            for tt in res:
                if tt['start_date'] < date_from or tt['end_date'] > date_to:
                    tt['time'] = self.get_time_for_period(tt, date_from, date_to, ts.resource_id.calendar_id.id)
        return res
    
    def get_time_for_period(self, tt, date_from, date_to, calendar_id):
        #===============================================================================================================
        # 
        #===============================================================================================================
        track_date_start = tt['start_date']
        track_date_end = tt['end_date']
        track_hours = tt['time']
        calendar_line_obj = self.env['calendar.line']
        total_input_hours = 0
        #Si date de début et de fin de la ligne sont comprise entre date de début et de fin timesheet on ajoute le temps de la ligne
        if date_from <= track_date_start <= date_to and date_from <= track_date_end <= date_to:
            total_input_hours += track_hours
        else:
            #Sinon on fait le prorata de la quantité d'heures travaillées sur la timesheet par rapport au nombre de jours travaillés
            #de la timesheet et le nombre de jours total de la ligne 
            total_length_day = sum([x.get_availability_start(track_date_start) for x in calendar_line_obj.search([('real_end_date', '>=', track_date_start), 
                                                         ('real_start_date', '<=', track_date_end), 
                                                         ('calendar_id', '=', calendar_id)])])
            if total_length_day > 0:
                comp_date_start = track_date_start
                comp_date_end = track_date_end
                if track_date_start < date_from:
                    comp_date_start = date_from
                
                if comp_date_end > date_to:
                    comp_date_end = date_to
                
#                 timesheet_length_day = len(calendar_line_obj.search([('real_end_date', '>=', comp_date_start), 
#                                                                  ('real_start_date', '<=', comp_date_end), 
#                                                                  ('calendar_id', '=', calendar_id)]))
                timesheet_length_day = sum([x.get_availability_start(track_date_start) for x in calendar_line_obj.search([('real_end_date', '>=', comp_date_start), 
                                                                  ('real_start_date', '<=', comp_date_end), 
                                                                  ('calendar_id', '=', calendar_id)])])
                total_input_hours += (track_hours*(timesheet_length_day/float(total_length_day)))
        return total_input_hours
    