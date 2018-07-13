# coding: utf-8
from openerp import models, fields, api, _
from openerp.exceptions import ValidationError
import openerp.addons.decimal_precision as dp
from unidecode import unidecode

    
    
class stock_pallet_type(models.Model):
    """ 
    Pallet type 
    """
    _name = 'stock.pallet.type'
    _description = 'Pallet type'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    length = fields.Float(digits=dp.get_precision('Stock Weight'), default=0.0)
    width = fields.Float(digits=dp.get_precision('Stock Weight'), default=0.0)



class shipment_carrier(models.Model):
    """ 
        Shipment carrier 
    """
    _name = 'shipment.carrier'
    _description = 'Shipment carrier'


    @api.one
    @api.depends('departure_date', 'delay')
    def _compute_arrival_date(self):
        import datetime as t
        if self.departure_date:
            self.arrival_date = fields.Date.from_string(self.departure_date) + t.timedelta(days=self.delay)
        else:
            return None


    @api.onchange('product_id')
    def _compute_transport(self):
        for line in self:
            if line.sinfo_id:
                line.total_price = line.sinfo_id.first_price
                line.delay = line.sinfo_id.delivery_delay
                line.currency_id = line.sinfo_id.currency_id
            else:
                line.total_price = 0
                line.delay = 0
                line.currency_id = 0


    #===========================================================================
    # COLUMNS
    #===========================================================================
    shipment_id = fields.Many2one('shipment', string='Shipment', required=True, ondelete='cascade')
    transporter_id = fields.Many2one('res.partner', string='Transporter', required=True, ondelete='restrict')
    sinfo_id = fields.Many2one('product.supplierinfo', string='Supplier info', required=False, ondelete='restrict')
    total_price = fields.Float(string='Total price')
    delay = fields.Integer(string='Delay')
    currency_id = fields.Many2one('res.currency', compute='_compute_transport', ondelete='restrict')
    departure_date = fields.Date(string='Departure date')
    arrival_date = fields.Date(string='Arrival date', compute='_compute_arrival_date')
    selected = fields.Boolean(string='Selected', default=False)
    price_quote_deadline_send = fields.Boolean(default=False)
    shipment_state = fields.Selection(related='shipment_id.state', readonly=True)
    
    
    @api.multi
    def action_mail_transport(self):
        context = self.env.context.copy()
        context.update({'send_mail_method_next': 'set_price_quote_deadline_send', 
                        'real_thread_model': 'shipment.carrier', 
                        'active_model': self._name, 
                        'active_id': self.id, 
                        'active_ids': self.ids})
        return self.env['mail.message'].with_context(context).action_send_mail(False, self._name, 'shipment_carrier', self.id)
    
    
    @api.multi
    def set_price_quote_deadline_send(self):
        self.write({'price_quote_deadline_send': True})
        

    @api.multi
    def select(self):
        if self.shipment_id.state != 'draft':
            return False
        
        self.write({'selected': True})
        return {'type':'ir.actions.act_window_view_reload'}


    @api.multi
    def write(self, vals):
        if vals and vals.get('selected', False):
            self.shipment_id.carrier_ids.write({'selected': False})
            self.shipment_id.write({
                'selected_transporter_id': self.transporter_id.id, 
                'carrier_processing_id': self.transporter_id.carrier_processing_id.id
            })
        return super(shipment_carrier, self).write(vals)

    
    @api.model
    def create(self, vals):
        res = super(shipment_carrier, self).create(vals)
        if vals and vals.get('selected', False):
            res.select()
            
        return res
    


