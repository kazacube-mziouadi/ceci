# coding: utf-8
from openerp import models, fields, api, _
from itertools import count
from lxml import etree
import xml.etree.ElementTree as ET
import json

class edit_tree_wizard(models.TransientModel):
    """ 
    Edit tree wizard 
    """
    _name = 'edit.tree.wizard'
    _description = 'Edit tree wizard'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    field_ids = fields.One2many('edit.tree.field', 'wizard_id')
    hidden_field_ids = fields.One2many('edit.tree.field', 'hidden_wizard_id')
    model = fields.Char(string='Model', required=True)
    name = fields.Char(string='Name', required=True)
    priority = fields.Integer(string='Priority', default=5000, required=True)
    group_ids = fields.Many2many('res.groups', 'edit_tree_groups', 'edit_tree_id', 'group_id', string="Groups")
    
    @api.model
    def default_get(self, fields):
        model = self.env.context.get('model')
        view_id = self.env.context.get('tree_view_id', None)
        model_obj = self.env[model]
        fields_view = model_obj.fields_view_get(view_id=view_id, view_type='tree')
        field_ids = self.env['ir.model.fields'].search([('model', '=', model), ('name', 'in', fields_view['fields'].keys())])
        view_name = (self.env['ir.ui.view'].browse(view_id).name or _('Additional')) if not self.env.context.get('new_view') else _('Additional')
        priority = (self.env['ir.ui.view'].browse(view_id).priority or 5000) if not self.env.context.get('new_view') else 5000
        group_ids = [(6, 0,self.env['ir.ui.view'].browse(view_id).groups_id.ids )] if not self.env.context.get('new_view') else []
        
        fields = []
        hidden_fields = []
        for child in etree.fromstring(fields_view['arch']):
            if child.tag == 'field':
                field_id = field_ids.filtered(lambda r: r.name == child.attrib['name'])
                if len(field_id):
                    invisible = 'modifiers' in child.attrib and json.loads(child.attrib['modifiers']).get('invisible', '0') not in ('0', False)
                    if child.attrib.get('invisible', '0') != '0' or invisible:
                        hidden_fields.append((field_id.id, json.dumps(dict(child.attrib))))
                    else:
                        fields.append((field_id.id, json.dumps(dict(child.attrib))))
        
        sequence_count = count(start=1)
        hidden_sequence_count = count(start=1)
        fields = [(0, 0, {'field_id':f, 'sequence': sequence_count.next(), 'attributes': attrs}) for (f, attrs) in fields]
        hidden_fields = [(0, 0, {'field_id':f, 'sequence': hidden_sequence_count.next(), 'attributes': attrs}) for (f, attrs) in hidden_fields]
        return {
                'field_ids': fields,
                'hidden_field_ids': hidden_fields,
                'model': model,
                'wizard_id': self.id,
                'name': view_name,
                'priority': priority,
                'group_ids': group_ids,
                }
    
    @api.multi
    def override_view(self):
        view_obj = self.env['ir.ui.view']
        field_list = []
        hidden_field_list = []
        for f in self.field_ids:
            attrs = json.loads(f.attributes or '{}')
            attrs['name'] = f.field_id.name
            field_list.append(ET.tostring(ET.Element('field', attrs)))
        for f in self.hidden_field_ids:
            attrs = json.loads(f.attributes or '{}')
            attrs['name'] = f.field_id.name
            hidden_field_list.append(ET.tostring(ET.Element('field', attrs)))
        arch = """
        <tree>""" + \
        "\n".join(field_list) + \
        "\n".join(hidden_field_list) + \
        """</tree>"""
        # FIXME
        if not self.env.context.get('new_view'):
            # self.env.context.get('tree_view_id')
            view = view_obj.search([('id', '=', self.env.context.get('tree_view_id')), ('is_override', '=', True)])
        else:
            view = []
        if len(view):
            view.write({'arch_db':arch, 'name': self.name, 'priority': self.priority})
        else:
            vals = {
                'model': self.model,
                'type': 'tree',
                'priority': self.priority,
                'active': True,
                'name': self.name,
                'arch_db': arch,
                'is_override': True,
                'groups_id': [(6, 0, self.group_ids.ids)]
            }
            view = view_obj.create(vals)
        view_obj.clear_caches()
        return {
            'res_model': self.model,
            'type': 'ir.actions.act_window',
            'views': [[view.id, 'list']],
        };
    
class edit_tree_field(models.TransientModel):
    """
    field
    """
    _name = 'edit.tree.field'
    _order = 'sequence'
    
    #============================================================================
    # COLUMNS
    #============================================================================
    wizard_id = fields.Many2one('edit.tree.wizard', string='Wizard', required=False, ondelete='cascade')
    hidden_wizard_id = fields.Many2one('edit.tree.wizard', string='Wizard', required=False, ondelete='cascade')
    model = fields.Char(related="wizard_id.model", store=True)
    field_id = fields.Many2one('ir.model.fields', string='Field', required=True, ondelete='cascade', domain="[('model', '=', model)]")
    sequence = fields.Integer(string='Sequence', default=0, required=True)
    attributes = fields.Char(string='Attributes')
