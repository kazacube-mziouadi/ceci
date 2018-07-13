# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import ValidationError

class clock_in_out(models.TransientModel):
    """ 
        Wizard to clock in and/or out
    """
    _name = 'clock.in.out'
    _description = 'Wizard to clock in and/or out'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    date_in = fields.Datetime(string='Date in')
    date_out = fields.Datetime(string='Date out')
    
    @api.multi
    def create_resource_timetracking(self):
        date_in = self.date_in
        date_out = self.date_out
        attendance_list_obj = self.env['attendance.list']
        if date_in and date_out and date_out <= date_in:
            raise ValidationError(_('If you have an in and an out date, the out date must be superior to the in date!'))
        
        resource_id = self.env.user.resource_id and self.env.user.resource_id.id or False
        if resource_id:
            today = fields.Date.today()
            #Recherche de la timesheet de l'utilisateur
            timesheet_id = self.env['resource.timesheet'].search([('resource_id', '=', resource_id),
                                                                  ('date_from', '<=', today),
                                                                  ('date_to', '>=', today)], limit=1).id
            if timesheet_id:
                if date_in:
                    attendance_list_obj._create_attendance_line(date_in, timesheet_id, attendance_type='in')
                    
                if date_out:
                    attendance_list_obj._create_attendance_line(date_out, timesheet_id, attendance_type='out')
                    
        else:
            raise ValidationError(_('There is no resource linked to your user, please select a resource in your user profile!'))
            
        return  {'type': 'ir.actions.act_window_close'}
        
        
