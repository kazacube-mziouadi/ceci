# -*- coding: utf-8 -*-
from datetime import date
import smtplib
import re

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from openerp import models, fields, api
from openerp.exceptions import UserError
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.tools.translate import _


ISSUE_PHASE_TYPE_SPEC = 'spec'
ISSUE_PHASE_TYPE_DEV = 'dev'
ISSUE_PHASE_TYPE_TEST = 'test'
ISSUE_PHASE_TYPE_DEP = 'prod'
ISSUE_PHASE_TYPES = [
    (ISSUE_PHASE_TYPE_SPEC, _('Specification')),
    (ISSUE_PHASE_TYPE_DEV, _('Development')),
    (ISSUE_PHASE_TYPE_TEST, _('Test')),
    (ISSUE_PHASE_TYPE_DEP, _('Deployment')),
]

ISSUE_STATE_DRAFT = 'draft'
ISSUE_STATE_WIP = 'progress'
ISSUE_STATE_FINISHED = 'finished'
ISSUE_STATE_CANCELED = 'canceled'
ISSUE_STATES = [
    (ISSUE_STATE_DRAFT, _('Draft')),
    (ISSUE_STATE_WIP, _('Work in progress')),
    (ISSUE_STATE_FINISHED, _('Finished')),
    (ISSUE_STATE_CANCELED, _('Canceled')),
]

TASK_STATE_TYPE_DRAFT = 'draft'
TASK_STATE_TYPE_PROGRESS = 'progress'
TASK_STATE_TYPE_FINISHED = 'finished'
TASK_STATE_TYPE_CANCELED = 'canceled'
TASK_STATE_TYPES = [
    (TASK_STATE_TYPE_DRAFT, _('Draft')),
    (TASK_STATE_TYPE_PROGRESS, _('Work in progress')),
    (TASK_STATE_TYPE_FINISHED, _('Finished')),
    (TASK_STATE_TYPE_CANCELED, _('Canceled'))
]

PRIORITY_TYPE_CRITICAL = 1
PRIORITY_TYPE_HIGH = 2
PRIORITY_TYPE_MEDIUM = 3
PRIORITY_TYPE_LOW = 4
PRIORITY_TYPE_MINOR = 5
PRIORITY_TYPES = [
    (PRIORITY_TYPE_CRITICAL, _('Critical')),
    (PRIORITY_TYPE_HIGH, _('High')),
    (PRIORITY_TYPE_MEDIUM, _('Medium')),
    (PRIORITY_TYPE_LOW, _('Low')),
    (PRIORITY_TYPE_MINOR, _('Minor')),
]

PRODUCTION_INSTRUCTION_TYPE_MAIL = 'mail'
PRODUCTION_INSTRUCTION_TYPE_SQL = 'sql'
PRODUCTION_INSTRUCTION_TYPE_INSTALLATION = 'installation'
PRODUCTION_INSTRUCTION_TYPE_SETTING = 'setting'
PRODUCTION_INSTRUCTION_TYPE_TEST = 'test'
PRODUCTION_INSTRUCTION_TYPES = [
    (PRODUCTION_INSTRUCTION_TYPE_MAIL, _('Mail')),
    (PRODUCTION_INSTRUCTION_TYPE_SQL, _('SQL')),
    (PRODUCTION_INSTRUCTION_TYPE_INSTALLATION, _('Installation')),
    (PRODUCTION_INSTRUCTION_TYPE_SETTING, _('Setting')),
    (PRODUCTION_INSTRUCTION_TYPE_TEST, _('Test'))
]

ISSUE_COMPLEXITY_HIGH = 1
ISSUE_COMPLEXITY_MEDIUM = 2
ISSUE_COMPLEXITY_LOW = 3
ISSUE_COMPLEXITIES = [
    (ISSUE_COMPLEXITY_HIGH, _('High')),
    (ISSUE_COMPLEXITY_MEDIUM, _('Medium')),
    (ISSUE_COMPLEXITY_LOW, _('Low')),
]

PRODUCTION_INSTRUCTION_TIMING_BEFORE = 1
PRODUCTION_INSTRUCTION_TIMING_UPDATES = 2
PRODUCTION_INSTRUCTION_TIMING_DURING = 3
PRODUCTION_INSTRUCTION_TIMING_AFTER = 4
PRODUCTION_INSTRUCTION_TIMING = [
    (PRODUCTION_INSTRUCTION_TIMING_BEFORE, _('1-Before production')),
    (PRODUCTION_INSTRUCTION_TIMING_UPDATES, _('2-Updates Module')),
    (PRODUCTION_INSTRUCTION_TIMING_DURING, _('3-During production')),
    (PRODUCTION_INSTRUCTION_TIMING_AFTER, _('4-After production'))
]

OPTION_EMAIL_NONE = 0
OPTION_EMAIL_ALL = 1
OPTION_EMAIL_ONLY_ASSIGNED = 2
OPTION_EMAIL_ONLY_ASSIGNED_TASKS = 3
OPTION_EMAIL_TYPES = [
    (OPTION_EMAIL_NONE, _('Never')),
    (OPTION_EMAIL_ALL, _('For all issues (not implemented yet)')),
    (OPTION_EMAIL_ONLY_ASSIGNED, _('For all issues where I am assigned')),
    (OPTION_EMAIL_ONLY_ASSIGNED_TASKS, _(
        'For all issues in a state where I am assigned'
    )),
]

