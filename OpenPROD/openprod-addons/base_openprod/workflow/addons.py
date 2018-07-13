# -*- coding: utf-8 -*-
from openerp import models, api, fields, _
from openerp.addons.base_openprod.common import get_form_view
from openerp.addons.base_openprod import utils
from lxml import etree
import re
from operator import itemgetter
from openerp.osv.orm import setup_modifiers


class wkf(models.Model):
    def _auto_init(self, cr, context=None):
        """
            On ne peut pas avoir deux workflow actifs pour le même model
        """
        res = super(wkf, self)._auto_init(cr, context=context)
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = \'active_wkf_osv_unique\'')
        if not cr.fetchone():
            cr.execute('CREATE UNIQUE INDEX active_wkf_osv_unique ON wkf (is_active, osv) WHERE is_active')
               
        return res
    
    _inherit = 'workflow'
        
    @api.one
    @api.depends('activities', 'activities.out_transitions', 'activities.out_transitions.signal', 'activities.out_transitions.visible_button', 'activities.out_transitions.attrs')
    def _compute_attrs_buttons(self):
        """
            Calcul de l'attrs des boutons générés par le workflow
        """
        res = {}
        for activity in self.activities:
            for out_transition in activity.out_transitions:
                # En fonction des transitions
                if out_transition.signal and out_transition.visible_button:
                    if res.get(out_transition.signal) and 'invisible' in res[out_transition.signal][0]:
                        for item in res[out_transition.signal][0]['invisible']:
                            if isinstance(item, tuple) and item[0] == 'wkf_progress_instance':
                                item[-1].append([str(out_transition.act_from.id), out_transition.id])
                                break
                                
                    else:       
                        res[out_transition.signal] = [{'invisible': [('wkf_progress_instance', 'not in', ['%s'%(str(out_transition.act_from.id))])]}, out_transition.id]

                # En fonction de l'attrs entré dans la transition
                if out_transition.attrs and res.get(out_transition.signal) and 'invisible' in res[out_transition.signal][0]:
                    res[out_transition.signal][0]['invisible'].insert(0, '|')
                    res[out_transition.signal][0]['invisible'].extend(eval(out_transition.attrs))
                        
        self.attrs_buttons = str(res)
        
        
    @api.one
    @api.depends('display_state_ids', 'display_state_ids.always_visible') # 'display_state_ids.color'
    def _compute_display_state(self):
        """
            Calcul du champ diplay_state
        """
        visible = []
#         colors = {}
        for display_state in self.display_state_ids:
            # A décommenter si on gère statusbar_colors
#             if display_state.color:
#                 colors[display_state.name] = display_state.color
                
            if display_state.always_visible:
                visible.append(display_state.name)
        
#         self.display_state_colors = str(colors)
        self.display_state_visible = ','.join(visible)
        
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    attrs_buttons = fields.Text(compute='_compute_attrs_buttons', store=True)
    # A décommenter si on gère statusbar_colors
#     display_state_colors = fields.Text(compute='_compute_display_state', store=True)
    display_state_visible = fields.Text(compute='_compute_display_state', store=True)
    versioning_date = fields.Datetime(default=False)
    is_active = fields.Boolean(string='Active', default=True)
    version = fields.Integer(default=0, required=False)
    display_state_ids = fields.One2many('workflow.display.state', 'wkf_id',  string='Display states', copy=True)


    @api.multi
    def new_version(self):
        """
            Crée une nouvelle version du Workflow: Copie du workflow actuel
        """
        new_rs = self.env['workflow']
        transition_obj = self.env['workflow.transition']
        for wkf in self:
            name = wkf.name
            wkf.write({'versioning_date': fields.Datetime.now(),
                        'is_active': False,
                        'name': '%s (%s)'%(name, wkf.version)})
            new_rs = self.create({'is_active': True,
                                  'name': name,
                                  'osv': wkf.osv,
                                  'version': wkf.version + 1,
                                  'on_create': wkf.on_create})
            acivities_rs = wkf.activities
            acivities_ids = acivities_rs.ids
            act_map_dict = {}
            for act_rs in acivities_rs:
                act_map_dict[act_rs.id] = act_rs.copy({'wkf_id': new_rs.id}).id
                
            for act_rs in wkf.display_state_ids:
                act_rs.copy({'wkf_id': new_rs.id})

            # Map entre anciennes et nouvelles transitions
            for transition_rs in transition_obj.search(['|', ('act_from', 'in', acivities_ids), ('act_to', 'in', acivities_ids)]):
                transition_rs.copy({'act_from': act_map_dict[transition_rs.act_from.id],
                                    'act_to': act_map_dict[transition_rs.act_to.id]})
        
        return get_form_view(self, 'base.action_workflow_form', new_rs.id, 'form,tree,diagram')



