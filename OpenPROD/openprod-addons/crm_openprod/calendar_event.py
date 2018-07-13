# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.addons.base_openprod.common import get_form_view


class calendar_event(models.Model):
    _inherit = 'calendar.event'
    
    
    @api.model
    def _link_object_get(self):
        res = super(calendar_event, self)._link_object_get()
        res.append(('crm', _('CRM')))
        return res
    
    
    @api.one
    def _compute_linked_objects(self):
        """
            Surcharge pour permettre de calculer le champ fonction sélection si
            une crm est saisie
        """
        super(calendar_event, self)._compute_linked_objects()
        if self.crm_id:
            self.link_object = 'crm'
    
    
    @api.multi
    def create_new_opportunity(self):
        """
            Fonction qui permet de créer une opportunité à partir d'une action
        """
        crm_obj = self.env['crm']
        crm_state_obj = self.env['crm.state']
        data_obj = self.env['ir.model.data']
        for action in self:
            object_model, object_id = data_obj.get_object_reference('crm_openprod', 'crm_state_new')
            if object_model and object_model == 'crm.state':
                state = crm_state_obj.browse(object_id)
                if state:
                    new_opportunity = crm_obj.create({'description': action.description, 
                                                      'criticality': 'normal',
                                                      'state_id': state.id,
                                                      'salesman_id': self.env.user.id})
                    if new_opportunity:
                        action.write({'crm_id': new_opportunity.id})
                        action_dict = get_form_view(self, 'crm_openprod.act_crm_view_only_form')
                        if action_dict and action_dict.get('id') and action_dict.get('type'):
                            action = self.env[action_dict['type']].browse(action_dict['id'])
                            action_struc = action.read()
                            action_struc[0]['res_id'] = new_opportunity.id
                            action_struc = action_struc[0]
                            return action_struc
                
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    crm_id = fields.Many2one('crm', string='CRM', required=False, ondelete='set null')

    
    def no_recurrency_list(self):
        """
            Surcharge de la liste pour indiquer que l'on ne peut pas lier un événement 
            récurrent à la CRM
        """
        field_list = super(calendar_event, self).no_recurrency_list()
        field_list.append('crm_id')
        return field_list
    
    
    def fields_to_check(self):
        """
            Surcharge de la liste pour vérifier ce champ
        """
        fields_list = super(calendar_event, self).fields_to_check()
        fields_list.append('crm_id')
        return fields_list
    
    
    @api.onchange('crm_id')
    def _onchange_crm_id(self):
        """
            On passe le champ fonction à la bonne valeur pour gérer les attrs
        """
        if self.crm_id:
            self.link_object = 'crm'
        else:
            self.link_object = 'none'