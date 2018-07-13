# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from datetime import datetime, timedelta
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm, ValidationError, Warning
from openerp.addons.base_openprod.common import get_form_view, myhtmlparser, calendar_id2real_id
from dateutil.relativedelta import relativedelta



class crm_reclaim_state(models.Model):
    """ 
        States for CRM reclaim
    """
    
    _name = 'crm.reclaim.state'
    _description = 'States for CRM reclaim'
    _order = 'sequence'
    def _auto_init(self, cursor, context=None):
        """
            Un seul enregistrement avec is_sale_creation_state
        """
        res = super(crm_reclaim_state, self)._auto_init(cursor, context=context)
        cursor.execute('SELECT indexname FROM pg_indexes WHERE indexname = \'only_one_is_crm_reclaim_state\'')
        if not cursor.fetchone():
            cursor.execute('CREATE UNIQUE INDEX only_one_is_crm_reclaim_state ON crm_reclaim_state (is_sale_creation_state) WHERE is_sale_creation_state')
             
        return res
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    #En-tête
    name = fields.Char('Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=0, required=False)
    description = fields.Text(string='Description')
    
    fold = fields.Boolean(string='Folded in kanban view', default=False, help='This stage is folded in the kanban view when'
                               'there are no records in that stage to display.')
    is_end = fields.Boolean(string='Is CRM end', default=False, help='This stage is the end of the crm process. For example '
                            'state "Won" or "Lost"')
    is_sale_creation_state = fields.Boolean(default=False, help='State in which the record will pass when a sale order will be created')
    is_new_state = fields.Boolean(default=False, string='Is new state', help='State in which the record will pass when you create a new CRM')
    is_won_state = fields.Boolean(default=False, string='Is won state', help='State in which the record will pass when the CRM is won')
    is_lost_state = fields.Boolean(default=False, string='Is lost state', help='State in which the record will pass when the CRM is lost')
    
    _sql_constraints = [
        ('unique_sequence', 'unique(sequence)', 'Error: There is already an other state with this sequence.'),
    ]
    
    

class crm_reclaim(models.Model):
    """ 
        CRM Reclaim 
    """
    _name = 'crm.reclaim'
    _description = 'CRM Reclaim'
    _rec_name = 'sequence'

    
    @api.model
    def _state_get(self):
        return [
                ('new', _('New')),
                ('waiting', _('Waiting')),
                ('progress', _('Progress')),
                ('done', _('Done')),
                ('cancel', _('Cancel')),
                       ]
    
    
    @api.model
    def _criticality_get(self):
        return [
                ('base', _('Base')),
                ('normal', _('Normal')),
                ('critical', _('Critical')),
                       ]
    
    
    @api.one
    def _compute_mail(self):
        self.mail_ids = self.env['mail.mail'].search([('model', '=', 'crm.reclaim'), ('res_id', '=', self.id)]).ids
    
    
    @api.one
    def _compute_color(self):
        today = fields.Date.today()
        color = 0
        if self.processing_date and today > self.processing_date:
            color = 2
        
        self.color = color
    
    
    @api.one
    @api.depends('park_id')
    def _compute_customer_park_id(self):
        self.customer_park_id = self.park_id and self.park_id.customer_id and self.park_id.customer_id.id or False
        
    
    
    @api.model
    def _read_group_state_ids(self, present_ids, domain, **kwargs):
        folded = {}
        states_list = []
        state_search = self.env['crm.reclaim.state'].search([])
        for state in state_search:
            states_list.append((state.id, state.name))
            folded[state.id] = state.fold
        
        return states_list, folded
    
    
    def _default_new_state_id(self):
        new_state_rcs = self.env['crm.reclaim.state'].search([('is_new_state', '=', True)], limit=1)
        res = new_state_rcs and new_state_rcs.id or False
        return res
    
    
    @api.one
    def _compute_next_action(self):
        """
            On récupère la date et le responsable de la prochaine action
        """
        next_action_date = False
        next_action_user_id = False
        next_action = self.env['calendar.event'].search([('crm_reclaim_id', '=', self.id), ('state_id.end_state', '=', False)], limit=1, order='stop_datetime asc')
        if next_action:
            next_action_date = next_action.stop_datetime
            next_action_user_id = next_action.affected_user_id.id
        
        self.next_action_date = next_action_date
        self.next_action_user_id = next_action_user_id
    
    
    @api.one
    def _compute_nb_actions(self):
        nb_actions = len([event.id for event in self.action_ids if event.state_id and not event.state_id.end_state])
        self.nb_actions = nb_actions
    
    
    @api.one
    def _compute_trunc_description(self):
        """
            On ne récupère que les 30 premiers caractères de
            la description pour l'afficher dans la vue kanban.
            Pour cela, on extrait le texte du champ HTML
        """
        if self.description:
            description = ''
            parser = myhtmlparser()
            parser.feed(self.description)
            data = parser.HTMLDATA
            parser.clean()
            for text in data:
                description += text + ' '

            self.trunc_description = description[:20] + '...'
        else:
            self.trunc_description = '...'
            
            
    #===========================================================================
    # COLUMNS
    #===========================================================================
    sequence = fields.Char(string='Name', size=128, default='/')
    state_id = fields.Many2one('crm.reclaim.state', string='State', required=False, ondelete='restrict',
                               default=_default_new_state_id)
    criticality = fields.Selection('_criticality_get', string='Criticality')
    responsible_id = fields.Many2one('res.users', string='Responsible', required=True, ondelete='restrict')
    customer_id = fields.Many2one('res.partner', string='Customer', required=True, ondelete='restrict')
    date_create = fields.Date(string='Create date', required=True, default=lambda *a: fields.Date.today())
    category_ids = fields.Many2many('crm.reclaim.category', 'crm_reclaim_category_rel', 'reclaim_id', 'category_id', string='Categories')
    processing_date = fields.Date(string='Processing date')
    park_id = fields.Many2one('park', string='Park', required=False, ondelete='restrict')
    end_date = fields.Date(string='End date')
    return_picking_id = fields.Many2one('stock.picking', string='Return picking', required=False, ondelete='restrict')
    intervention_id = fields.Many2one('intervention', string='Intervention', required=False, ondelete='restrict')
    cause_id = fields.Many2one('crm.reclaim.cause', string='Cause', required=False, ondelete='restrict')
    description = fields.Text(string='Description')
    action_ids = fields.One2many('calendar.event', 'crm_reclaim_id',  string='Action')
    contact_ids = fields.Many2many('res.partner', 'crm_reclaim_contact_rel', 'reclaim_id', 'contact_id', string='Contacts', domain=[('is_company', '=', False)])
    mail_ids = fields.One2many('mail.mail', string='Mails', compute='_compute_mail', readonly=True)
    note_ids = fields.One2many('crm.reclaim.note', 'crm_reclaim_id',  string='Notes')
    document_ids = fields.One2many('crm.reclaim.document', 'crm_reclaim_id',  string='Documents')
    customer_park_id = fields.Many2one('res.partner', string='Customer park', compute='_compute_customer_park_id')
    #Vue kanban
    color = fields.Integer(string='Color', default=5, required=False, compute='_compute_color')
    nb_actions = fields.Integer(string='Actions', default=0, required=False, compute='_compute_nb_actions')
    next_action_user_id = fields.Many2one('res.users', string='Next action responsible', required=False, ondelete='set null', compute='_compute_next_action')
    next_action_date = fields.Date(string='Next action date', compute='_compute_next_action')
    trunc_description = fields.Text(string='Truncate description', compute='_compute_trunc_description')
    
    
    
    _group_by_full = {
        'state_id': _read_group_state_ids
    }
    
    
    @api.onchange('park_id')
    def _onchange_park_id(self):
        """
        """
        if self.park_id:
            self.customer_id = self.park_id.customer_id.id
            
            
    #===========================================================================
    # button
    #===========================================================================
    @api.model
    def create(self, vals):
        res = super(crm_reclaim, self).create(vals)
        res.write({'sequence': self.env['ir.sequence'].get('sequence.crm.reclaim.generation')})
        return res
        
    
#     @api.multi 
#     def wkf_new(self):
# #         self.write({'state': 'new'})
#     
#     
#     @api.multi
#     def wkf_waiting(self):
# #         self.write({'state': 'waiting'})
#     
#     
#     @api.multi
#     def wkf_progress(self):
# #         self.write({'state': 'progress'})
#     
#     
#     @api.multi
#     def wkf_done(self):
# #         self.write({'state': 'done'})
#         
#      
#     @api.multi   
#     def wkf_cancel(self):
# #         self.write({'state': 'cancel'})
#     
    
    @api.multi
    def button_create_intervention(self):
        interv_obj = self.env['intervention']
        for crm_reclaim in self:
            vals = {'start_date_requested': fields.Date.today(),
                    'emergency': 'high',
                    'park_id': crm_reclaim.park_id.id,
                    'type': 'preventive'
            }
            if crm_reclaim.park_id.type == 'external':
                vals['customer_id'] = crm_reclaim.park_id.customer_id.id
                vals['currency_id'] = crm_reclaim.park_id.customer_id.currency_id.id
            
            vals['type_invoice'] = 'billable'
            intervention_rcs = interv_obj.create(vals)
            crm_reclaim.write({'intervention_id': intervention_rcs.id})
            return {
                    'name': _('Intervention'),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'intervention',
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'res_id': intervention_rcs.id,
                    'nodestroy': True,
            }
            
        return True
    
    
    @api.multi
    def button_return_move(self):
        move_label_obj = self.env['stock.move.label']
        move_obj = self.env['stock.move']
        for crm_reclaim in self:
            move_label_rcs = move_label_obj.search([('label_id', '=', crm_reclaim.park_id.num_serie_id.id)])
            move_ids = [move_label_read['move_id'] for move_label_read in move_label_rcs.read(['move_id'], load='_classic_write')]
            if move_ids:
                move_ids = list(set(move_ids))
                arg_move = [('type', '=', 'out'), ('id', 'in', move_ids), ('picking_id', '!=', False), ('sale_line_id', '!=', False)]
                move_rcs = move_obj.search(arg_move, order='date desc', limit=1)
                if not move_rcs:
                    arg_move = [('type', '=', 'out'), ('id', 'in', move_ids), ('picking_id', '!=', False)]
                    move_rcs = move_obj.search(arg_move, order='date desc', limit=1)
                
                if move_rcs:
                    picking_id = move_rcs.picking_id.id
                    crm_reclaim.write({'return_picking_id': picking_id})
                    move_and_label_rcs = [(move_rcs.id, crm_reclaim.park_id.num_serie_id.id, crm_reclaim.park_id.num_serie_id.origin_uom_qty)]
                    return {
                            'name': _('Return picking'),
                            'view_type': 'form',
                            'view_mode': 'form',
                            'res_model': 'stock.return.picking',
                            'type': 'ir.actions.act_window',
                            'target': 'new',
                            'nodestroy': True,
                            'context': {'move_and_label_rcs': move_and_label_rcs, 'picking_id': picking_id, 'park_id': crm_reclaim.park_id.id, 'authorize_return': True}
                    }
                
                else:
                    raise except_orm(_('Error'), _('No move out.'))
            
        return True
    
    
    
    @api.multi
    def action_send_mail(self):
        return self.env['mail.message'].action_send_mail(False, 'crm.reclaim', '', self.id)
    
    
    @api.multi
    def copy(self, default=None):
        """
            On vide certains champs et on passe l'état à "nouveau"
        """
        if not default:
            default = {}
            
        #On recherche l'id de l'état "Nouveau"
        new_state = self.env['crm.reclaim.state'].search([('is_new_state', '=', True)], limit=1)
        default['state_id'] = new_state and new_state.id or False
        return super(crm_reclaim, self).copy(default=default)
    
    

class crm_reclaim_category(models.Model):
    """ 
    CRM reclaim category 
    """
    _name = 'crm.reclaim.category'
    _description = 'CRM reclaim category'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    
    
    
class crm_reclaim_cause(models.Model):
    """ 
    CRM reclaim cause
    """
    _name = 'crm.reclaim.cause'
    _description = 'CRM reclaim cause'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    
    
    
class crm_reclaim_note(models.Model):
    """ 
    CRM reclaim note
    """
    _name = 'crm.reclaim.note'
    _description = 'CRM reclaim note'
    _rec_name = 'user_id'
    _order = 'date desc'
    
    
    @api.model
    def _type_get(self):
        return [
                ('internal', _('Internal')),
                 ('external', _('External')),
                       ]

    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='restrict')
    type = fields.Selection('_type_get', string='Type', default='internal', required=True)
    subject = fields.Char(string='subject', size=128, required=True)
    description = fields.Text(string='Description')
    date = fields.Date(string='Date', required=True, default=lambda *a: fields.Date.today())
    crm_reclaim_id = fields.Many2one('crm.reclaim', string='CRM reclaim', required=False, ondelete='cascade')
    
    
    