ISSUE_TEST_TYPE_INSTRUCTION = 'instruction'
ISSUE_TEST_TYPE_BUG = 'bug'
ISSUE_TEST_TYPE_NOTE = 'note'
ISSUE_TEST_TYPES = [
    (ISSUE_TEST_TYPE_INSTRUCTION, _('Insctruction')),
    (ISSUE_TEST_TYPE_BUG, _('Bug')),
    (ISSUE_TEST_TYPE_NOTE, _('Note')),
]

ISSUE_TEST_STATE_TODO = 'todo'
ISSUE_TEST_STATE_TOTEST = 'totest'
ISSUE_TEST_STATE_DONE = 'done'


ISSUE_TEST_STATES = [
    (ISSUE_TEST_STATE_TODO, _('Todo')),
    (ISSUE_TEST_STATE_TOTEST, _('To test')),
    (ISSUE_TEST_STATE_DONE, _('Done')),
]

TRACKER_CONFIG_ID = 'TRACKER_MAIN_CONFIG'
DEFAULT_TAG_COLOR = '#000000'


class tracker_issue(models.Model):
    """
        Représentation d'un worflow de développement ou de résolution de bug
        décomposé en 'n' définis par la société propriétaire.
    """

    _name = 'tracker.issue'
    _rec_name = 'title'
    _order = 'treatment_order'

    FOLDED_STATES = [
        ISSUE_STATE_DRAFT
    ]
    FOLDED_PHASE_TYPES = []

    @api.multi
    def copy(self, *args, **kwargs):
        raise UserError(
            _('Is not possible to duplicate an issue, please create a new one.')
        )

    @api.model
    def state_groups(self, present_ids, domain, **kwargs):
        folded = {key: (key in self.FOLDED_STATES) for key, _ in ISSUE_STATES}
        # Need to copy self.STATES list before returning it,
        # because odoo modifies the list it gets,
        # emptying it in the process. Bad odoo!
        return ISSUE_STATES[:], folded

    @api.model
    def phase_type_groups(self, present_ids, domain, **kwargs):
        folded = {key: (key in self.FOLDED_PHASE_TYPES) for key, _ in ISSUE_PHASE_TYPES}
        return ISSUE_PHASE_TYPES[:], folded

    _group_by_full = {
        'state': state_groups,
        'current_phase_type': phase_type_groups,
    }

    @api.model
    def default_get(self, kwargs):
        res = super(tracker_issue, self).default_get(kwargs)
        user_obj = self.env['res.users']
        user_id = user_obj.browse(self.env.context.get('uid'))
        res['applicant_id'] = user_id.id
        res['company_id'] = user_id.company_id.id
        return res

    @api.model
    def _get_ir_sequence(self):
        return self.env['ir.sequence'].get('issue_sequence')

    @api.model
    def _phase_types_get(self):
        return ISSUE_PHASE_TYPES

    @api.model
    def _priority_type_get(self):
        return PRIORITY_TYPES

    @api.one
    @api.depends('current_task_id')
    def _compute_current_setup(self):
        self.current_phase_type = self.current_task_id.phase_type
        self.current_user_in_charge_id = self.current_task_id.user_in_charge_id
        email_manager_obj = self.env['tracker.email.manager']
        email_manager_id = email_manager_obj.search([], limit=1)
        if len(email_manager_id):
            email_manager_id.alert_users(issue_id=self)

    @api.one
    def _inverse_current_setup(self):
        for issue in self:
            issue.current_task_id.write({'user_in_charge_id': issue.current_user_in_charge_id.id})

    @api.one
    @api.depends('time_tracking_ids')
    def _compute_duration(self):
        total_time = 0.0
        for time_tracking_id in self.time_tracking_ids:
            total_time += time_tracking_id.time
        self.duration = total_time

    @api.one
    @api.multi
    def _get_default_applicant_id(self):
        return self.env.context.get('uid')

    @api.multi
    def create_quick_draft(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tracker.issue',
            'views': [[False, 'tree'], [False, 'form']],
            'target': 'self',
            'nodestroy': True,
            'view_id': 'view_tree_issue',
            'context': {'filter_my_drafts': 1}
        }

    @api.one
    @api.multi
    def create_quick_progress(self):
        self.wkf_open_button()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tracker.issue',
            'views': [[False, 'tree'], [False, 'form']],
            'target': 'self',
            'nodestroy': True,
            'view_id': 'view_tree_issue',
            'context': {'filter_my_active_issues': 1}
        }

    @api.multi
    def write(self, kwargs):
