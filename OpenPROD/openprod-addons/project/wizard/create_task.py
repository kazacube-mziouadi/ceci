from openerp import models, fields, api

class create_task_wizard(models.TransientModel):
    """ 
    Create task from affair wizard 
    """
    _name = 'create.task.wizard'
    _description = 'Create task from affair wizard'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    event_id = fields.Many2one('calendar.event', required=False, ondelete='cascade')
    mo_id = fields.Many2one('mrp.manufacturingorder', required=False, ondelete='cascade')
    phase_id = fields.Many2one('project.phase', string='Parent task', required=False, ondelete='cascade')
    resource_id = fields.Many2one('mrp.resource', string='Resource', required=False, ondelete='cascade')
    propagate = fields.Boolean(string='Propagate', default=False)
    
    @api.multi
    def create_task(self):
        if self.event_id:
            self.event_id.create_task(parent_id=self.phase_id)
        elif self.mo_id:
            self.mo_id.create_task(parent_id=self.phase_id, propagate=self.propagate)
        else:
            return {'warning':'Nothing to relate'} 