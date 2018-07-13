# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
import openerp.addons.decimal_precision as dp

        
class mrp_planning_mo_at_the_latest(models.TransientModel):
    """ 
        ManufacturingOrder Planning at the latest
    """
    _inherit = 'mrp.planning.mo.at.the.latest'
    
    
    @api.one
    @api.depends('mo_id')
    def _compute_is_intervention(self):
        """
            Fonction qui calcule is_intervention
        """
        if self.mo_id and self.mo_id.intervention_id:
            is_intervention = True
        else:
            is_intervention = False
        
        self.is_intervention = is_intervention
        
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    is_intervention = fields.Boolean(string='Intervention', compute='_compute_is_intervention')
    