#         if self.env.context.get('params', {}).get('view_type', '') == 'kanban' and not self.env.context.get('treatment_order_modification', False):
#             raise UserError('Edit disabled in kanban view')
        success = super(tracker_issue, self).write(kwargs)
        if not success:
            return success

        old_follower_ids = self.follower_ids.filtered(
            lambda r: r.is_automatic is True
        )
        old_user_ids = [follower_id.user_id.id for follower_id in old_follower_ids]
        current_user_in_charge_ids = list()
        for task_id in self.task_ids:
            if task_id.user_in_charge_id:
                current_user_in_charge_ids.append(task_id.user_in_charge_id.id)
                
        follower_to_delete_ids = list()
        for old_user_id in old_user_ids:
            if old_user_id not in current_user_in_charge_ids:
                follower_to_delete_ids.append(old_user_id)
                
        new_follower_ids = list()
        for current_user_in_charge_id in current_user_in_charge_ids:
            if current_user_in_charge_id not in old_user_ids:
                new_follower_ids.append(current_user_in_charge_id)

        follower_obj = self.env['tracker.follower']
        if follower_to_delete_ids:
            follower_rs = follower_obj.search([
                ('issue_id', '=', self.id),
                ('user_id', 'in', follower_to_delete_ids),
                ('is_automatic', '=', True)
            ])
            follower_rs.unlink()
            
        if new_follower_ids:
            for new_follower_id in set(new_follower_ids):
                try:
                    follower_obj.create({
                        'issue_id': self.id,
                        'user_id': new_follower_id,
                        'is_automatic': True
                    })
                except Exception:
                    # SALE SALE SALE
                    pass

        if 'state' in kwargs:
            first_day_of_month = date.today().replace(day=1).strftime(DEFAULT_SERVER_DATE_FORMAT)
            setattr(
                self,
                '%s_write_date' % kwargs['state'],
                first_day_of_month
            )

        return success

    @api.one
    @api.onchange('company_id')
    def _on_change_company_id(self):
        if self.id:
            return

        self.task_ids = [(5, 0)] 
        if not self.company_id:
            return

        task_ids = list()
        task_settings_obj = self.env['tracker.task.settings']
        task_settings_rs = task_settings_obj.search([
            ('company_id', '=', self.company_id.id)
        ])
        if not task_settings_rs:
            task_settings_rs = task_settings_obj.search([
                ('company_id', '=', False)
            ])
            
        for task in task_settings_rs:
            user_in_charge = task.user_in_charge_id.id if task.user_in_charge_id else None
            task_ids.append([
                0, False, {
                    'company_id': self.company_id,
                    'sequence': task.sequence,
                    'title': task.title,
                    'user_in_charge_id': user_in_charge,
                    'phase_type': task.phase_type,
                    'state': TASK_STATE_TYPE_DRAFT
                }
            ])
        self.task_ids = task_ids

    @api.one
    def _compute_developper_id(self):
        self.developper_id = False
        for task in self.task_ids:
            if task.phase_type == 'dev':
                if task.user_in_charge_id:
                    self.developper_id = task.user_in_charge_id
                    pass

    @api.one
    @api.onchange('developper_id')
    def _on_change_developper_id(self):
        if not self.developper_id:
            return

        dev_task_ids = self.task_ids.filtered(
            lambda r: r.phase_type == ISSUE_PHASE_TYPE_DEV
        )
        for task in dev_task_ids:
            if task.phase_type == ISSUE_PHASE_TYPE_DEV:
                task.user_in_charge_id = self.developper_id

    @api.one
    @api.onchange('tester_id')
    def _on_change_tester_id(self):
        if not self.tester_id:
            return

        dev_task_ids = self.task_ids.filtered(
            lambda r: r.phase_type == ISSUE_PHASE_TYPE_TEST
        )
        for task in dev_task_ids:
            if task.phase_type == ISSUE_PHASE_TYPE_TEST:
                task.user_in_charge_id = self.tester_id
                
    @api.one
    def _compute_color(self):
        self.background_color = False
        self.border_color = False
        if self.deadline and self.deadline < fields.Date.today():
            self.background_color = 'background_Red'
        
        if self.priority == PRIORITY_TYPE_HIGH or self.priority == PRIORITY_TYPE_CRITICAL:
            self.border_color = 'border_Red'
          
    @api.one
    def _compute_nb_attachment(self):
        self.nb_attachment = len(self.attachment_ids)
        

    applicant_id = fields.Many2one(
        comodel_name='res.users',
        string='Applicant', required=False,
        default=_get_default_applicant_id
    )
    attachment_ids = fields.Many2many(
        comodel_name='document.openprod',
        string='Attachments', copy=False,
    )
    category_id = fields.Many2one(
        comodel_name='tracker.issue.category', string='Category'
    )
    complexity = fields.Selection(
        default=ISSUE_COMPLEXITY_LOW, required=False,
        selection=ISSUE_COMPLEXITIES
    )
    company_id = fields.Many2one(
        'res.company', string='Company',
    )
    current_task_id = fields.Many2one(
        comodel_name='tracker.task',
        string='Current task', required=False, readonly=True
    )
    current_phase_type = fields.Selection(
        selection=ISSUE_PHASE_TYPES,
        default=ISSUE_PHASE_TYPE_SPEC, required=False,
        readonly=True, compute=_compute_current_setup,
        store=True
    )
    current_user_in_charge_id = fields.Many2one(
        comodel_name='res.users',
        required=False, compute=_compute_current_setup,
        store=True, string="Current user in charge",
        inverse=_inverse_current_setup
    )
    description_customer = fields.Html(
        required=False
    )
    developper_id = fields.Many2one(
        compute='_compute_developper_id', comodel_name='res.users',
        string='Developper', required=False
    )
    deadline = fields.Date(
        required=False
    )
    duration = fields.Float(
        required=False, readonly=True,
        compute='_compute_duration'
    )
    expected_time = fields.Float(
        required=False, default=0.0
    )
    follower_ids = fields.One2many(
        comodel_name='tracker.follower',
        string='Followers', required=False,
        inverse_name='issue_id'
    )
    draft_write_date = fields.Date(
        required=False,
    )
    progress_write_date = fields.Date(
        required=False,
    )
    finished_write_date = fields.Date(
        required=False,
    )
    canceled_write_date = fields.Date(
        required=False,
    )

    priority = fields.Selection(
        selection=PRIORITY_TYPES,
        default=PRIORITY_TYPE_MEDIUM, required=False
    )
    production_instruction_ids = fields.One2many(
        comodel_name='tracker.production.instruction',
        required=False, inverse_name="issue_id"
    )
    sprint_id = fields.Many2one(
        comodel_name='tracker.sprint',
        string='Sprint', required=False
    )
    sequence = fields.Char(
        default=_get_ir_sequence,
        size=8
    )
    specification_developer = fields.Html(
        required=False
    )
    commit_ids = fields.Many2many(
        comodel_name='tracker.commit',
        inverse_name='issue_ids',
        relation='tracker_commit_tracker_issue_rel',
    )
    state = fields.Selection(
        selection=ISSUE_STATES,
        default=ISSUE_STATE_DRAFT, required=True
    )
    tag_ids = fields.Many2many(
        comodel_name='tracker.tag',
        required=False, string='Tags'
    )
    task_ids = fields.One2many(
        comodel_name='tracker.task', inverse_name='issue_id',
        string='Tasks', required=False,
    )
    test_ids = fields.One2many(
        comodel_name='tracker.issue.test',
        inverse_name='issue_id', required=False
    )
    tester_id = fields.Many2one(
        comodel_name='res.users',
        string='Tester', required=False
    )
    time_tracking_ids = fields.One2many(
        comodel_name='resource.timetracking', required=False,
        inverse_name='issue_id', string='Time tracking',
    )
    title = fields.Char(
        size=255, required=True,
    )
    transcription_customer = fields.Html(
        required=False
    )
    treatment_order = fields.Integer(
        string='Treatment order', default=7
    )
    resource_id = fields.Many2one('mrp.resource', string='User resource', default=lambda self: self.env.user.resource_id)
    is_unvalidate_test = fields.Boolean(string='Unvalidate test', default=False)
    background_color = fields.Char(compute='_compute_color', string='Background color')
    border_color = fields.Char(compute='_compute_color', string='Border color')
    nb_attachment = fields.Integer(string='Attachment', default=0, required=False, compute='_compute_nb_attachment')
    development_comment = fields.Text(string='Comment')
    is_translation = fields.Boolean(string='Is translation', default=False)
    is_security = fields.Boolean(string='Is security', default=False)

    @api.one
    @api.multi
    def wkf_next_task_button(self):
        if not self.current_task_id:
            raise UserError('You must open the issue first.')

        constraint_errors = self.current_task_id.get_constraint_errors()
        if constraint_errors:
            raise UserError(constraint_errors)

        next_task = self.task_ids.filtered(
            lambda r: r.sequence > self.current_task_id.sequence
        )
        if not next_task.exists():
            if self.current_task_id.id:
                self.current_task_id.write({
                    'state': TASK_STATE_TYPE_FINISHED,
                    'last_update_date': fields.Datetime.now()
                })
            self.state = ISSUE_STATE_FINISHED
            return
        
        if self.current_task_id.phase_type == ISSUE_PHASE_TYPE_DEV:
            message = ''
            if not self.commit_ids:
                message = _('%s\n- The tickets should have commit')%message
                
            if not self.is_translation:
                message = _('%s\n- The translation should be done')%message
            
            if not self.is_security:
                message = _('%s\n- The security should be done')%message
            
            if message != '':
                raise UserError(_('To validate a developmet phase:%s')%message)
            
        self.current_task_id.state = TASK_STATE_TYPE_FINISHED
        self.current_task_id.last_update_date = fields.Datetime.now()
        next_task[0].state = TASK_STATE_TYPE_PROGRESS
        self.current_task_id = next_task[0].id
        if self.current_task_id.phase_type == ISSUE_PHASE_TYPE_TEST:
            self.is_unvalidate_test = False
        

    @api.one
    @api.multi
    def wkf_previous_task_button(self):
        if not self.current_task_id:
            raise UserError('You must open the issue first.')

        previous_task = self.task_ids.filtered(
            lambda r: r.sequence < self.current_task_id.sequence
        )
        if not previous_task.exists():
            return
        
        if self.current_task_id.phase_type == ISSUE_PHASE_TYPE_TEST: 
            if not self.test_ids:
                raise UserError(_('The tickets should have test report to unvalidate a test phase'))
            else:
                self.is_unvalidate_test = True
            
        self.current_task_id.state = TASK_STATE_TYPE_DRAFT
        self.current_task_id.last_update_date = fields.Datetime.now()
        self.current_task_id = previous_task[-1].id
        previous_task[-1].state = TASK_STATE_TYPE_PROGRESS

    @api.one
    @api.multi
    def wkf_open_button(self):
        if not len(self.task_ids):
            raise UserError('You must define a workflow first.')

        current_task_id = self.task_ids.filtered(
            lambda r: r.state == TASK_STATE_TYPE_PROGRESS
        )
        if len(current_task_id) > 1:
            current_task_id = current_task_id[-1]
        if not current_task_id:
            current_task_id = self.task_ids[0]
        self.write({
            'state': ISSUE_STATE_WIP,
            'current_task_id': current_task_id.id
        })
        current_task_id.write({
            'state': TASK_STATE_TYPE_PROGRESS
        })

    @api.one
    @api.multi
    def wkf_close_button(self):
        if self.state == ISSUE_STATE_CANCELED:
            return

        self.write({
            'state': ISSUE_STATE_CANCELED
        })
        self.task_ids.filtered(
            lambda r: r.state == TASK_STATE_TYPE_DRAFT
        ).write({
            'state': TASK_STATE_TYPE_CANCELED
        })

    @api.one
    @api.multi
    def follow_button(self):
        current_user = self.env.context.get('uid')
        follower_obj = self.env['tracker.follower']
        follower_id = follower_obj.search([
            ('user_id', '=', current_user),
            ('issue_id', '=', self.id)
        ], limit=1
        )
        if len(follower_id):
            follower_id.write({
                'is_following': True
            })
            return

        follower_obj.create({
            'user_id': current_user,
            'issue_id': self.id,
            'is_following': True,
            'is_automatic': False
        })

    @api.one
    @api.multi
    def unfollow_button(self):
        current_user = self.env.context.get('uid')
        follower_obj = self.env['tracker.follower']
        follower_id = follower_obj.search([
            ('user_id', '=', current_user),
            ('issue_id', '=', self.id),
            ('is_following', '=', True)
        ], limit=1
        )
        if not len(follower_id):
            return

        follower_id.write({
            'is_following': False
        })

    @api.one
    def decrease_treatment_order(self):
        self.treatment_order -= 1

    @api.one
    def increase_treatment_order(self):
        self.treatment_order += 1

    @api.multi
    def open_complete_form(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tracker.issue',
            'views': [[False, 'form']],
            'res_id': self.id,
            'target': 'self',
            'nodestroy': True,
            'view_id': 'view_form_tracker_issue',
        }

    @api.multi
    def open_quick_form(self):
        view_obj = self.env['ir.ui.view']
        view_rs = view_obj.search(
            [('name', '=', 'quick_issue_form')],
            limit=1
        )
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tracker.issue',
            'views': [[view_rs.id, 'form']],
            'res_id': self.id,
            'target': 'self',
            'nodestroy': True,
            'view_id': (view_rs.id, view_rs.name),
            'xml_id': 'tracker.view_form_new_issue'
        }

    def _read_group_fill_results(self, cr, uid, domain, groupby,
                                 remaining_groupbys, aggregated_fields,
                                 count_field, read_group_result,
                                 read_group_order=None, context=None):
        """
        The method seems to support grouping using m2o fields only,
        while we want to group by a simple status field.
        Hence the code below - it replaces simple status values
        with (value, name) tuples.
        """
        if groupby in ('state', 'current_phase_type'):
            if groupby == 'state':
                GROUPBY_DICT = dict(ISSUE_STATES)
            if groupby == 'current_phase_type':
                GROUPBY_DICT = dict(ISSUE_PHASE_TYPES)
            for result in read_group_result:
                res_groupby = result[groupby]
                result[groupby] = (res_groupby, GROUPBY_DICT.get(res_groupby))

        return super(tracker_issue, self)._read_group_fill_results(
            cr, uid, domain, groupby, remaining_groupbys, aggregated_fields,
            count_field, read_group_result, read_group_order, context
        )
    
    @api.multi
    def unlink(self):
        if self.state == ISSUE_STATE_CANCELED:
            return super(tracker_issue, self).unlink()
        else:
            raise UserError(_('You can\'t delete record with state not canceled.'))