class wkf_activity(models.Model):
    _inherit = 'workflow.activity'   
    @api.one
    @api.constrains('required', 'can_not_be_deleted')
    def _check_function(self):
        if self.can_not_be_deleted and not self.required:
            raise Warning(_('This activity is required by system'))
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    required = fields.Boolean(default=True, help='If this field is checked, instances of activities in the records using this workflow cannot be deactivate')
    sequence = fields.Integer(default=0, required=False, help='Define the display order of instances of activities in the records using this workflow')
    can_not_be_deleted = fields.Boolean(default=False, readonly=True, help='If this field is checked, the activity is required by the system')
    position_x = fields.Integer()
    position_y = fields.Integer()
    
    
    @api.multi
    def unlink(self):
        for act in self:
            if act.can_not_be_deleted:
                raise Warning(_('This activity is required by system'))
                
        return super(wkf_activity, self).unlink()
    
    
    @api.model
    def save_position(self, positions):
        for act_id, vals in positions.items():
            act = self.browse(int(act_id))
            act.write({'position_x': vals['x'], 'position_y': vals['y']})
        pass
    
    
    @api.multi
    def create_display_state(self):
        display_state_obj = self.env['workflow.display.state']
        for act in self:
            display_name = act.name
            name = '_'.join(display_name.lower().split()).encode('ascii', 'replace').replace('?', '_')
            if re.search("[^a-z0-9_]+", name) != None:
                raise Warning(_('%s is not ASCII'))%(name)
            else:
                if act.action:
                    action = '%s\n%s'%(act.action, 'write({\'display_state\': \'%s\', \'state\': \'XXXX\'})'%(name))
                else:
                    action = 'write({\'display_state\': \'%s\', \'state\': \'XXXX\'})'%(name)
                    
                act.write({'action': action})
                display_state_rs = display_state_obj.search([('wkf_id', '=', act.wkf_id.id)], order='sequence desc', limit=1)
                display_state_obj.create({'wkf_id': act.wkf_id.id, 
                                          'name': name, 
                                          'label': display_name, 
                                          'sequence': (display_state_rs and display_state_rs.sequence or 0) + 10})
        
        return True



class wkf_transition(models.Model):
    _inherit = 'workflow.transition'
    #===========================================================================
    # COLUMNS
    #===========================================================================
    is_default = fields.Boolean(default=True, help='Check this box if this transition is the default transition of the activity (In case the activity is disabled, this transition process will default)')
    visible_button = fields.Boolean(default=False, help='Uncheck this box to set button invisible')
    button_label = fields.Char(size=64, required=False, translate=True, help='Label visible in the button')
    with_mail = fields.Boolean(default=False)
    with_custom_wizard = fields.Boolean(default=False)
    custom_wizard_method = fields.Char(default='', size=128)
    button_specific_sequence = fields.Integer(string='Specific sequence', default=0, required=False, help='Sequence of buttons display. If this field is at 0, it is the transition sequence who will be take into account')
    button_group_id = fields.Many2one('res.groups', string='Group Required', help='The group that a user must have to be authorized to view button.')
    mail_template_id = fields.Many2one('mail.template', string='Mail template', ondelete='restrict')
    attrs = fields.Text('Invisibility conditions', help="Invisibility conditions of button\nExample:\n['|', ('name', '=', 'abc'), ('is_model', '=', True)]\nButton will be invisible if record name is 'abc' or if record field 'is_model' is checked\nN.B.: Used fields must be in the from view of object")
    button_context = fields.Text('Context', help='Context of button. Write context without "{}" \nExample:\n("validate_order": True)')
    button_confirm = fields.Char(string="", size=224, required=False, translate=True, help='A confirm sentence display when you click on the button')
    button_class = fields.Text('Class', help="CSS class applied to the button")
    filter_group_id = fields.Many2one('workflow.transition.group', string='Group', required=False, ondelete='set null')



