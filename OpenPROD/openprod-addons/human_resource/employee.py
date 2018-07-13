# -*- coding: utf-8 -*-
from openerp import models, api, fields, _
from openerp.exceptions import except_orm
from openerp.addons.base_openprod.common import get_form_view
from dateutil.relativedelta import relativedelta
from datetime import datetime


class employee(models.Model):
    """ 
    Employee 
    """
    _name = 'employee'
    _description = 'Employee'
    
    
    @api.multi
    @api.depends('name')
    def name_get(self):
        """
            On affiche prenom nom
        """
        result = []
        for employee_rcs in self:
            name = '%s %s'%(employee_rcs.first_name, employee_rcs.name)
            result.append((employee_rcs.id, name))
             
        return result
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=1000):
        """
            Fonction name_search
        """
        recs = self.search(['|', ('name', operator, name), ('first_name', 'ilike', name)] + args, limit=limit)
        return recs.name_get()

    
    @api.model
    def _state_get(self):
        return [
                ('future', _('Future')),
                ('active', _('Active')),
                ('old', _('Old')),
                       ]


    @api.one
    def _get_picture_binary_filesystem(self):
        attachment_obj = self.env['ir.attachment']
        attachment_rs = attachment_obj.search([('res_model','=',self._name),('res_id','=',self.id),('binary_field','=','picture')])
        if attachment_rs:
            self['picture'] = attachment_rs[0].datas

    
    @api.one
    def _set_picture_binary_filesystem(self):
        attachment_obj = self.env['ir.attachment']
        attachment_rs = attachment_obj.search([('res_model','=',self._name),('res_id','=',self.id),('binary_field','=','picture'),('is_binary_field','=',True)])
        if self.picture:
            if attachment_rs:
                attachment_rs.datas = self.picture
            else:
                attachment_obj.create({'res_model': self._name, 'res_id': self.id, 'name': 'picture datas' , 'is_binary_field': True, 'binary_field': 'picture', 'datas': self.picture, 'datas_fname':'picture datas'})
        else:
            attachment_rs.unlink()
    
    
    @api.model
    def _family_situation_get(self):
        return [
                ('single', _('Single')),
                ('married', _('Married')),
                ('divorced', _('Divorced')),
                ('widowed', _('Widowed')),
                       ]

    
    @api.model
    def _type_sex_get(self):
        return [
                ('female', _('Female')),
                ('male', _('Male')),
                       ]
    @api.one
    @api.depends('birth_date')
    def _compute_age(self):
        age = 0
        if self.birth_date:
            age= relativedelta(datetime.now(), datetime.strptime(self.birth_date, "%Y-%m-%d")).years
            
        self.age = age
        
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    # Entete
    name = fields.Char(required=True, size=256)
    state = fields.Selection('_state_get', string='State', default='future',  required=True)
    first_name = fields.Char(string="First name", required=True, size=256)
    resource_id = fields.Many2one('mrp.resource', string='Resource', required=False, ondelete='restrict')
    account_id = fields.Many2one('account.account', string='Account', required=True, ondelete='restrict')
    company_id = fields.Many2one('res.company', string='Company', required=True, ondelete='restrict', default=lambda self: self.env.user.company_id)
    picture  = fields.Binary(string='Picture', compute='_get_picture_binary_filesystem', inverse='_set_picture_binary_filesystem', help='help')
    is_responsible = fields.Boolean(string='Responsible', default=False)
    calendar_id = fields.Many2one('calendar', string='Calendar', required=True, ondelete='restrict', help='Come from the selected resource or manually selected')
    category_id = fields.Many2one('employee.category', string='Category', required=True, ondelete='restrict')
    # Information personnelle
    address_id = fields.Many2one('address', string='Address', required=True, ondelete='restrict')
    age  = fields.Integer(string='Age', compute='_compute_age')
    nationality_id = fields.Many2one('res.country', string='Nationality', required=False, ondelete='restrict')
    civility_id = fields.Many2one('res.partner.title', string='Civility', required=False, ondelete='restrict')
    phone = fields.Char(string='Phone', size=20, required=False)
    email = fields.Char(string='Email', size=128, required=False)
    identity_number = fields.Char(string='Identity number', size=128, required=False)
    passport_number = fields.Char(string='Passport number', size=128, required=False)
    birth_date = fields.Date(string='Birth date')
    account_bank_id = fields.Many2one('res.partner.bank', string='Account bank', required=False, ondelete='restrict')
    place_birth = fields.Char(string='Place of birth', size=256, required=False)
    contact_name = fields.Char(string='Contact name', size=256, required=False)
    relationship_contact = fields.Char(string='Relationship with the contact', size=256, required=False)
    contact_phone = fields.Char(string='Contact phone', size=20, required=False)
    specific_note_contact = fields.Text(string='Specific note contact')
    family_situation = fields.Selection('_family_situation_get', string='Family situation')
    type_sex = fields.Selection('_type_sex_get', string='Type of sex')
    children_ids = fields.One2many('employee.children', 'employee_id',  string='Children')
    # Information RH
    entry_date = fields.Date(string='Entry date')
    release_date = fields.Date(string='Release date')
    employee_number = fields.Char(string='Employee number', size=256, required=False)
    degree_id = fields.Many2one('employee.degree', string='Degree', required=False, ondelete='restrict')
    office_id = fields.Many2one('employee.office', string='Office', required=False, ondelete='restrict')
    responsible_id = fields.Many2one('employee', string='Responsible', required=False, ondelete='restrict', domain=[('is_responsible', '=', True)])
    service_id = fields.Many2one('employee.service', string='Service', required=False, ondelete='restrict')
    note_hr = fields.Text(string='Note HR')
    avg_hour = fields.Float(string='Average hours', default=0.0, required=False, 
                            help="The average work hours of the employee (used to help for input the holidays )")
    
    #===========================================================================
    # Contraintes
    #===========================================================================
    @api.one
    @api.constrains('resource_id', 'calendar_id')
    def _check_calendar_resource(self):
        """
            Si l'employé est lié à une resource, son calendrier doit être le même
            que celui de la ressource 
        """
        if self.resource_id:
            if self.calendar_id != self.resource_id.calendar_id:
                raise Warning(_("If your employee is linked to a resource, he must have the same calendar than the resource"))
    
    
    #===========================================================================
    # Onchanges
    #===========================================================================
    @api.onchange('resource_id')
    def _onchange_resource_id(self):
        """
            On ramène le calendrier de la resource sélectionnée
        """
        calendar_id = False
        if self.resource_id:
            calendar_id = self.resource_id.calendar_id and self.resource_id.calendar_id.id or False
            
        self.calendar_id = calendar_id
    
    #===========================================================================
    # Fonction
    #===========================================================================
    @api.model
    def create(self, vals):
        """
            Test pour ne pas avoir deux employés avec la même resource sauf si old
        """
        employee_rcs = super(employee, self).create(vals)
        if employee_rcs.resource_id:
            employee_search_rcs = self.search([('resource_id', '=', employee_rcs.resource_id.id), ('state', '!=', 'old'), ('id', '!=', employee_rcs.id)])
            if employee_search_rcs:
                raise except_orm(_('Error'),
                        _("Employee already using this resource, you must change its status to 'old' before creating a new employee with this resource (%s %s).") % (employee_search_rcs[0].first_name, employee_search_rcs[0].name))
                
        return employee_rcs
    
    
    @api.multi
    def write(self, vals):
        """
            Test pour ne pas avoir deux employés avec la même resource sauf si old
        """
        for employee_rc in self:
            if vals and 'resource_id' in vals and vals['resource_id'] and (('state' not in vals and employee_rc.state != 'old') or ('state' in vals and vals['state'] != 'old')):
                if len(self.ids) > 1:
                    raise except_orm(_('Error'), _('It is not possible to have more employees with the same resource with different old of state'))
                
                employee_rcs = self.search([('resource_id', '=', vals['resource_id']), ('state', '!=', 'old')])
                if employee_rcs:
                    raise except_orm(_('Error'),
                            _("Employee already using this resource, you must change its status to 'old' before creating a new employee with this resource (%s %s).") % (employee_rcs[0].first_name,employee_rcs[0].name))
            
            elif 'state' in vals and vals['state'] != 'old':
                employee_rcs = self.search([('resource_id', '=', employee_rc.resource_id.id), ('state', '!=', 'old'), ('id', '!=', employee_rc.id)])
                if employee_rcs:
                    raise except_orm(_('Error'),
                            _("Employee already using this resource, you must change its status to 'old' before creating a new employee with this resource (%s %s).") % (employee_rcs[0].first_name,employee_rcs[0].name))
        
        return super(employee, self).write(vals)
    
    
    
