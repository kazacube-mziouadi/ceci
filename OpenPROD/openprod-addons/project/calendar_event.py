# coding: utf-8

from openerp import models, fields, api

class calendar_event(models.Model):
    _inherit = 'calendar.event'
    
    task_id = fields.Many2one('project.phase', required=False, ondelete='set null')
    
    @api.multi
    def create_task(self, parent_id=None):
        for act in self:
            vals = {
                        'name':act.name,
                        'start_date':act.start_datetime,
                        'user_id':self.env.uid,
                        'charge':act.duration,
            }
            if parent_id:
                vals['parent_id'] = parent_id.id
            task_id = self.env['project.phase'].create(vals)
            act.write({'task_id':task_id.id})
        return True
    
    @api.multi
    def unlink(self, can_be_deleted=True):
        for ce in self:
            ce.task_id.unlink()
        super(calendar_event, self).unlink(can_be_deleted)