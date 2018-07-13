# -*- coding: utf-8 -*-
from openerp import models, fields, api, _

class project_phase(models.Model):
    """ 
    Project phase 
    """
    _name = 'project.phase'
    _description = 'Project phase'
    _inherit= 'workflow.base'
    _order = 'sequence asc'
    _parent_store = True
    
    @api.one
    def _compute_progress(self):
        # si on change self le champ fonction ne fonctionne plus. Semble fonctionner malgré tout, ligne suivante à voir si problème
        # self = self.with_context(gantt=False)
        if len(self.wo_ids):
            self.progress = self.wo_ids[0].advancement
        elif len(self.mo_ids) and len(self.mo_ids[0].workorder_ids):
            self.progress = min(self.mo_ids[0].workorder_ids, key=lambda x:x.advancement).advancement
        elif len(self.child_ids):
            self.child_ids._compute_progress()
            self.progress = sum((x.progress for x in self.child_ids)) / len(self.child_ids)
        else:
            self.progress = self.manual_progress
            
    @api.one
    def _inverse_progress(self):
        self.manual_progress = self.progress
    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('progress', _('In progress')),
                ('done', _('Done')),
                       ]
    @api.one
    @api.depends('name', 'parent_id')
    def _compute_name_level(self):
        level = self.get_level()
        if level > 0:
            self.name_level = u'{} {}'.format('---' * level, self.name)
        else:
            self.name_level = self.name
            
    @api.one
    def _compute_fullfiled(self):
        tt_ids = self.env['resource.timetracking'].search([('phase_id', '=', self.id)])
        self.fullfiled = sum([x.time for x in tt_ids])
            
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    name_level = fields.Char(string='Name', compute='_compute_name_level')
    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='restrict')
    description = fields.Text(string='Description')
    start_date = fields.Date(string='Start date', required=False)
    end_date = fields.Date(string='End date', required=False)
    duration = fields.Integer(string='Duration')
    progress = fields.Integer(string='Progress', compute='_compute_progress', inverse='_inverse_progress')
    manual_progress = fields.Integer(string='Progress', default=0, required=False)
    parent_id = fields.Many2one('project.phase', string="Parent task", ondelete='cascade')
    next_ids = fields.Many2many('project.phase', 'project_phase_arrows', 'source_id', 'dest_id', string='Next')
    sequence = fields.Integer(default=0)
    parent_left = fields.Integer()
    parent_right = fields.Integer()
    mo_ids = fields.One2many('mrp.manufacturingorder', 'task_id')
    wo_ids = fields.One2many('mrp.workorder', 'task_id')
    event_ids = fields.One2many('calendar.event', 'task_id')
    charge = fields.Integer(string='Charge', default=0, required=False)
    resource_id = fields.Many2one('mrp.resource', string='Resource', required=False, ondelete='cascade')
    state = fields.Selection('_state_get', string='State', default="draft")
    child_ids = fields.One2many('project.phase', 'parent_id',  string='Childs')
    phase_document_ids = fields.Many2many('document.openprod', 'project_phase_document_openprod_rel', 'phase_id', 'document_id', 
                                         string='Documents', copy=False)
    fullfiled = fields.Float(string='Fullfilled', compute='_compute_fullfiled')
    is_model = fields.Boolean(string='Is Model', default=False)

    
    
    def get_level(self):
        x = self
        res = 0
        while x.parent_id:
            res += 1
            x = x.parent_id
        return res
    
    @api.multi
    @api.constrains('parent_id')
    def _check_recursion(self):
        """
            Verifie la non recursivité (100 niveaux maximum)
        """
        level = 100
        ids = self.ids
        while len(ids):
            self._cr.execute('select distinct parent_id from project_phase where id IN %s',(tuple(ids),))
            ids = filter(None, map(lambda x:x[0], self._cr.fetchall()))
            if not level:
                raise Warning(_('Error ! You cannot create recursive phases.'))
            
            level -= 1
            
        return True
    
    @api.one
    @api.constrains('child_ids')
    def _check_is_parent(self):
        """
            Verifie que la date de départ existe si la tâche n'a pas d'enfants
        """
        if not len(self.child_ids) and not self.start_date:
            raise Warning(_('Invalid task : No child and no start date'))
            
        return True
    
    
    @api.model
    def search(self, domains, *args, **kwargs):
        if not self.env.context.get('gantt', False):
            return super(project_phase, self).search(domains, *args, **kwargs)
        res = super(project_phase, self).search(domains, *args, **kwargs).ids
        res_ids = res
        for res_id in res_ids:
            res = res + super(project_phase, self).search([('id', 'child_of', res_id)]).ids
        return self.browse(res)
    
    @api.multi
    def write(self, vals, no_wo_update=False):
        res = super(project_phase, self).write(vals)
        for proj in self:
            if 'is_model' in vals:
                proj.child_ids.write({'is_model':vals['is_model']})
        if not 'start_date' in vals or no_wo_update:
            return res
        for proj in self:
            if len(proj.wo_ids):
                wo_id = proj.wo_ids[0]
                is_at_earlier = wo_id.is_at_earlier
                date = vals['start_date']
                wo_id.action_plannification_wo_at_earlier(date)
                if is_at_earlier != wo_id.is_at_earlier:
                    wo_id.is_at_earlier = is_at_earlier
        return res
    
    @api.model
    def create(self, vals):
        if 'parent_id' in vals:
            parent_id = self.browse(vals['parent_id'])
            if parent_id.is_model:
                vals['is_model'] = True
        return super(project_phase, self).create(vals)
    
    @api.onchange('parent_id')
    def _onchange_parent_id(self):
        self.is_model = self.parent_id.is_model
