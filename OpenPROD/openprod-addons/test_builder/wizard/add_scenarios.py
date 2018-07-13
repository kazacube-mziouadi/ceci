# coding: utf-8

from openerp import models, api, fields

class add_scenarios(models.TransientModel):
    """ 
    Add multiple scenarios at once to a batch 
    """
    _name = 'add.scenarios'
    _description = 'Add multiple scenarios at once to a batch'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    batch_id = fields.Many2one('batch', string='Batch', required=True, ondelete='cascade')
    scenario_ids = fields.Many2many('scenario', string='string')
    
    @api.multi
    def add_scenarios(self):
        self.batch_id.write({
                             'scenario_ids': [(0, 0, {'scenario_id':x.id, 'sequence':-1}) for x in self.scenario_ids]
                             })