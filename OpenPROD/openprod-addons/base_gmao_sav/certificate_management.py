# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.translate import _
from datetime import datetime, timedelta

class certificate_template(models.Model):
    """ 
        Certificate template 
    """
    _inherit = 'certificate.template'

    
    @api.model
    def _type_get(self):
        res = super(certificate_template, self)._type_get()
        res.append(('park', _('Park')))
        res.append(('equipment', _('Equipment')))
        return res

    
    
    def fonction_list_ids_text(self, type):
        res = super(certificate_template, self).fonction_list_ids_text(type)
        list_ids = []
        for line in self.line_application_ids:
            if type == 'park' and line.park_id:
                list_ids.append(line.park_id.id)
            elif type == 'equipment' and line.equipment_id:
                list_ids.append(line.equipment_id.id)
        
        if list_ids:
            res = str(list_ids)
        
        return res
    
    

class certificate_line(models.Model):
    """ 
        Certificate line
    """
    _inherit = 'certificate.line'
    
    
    @api.model
    def _type_get(self):
        res = super(certificate_template, self)._type_get()
        res.append(('park', _('Park')))
        res.append(('equipment', _('Equipment')))
        return res
        
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    park_id = fields.Many2one('park', string='Park', required=False, ondelete='restrict')
    equipment_id = fields.Many2one('park', string='Equipment', required=False, ondelete='restrict')
    
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('type', 'resource_id', 'customer_id', 'supplier_id', 'ref_customer_id', 'ref_supplier_id', 'park_id', 'equipment_id')
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
        elif self.type == 'park':
            name = self.park_id and self.park_id.name or False
        elif self.type == 'equipment':
            name = self.equipment_id and self.equipment_id.name or False
        
        self.name = name
    
    
    #===========================================================================
    # Fonction
    #===========================================================================
    def args_search_modif_expiry_date(self):
        """
            On prépare les arguments pour le search des applications, on regarde sur quelle objet pointe le certificat
        """
        args_search = super(certificate_line, self).args_search_modif_expiry_date()
        if self.type == 'park' and self.park_id:
            args_search = [('park_id', '=', self.park_id.id)]
        elif self.type == 'equipment' and self.equipment_id:
            args_search = [('equipment_id', '=', self.equipment_id.id)]
        
        return args_search



class certificate_line_application(models.Model):
    """ 
        Certificate line application
    """
    _inherit = 'certificate.line.application'
    
    
    @api.model
    def _type_get(self):
        res = super(certificate_template, self)._type_get()
        res.append(('park', _('Park')))
        res.append(('equipment', _('Equipment')))
        return res
    
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    park_id = fields.Many2one('park', string='Park', required=False, ondelete='restrict')
    equipment_id = fields.Many2one('park', string='Equipment', required=False, ondelete='restrict')
    
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('type', 'resource_id', 'customer_id', 'supplier_id', 'ref_customer_id', 'ref_supplier_id', 'park_id', 'equipment_id')
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
        elif self.type == 'park':
            name = self.park_id and self.park_id.name or False
        elif self.type == 'equipment':
            name = self.equipment_id and self.equipment_id.name or False
        
        self.name = name
    
    
    def args_search_modif_expiry_date(self):
        """
            On prépare les arguments pour le search des applications, on regarde sur quelle objet pointe l'application
        """
        args_search = super(certificate_line_application, self).args_search_modif_expiry_date()
        if self.type == 'park' and self.park_id:
            args_search = [('park_id', '=', self.park_id.id)]
        elif self.type == 'equipment' and self.equipment_id:
            args_search = [('equipment_id', '=', self.equipment_id.id)]
        
        return args_search

    