class wkf_instance(models.Model):
    """ 
    WKF instance
    """
    _inherit = 'workflow.instance'
    _order = 'sequence'
    
    def _auto_init(self, cr, context=None):
        super(wkf_instance, self)._auto_init(cr, context)
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = \'wkf_instance_res_type_res_id_index\'')
        if not cr.fetchone():
            cr.execute('CREATE INDEX wkf_instance_res_type_res_id_index ON wkf_instance (res_type, res_id)')
            
            
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=False)
    date = fields.Datetime(defaults=fields.Datetime.now())
    uid = fields.Many2one('res.users', string='User', ondelete='set null')
    is_active = fields.Boolean(string='Active', default=True)
    required = fields.Boolean(default=False)
    sequence = fields.Integer(default=0, required=False)
    activity_id = fields.Many2one('workflow.activity', string='Activity', required=True, ondelete='cascade')
    
    
    @api.model
    def initialize(self, model, link_field_name, link_field_id):
        wkf_obj = self.env['workflow']
        wkf_rs = wkf_obj.search([('osv', '=', model)], limit=1)
        if wkf_rs:
            for activity in wkf_rs.activities:
                if activity.flow_start:
                    self.create({
                                     'activity_id': activity.id,
                                     'name': activity.name,
                                     'required': activity.required,
                                     'sequence': activity.sequence,
                                     'progress': True,
                                     'date': fields.Datetime.now(),
                                     'uid': self.env.user.id,
                                     'res_id': link_field_id,
                                     'res_type': model,
                                     'wkf_id': wkf_rs.id,
                                         })
                else:
                    self.create({
                                     'activity_id': activity.id,
                                     'name': activity.name,
                                     'required': activity.required,
                                     'sequence': activity.sequence,
                                     'res_id': link_field_id,
                                     'res_type': model,
                                     'wkf_id': wkf_rs.id,
                                         })
                    
        return True
    
    

class wkf_display_state(models.Model):
    _name = 'workflow.display.state'
    _order = 'sequence ASC'
    #===========================================================================
    # COLUMNS
    #===========================================================================
    sequence = fields.Integer(default=0, required=True, help='Define the state order in the record status bar')
    name = fields.Char(size=64, required=True, help='Technical state name. Usable in write function')
    label = fields.Char(size=64, required=True, translate=True, help='Label visible in the record status bar')
    wkf_id = fields.Many2one('workflow', string='Workflow', required=True, ondelete='cascade')
    always_visible = fields.Boolean(default=True, help='If this field is checked, this state will be always visible in the status bar')
#     color = fields.Char(size=64, required=False)
    
    
    @api.one
    @api.constrains('name')
    def _check_name(self):
        if re.search("[^a-z0-9_]+", self.name) != None:
            raise Warning(_('Name must be ASCII'))
    
    
    @api.onchange('label')
    def onchange_label(self):
        if self.label:
            self.name = '_'.join(self.label.lower().split()).encode('ascii', 'replace').replace('?', '_')
        else:
            self.name = ''
    
    
    @api.onchange('name')
    def onchange_name(self):
        w = {}
        v = {}
        if re.search("[^a-z0-9_]+", self.name) != None:
            w = {'title': 'Error', 'message': 'Name must be ASCII'}
            self.name = '_'.join(self.label.lower().split()).encode('ascii', 'replace').replace('?', '_')
             
        return {'warning': w, 'value': v}
    
    
    