class tracker_task(models.Model):
    """Tâche associé à un worflow"""

    _name = 'tracker.task'
    _rec_name = 'title'
    _sql_constraints = [
        (
            'sequence_unique',
            'unique(issue_id,sequence,company_id)',
            'Sequence must be unique for a given issue'
        ),
    ]
    _order = 'sequence'

    @api.model
    def create(self, kwargs):
        kwargs['is_default'] = self.env.context.get('is_default', False)
        return super(tracker_task, self).create(kwargs)

    @api.one
    @api.onchange('user_in_charge_id')
    def create_user_config(self):
        if not self.user_in_charge_id:
            return

        user_config_obj = self.env['tracker.user.email.config']
        user_config_id = user_config_obj.search(
            [('user_id', '=', self.user_in_charge_id.id)],
            limit=1
        )
        if not len(user_config_id):
            user_config_obj.create({'user_id': self.user_in_charge_id.id})

    company_id = fields.Many2one(
        'res.company', string='Company'
    )
    issue_id = fields.Many2one(
        comodel_name='tracker.issue', string='Issue',
        required=False
    )
    phase_type = fields.Selection(
        selection=ISSUE_PHASE_TYPES,
        default=ISSUE_PHASE_TYPE_SPEC, required=True
    )
    state = fields.Selection(
        selection=TASK_STATE_TYPES,
        default=TASK_STATE_TYPE_DRAFT, required=True
    )
    sequence = fields.Integer(
        'Sequence', required=True
    )
    title = fields.Char(
        size=255, required=True
    )
    user_in_charge_id = fields.Many2one(
        comodel_name='res.users', required=False,
        string='User in charge'
    )
    last_update_date = fields.Datetime(
        string='Last update on'
    )

    def get_constraint_errors(self):
        # TODO pour rendre les contraintes dynamique
        return ''