class shipment(models.Model):
    """ 
    Shipment 
    """
    _name = 'shipment'
    _description = 'Shipment'


    @api.model
    def _state_get(self):
        return [
            ('draft', _('Draft')), 
            ('validated', _('Validated')), 
            ('done', _('Done')), 
            ('canceled', _('Canceled')), 
        ]

    
    @api.model
    def _processing_state_get(self):
        return [
            ('draft', _('Draft')),
            ('done', _('Done')),
            ('error', _('Error')),
        ]


    def _get_states(self):
        return {
            'draft': [('readonly', False)], 
            'validated': [('readonly', True)], 
            'done': [('readonly', True)], 
            'canceled': [('readonly', True)]
        }


    @api.one
    @api.constrains('carrier_ids')
    def _check_selected_unique(self):
        total = 0
        for line in self.carrier_ids:
            if line.selected:
                total += 1
                
        if total > 1:
            raise ValidationError(_('Only one transporter can be selected'))


    @api.one
    @api.depends('address_id', 'picking_ids')
    def _compute_address(self):
        if self.picking_ids:
            picking = self.picking_ids[0]
            self.address_name = picking.address_name
            self.street = picking.street
            self.street2 = picking.street2
            self.street3 = picking.street3
            self.zip = picking.zip
            self.city = picking.city
            self.region_id = picking.region_id and picking.region_id.id or False 
            self.country_id = picking.country_id
        elif self.address_id:
            self.address_name = self.address_id.name
            self.street = self.address_id.street
            self.street2 = self.address_id.street2
            self.street3 = self.address_id.street3
            self.zip = self.address_id.zip
            self.city = self.address_id.city
            self.region_id = self.address_id.region_id and self.address_id.region_id.id or False 
            self.country_id = self.address_id.country_id
        else:
            self.address_name = ''
            self.street = ''
            self.street2 = ''
            self.street3 = ''
            self.zip = ''
            self.city = ''
            self.region_id = False
            self.country_id = None
        
        
    @api.one
    @api.depends('forwarding_agent_id')
    def _compute_forwarding_agent_address(self):
        if self.forwarding_agent_address_id:
            self.forwarding_agent_address_id = self.forwarding_agent_address_id.id
            self.forwarding_agent_address_name = self.forwarding_agent_address_id.name
            self.forwarding_agent_street = self.forwarding_agent_address_id.street
            self.forwarding_agent_street2 = self.forwarding_agent_address_id.street2
            self.forwarding_agent_street3 = self.forwarding_agent_address_id.street3
            self.forwarding_agent_zip = self.forwarding_agent_address_id.zip
            self.forwarding_agent_city = self.forwarding_agent_address_id.city
            self.forwarding_agent_region_id = self.forwarding_agent_address_id.region_id and self.forwarding_agent_address_id.region_id.id or False 
            self.forwarding_agent_country_id = self.forwarding_agent_address_id.country_id
        else:
            self.forwarding_agent_address_name = ''
            self.forwarding_agent_street = ''
            self.forwarding_agent_street2 = ''
            self.forwarding_agent_street3 = ''
            self.forwarding_agent_zip = ''
            self.forwarding_agent_city = ''
            self.forwarding_agent_region_id = False
            self.forwarding_agent_country_id = None
            
    
    @api.one
    @api.depends('selected_transporter_id')
    def _compute_invoice_ids(self):
        invoice_line_obj = self.env['account.invoice.line']
        self.invoice_ids = []
        sol_ids = []
        for picking_rc in self.picking_ids:
            for move_rc in picking_rc.move_ids:
                if move_rc.sale_line_id:
                    sol_ids.append(move_rc.sale_line_id.id)
            
        if sol_ids:
            invoice_line_rc = invoice_line_obj.search([('sale_order_line_id', 'in', sol_ids)])
            if invoice_line_rc:
                self.invoice_ids = [x.invoice_id.id for x in invoice_line_rc if x.invoice_id] 
            
        
    @api.one
    @api.depends('selected_transporter_id')
    def _compute_transport_cost(self):
        self.transport_cost = False
        for x in self.carrier_ids:
            if x.selected:
                self.transport_cost = x.total_price
                return
            
            
    @api.one
    @api.depends('desired_departure_date', 'delay')
    def _compute_desired_arrival_date(self):
        if self.desired_departure_date:
            if self.delay:
                if self.customer_id:
                    self.desired_arrival_date = self.customer_id.calendar_id.get_date(self.desired_departure_date, self.delay)
                    
            else:
                self.desired_arrival_date = self.desired_departure_date
                
        else:
            self.desired_arrival_date = False
            
            
    @api.one
    @api.depends('shipment_processing_id')
    def _compute_shipment_processing_fields(self):
        history_obj = self.env['edi.transformation.history']
        history = history_obj.get_history('shipment', self.id, self.shipment_processing_id.id)
        if history:
            self.shipment_processing_state = history.check 
            self.shipment_processing_start_date = history.start_date 
            self.shipment_processing_end_date = history.end_date 
        else:
            self.shipment_processing_state = False 
            self.shipment_processing_start_date = False 
            self.shipment_processing_end_date = False 


    @api.one
    @api.depends('carrier_processing_id')
    def _compute_carrier_processing_fields(self):
        history_obj = self.env['edi.transformation.history']
        history = history_obj.get_history('shipment', self.id, self.carrier_processing_id.id)
        if history:
            self.carrier_processing_state = history.check 
            self.carrier_processing_start_date = history.start_date 
            self.carrier_processing_end_date = history.end_date 
        else:
            self.carrier_processing_state = False 
            self.carrier_processing_start_date = False 
            self.carrier_processing_end_date = False
                
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True, default='/', copy=False, states=_get_states)
    state = fields.Selection('_state_get', string='State', default='draft')
    incoterm_id = fields.Many2one('stock.incoterms', string='Incoterm', required=True, ondelete='restrict', help='Incoterm which stands for \'International Commercial terms\' '
                                                                            'implies its a series of purchases terms which are used in the commercial transaction.', states=_get_states)
    desired_departure_date = fields.Date(string='Desired departure', states=_get_states)
    desired_arrival_date = fields.Date(string='Desired arrival', compute='_compute_desired_arrival_date')
    forecast_departure_date = fields.Date(string='Forecast departure', states=_get_states)
    forecast_arrival_date = fields.Date(string='Forecast arrival', states=_get_states)
    real_departure_date = fields.Date(string='Real departure', readonly=True, copy=False)
    real_arrival_date = fields.Date(string='Real arrival', readonly=True, copy=False)
    delay = fields.Integer(string='Delay', states=_get_states)
    
    selected_transporter_id = fields.Many2one('res.partner', string='Selected carrier', required=False, ondelete='restrict', readonly=True)
    customer_id = fields.Many2one('res.partner', string='Customer', required=True, ondelete='restrict')
    address_id = fields.Many2one('address', string='Address', ondelete='restrict')
    address_name = fields.Char(string='Name', compute='_compute_address', store=True)
    street = fields.Char(string='Street', compute='_compute_address', store=True)
    street2 = fields.Char(string='Street 2', compute='_compute_address', store=True)
    street3 = fields.Char(string='Street 3', compute='_compute_address', store=True)
    zip = fields.Char(string='Zip', compute='_compute_address', store=True)
    city = fields.Char(string='City', compute='_compute_address', store=True)
    region_id = fields.Many2one('res.region', string='Region', required=False, compute='_compute_address', store=True)
    country_id = fields.Many2one('res.country', string='Country', compute='_compute_address', store=True)

    forwarding_agent_id = fields.Many2one('res.partner', string='Forwarding agent', required=False, ondelete='restrict', domain=[('is_company', '=', True)], states=_get_states)
    forwarding_agent_address_id = fields.Many2one('address', string='Address', ondelete='restrict')
    forwarding_agent_address_name = fields.Char(string='Name', compute='_compute_forwarding_agent_address', store=True)
    forwarding_agent_street = fields.Char(string='Street', compute='_compute_forwarding_agent_address', store=True)
    forwarding_agent_street2 = fields.Char(string='Street 2', compute='_compute_forwarding_agent_address', store=True)
    forwarding_agent_street3 = fields.Char(string='Street 3', compute='_compute_forwarding_agent_address', store=True)
    forwarding_agent_zip = fields.Char(string='Zip', compute='_compute_forwarding_agent_address', store=True)
    forwarding_agent_city = fields.Char(string='City', compute='_compute_forwarding_agent_address', store=True)
    forwarding_agent_region_id = fields.Many2one('res.region', string='Region', required=False, compute='_compute_forwarding_agent_address', store=True)
    forwarding_agent_country_id = fields.Many2one('res.country', string='Country', compute='_compute_forwarding_agent_address', store=True)
    
    insurance_value = fields.Float(string='Insurance value', default=0.0, required=False, states=_get_states)
    transporter_contact_id = fields.Many2one('res.partner', string='Transporter contact', required=False, ondelete='restrict', states=_get_states, domain="[('parent_id', '=', selected_transporter_id)]")
    transport_cost = fields.Float(string='Transport cost', default=0.0, required=False, states=_get_states, readonly=True, compute="_compute_transport_cost")
    transporter_comments = fields.Text(string='Comments for the transporter', states=_get_states)
    grand_export_invoiced = fields.Boolean(default=False)

    picking_ids = fields.One2many('stock.picking', 'shipment_id', string='Picking', states=_get_states)
    weight = fields.Float(string='Weight', required=False, states=_get_states)
    pallet_type_id = fields.Many2one('stock.pallet.type', string='Pallet type', required=False, ondelete='restrict')
    pallet_number = fields.Integer(string='Number of pallet', required=False, states=_get_states)
    package_number = fields.Integer(string='Number of packages', required=False, states=_get_states)
    label_number = fields.Integer(string='Number of Labels', required=False, states=_get_states)
    length = fields.Float(digits=dp.get_precision('Stock Weight'), states=_get_states)
    width = fields.Float(digits=dp.get_precision('Stock Weight'), states=_get_states)
    height = fields.Float(digits=dp.get_precision('Stock Weight'), states=_get_states)
    volume = fields.Float(digits=dp.get_precision('Stock Weight'), states=_get_states)
    shipment_comments = fields.Text(string='Comments on shipment', states=_get_states)

    carrier_ids = fields.One2many('shipment.carrier', 'shipment_id', string='Transporter lines', states=_get_states)
    mail_ids = fields.One2many('mail.message', 'res_id', string='Mails', domain=[('model', '=', 'shipment')], states=_get_states)
    invoice_ids = fields.One2many('account.invoice', compute='_compute_invoice_ids',  string='Invoices')
    
    # EDI
    shipment_processing_id = fields.Many2one('edi.transformation.processing', string='Shipping advice', required=False, ondelete='restrict')
    shipment_processing_state = fields.Selection('_processing_state_get', string='State', compute='_compute_shipment_processing_fields')
    shipment_processing_start_date = fields.Datetime(string='Start date', compute='_compute_shipment_processing_fields')
    shipment_processing_end_date = fields.Datetime(string='End date', compute='_compute_shipment_processing_fields')
    carrier_processing_id = fields.Many2one('edi.transformation.processing', string='Carrier processing', required=False, ondelete='restrict')
    carrier_processing_state = fields.Selection('_processing_state_get', string='State', compute='_compute_carrier_processing_fields')
    carrier_processing_start_date = fields.Datetime(string='Start date', compute='_compute_carrier_processing_fields')
    carrier_processing_end_date = fields.Datetime(string='End date', compute='_compute_carrier_processing_fields')
            
            
    def onchange_customer_id(self, customer_rc):
        res = {}
        if customer_rc:
            res['shipment_processing_id'] = customer_rc.shipment_processing_id.id
            res['incoterm_id'] = customer_rc.sale_incoterm_id.id
            res['address_id'] = customer_rc.address_id.id
            res['forwarding_agent_id'] = customer_rc.sale_forwarding_agent_id.id
            res['delay'] = customer_rc.sale_delivery_delay
        else:
            res['shipment_processing_id'] = False
            res['incoterm_id'] = False
            res['address_id'] = False
            res['forwarding_agent_id'] = False 
            res['delay'] = 0
        
        return res
    
    
    def onchange_forwarding_agent_id(self, forwarding_agent_rc):
        res = {}
        if forwarding_agent_rc:
            res['forwarding_agent_address_id'] = forwarding_agent_rc.address_id.id
        else:
            res['forwarding_agent_address_id'] = False
            
        return res
    
    
    def onchange_delay(self, forecast_departure_date, delay, customer_rc):
        res = {}
        if forecast_departure_date:
            if delay:
                if customer_rc:
                    res['forecast_arrival_date'] = customer_rc.calendar_id.get_date(forecast_departure_date, delay)
                    
            else:
                res['forecast_arrival_date'] = forecast_departure_date
                
        else:
            res['forecast_arrival_date'] = False
            
        return res
    
                    
    @api.onchange('customer_id')
    def _onchange_customer_id(self):
        res = self.onchange_customer_id(self.customer_id)
        for k,v in res.iteritems():
            self[k] = v
            
            
    @api.onchange('forwarding_agent_id')
    def _onchange_forwarding_agent_id(self):
        res = self.onchange_forwarding_agent_id(self.forwarding_agent_id)
        for k,v in res.iteritems():
            self[k] = v
            
            
    @api.onchange('picking_ids')
    def _onchange_picking_ids(self):
        if self.picking_ids:
            if not self.desired_departure_date:
                self.desired_departure_date = self.picking_ids[0].date 
                
        else:
            self.desired_departure_date = False    
            
    
    @api.onchange('delay', 'forecast_departure_date')
    def _onchange_delay(self):
        res = self.onchange_delay(self.forecast_departure_date, self.delay, self.customer_id)
        for k,v in res.iteritems():
            self[k] = v
    
    
    @api.onchange('length', 'width', 'height')
    def onchange_volume(self):
        if self.length and self.width and self.height:
            self.volume = self.length * self.width * self.height / 1000000.0
        else:
            self.volume = 0.0
            
    
    @api.onchange('pallet_type_id')
    def _onchange_pallet_type_id(self):
        if self.pallet_type_id:
            self.length = self.pallet_type_id.length
            self.width = self.pallet_type_id.width
        
    
    def get_exw(self):
        return self.env['stock.incoterms'].ref('stock.incoterm_EXW')
    
    
    def get_selected_carrier(self, incoterm_exw_rc=False, with_raise=True):
        if not incoterm_exw_rc:
            incoterm_exw_rc = self.get_exw()
        
        carrier_rcs = self.env['shipment.carrier'].search([
            ('selected', '=', True),
            ('shipment_id', '=', self.id),
        ])
        # Raise si l'incoterm n'est pas EXW et plus ou moins d'un transporteur selectionné
        if with_raise and self.incoterm_id.id != incoterm_exw_rc.id:
            if len(carrier_rcs) != 1:
                raise ValidationError(_('You must select exactly one carrier !'))
                
        return carrier_rcs and carrier_rcs[0]


    @api.one
    def invoice_grand_export(self):
        for picking in self.picking_ids:
            if picking.invoice_state == '2binvoiced':
                picking.create_invoice()
                
        self.grand_export_invoiced = True
        return self.add_shipping_to_invoices()


    @api.one
    def add_shipping_to_invoices(self):
        total_price = 0
        invoice_ids = {}
        picking_totals = {}
        account_invoice_line_obj = self.env['account.invoice.line']
        selected_shipment_transporter = self.carrier_ids.search([('shipment_id', '=', self.id), ('selected', '=', True)])
        for picking_id in self.picking_ids:
            for line in picking_id.move_ids:
                total_price += line.partner_price * line.uoi_qty
                invoice_ids[picking_id.id] = line.invoice_line_id.invoice_id
                if picking_id.id not in picking_totals:
                    picking_totals[picking_id.id] = line.partner_price * line.uoi_qty
                else:
                    picking_totals[picking_id.id] += line.partner_price * line.uoi_qty
                    
        for picking_id in self.picking_ids:
            pay_transport = False
            if picking_id.incoterm_id.id == self.get_exw().id or picking_id.invoice_postage == 'always':
                pay_transport = True
                
            elif picking_id.invoice_postage == 'threshold' and picking_totals[picking_id.id] < picking_id.threshold:
                pay_transport = True

            if pay_transport and selected_shipment_transporter:
                price_unit = selected_shipment_transporter.total_price * picking_totals[picking_id.id] / total_price
                data = {
                    'price_unit': price_unit,
                    'quantity': 1,
                    'uom_qty': 1,
                    'sec_uom_qty': 1
                }
                line_id = account_invoice_line_obj.create_invoice_line(invoice_ids[picking_id.id], selected_shipment_transporter.product_id, False, data)
                line_id.write({'price_unit': price_unit})


    @api.one
    def unselect(self):
        self.carrier_ids.write({'selected': False})
        self.write({'selected_transporter_id': False})
    
    
    def create_shipment(self, customer_rc, forwarder_agent_rc=False, address_rc=False, incoterm_rc=False, date=False, other_data=None):
        vals = {'customer_id': customer_rc.id}
        if other_data:
            vals.update(other_data)
        
        vals.update(self.onchange_customer_id(customer_rc))
        if date:
            vals['forecast_departure_date'] = vals['desired_departure_date'] = date
            vals.update(self.onchange_delay(vals['forecast_departure_date'], vals['delay'], customer_rc))
            
        if 'forwarding_agent_id' in vals and not forwarder_agent_rc:
            forwarder_agent_rc = self.env['res.partner'].browse(vals['forwarding_agent_id'])
            
        if forwarder_agent_rc:
            vals.update(self.onchange_forwarding_agent_id(forwarder_agent_rc))
                                                          
        if address_rc:
            vals['address_id'] = address_rc.id
            
        if incoterm_rc:
            vals['incoterm_id'] = incoterm_rc.id
            
        return self.create(vals)
    
    
    @api.multi
    def create_invoice(self):
        for shipment_rc in self:
            for picking_rc in shipment_rc.picking_ids:
                if picking_rc.invoice_state == '2binvoiced':
                    picking_rc.create_invoice()
        
    
    @api.multi
    def action_send_mail(self):
        return self.env['mail.message'].action_send_mail(self.customer_id, 'shipment', '', self.id)


    @api.multi
    def run_processing(self):
        context = self.env.context.copy()
        field = self.env.context.get('processing_field', '')
        if field:
            context['object_model'] = 'shipment' 
            processing_obj = self.env['edi.transformation.processing']
            for this in self.read([field], load='_classic_write'):
                context['object_id'] = this['id']
                if this[field]: 
                    processing_obj.browse([this[field]]).with_context(context).run_all()
            
        return True
    
    
    @api.one
    def reopen(self):
        for shipment in self:
            for picking in shipment.picking_ids:
                picking.reopen()
                picking.wkf_waiting()
            
        self.write({'state': 'draft', 'real_departure_date': False, 'real_arrival_date': False})


    @api.multi
    def wkf_draft(self):
        self.write({'state': 'draft', 'grand_export_invoiced': False})


    @api.multi
    def wkf_validated(self):
        self.with_context(processing_field='shipment_processing_id').run_processing()
        self.write({'state': 'validated'})


    @api.multi
    def wkf_done(self):
        self.with_context(processing_field='carrier_processing_id').run_processing()
        today = fields.Date.today()
        for shipment_rc in self:
            if shipment_rc.picking_ids:
                shipment_rc.picking_ids.do_partial_auto()
                
            shipment_rc.write({
                'state': 'done', 
                'real_departure_date': today, 
                'real_arrival_date': shipment_rc.customer_id.calendar_id.get_date(today, shipment_rc.delay)
            })


    @api.multi
    def wkf_cancel(self):
        self.picking_ids.write({'shipment_id': None})
        self.write({'state': 'canceled', 'real_departure_date': False, 'real_arrival_date': False})


    @api.model
    def create(self, vals):
        if 'name' not in vals or vals.get('name') == '/':
            vals['name'] = self.env['ir.sequence'].get('shipment.shipment')

        return super(shipment, self).create(vals=vals)
