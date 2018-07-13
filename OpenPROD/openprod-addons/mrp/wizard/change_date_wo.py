# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
import time, datetime
import openerp.addons.decimal_precision as dp

class change_date_wo(models.TransientModel):
    """ 
        Changer la date d'un OT
    """
    _name = 'change.date.wo'
    _description = 'Change Date Wo'
    
    @api.model
    def default_get(self, fields_list):
        res = super(change_date_wo, self).default_get(fields_list=fields_list)
        wo_obj = self.env['mrp.workorder']
        #Fonction permettant de passer par défaut l'id de l'OT ouvert
        wo = wo_obj.browse(self._context.get('active_id'))
        vals = {
            'wo_id': wo.id,
        }
        
        res.update(vals)
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
        
    wo_id = fields.Many2one('mrp.workorder', string='Workorder', required=False, ondelete='cascade')
    date = fields.Datetime(string='Date', required=True)
    
    
    #===========================================================================
    # Bouton
    #===========================================================================
    @api.multi
    def action_validation(self):
        """
            Bouton de validation
        """
        for wiz in self:
            # TODO migrer le test dans une méthode mrp_workorder/change_date()
            if wiz.wo_id.is_at_earlier:
                wiz.wo_id.action_plannification_wo_at_earlier(wiz.date, automatic_purchase=False, is_procur_level_manufact=False, is_procur_level_purchase=False, no_modif_prio_date=False)
            else:
                wiz.wo_id.action_plannification_wo_at_the_latest(wiz.date, automatic_purchase=False, is_procur_level_manufact=False, is_procur_level_purchase=False, no_modif_prio_date=False)
                
        return True


    