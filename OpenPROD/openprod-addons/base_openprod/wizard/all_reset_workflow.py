# -*- coding: utf-8 -*-
from openerp import models, fields, api, tools, _
from datetime import datetime, timedelta
from openerp.addons.base_openprod.common import get_form_view

class all_reset_workflow(models.TransientModel):
    """ 
        Reinitialiser le workflow pour plusieurs enregistrements
    """
    _name = 'all.reset.workflow'
    _description = 'Reinitialiser le workflow pour plusieurs enregistrements'
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(all_reset_workflow, self).default_get(fields_list=fields_list)
        #Fonction permettant de passer par défaut l'id de l'OT ouvert
        vals = {
            'list_ids': self._context.get('active_ids'),
            'name': self._context.get('active_model'),
            'nb_recording': len(self._context.get('active_ids')),
        }
        
        res.update(vals)
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    list_ids = fields.Text(string='List ids')
    name = fields.Char(string='Model', size=256, required=False)
    nb_recording = fields.Integer(string='Number recording', default=0, readonly=True)
    

    @api.multi
    def button_reset_workflow(self):
        for wiz in self:
            if wiz.list_ids and wiz.name:
                rcs_ids = [int(x) for x in wiz.list_ids.split(',')]
                self.env[wiz.name].browse(rcs_ids).reset_workflow()