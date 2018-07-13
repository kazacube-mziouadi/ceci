# -*- coding: utf-8 -*-
from openerp import models, fields, api, tools, _

class wizard_create_timetracking(models.TransientModel):
    _inherit = 'wizard.create.timetracking'
    
    def find_resource_rcs(self, context):
        """
            Fonction qui permet de récupérer la ressource
        """
        resource_rcs = super(wizard_create_timetracking, self).find_resource_rcs(context=context)
        if not resource_rcs:
            if context.get('active_model') == 'resource.timesheet' and context.get('active_id', False):
                resource_rcs = self.env['resource.timesheet'].browse(context['active_id']).resource_id
        
        return resource_rcs