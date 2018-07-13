# -*- coding: utf-8 -*-
from openerp import models, fields, api

class picking_update_covers(models.TransientModel):
    """ 
    Picking update covers 
    """
    _name = 'picking.update.covers'
    _description = 'Picking update covers'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    @api.multi
    def update(self):
        return self.env['stock.picking'].browse(self.env.context.get('active_ids')).update_covers()