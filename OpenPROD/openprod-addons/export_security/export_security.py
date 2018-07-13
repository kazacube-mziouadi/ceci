# -*- coding: utf-8 -*-
from openerp import models, api, fields, _


class export_security_rule(models.Model):
    """ Règle de sécurité pour les exports, ajoutée au fields_view_get
    """
    _name = "export.security.rule"

    @api.one
    def _get_log_ids(self):
        self.log_ids = self.env['export.security.log'].search(
            [('model', '=', self.model_id.model)],
            order="create_date desc"
        ).ids

    model_id = fields.Many2one('ir.model', required=True, string="Model")
    criticality = fields.Selection(
        string="Criticality",
        required=True,
        selection=[
             ('none', 'None'),
             ('normal', 'Normal'),
             ('strategic', 'Strategic'),
        ])
    hide_reports = fields.Boolean(string="Hide reports")
    show_export = fields.Boolean(string="Export")
    show_export_current = fields.Boolean(string="Export current view")
    show_import = fields.Boolean(string="Import")
    trace_export = fields.Boolean(string="Trace export")
    trace_export_current = fields.Boolean(string="Trace export current view")
    trace_report = fields.Boolean(string="Trace reports")
    
    auth_export = fields.Many2many(
        'res.groups',
        'export_security_groups_rel',
        'sec_rule_id',
        'group_id')
    auth_export_users = fields.Many2many(
        'res.users',
        'export_security_users_rel',
        'sec_rule_id',
        'user_id')
    log_ids = fields.One2many(
        compute='_get_log_ids',
        string="Logs",
        readonly=True,
        comodel_name='export.security.log')

    @api.model
    def get_security_rule(self, model, user):
        user_obj = self.env['res.users']
        sec_rule = self.search([('model_id.model', '=', model)]).read()
        if len(sec_rule) == 0:
            model_id = self.env['ir.model'].search([('model', '=', model)])
            group_admin = self.env.ref('base.group_erp_manager')
            sec_rule = len(self.env['res.groups'].search([
                ('id', '=', group_admin.id),
                ('users', 'in', user.id)
            ])) > 0
            model_id = model_id.id
        else:
            sec_rule = sec_rule[0]
            if len(user_obj.search([
                ('id', '=', user.id),
                ('groups_id', 'in', sec_rule['auth_export'])
            ])) > 0:
                sec_rule['can_export'] = True
            elif user.id in sec_rule['auth_export_users']:
                sec_rule['can_export'] = True
            elif user.id == 1:
                sec_rule['can_export'] = True
            else:
                sec_rule['can_export'] = False
            group_admin = self.env.ref('base.group_erp_manager')
            sec_rule['is_admin'] = group_admin in user.groups_id
            model_id = sec_rule['model_id'][0]
        return (sec_rule, model_id)


class export_security_log(models.Model):
    _name = "export.security.log"

    model = fields.Char(string="Model")
    user_id = fields.Many2one('res.users', string="User")
    criticality = fields.Char(string="Criticality")
    name = fields.Char(string="Name")
    filter = fields.Char(string="Filter")
    group_by = fields.Char(string="Group by")
    lines_count = fields.Integer(string="Lines count")
    create_date = fields.Datetime('Create date', readonly=True)
    
    @api.model
    def search(self, args=None, *largs, **kwargs):
        for arg in args:
            if isinstance(arg, list) and len(arg) == 3 and arg[0] == 'model':
                arg[2] = self.env['ir.model'].browse(arg[2]).model
        return super(export_security_log, self).search(args, *largs, **kwargs)