class crm_reclaim_document(models.Model):
    """ 
    CRM reclaim document
    """
    _name = 'crm.reclaim.document'
    _description = 'CRM reclaim document'
    _order = 'date desc'
    
    
    @api.one
    def _get_document_binary_filesystem(self):
        attachment_obj = self.env['ir.attachment']
        attachment_rs = attachment_obj.search([('res_model','=',self._name),('res_id','=',self.id),('binary_field','=','document')])
        if attachment_rs:
            self['document'] = attachment_rs[0].datas
        else:
            self.document = False
    
    @api.one
    def _set_document_binary_filesystem(self):
        attachment_obj = self.env['ir.attachment']
        attachment_rs = attachment_obj.search([('res_model','=',self._name),('res_id','=',self.id),('binary_field','=','document'),('is_binary_field','=',True)])
        if self.document:
            if attachment_rs:
                attachment_rs.datas = self.document
            else:
                attachment_obj.create({'res_model': self._name, 'res_id': self.id, 'name': 'document datas' , 'is_binary_field': True, 'binary_field': 'document', 'datas': self.document, 'datas_fname':'document datas'})
        else:
            attachment_rs.unlink()
        
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='subject', size=128, required=True)
    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='restrict', default=lambda self: self.env.uid)
    type = fields.Many2one('crm.reclaim.document.type', string='Type', required=True, ondelete='restrict')
    date = fields.Date(string='Date', required=True, default=lambda *a: fields.Date.today())
    document  = fields.Binary(string='Document', compute='_get_document_binary_filesystem', inverse='_set_document_binary_filesystem')
    crm_reclaim_id = fields.Many2one('crm.reclaim', string='CRM reclaim', required=False, ondelete='cascade')



class crm_reclaim_document_type(models.Model):
    """ 
    CRM reclaim document type
    """
    _name = 'crm.reclaim.document.type'
    _description = 'CRM reclaim document type'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)    
