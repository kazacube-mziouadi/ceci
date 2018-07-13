# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.addons.base_openprod import utils
from openerp.tools.translate import _


class affair_state(models.Model):
    """ 
        States for affair 
    """
    _name = 'affair.state'
    _description = 'States for affair'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    #En-tête
    name = fields.Char('Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=0, required=False)
    description = fields.Text(string='Description')
    fold = fields.Boolean(string='Folded in kanban view', default=False, help='This stage is folded in the kanban view when'
                                                                               'there are no records in that stage to display.')
    is_end = fields.Boolean(string='Is affair end', default=False, help='This stage is the end of the affair process. For example state "Done"')
    
    _sql_constraints = [
        ('unique_sequence', 'unique(sequence)', 'Error: There is already an other state with this sequence.'),
    ]
    
    

class affair(models.Model):
    """ 
        Affair 
    """
    _name = 'affair'
    _description = 'Affair'
    
    @api.model
    def _type_get(self):
        return [
                ('standard', 'Standard'),
                ('specific', 'Specific'),
                       ]

        
    @api.model
    def _criticality_get(self):
        return [
                ('critical', 'Critical'),
                ('normal', 'Normal')
                       ]


    @api.one
    def _compute_mail(self):
        self.mail_ids = self.env['mail.mail'].search([('model', '=', 'affair'), ('res_id', '=', self.id)]).ids
    
    
    @api.one
    def _compute_color(self):
        today = fields.Date.today()
        color = 0
        if self.limit_date and today > self.limit_date:
            color = 2
        
        self.color = color
    
    
    @api.one
    def _compute_nb_actions(self):
        self.nb_actions = len(self.user_event_ids)
    
    
    @api.model
    def _read_group_state_ids(self, present_ids, domain, **kwargs):
        folded = {}
        states_list = []
        state_search = self.env['affair.state'].search([])
        for state in state_search:
            states_list.append((state.id, state.name))
            folded[state.id] = state.fold
        
        return states_list, folded
        

    @api.multi
    def name_get(self):
        return [(x.id, "[%s] %s" % (x.code, x.name)) for x in self]
        

    @api.one
    @api.depends()
    def _compute_costs(self):
        wo_read = self.env['mrp.workorder'].search([('affair_id', '=', self.id), ('level', '=', 0), ('mo_level', '=', 0)]).read(['theo_total_cost', 'real_total_cost'])
        self.wo_theo_cost = wo_theo_cost = sum([x['theo_total_cost'] for x in wo_read] or [])
        self.wo_real_cost = wo_real_cost = sum([x['real_total_cost'] for x in wo_read] or [])
        self.sol_price = sol_price = sum([x['total_price_currency'] for x in self.sol_ids.read(['total_price_currency'])] or [])
        self.profit_margin_real = sol_price - wo_real_cost  
        self.profit_margin_theo = sol_price - wo_theo_cost  
        

    @api.one
    @api.depends()
    def _compute_display_name(self):
        self.display_name = u"[%s] %s" % (self.code, self.name)
            
            
    #===========================================================================
    # COLUMNS
    #===========================================================================
    # Entête
    name = fields.Char(required=True, copy=False)
    display_name = fields.Char(size=64, string='Name', compute='_compute_display_name')
    code = fields.Char(string='Code', default="/", required=True, size=32, help='The code must be unique')
    customer_id = fields.Many2one('res.partner', string='Customer', required=False, ondelete='restrict')
    responsible_id = fields.Many2one('res.users', string='Responsible', required=True, ondelete='restrict', oldname="commercial_id")
    type = fields.Selection('_type_get', string='Type', required=True, default='specific')
    criticality = fields.Selection('_criticality_get', required=True, string='Criticality', default='normal')
    date = fields.Date(string='Create date')
    limit_date = fields.Date(string='Limit date')
    end_date = fields.Date(string='End date')
    state_id = fields.Many2one('affair.state', string='State', required=False, ondelete='restrict', default=lambda self: self.env.ref('affair.affair_state_draft'))
    # Description
    user_event_ids = fields.One2many('calendar.event', 'affair_id', string='Actions')
    description = fields.Html(string='Description')
    # Communication
    mail_ids = fields.One2many('mail.mail', string='Mails', compute='_compute_mail', readonly=True)
    # Note
    note_ids = fields.One2many('note.openprod', 'affair_id', string='Notes')
    document_ids = fields.Many2many('document.openprod', 'affair_document_openprod_rel', 'affair_id', 'document_id',  string='Document', copy=True)
    directory_id = fields.Many2one('document.directory', string="Directory", ondelete='restrict')
    # Vente
    sol_ids = fields.One2many('sale.order.line', 'affair_id',  string='Sale order lines')
    # Données tehniques
    bom_ids = fields.One2many('mrp.bom', 'affair_id',  string='BoM lines')
    rl_ids = fields.One2many('mrp.routing.line', 'affair_id',  string='Routing lines')
    # Production
    wo_ids = fields.One2many('mrp.workorder', 'affair_id',  string='Work orders')
    # Purchase
    pol_ids = fields.One2many('purchase.order.line', 'affair_id',  string='Purchase lines')
    #Vue kanban
    color = fields.Integer(string='Color', default=5, required=False, compute='_compute_color')
    nb_actions = fields.Integer(string='Actions', default=0, required=False, compute='_compute_nb_actions')
    # Couts
    sol_price = fields.Float(string='Sale price', compute='_compute_costs', digits=dp.get_precision('Product price'))
    wo_real_cost = fields.Float(string='Real WO costs', compute='_compute_costs', digits=dp.get_precision('Product price'))
    wo_theo_cost = fields.Float(string='Theorical WO costs', compute='_compute_costs', digits=dp.get_precision('Product price'))
    profit_margin_real = fields.Float(string='Real profit margin', compute='_compute_costs', digits=dp.get_precision('Product price'))
    profit_margin_theo = fields.Float(string='Theorical profit margin', compute='_compute_costs', digits=dp.get_precision('Product price'))
    
    phase_ids = fields.One2many('project.phase', 'affair_id',  string='Phases')
    

    
    _group_by_full = {
        'state_id': _read_group_state_ids
    }
    
    
    #===========================================================================
    # Onchange
    #===========================================================================
    
    @api.onchange('customer_id')
    def _onchange_customer_id(self):
        """
        """
        self.responsible_id = self.customer_id and (self.customer_id.seller_id and self.customer_id.seller_id.id or self.customer_id.sales_manager_id or self.customer_id.sales_manager_id.id) or False
        

    #===========================================================================
    # Button
    #===========================================================================
    
    @api.multi
    def compute_wo_level(self):
        for affair in self:
            if affair.wo_ids:
                affair.wo_ids.compute_sorting_level()
                
    
    @api.multi
    def action_send_mail(self):
        return self.env['mail.message'].action_send_mail(self.customer_id, 'affair', '',self.id)
    
    @api.model
    def create(self, vals):
        if vals.get('code', '/') == '/':
            vals['code'] = self.env['ir.sequence'].get('affair')
        return super(affair, self).create(vals)