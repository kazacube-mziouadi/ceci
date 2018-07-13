# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
from openerp.addons.base_openprod.common import get_form_view, myhtmlparser, calendar_id2real_id
from openerp.addons.base_openprod import utils

class crm_log(models.Model):
    """ 
        Logs for customer relationship management 
    """
    _name = 'crm.log'
    _description = 'Logs for customer relationship management'
    _rec_name = 'state_id'
    _order = 'sequence asc'
    
    @api.model
    def _month_get(self):
        return [
                ('1', _('January')),
                ('2', _('February')),
                ('3', _('March')),
                ('4', _('April')),
                ('5', _('May')),
                ('6', _('June')),
                ('7', _('July')),
                ('8', _('August')),
                ('9', _('September')),
                ('10', _('October')),
                ('11', _('November')),
                ('12', _('December')),
                       ]
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    #En-tête
    state_id = fields.Many2one('crm.state', string='Action', required=False, ondelete='set null')
    sequence = fields.Integer(string='Sequence', default=0, required=False)
    year = fields.Char(string='Year', size=4, required=False)
    date = fields.Date(string='Date')
    month = fields.Selection('_month_get', string='Month')
    user_id = fields.Many2one('res.users', string='User', required=False, ondelete='restrict')
    time = fields.Integer(string='Time', default=0, required=False, group_operator='avg')
    crm_id = fields.Many2one('crm', string='CRM', required=False, ondelete='cascade')
    
    
    
class crm_state(models.Model):
    """ 
        States for customer relationship management 
    """
    
    _name = 'crm.state'
    _description = 'States for customer relationship management'
    _order = 'sequence'
    def _auto_init(self, cursor, context=None):
        """
            Un seul enregistrement avec is_sale_creation_state
        """
        res = super(crm_state, self)._auto_init(cursor, context=context)
        cursor.execute('SELECT indexname FROM pg_indexes WHERE indexname = \'only_one_is_sale_creation_state\'')
        if not cursor.fetchone():
            cursor.execute('CREATE UNIQUE INDEX only_one_is_sale_creation_state ON crm_state (is_sale_creation_state) WHERE is_sale_creation_state')
             
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
    
    
    
class crm_origin(models.Model):
    """ 
        Origin for customer relationship management 
    """
    _name = 'crm.origin'
    _description = 'Origin for customer relationship management'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    #En-tête
    name = fields.Char('Name', required=True, translate=True)
    comments = fields.Char('Comments')
    
    
    
class crm_category(models.Model):
    """ 
        Categories for customer relationship management 
    """
    _name = 'crm.category'
    _description = 'Categories for customer relationship management'
    _parent_name = "parent_id"
    _parent_store = True
    _parent_order = 'name'
    _order = 'parent_left'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    #En-tête
    name = fields.Char('Name', required=True)
    description = fields.Text(string='Description')
    parent_left = fields.Integer(string='Parent left', select=True)
    parent_right = fields.Integer(string='Parent right', select=True)
    parent_id = fields.Many2one('product.category', string='Parent category', required=False, ondelete='cascade', select=True)
    child_ids = fields.One2many('product.category', 'parent_id',  string='Child categories')
    
    @api.multi
    @api.constrains('parent_id')    
    def _check_recursion(self):
        """
            Verifie la non recursivité (100 niveaux maximum)
        """
        level = 100
        ids = self.ids
        while len(ids):
            self._cr.execute('select distinct parent_id from product_category where id IN %s',(tuple(ids),))
            ids = filter(None, map(lambda x:x[0], self._cr.fetchall()))
            if not level:
                raise Warning(_('Error ! You cannot create recursive categories.'))
            
            level -= 1
            
        return True



