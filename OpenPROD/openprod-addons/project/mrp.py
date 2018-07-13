# coding: utf-8

from openerp import models, fields, api
from math import ceil

class mrp_workorder(models.Model):
    _inherit = 'mrp.workorder'
    
    task_id = fields.Many2one('project.phase', required=False, ondelete='set null')
    
    @api.multi
    def write(self, vals):
        res = super(mrp_workorder, self).write(vals)
        for wo in self:
            if not wo.task_id:
                return res
            insert = {}
            if 'planned_start_date' in vals:
                insert.update({'start_date':vals['planned_start_date'], 'end_date':wo.planned_end_date})
            if len(insert):
                wo.task_id.write(insert, no_wo_update=True)
        return res
    
    @api.multi
    def unlink(self):
        for wo in self:
            wo.task_id.unlink()
        super(mrp_workorder, self).unlink()
    

class mrp_manufacturingorder(models.Model):
    _inherit = 'mrp.manufacturingorder'
    
    task_id = fields.Many2one('project.phase', required=False, ondelete='set null')
    
    @api.multi
    def create_task(self, next_id=None, parent_id=None, propagate=False):
        if isinstance(next_id, int):
            next_id = [(4, next_id, 0)]
        for mo in self:
            if mo.task_id:
                break
            vals = {
                        'name':mo.name,
                        'start_date':mo.planned_start_date,
                        'user_id':self.env.uid,
                        'next_ids':next_id,
                        'sequence':mo.product_id.bom_level * 10,
            }
            if parent_id:
                vals['parent_id'] = parent_id.id
            if mo._columns.has_key('affair_id') and mo.affair_id:
                vals['affair_id'] = mo.affair_id.id
            mo_task_id = self.env['project.phase'].create(vals)
            mo.write({'task_id':mo_task_id.id})
            old_task_id = None
            
            sub_mo_ids = []
            for wo in mo.workorder_ids:
                vals = {
                            'name': '[%d] %s' % (wo.sequence, wo.name),
                            'start_date':wo.planned_start_date,
                            'user_id':self.env.uid,
                            'end_date':wo.planned_end_date,
                            'parent_id':mo_task_id.id,
                            'charge':wo.total_time_theo,
                            'sequence':wo.sequence,
                }
                if wo.first_resource_id:
                    vals['resource_id'] = wo.first_resource_id.id
                    
                if mo._columns.has_key('affair_id') and mo.affair_id:
                    vals['affair_id'] = mo.affair_id.id
                wo_task_id = self.env['project.phase'].create(vals)
                if old_task_id:
                    old_task_id.write({'next_ids':[(4, wo_task_id.id, 0)]})
                wo.write({'task_id':wo_task_id.id})
                old_task_id = wo_task_id
                
                if propagate:
                    sub_mo_ids += [p.mo_id.id for p in wo.procurement_ids if p.mo_id.id]
                
            if propagate:
                sub_mo_ids = self.browse(sub_mo_ids)
                for sub_mo_id in sub_mo_ids:
                    sub_mo_id.create_task(next_id=mo_task_id.id, propagate=propagate, parent_id=parent_id)
        return True
    
    @api.multi
    def unlink(self):
        for mo in self:
            mo.task_id.unlink()
        super(mrp_manufacturingorder, self).unlink()
        