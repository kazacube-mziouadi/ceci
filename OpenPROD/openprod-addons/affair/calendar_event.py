# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _


class calendar_event(models.Model):
    _inherit = 'calendar.event'
    
    @api.model
    def _link_object_get(self):
        res = super(calendar_event, self)._link_object_get()
        res.append(('affair', _('Affair')))
        return res
    
    
    @api.one
    def _compute_linked_objects(self):
        """
            Surcharge pour permettre de calculer le champ fonction sélection si
            une affaire est saisie
        """
        super(calendar_event, self)._compute_linked_objects()
        if self.affair_id:
            self.link_object = 'affair'
                
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    affair_id = fields.Many2one('affair', string='Affair', required=False, ondelete='restrict')

    
    def no_recurrency_list(self):
        """
            Surcharge de la liste pour indiquer que l'on ne peut pas lier un événement 
            récurrent à une affaire
        """
        field_list = super(calendar_event, self).no_recurrency_list()
        field_list.append('affair_id')
        return field_list
    
    
    def fields_to_check(self):
        """
            Surcharge de la liste pour vérifier ce champ
        """
        fields_list = super(calendar_event, self).fields_to_check()
        fields_list.append('affair_id')
        return fields_list
    
    
    @api.onchange('affair_id')
    def _onchange_affair_id(self):
        """
            On passe le champ fonction à la bonne valeur pour gérer les attrs
        """
        if self.affair_id:
            self.link_object = 'affair'
        else:
            self.link_object = 'none'
    