class crm(models.Model):
    """ 
        Customer relationship management 
    """
    _name = 'crm'
    _inherit = 'workflow.base'
    _description = 'Customer relationship management'
    
    
    @api.one
    def _compute_mail(self):
        self.mail_ids = self.env['mail.mail'].search([('model', '=', 'crm'), ('res_id', '=', self.id)]).ids
        
           
    @api.one
    def _compute_nb_actions(self):
        self.nb_actions = len([event for event in self.user_event_ids if event.state_id and not event.state_id.end_state])
        
           
    @api.one
    def _compute_next_action(self):
        """
            On récupère la date et le responsable de la prochaine action
        """
        next_action_date = False
        next_action_user_id = False
        next_action = self.env['calendar.event'].search([('crm_id', '=', self.id), ('state_id.end_state', '=', False)], limit=1, order='stop_datetime asc')
        if next_action:
            next_action_date = next_action.stop_datetime
            next_action_user_id = next_action.affected_user_id.id
        
        self.next_action_date = next_action_date
        self.next_action_user_id = next_action_user_id
         
    
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

            self.trunc_description = description[:30] + '...'
        else:
            self.trunc_description = '...'
        
        
    @api.one
    def _compute_color(self):
        today = fields.Date.today()
        color = 0
        if self.limit_date and today > self.limit_date:
            color = 2
        
        self.color = color
        
        
    @api.one
    @api.depends('estimated_revenue', 'success_percent')
    def _compute_estimated_revenue_avg(self):
        """
            On calcule CA estimé en prenant en compte le % de réussite:
            CA estimé * % de réussite
        """
        estimated_revenue_avg = 0
        if self.success_percent != 0:
            estimated_revenue_avg = self.estimated_revenue * (self.success_percent / 100.0)
            
        self.estimated_revenue_avg = estimated_revenue_avg
        

    @api.one
    @api.depends('category_ids', 'category_ids.name')
    def _compute_concat_category(self):
        """
            Champ qui concatène les catégories pour l'affichage en vue kanban
        """
        concat_category = ''
        for category in self.category_ids:
            if not concat_category:
                concat_category = category.name
            else:
                concat_category = ' %s, %s'%(concat_category,category.name)
                
        self.concat_category = concat_category
        
    
    @api.model
    def _criticity_get(self):
        return [
                ('normal', _('Normal')),
                ('critical', _('Critical')),
                ]
    
    
    @api.model
    def _read_group_state_ids(self, present_ids, domain, **kwargs):
        folded = {}
        states_list = []
        state_search = self.env['crm.state'].search([])
        for state in state_search:
            states_list.append((state.id, state.name))
            folded[state.id] = state.fold
        
        return states_list, folded
    
    
    def _default_new_state_id(self):
        new_state_rcs = self.env['crm.state'].search([('is_new_state', '=', True)], limit=1)
        res = new_state_rcs and new_state_rcs.id or False
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    #En-tête
    name = fields.Char('Opportunity name', required=False, readonly=True, default="/", copy=False)
    state_id = fields.Many2one('crm.state', string='State', required=False, ondelete='restrict',
                               default=_default_new_state_id)
    criticality = fields.Selection('_criticity_get', string='Criticality', required=True)
    salesman_id = fields.Many2one('res.users', string='Salesman', required=False, ondelete='restrict')
    creation_date = fields.Date(string='Creation date', default=lambda self: fields.Date.today())
    customer_id = fields.Many2one('res.partner', string='Customer', required=False, ondelete='restrict')
    origin_id = fields.Many2one('crm.origin', string='Origin', required=False, ondelete='restrict')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, ondelete='restrict', 
                                  default=lambda self: self.env.ref('base.EUR'))
    estimated_revenue = fields.Float(string='Estimated revenue', default=0.0, required=False)
    success_percent = fields.Float(string='% of success', default=0.0, required=False)
    limit_date = fields.Date(string='Treatment limit date')
    customer_name = fields.Char(string='Name', size=25, required=False)
    street = fields.Char(string='Street', size=128, required=False)
    street2 = fields.Char(string='Street 2', size=128, required=False)
    street3 = fields.Char(string='Street 3', size=128, required=False)
    zip = fields.Char(string='Zip', size=24, required=False)
    city = fields.Char(string='City', size=128, required=False)
    region_id = fields.Many2one('res.region', string='Region', required=False, ondelete='restrict')
    country_id = fields.Many2one('res.country', string='Country', required=False, ondelete='restrict')
    phone = fields.Char(string='Phone', size=20, required=False)
    email = fields.Char(string='Email', size=128, required=False)
    category_ids = fields.Many2many('crm.category',
                'openprod_crm_category_rel', 'openprod_crm_id', 'openprod_category_id', string='Categories')
    concat_category = fields.Char(string='Categories', size=256, compute='_compute_concat_category', store=True)
    b2c_flag = fields.Boolean(string='B2C', default=lambda self:self.env.user.crm_b2c)
    #Description et action
    description = fields.Html(string='Description')
    trunc_description = fields.Text(string='Truncate description', compute='_compute_trunc_description')
    user_event_ids = fields.One2many('calendar.event', 'crm_id', string='Actions')
    #Communication
    contact_ids = fields.Many2many('res.partner', 'crm_contact_opportunity_rel', 'opportunity_contact_id',
                                    'opportunity_id', string='Contacts', domain=[('is_company', '=', False)])
    mail_ids = fields.One2many('mail.mail', string='Mails', compute='_compute_mail', readonly=True)
    #Note
    note_ids = fields.One2many('note.openprod', 'crm_id', string='Notes')
    document_ids = fields.Many2many('document.openprod', 'crm_document_openprod_rel', 'crm_id', 'document_id', 
                                    string='Documents', copy=True)
    #Historique
    end_date = fields.Date(string='End date', readonly=True)
    log_ids = fields.One2many('crm.log', 'crm_id',  string='Logs', readonly=True)
    #Vue kanban
    color = fields.Integer(string='Color', default=5, required=False, compute='_compute_color')
    nb_actions = fields.Integer(string='Actions', default=0, required=False, compute='_compute_nb_actions')
    next_action_user_id = fields.Many2one('res.users', string='Next action responsible', required=False, ondelete='set null', compute='_compute_next_action')
    next_action_date = fields.Date(string='Next action date', compute='_compute_next_action')
    #Vue pivot
    estimated_revenue_avg = fields.Float(string='Forecast revenue', default=0.0, compute='_compute_estimated_revenue_avg',
                                         store=True)
    
    sale_ids = fields.One2many('sale.order', 'crm_id',  string='Sale orders')
    
    _group_by_full = {
        'state_id': _read_group_state_ids
    }
    
    @api.onchange('customer_id')
    def _onchange_customer_id(self):
        """
            Permet de récupérer le commercial du client ainsi que les informations de son adresse et de ses moyens
            de communication
        """
        customer = self.customer_id
        if customer:
            if not self.b2c_flag:
                self.salesman_id = customer.seller_id and customer.seller_id.id or False
                
            self.customer_name = customer.name
            self.street = customer.street
            self.street2 = customer.street2
            self.street3 = customer.street3
            self.city = customer.city
            self.region_id = customer.region_id and customer.region_id.id or False
            self.zip = customer.zip
            self.country_id = customer.country_id and customer.country_id.id
            self.phone = customer.phone
            self.email = customer.email
        else:
            if not self.b2c_flag:
                self.salesman_id = False
                
            self.customer_name = False
            self.street = ''
            self.street2 = ''
            self.street3 = ''
            self.city = ''
            self.region_id = False
            self.zip = ''
            self.country_id = False
            self.phone = ''
            self.email = ''
    
    
    @api.onchange('country_id')
    def _onchange_country_id(self):
        """
            Si on change de pays, on vide le champ de la région
        """
        if self.region_id and self.region_id.country_id != self.country_id:
            self.region_id = False
             
    
    @api.multi
    def create_new_partner_action(self):
        """
            Fonction qui vérifie qu'il y ai bien un nom et un pays pour afficher le wizard
            de création de partenaire
        """
        for crm in self:
            if not crm.customer_name or not crm.country_id:
                raise except_orm(_('Error'), _('You need a name and a country to create a partner'))
            else:
                action_dict = get_form_view(self, 'crm_openprod.action_create_new_customer_crm')
                if action_dict and action_dict.get('id') and action_dict.get('type'):
                    action = self.env[action_dict['type']].browse(action_dict['id'])
                    action_struc = action.read()
                    action_struc = action_struc[0]
                    return action_struc
                
                
    @api.multi
    def create_new_sale(self):
        """
            Fonction qui permet de créer une vente à partir de la CRM
        """
        sale_obj = self.env['sale.order']
        state = self.env['crm.state'].search([('is_sale_creation_state', '=', True)], limit=1)
        for crm in self:
            if crm.customer_id:
                if crm.customer_id.state != 'qualified':
                    raise except_orm(_('Error'), _('You can\'t create a sale with a customer not qualified'))
                else:
                    new_sale = sale_obj.create_sale(self.customer_id.id, False, fields.Date.today(), {'crm_id': crm.id})
                    if state:
                        crm.write({'state_id': state.id})
                        
                    action_dict = get_form_view(self, 'sale.sale_order_see_form')
                    if action_dict and action_dict.get('id') and action_dict.get('type'):
                        action = self.env[action_dict['type']].browse(action_dict['id'])
                        action_struc = action.read()
                        action_struc[0]['res_id'] = new_sale.id
                        action_struc = action_struc[0]
                        return action_struc 
            
            return True
    
    
    @api.multi
    def action_send_mail(self):
        return self.env['mail.message'].action_send_mail(self.customer_id, 'crm', '',self.id)
    
    
    @api.model
    def create(self, vals):
        """
            Création du nom à partir de la séquence de la CRM
            Et saisi du premier log
        """
        if not vals:
            vals={}
            
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].get('crm') or '/'
        
        if vals.get('state_id'):
            state = self.env['crm.state'].browse(vals['state_id'])
            if state:
                today = fields.Date.today()
                if state.is_end:
                    vals['end_date'] = today
                    
                month = str(fields.Date.from_string(fields.Date.today()).month)
                year = str(fields.Date.from_string(fields.Date.today()).year)
                log_values = {'name': state.id,
                              'date': today,
                              'month': month,
                              'user_id': self.env.user.id,
                              'sequence': 1,
                              'year': year}
                vals['log_ids'] = [(0,0,log_values)]
        
        res = super(crm, self).create(vals)
        return res
    
    
    @api.multi
    def copy(self, default=None):
        """
            On vide certains champs et on passe l'état à "nouveau"
        """
        if not default:
            default = {}
            
        #On recherche l'id de l'état "Nouveau"
        new_state = self.env['crm.state'].search([('is_new_state', '=', True)], limit=1)
        default['state_id'] = new_state and new_state.id or False
        return super(crm, self).copy(default=default)
    
    
    @api.multi
    def write(self, vals=None):
        """
            On crée une ligne de log si l'état a été modifié
        """
        if not vals:
            vals = {}
        
        if vals.get('state_id'):
            log_obj = self.env['crm.log']
            state_obj = self.env['crm.state']
            state = state_obj.browse(vals['state_id'])
            if state:
                previous_sequence = 0
                time = 0
                month = str(fields.Date.from_string(fields.Date.today()).month)
                year = str(fields.Date.from_string(fields.Date.today()).year)
                today = fields.Date.today()
                if state.is_end:
                    vals['end_date'] = today
                else:
                    vals['end_date'] = False
                    
                log_read = log_obj.search_read([('crm_id', '=', self.id)], ['sequence', 'date'], limit=1, order='sequence desc')
                if log_read:
                    previous_sequence = log_read[0]['sequence']
                    previous_date = log_read[0]['date']
                    time_delta = fields.Date.from_string(today) - fields.Date.from_string(previous_date)
                    time = time_delta.days
                    
                log_values = {'state_id': state.id,
                              'date': today,
                              'month': month,
                              'user_id': self.env.user.id,
                              'sequence': previous_sequence + 1,
                              'time': time,
                              'year': year}
                vals['log_ids'] = [(0,0,log_values)]
                #On recherche l'id de l'état "Perdu" et "Gagné" pour modifier le pourcentage de réussite
                win_state = state_obj.search([('is_won_state', '=', True)], limit=1)
                lost_state = state_obj.search([('is_lost_state', '=', True)], limit=1)
                if win_state and state == win_state:
                    vals['success_percent'] = 100
                elif lost_state and state == lost_state:
                    vals['success_percent'] = 0
                
        res = super(crm, self).write(vals)
        return res
    
    
    @api.multi
    def unlink(self):
        """
            Lorsqu'on supprime l'opportunité, on supprime les mails qui lui sont liés
        """
        for opportunity in self:
            mail_rs = self.env['mail.mail'].search([('model', '=', 'crm'), ('res_id', '=', opportunity.id)])
            mail_rs = self.env['mail.message'].search([('model', '=', 'crm'), ('res_id', '=', opportunity.id)])
            mail_rs.unlink()
            
        return super(crm, self).unlink()
    
