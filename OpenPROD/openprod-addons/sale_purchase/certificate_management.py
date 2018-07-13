# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.translate import _
from datetime import datetime, timedelta

class certificate_template(models.Model):
    """ 
        Certificate template 
    """
    _name = 'certificate.template'
    _description = 'Certificate template'

    
    @api.model
    def _type_get(self):
        return [
                ('resource', _('Resource')),
                ('customer', _('Customer')),
                ('ref_customer', _('Ref customer')),
                ('supplier', _('Supplier')),
                ('ref_supplier', _('Ref supplier')),
                       ]

    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('validate', _('Validate')),
                ('cancel', _('Cancel')),
                       ]
    
    @api.one
    def _list_ids_text_compute(self):
        """
            Champ fonction qui permet de stocker la liste des ids de l'objet choisi pour faire un domain et ne pas pouvoir sélectionner un valeur déjà choisie
        """
        self.list_ids_text = self.fonction_list_ids_text(self.type)
    
    
    def fonction_list_ids_text(self, type):
        list_ids_text = '[]'
        list_ids = []
        for line in self.line_application_ids:
            if type == 'resource' and line.resource_id:
                list_ids.append(line.resource_id.id)
            elif type == 'supplier' and line.supplier_id:
                list_ids.append(line.supplier_id.id)
            elif type == 'ref_supplier' and line.ref_supplier_id:
                list_ids.append(line.ref_supplier_id.id)
            elif type == 'customer' and line.customer_id:
                list_ids.append(line.customer_id.id)
            elif type == 'ref_customer' and line.ref_customer_id:
                list_ids.append(line.ref_customer_id.id)
        
        if list_ids:
            list_ids_text = str(list_ids)
        
        return list_ids_text
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    validity_days = fields.Integer(string='Validity in days', required=True)
    type = fields.Selection('_type_get', string='Type', required=True)
    type_text = fields.Char(string='type_text', size=128, required=False)
    state = fields.Selection('_state_get', string='State', default='draft', required=True)
    line_ids = fields.One2many('certificate.line', 'certicate_template_id',  string='Lines')
    line_application_ids = fields.One2many('certificate.line.application', 'certicate_template_id',  string='Lines application')
    list_ids_text = fields.Text(string='List ids text', compute='_list_ids_text_compute')
    
    
    #===========================================================================
    # onchange
    #===========================================================================
    @api.onchange('line_application_ids', 'type', 'line_ids')
    def _onchange_list_ids_text(self):
        """
            Calcul list_ids_text
        """
        if self.type and not self.line_application_ids and not self.line_ids:
            self.type_text = self.type
        elif self.type and (self.line_application_ids or self.line_ids):
            self.type = self.type_text
        
        self.list_ids_text = self.fonction_list_ids_text(self.type)
    
    
    #===========================================================================
    # Bouton
    #===========================================================================
    @api.multi
    def button_add_certif_appli(self):
        for template in self:
            res_rcs = self.env['wiz.add.certificate.application'].create({'certicate_template_id': template.id, 'type': template.type})
            return {'name': _('Add certificate application'),
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'wiz.add.certificate.application',
                        'type': 'ir.actions.act_window',
                        'res_id': res_rcs.id,
                        'target': 'new',
                        'nodestroy': True,
                        }
    
    