class workflow_base(models.Model):
    _name = 'workflow.base'


    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        res = super(workflow_base, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type in ('tree', 'form') and hasattr(self, 'wkf_id'):
            if self.env.context.get('active_id', False):
                self.env.cr.execute('SELECT wkf_id FROM %s WHERE id=%s LIMIT 1'%(self._table, self.env.context['active_id']))
                wkf_id = self.env.cr.dictfetchone()
                wkf_id = wkf_id and wkf_id['wkf_id']
            else:
                wkf_id = False
            
            if not wkf_id:
                self.env.cr.execute('SELECT id FROM wkf WHERE osv=%s AND is_active LIMIT 1', (self._name, ))
                wkf_id = self.env.cr.dictfetchone()
                wkf_id = wkf_id and wkf_id['id']
                
            if wkf_id:
                self.env.cr.execute('SELECT attrs_buttons, display_state_visible from wkf WHERE id=%s LIMIT 1', (wkf_id, ))
                wkf = self.env.cr.dictfetchone()
                if wkf and wkf['attrs_buttons']:
                    doc = etree.XML(res['arch'])

                    # Gestion du display state
                    selection = []
                    for display_state in self.env['workflow.display.state'].search([('wkf_id', '=', self.wkf_id and self.wkf_id.id or wkf_id)]).read(['name', 'label']):
                        selection.append((display_state['name'], display_state['label']))
                    
                    if selection:
                        res['fields']['display_state'] = {'type': 'selection', 'string': _('State'), 'selection': selection}
                        f_display = {'string': 'State', 'name': 'display_state', 'widget': 'statusbar'}
#                         A décommenter si on gère statusbar_colors
#                         if wkf['display_state_colors']:
#                             if wkf['display_state_colors']:
#                                 f_display['statusbar_colors'] = wkf['display_state_colors']
    
                        if wkf['display_state_visible']:
                            f_display['statusbar_visible'] = wkf['display_state_visible']
                            
                    if view_type == 'tree':
                        if selection:
                            # Remplacement du state par le display state
                            sn = doc.xpath("//field[@name='state']")
                            if sn:
                                sn[0].attrib['invisible'] = '1'
                                setup_modifiers(sn[0], in_tree_view=True)
                                sn_parent = sn[0].getparent()
                                sn_parent.insert(sn_parent.index(sn[0]) + 1, etree.Element('field', f_display))
                                
                    else:
                        notebook = doc.xpath("//notebook")
                        if notebook:
                            page = etree.Element('page', {'string': _('Workflow')})
                            # wkf_id pour l'admin
                            res['fields']['wkf_id'] = {'name': 'wkf_id', 'type': 'many2one', 'relation': 'workflow'}
                            workflow_id = etree.Element('field', {'name': 'wkf_id', 'groups': 'base.group_erp_manager', 'string': _('Workflow')})
                            page.append(workflow_id)
                            setup_modifiers(workflow_id)
                            # Bouton de réinitialisation du WKF pour l'admin
                            b_display = {'string': _('Reset workflow'), 'groups': 'base.group_erp_manager', 'name': 'reset_workflow', 'type': 'object', 'confirm': _('Are you sure to want to reset workflow?')}
                            b = etree.Element('button', b_display)
                            page.append(b)
                            setup_modifiers(b, b_display)
                            # Champ d'état du workflow
                            res['fields']['wkf_progress_instance'] = {'name': 'wkf_progress_instance', 'type': 'char', 'size': 128, 'compute': '_compute_wkf_progress_instance'}
                            wkf_progress_instance = etree.Element('field', {'name': 'wkf_progress_instance', 'invisible': '1'})
                            setup_modifiers(wkf_progress_instance)
                            page.append(wkf_progress_instance)
                            # Liste des activités du workflow
                            res['fields']['wkf_instance_ids'] = {'store': False, 'name': 'wkf_instance_ids', 'type': 'one2many', 'compute': '_compute_wkf_instance', 'inverse': '_write_wkf_instance', 'comodel_name': 'workflow.instance', 'relation': 'workflow.instance', 'model': self._name}
                            wkf_instance_ids = etree.Element('field', {'name': 'wkf_instance_ids', 'nolabel': '1', 'colspan': '4'})
                            setup_modifiers(wkf_instance_ids)
                            page.append(wkf_instance_ids)
                            notebook[0].append(page)
                        
                        nodes = doc.xpath("//header")
                        if not nodes:
                            nodes = doc.xpath("//form")
                            if nodes:
                                nodes[0].append(etree.Element('header'))
                                nodes = doc.xpath("//header")
                            else:
                                nodes = False

                        if nodes:
                            attrs_buttons = eval(wkf['attrs_buttons'])
                            transition_obj = self.env['workflow.transition']
                            b_list = []
                            # Champ pour les attrs des boutons et boutons
                            for b_name, b_attrs in attrs_buttons.iteritems():
                                b_vals = transition_obj.browse(b_attrs[1]).read(['button_specific_sequence', 'sequence', 'button_label', 'with_mail', 'mail_template_id', 'button_group_id', 'button_context', 'button_confirm', 'button_class', 'with_custom_wizard', 'custom_wizard_method'], load='_classic_write')[0]
                                b_list.append((b_vals['button_specific_sequence'] or b_vals['sequence'], b_name, b_vals, b_attrs))
                              
                            for dummy, b_name, b_vals, b_attrs in sorted(b_list, key=itemgetter(0), reverse=True):
                                if not b_vals['button_group_id'] or self.env.user.user_has_group(b_vals['button_group_id']):
                                    mail_context = ''
                                    wizard_context = ''
                                    if b_vals['with_custom_wizard']:
                                        wizard_context = '"custom_wizard_wkf_signal": "%s", '%(b_name)
                                        b_display = {'string': b_vals['button_label'],
                                                     'attrs': str(b_attrs[0]), 
                                                     'name': b_vals['custom_wizard_method'], 
                                                     'type': 'object'}
                                        b = etree.Element('button', b_display)
                                        if b_vals['with_mail']:
                                            mail_context = '"send_mail_wkf_signal": "%s", "send_mail_wkf_mail_template": %s,'%(b_name, b_vals['mail_template_id'])
                                            
                                    elif b_vals['with_mail']:
                                        mail_context = '"send_mail_wkf_signal": "%s", "send_mail_wkf_mail_template": %s,'%(b_name, b_vals['mail_template_id'])
                                        b_display = {'string': b_vals['button_label'],
                                                     'attrs': str(b_attrs[0]), 
                                                     'name': 'send_mail_workflow', 
                                                     'type': 'object'}
                                        b = etree.Element('button', b_display)
                                    else:
                                        b_display = {'string': b_vals['button_label'], 
                                                     'attrs': str(b_attrs[0]), 
                                                     'name': b_name}
                                    
                                    if b_vals['button_class']:
                                        b_display['class'] = b_vals['button_class']
                                        
                                    if b_vals['button_group_id']:
                                        b_display['groups'] = str(b_vals['button_group_id'])
                                        
                                    if b_vals['button_confirm']:
                                        b_display['confirm'] = b_vals['button_confirm']
                                    
                                    if mail_context or wizard_context or b_vals['button_context']:
                                        button_context = '{%s %s %s}'%(mail_context or '', wizard_context or '', b_vals['button_context'] or '')
                                        b_display['context'] = button_context
                                        
                                    b = etree.Element('button', b_display)
                                    nodes[0].insert(0, b)
                                    setup_modifiers(b, b_display)
        
                            # Remplacement du state par le display state
                            if selection:
                                state_nodes = doc.xpath("//header/field[@name='state']")
                                if state_nodes:
                                    state_nodes[0].attrib['invisible'] = '1'
                                    setup_modifiers(state_nodes[0])
                                    
                                nodes[0].insert(-1, etree.Element('field', f_display))
                            
                    res['arch'] = etree.tostring(doc)
                    
        return res
    
    
    @api.one
    def _compute_wkf_instance(self):
        if self.id:
            self.wkf_instance_ids = self.env['workflow.instance'].search([('res_type', '=', self._name), ('res_id', '=', self.id)]).ids    
        else:
            self.wkf_instance_ids = []
     
         
    @api.one
    def _compute_wkf_progress_instance(self):
        if self.id:
            self.env.cr.execute('SELECT activity_id FROM wkf_instance WHERE res_type=%s AND res_id=%s and progress=true LIMIT 1', (self._name, self.id))
            res = self.env.cr.dictfetchone()
            if res:
                self.wkf_progress_instance = res['activity_id']
            else:
                self.wkf_progress_instance = False
                  
        else:
            self.wkf_progress_instance = False
     
     
    @api.one
    @api.depends('wkf_instance_ids')
    def _write_wkf_instance(self):
        """
            Fonction inverse du One2many des actions
            Permet de créer ou de supprimer une ou plusieurs actions 
        """
        id_list = []
        # Si c'est un nouvel id, on crée un enregistrement
        # Sinon on crée une liste de comparaison avec les ids déjà présents 
        for wkfi in self.wkf_instance_ids:
            if isinstance(wkfi.id, int):
                id_list.append(wkfi.id)
            else:
                new_wkfi = utils.create_from_newid(self, wkfi)
                if new_wkfi:
                    new_wkfi.write({'res_type': self._name, 'res_id': self.id})
                    id_list.append(new_wkfi.id)
                     
                     
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wkf_instance_ids = fields.One2many('workflow.instance', compute='_compute_wkf_instance', inverse='_write_wkf_instance')
    wkf_progress_instance = fields.Char(size=128, compute='_compute_wkf_progress_instance')
    display_state = fields.Char(size=128, string='State')
    wkf_id = fields.Many2one('workflow', string='Workflow', required=False, ondelete='restrict')
    
     
    @api.multi
    def reset_workflow(self):
        """
            Remise à zero du workflow
        """
        self.delete_workflow()
        self.create_workflow()
        return {'type': 'ir.actions.client', 'tag': 'reload'}
            
        
    @api.multi
    def send_mail_workflow(self):
        """
            Fonction permettant d'envoyer un mail
        """
        mail_id = self.env.context.get('send_mail_wkf_mail_template', False)
        if mail_id and isinstance(mail_id, int):
            mail_id = self.env['mail.template'].browse(mail_id)
        else:  
            mail_id = False
          
        return self.env['mail.message'].action_send_mail(False, self._name, False, self.id, mail_id=mail_id)
            
        
    @api.multi
    def continu_workflow_after_custom(self):
        """
            Fonction permettant de faire un traitement avant d'envoyer la quotation d'une commande
        """
        context = self.env.context.copy()
        # Si un mail doit etre envoyé, on retourne le wizard de mail, qui s'occupe de la suite
        if context.get('send_mail_wkf_signal', False):
            if context.get('send_mail_wkf_signal', False):
                context.update({'send_mail_method_next': context.get('control_to_confirmed', False)})
                
            res = self.with_context(context).send_mail_workflow()
        # Sinon on passe la transition
        else:
            res = self.signal_workflow(self.env.context['custom_wizard_wkf_signal'])
            if self.env.context.get('custom_method_next', False):
                getattr(self, self.env.context['custom_method_next'])()
            
        return res
    
    
    
class workflow_transition_group(models.Model):
    """ 
    Group to allow filtering transitions 
    """
    _name = 'workflow.transition.group'
    _description = 'Group to allow filtering transitions'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True, translate=True)
        