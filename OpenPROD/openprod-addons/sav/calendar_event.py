# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _


class calendar_event(models.Model):
    _inherit = 'calendar.event'
    
    
    @api.model
    def _link_object_get(self):
        res = super(calendar_event, self)._link_object_get()
        res += [('crm_reclaim', _('CRM reclaim'))]
        return res
    
    
    @api.one
    def _compute_linked_objects(self):
        """
            Surcharge pour permettre de calculer le champ fonction sélection si
            un crm_reclaim est saisi
        """
        super(calendar_event, self)._compute_linked_objects()
        if self.workorder_id:
            self.link_object = 'crm_reclaim'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    crm_reclaim_id = fields.Many2one('crm.reclaim', string='CRM reclaim', required=False, ondelete='restrict')

    
    def fields_to_check(self):
        """
            Surcharge de la liste pour vérifier ce champ
        """
        fields_list = super(calendar_event, self).fields_to_check()
        fields_list += ['crm_reclaim_id']
        return fields_list
    
    
    @api.onchange('workorder_id')
    def _onchange_workorder(self):
        """
            On passe le champ fonction à la bonne valeur pour gérer les attrs
        """
        if self.workorder_id:
            self.link_object = 'crm_reclaim'
        else:
            self.link_object = 'none'
    