class employee_category(models.Model):
    """ 
        Employee's category
    """
    _name = 'employee.category'
    _description = "Employee's category"
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True, size=256)
    employee_ids = fields.One2many('employee', 'category_id',  string='Employees')
    
    
    
class employee_children(models.Model):
    """ 
        Employee children
    """
    _name = 'employee.children'
    _description = 'Employee children'
    
    
    @api.one
    @api.depends('birth_date')
    def _compute_age(self):
        age = 0
        if self.birth_date:
            age= relativedelta(datetime.now(), datetime.strptime(self.birth_date, "%Y-%m-%d")).years
            
        self.age = age
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    employee_id = fields.Many2one('employee', string='Employee', required=False, ondelete='cascade')
    name = fields.Char(required=True, size=256)
    first_name = fields.Char(string="First name", required=True, size=256)
    birth_date = fields.Date(string='Birth date')
    comment = fields.Text(string='Comment')
    age  = fields.Integer(string='Age', compute='_compute_age')


class employee_degree(models.Model):
    """ 
        Employee degree
    """
    _name = 'employee.degree'
    _description = 'Employee degree'
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True, size=256)



class employee_office(models.Model):
    """ 
        Employee office
    """
    _name = 'employee.office'
    _description = 'Employee office'
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True, size=256)
    code = fields.Char(string='Code', size=32, required=True)



class employee_service(models.Model):
    """ 
        Employee service
    """
    _name = 'employee.service'
    _description = 'Employee service'
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True, size=256)
    parent_id = fields.Many2one('employee.service', string='Parent', required=False, ondelete='restrict')
    
    