class tracker_task_config(models.Model):

    _name = 'tracker.task.config'
    _rec_name = 'display_name'

    @api.model
    def display_name_get(self):
        return 'Task config'


class tracker_sprint(models.Model):
    """docstring for tracker_sprint"""
    _name = 'tracker.sprint'

    description = fields.Text(
        required=False
    )
    end_date = fields.Date(
        required=False
    )
    issue_ids = fields.One2many(
        inverse_name='sprint_id', comodel_name='tracker.issue',
        string='Issues', required=False
    )
    name = fields.Char(
        size=255, required=True
    )
    start_date = fields.Date(
        required=False
    )


class tracker_tag(models.Model):
    _name = 'tracker.tag'

    color = fields.Char(
        size=8, default=DEFAULT_TAG_COLOR,
        required=True
    )
    name = fields.Char(
        size=24, required=True
    )


class tracker_commit(models.Model):
    _name = 'tracker.commit'
    _sql_constraints = [(
        'unique_revision',
        'unique(revision)',
        'Revision number must be unique'
    ), ]
    _order = 'write_date desc'
    _rec_name = 'revision'

    @api.model
    def create(self, kwargs):
        commit_id = super(tracker_commit, self).create(kwargs)
        if commit_id:
            commit_id.parse_message_and_link_issues()
        return commit_id

    revision = fields.Char(
        size=255, required=False,
    )
    message = fields.Text(
        required=False
    )
    url = fields.Text(
        required=False, size=255
    )
    username = fields.Char(
        required=False, size=255,
        string="User"
    )
    branch_name = fields.Char(
        required=False, size=255,
    )
    source = fields.Char(
        required=False, size=8
    )
    source_created_datetime = fields.Datetime(
        required=False, string="Created at"
    )
    tag = fields.Char(
        required=False, size=16
    )
    issue_ids = fields.Many2many(
        comodel_name='tracker.issue',
        inverse_name='commit_ids',
        relation='tracker_commit_tracker_issue_rel',
        required=False
    )

    @api.one
    def parse_message_and_link_issues(self):
        issue_pattern = '#([0-9]{8})'
        close_pattern = 'close\s#([0-9]{8})'
        if self.message:
            issue_sequences = list(set(re.findall(issue_pattern, self.message)))
            if not issue_sequences:
                return
    
            issue_obj = self.env['tracker.issue']
            issue_rs = issue_obj.search([('sequence', 'in', issue_sequences)])
            issue_rs.write({'commit_ids': [(4, self.id)]})
            issue_to_close_sequences = list(
                set(re.findall(close_pattern, self.message))
            )
            if not issue_to_close_sequences:
                return
    
            issue_rs = issue_obj.search([
                ('sequence', 'in', issue_to_close_sequences)
            ])
            issue_rs.write({'state': ISSUE_STATE_CANCELED})


