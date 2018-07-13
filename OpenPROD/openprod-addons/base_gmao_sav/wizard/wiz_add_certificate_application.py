# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError

class wiz_add_certificate_application(models.TransientModel):
    """ 
        Wiz add certificate application
    """
    _inherit = 'wiz.add.certificate.application'
    
    
    @api.model
    def _type_get(self):
        res = super(wiz_add_certificate_application, self)._type_get()
        res.append(('park', _('Park')))
        res.append(('equipment', _('Equipment')))
        return res
    
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    park_ids = fields.Many2many('park', 'park_wiz_aca_rel', 'waca_id', 
                                'park_id', string='Resources')
    equipment_ids = fields.Many2many('park', 'equipment_wiz_aca_rel', 'waca_id', 
                                     'equipment_id', string='Customers')
    
    #===========================================================================
    # BUTTON
    #===========================================================================
    def prepa_create_line(self):
        """
            Préparation création certificat d'application
        """
        list_vals = super(wiz_add_certificate_application, self).prepa_create_line()
        if self.type == 'park' and self.park_ids:
            for park in self.park_ids:
                list_vals.append({'park_id': park.id, 'certicate_template_id': self.certicate_template_id.id, 'name': park.name})
                
        elif self.type == 'equipment' and self.equipment_ids:
            for equipment in self.equipment_ids:
                list_vals.append({'equipment_id': equipment.id, 'certicate_template_id': self.certicate_template_id.id, 'name': equipment.name})
        
        return list_vals
        
        