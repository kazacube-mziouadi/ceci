# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _


class calendar_event(models.Model):
    _inherit = 'calendar.event'
    
    
    def get_default_values(self):
        res = super(calendar_event, self).get_default_values()
        if self.env.context.get('active_model', '') == 'purchase.order' and self.env.context.get('active_id', ''):
            res.update(self.env['purchase.order'].browse(self.env.context['active_id']).get_purchase_action_vals())
            
        return res


    @api.model
    def _link_object_get(self):
        res = super(calendar_event, self)._link_object_get()
        res.append(('purchase', _('Purchase')))
        return res
    
    
    @api.one
    def _compute_linked_objects(self):
        """
            Surcharge pour permettre de calculer le champ fonction sélection si
            une affaire est saisie
        """
        super(calendar_event, self)._compute_linked_objects()
        if self.purchase_id:
            self.link_object = 'purchase'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    purchase_id = fields.Many2one('purchase.order', string='Purchase', required=False, ondelete='restrict')

    
    def fields_to_check(self):
        """
            Surcharge de la liste pour vérifier ce champ
        """
        fields_list = super(calendar_event, self).fields_to_check()
        fields_list.append('purchase_id')
        return fields_list
    
    
    @api.onchange('purchase_id')
    def _onchange_purchase_id(self):
        """
            On passe le champ fonction à la bonne valeur pour gérer les attrs
        """
        if self.purchase_id:
            self.link_object = 'purchase'
        else:
            self.link_object = 'none'