class tracker_user_email_config(models.Model):

    _name = 'tracker.user.email.config'

    _rec_name = 'user_id'

    user_id = fields.Many2one(
        comodel_name='res.users',
    )
    user_email = fields.Char(
        size=255, required=False,
        string='Email'
    )
    option_email = fields.Selection(
        selection=OPTION_EMAIL_TYPES,
        default=OPTION_EMAIL_ONLY_ASSIGNED_TASKS,
        required=True
    )

    @api.one
    @api.multi
    def user_wants_email(self, issue_id):
        if self.option_email == OPTION_EMAIL_NONE:
            return False
        if (
            self.option_email == OPTION_EMAIL_ONLY_ASSIGNED_TASKS and
            issue_id.current_user_in_charge_id != self.user_id
        ):
            return False
        return True


class tracker_email_manager(models.Model):
    """
        Email manager pour l'envoi de mail concernant les tickets
    """
    _name = 'tracker.email.manager'

    @api.model
    def create(self, kwargs):
        return super(tracker_email_manager, self).create(kwargs)

    base_url = fields.Char(
        size=255, required=True,
        help_text='Base url of the openerp server to complete'
    )
    smtp_url = fields.Char(
        size=255,
        required=True
    )
    smtp_port = fields.Integer(
        required=True
    )
    name = fields.Char(
        size=20, required=True,
        string='Unique name'
    )
    from_email = fields.Char(
        size=255,
        required=True
    )
    smtp_user = fields.Char(
        size=255,
        required=True
    )
    smtp_pwd = fields.Char(
        size=255,
        required=True
    )
    _sql_constraints = [(
        'name_unique',
        'unique(name)',
        'Name must be unique'
    ), ]

    @api.one
    @api.multi
    def alert_users(self, issue_id):
        follower_following_ids = issue_id.follower_ids.filtered(
            lambda r: r.is_following is True
        )
        automatic_follower_ids = follower_following_ids.filtered(
            lambda r: r.is_automatic is True
        )
        manual_follower_ids = follower_following_ids.filtered(
            lambda r: r.is_automatic is not True
        )

        user_email_settings_obj = self.env['tracker.user.email.config']
        automatic_user__ids = list()
        manual_user__ids = list()
        for follower_id in automatic_follower_ids:
            automatic_user__ids.append(follower_id.user_id.id)
        for follower_id in manual_follower_ids:
            manual_user__ids.append(follower_id.user_id.id)

        automatic_settings_ids = user_email_settings_obj.search(
            [('user_id', 'in', automatic_user__ids)]
        )
        manual_settings_ids = user_email_settings_obj.search(
            [('user_id', 'in', manual_user__ids)]
        )

        user_email_to_alert = set()
        for setting in manual_settings_ids:
            user_email_to_alert.add(setting.user_email)
        for setting in automatic_settings_ids:
            if setting.user_wants_email(issue_id) and setting.user_email:
                user_email_to_alert.add(setting.user_email)

        if not user_email_to_alert:
            return

        text, html = self._make_email(issue_id)
        subject = _('Issue ({}) updated'.format(issue_id.sequence))
        self._send_mass_mail(
            to_emails=user_email_to_alert, subject=subject,
            html=html, text=text
        )

    def _send_mass_mail(self, to_emails, subject, html, text):
        server = self.get_smtp_server()
        from_ = self.from_email

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = from_
        msg.attach(MIMEText(text, 'plain'))
        msg.attach(MIMEText(html, 'html'))

        server.sendmail(from_, to_emails, msg.as_string())

        server.quit()

    def get_smtp_server(self):
        server = smtplib.SMTP_SSL(self.smtp_url, self.smtp_port, timeout=30)
        server.login(self.smtp_user, self.smtp_pwd)

        return server

    @api.multi
    def test_connection(self):
        try:
            server = smtplib.SMTP_SSL(self.smtp_url, self.smtp_port, timeout=30)
            server.login(self.smtp_user, self.smtp_pwd)
            raise UserError('Connection works')
        except Exception as e:
            raise UserError(str(e))

    @api.multi
    def _make_email(self, issue_id):
        base_url = getattr(self, 'base_url', 'http://localhost')
        link = '%s/web#id=%s&view_type=form&model=%s' % (base_url, issue_id.id, issue_id._name)
        html = self._make_html_email(issue_id=issue_id, link=link)
        text = self._make_text_email(issue_id=issue_id, link=link)
        return (text, html)

    def _make_text_email(self, issue_id, link):
        return _('Hello,\n The issue ({0}) "{1}"" has been updated\n Here is the link: {2}'.format(
            issue_id.sequence,
            issue_id.title,
            link
        ))

    def _make_html_email(self, issue_id, link):
        return _("""
<html>
  <head></head>
  <body>
    <p>Hello,<br>
       The issue ({0}) "{1}" has been updated<br>
       Here is the <a href="{2}">link</a> to see it.
    </p>
  </body>
</html>
""".format(
            issue_id.sequence,
            issue_id.title,
            link
        ))


