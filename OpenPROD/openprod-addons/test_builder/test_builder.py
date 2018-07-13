# -*- coding: utf-8 -*-
'''
Created on 29 juil. 2015

@author: sylvain
'''
from openerp import models, fields, api, _

class rule_type(models.Model):
    _name = 'rule.type'
    _rec_name = 'text'
    
    text = fields.Text(string='Text', required=True, translate=True)
    nb_args = fields.Integer(string='Number of arguments', default=0, required=True)
    example = fields.Text(string='Example', translate=True)


class argument(models.Model):
    _name = 'argument'
    
    scenario_line_id = fields.Many2one('scenario.line', string='Scenario line', required=True, ondelete='cascade')
    value = fields.Text(string='Value')


class scenario_line(models.Model):
    _name = 'scenario.line'
    _order = 'sequence asc'
    
    @api.one
    @api.depends('rule_type_id', 'argument_ids')
    def _compute_text(self):
        if self.rule_type_id and self.rule_type_id.nb_args == len(self.argument_ids):
            self.text = self.rule_type_id.text.format(*[(x.value or u'\x8203') for x in self.argument_ids])
        else:
            self.text = ""
    
    @api.one
    @api.constrains('rule_type_id', 'argument_ids')
    def _check_text(self):
        if self.text == '':
            raise Warning(_('Wrong number of arguments'))
    
    @api.model
    def create(self, vals):
        if vals['sequence'] == -1:
            scenario_id = self.env['scenario'].browse(vals['scenario_id'])
            if len(scenario_id.scenario_line_ids):
                max_sequence = max(scenario_id.scenario_line_ids, key=lambda x: x.sequence).sequence + 1
            else:
                max_sequence = 0
            vals['sequence'] = max_sequence
        return super(scenario_line, self).create(vals)
            
    description = fields.Text(string='Description', translate=True)
    rule_type_id = fields.Many2one('rule.type', string='Rule Type', required=True, ondelete='restrict')
    rule_example = fields.Text(string='Rule Example', related='rule_type_id.example', readonly=True)
    argument_ids = fields.One2many('argument', 'scenario_line_id',  string='Arguments', copy=True)
    scenario_id = fields.Many2one('scenario', string='Scenario', ondelete='cascade')
    text = fields.Text(string='Text', compute='_compute_text')
    sequence = fields.Integer(string='Sequence', required=True, default=-1)
    hide = fields.Boolean(string='Hide', default=False)
    
    @api.one
    def launch(self):
        launch_id = self.env['launch.test.suit'].create({'scenario_line_id':self.id})
        run_id = launch_id.with_context({}).launch_test_suit()
        if run_id == 'failed':
            raise Warning(_('Failed launch'))
    
    @api.one
    def launch_to(self):
        parent = self.scenario_id
        for line in parent.scenario_line_ids:
            line.launch()
            if line == self:
                break
    
    @api.multi
    def add_screenshot(self):
        current_sequence = self.sequence
        next_line_ids = self.search([('sequence', '>', current_sequence), ('scenario_id', '=', self.scenario_id.id)], order="sequence desc")
        for line in next_line_ids:
            line.write({
                        'sequence': line.sequence + 1,
                        })
        mod_obj = self.env['ir.model.data']
        rule_model, rule_type_id = mod_obj.get_object_reference('test_builder', 'rule_13')
        self.create({
                     'scenario_id': self.scenario_id.id,
                     'rule_type_id': rule_type_id,
                     'sequence': current_sequence + 1,
                     })
        return {'type':'ir.actions.act_window_view_reload'}


class scenario(models.Model):
    _name = 'scenario'
    
    name = fields.Char(string='Name', required=True, translate=True)
    description = fields.Text(string='Description', translate=True)
    scenario_line_ids = fields.One2many('scenario.line', 'scenario_id',  string='Scenario lines', copy=True)
    hide = fields.Boolean(string='Hide', default=False)


class trade(models.Model):
    """ 
    Trade 
    """
    _name = 'trade'
    _description = 'Trade'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True, translate=True)
    
    
class domain_name(models.Model):
    """ 
    Domain Names 
    """
    _name = 'domain.name'
    _description = 'Domain Names'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True, translate=True)
    parent_id = fields.Many2one('domain.name')
    complete_name = fields.Char(translate=True)
    
class verb(models.Model):
    """ 
    Verb 
    """
    _name = 'verb'
    _description = 'Verb'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True, translate=True)


class batch(models.Model):
    _name = 'batch'
    
    @api.one
    @api.depends('verb_id', 'domain_name_id', 'complimentary_text')
    def _compute_document_name(self):
        self.document_name = "{} {} {}".format(self.verb_id.name or '', self.domain_name_id.name or '', self.complimentary_text or '')
    
    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')
    scenario_ids = fields.One2many('batch.scenario.rel', 'batch_id', string='Test lines')
    auto_launch = fields.Boolean(string='Automatic launch', default=False)
    create_doc = fields.Boolean(string='Create Documentation', default=False)
    document_name = fields.Char(string='Document Name', compute="_compute_document_name")
    verb_id = fields.Many2one('verb', string="Verb")
    domain_name_id = fields.Many2one('domain.name', string="Domain name", ondelete="restrict")
    complimentary_text = fields.Char('Complimentary Text', translate=True)
    trade_id = fields.Many2one('trade', string='Trade', ondelete='restrict')
    jasper_template_id = fields.Many2one('jasper.document', string='Jasper Template', ondelete='restrict')
    run_ids = fields.One2many('run', 'batch_id',  string='Runs')
    last_run_result = fields.Text(string='Last run result')
    last_run_date = fields.Datetime()
    last_document_id = fields.Many2one('jasper.document', string='Last Document', ondelete='restrict')
    last_document_date = fields.Datetime()
    
