# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
from openerp.exceptions import except_orm,Warning
import re


email_re = re.compile(r"""(([a-zA-Z\w][\w\.-]*[a-zA-Z0-9]|[0-9]+)@[a-zA-Z0-9][\w\.-]*\.[a-z]{2,3})""", re.VERBOSE)
class multi_communication_type(models.Model):
    """ 
    Type for multi communications 
    """
    _name = 'multi.communication.type'
    _description = 'Type for multi communications'
    
    @api.model
    def _communication_type_get(self):
        return [
                ('phone', _('Phone')),
                ('mobile', _('Mobile')),
                ('email', _('Email')),
                ('fax', _('Fax')),
                ('webp', _('Web portal')),
                ('other', _('Other')),
                       ]
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True, translate=True)
    type = fields.Selection('_communication_type_get', string='Type', required=False)
    
    

class multi_communication(models.Model):
    """ 
    Multiple communications object 
    """
    _name = 'multi.communication'
    _description = 'Multiple communications object'
    _order = 'sequence'
    
    
    @api.one
    @api.depends('sequence', 'partner_id', 'communication_type_id', 'international', 'indicative', 'number', 'intern', 'value', 'login', 'password')
    def _compute_communication_name(self):
        #Fonction permettant d'afficher la valeur de la communication choisie à partir des données entrées
        num = ''
        if self.type == 'phone' or self.type == 'mobile' or self.type == 'fax':
            if self.number:
                #On formate le numéro en ajoutant des espaces tous les 2 numéros
                x = 0
                for i in self.number:
                    try:
                        int(i)
                    except ValueError:
                        continue
                    
                    x += 1
                    if x % 2:
                        num += ' %s'%(i)
                    else:
                        num += '%s'%(i)
                        
                if self.intern:
                    self.name = '+%d %d %s int %d'%(self.international,self.indicative,num,self.intern)
                else:
                    self.name = '+%d %d %s'%(self.international,self.indicative,num)
            
        elif self.type=='email' or not self.type:
            self.name = self.value
        
        elif self.type=='webp' or not self.type:
            self.name = '%s %s/%s'%(self.value, self.login, self.password)
    
    
    @api.model
    def _type_get(self):
        return [
                ('phone', _('Phone')),
                ('mobile', _('Mobile')),
                ('email', _('Email')),
                ('fax', _('Fax')),
                ('webp', _('Web portal')),
                ('other', _('Other')),
                       ]
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Name', size=130, required=False, compute='_compute_communication_name')
    sequence = fields.Integer(string='Sequence', default=1, required=True)
    partner_id = fields.Many2one('res.partner', string='Partner', required=False, ondelete='cascade')
    communication_type_id = fields.Many2one('multi.communication.type', string='Type', required=True, ondelete='restrict')
    type = fields.Selection('_type_get', string='Type')
    international = fields.Integer(string='International', default=0, required=False, help='Country number. '
                                   'For example: 33 for the France')
    indicative = fields.Integer(string='Indicative', default=0, required=False, help='Number of the region. '
                                'For example: In France, 4 for the southwest, 6 for mobile')
    number = fields.Char(string='Number', size=12, required=False, help='Phone number. Example: 8 digits '
                         'for the France')
    intern = fields.Integer(string='Intern', default=0, required=False, help='Post number to call '
                            '(never fill for FAX)')
    value = fields.Char(string='Value', size=130, required=False)
    login = fields.Char(string='Login', size=130, required=False, help='multi_communication.login.help')
    password = fields.Char(string='Password', size=130, required=False, help='multi_communication.password.help')

    
    @api.onchange('communication_type_id')
    def _onchange_type(self):
        """
            Au changement du type de communication, on modifie le type caché afin d'afficher les champs correspondants
        """
        if not self.communication_type_id:
            self.type = ''
        else:
            if self.communication_type_id.type:
                self.type = self.communication_type_id.type
            else:
                self.type = ''
                
                
                
    @api.model
    def create(self, vals):
        """
            Vérification que l'adresse mail soit correcte
        """
        res = super(multi_communication, self).create(vals=vals)
        if res.communication_type_id and res.communication_type_id.type == 'email' and not email_re.match(res.value): 
            raise except_orm(_('Error'), _('The email is not correct %s') % (res.value))
               
        return res            
              
                
    @api.multi
    def write(self, vals=None):
        """
            Vérification que l'adresse mail soit correcte
        """
        if not vals:
            vals = {}
        
        res = super(multi_communication, self).write(vals=vals)     
        for com in self:       
            if com.communication_type_id and com.communication_type_id.type == 'email' and not email_re.match(com.value): 
                raise except_orm(_('Error'), _('The email is not correct %s') % (com.value))       
                
        return res
                
                
                
class res_partner(models.Model):
    _inherit = 'res.partner'
    
    
    def calcul_min_comm(self, type, partner):
        #Fonction permettant de ramener la valeur de la séquence la plus basse pour un type
        #de communication donné
        res = ''
        if type and partner:
            seq = 100000
            for comm in partner.communication_ids:
                if comm.type:
                    if comm.type == type and comm.sequence <= seq:
                        seq = comm.sequence
                        res = comm.name
                    
        return res
    
    @api.one
    @api.depends('communication_ids')
    def _compute_communication_fields(self):
        #Fonction permettant de récupérer les numéros de téléphone, portable...
        #des lignes ayant la séquence la plus basse
        self.phone = self.calcul_min_comm('phone', self)
        self.mobile = self.calcul_min_comm('mobile', self)
        self.email = self.calcul_min_comm('email', self)
        self.fax = self.calcul_min_comm('fax', self)
        self.webp = self.calcul_min_comm('webp', self)
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    phone = fields.Char(string='Phone', size=130, required=False, compute='_compute_communication_fields', store=True)
    mobile = fields.Char(string='Mobile', size=130, required=False, compute='_compute_communication_fields', store=True)
    email = fields.Char(string='Email', size=128, required=False, compute='_compute_communication_fields', store=True)
    fax = fields.Char(string='Fax', size=130, required=False, compute='_compute_communication_fields', store=True)
    webp = fields.Char(string='Web portal', size=130, required=False, compute='_compute_communication_fields', store=True)
    communication_ids = fields.One2many('multi.communication', 'partner_id',  string='Communications')