class tracker_production_instruction(models.Model):

    _name = 'tracker.production.instruction'
    _order = 'timing'
    _rec_name = 'title'

    user_in_charge_id = fields.Many2one(
        comodel_name='res.users',
        required=False, string="User in charge"
    )
    issue_id = fields.Many2one(
        comodel_name='tracker.issue',
        required=False, string="Issue"
    )
    action_type = fields.Selection(
        selection=PRODUCTION_INSTRUCTION_TYPES,
        required=True
    )
    timing = fields.Selection(
        selection=PRODUCTION_INSTRUCTION_TIMING,
        required=True
    )
    title = fields.Char(
        size=255, required=True
    )
    company_ids = fields.Many2many(
        comodel_name='res.company',
        string='company', required=False
    )


class tracker_issue_category(models.Model):
    _name = 'tracker.issue.category'
    name = fields.Char(
        required=True, size=255
    )


class tracker_task_settings(models.Model):
    _name = 'tracker.task.settings'
    _sql_constraints = [
        (
            'sequence_unique',
            'unique(company_id,sequence)',
            'Sequence must be unique for a given company'
        ),
    ]
    _rec_name = 'title'
    _order = 'sequence'

    company_id = fields.Many2one(
        'res.company', string='Company'
    )
    phase_type = fields.Selection(
        selection=ISSUE_PHASE_TYPES,
        default=ISSUE_PHASE_TYPE_SPEC, required=True
    )
    sequence = fields.Integer(
        'Sequence', required=True
    )
    title = fields.Char(
        size=255, required=True
    )
    user_in_charge_id = fields.Many2one(
        comodel_name='res.users', required=False,
        string='User in charge'
    )


class tracker_production_deployment(models.Model):
    _name = 'tracker.production.deployment'
    _rec_name = 'title'

    @api.one
    @api.onchange('commit_ids')
    def _on_change_commit_ids(self):
        self.issue_ids = [(5, 0)]
        if not self.commit_ids:
            return

        self.last_commit = self.commit_ids[-1].revision
        issue_ids = list()
        for commit_id in self.commit_ids:
            for issue_id in commit_id.issue_ids:
                issue_ids.append([
                    4, issue_id.id
                ])
        if not issue_ids:
            return
        self.issue_ids = issue_ids

    @api.one
    @api.onchange('issue_ids', 'manual_issue_ids', 'company_id')
    def _on_change_issue_ids(self):
        if not (len(self.issue_ids or self.manual_issue_ids)):
            self.production_instruction_ids = [(5, 0)]
            return

        old_issue_ids = self.get_old_issue_ids_to_list()
        new_old_issue_ids = list()
        instruction_obj = self.env['tracker.deployment.instruction']
        instruction_ids = list()
        for issue_id in self.issue_ids:
            if issue_id.id in self.manual_issue_ids.ids:
                continue
            if issue_id in old_issue_ids:
                instruction_ids += instruction_obj.get_or_create_batch_as_command(issue_id, self)
            else:
                instruction_ids += instruction_obj.create_batch_as_command(
                    issue_id=issue_id, deployment_id=self
                )
            new_old_issue_ids.append(issue_id.id)

        for issue_id in self.manual_issue_ids:
            if issue_id in old_issue_ids:
                instruction_ids += instruction_obj.get_or_create_batch_as_command(issue_id, self)
            else:
                instruction_ids += instruction_obj.create_batch_as_command(
                    issue_id=issue_id, deployment_id=self
                )
            new_old_issue_ids.append(issue_id.id)

        self.production_instruction_ids = [(5, 0)]
        if not instruction_ids:
            return

        self.old_user_ids = self.format_old_issue_ids(new_old_issue_ids)
        self.production_instruction_ids = instruction_ids

    title = fields.Char(
        size=255, required=True
    )
    user_in_charge_id = fields.Many2one(
        comodel_name='res.users', required=False,
        string='User in charge'
    )
    customer_company_id = fields.Many2one(
        comodel_name='res.company',
        string='Customer\'s compane', required=False
    )
    company_in_charge_id = fields.Many2one(
        comodel_name='res.company',
        string='Company in charge', required=False
    )
    deployment_date = fields.Date(
        required=False,
    )
    last_commit = fields.Char(
        size=255, required=False
    )
    commit_ids = fields.Many2many(
        comodel_name='tracker.commit',
        required=False
    )
    manual_issue_ids = fields.Many2many(
        comodel_name='tracker.issue',
        required=False, relation='tracker_deployment_manual_issue'
    )
    issue_ids = fields.Many2many(
        comodel_name='tracker.issue',
        required=False
    )
    production_instruction_ids = fields.One2many(
        comodel_name='tracker.deployment.instruction',
        required=False, relation='tracker_deployment_instruction',
        inverse_name='deployment_id'
    )
    comments = fields.Text(
        required=False
    )
    old_issue_ids = fields.Char(
        size=1024, required=False,
        default=''
    )

    @api.one
    def get_old_issue_ids_to_list(self):
        if not self.old_issue_ids:
            return list()
        return [int(id_) for id_ in self.old_issue_ids.split(',')]

    @api.one
    def format_old_issue_ids(self, ids):
        self.old_issue_ids = ','.join((map(str, ids)))


