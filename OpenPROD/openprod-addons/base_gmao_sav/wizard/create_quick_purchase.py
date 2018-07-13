# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _

class create_quick_purchase(models.TransientModel):
    """ 
        Wizard to create purchase quickly
    """
    _inherit = 'create.quick.purchase'

    #===========================================================================
    # COLUMNS
    #===========================================================================
    pm_intervention_id = fields.Many2one('piece.maintenance.intervention', string='Intervention', required=False, ondelete='restrict')
    
    
    def write_intervention(self, new_purchase):
        res = super(create_quick_purchase, self).write_intervention(new_purchase)
        if self.pm_intervention_id and new_purchase:
            self.pm_intervention_id.purchase_id = new_purchase.id
            
        return res