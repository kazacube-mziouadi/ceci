# coding: utf-8

from openerp import models, fields, api

class quick_create_project(models.TransientModel):
    """ 
    Quick create wizard for projects 
    """
    _name = 'quick.create.project'
    _description = 'Quick create wizard for projects'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    model_id = fields.Many2one('project.phase', string='Model Project', required=True, ondelete='cascade', domain="[('is_model', '=', True), ('parent_id', '=', None)]")
    start_date = fields.Date(string='Start Date', required=True)
    keep_documents = fields.Boolean(string='Keep Documents', default=True)
    keep_resources = fields.Boolean(string='Keep Resources', default=True)
    
    @api.multi
    def create_project(self):
        additional_vals = self.get_additional_vals()
            
        cal_id = self.env.user.company_id.partner_id.calendar_id
        delta = self.env['calendar.line'].search_count([
                                                  ('calendar_id', '=', cal_id.id),
                                                  ('real_start_date', '>=', self.model_id.start_date),
                                                  ('real_end_date', '<=', self.start_date)
                                                  ])
        
        corresp_phases = {}
        first_phase_id = None
        model_phase_ids = self.env['project.phase'].search(['|', ('id', '=', self.model_id.id), ('id', 'child_of', self.model_id.id)], order="parent_right desc")
        todo_next_ids = {}
        for phase_id in model_phase_ids:
            copy_vals = {
                           'start_date': cal_id.get_date(phase_id.start_date, delta),
                           'parent_id': None,
                           'is_model': False,
                           }
            copy_vals.update(additional_vals)
            if not first_phase_id:
                copy_vals['name'] = self.name
            if self.keep_documents:
                copy_vals['phase_document_ids'] = self.get_copy_documents(phase_id)
            if self.keep_resources:
                copy_vals['resource_id'] = phase_id.resource_id.id
            else:
                copy_vals['resource_id'] = None
            new_phase = phase_id.copy(copy_vals)
            todo_next_ids[new_phase] = (phase_id.parent_id.id, phase_id.next_ids.ids)
            if not first_phase_id:
                first_phase_id = new_phase
            corresp_phases[phase_id.id] = new_phase.id
        for phase, phase_todo_vals in todo_next_ids.iteritems():
            phase.write({
                         'next_ids': [(6, 0, [corresp_phases[x] for x in phase_todo_vals[1]])],
                         'parent_id': corresp_phases.get(phase_todo_vals[0]),
                         })
        return {
              'view_type': 'form',
              "view_mode": 'form,tree',
              'res_model': 'project.phase',
              'res_id': first_phase_id.id,
              'type': 'ir.actions.act_window',
              }

    def get_copy_documents(self, phase_id):
        return [(6, 0, phase_id.phase_document_ids.ids)]

    def get_additional_vals(self):
        return {}