class tracker_follower(models.Model):
    _name = 'tracker.follower'
    _rec_name = 'user_id'

    user_id = fields.Many2one(
        comodel_name='res.users',
        required=True, string='User',
        inverse_name='follower_ids'
    )
    issue_id = fields.Many2one(
        comodel_name='tracker.issue',
        required=True, string='Issue', ondelete='cascade'
    )
    is_following = fields.Boolean(
        default=True
    )
    is_automatic = fields.Boolean(
        default=True
    )


class tracker_issue_test(models.Model):

    _name = 'tracker.issue.test'

    @api.model
    def default_get(self, kwargs):
        defaults = super(tracker_issue_test, self).default_get(kwargs)
        user_obj = self.env['res.users']
        user_id = user_obj.browse(self.env.context.get('uid'))
        defaults['telltale_id'] = user_id.id
        defaults['developper_in_charge_id'] = user_id.id
        return defaults
        

    type_ = fields.Selection(
        selection=ISSUE_TEST_TYPES,
        required=True
    )
    developper_in_charge_id = fields.Many2one(
        comodel_name='res.users',
        required=True, string='Developper in charge'
    )
    state = fields.Selection(
        selection=ISSUE_TEST_STATES,
        required=True, default=ISSUE_TEST_STATE_TODO
    )
    telltale_id = fields.Many2one(
        comodel_name='res.users',
        required=True, string='Telltale'
    )
    description = fields.Html(
        required=False
    )
    issue_id = fields.Many2one(
        comodel_name='tracker.issue',
        inverse_name='test_ids'
    )
    
    
    @api.multi
    def change_to_next_state(self):
        i = 0
        while i < len(ISSUE_TEST_STATES) and self.state != ISSUE_TEST_STATES[i][0]:
            i += 1
            
        self.state = ISSUE_TEST_STATES[i+1][0]
    
    
    @api.multi
    def change_to_previous_state(self):
        i = 0
        while i < len(ISSUE_TEST_STATES) and self.state != ISSUE_TEST_STATES[i][0]:
            i += 1
            
        self.state = ISSUE_TEST_STATES[i-1][0]
        


class tracker_deployment_instruction(models.Model):
    _name = 'tracker.deployment.instruction'
    _order = 'timing_related'

    @api.multi
    def get_or_create_batch_as_command(self, issue_id, deployment_id):
        objs = list()
        for instruction_id in issue_id.production_instruction_ids:
            if instruction_id in deployment_id.production_instruction_ids.ids:
                continue
            if instruction_id.company_ids:
                if not deployment_id.customer_company_id or \
                        deployment_id.customer_company_id.id not in instruction_id.company_ids.ids:
                    continue
            deployment_instruction_id = self.search([
                ('deployment_id', '=', deployment_id.id),
                ('instruction_id', '=', instruction_id.id)
            ])
            if not deployment_instruction_id:
                obj = self.create_as_command(instruction_id)
            else:
                obj = [4, deployment_instruction_id.id]
            objs.append(obj)
        return objs

    def create_as_command(self, instruction_id):
        return [
            0, False, {
                'instruction_id': instruction_id.id
            }
        ]

    @api.multi
    def create_batch_as_command(self, issue_id, deployment_id):
        objs = list()
        for instruction_id in issue_id.production_instruction_ids:
            if instruction_id.company_ids:
                if not deployment_id.customer_company_id or \
                        deployment_id.customer_company_id.id not in instruction_id.company_ids.ids:
                    continue
            objs.append(self.create_as_command(instruction_id))
        return objs

    deployment_id = fields.Many2one(
        required=True, comodel_name='tracker.production.deployment',
        inverse_name='instructions_ids'
    )
    instruction_id = fields.Many2one(
        required=True, comodel_name='tracker.production.instruction',
    )
    is_done = fields.Boolean(
        default=False
    )
    is_automatic = fields.Boolean(
        default=True
    )
    action_type_related = fields.Selection(
        related='instruction_id.action_type',
        store=True
    )
    title_related = fields.Char(
        related='instruction_id.title',
        store=True
    )
    timing_related = fields.Selection(
        related='instruction_id.timing',
        store=True
    )
    user_in_charge_id_related = fields.Many2one(
        related='instruction_id.user_in_charge_id',
        store=True
    )