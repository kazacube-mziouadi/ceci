# -*- coding: utf-8 -*-
from openerp import models, api, fields, _

class oa_course(models.Model):
    """ 
    Course 
    """
    _name = 'oa.course'
    _description = 'Course'
    _sql_constraints = [
        ('name_unique', 'unique(name)', 'Error! Course name must be unique.'),
    ]

    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    description = fields.Text()
    responsible_id = fields.Many2one('res.users', string='Responsible', required=True, ondelete='restrict')
    session_ids = fields.One2many('oa.session', 'course_id',  string='Sessions')
    
    
    @api.one
    @api.constrains('name', 'description')
    def _check_function(self):
        if self.name == self.description:
            raise Warning(_('Name cannot be equals to description'))
        
    
    @api.multi
    def copy(self, default=None):
        """
            Copie des lignes de ventes
        """
        if not default:
            default = {}
        
        default['name'] = 'Copy of %s'%('name' in default and default['name'] or self.name)
        return super(oa_course, self).copy(default=default)
    
    
    
class oa_attendee(models.Model):
    """ 
    Attendee 
    """
    _name = 'oa.attendee'
    _description = 'Attendee'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    session_id = fields.Many2one('oa.session', string='Session', required=False, ondelete='restrict')
    partner_id = fields.Many2one('res.partner', string='Partner', required=False, ondelete='restrict')
    
    
    
class oa_session(models.Model):
    """ 
    Session 
    """
    _name = 'oa.session'
    _description = 'Session'
    
    @api.one
    @api.depends('attendee_ids')
    def _compute_attendee_nb(self):
        self.attendee_nb = len(self.attendee_ids)
            

    @api.one
    @api.depends('attendee_ids', 'seats')
    def _compute_remaining_seats(self):
        self.remaining_seats = self.seats and (float(self.seats) - self.attendee_nb) / self.seats * 100.0 or 100
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    start_date = fields.Date(default=fields.Date.today())    
    duration = fields.Float(default=0.0, required=False)
    seats = fields.Integer(default=0, required=False)
    course_id = fields.Many2one('oa.course', string='Course', required=True, ondelete='restrict')
    active = fields.Boolean(default=True)
    attendee_ids = fields.One2many('oa.attendee', 'session_id',  string='Attendees')
    attendee_nb = fields.Integer(string='Attendee Nb', compute='_compute_attendee_nb')
    remaining_seats = fields.Float(compute='_compute_remaining_seats')
    instructor_id = fields.Many2one('res.partner', string='Instructor', required=False, ondelete='restrict', domain=[('is_instructor', '=', True),
                                                                                                                    ('is_supplier', '=', True)])