class certificate_line(models.Model):
    """ 
        Certificate line
    """
    _name = 'certificate.line'
    _description = 'Certificate line'
    
    
    @api.model
    def _type_get(self):
        return [
                ('resource', _('Resource')),
                ('customer', _('Customer')),
                ('ref_customer', _('Ref customer')),
                ('supplier', _('Supplier')),
                ('ref_supplier', _('Ref supplier')),
                       ]
        
        
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('validate', _('Validate')),
                ('cancel', _('Cancel')),
                       ]

    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Comment', required=True)
    certicate_template_id = fields.Many2one('certificate.template', string='Certificate template', required=True, ondelete='cascade')
    stop_date = fields.Date(string='Stop date', required=True)
    resource_id = fields.Many2one('mrp.resource', string='Resource', required=False, ondelete='restrict')
    customer_id = fields.Many2one('res.partner', string='Customer', required=False, ondelete='restrict')
    supplier_id = fields.Many2one('res.partner', string='Supplier', required=False, ondelete='restrict')
    ref_customer_id = fields.Many2one('product.customerinfo', string='Ref customer', required=False, ondelete='restrict')
    ref_supplier_id = fields.Many2one('product.supplierinfo', string='Ref supplier', required=False, ondelete='restrict')
    document_id = fields.Many2one('document.openprod', string='Document', required=False, ondelete='restrict')
    type = fields.Selection('_type_get', string='Type', related='certicate_template_id.type', store=False)
    state = fields.Selection('_state_get', string='State', default='draft', related='certicate_template_id.state', store=True)
    list_ids_text = fields.Text(string='List ids text', related='certicate_template_id.list_ids_text')
    
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('certicate_template_id', 'certicate_template_id.validity_days', 'type')
    def _onchange_stop_date(self):
        """
            On_change pour calculer la date de fin
        """
        now = fields.date.today()
        if self.certicate_template_id and self.certicate_template_id.validity_days:
            stop_date = fields.Date.to_string(now + timedelta(days=self.certicate_template_id.validity_days))
        else:
            stop_date = fields.Date.to_string(now)
        
        self.stop_date = stop_date
    
    
    @api.onchange('type', 'resource_id', 'customer_id', 'supplier_id', 'ref_customer_id', 'ref_supplier_id')
    def _onchange_name(self):
        """
            On_change du nom 
        """
        name = ''
        if self.type == 'resource':
            name = self.resource_id and self.resource_id.name or False
        elif self.type == 'customer':
            name = self.customer_id and self.customer_id.name or False
        elif self.type == 'supplier':
            name = self.supplier_id and self.supplier_id.name or False
        elif self.type == 'ref_customer':
            name = self.ref_customer_id and self.ref_customer_id.partner_id and self.ref_customer_id.partner_id.name or False
        elif self.type == 'ref_supplier':
            name = self.ref_supplier_id and self.ref_supplier_id.partner_id and self.ref_supplier_id.partner_id.name or False
        
        self.name = name
    
    
    #===========================================================================
    # Fonction
    #===========================================================================
    
    @api.model
    def create(self, vals=None):
        """
            Calcule de la date d'expiration pour les lignes d'applications
        """
        res = super(certificate_line, self).create(vals=vals)
        res.modif_expiry_date_line_application()
        return res
    
    
    @api.multi
    def write(self, vals=None):
        """
            Calcule de la date d'expiration pour les lignes d'applications
        """
        res = super(certificate_line, self).write(vals=vals)
        for certificate in self:
            certificate.modif_expiry_date_line_application()
            
        return res
    
    @api.multi
    def unlink(self):
        """
            Calcule de la date d'expiration pour les lignes d'applications
        """
        for certif in self:
            certif.modif_expiry_date_line_application(is_unlink=True)
            
        res = super(certificate_line, self).unlink()
        return res
    
    
    
    def args_search_modif_expiry_date(self):
        """
            On prépare les arguments pour le search des applications, on regarde sur quelle objet pointe le certificat
        """
        args_search = []
        if self.type == 'resource' and self.resource_id:
            args_search = [('resource_id', '=', self.resource_id.id)]
        elif self.type == 'customer' and self.customer_id:
            args_search = [('customer_id', '=', self.customer_id.id)]
        elif self.type == 'supplier' and self.supplier_id:
            args_search = [('supplier_id', '=', self.supplier_id.id)]
        elif self.type == 'ref_customer' and self.ref_customer_id:
            args_search = [('ref_customer_id', '=', self.ref_customer_id.id)]
        elif self.type == 'ref_supplier' and self.ref_supplier_id:
            args_search = [('ref_supplier_id', '=', self.ref_supplier_id.id)]
        
        return args_search
    
    
    def modif_expiry_date_line_application(self, is_unlink=False):
        """
            On recalcule la date d'expiration pour les lignes d'applications
        """
        args_search = self.args_search_modif_expiry_date()
        if args_search:
            args_search.append(('certicate_template_id', '=', self.certicate_template_id.id))
            # On prépare les arguments pour le search des certificats pour savoir s'il y a des certificats avec une date de fin plus grande
            # Si on est en suppression d'un certificat on cherche un autre certificat pour calculer la date d'expiration 
            line_args_search = args_search[:]
            if not is_unlink:
                line_args_search.append(('stop_date', '>', self.stop_date))
            else:
                line_args_search.append(('id', '!=', self.id))
                
            line_rcs = self.search(line_args_search, order='stop_date desc', limit=1)
            if not line_rcs:
                line_application_rcs = self.env['certificate.line.application'].search(args_search)
                if line_application_rcs:
                    line_application_rcs.write({'expiry_date': self.stop_date})
            elif is_unlink and line_rcs:
                line_application_rcs = self.env['certificate.line.application'].search(args_search)
                if line_application_rcs:
                    line_application_rcs.write({'expiry_date': line_rcs.stop_date})
                
        return True



