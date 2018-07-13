# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.addons.base_openprod.common import get_form_view

    

class calendar_event(models.Model):
    _inherit = 'calendar.event'
    

    @api.model
    def _link_object_get(self):
        res = super(calendar_event, self)._link_object_get()
        res.append(('nonconformity_file', _('Nonconformity File')))
        return res
    
    
    @api.one
    def _compute_linked_objects(self):
        """
            Surcharge pour permettre de calculer le champ fonction sélection si
            une fiche de non conformité est saisie
        """
        super(calendar_event, self)._compute_linked_objects()
        if self.nonconformity_file_id:
            self.link_object = 'nonconformity_file'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    nonconformity_file_id = fields.Many2one('nonconformity.file', string='Nonconformity File', required=False, ondelete='restrict')
    
    
    def no_recurrency_list(self):
        """
            Surcharge de la liste pour indiquer que l'on ne peut pas lier un événement 
            récurrent à la fiche de non conformité
        """
        field_list = super(calendar_event, self).no_recurrency_list()
        field_list.append('nonconformity_file_id')
        return field_list
    
    
    def fields_to_check(self):
        """
            Surcharge de la liste pour vérifier ce champ
        """
        fields_list = super(calendar_event, self).fields_to_check()
        fields_list.append('nonconformity_file_id')
        return fields_list
    
    
    @api.onchange('nonconformity_file_id')
    def _onchange_nonconformity_file_id(self):
        """
            On passe le champ fonction à la bonne valeur pour gérer les attrs
        """
        if self.nonconformity_file_id:
            self.link_object = 'nonconformity_file'
        else:
            self.link_object = 'none'
    