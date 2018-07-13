# coding: utf-8
from openerp.models import BaseModel
from openerp import api, fields, models, _
from traceback import extract_stack
from openerp.service import model

#=======================================================================================================================
# Surcharge de write pour tous les modèles
#=======================================================================================================================
old_write = BaseModel.write
old_unlink = BaseModel.unlink

@api.multi
def write(self, vals):
    
    log_class = []
    vals_to_update = []
    if self.env.context.get('no_audittrail', False):
        return old_write(self, vals)
    if 'audittrail.rule' in self.env:
        log_class = self.env['audittrail.rule'].search([('model_id.model', '=', type(self).__name__), ('log_write', '=', True), ('state', '=', 'activated')])
        if len(log_class):
            stack = extract_stack()
            method = ''
            for line in reversed(stack):
                if line[2] not in ('wrapper', 'write', 'old_api'):
                    method = line[2]
                    break
            if method != '_call_kw' and log_class.interface_only:
                return old_write(self, vals)
            
            value_obj = self.env['audittrail.value']
                
            for obj in self:
                vals_to_update = []
                line_id = self.env['audittrail.line'].create({
                                                    'resource_id':obj.id,
                                                    'rule_id':log_class[0].id,
                                                    'user_id':obj.env.user.id,
                                                    'method':method,
                                                    'type':'write',
                                                    })
                for key, val in vals.iteritems():
                    to_update = False
                    if type(self._fields[key]) in (fields.One2many, fields.Many2many):
                        val_text = ''
                        old_val_text = [x[1] for x in obj[key].name_get()]
                        to_update = True
                    elif type(self._fields[key]) == fields.Many2one:
                        val_text = ''
                        old_val_text = obj[key].name_get()
                        if len(old_val_text):
                            old_val_text = old_val_text[0][1]
                        to_update = True
                    else:
                        val_text = unicode(val)
                        old_val_text = unicode(obj[key])
                    value_line_id = value_obj.create({'line_id':line_id.id, 'field_name':key, 'field_value':val_text, 'old_value':old_val_text})
                    if to_update:
                        vals_to_update.append((value_line_id, obj, key))
            
    res = old_write(self, vals)
    for line_id, obj, key in vals_to_update:
        line_id.write({'field_value': [x[1] for x in obj[key].name_get()]})
    return res


@api.multi
def unlink(self):
    if self.env.context.get('no_audittrail', False):
        return old_unlink(self)
    log_class = []
    if 'audittrail.rule' in self.env:
        log_class = self.env['audittrail.rule'].search([('model_id.model', '=', type(self).__name__), ('log_delete', '=', True), ('state', '=', 'activated')])
        if len(log_class):
            stack = extract_stack()
            method = ''
            for line in reversed(stack):
                if line[2] not in ('wrapper', 'unlink', 'old_api'):
                    method = line[2]
                    break
            
            line_obj = self.env['audittrail.line']
            for obj in self:
                line_obj.create({
                                'resource_id':obj.id,
                                'rule_id':log_class[0].id,
                                'user_id':self.env.user.id,
                                'method':method,
                                'type':'unlink',
                                })
    return old_unlink(self)

BaseModel.write = write
BaseModel.unlink = unlink



class audittrail_rule(models.Model):
    """ 
    Audit trail rule 
    """
    _name = 'audittrail.rule'
    _description = 'Audit trail rule'
    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('activated', _('Activated'))
                       ]
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    model_id = fields.Many2one('ir.model', string='Model', required=True, ondelete='restrict')
    log_write = fields.Boolean(string="Log write")
    log_delete = fields.Boolean(string="Log delete")
    interface_only = fields.Boolean(string='Interface only', default=False)
    state = fields.Selection('_state_get', string='State', default="draft")
    _sql_constraints = [
        ('model_uniq', 'unique(model_id)',
            'Only one rule per object type'),
    ]
    
    @api.multi
    def create_action(self):
        vals = {}
        action_obj = self.env['ir.actions.act_window']
        ir_values_obj = self.env['ir.values']
        for rule in self:
            src_obj = rule.model_id.model
            button_name = _('View audit trail')
            vals['ref_ir_act_window'] = action_obj.sudo().create(
                {
                    'name': button_name,
                    'type': 'ir.actions.act_window',
                    'res_model': 'audittrail.model_log',
                    'src_model': src_obj,
                    'view_type': 'form',
                    'context': "{'default_model_id' : %d, 'resource_id':id}" % (rule.model_id.id),
                    'view_mode': 'form,tree',
                    'target': 'new',
                    'auto_refresh': 1,
                })
            vals['ref_ir_value'] = ir_values_obj.sudo().create(
                {
                    'name': button_name,
                    'model': src_obj,
                    'key2': 'client_action_multi',
                    'value': (
                        "ir.actions.act_window," +
                        str(vals['ref_ir_act_window'].id)),
                    'object': True,
                })
        return True
    
    @api.multi
    def unlink_action(self):
        for rule in self:
            act_window = self.env['ir.actions.act_window'].search([('res_model', '=', 'audittrail.model_log'), ('src_model', '=', rule.model_id.model)])
            act_window_id = act_window.id
            act_window.unlink()
            self.env['ir.values'].search([('value', '=', "ir.actions.act_window," + str(act_window_id)), ('model', '=', rule.model_id.model)]).unlink()
        return True
    
    @api.multi
    def activate(self):
        self.create_action()
        self.write({'state':'activated'})
    
    
    @api.multi
    def deactivate(self):
        self.unlink_action()
        self.write({'state':'draft'})
    
    

class audittrail_line(models.Model):
    """ 
    Audit trail line 
    """
    _name = 'audittrail.line'
    _description = 'Audit trail line'
    _order = 'id desc'
    
    @api.model
    def _type_get(self):
        return [
                ('write', _('Write')),
                ('unlink', _('Unlink')),
                       ]
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    resource_id = fields.Integer(string='Resource ID', default=0, required=False)
    rule_id = fields.Many2one('audittrail.rule', string="Rule", ondelete="cascade")
    user_id = fields.Many2one('res.users', string='User', required=False, ondelete='restrict')
    method = fields.Char(string='Method')
    value_ids = fields.One2many('audittrail.value', 'line_id',  string='Values')
    type = fields.Selection('_type_get', string='Type')
    timestamp = fields.Datetime(string='Timestamp', default=lambda self: fields.Datetime.now())
    
    @api.multi
    def name_get(self):
        return [(x.id, x.rule_id.name + ' : ' + x.type + _(' on ') + str(x.resource_id)) for x in self]
    
    
class audittrail_value(models.Model):
    """ 
    Audittrail line value 
    """
    _name = 'audittrail.value'
    _description = 'Audittrail line value'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    line_id = fields.Many2one('audittrail.line', ondelete='cascade')
    field_name = fields.Char()
    field_value = fields.Char()
    old_value = fields.Char()