class certificate_line_application(models.Model):
    """ 
        Certificate line application
    """
    _name = 'certificate.line.application'
    _description = 'Certificate line application'
    
    
    @api.model
    def _status_get(self):
        return [
                ('covered', _('Covered')),
                ('not_covered', _('Not covered')),
                       ]
    
    
    @api.model
    def _type_get(self):
        return [
                ('resource', _('Resource')),
                ('customer', _('Customer')),
                ('ref_customer', _('Ref customer')),
                ('supplier', _('Supplier')),
                ('ref_supplier', _('Ref supplier')),
                       ]
    
    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('validate', _('Validate')),
                ('cancel', _('Cancel')),
                       ]
    
    
    @api.one
    def _status_compute(self):
        """
            Champ fonction status qui couvert s'il y a un certificat avec une date de début et de fin comprise dans le jour
        """
        status = 'not_covered'
        now = fields.date.today()
        if self.expiry_date and self.expiry_date >= fields.Date.to_string(now):
            status = 'covered'
            
        self.status = status
    
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Comment', required=True)
    certicate_template_id = fields.Many2one('certificate.template', string='Certificate template', required=True, ondelete='cascade')
    resource_id = fields.Many2one('mrp.resource', string='Resource', required=False, ondelete='restrict')
    customer_id = fields.Many2one('res.partner', string='Customer', required=False, ondelete='restrict')
    supplier_id = fields.Many2one('res.partner', string='Supplier', required=False, ondelete='restrict')
    ref_customer_id = fields.Many2one('product.customerinfo', string='Ref customer', required=False, ondelete='restrict')
    ref_supplier_id = fields.Many2one('product.supplierinfo', string='Ref supplier', required=False, ondelete='restrict')
    status = fields.Selection('_status_get', string='Status', compute='_status_compute', readonly=True)
    expiry_date = fields.Date(string='Expiry date', readonly=True)
    type = fields.Selection('_type_get', string='Type', related='certicate_template_id.type',readonly=True, store=False)
    state = fields.Selection('_state_get', string='State', default='draft', related='certicate_template_id.state', readonly=True, store=True)
    list_ids_text = fields.Text(string='List ids text', related='certicate_template_id.list_ids_text')
    
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('type', 'resource_id', 'customer_id', 'supplier_id', 'ref_customer_id', 'ref_supplier_id')
    def _onchange_name(self):
        """
            On_change du nom 
        """
        name = ''
        if self.type == 'resource':
            name = self.resource_id and self.resource_id.name or False
        elif self.type == 'customer':
            name = self.customer_id and self.customer_id.name or False
        elif self.type == 'supplier':
            name = self.supplier_id and self.supplier_id.name or False
        elif self.type == 'ref_customer':
            name = self.ref_customer_id and self.ref_customer_id.partner_id and self.ref_customer_id.partner_id.name or False
        elif self.type == 'ref_supplier':
            name = self.ref_supplier_id and self.ref_supplier_id.partner_id and self.ref_supplier_id.partner_id.name or False
        
        self.name = name

    
    @api.model
    def create(self, vals=None):
        """
            Calcule de la date d'expiration pour les lignes d'applications
        """
        res = super(certificate_line_application, self).create(vals=vals)
        res.modif_expiry_date()
        return res
    
    
    @api.multi
    def write(self, vals=None):
        """
            Calcule de la date d'expiration pour les lignes d'applications
        """
        if not vals:
            vals = {}
        
        # Si le write contient expiry_date on ne lance pas la fonction de modif expiry date
        no_compute_expiry_date = True
        if vals and 'expiry_date' in vals:
            no_compute_expiry_date = False
            
        res = super(certificate_line_application, self).write(vals=vals)
        if no_compute_expiry_date:
            for application in self:
                application.modif_expiry_date()
            
        return res
    
    
    def args_search_modif_expiry_date(self):
        """
            On prépare les arguments pour le search des applications, on regarde sur quelle objet pointe l'application
        """
        args_search = []
        if self.type == 'resource' and self.resource_id:
            args_search = [('resource_id', '=', self.resource_id.id)]
        elif self.type == 'customer' and self.customer_id:
            args_search = [('customer_id', '=', self.customer_id.id)]
        elif self.type == 'supplier' and self.supplier_id:
            args_search = [('supplier_id', '=', self.supplier_id.id)]
        elif self.type == 'ref_customer' and self.ref_customer_id:
            args_search = [('ref_customer_id', '=', self.ref_customer_id.id)]
        elif self.type == 'ref_supplier' and self.ref_supplier_id:
            args_search = [('ref_supplier_id', '=', self.ref_supplier_id.id)]
        
        return args_search
    
    
    def modif_expiry_date(self, is_unlink=False):
        """
            On recalcule la date d'expiration pour les lignes d'applications
        """
        args_search = self.args_search_modif_expiry_date()
        if args_search:
            args_search.append(('certicate_template_id', '=', self.certicate_template_id.id))
            certificat_line_rcs = self.env['certificate.line'].search(args_search, order='stop_date desc', limit=1)
            if certificat_line_rcs:
                self.write({'expiry_date': certificat_line_rcs.stop_date})
                
        return True
    
    