class batch_scenario_rel(models.Model):
    _name = 'batch.scenario.rel'
    _order = 'sequence asc'
    
    batch_id = fields.Many2one('batch', string='Batch', required=True, ondelete='cascade')
    scenario_id = fields.Many2one('scenario', string='Scenario', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', required=True, default=-1)
    
    @api.model
    def create(self, vals):
        if vals['sequence'] == -1:
            batch_id = self.env['batch'].browse(vals['batch_id'])
            if len(batch_id.scenario_ids):
                max_sequence = max(batch_id.scenario_ids, key=lambda x: x.sequence).sequence + 1
            else:
                max_sequence = 0
            vals['sequence'] = max_sequence
        return super(batch_scenario_rel, self).create(vals)


class run(models.Model):
    _name = 'run'
    
    name = fields.Char(string='Name', required=True, default='/', readonly=True, copy=False)
    batch_id = fields.Many2one('batch', string='Batch', required=False, ondelete='restrict')
    scenario_id = fields.Many2one('scenario', string='Scenario', required=False, ondelete='restrict')
    target_id = fields.Many2one('target.db', string='Database', required=True, ondelete='restrict')
    result = fields.Text(string='Result')
    lang_code = fields.Char(string='Lang code', size=5)
    scenario_result_ids = fields.One2many('scenario.result', 'run_id',  string='Scenario results')
    
    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].get('test_builder.run') or '/'
        
        return super(run, self).create(vals)

class scenario_result(models.Model):
    _name = "scenario.result"
    
    run_id = fields.Many2one('run', string='Run', required=True, ondelete='cascade')
    scenario_id = fields.Many2one('scenario', string='Scenario', required=False, ondelete='restrict')
    result = fields.Text(string='Result')
    result_line_ids = fields.One2many('scenario.line.result', 'scenario_result_id',  string='Scenario line results')
    hide = fields.Boolean(string='Hide', default=False)

class scenario_line_result(models.Model):
    _name = "scenario.line.result"
    
    @api.one
    @api.depends('screenshot')
    def _compute_screenshot_name(self):
        if self.screenshot:
            self.screenshot_name = "screenshot_%d.png" % self.id
    
    scenario_result_id = fields.Many2one('scenario.result', string='Scenario Result', required=False, ondelete='cascade')
    scenario_line_id = fields.Many2one('scenario.line', string='Scenario Line', required=False, ondelete='cascade')
    line_text = fields.Text(string='Line Text', related='scenario_line_id.text', readonly=True)
    result = fields.Text(string='Result')
    error = fields.Text(string='Error')
    hide = fields.Boolean(string='Hide', default=False)
    
    @api.one
    def _get_screenshot_binary_filesystem(self):
        attachment_obj = self.env['ir.attachment']
        attachment_rs = attachment_obj.search([('res_model','=',self._name),('res_id','=',self.id),('binary_field','=','screenshot')])
        if attachment_rs:
            self['screenshot'] = attachment_rs[0].datas
        else:
            self.screenshot = False
    
    @api.one
    def _set_screenshot_binary_filesystem(self):
        attachment_obj = self.env['ir.attachment']
        attachment_rs = attachment_obj.search([('res_model','=',self._name),('res_id','=',self.id),('binary_field','=','screenshot'),('is_binary_field','=',True)])
        if self.screenshot:
            if attachment_rs:
                attachment_rs.datas = self.screenshot
            else:
                attachment_obj.create({'res_model': self._name, 'res_id': self.id, 'name': 'screenshot datas' , 'is_binary_field': True, 'binary_field': 'screenshot', 'datas': self.screenshot, 'datas_fname':'screenshot datas'})
        else:
            attachment_rs.unlink()
        
    screenshot  = fields.Binary(string='string', compute='_get_screenshot_binary_filesystem', inverse='_set_screenshot_binary_filesystem', help='help')
    screenshot_name = fields.Char(compute="_compute_screenshot_name")
    label = fields.Char(string='Label', required=False)
    help_text = fields.Char(string='Help Text', required=False)

class target(models.Model):
    _name = 'target'
    
    name = fields.Char(string='Name', required=True, help="For human use only")
    url = fields.Char(string='URL', required=True, help="URL of home page, from the Selenium server PoV")


class target_db(models.Model):
    _name = 'target.db'
    
    target_id = fields.Many2one('target', string='Target', required=True, ondelete='cascade')
    name = fields.Char(string='Name', required=True, help="database name")

class test_variable(models.Model):
    """ 
    Persistent variable for the test builder 
    """
    _name = 'test.variable'
    _description = 'Persistent variable for the test builder'

    _sql_constraints = [
        ('unique_name', 'unique(name)', _("You can't have the same variable twice.")),
    ]
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Name', required=True)
    value = fields.Char(string='Value')
    