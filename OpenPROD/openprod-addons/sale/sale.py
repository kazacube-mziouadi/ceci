# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm, ValidationError, Warning
from openerp import netsvc, workflow
from openerp.addons.base_openprod import utils
from openerp.addons.base_openprod.common import get_form_view, roundingUp
from decimal import Decimal
import pdb
from pdb import Pdb


class res_currency(models.Model):
    _inherit = "res.currency"

    def compute_domain_args(self, args):
        #Fonction appelée par le search afin d'empécher la sélection d'une autre devise
        #après création d'une ligne de vente
        args2 = []
        for arg in args:
            match = False
            if isinstance(arg, str) or (isinstance(arg, list) and arg[0] in ('!', '|', '&')):
                args2.append(arg)
                continue
            
            if arg[0] == 'sale_order_currency_domain':
                if isinstance(arg[-1], list) and arg[-1][0]:
                    arg = ('id', '=', arg[-1][1])
                else:
                    match = True
                    
            if not match:
                args2.append(arg)
        
        return args2
 
     
    @api.model
    def search(self,args=None, offset=0, limit=None, order=None, count=None):
        #Modification du search afin d'empécher la sélection d'une autre devise
        #après création d'une ligne de vente
        args = args or []
        args_modified = self.compute_domain_args(args)
        return super(res_currency,self).search(args=args_modified, offset=offset, limit=limit, order=order, count=count)
    
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=1000):
        """
            Fonction name_search de la devise
        """
        args = self.compute_domain_args(args)
        recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()
    
    

class sale_order_line_section(models.Model):
    """ 
    Section for sale order lines 
    """
    _name = 'sale.order.line.section'
    _description = 'Section for sale order lines'
    _order = 'sequence asc'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    sequence = fields.Integer(string='Sequence', default=0, required=True)
    subtotal = fields.Boolean(string='Add subtotal', default=True)
    separator = fields.Boolean(string='Add separator', default=True)
    pagebreak = fields.Boolean(string='Add pagebreak', default=False)



class mail_message(models.Model):
    _inherit = 'mail.message'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    sale_id = fields.Many2one('sale.order', string='Sale', required=False, ondelete='restrict')



class sale_family(models.Model):
    """
    Purchase Family
    """
    _name = 'sale.family'
    _description = 'Sale Family'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)



class sale_order_line(models.Model):
    """ 
    Sale order line 
    """
    _name = 'sale.order.line'
    _description = 'Sale order line'
    _order = 'sequence asc'
    
    
    @api.model
    def _supply_method_get(self):
        return [
                ('make_to_plan', _('Supply on scheduler')),
                ('make_to_order', _('Supply on demand')),
                ('make_to_order_with_stock', _('Supply on demand with stock')),
                ('without_stock', _('No supply')),
                       ]
    
    
    @api.model
    def _sale_state_get(self):
        return [
                ('draft', _('Draft')),
                ('waiting_delay', _('Awaiting delay')),
                ('waiting_conf_delay', _('Sent the confirmation')),
                ('waiting', _('Waiting')),
                ('progress', _('In progress')),
                ('done', _('Done')),
                ('cancel', _('Cancelled')),
                       ]
    
    
    @api.model
    def _month_get(self):
        return [
                    ('00', _('Without month')), 
                    ('01', _('January')), 
                    ('02', _('February')), 
                    ('03', _('March')), 
                    ('04', _('April')), 
                    ('05', _('May')), 
                    ('06', _('June')), 
                    ('07', _('July')), 
                    ('08', _('August')), 
                    ('09', _('September')), 
                    ('10', _('October')), 
                    ('11', _('November')), 
                    ('12', _('December'))
           ]
    
    
    @api.model
    def _day_get(self):
        return [
                    ('0', _('Without day')), 
                    ('1', _('Monday')), 
                    ('2', _('Tuesday')), 
                    ('3', _('Wednesday')), 
                    ('4', _('Thursday')), 
                    ('5', _('Friday')), 
                    ('6', _('Saturday')), 
                    ('7', _('Sunday'))
           ]
    
    
    @api.model
    def _sale_type_get(self):
        self.env['sale.order']._type_get()
    
        
    @api.one
    @api.depends('confirmed_departure_date', 'transport_delay')
    def _compute_arrival_date(self):
        arrival_date = False
        #On récupère le calendrier du transport et le calendrier du client livré
        sale_order = self.sale_order_id
        transport_calendar = sale_order.company_id.transport_calendar_id
        customer_calendar = sale_order.delivered_customer_id.calendar_id
        if transport_calendar and customer_calendar and self.confirmed_departure_date:
            #On calcule la date de départ à partir de la date demandée et du calendrier de transport
            transport_date = transport_calendar.get_date(self.confirmed_departure_date, self.transport_delay)
            #On recherche la date la plus proche de cette date dans le calendrier du client
            arrival_date_list = self.env['calendar.line'].search([('real_start_date', '>=', transport_date), 
                                                         ('calendar_id', '=', customer_calendar.id)], limit=1, order='real_start_date asc')
            if arrival_date_list:
                arrival_date = arrival_date_list[0].real_start_date
            
        self.arrival_date = arrival_date
    
    
    @api.one
    @api.depends('requested_date', 'transport_delay')
    def _compute_departure_date(self):
        """
            Au changement de la date demandée ou du délai de transport, on va calculer la date
            de départ de la commande
        """
        departure_date = False
        #On récupère le calendrier du transport et le calendrier de la société
        company = self.sale_order_id.company_id
        transport_calendar = company.transport_calendar_id
        company_calendar = company.partner_id.calendar_id
        if transport_calendar and company_calendar and self.requested_date:
            #On calcul la date de départ à partir de la date demandée et du calendrier de transport
            transport_date = transport_calendar.get_date_inverse(self.requested_date, self.transport_delay)
            #On recherche la date la plus proche de cette date dans le calendrier de l'entreprise
            departure_date_list = self.env['calendar.line'].search([('real_start_date', '<=', transport_date), 
                                                         ('calendar_id', '=', company_calendar.id)], limit=1, order='real_start_date desc')
            if departure_date_list:
                departure_date = departure_date_list[0].real_start_date
        
        if not departure_date:
            departure_date = self.requested_date
            
        self.departure_date = departure_date

    
    @api.one
    @api.depends('price_unit', 'uoi_qty')
    def _compute_total_price(self):
        """
            Fonction permettant de calculer le prix total de la ligne de vente
        """
        price = self.price_unit
        taxes = self.taxes_ids.compute_all(price, self.currency_id, self.uoi_qty, product=self.product_id, partner=self.sale_partner_id)
        total_price = taxes['total_excluded']
        self.total_price = (self.currency_id.round(total_price))
        
        
    
    @api.one
    @api.depends('price_unit', 'uoi_qty', 'currency_id', 'sale_order_id.creation_date',
                 'sale_order_id.confirmation_date')
    def _compute_price_with_currency(self):
        """
            Fonction permettant de calculer le prix total de la ligne de vente dans la devise de
            la société ainsi que le taux de conversion utilisé lors du calcul
        """
        company_currency = self.sale_order_id.company_id.currency_id
        line_currency = self.currency_id or self.sale_order_id.currency_id
        if line_currency and line_currency != company_currency:
            context2 = {}
            if self.sale_order_id.confirmation_date:
                context2 = {'date': self.sale_order_id.confirmation_date}
            else:
                context2 = {'date': self.sale_order_id.creation_date}
            
            self.total_price_currency = line_currency.with_context(context2).compute((self.price_unit * self.uoi_qty), company_currency)
            self.currency_rate = line_currency.with_context(context2)._get_conversion_rate(line_currency, company_currency)
        
        else:
                self.total_price_currency = self.price_unit * self.uoi_qty
                self.currency_rate = 0
    
    
    @api.one
    @api.depends('confirmed_departure_date', 'departure_date', 'requested_date')
    def _compute_date(self):
        """
            Fonction qui calcule le jour, la semaine, le mois et l'année de la ligne de vente
        """
        date = False
        #On prend la date de départ confirmée
        if self.confirmed_departure_date:
            date = fields.Date.from_string(self.confirmed_departure_date)
        #Ou la date de départ
        elif self.departure_date:
            date = fields.Date.from_string(self.departure_date)
        #Ou la date de départ demandée
        elif self.requested_date:
            date = fields.Date.from_string(self.requested_date)
        else:
            self.week_number = '00'
            self.month = '00'
            self.year = '0'
            self.day = False
        
        if date:
            #On récupère le nom du jour et le numéro de l'année
            isocal = date.isocalendar()
            self.day = str(isocal[2])
            self.year = str(isocal[0])
            #On récupère le numéro de semaine
            if len(str(isocal[1])) == 1:
                self.week_number = '0%s'%(str(isocal[1]))
            else:
                self.week_number = str(isocal[1])
            
            #On récupère le mois
            if len(str(date.month)) == 1:
                self.month = '0%s'%(str(date.month))
            else:
                self.month = str(date.month)
                
                
    @api.one
    @api.depends('stock_move_ids')
    def _compute_color_line(self):
        """
            Fonction permettant de récupérer la plus haute valeur de priorité des moves
        """
        color_priority_need_read = self.env['stock.move'].search_read([('id', 'in', self.stock_move_ids.ids)], ['color_priority_need'], limit=1, order='color_priority_need desc')
        color_priority_need = color_priority_need_read and color_priority_need_read[0]['color_priority_need'] or 0
        self.sale_line_color = color_priority_need
    
    
    def _search_color_line(self, operator, value):
        request = 'SELECT sale_line_id FROM stock_move WHERE color_priority_need=%s ORDER BY id'%(value)
        self.env.cr.execute(request)
        res_ids = self.env.cr.fetchall()          
        return [('id', 'in', res_ids)]
    
    
    @api.one
    @api.depends('stock_move_ids', 'stock_move_ids.state', 'requested_date', 'confirmed_departure_date')
    def _compute_lateness(self):
        """
            Fonction permettant de savoir s'il y a du retard ou non pour la livraison
        """
        if self.product_id.type == 'service' and not self.product_id.manage_service_delivery:
            self.lateness = False
        else:
            if self.confirmed_departure_date:
                date = self.confirmed_departure_date
            else:
                date = self.requested_date
            
            if date < fields.Date.today():
                self.lateness = True
            else:
                self.lateness = False
    
    
    @api.one
    def _compute_engagement_delay(self):
        """
            Fonction permettant de ramener le délai d'engagement du produit
        """
        product = self.product_id
        delay = 0
        #Si le produit est en vente libre, on récupère le délai de livraison
        if product.free_sale:
            delay = product.free_delivery_delay
        else:
            #Si le produit n'est pas en vente libre, on récupère le délai
            #de livraison du client 
            customer = self.sale_order_id.partner_id
            customerinfo = product.get_cinfo(partner_id=customer.id, property_ids=self.property_ids.ids)
            if customerinfo:
                delay = customerinfo.delivery_delay
            else:
                delay = product.free_supply_delay
        
        self.engagement_delay = delay
                
    
    def _search_lateness(self, operator, value):
        """
            Fonction search du booléen de retard
        """ 
        query = """
            SELECT 
                line.id 
            FROM 
                sale_order_line line 
            LEFT OUTER JOIN
                product_product product ON product.id=line.product_id
            WHERE
                 remaining_qty > 0.0
             AND
                ((line.confirmed_departure_date IS NOT NULL and line.confirmed_departure_date < current_date) 
                OR
                (line.confirmed_departure_date IS NULL and line.requested_date < current_date))
            AND
                (product.type != 'service' OR product.manage_service_delivery = true)
        """
        self.env.cr.execute(query)
        res_ids = self.env.cr.fetchall()
        return [('id', 'in', res_ids)]
    
    
    @api.one
    @api.depends('sale_order_id.called_order_ids', 'sec_uom_qty')
    def _compute_remaining_called_order_qty(self):
        """
            Fonction permettant de calculer la quantité restante à acheter d'une commande ouverte
        """
        sale = self.sale_order_id
        qty = 0
        #On vérifie que la vente soit de type ouvert et qu'elle ne soit pas annulée
        if sale.type == 'open' and self.sale_state != 'cancel':
            uom_obj = self.env['product.uom']
            #On récupère le produit et l'unité de vente de la ligne
            product_id = self.product_id and self.product_id.id
            sec_uom_id = self.sec_uom_id and self.sec_uom_id.id 
            #On parcourt la liste des commandes appelées de la vente
            for called_order in sale.called_order_ids:
                if called_order.state != 'cancel':
                    #On parcourt les lignes de vente des commandes appelées de vente
                    for called_order_line in called_order.order_line_ids:
                        #Pour chaque ligne, si on tombe sur le même produit on ajoute cette quantité au total
                        if called_order_line.product_id and product_id == called_order_line.product_id.id:
                            qty += uom_obj._compute_qty(called_order_line.sec_uom_id.id, called_order_line.sec_uom_qty, sec_uom_id)
        
        remaining_qty = self.sec_uom_qty - qty
        self.remaining_called_qty = remaining_qty >= 0 and remaining_qty or 0
                
    
    @api.one
    @api.depends('fixed_discount_ids', 'fixed_discount_ids.amount')
    def _compute_fixed_discount(self):
        """
            Fonction permettant de calculer la remise fixe sur le prix unitaire
        """
        fixed_discount = 0.0
        for line in self.fixed_discount_ids:
            fixed_discount += line.amount
        
        self.fixed_discount = fixed_discount
    
    
    @api.one
    @api.depends('variable_discount_ids', 'variable_discount_ids.amount', 'variable_discount_ids.type')
    def _compute_variable_discount(self):
        """
            Fonction permettant de calculer la remise fixe sur le prix unitaire
        """
        variable_discount = 0.0
        type = False
        for line in self.variable_discount_ids:
            if not type:
                type = line.type
            else:
                if type != line.type:
                    raise except_orm(_('All lines must be of the same type!'))
                    break
                    
            if type == 'cumulative':
                variable_discount += line.amount
            else:
                if variable_discount == 0:
                    variable_discount = 1
                    
                variable_discount *= (line.amount/100+1)
                                    
        if type:
            if type != 'cumulative':
                variable_discount = variable_discount and variable_discount*100-100 or 0
        
        self.variable_discount = variable_discount
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    #Ligne de commande
    sequence = fields.Integer(string='Sequence', default=0, required=False)
    sale_line_color = fields.Integer(string='Color priority', default=0, required=False, compute='_compute_color_line', 
                                     store=False, search='_search_color_line')
    name = fields.Text(string='Description', required=True)
    sale_order_id = fields.Many2one('sale.order', string='Sale order', required=False, ondelete='cascade', select=True)
    sale_partner_id = fields.Many2one('res.partner', string='Partner', required=False, ondelete='set null', 
                                      related='sale_order_id.partner_id', store=True, readonly=True)
    sale_state = fields.Selection('_sale_state_get', string='State', related='sale_order_id.state', store=True, readonly=True)
    sale_type = fields.Selection('_sale_type_get', string='Type', related='sale_order_id.type', store=True, readonly=True)
    sale_seller_id = fields.Many2one('res.users', string='Seller', required=False, ondelete='set null', 
                                     related='sale_order_id.seller_id', store=True, readonly=True)
    sale_order_manager_id = fields.Many2one('res.users', string='ADV', required=False, ondelete='set null', 
                                            related='sale_order_id.sale_manager_id', store=True, readonly=True)
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='restrict')
    sec_uom_qty = fields.Float(string='Quantity in sale unity', default=0.0, digits=dp.get_precision('Product quantity'), 
                               required=True)
    uom_qty = fields.Float(string='Quantity in measure unit', default=0.0, digits=dp.get_precision('Product quantity'), 
                           required=True)
    uoi_qty = fields.Float(string='Quantity in price unity', default=0.0, digits=dp.get_precision('Product quantity'), 
                           required=True)
    price_unit = fields.Float(string='Price unit', default=0.0, digits=dp.get_precision('Product price'), 
                              required=True)
    sec_uom_id = fields.Many2one('product.uom', string='Sale unity', required=True, ondelete='restrict')
    sec_uom_category_id = fields.Many2one('product.uom.category', string='Second uom category', required=False, 
                                          ondelete='restrict')
    total_price = fields.Float(string='Total price', default=0.0, required=False, compute='_compute_total_price', 
                               store=True)
    total_price_currency = fields.Float(string='Total price currency company', default=0.0, required=False, compute='_compute_price_with_currency', 
                               store=True)
    currency_rate = fields.Float(string='Currency rate', default=0.0, required=False, compute='_compute_price_with_currency', 
                               store=True, digits=(12,6))
    uom_id = fields.Many2one('product.uom', string='Measure unity', required=True, ondelete='restrict')
    uom_category_id = fields.Many2one('product.uom.category', string='Uom category', required=False, ondelete='restrict')
    uoi_id = fields.Many2one('product.uom', string='Price unity', required=True, ondelete='restrict')
    uoi_category_id = fields.Many2one('product.uom.category', string='Uoi category', required=False, ondelete='restrict')
    currency_id = fields.Many2one('res.currency', string='Currency', required=False, ondelete='restrict', 
                                  related='sale_order_id.currency_id', readonly=True)
    property_ids = fields.Many2many('purchase.property', string='Properties', domain=[('sale', '=', True)])
    purchase_property_ids = fields.Many2many('purchase.property', string='Properties')
    taxes_ids = fields.Many2many('account.tax', 'account_tax_rel', 'sale_order_id', 'tax_line_id', string='Taxes', 
                                 domain=[('type_tax_use', '!=', 'purchase'), ('parent_id', '=', False)])
    section_id = fields.Many2one('sale.order.line.section', string='Section', required=False, ondelete='restrict')
    customer_product_name = fields.Char(string='Customer product name', size=128, required=False)
    customer_product_code = fields.Char(string='Customer product code', size=128, required=False)
    delivered = fields.Float(string='Delivered percentage', default=0.0, required=False)
    invoiced = fields.Float(string='Invoice generated percentage', default=100.0, required=False)
    paid = fields.Float(string='Invoice paid percentage', default=100.0, required=False)
    requested_date = fields.Date(string='Requested date', required=True)
    transport_delay = fields.Integer(string='Transport delay', default=0, required=False)
    departure_date = fields.Date(string='Departure date', compute='_compute_departure_date', store=True)
    scheduled_date = fields.Date(string='Scheduled date')
    confirmed_departure_date = fields.Date(string='Confirmed departure date (after planning)', copy=False)
    arrival_date = fields.Date(string='Arrival date', compute='_compute_arrival_date', store=True)
    supply_method = fields.Selection('_supply_method_get', string='Supply method', required=True)
    delay_confirm = fields.Boolean(string='Waiting delay confirmation', default=False)
    factor = fields.Float(string='Factor', default=1, required=False)
    divisor = fields.Float(string='Divisor', default=1, required=False)
    lateness = fields.Boolean(string='Lateness', default=False, compute='_compute_lateness', search='_search_lateness')
    engagement_delay = fields.Integer(string='Delay', compute='_compute_engagement_delay')
    remaining_called_qty = fields.Float(string='Remaining quantity (opened order)', default=0.0, required=False, compute='_compute_remaining_called_order_qty')
    
    #Informations supplémentaires
    gross_weight = fields.Float(string='Gross weight', default=0.0, required=False)
    net_weight = fields.Float(string='Net weight', default=0.0, required=False)
    guarantee = fields.Integer(string='Guarantee', default=0, required=False)
    guarantee_unity_id = fields.Many2one('product.uom', string='Guarantee unity', required=False, ondelete='restrict')
    packaging_id = fields.Many2one('product.packaging', string='Packaging', required=False, ondelete='restrict')
    company_id = fields.Many2one('res.company', string='Company', related='sale_order_id.company_id', store=True, readonly=True)
    
    #Notes
    internal_note = fields.Text(string='Internal note')
    delivery_printed_note = fields.Text(string='Note printed on the delivery note line')
    invoice_printed_note = fields.Text(string='Note printed on the invoice line')
    order_printed_note = fields.Text(string='Product note printed on order')
    work_note = fields.Text(string='Printed work note')
    
    #Historique
    invoice_line_ids = fields.One2many('account.invoice.line', 'sale_order_line_id',  string='Invoices lines')
    stock_move_ids = fields.One2many('stock.move', 'sale_line_id',  string='Stock moves')
    
    #Date pour le search
    year = fields.Char(string='Year', size=4, compute='_compute_date', store=True)
    month = fields.Selection('_month_get', string='Month', compute='_compute_date', store=True)
    week_number = fields.Char(string='Week number', size=2, compute='_compute_date', store=True) 
    day = fields.Selection('_day_get', string='Day', compute='_compute_date', store=True)
    
    #Champs permettant le calcul des pourcentages
    delivered_qty = fields.Float(string='Delivered quantity', default=0.0, required=False, 
                                 digits=dp.get_precision('Product quantity'))
    remaining_qty = fields.Float(string='Remaining quantity', default=0.0, required=False)

    # Attributs
    product_attribute_ids = fields.One2many('sale.common.attribute', 'sale_line_id',  string='Attributes', copy=True)
    
    # Date pour calendrier
    calendar_date = fields.Datetime(string='Calendar date')
    
    # Disocunt
    fixed_discount_ids = fields.One2many('sale.order.line.fixed.discount', 'sale_line_id',  string='Fixed discount', copy=True)
    variable_discount_ids = fields.One2many('sale.order.line.variable.discount', 'sale_line_id',  string='Variable discount', copy=True)
    price_unit_without_discount = fields.Float(string='Price unit without discount', default=0.0, digits=dp.get_precision('Product price'), 
                              required=False, copy=True)
    fixed_discount = fields.Float(string='Fixed discount on unit price', compute='_compute_fixed_discount', store=True, readonly=True, digits=dp.get_precision('Product quantity'))
    variable_discount = fields.Float(string='Variable discount % on unit price', compute='_compute_variable_discount', store=True, readonly=True, digits=dp.get_precision('Product quantity'))
    is_print_discount = fields.Boolean(string='Discount visible in reports', default=False, copy=True)
    
    last_delivery_date = fields.Datetime()
    
    parameter_ids = fields.One2many('parameter.dimension', 'sale_order_line_id', string="Parameters", copy=True)
    
    
    def onchange_product_id(self, product_id, sale_order, send_quantity=False):
        """
            Récupération des infos du produit et du customerinfo
        """
        res = {}
        if isinstance(product_id, int):
            product_id = self.env['product.product'].browse(product_id)
            
        customer = False
        fiscal_position = sale_order.sale_account_system_id
        res['product_attribute_ids'] = [(5, 0)]
        if product_id:
            partner = sale_order.partner_id
            taxes_list = fiscal_position and fiscal_position.map_tax(product_id.sale_taxes_ids) or []
            res['taxes_ids'] = taxes_list
            res['supply_method'] = product_id.trigger_supply
            res['internal_note'] = product_id.internal_note
            res['delivery_printed_note'] = product_id.transport_note
            res['invoice_printed_note'] = product_id.description_invoice
            res['name'] = product_id.with_context(lang=partner.lang).name
            res['guarantee'] = product_id.guarantee
            res['guarantee_unity_id'] = product_id.guarantee_unity_id.id
            res['gross_weight'] = product_id.gross_weight
            res['net_weight'] = product_id.net_weight
            res['transport_delay'] = sale_order.transport_delay
            res['delay_confirm'] = product_id.delay_confirm
            if product_id.free_sale:
                res['engagement_delay'] = product_id.free_delivery_delay
                res['order_printed_note'] = product_id.printed_sale_note
                res['packaging_id'] = product_id.packaging_id and product_id.packaging_id.id or False
                #On récupère le multiple pour calculer la quantité minimum de produit
                if product_id.sale_multiple_qty == 0:
                    multiple_qty = 1
                else:
                    multiple_qty = product_id.sale_multiple_qty
                if send_quantity:
                    res['sec_uom_qty'] = roundingUp(send_quantity, multiple_qty)
                else:
                    res['sec_uom_qty'] = roundingUp(product_id.sale_min_qty, multiple_qty)
                    
            else:
                customer = product_id.get_cinfo(partner_id=sale_order.partner_id.id, property_ids=self.property_ids)
                if customer:
                    #On récupère le multiple pour calculer la quantité minimum de produit
                    if customer.multiple_qty == 0:
                        multiple_qty = 1
                    else:
                        multiple_qty = customer.multiple_qty
                        
                    res['engagement_delay'] = customer.delivery_delay
                    res['customer_product_name'] = customer.cust_product_name
                    res['customer_product_code'] = customer.cust_product_code
                    res['packaging_id'] = customer.packaging_id and customer.packaging_id.id or False
                    if send_quantity:
                        res['sec_uom_qty'] = roundingUp(send_quantity, multiple_qty)
                    else:
                        res['sec_uom_qty'] = roundingUp(customer.min_qty, multiple_qty)
                        
                    if product_id.printed_sale_note and customer.sale_note:
                        res['order_printed_note'] = 'Produit: %s / Informations client: %s'%(product_id.printed_sale_note, customer.sale_note)
                    elif product_id.printed_sale_note:
                        res['order_printed_note'] = product_id.printed_sale_note
                    elif customer.sale_note:
                        res['order_printed_note'] = 'Informations client: %s'%(customer.sale_note)
                    else:
                        res['order_printed_note'] = product_id.printed_sale_note
                        
                else:
                    res['sec_uom_qty'] = 0
                
            uoms = product_id.get_uoms(pinfo=customer or False, partner=sale_order.partner_id, type='out', property_ids=self.property_ids, with_factor=True)
            for k, v in uoms.iteritems():
                res[k] = v
            
            if res.get('sec_uom_id', False) and res.get('uom_id', False) and res.get('sec_uom_id', False) and res.get('uoi_id', False)\
            and res.get('factor', False) and res.get('divisor', False):
                qtys = product_id.get_qtys(res['sec_uom_qty'], 
                                     uom_id=res['uom_id'], 
                                     sec_uom_id=res['sec_uom_id'], 
                                     uoi_id=res['uoi_id'], 
                                     by_field='sec_uom', 
                                     dual_unit=product_id.dual_unit, 
                                     dual_unit_type=product_id.dual_unit_type, 
                                     factor=res['factor'], 
                                     divisor=res['divisor'], 
                                     with_raise=True)
                
                res['uom_qty'] = qtys.get('uom_qty')
            
            # Attributs
            for attribute in product_id.get_common_attribute_ids():
                if attribute.is_visible and not attribute.is_readonly and not attribute.is_compute and not attribute.is_default_compute and attribute.sale:
                    res['product_attribute_ids'].append([0, False, {
                                                    'sequence': attribute.sequence,
                                                    'product_common_attribute_id': attribute.id,
                                                    'value': attribute.default_value,
                                                                    }])
            
            res['parameter_ids'] = []
            if product_id.parameter_ids:
                for parameter in product_id.parameter_ids:
                    res['parameter_ids'].append([0, False, {'type_param_id': parameter.type_param_id.id,
                                                            'value': parameter.value}])
            else:
                res['parameter_ids'] = [(5, 0)]
            
        else:
            res['taxes_ids'] = []
            res['supply_method'] = False
            res['internal_note'] = ''
            res['delivery_printed_note'] = ''
            res['invoice_printed_note'] = ''
            res['name'] = ''
            res['guarantee'] = 0
            res['guarantee_unity_id'] = False
            res['gross_weight'] = 0
            res['net_weight'] = 0
            res['transport_delay'] = 0
            res['order_printed_note'] = ''
            res['engagement_delay'] = 0
            res['sec_uom_qty'] = 0
            res['sec_uom_id'] = False
            res['order_printed_note'] = ''
            res['uom_qty'] = 0
            res['uoi_qty'] = 0
            res['uom_id'] = False
            res['uoi_id'] = False
            res['price_unit'] = 0
            res['property_ids'] = False
            res['delay_confirm'] = False
            
        return res
    

    @api.onchange('product_id')
    def _onchange_warning_product_id(self):
        """
            On vérifie qu'il y a bien un partenaire de saisi dans la vente
        """
        res = {}
        if not self.sale_order_id.partner_id:
            res['warning'] = {'title':_('Warning'), 'message':_('You must first select a customer in the sale order')}
            self.product_id = False
        
        return res
    
    
    @api.onchange('product_id', 'property_ids')
    def _onchange_product_id(self):
        """
            Au changement du produit, changement des UoM et du nom
        """
        res = {}
        if self.product_id:
            old_sec_uom_qty = self.sec_uom_qty
            if not self.product_id.state in ['lifeserie', 'endlife']:
                msg = {'title':_('Warning'), 'message':_('To be sold, the product\'s state should be life serie or end life')}
                res['warning'] = msg
                self.product_id = False
            
            res_value = self.onchange_product_id(self.product_id, self.sale_order_id)
            for k,v in res_value.iteritems():
                self[k] = v
            
            if old_sec_uom_qty == self.sec_uom_qty:
                self._onchange_sec_uom_qty()
        
        return res
        
    
    @api.onchange('sec_uom_qty', 'sec_uom_id', 'property_ids', 'parameter_ids')
    def _onchange_sec_uom_qty(self, with_warning=True):
        """
            Au changement de la qty, changement des autres qty
        """
        res = {}
        if self.product_id:
            uom_obj = self.env['product.uom']
            warning = False
            msg = {}
            qtys = self.product_id.get_qtys(self.sec_uom_qty, 
                                     uom_id=self.uom_id, 
                                     sec_uom_id=self.sec_uom_id, 
                                     uoi_id=self.uoi_id, 
                                     by_field='sec_uom', 
                                     dual_unit=self.product_id.dual_unit, 
                                     dual_unit_type=self.product_id.dual_unit_type, 
                                     factor=self.factor, 
                                     divisor=self.divisor, 
                                     with_raise=True)
             
            if not self.uom_id or not self.sec_uom_id:
                warning = True
                msg = {'title': _('Warning'), 'message': _('You must have Management unit and Sale unit')}
                self.uom_qty = 0
                self.sec_uom_qty = 0
             
            if not self.product_id.free_sale:
                customer_info = self.product_id.get_cinfo(partner_id=self.sale_order_id.partner_id.id, property_ids=self.property_ids.ids)
                if customer_info:
                    if customer_info.multiple_qty:
                        multiple_qty = uom_obj._compute_qty_obj(self.sec_uom_id, self.sec_uom_qty, customer_info.uos_id)
                        if Decimal(str(multiple_qty)) % Decimal(str(customer_info.multiple_qty)):
                            warning = True
                            msg = {'title': _('Warning'), 'message': _('The quantity is not a multiple of %f')%(customer_info.multiple_qty)}
                        
                    if customer_info.min_qty:
                        min_qty = uom_obj._compute_qty_obj(self.sec_uom_id, self.sec_uom_qty, customer_info.uos_id)
                        if customer_info.min_qty > min_qty:
                            warning = True
                            msg = {'title': _('Warning'), 'message': _('The quantity in sale unit should be higher to the minimum quantity '
                                                                                        '(%.2f)')%(customer_info.min_qty)}
                     
                            
                    elif self.product_id.dual_unit and not customer_info.factor:
                        self.uom_qty = 0
                        
                else:
                    warning = True
                    msg = {'title': _('Warning'), 'message': _('There is no active referencing for this properties, this product'
                                                               ' and this customer')}
                    self.product_id = False
                    #On vide tous les champs de la ligne
                    res_value = self.onchange_product_id(self.product_id, self.sale_order_id)
                    for k,v in res_value.iteritems():
                        self[k] = v
             
            else:
                if self.product_id.sale_multiple_qty:
                    multiple_qty = uom_obj._compute_qty_obj(self.sec_uom_id, self.sec_uom_qty, self.product_id.uos_id)
                    if Decimal(str(multiple_qty)) % Decimal(str(self.product_id.sale_multiple_qty)):
                        warning = True
                        msg = {'title': _('Warning'), 'message': _('The quantity is not a multiple of %f')%(self.product_id.sale_multiple_qty)}
                
                if self.product_id.sale_min_qty:
                    min_qty = uom_obj._compute_qty_obj(self.sec_uom_id, self.sec_uom_qty, self.product_id.uos_id)
                    if self.product_id.sale_min_qty > min_qty:
                        warning = True
                        msg = {'title': _('Warning'), 'message': _('The quantity in sale unit should be higher to the minimum quantity '
                                                                                    '(%.2f)')%(self.product_id.sale_min_qty)}
            if self.currency_id:
                currency_rs = self.currency_id
            else:
                currency_rs = False
            
            self.price_unit = self.product_id.get_price_sale(self.sale_order_id.partner_id, self.property_ids, currency_price_return=currency_rs, qty_uos=self.sec_uom_qty, 
                                                             uos=self.sec_uom_id, date=self.scheduled_date, type='price', with_uoi=self.uoi_id, sale_line_rcs=self)
            self.price_unit_without_discount =  self.price_unit
            for k, v in qtys.iteritems():
                self[k] = v
            
            if self.sec_uom_id:
                self.sec_uom_category_id = self.sec_uom_id.category_id.id
            
            if warning and with_warning:
                res['warning'] = msg
            
        return res
    
    
    @api.onchange('uom_qty', 'uom_id')
    def _onchange_uom_qty(self):
        """
            Au changement de la qty, changement des autres qty
        """
        res = {}
        if self.product_id: 
            qtys = self.product_id.get_qtys(self.uom_qty, 
                                     uom_id=self.uom_id, 
                                     sec_uom_id=self.sec_uom_id, 
                                     uoi_id=self.uoi_id, 
                                     by_field='uom', 
                                     dual_unit=self.product_id.dual_unit, 
                                     dual_unit_type=self.product_id.dual_unit_type, 
                                     factor=self.factor, 
                                     divisor=self.divisor, 
                                     with_raise=True)
             
            for k, v in qtys.iteritems():
                self[k] = v
             
            if self.uom_id:
                self.uom_category_id = self.uom_id.category_id.id
                 
            if not self.uom_id or not self.sec_uom_id:
                res['warning'] = {'title': _('Warning'), 'message': _('You must have Management unit and Sale unit')}
         
        return res
            
            
    @api.onchange('uoi_qty', 'uoi_id', 'property_ids')
    def _onchange_uoi_qty(self):
        """
            Au changement de la qty, changement des autres qty
        """
        if self.product_id:
            qtys = self.product_id.get_qtys(self.uoi_qty, 
                                     uom_id=self.uom_id, 
                                     sec_uom_id=self.sec_uom_id, 
                                     uoi_id=self.uoi_id, 
                                     by_field='uoi', 
                                     dual_unit=self.product_id.dual_unit, 
                                     dual_unit_type=self.product_id.dual_unit_type, 
                                     factor=self.factor, 
                                     divisor=self.divisor, 
                                     with_raise=True)
             
            for k, v in qtys.iteritems():
                self[k] = v
             
            if self.uoi_id:
                self.uoi_category_id = self.uoi_id.category_id.id
                 
            if not self.uom_id or not self.uoi_id:
                self.sec_uom_qty = 0
            
    
    @api.onchange('requested_date', 'transport_delay')
    def _onchange_requested_date(self):
        """
            Au changement de la date demandée ou du délai de transport, on va calculer la date
            de départ de la commande
            On vérifie également que la date demandée fasse bien parti du calendrier client
        """
        res = {}
        now = fields.Date.today()
        if self.requested_date:
            if self.requested_date < now:
                res['warning'] = {'title': _('Warning'), 'message': _('The requested date is in the past')}
        
            calendar = self.sale_order_id.delivered_customer_id.calendar_id
            if calendar:
                check_date = self.env['calendar.line'].search([('calendar_id', '=', calendar.id),
                                                               ('real_start_date', '<=', self.requested_date),
                                                               ('real_end_date', '>=', self.requested_date)])
                if not check_date:
                    res['warning'] = {'title': _('Warning'), 'message': _('The selected date is not a business '
                                                                          'day for this customer')}
        
        return res
                
    
    @api.onchange('confirmed_departure_date')
    def _onchange_confirmed_departure_date(self):
        """
            Au changement de la date de départ confirmée, on vérifie que celle-ci soit valide
            On vérifie également qu'elle fasse bien partie du calendrier de la société
        """
        res = {}
        now = fields.Date.today()
        if self.confirmed_departure_date:
            if self.confirmed_departure_date < now:
                res['warning'] = {'title': _('Warning'), 'message': _('The confirmed departure date is in the past')}
        
            calendar = self.sale_order_id.company_id.partner_id.calendar_id
            if calendar:
                check_date = self.env['calendar.line'].search([('calendar_id', '=', calendar.id),
                                                               ('real_start_date', '<=', self.confirmed_departure_date),
                                                               ('real_end_date', '>=', self.confirmed_departure_date)])
                if not check_date:
                    res['warning'] = {'title': _('Warning'), 'message': _('The confirmed departure date is not a business '
                                                                          'day for your company')}
        
        return res
    
    
    @api.onchange('scheduled_date')
    def _onchange_scheduled_date(self):
        """
            Au changement de la date planifiée, on vérifie qu'elle soit dans le calendrier
            de la société
        """
        res = {'warning': {}}
        calendar = self.sale_order_id.company_id.partner_id.calendar_id
        if calendar and self.scheduled_date:
            check_date = self.env['calendar.line'].search([('calendar_id', '=', calendar.id),
                                                           ('real_start_date', '<=', self.scheduled_date),
                                                           ('real_end_date', '>=', self.scheduled_date)])
            if not check_date:
                res['warning'] = {'title': _('Warning'), 'message': _('The scheduled date is not a business '
                                                                      'day for your company')}
        
        return res
        
    
    @api.multi
    def action_change_date(self):
        """
            Fonction permettant d'appeler le wizard de modification de la date
        """
        action_struc = {}
        for line in self:
            if line.sale_order_id.state in ['done', 'cancel']:
                raise ValidationError(_('You cannot change the value of the date because the sale is done '
                    'or cancelled'))
                 
            action_dict = get_form_view(self, 'sale.action_replacement_date')
            if action_dict and action_dict.get('id') and action_dict.get('type'):
                action = self.env[action_dict['type']].browse(action_dict['id'])
                action_struc = action.read()
                action_struc = action_struc[0]
                
            return action_struc
    
    
    @api.multi
    def show_sale_line_stock_move(self):
        """
            Fonction qui cherche et retourne les mouvements de stock pour une ligne de vente
        """
        action_struc = {}
        action_dict = get_form_view(self, 'sale.sale_stock_move_action')
        if action_dict and action_dict.get('id') and action_dict.get('type'):
            action = self.env[action_dict['type']].browse(action_dict['id'])
            action_struc = action.read()
            action_struc[0]['context'] = {'sale_line_ids': [self.id]}
            action_struc = action_struc[0]
              
        return action_struc
    
    
    @api.multi
    def show_sale_line_invoice_line(self):
        """
            Fonction qui cherche et retourne les lignes de facture de la ligne de vente
        """
        action_struc = {}
        action_dict = get_form_view(self, 'sale.sale_line_invoice_action')
        line_ids = [x.id for x in self.invoice_line_ids]
        if action_dict and action_dict.get('id') and action_dict.get('type'):
            action = self.env[action_dict['type']].browse(action_dict['id'])
            action_struc = action.read()
            action_struc[0]['context'] = {'invoice_ids': line_ids}
            action_struc = action_struc[0]
              
        return action_struc
    
    
    @api.multi
    def change_sale_line_info(self):
        """
            Fonction qui appelle le wizard de modification des informations des lignes de vente
            à condition qu'aucune facture liée à la vente ne soit validée
        """
        action_struc = {}
        action_dict = get_form_view(self, 'sale.action_change_sale_line_info')
        invoice_rs = [x.invoice_id for x in self.invoice_line_ids]
        invoice_rs = list(set(invoice_rs))
        for invoice in invoice_rs:
            if invoice.state != 'draft':
                raise ValidationError(_('You can\'t change the accounting information because there is already a '
                                      'validated invoice linked to the sale'))
                
        if action_dict and action_dict.get('id') and action_dict.get('type'):
            action = self.env[action_dict['type']].browse(action_dict['id'])
            action_struc = action.read()
            action_struc[0]['context'] = {'sale_line_id': self.id}
            action_struc = action_struc[0]
              
        return action_struc
    
    
    def create_sale_order_line(self, sale=False, product=None, values=None, forced_qty=False, forced_price_unit=None):
        """
            Création d'une ligne de vente
            :type self: sale.order.line
            :param sale: La vente liée à la ligne
            :type sale: recordset: sale.order
            :param product: Le produit de la ligne de vente
            :type product: recordset product.product
            :param values: Les détails de la ligne de vente (optionnel)
            :type values: dict {'uom_qty':..., 'price_unit':... }
            :param forced_qty: True si on souhaite entrer une qté inférieure à la qté minimale
            :type forced_qty: boolean
            :param forced_price_unit: Si on a forced_price_unit alors on force le prix
            :type forced_price_unit: float
            :return: La lignee de vente créée
            :rtype: recordset sale.order.line
        """
        vals = {}
        if not values:
            values = {}
            
        if sale and product:
            multiple_qty = 1
            min_qty = 1
            if isinstance(sale, int):
                sale = self.env['purchase.order'].browse(sale)
            
            if isinstance(product, int):
                product = self.env['product.product'].browse(product)
                
            vals['sale_order_id'] = sale.id
            vals['product_id'] = product.id
            #On lance le onchange principal du produit pour récupérer toutes ses informations
            #On fait en sorte de ne récupérer que les ids de ce qui est retourné
            #On récupère le minimum et le multiple du produit
            if product.free_sale:
                min_qty = product.sale_min_qty
                multiple_qty = product.sale_multiple_qty
            else:
                customer = product.get_cinfo(partner_id=sale.partner_id.id, property_ids=False)
                if customer:
                    min_qty = customer.min_qty
                    multiple_qty = customer.multiple_qty
            
            if multiple_qty == 0:
                multiple_qty = 1
            
            #On récupère la quantité minimum du produit en fonction du multiple
            min_qty = roundingUp(min_qty, multiple_qty)
            if 'sec_uom_qty' in values:
                send_qty = values['sec_uom_qty']
            else:
                send_qty = False
                
            vals.update(utils.transform_to_ids(self, self.onchange_product_id(product, sale, send_qty)))
                
            #On récupère les valeurs "forcées"
            if values:
                #Si on a forcé la quantité (forced_qty=True), alors on récupère forcément cette valeur
                #Sinon, on supprime la quantité passée et on laisse la quantité minimum calculée par le onchange
                if 'sec_uom_qty' in values and values['sec_uom_qty'] < min_qty and not forced_qty:
                    del values['sec_uom_qty']
                    
                vals.update(values)
            #Création de la ligne d'achat
            sale_line = self.create(vals)
            #Lancement des onchanges de calcul des quantité et des unités
            sale_line._onchange_sec_uom_qty()
            sale_line._onchange_uom_qty()
            sale_line._onchange_uoi_qty()
            # Commenter car isinstance(False, int) renvoie True et donc force le prix à False
#             if isinstance(forced_price_unit, (float, int)):
            if type(forced_price_unit) == int or type(forced_price_unit) == float:
                sale_line.price_unit = forced_price_unit
            
            sale_line.price_unit_without_discount = sale_line.price_unit
            return sale_line
        else:
            return False
    
    
    @api.multi
    def compute_delivered_qty(self):
        """
            Fonction permettant de calculer les champs de quantités livrées, commandées
            et restantes des lignes de vente
            :type self: sale.order.line
            :rtype: Boolean
        """
        remaining_qty = 0
        delivered_qty = 0
        uom_id = self.uom_id.id
        product_id = self.product_id.id
        move_obj = self.env['stock.move']
        uom_obj = self.env['product.uom']
        move_datas = move_obj.search_group(fields=['uom_qty', 'uom_id', 'type', 'state', 'date'], 
                                           groupby=['product_id', 'uom_id', 'type', 'state'], 
                                           args=[('sale_line_id', '=', self.id), ('product_id', '=', product_id)],
                                           sum='uom_qty',
                                           max='date',
                                           return_dict=True)
        dates = []
        for move_data in move_datas:
            if move_data['uom_id'] == uom_id:
                qty = move_data['uom_qty']
            else:
                qty = uom_obj._compute_qty(move_data['uom_id'], move_data['uom_qty'], to_uom_id=uom_id, with_raise=True, with_round=False)

            if move_data['type'] == 'out':
                # Si le move est done, on incrémente la quantité livrée
                if move_data['state'] == 'done':
                    delivered_qty += qty
                    dates.append(move_data['date'])
                    
                # Sinon, on incrémente la quantité restante
                elif move_data['state'] == 'waiting':
                    remaining_qty += qty
                    
            # Si le move est 'IN' on va venir ajouter la quantité à la quantité restante
            elif move_data['type'] == 'in':
                # Si le move est done, on incrémente la quantité restante et on décrémente la quantité reçue
                if move_data['state'] == 'done':
                    delivered_qty -= qty
            
        self.write({'remaining_qty': remaining_qty, 'delivered_qty': delivered_qty, 'last_delivery_date': dates and max(dates) or False})
        return True
    
    
    def change_invoiced_amount(self, amount=0, add=False, inv_currency_rs=False, inv_date=False):
        """
            Fonction permettant d'ajouter ou d'enlever un montant au champ
            de montant de facture généré
            :type self: sale.order.line
            :param amount: Le montant à ajouter ou à retirer
            :type amount: float
            :param add: Si on doit ajouter ou enlever la quantité
            :type add: boolean
            :param inv_currency_rs: La devise de la facture
            :type inv_currency_rs: recordset: res.currency
            :param inv_date: Date de la facture
            :type inv_date: Date
            :return: True
            :rtype: Boolean
        """
        vals = {}
        context2 = {}
        context2.update(self.env.context)
        #On récupère la valeur initiale de la quantité facturée
        #de la ligne de vente
        #On récupère la valeur initiale de la quantité facturée
        #de la vente
        sale_order = self.sale_order_id
        sale_invoiced_amount = sale_order.sale_invoiced_amount
        if sale_order.currency_id != inv_currency_rs:
            if inv_date:
                context2['date'] = inv_date
                
            amount = inv_currency_rs.with_context(context2).compute(amount, sale_order.currency_id)
            
        if add:
            vals['sale_invoiced_amount'] = sale_invoiced_amount + amount
        else:
            vals['sale_invoiced_amount'] = sale_invoiced_amount - amount
            
        sale_order.write(vals)
        return True

    
    @api.multi
    def update_delay(self, date=False, with_raise=True):
        if date:
            self.write({'scheduled_date': date})
            
        so_obj = self.env['sale.order']
        for sol in self.read(['sale_order_id', 'requested_date'], load='_classic_write'):
            if not date:
                self.browse(sol['id']).write({'scheduled_date': sol['requested_date']})
                
            so_rs = so_obj.browse(sol['sale_order_id'])
            so_datas = so_rs.read(['state', 'name'])[0]
            if so_datas['state'] == 'waiting_delay':
                so_rs.update_waiting_delay()
            elif with_raise:
                raise Warning(_('Error! Sale order %s must be in state waiting delay to be able to change its date')%(so_rs.name))
                
        return True
    
    
    def confirm_forecast_line(self):
        """
            Fonction permettant de passer la vente liée à la ligne de vente en type "Série" si
            elle est de type prévisionnelle
        """
        if self.sale_type == 'forecast':
            self.sale_order_id.write({'type': 'series'})
                
        return True
    
    
    @api.multi
    @api.depends('name')
    def name_get(self):
        """
            On affiche : nom [sequence]
        """
        result = []
        for order_line in self:
            if order_line.sale_order_id:
                name = '%s [%s]'%(order_line.sale_order_id.name, order_line.sequence)
            else:    
                name = order_line.name
                 
            result.append((order_line.id, name))
             
        return result
    
    
    @api.multi
    def unlink(self):
        """
            On supprime le move cancel lié à la ligne de vente, et le BL s'il n'avait que ce move
        """
        for line in self:
            picking_list = self.env['stock.picking']
            for move in line.stock_move_ids:
                if move.state == 'cancel':
                    picking_list += move.picking_id
                    move.unlink()
            
            #Si le picking n'a plus de move, on le supprime
            for picking in picking_list:
                if not picking.move_ids:
                    picking.unlink()
            
        return super(sale_order_line, self).unlink()
    
    
    @api.model
    def create(self, vals):
        """
            A la création de la ligne, on attribut la valeur de la date de création
            à la date du calendrier
        """
        sale_line = super(sale_order_line, self).create(vals)
        sale_line.write({'calendar_date': sale_line.create_date})
        return sale_line
    
    
    @api.multi
    def copy(self, default=None):
        """
            On vide les champs de quantités livrées et facturées
            Et les dates confirmées
        """
        if not default:
            default = {}
        
        new_default = {
                       'delivered_qty' : 0,
                       'remaining_qty' : 0,
                       'scheduled_date': False,
                       'confirmed_departure_date': False,
                       }
        default.update(new_default)
        return super(sale_order_line, self).copy(default=default)
    


class sale_order(models.Model):
    """ 
    Sale module 
    """
    _name = 'sale.order'
    _description = 'Sale module'
    _inherit = 'workflow.base'
    _order = 'id desc'
    
    
    @api.model
    def _type_get(self):
        return [
                ('forecast', _('Forecast')),
                ('prototype', _('Prototype')),
                ('series', _('Series')),
                ('open', _('Open')),
                ('call', _('Called')),
                ('renting', _('Renting')),
                       ]
    

    # START TO DELETE #    
    @api.model
    def _sale_account_invoice_trigger_get(self):
        return [
                ('picking', _('To the delivery')),
                ('manual', _('On demand')),
                ('postpaid', _('On the order')),
                       ]
    
    
    @api.model
    def _sale_account_invoiced_on_get(self):
        return [
                ('order', _('Ordered quantities')),
                ('delivery', _('Delivered quantities')),
                       ]
        
    
    @api.model
    def _payment_type_get(self):
        return [
                ('before_validation', _('On the order')),
                ('before_delivery', _('Before delivery')),
                ('after_invoicing', _('After invoicing')),
                       ]
    # END TO DELETE #
        
        
    @api.model
    def _sale_send_method_get(self):
        return [
                ('manual', _('Manual printing')),
                ('printer', _('Printer')),
                ('edi', _('EDI')),
                ('email', _('Mail')),
                       ]
    
    
    @api.model
    def _sale_communication_method_get(self):
        return [
                ('fax', _('Fax')),
                ('email', _('Email')),
                       ]
    
    
    @api.one
    @api.depends('sale_contact_ids', 'sale_communication_method', 'partner_id')
    def _compute_sale_communication_value(self):
        if self.partner_id:
            self.sale_communication_value = self.env['res.partner'].calcul_value_com(self.sale_contact_ids, 
                                                                                     self.partner_id, self.sale_communication_method)
        else:
            self.sale_communication_value = ''
    
    
    @api.one
    @api.depends('order_line_ids.total_price', 'tax_line_ids.amount')
    def _compute_amount(self):
        self.amount_ex_taxes = sum(line.total_price for line in self.order_line_ids)
        self.taxes = sum(line.amount for line in self.tax_line_ids)
        self.total_amount = self.amount_ex_taxes + self.taxes
    
    
    @api.one
    @api.depends('delivery_note_ids.state', 'delivery_note_ids.move_ids')
    def _compute_delivered_amount(self):
        delivered_amount = 0
        for picking in self.delivery_note_ids:
            if picking.state == 'done':
                delivered_amount += sum(move.uoi_qty * move.partner_price for move in picking.move_ids)
                
        self.delivered_amount = delivered_amount
        
        
    @api.one
    @api.depends('delivered_amount', 'total_amount', 'state', 'invoicing_method_id')
    def _compute_residual_amount(self):
        residual_amount = 0
        if self.state == 'progress':
            if self.sale_invoice_balance_invoiced_on == 'order':
                residual_amount = self.amount_ex_taxes - self.sale_invoiced_amount
            elif self.sale_invoice_balance_invoiced_on == 'delivery':
                residual_amount = self.delivered_amount - self.sale_invoiced_amount
                
        self.residual_amount = residual_amount
    
    
    @api.one
    @api.depends('accounting_contact_ids', 'sale_send_method', 'invoiced_customer_id')
    def _compute_accounting_communication_value(self):
        if self.partner_id and self.sale_send_method == 'email':
            self.accounting_communication_value = self.env['res.partner'].calcul_value_com(self.accounting_contact_ids, 
                                                                                     self.invoiced_customer_id, 'email')
        else:
            self.accounting_communication_value = ''
    
    
    @api.one
    @api.depends('requested_date', 'transport_delay')
    def _compute_departure_date(self):
        """
            Au changement de la date demandée ou du délai de transport, on va calculer la date
            de départ de la commande
        """
        departure_date = False
        if self.partner_id.calendar_id:
            if self.requested_date:
                departure_date = self.partner_id.calendar_id.get_date_inverse(self.requested_date, self.transport_delay)
        
        if not departure_date:
            departure_date = self.compute_date_delay(self.requested_date, self.transport_delay)
        
        self.departure_date = departure_date
    
    
    @api.model
    def _sale_invoice_postage_get(self):
        return [
                ('never', _('Never')),
                ('always', _('Always')),
                ('threshold', _('< Threshold')),
                       ]
    
    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('waiting', _('Waiting')),
                ('waiting_delay', _('Awaiting delay')),
                ('waiting_conf_delay', _('Sent the confirmation')),
                ('progress', _('In progress')),
                ('done', _('Done')),
                ('cancel', _('Cancelled')),
                       ]
    
    
    @api.model
    def _sale_month_get(self):
        return [
                    ('00', _('Without month')), 
                    ('01', _('January')), 
                    ('02', _('February')), 
                    ('03', _('March')), 
                    ('04', _('April')), 
                    ('05', _('May')), 
                    ('06', _('June')), 
                    ('07', _('July')), 
                    ('08', _('August')), 
                    ('09', _('September')), 
                    ('10', _('October')), 
                    ('11', _('November')), 
                    ('12', _('December'))
           ]
    
    
    @api.model
    def _sale_day_get(self):
        return [
                    ('0', _('Without day')), 
                    ('1', _('Monday')), 
                    ('2', _('Tuesday')), 
                    ('3', _('Wednesday')), 
                    ('4', _('Thursday')), 
                    ('5', _('Friday')), 
                    ('6', _('Saturday')), 
                    ('7', _('Sunday'))
           ]
    
    
    @api.model
    def _invoices_period_get(self):
        return [
                ('end_week', _('End of week')),
                ('end_month', _('End of month')),
                       ]
    
    
    @api.one   
    @api.depends('order_line_ids')
    def _compute_invoice_line_ids(self):
        """
            On récupère toutes les lignes de factures liées aux lignes de ventes
        """
        invoice_line_list = []
        for line in self.order_line_ids:
            invoice_line_list.extend([x.id for x in line.invoice_line_ids])
        
        self.invoice_line_ids = invoice_line_list
    

    
    @api.one
    @api.depends('confirmation_date')
    def _compute_sale_order_date(self):
        """
            Fonction qui calcule le jour, la semaine, le mois et l'année de la vente
        """
        date = False
        #On prend la date de confirmation
        if self.quotation_date:
            date = fields.Date.from_string(self.quotation_date)
        else:
            self.week_number = '00'
            self.month = '00'
            self.year = '0'
            self.day = False
        
        if date:
            #On récupère le nom du jour et le numéro de l'année
            isocal = date.isocalendar()
            self.day = str(isocal[2])
            self.year = str(isocal[0])
            #On récupère le numéro de semaine
            if len(str(isocal[1])) == 1:
                self.week_number = '0%s'%(str(isocal[1]))
            else:
                self.week_number = str(isocal[1])
            
            #On récupère le mois
            if len(str(date.month)) == 1:
                self.month = '0%s'%(str(date.month))
            else:
                self.month = str(date.month)
    
    
    @api.one
    @api.depends('order_line_ids.delay_confirm', 'type')
    def _compute_delay_confirm(self):
        if self.type == 'open':
            self.delay_confirm  = False
        else:
            self.delay_confirm  = max([l.delay_confirm for l in self.order_line_ids] or [False])

    
    @api.one   
    def _compute_advanced_amount(self):
        """
            On recherche d'éventuelles factures anticipées et on calcule le montant total, 
            ainsi que le montant restant à payer 
        """
        total_amount = 0
        total_without_tax = 0
        invoice_amount = 0
        remaining_amount = 0
        advanced_invoice = False
        if self.order_line_ids:
            anticipated_invoice_list = []
            #On recherche les factures anticipées liées à la vente
            account_line_obj = self.env['account.invoice.line']
            advanced_invoice_lines = account_line_obj.search([('sale_order_line_id', 'in', self.order_line_ids.ids),
                                                        ('invoice_id.anticipated', '=', True)])
            if advanced_invoice_lines:
                advanced_invoice = True
                for line in advanced_invoice_lines:
                    if not line.invoice_id in anticipated_invoice_list:
                        total_amount += line.invoice_id.amount_total
                        total_without_tax += line.invoice_id.amount_untaxed
                        anticipated_invoice_list.append(line.invoice_id)
            
            #On cherche les éventuelles lignes de facture négatives liées à la vente
            invoiced_amount_lines = account_line_obj.search([('sale_order_line_id', 'in', self.order_line_ids.ids),
                                                             ('price_unit', '<', 0)])
            #On effectue le calcul ligne par ligne afin de prendre en compte les éventuelles taxes
            for invoiced_line in invoiced_amount_lines:
                invoice_amount += invoiced_line.price_unit / -1
                taxes = invoiced_line.invoice_line_tax_ids.compute_all(invoiced_line.price_unit, invoiced_line.currency_id, 
                                                            invoiced_line.sec_uom_qty, invoiced_line.product_id, 
                                                            invoiced_line.partner_id)['taxes']
                for tax in taxes:
                    if tax['amount'] < 0:
                        invoice_amount += tax['amount'] / -1
                    else:
                        invoice_amount += tax['amount']
            
        #Gestion de l'arrondi provoqué par les taxes
        if 0 < (total_amount - invoice_amount) <= 0.1:
            remaining_amount = 0
        else:
            remaining_amount = total_amount - invoice_amount
            
        self.advanced_amount = total_amount
        self.advanced_amount_without_tax = total_without_tax
        self.remaining_advanced_amount = remaining_amount
        self.advanced_invoice = advanced_invoice

                
    @api.one
    @api.depends('invoicing_method_id')
    def _compute_block_paymen_term(self):
        self.block_picking_payment = False
        self.block_sale_payment = False
        self.need_picking_payment = False
        self.need_sale_payment = False
        if self.id:
            self.env.cr.execute("""
            SELECT  
              DISTINCT impl.payment_type, true as blocking
            FROM
              sale_order s
              JOIN account_invoicing_method im ON s.invoicing_method_id = im.id
              JOIN account_invoicing_method_payment_line impl ON im.id = impl.invoicing_method_id
            WHERE
              s.id = %s AND
              impl.is_blocking
            
            UNION ALL
              
            SELECT  
              DISTINCT impl.payment_type, false as blocking
            FROM
              sale_order s
              JOIN account_invoicing_method im ON s.invoicing_method_id = im.id
              JOIN account_invoicing_method_payment_line impl ON im.id = impl.invoicing_method_id
            WHERE
              s.id = %s AND
              not impl.is_blocking
            """%(self.id, self.id))
            query_res = self.env.cr.dictfetchall()
            if query_res:
                for query_res_item in query_res:
                    if query_res_item['payment_type'] == 'before_delivery':
                        self.need_picking_payment = True
                        if query_res_item['blocking']:
                            self.block_picking_payment = True
                            
                    elif query_res_item['payment_type'] == 'before_validation':
                        self.need_sale_payment = True
                        if query_res_item['blocking']:
                            self.block_sale_payment = True
                
                
    @api.one
    @api.depends('invoicing_method_id')
    def _compute_sale_invoice_balance(self):
        self.sale_invoice_balance_trigger = False
        self.sale_invoice_balance_invoiced_on = False
        if self.id:
            self.env.cr.execute("""
                SELECT
                  iml.invoice_trigger,
                  iml.account_invoiced_on
                FROM
                  sale_order s
                  JOIN account_invoicing_method im ON s.invoicing_method_id = im.id
                  JOIN account_invoicing_method_line iml ON im.id = iml.invoicing_method_id
                WHERE
                  s.id = %s
                  AND iml.value = 'balance'
                LIMIT 1
                """%(self.id))
            
            query_res = self.env.cr.dictfetchone()
            if query_res:
                self.sale_invoice_balance_trigger = query_res['invoice_trigger']
                self.sale_invoice_balance_invoiced_on = query_res['account_invoiced_on']
            
        
    @api.one
    @api.depends('invoicing_method_id')
    def _compute_sale_invoice_trigger(self):
        self.sale_invoice_trigger_postpaid = False
        self.sale_invoice_trigger_manual = False
        self.sale_invoice_trigger_picking = False
        if self.id:
            self.env.cr.execute("""
            SELECT
              iml.invoice_trigger
            FROM
              sale_order s
              JOIN account_invoicing_method im ON s.invoicing_method_id = im.id
              JOIN account_invoicing_method_line iml ON im.id = iml.invoicing_method_id
            WHERE
              s.id = %s
            GROUP BY
              iml.invoice_trigger
            """%(self.id))
            query_res = self.env.cr.dictfetchall()
            if query_res:
                for query_res_item in query_res:
                    if query_res_item['invoice_trigger'] == 'postpaid':
                        self.sale_invoice_trigger_postpaid = True
                    elif query_res_item['invoice_trigger'] == 'manual':
                        self.sale_invoice_trigger_manual = True
                    elif query_res_item['invoice_trigger'] == 'picking':
                        self.sale_invoice_trigger_picking = True
            
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    
    # En-tête
    name = fields.Char(required=True, string='Order reference', default='/', readonly=True, copy=False)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, ondelete='restrict')
    ref_order = fields.Char(string='Order reference', size=256, required=False)
    order_date = fields.Date(string='Input order date', default=lambda self: fields.Date.today())
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, ondelete='restrict')
    type = fields.Selection('_type_get', string='Type')
    state = fields.Selection('_state_get', string='State', default='draft')
    show_invoice_button = fields.Boolean(string='Show invoice button', default=True, copy=False)
    renting_end_date = fields.Date(string='Renting end date')
    
    # Références
    requested_date = fields.Date(string='Requested date')
    transport_delay = fields.Integer(string='Transport delay', default=0, required=False, help="The transport delay come from the delivered partner.")
    departure_date = fields.Date(string='Departure date', compute='_compute_departure_date')
    order_line_ids = fields.One2many('sale.order.line', 'sale_order_id',  string='Sale order line', copy=False)
    amount_ex_taxes = fields.Float(string='Amount excluding taxes', default=0.0, required=False, compute='_compute_amount')
    taxes = fields.Float(string='taxes', default=0.0, required=False, compute='_compute_amount')
    total_amount = fields.Float(string='Total', default=0.0, required=False, compute='_compute_amount')
    delivered_amount = fields.Float(string='Delivered amount', default=0.0, required=False, compute='_compute_delivered_amount')
    residual_amount = fields.Float(string='Residual', default=0.0, required=False, compute='_compute_residual_amount')
    max_sequence = fields.Integer(string='Sequence max', default=10, required=False)
    tax_line_ids = fields.One2many('account.sale.tax', 'sale_id',  string='Taxes update', copy=True)
    
    # Adresse
    invoiced_customer_id = fields.Many2one('res.partner', string='Invoiced customer', required=True, ondelete='restrict')
    invoicing_address_id = fields.Many2one('address', string='Invoicing address', required=True, ondelete='restrict')
    tva_number = fields.Char(string='TVA number', size=32, required=False)
    subject_deb = fields.Boolean(string='DEB declaration', default=False)
    order_address_id = fields.Many2one('address', string='Order address', required=True, ondelete='restrict')
    final_customer_id = fields.Many2one('res.partner', string='Final customer', required=False, ondelete='restrict')
    paid_customer_id = fields.Many2one('res.partner', string='Payer customer name', required=True, ondelete='restrict')
    location_id = fields.Many2one('stock.location', string='Location', required=True, ondelete='restrict')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True, default=lambda self: self.env.user.company_id.warehouse_id, ondelete='restrict')
    delivered_customer_id = fields.Many2one('res.partner', string='Delivered customer', required=True, ondelete='restrict', 
                                          domain=[('is_company', '=', True), ('can_be_delivered', '=', True), ('is_customer', '=', True), ('state', 'not in', ['prospect', 'stopped'])])
    delivered_contact_id = fields.Many2one('res.partner', string='Contact', required=False, ondelete='restrict')
    delivered_name = fields.Char(string='Name', size=128, required=True)
    delivered_street = fields.Char(string='Street', size=128, required=False)
    delivered_street2 = fields.Char(string='Street 2', size=128, required=False)
    delivered_street3 = fields.Char(string='Street 3', size=128, required=False)
    delivered_zip = fields.Char(string='Zip', size=24, required=False)
    delivered_city = fields.Char(string='City', size=128, required=False)
    delivered_region_id = fields.Many2one('res.region', string='Region', required=False, ondelete='restrict')
    delivered_country_id = fields.Many2one('res.country', string='Country', required=True, ondelete='restrict')
    delivered_address_id = fields.Many2one('address', string='Delivered address', required=True, ondelete='restrict')
    
    # Comptabilité
    discount = fields.Boolean(string='Discount', default=False, help="Comes from the customer who pays the order")
    discount_value = fields.Float(string='Discount value in percentage', default=0.0, required=False)
    max_delay = fields.Integer(string='Maximal delay applicated', default=0, required=False)
    sale_account_system_id = fields.Many2one('account.fiscal.position', string='Account system', required=True, ondelete='restrict', help="Comes from the delivered customer")
    sale_send_method = fields.Selection('_sale_send_method_get', string='Send method', required=False)
    group_invoices = fields.Boolean(string='Group invoices', default=False, help="Comes from the invoiced customer")
    invoices_period = fields.Selection('_invoices_period_get', string='Invoices period', required=False)
    locked_invoice = fields.Boolean(string='Locked invoice', default=False, help="Comes from the invoiced customer")
    accounting_contact_ids = fields.Many2many('res.partner', 'accounting_contact_id_sale_rel', 'sale_order_id', 'contact_id', string='Contacts', help='If you choose a contact, '
                                      'the communication value will refer to its coordinates')
        # Paiements
    invoicing_method_id = fields.Many2one('account.invoicing.method', string='Invoicing method', required=True, ondelete='restrict', help='Comes from the customer who pays the order')
    payment_id = fields.Many2one('payment.method', string='Payment', required=True, ondelete='restrict', help='Comes from the customer who pays the order')
    payment_term_id = fields.Many2one('account.payment.term', string='Payment term', required=True, ondelete='restrict', help='Comes from the customer who pays the order')
    block_picking = fields.Boolean(string='Block delivery', default=False, copy=False, help="Check if you want to block manually the picking. You will have to unlock manually the picking.")
    payment_ids = fields.One2many('account.voucher', 'sale_id',  string='Payments', help="The automatic payments linked to the sale")
    manual_hide_invoice_button = fields.Boolean(default=False, copy=False)
    check_paid = fields.Boolean(string='Paid', default=False, copy=False)
    need_sale_payment = fields.Boolean(compute='_compute_block_paymen_term')
    block_sale_payment = fields.Boolean(compute='_compute_block_paymen_term')
    block_picking_payment = fields.Boolean(compute='_compute_block_paymen_term')
    need_picking_payment = fields.Boolean(compute='_compute_block_paymen_term')
        # Facturation
    sale_invoice_balance_invoiced_on = fields.Char(compute='_compute_sale_invoice_balance')
    sale_invoice_balance_trigger = fields.Char(compute='_compute_sale_invoice_balance')
    sale_invoice_trigger_manual = fields.Boolean(compute='_compute_sale_invoice_trigger')
    sale_invoice_trigger_picking = fields.Boolean(compute='_compute_sale_invoice_trigger')
    sale_invoice_trigger_postpaid = fields.Boolean(compute='_compute_sale_invoice_trigger')
        
    # START TO DELETE
    sale_account_invoiced_on = fields.Selection('_sale_account_invoiced_on_get', string='Invoiced on', required=False, help='This field '
                                                'comes from the invoiced customer. It indicates if the invoice on the basis of quantities '
                                                'actually delivered or on the basis of quantities ordered (can be useful in case of flat rate'
                                                ', for example)')
    sale_account_invoice_trigger = fields.Selection('_sale_account_invoice_trigger_get', string='Invoicing method trigger', required=False, help='Comes from the invoiced customer')
    payment_type = fields.Selection('_payment_type_get', string='Payment type', required=False, default='after_invoicing', related='payment_term_id.payment_type', store=False, readonly=True)
    check_paid_invoice = fields.Boolean(string='Paid invoice', default=False, copy=False)
    check_paid_sale = fields.Boolean(string='Paid sale', default=False, copy=False)
    # END TO DELETE
    
    # Champ conservé pour la reprise des données, à supprimer plus tard
    accounting_contact_id = fields.Many2one('res.partner', string='Contact', required=False, ondelete='restrict', help='If you choose a contact, '
                                            'the communication value will refer to its coordinates')
    accounting_communication_value = fields.Char(string='Communication value', compute='_compute_accounting_communication_value')
    
    # Communication
    receipt_demand = fields.Boolean(string='Order\'s acknowledgement of receipt', default=False)
    delay_confirmation = fields.Boolean(string='Delay confirmation', default=False)
    sale_communication_method = fields.Selection('_sale_communication_method_get', string='Communication method')
    sale_contact_ids = fields.Many2many('res.partner', 'sale_contact_id_sale_rel', 'sale_order_id', 'contact_id', string='Contacts', help='If you choose a contact, '
                                      'the communication value will refer to its coordinates')
    # Champ conservé pour la reprise des données, à supprimer plus tard
    sale_contact_id = fields.Many2one('res.partner', string='Contact', required=False, ondelete='restrict')
    sale_communication_value = fields.Char(string='Communication value', compute='_compute_sale_communication_value')
    creation_date = fields.Datetime(string='Creation date')
    creation_user_id = fields.Many2one('res.users', string='User', required=False, ondelete='restrict')
    ar_send_date = fields.Datetime(string='AR send date')
    ar_user_id = fields.Many2one('res.users', string='User', required=False, ondelete='restrict')
    confirmation_date = fields.Datetime(string='Confirmation date')
    confirmation_user_id = fields.Many2one('res.users', string='User', required=False, ondelete='restrict')
    seller_id = fields.Many2one('res.users', string='Seller', required=False, ondelete='restrict')
    sale_manager_id = fields.Many2one('res.users', string='Sale manager', required=False, ondelete='restrict')
    company_id = fields.Many2one('res.company', string='Company', required=False, ondelete='restrict', readonly=True, default=lambda self:self.env.user.company_id)
    quotation_date = fields.Date(string='Quotation date')
    quotation_user_id = fields.Many2one('res.users', string='User', required=False, ondelete='restrict')
    validity_period = fields.Integer(string='Validity period', default=0, required=False, help='The validity period for the quotation')
    
    # Historique
    delivery_note_ids = fields.One2many('stock.picking', 'sale_id',  string='Delivery notes')
    invoice_line_ids = fields.One2many('account.invoice.line', compute='_compute_invoice_line_ids')
    advanced_invoice = fields.Boolean(string='Has an advanced invoice', default=False, compute='_compute_advanced_amount', store=False)
    advanced_amount = fields.Float(string='Advanced invoice amount', default=0.0, required=False, compute='_compute_advanced_amount', store=False)
    advanced_amount_without_tax = fields.Float(string='Advanced invoice amount without taxes', default=0.0, required=False, compute='_compute_advanced_amount', store=False)
    remaining_advanced_amount = fields.Float(string='Remaining advanced invoice amount', default=0.0, required=False, compute='_compute_advanced_amount', store=False)
    
    # Mail et PJ
    mail_ids = fields.One2many('mail.mail', 'sale_id',  string='Mails', readonly=True)
    
    # Notes
    inter_note = fields.Text(string='Intern note / Preparation note')
    work_note = fields.Text(string='Printed work note')
    delivery_note = fields.Html(string='Note on delivery note')
    invoice_note = fields.Html(string='Invoice note')
    customer_order_note = fields.Html(string='Note printed on customer order')
    
    # Livraison
    partial_delivery = fields.Boolean(string='Partial delivery allowed', default=False, help="Comes from the customer who orders")
    allowed_rest = fields.Boolean(string='Allowed rest', default=False, help="Comes from the customer who orders")
    delivery_note_and_date = fields.Boolean(string='Make delivery note for each delivery date', default=False)
    sale_incoterm_id = fields.Many2one('stock.incoterms', string='Incoterm', required=False, ondelete='restrict', help='Incoterm which '
                                       'stands for \'International Commercial terms\' implies its a series of sales terms which are used '
                                       'in the commercial transaction.')
    sale_invoice_postage = fields.Selection('_sale_invoice_postage_get', string='Invoice postage', required=False)
    sale_threshold = fields.Float(string='Threshold', default=0.0, required=False)
    sale_forwarding_agent_id = fields.Many2one('res.partner', string='Forwarding Agent', required=False, ondelete='restrict', domain=[('is_company', '=', True)])
    
    # Commandes appellées
    open_order_id = fields.Many2one('sale.order', string='Open order', required=False, ondelete='restrict')
    called_order_ids = fields.One2many('sale.order', 'open_order_id', string='Called orders', readonly=True)
    
    # Montant facturé
    sale_invoiced_amount = fields.Float(string='Invoiced amount', default=0.0, required=False, digits=dp.get_precision('Product price'), readonly=True)
    
    # Dates pour le search
    year = fields.Char(string='Year', size=4, compute='_compute_sale_order_date', store=True)
    month = fields.Selection('_sale_month_get', string='Month', compute='_compute_sale_order_date', store=True)
    week_number = fields.Char(string='Week number', size=2, compute='_compute_sale_order_date', store=True) 
    day = fields.Selection('_sale_day_get', string='Day', compute='_compute_sale_order_date', store=True)

    # Attente délai
    need_delay_validation = fields.Boolean(default=False, copy=False)
    waiting_delay = fields.Boolean(default=False, copy=False)
    # Champ fonction pour l'affichage du bouton Attente délai
    delay_confirm = fields.Boolean(string='Delay confirm', compute='_compute_delay_confirm') 
            
    done_sale = fields.Boolean('Done sale', default=False, copy=False)
    
        
#     @api.one
#     @api.constrains('sale_account_invoice_trigger', 'sale_account_invoiced_on', 'payment_type', 'payment_term_id')
#     def _check_sale_invoiced_on(self):
#         """
#             Verifie:
#             - que le déclenchement de la facturation soit cohérent avec le type de facturation
#             - que la facturation ne se fait pas sur les quantités livrées si la facturation est manuelle
#         """
#         # On vérifie que le type de paiement soit cohérent avec celui des conditions de paiement
#         if self.sale_account_invoiced_on == 'delivery' and self.sale_account_invoice_trigger != 'picking':
#             raise Warning(_('Error ! You cannot have an invoice in the delivered quantities if the invoice trigger is not on the picking'))
#         
#         if self.sale_account_invoiced_on == 'order':
#             if self.payment_type in ['before_validation', 'before_delivery'] and self.sale_account_invoice_trigger not in ['postpaid', 'manual']:
#                 raise Warning(_('Error ! You cannot have an invoice in the ordered quantities if the invoice trigger is not in the order or manual'))
#             
#     
#     @api.one
#     @api.constrains('payment_type', 'state', 'type')
#     def _check_blocked_sale_order(self):
#         """
#             Verifie que la vente ne puisse pas être validée si elle est bloquée ou si elle est de type prévisionnelle
#         """
#         if self.type == 'forecast' and self.state != ('draft'):
#             raise Warning(_('Error ! You cannot validate a forecast sale'))
#             
#         elif self.payment_type == 'before_validation' and self.state in ('progress', 'done'):
#             if self.sale_account_invoice_trigger == 'manual' and not self.check_paid:
#                 raise Warning(_('Error ! You cannot validate a blocked sale (accounting tab)'))
        
    
    @api.one
    @api.constrains('partial_delivery', 'allowed_rest')    
    def _check_partial_delivery(self):
        """
            Verifie que le booléen de génération de reliquat soit bien décoché si celui
            de livraison incomplète l'es aussi 
        """
        if self.allowed_rest and not self.partial_delivery:
            raise Warning(_('Error ! You cannot generate rest if you don\'t accept partial delivery'))
            
        return True
    
    
    @api.one
    @api.constrains('type', 'order_line_ids', 'open_order_id')    
    def _check_called_order(self):
        """
            Dans le cas d'une commande appelée, vérifie que les produits de la vente sont les mêmes
            que ceux de la commande ouverte attachée. Il peut y avoir moins de produits mais pas
            plus.
        """
        diff_list = False
        if self.type == 'call' and self.open_order_id:
            open_list_ids = []
            call_list_ids = []
            # On récupère les ids des produits de la commande ouverte
            for open_line in self.open_order_id.order_line_ids:
                open_list_ids.append(open_line.product_id.id)
             
            # On récupère les ids des produits de la vente actuelle
            for line in self.order_line_ids:
                call_list_ids.append(line.product_id.id)
            
            if call_list_ids and open_list_ids:
                diff_list = set(call_list_ids) - set(open_list_ids)
            
            if diff_list:
                raise Warning(_('Error ! You cannot have products in your sale that are not present in the opened order'))
             
        return True
    
    
    def onchange_sale_customer(self, partner):
        """
            Récupération des infos du client
        """
        res = {}
        res_partner_obj = self.env['res.partner']
        if isinstance(partner, int):
            partner = res_partner_obj.browse(partner)
        
        if partner:
            #On appelle la fonction 'get_partner_address' de res_partner qui va nous permettre de récupérer
            #toutes les informations des livrés, facturés et payeurs (id et adresses)
            infos = {'delivery': True, 'paid': True, 'invoiced': True}
            info_dict = partner.get_partner_address(infos, return_id=True)
            if isinstance(info_dict, dict):
                #On récupère le partner livré et les informations qui lui sont relatives
                if info_dict.get('delivery_partner', False):
                    delivery_partner = res_partner_obj.browse(info_dict['delivery_partner']) 
                    res['delivered_customer_id'] = info_dict['delivery_partner']
                    res['delivered_address_id'] = info_dict.get('delivery_address', False)
                    res['delivery_note'] = delivery_partner.note_delivery_order
                    res['partial_delivery'] = delivery_partner.partial_sale_delivery
                    res['allowed_rest'] = delivery_partner.generate_sale_rest
                
                # Récupération du partner facturé et des informations qui lui sont relatives
                if info_dict.get('invoiced_partner', False):
                    invoice_partner = res_partner_obj.browse(info_dict['invoiced_partner'])
                    res['invoiced_customer_id'] = info_dict.get('invoiced_partner', False)
                    if not invoice_partner.is_company and invoice_partner.parent_id:
                        invoice_partner = invoice_partner.parent_id
                        
                    res['invoice_note'] = invoice_partner.sale_invoice_note
#                     res['sale_account_invoice_trigger'] = invoice_partner.sale_invoicing_trigger
#                     res['sale_account_invoiced_on'] = invoice_partner.sale_invoiced_on
                    res['accounting_contact_ids'] = [(4, contact_id) for contact_id in invoice_partner.invoicing_contact_ids.ids]
                
                res['invoicing_address_id'] = info_dict.get('invoiced_address', False)
                res['paid_customer_id'] = info_dict.get('pay_partner', False)
                res['order_address_id'] = info_dict.get('order_address', False)
            
            if not partner.is_company and partner.parent_id:
                partner = partner.parent_id
                
            res['currency_id'] = partner.currency_id.id
            res['receipt_demand'] = partner.receipt_demand
            res['delay_confirmation'] = partner.delay_confirmation
            if partner.sale_communication_method != 'printer':
                res['sale_communication_method'] = partner.sale_communication_method
            else:
                res['sale_communication_method'] = False
            
            res['sale_contact_ids'] = [(4, contact_id) for contact_id in partner.sale_contact_ids.ids]
            res['seller_id'] = partner.seller_id.id
            res['sale_manager_id'] = partner.sales_manager_id.id
            res['customer_order_note'] = partner.note_header
            res['inter_note'] = partner.internal_note
            if self.warehouse_id:
                warehouse_rs = self.warehouse_id 
            else:
                warehouse_rs = partner.company_id.warehouse_id
                res['warehouse_id'] = warehouse_rs.id
                
            res['location_id'] = warehouse_rs.delivery_location_id.id
                
        else:
            res['delivered_customer_id'] = False
            res['delivered_address_id'] = False
            res['delivery_note'] = ''
            res['partial_delivery'] = False
            res['allowed_rest'] = False
            res['invoiced_customer_id'] = False
            res['invoice_note'] = ''
#             res['sale_account_invoice_trigger'] = False
#             res['sale_account_invoiced_on'] = False
            res['invoicing_address_id'] = False
            res['paid_customer_id'] = False
            res['order_address_id'] = False
            res['currency_id'] = False
            res['receipt_demand'] = False
            res['sale_communication_method'] = False
            res['sale_contact_ids'] = [(5)]
            res['seller_id'] = False
            res['sale_manager_id'] = False
            res['customer_order_note'] = ''
            res['inter_note'] = ''
            res['location_id'] = False
            res['warehouse_id'] = False
        
        return res
            
    
    @api.onchange('partner_id')
    def _onchange_sale_customer(self):
        """
            Au changement de client, on va récupérer toutes les informations le concernant:
            Adresses de livraison, partenaires de livraisons, notes des ventes, devises etc...
        """
        res = {}
        if self.partner_id:
            partner = self.partner_id
            if partner.is_company and partner.state != 'qualified':
                self.partner_id = False
                res['warning'] = {'title': _('Warning'), 'message': _('The selected partner is not qualified to order, his state '
                                                                      'must be "qualified"')}
                return res
            #Si la limite de crédit est atteinte ou dépassée pour le partenaire, on envoie un message bloquant ou non
            credit_limit = partner.credit_limit
            if credit_limit > 0:
                if partner.invoice_outstanding >= credit_limit:
                    msg = {'title': _('Warning'), 'message': _('The selected partner has reached his credit limit')}
                    res['warning'] = msg
                    if partner.block_sale_credit:
                        self.partner_id = False
                        return res
            
            res2 = self.onchange_sale_customer(partner)
            for k,v in res2.iteritems():
                self[k] = v
        
        return res
    
    
    def onchange_invoiced_customer_id(self, invoiced_customer):
        """
            Récupération des infos du client facturé
        """
        res = {}
        res_partner_obj = self.env['res.partner']
        if isinstance(invoiced_customer, int):
            invoiced_customer = res_partner_obj.browse(invoiced_customer)
            
        if invoiced_customer:
            #On récupère le client chez lequel on va prendre les informations: le partenaire sélectionné,
            #le partenaire parent du contact sélectionné ou rien (si c'est un contact, les infos n'existent pas)
            if not invoiced_customer.is_company and invoiced_customer.parent_id:
                invoiced_customer = invoiced_customer.parent_id
            
            if invoiced_customer:
#                 res['sale_account_invoice_trigger'] = invoiced_customer.sale_invoicing_trigger
                res['group_invoices'] = invoiced_customer.group_invoices
                res['invoices_period'] = invoiced_customer.invoices_period
                res['locked_invoice'] = invoiced_customer.lock_invoices
                if invoiced_customer.accounting_communication_method == 'edi':
                    res['sale_send_method'] = False
                else:
                    res['sale_send_method'] = invoiced_customer.accounting_communication_method
            else:
                #Si le partenaire est un contact sans parent, on vide tous ces champs
#                 res['sale_account_invoice_trigger'] = False
                res['group_invoices'] = False
                res['invoices_period'] = False
                res['locked_invoice'] = False
                res['sale_send_method'] = False
        
        return res
    
    
    @api.onchange('invoiced_customer_id')
    def _onchange_invoiced_customer_id(self):
        """
            Au changement de client, on va récupérer son numéro de TVA, et les informations
            relatives à la facturation de l'onglet de comptabilité
        """
        res = {}
        if self.invoiced_customer_id:
            if self.invoiced_customer_id.is_company and self.invoiced_customer_id.state in ['prospect', 'stopped']:
                res['warning'] = {'title': _('Warning'), 'message': _('The selected invoiced customer is not qualified to be charged, '
                                                                      'his state must be "qualified"')}
                self.invoiced_customer_id = False
                self.invoicing_address_id = False
                self.tva_number = ''
                return res
            
            partner_rs = self.partner_id
            #Si le client est un contact, on récupère le client commandeur qui lui est lié
            if not partner_rs.is_company and partner_rs.parent_id:
                partner_rs = partner_rs.parent_id
                
            partner_verif = self.env['res.partner.type'].search([('partner_type', '=', 'can_be_charged'), 
                                                                 ('partner_type_id', '=', self.invoiced_customer_id.id),
                                                                 ('partner_id', '=', partner_rs.id)], limit=1)
            if not partner_verif and self.invoiced_customer_id != self.partner_id:
                res['warning'] = {'title': _('Warning'), 'message': _('The selected invoiced customer is not in the invoiced list of the partner'
                                                                      ' who orders')}
                self.invoiced_customer_id = False
                self.invoicing_address_id = False
                self.tva_number = ''
                return res
            
            invoiced_customer = self.invoiced_customer_id
            res2 = self.onchange_invoiced_customer_id(invoiced_customer)
            for k,v in res2.iteritems():
                self[k] = v
        
        return res
    
    
    def onchange_delivered_customer_id(self, delivered_customer):
        """
            Récupération des infos du client livré
        """
        res = {}
        res_partner_obj = self.env['res.partner']
        if isinstance(delivered_customer, int):
            delivered_customer = res_partner_obj.browse(delivered_customer)
            
        if delivered_customer:
            #On commence par récupérer l'adresse du partenaire
            #On récupère le client chez lequel on va prendre les informations: le partenaire sélectionné,
            #le partenaire parent du contact sélectionné ou rien (si c'est un contact, les infos n'existent pas)
            if not delivered_customer.is_company and delivered_customer.parent_id:
                delivered_customer = delivered_customer.parent_id
                
            infos_dict = delivered_customer.get_partner_address({'delivery': True}, return_id=True)
            res['delivered_address_id'] = infos_dict.get('delivery_address', False)
            res['sale_account_system_id'] = delivered_customer.property_account_position_id.id
            res['delivered_contact_id'] = delivered_customer.sale_delivery_contact_id and delivered_customer.sale_delivery_contact_id.id or False
            
            res.update(delivered_customer.get_sale_transport_fields(return_id=True))
        
        return res
    
    
    @api.onchange('delivered_customer_id')
    def _onchange_delivered_customer_id(self):
        """
            Au changement de client, on va récupérer l'adresse d'expédition, le délai de transport,
            le régime fiscal et les informations de l'onglet livraison
        """
        res = {}
        if self.delivered_customer_id:
            if self.delivered_customer_id.is_company and self.delivered_customer_id.state in ['prospect', 'stopped']:
                res['warning'] = {'title': _('Warning'), 'message': _('The selected delivered customer is not qualified to be charged, '
                                                                      'his state must be "qualified"')}
                self.delivered_customer_id = False
                self.delivered_address_id = False
                self.transport_delay = 0
                self.sale_account_system_id = False
                self.sale_incoterm_id = False
                self.sale_invoice_postage = False
                self.sale_threshold = 0
                self.sale_forwarding_agent_id = False
                return res
            
            partner_rs = self.partner_id
            #Si le client est un contact, on récupère le client commandeur qui lui est lié
            if not partner_rs.is_company and partner_rs.parent_id:
                partner_rs = partner_rs.parent_id
            
            partner_verif = self.env['res.partner.type'].search([('partner_type', '=', 'can_be_delivered'), 
                                                                 ('partner_type_id', '=', self.delivered_customer_id.id),
                                                                 ('partner_id', '=', partner_rs.id)], limit=1)
            if not partner_verif and self.delivered_customer_id != self.partner_id:
                res['warning'] = {'title': _('Warning'), 'message': _('The selected delivered customer is not in the delivered list of the partner'
                                                                      ' who orders')}
                self.delivered_customer_id = False
                self.delivered_address_id = False
                self.transport_delay = 0
                self.sale_account_system_id = False
                self.sale_incoterm_id = False
                self.sale_invoice_postage = False
                self.sale_threshold = 0
                self.sale_forwarding_agent_id = False
                return res
            
            delivered_customer = self.delivered_customer_id
            res2 = self.onchange_delivered_customer_id(delivered_customer)
            for k,v in res2.iteritems():
                self[k] = v
        
        return res
    
    
    def onchange_delivered_country_id(self, invoiced_customer, delivered_country):
        """
            Récupération des infos de TVA
        """
        res = {}
        res_partner_obj = self.env['res.partner']
        if isinstance(invoiced_customer, int):
            invoiced_customer = res_partner_obj.browse(invoiced_customer)
        
        if self.delivered_region_id and self.delivered_region_id.country_id != delivered_country:
            res['delivered_region_id'] = False
             
        if invoiced_customer:
            tva_obj = self.env['country.tva']
            if invoiced_customer.can_be_charged:
                #On récupère le client chez lequel on va prendre les informations: le partenaire sélectionné,
                #le partenaire parent du contact sélectionné ou rien (si c'est un contact, les infos n'existent pas)
                if invoiced_customer.is_company:
                    invoiced_customer = invoiced_customer
                    res['invoicing_address_id'] = invoiced_customer.address_id
                elif invoiced_customer.parent_id:
                    if invoiced_customer.company_address:
                        res['invoicing_address_id'] = invoiced_customer.parent_id.address_id.id
                    else:
                        res['invoicing_address_id'] = invoiced_customer.address_id.id
                        
                    invoiced_customer = invoiced_customer.parent_id
                else:
                    invoiced_customer = False
                
                #On récupère le numéro de TVA
                find_tva = False
                if delivered_country and invoiced_customer:
                    #Si on a un pays livré on recherche le numéro de TVA de ce pays chez le partenaire
                    tva_ids = tva_obj.search([('partner_id', '=', invoiced_customer.id), 
                                              ('country_id', '=', delivered_country.id)], limit=1)
                    if tva_ids:
                        res['tva_number'] = tva_ids[0].name
                        find_tva = True
                        
                if not delivered_country or not find_tva:
                    #Sinon on recherche le numéro de TVA du pays de l'adresse du partenaire
                    if res.get('invoicing_address_id', False):
                        invoicing_address = res['invoicing_address_id']
                        if isinstance(invoicing_address, int):
                            invoicing_address = self.env['address'].browse(invoicing_address)
                            
                        if invoicing_address.country_id:
                            tva_ids = tva_obj.search([('partner_id', '=', invoiced_customer.id), 
                                                      ('country_id', '=', invoicing_address.country_id.id)], limit=1)
                            if tva_ids:
                                res['tva_number'] = tva_ids[0].name
                                find_tva = True
                
                #Si on a trouvé aucun numéro TVA, on vide le champ
                if not find_tva:
                    res['tva_number'] = ''
        
        return res
            
    
    @api.onchange('invoiced_customer_id', 'delivered_country_id')
    def _onchange_delivered_country_id(self):
        """
            Au changement de pays, on va récupérer le numéro TVA correspondant
        """
        res = {}
        res2 = self.onchange_delivered_country_id(self.invoiced_customer_id, self.delivered_country_id)
        for k,v in res2.iteritems():
            self[k] = v
        
        return res
            
    
    def onchange_delivered_address_id(self, delivered_address):
        """
            Récupération des infos de l'adresse
        """
        res = {}
        address_obj = self.env['address']
        if isinstance(delivered_address, int):
            delivered_address = address_obj.browse(delivered_address)
        
        if delivered_address:
            res['delivered_name'] = delivered_address.name
            res['delivered_street'] = delivered_address.street
            res['delivered_street2'] = delivered_address.street2
            res['delivered_street3'] = delivered_address.street3
            res['delivered_zip'] = delivered_address.zip
            res['delivered_city'] = delivered_address.city
            res['delivered_region_id'] = delivered_address.region_id and delivered_address.region_id.id or False
            res['delivered_country_id'] = delivered_address.country_id.id
        else:
            res['delivered_name'] = ''
            res['delivered_street'] = ''
            res['delivered_street2'] = ''
            res['delivered_street3'] = ''
            res['delivered_zip'] = ''
            res['delivered_city'] = ''
            res['delivered_region_id'] = False
            res['delivered_country_id'] = False
        
        return res
    
    
    @api.onchange('delivered_address_id')
    def _onchange_delivered_address_id(self):
        """
            Au changement d'adresse d'expédition, on récupère tous les détails de l'adresse
        """
        res = {}
        res2 = self.onchange_delivered_address_id(self.delivered_address_id)
        for k,v in res2.iteritems():
            self[k] = v
        
        return res
            
    
    def onchange_paid_customer_id(self, paid_customer):
        """
            Récupération des infos du client payeur
        """
        res = {}
        if isinstance(paid_customer, int):
            paid_customer = self.env['res.partner'].browse(paid_customer)
            
        if paid_customer.is_company:
            pay_customer = paid_customer
        elif paid_customer.parent_id:
            pay_customer = paid_customer.parent_id
        else:
            pay_customer = False
        
        if pay_customer:
            res['payment_id'] = pay_customer.sale_payment_method_id.id
            res['payment_term_id'] = pay_customer.property_payment_term_id.id
            res['invoicing_method_id'] = pay_customer.sale_invoicing_method_id.id
            res['discount'] = pay_customer.sale_discount_management
            res['discount_value'] = pay_customer.sale_discount_value
            res['max_delay'] = pay_customer.sale_max_delay
        else:
            res['payment_id'] = False
            res['payment_term_id'] = False
            res['invoicing_method_id'] = False
            res['discount'] = False
            res['discount_value'] = 0
            res['max_delay'] = 0
        
        return res
            
    
    @api.onchange('paid_customer_id')
    def _onchange_paid_customer_id(self):
        """
            Au changement du client payeur, on va remplir toutes les informations concernant
            le paiement dans l'onglet de comptabilité 
        """
        res = {}
        if self.paid_customer_id:
            if self.paid_customer_id.is_company and self.paid_customer_id.state in ['prospect', 'stopped']:
                res['warning'] = {'title': _('Warning'), 'message': _('The Customer selected to pay the order is not qualified to pay '
                                                                      'his state must be "qualified"')}
                self.paid_customer_id = False
                self.payment_id = False
                self.payment_term_id = False
                self.discount = False
                self.discount_value = 0
                self.max_delay = 0
                return res
            
            partner_rs = self.partner_id
            # Si le client est un contact, on récupère le client commandeur qui lui est lié
            if not partner_rs.is_company and partner_rs.parent_id:
                partner_rs = partner_rs.parent_id
            
            partner_verif = self.env['res.partner.type'].search([('partner_type', '=', 'can_paid'), 
                                                                 ('partner_type_id', '=', self.paid_customer_id.id),
                                                                 ('partner_id', '=', partner_rs.id)], limit=1)
            if not partner_verif and self.paid_customer_id != self.partner_id:
                res['warning'] = {'title': _('Warning'), 'message': _('The Customer selected to pay the order is not in the '
                                                                      'paid list of the partner who orders')}
                self.paid_customer_id = False
                self.payment_id = False
                self.payment_term_id = False
                self.discount = False
                self.discount_value = 0
                self.max_delay = 0
                return res
            
            res2 = self.onchange_paid_customer_id(self.paid_customer_id)
            for k,v in res2.iteritems():
                self[k] = v
        
        return res
    
    
    def onchange_location_id(self, location_rs):
        """
        """
        if location_rs:
            res = {'warehouse_id': location_rs.warehouse_id.id}
        else:
            res = {'warehouse_id': False}

        return res
            
    
    @api.onchange('location_id')
    def _onchange_location_id(self):
        """
            Au changement d'emplacement, changement de l'entrepot
        """
        res = self.onchange_location_id(self.location_id)
        for k, v in res.iteritems():
            self[k] = v
            
    
    def onchange_warehouse_id(self, warehouse_rs):
        """
        """
        if warehouse_rs:
            res = {'location_id': warehouse_rs.delivery_location_id.id}
        else:
            res = {'location_id': False}

        return res
            
    
    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        """
            Au changement d'entrepôt, changement de l'emplacement de livraison
        """
        res = self.onchange_warehouse_id(self.warehouse_id)
        for k, v in res.iteritems():
            self[k] = v
        
            
    @api.onchange('order_address_id')
    def _onchange_order_address_id(self):
        """
            Au changement de l'adresse de commande, si on a pas d'adresse livrée ou d'adresse
            facturée, on va les remplir avec l'adresse de commande 
        """
        res = {}
        if self.order_address_id:
            if not self.invoicing_address_id:
                self.invoicing_address_id = self.order_address_id.id
            
            if not self.delivered_address_id:
                self.delivered_address_id = self.order_address_id.id
        
        return res
     
     
#     @api.onchange('sale_account_invoice_trigger')
#     def _onchange_sale_account_invoice_trigger(self):
#         """
#             Si on passe le mode de déclenchement à la commande, on sélectionne la facturation sur 
#             quantités commandées
#             Si on passe le mode de déclenchement à la livraison, on sélectionne la facturation sur 
#             quantités livrées
#         """
#         if self.sale_account_invoice_trigger in ['manual','postpaid']:
#             self.sale_account_invoiced_on = 'order'
#         elif self.sale_account_invoice_trigger == 'picking' and self.payment_type != 'after_invoicing':
#             self.sale_account_invoiced_on = 'delivery'
#         
#     
#     @api.onchange('sale_account_invoiced_on', 'payment_type')
#     def _onchange_sale_account_invoiced_on(self):
#         """
#             On modifie la méthode de déclenchement de facturation en fonction du type de paiement
#             et du type de facturation (qtés livrées ou commandées)
#         """
#         if self.sale_account_invoiced_on == 'delivery':
#             self.sale_account_invoice_trigger = 'picking'
#         elif self.sale_account_invoiced_on == 'order' and self.payment_type != 'after_invoicing' and self.sale_account_invoice_trigger != 'manual':
#             self.sale_account_invoice_trigger = 'postpaid'


    @api.onchange('order_line_ids')
    def _onchange_order_line_ids(self):
        """
            On stocke la valeur de la plus haute séquence afin d'envoyer par défaut la bonne séquence 
            aux lignes de vente
            On calcule les taxes des lignes
        """
        #Récupération de la séquence
        res = {}
        seq_list = []
        for line in self.order_line_ids:
            seq_list.append(line.sequence)
        
        max_sequence = max(seq_list or [0])
        self.max_sequence = max_sequence + 10
        #Calcul des taxes
        taxes_grouped = self.get_taxes_values()
        tax_lines = self.tax_line_ids.browse([])
        for tax in taxes_grouped.values():
            tax_lines += tax_lines.new(tax)
            
        self.tax_line_ids = tax_lines
        return res
    
    
    def check_renting_end_date(self, nb_days=1):
        """
            Fonction appelée par un cron, on récupère toutes les ventes non annulées
            qui arrivent à nb_days jours de la date de fin de location de la vente
        """
        action_obj = self.env['calendar.event']
        data_obj = self.env['ir.model.data']
        today = fields.Date.today()
        compare_date = fields.Date.to_string((fields.Date.from_string(today) + relativedelta(days=nb_days)))
        sale_rcs = self.search([('state', '!=', 'cancel'), 
                                ('renting_end_date', '=', compare_date),
                                ('type', '=', 'renting')])
        state_action_rs = self.env['action.state'].search([('to_do_state', '=', True)], limit=1)
        if not state_action_rs:
            state_action_rs = self.env['action.state'].search([], limit=1)
            
        for sale in sale_rcs:
            object_model, action_type_id = data_obj.get_object_reference('base_openprod', 'simple_action_type_action')
            vals = {
                   'name': _('Renting end for %s / %s'%(sale.name, sale.partner_id.name)),
                   'description': _('The renting end date is near'),
                   'start_datetime': today,
                   'stop_datetime': today,
                   'user_id': self.env.user.id,
                   'affected_user_id': sale.seller_id and sale.seller_id.id or self.env.user.id,
                   'state_id': state_action_rs.id,
                   'sale_id': sale.id,
                   'type_id': action_type_id,
                   }
            action_obj.create(vals)
            
        return True
    
    
    def compute_date_delay(self, date, delay):
        """
            Fonction permettant, à partir d'une date de début, d'obtenir la date de début 
            moins le délai passé en paramètres
            :type self: sale.order
            :param date: Date de début
            :type date: char format date
            :param delay: délai à soustraire à la date
            :type delay: integer
            :return: Date de début moins le délai passé en paramètres
            :rtype: char format date
        """
        if date and delay:
            date_line = fields.Date.from_string(date)
            res = date_line - timedelta(delay)
        elif date: 
            res = date
        else:
            res = False
            
        return res
    
    
    def compute_add_date_delay(self, date, delay):
        """
            Fonction permettant, à partir d'une date de début, d'obtenir la date de début 
            plus le délai passé en paramètres
            :type self: sale.order
            :param date: Date de début
            :type date: char format date
            :param delay: délai à ajouter à la date
            :type delay: integer
            :return: Date de début plus le délai passé en paramètres
            :rtype: char format date
        """
        if date and delay:
            date_line = fields.Date.from_string(date)
            res = date_line + timedelta(delay)
        elif date: 
            res = date
        else:
            res = False
            
        return res
    
    
    @api.one
    def action_generate_payment(self):
        return self.generate_payment('before_validation')


    def generate_payment(self, payment_type):
        """
            Fonction permettant de créer le paiement lié à la vente
        """
        # S'il n'y a pas de lignes de vente on envoie un message d'erreur
        if not self.order_line_ids:
            raise ValidationError(_('There is no lines on your sale!'))
        
        # Commenté car on peut avoir plusieurs paiements en avances pour une vente
        #S'il y a déjà un paiement non annulé lié à la vente, on ne refait pas de paiement
#         for payment in self.payment_ids:
#             if payment.state != 'cancel':
#                 raise ValidationError(_('There is already a payment for this sale!'))
            
        # Récuperation de toutes les valeurs du paiement
        journal_obj = self.env['account.journal']
        payment_rate = 1
        today = fields.Date.today()
        period_rs = self.env['account.period'].find(today)
        currency_rs = self.currency_id or False
        # Recherche du journal par défaut du paiement. S'il n'y en a pas on prend le premier trouvé
        journal_rs = journal_obj.search([('is_default', '=', True), ('type', 'in', ['cash', 'bank'])], limit=1)
        if not journal_rs:
            journal_rs = journal_obj.search([('type', 'in', ['cash', 'bank'])], limit=1)
        
        payment_currency_rs = journal_rs and journal_rs.currency or journal_rs.company_id.currency_id
        context2 = {'date': today}
        context2.update(self.env.context)
        if journal_rs and period_rs and currency_rs and payment_currency_rs:
            currency_rate = payment_currency_rs.rate
            if currency_rate != 0:
                payment_rate = currency_rs.rate / currency_rate
            
            total_amount = self.invoicing_method_id.get_total_amount('payment', payment_type, self.total_amount)
            if payment_currency_rs != currency_rs:
                total_amount = currency_rs.with_context(context2).compute(total_amount, payment_currency_rs)
            else:
                total_amount = total_amount
            
            account_partner_id = self.paid_customer_id.property_account_receivable_id and self.paid_customer_id.property_account_receivable_id.id or False
            vals = {'partner_id': self.paid_customer_id.id,
                    'name': self.name,
                    'account_partner_id': account_partner_id,
                    'amount': total_amount,
                    'journal_id': journal_rs.id,
                    'date': today,
                    'period_id': period_rs.id,
                    'payment_rate_currency_id': currency_rs.id,
                    'company_id': self.company_id.id,
                    'payment_rate': payment_rate,
                    'payment_option': 'without_writeoff',
                    'currency_id': payment_currency_rs.id,
                    'account_id': journal_rs.default_debit_account_id.id,
                    'sale_id': self.id,
                    'type': 'receipt'}
            
            self.env['account.voucher'].create(vals)
            # On passe la vente en attente si elle est en brouillon
            if self.state == 'draft':
                context2['from_payment'] = True
                self.with_context(context2).action_waiting_sale()
            
        return True
    

    def change_invoice_button_display(self, display=True):
        """
            Fonction permettant de cacher le bouton de génération de facture
        """
        self.write({'manual_hide_invoice_button': not bool(display)})
    
    
    @api.multi
    def generate_invoice_button(self):
        return self.generate_invoice(invoice_trigger='manual')
    
    
    def more_other_data_invoice(self):
        return {}
        
    @api.one
    def generate_invoice(self, return_id_invoice=False, invoice_trigger=False):
        """
            Fonction permettant de créer la facture liée à la vente
        """
        if self.order_line_ids:
            context2 = {'force_invoice_price': True}
            context2.update(self.env.context)
            invoice_line_obj = self.env['account.invoice.line']
            invoice_obj = self.env['account.invoice']
            invoiced_partner = self.invoiced_customer_id
            payment_term_id = self.payment_term_id.id
            if invoice_trigger:
                balance = (invoice_trigger == self.sale_invoice_balance_trigger)
                invoicing_method_line_rs = self.env['account.invoicing.method.line'].search([('invoice_trigger', '=', invoice_trigger), 
                                                                                             ('invoicing_method_id', '=', self.invoicing_method_id.id)], limit=1)
                if invoicing_method_line_rs and invoicing_method_line_rs.payment_term_id:
                    payment_term_id = invoicing_method_line_rs.payment_term_id.id
                    
            else:
                balance = True
            
            # Desactivation du bouton de facturation manuelle si on lance une facture balance ou la facturation manuelle
            if balance or invoice_trigger == 'manual':
                self.write({'show_invoice_button': False})
                
            other_data = {'fiscal_position_id': self.sale_account_system_id.id,
                          'currency_id': self.currency_id.id,
                          'company_id': self.company_id.id,
                          'delivery_partner_id': self.delivered_customer_id.id,
                          'partner_order_id': self.partner_id.id,
                          'lock_invoice': self.locked_invoice,
                          'group_invoices': self.group_invoices,
                          'invoices_period': self.invoices_period,
                          'declaration_deb': self.subject_deb,
                          'tva_number': self.tva_number,
                          'note_invoice_intern': self.inter_note,
                          'note_invoice_header': self.invoice_note,
                          'payment_term_id': payment_term_id,
                          'discount_management': self.discount,
                          'discount_value': self.discount_value,
                          'max_delay': self.max_delay,
                          'invoice_trigger': invoice_trigger,
                          'payment_method_id': self.payment_id.id,
                          'paid_by_id': self.paid_customer_id.id,
                          'contact_ids': [(4, contact_id) for contact_id in invoiced_partner.invoicing_contact_ids.ids],
                          'communication_method': invoiced_partner.accounting_communication_method,
                          'auto_anticipated': not balance,
                          'origin': self.name_get()[0][1]}
            
            other_data.update(self.more_other_data_invoice())
            invoice_id = self.env['account.invoice'].create_invoice(invoiced_partner, self.invoicing_address_id.id, 'out_invoice', other_data)
            # Gestion de la facturation des lignes de vente
                # Gestion des facture anticipées en pourcentage
            invoicing_method_percentage = self.invoicing_method_id.get_invoice_percentage(invoice_trigger)
            if self.type == 'sav':
                invoicing_method_percentage = 1.0
                
            if invoicing_method_percentage:
                for line in self.order_line_ids:
                    taxes_ids = [x.id for x in line.taxes_ids]
                    other_data = {'sec_uom_qty': line.sec_uom_qty * invoicing_method_percentage,
                                  'sec_uom_id': line.sec_uom_id.id,
                                  'uom_qty': line.uom_qty * invoicing_method_percentage,
                                  'uom_id': line.uom_id.id,
                                  'quantity': line.uoi_qty * invoicing_method_percentage,
                                  'uoi_id': line.uoi_id.id,
                                  'price_unit': line.price_unit,
                                  'invoice_line_tax_ids': [(6, 0, taxes_ids)],
                                  'name': line.name,
                                  'section_id': line.section_id.id,
                                  'customer_product_name': line.customer_product_name,
                                  'customer_product_code': line.customer_product_code,
                                  'sale_order_line_id': line.id,
                                  'note_invoice_header': line.invoice_printed_note}
                    invoice_line_obj.with_context(context2).create_invoice_line(invoice_id.id, line.product_id, True, other_data)
            
            # Gestion des facture anticipées en montant fixe
            if self.order_line_ids:
                other_data = {'sale_order_line_id': self.order_line_ids[0].id} 
            else:
                other_data = None
                
            for fixed_amount, product_id in self.invoicing_method_id.get_invoice_fixed_amount(invoice_trigger):
                invoice_line_obj.with_context(context2).create_invoice_line(invoice_id.id, product_id, from_invoice=True, other_data=other_data, forced_price_unit=fixed_amount, forced_uoi_qty=1.0)
                

            invoice_id._onchange_invoice_line_ids()
            # Gestion des factures anticipées
            if self.remaining_advanced_amount:
                invoice_obj.generate_anticipated_invoice_line('sale', invoice_id, self.remaining_advanced_amount, self)
            
            # 2ème boucle car doit etre lancé apres generate_anticipated_invoice_line
            for line in self.order_line_ids:
                if balance:
                    invoice_obj.generate_auto_anticipated_invoice_line('sale', invoice_id, line)
                
            if return_id_invoice:
                return invoice_id
            
        else:
            raise ValidationError(_('You can\'t create an invoice if there is no lines in your sale'))
        
        return True
    
    
    @api.one
    def action_generate_picking(self):
        """
            Fonction permettant de générer un picking et des moves
        """
        if not self.type or self.type != 'sav':
            move_obj = self.env['stock.move']
            picking_obj = self.env['stock.picking']
            # Récuperation des valeurs de base de la vente
            picking_id = False
            # État de facturation
            if self.sale_invoice_trigger_picking:
                state = '2binvoiced'
            else:
                state = 'none'
    
            # Type du picking
            move_and_picking_type = self.env.context.get('force_sale_picking_type', 'out')
            
    #         if self.block_picking_payment or self.block_picking:
    #             payment_lock = True
    #         else:
    #             payment_lock = False
            
            currency_id = self.currency_id.id
            other_data = {'sale_id': self.id,
                          'is_partial': self.partial_delivery,
                          'manage_scrap': self.allowed_rest,
                          'internal_note': self.inter_note,
                          'printed_note': self.delivery_note,
                          'address_id': self.delivered_address_id.id,
                          'incoterm_id': self.sale_incoterm_id.id,
                          'forwarding_agent_id': self.sale_forwarding_agent_id.id,
                          'threshold': self.sale_threshold,
                          'invoice_postage': self.sale_invoice_postage,
                          'delivery_delay': self.transport_delay,
                          'address_name': self.delivered_name,
                          'street': self.delivered_street,
                          'street2': self.delivered_street2,
                          'street3': self.delivered_street3,
                          'zip': self.delivered_zip,
                          'city': self.delivered_city,
                          'region_id': self.delivered_region_id and self.delivered_region_id.id or False,
                          'country_id': self.delivered_country_id.id,
                          'payment_lock': (self.block_picking_payment and not self.check_paid),
                          'lock': self.block_picking,
                          'invoice_state': state,
                          'forecast': True,
                          'address_contact_id': self.delivered_contact_id and self.delivered_contact_id.id or False,
                          'origin': self.ref_order,}
            # Si la case 'Faire autant de BL que de date de livraison' n'est pas cochée, création d'un picking et des moves associés aux lignes de ventes
            if not self.delivery_note_and_date:
                picking_id = picking_obj.create_picking(type=move_and_picking_type, partner=self.delivered_customer_id, product_qty_uom={}, other_data=other_data)
                for line in self.order_line_ids:
                    old_move_rs = move_obj.search([('sale_line_id', '=', line.id), 
                                                   ('history_id', '!=', False), 
                                                   ('product_id', '=', line.product_id.id)], limit=1)
                    if old_move_rs:
                        history_id = old_move_rs.read(['history_id'], load='_classic_write')[0]['history_id']
                    else:
                        history_id = self.env['stock.move.history'].create({'product_id': line.product_id.id}).id
                        
                    if (line.product_id.type != 'service') or (line.product_id.type == 'service' and line.product_id.manage_service_delivery):
                        customer_info = line.product_id.get_cinfo(partner_id=line.sale_order_id.partner_id.id, property_ids=line.property_ids.ids)
                        move_date = line.confirmed_departure_date and line.confirmed_departure_date or line.departure_date
                        move_other_data = {'sequence': line.sequence,
                                           'sale_line_id': line.id,
                                           'name': line.name,
                                           'uom_id': line.uom_id.id,
                                           'sec_uom_qty': line.sec_uom_qty,
                                           'sec_uom_id': line.sec_uom_id.id,
                                           'uoi_qty': line.uoi_qty,
                                           'uoi_id': line.uoi_id.id,
                                           'initial_uom_qty': line.uom_qty,
                                           'note': line.internal_note,
                                           'partner_price': line.price_unit,
                                           'factor': line.factor,
                                           'divisor': line.divisor,
                                           'cinfo_id': customer_info and customer_info.id or False,
                                           'currency_id': currency_id,
                                           'trigger_supply': line.supply_method,
                                           'origin': line.name_get()[0][1],
                                           'note': line.delivery_printed_note,
                                           'history_id': history_id,
                                           }
                        if line.product_id.type == 'service' and line.product_id.manage_service_delivery:
                            if not self.warehouse_id.service_location_id:
                                raise ValidationError('There is no service location in your company')
                             
                            move_other_data['location_id'] = self.warehouse_id.service_location_id.id
                            
                        if move_and_picking_type == 'in':
                            src_location = dst_location = self.warehouse_id.customer_location_id.id
                            dst_location = False
                        else:
                            src_location = line.sale_order_id and line.sale_order_id.location_id and line.sale_order_id.location_id.id or False
                            #Si le partenaire a un emplacement client défini on récupère celui-ci sinon on récupère l'emplacement client de la société
                            if line.sale_order_id.delivered_customer_id and line.sale_order_id.delivered_customer_id.customer_location_id:
                                dst_location = line.sale_order_id.delivered_customer_id.customer_location_id.id
                            else:
                                dst_location = self.warehouse_id.customer_location_id and self.warehouse_id.customer_location_id.id or False
                            
                        move_obj.create_move(line.product_id, qty=line.uom_qty, type=move_and_picking_type, date=move_date, other_data=move_other_data, 
                                             picking=picking_id, src_location=src_location, dst_location=dst_location)
                
                picking_id.wkf_waiting()
            #Si on a coché la case 'Faire autant de BL que de date de livraison', on crée autant de picking
            #qu'il y a de date confirmée dans les lignes de ventes
            else:
                date_line = {}
                for line in self.order_line_ids:
                    move_date = line.confirmed_departure_date and line.confirmed_departure_date or line.departure_date
                    if move_date in date_line:
                        date_line[move_date].append(line)
                    else:
                        date_line[move_date] = [line]
                    
                for date, sale_lines in date_line.iteritems():
                    for sale_line in sale_lines:
                        old_move_rs = move_obj.search([('sale_line_id', '=', sale_line.id), ('history_id', '!=', False)], limit=1)
                        if old_move_rs:
                            history_id = old_move_rs.read(['history_id'], load='_classic_write')[0]['history_id']
                        else:
                            history_id = self.env['stock.move.history'].create({'product_id': sale_line.product_id.id}).id
                            
                        if (sale_line.product_id.type != 'service') or (sale_line.product_id.type == 'service' and \
                                                               sale_line.product_id.manage_service_delivery):
                            picking_id = picking_obj.create_picking(type=move_and_picking_type, partner=self.delivered_customer_id, 
                                                                 product_qty_uom={}, other_data=other_data)
                            customer_info = sale_line.product_id.get_cinfo(partner_id=sale_line.sale_order_id.partner_id.id, 
                                                                  property_ids=sale_line.property_ids.ids)
                            move_other_data = {'sequence': line.sequence,
                                               'sale_line_id': sale_line.id,
                                               'name': sale_line.name,
                                               'uom_id': sale_line.uom_id.id,
                                               'sec_uom_qty': sale_line.sec_uom_qty,
                                               'sec_uom_id': sale_line.sec_uom_id.id,
                                               'uoi_qty': sale_line.uoi_qty,
                                               'uoi_id': sale_line.uoi_id.id,
                                               'initial_uom_qty': sale_line.uom_qty,
                                               'note': sale_line.internal_note,
                                               'partner_price': sale_line.price_unit,
                                               'factor': line.factor,
                                               'divisor': line.divisor,
                                               'cinfo_id': customer_info and customer_info.id or False,
                                               'currency_id': currency_id,
                                               'note': line.delivery_printed_note,
                                               'history_id': history_id}
                            
                            if line.product_id.type == 'service' and line.product_id.manage_service_delivery:
                                if not self.warehouse_id.service_location_id:
                                    raise ValidationError('There is no service location in your company')
                                 
                                move_other_data['location_id'] = self.warehouse_id.service_location_id.id
                                
                            if move_and_picking_type == 'in':
                                src_location = dst_location = self.warehouse_id.customer_location_id.id
                                dst_location = False
                            else:
                                src_location = line.sale_order_id and line.sale_order_id.location_id and line.sale_order_id.location_id.id or False
                                # Si le partenaire a un emplacement client défini on récupère celui-ci sinon on récupère l'emplacement client de la société
                                if line.sale_order_id.delivered_customer_id and line.sale_order_id.delivered_customer_id.customer_location_id:
                                    dst_location = line.sale_order_id.delivered_customer_id.customer_location_id.id
                                else:
                                    dst_location = self.warehouse_id.customer_location_id and self.warehouse_id.customer_location_id.id or False
                                
                            move_obj.create_move(sale_line.product_id, qty=sale_line.uom_qty, type=move_and_picking_type, date=date, other_data=move_other_data,
                                                  picking=picking_id, src_location=src_location, dst_location=dst_location)
            
                    picking_id.wkf_waiting()
            
        return True
    
        
    def check_sale(self):
        """
            Vérifie que la vente peut être validée
        """
        # Vérification qu'il n'y a pas déjà un procurement avec une méthode d'appro différente
        self.check_procurement()
        # Récupération de la date minimum des lignes de la vente pour l'inscrire dans le champ "date demandée
        min_date_requested = self.env['sale.order.line'].search_read([('sale_order_id', '=', self.id)], ['requested_date'], limit=1, order='requested_date asc')
        if min_date_requested:
            self.write({'requested_date': fields.Date.from_string(min_date_requested[0]['requested_date'])})
            
        check_service = False
        # On vérifie qu'il n'y ai pas que des lignes de service non réceptionnés si la méthode de facturation est à la livraison
        if self.sale_invoice_trigger_picking:
            for line in self.order_line_ids:
                if line.product_id.type != 'service' or (line.product_id.type == 'service' and line.product_id.manage_service_delivery):
                    check_service = True
                    break
                
            if not check_service:
                raise ValidationError(_('You can\'t have a sale invoiced on the delivery if all the lines are linked to a service which not manage receipts'))
        
        # On vérifie qu'il y ai bien une date de reception de l'AR avant la validation si un AR est demandé
        if self.receipt_demand and not self.ar_send_date:
            raise ValidationError(_('You choose to have an AR but there is no AR send date (in the communication tab)'))
        
        return True
    
    
    def find_and_exec_done_sale(self):
        """
            Fonction permettant de trouver l'activité terminée de la vente et d'éxécuter son action
        """
        result = True
        object_model, object_id = self.env['ir.model.data'].get_object_reference('sale', 'act_done_sale')
        if object_model and object_model == 'workflow.activity':
            activity = self.env[object_model].browse(object_id)
            lines = activity.action
            if lines:
                assert lines, 'You used a NULL action in a workflow, use dummy node instead.'
                result = False
                for line in lines.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    if line == 'True':
                        result = True
                    elif line == 'False':
                        result = False
                    else:
                        result = eval('self.%s'%(line))
                     
            self.delete_workflow()
         
        return result
    
    
    @api.multi
    def action_waiting_sale(self):
        """
            Fonction permettant de passer la vente en attente
        """
        self.write({'quotation_date': fields.Date.today(),
                    'quotation_user_id': self.env.user.id,
                    'state': 'waiting'})
            
    
    def check_procurement(self):
        """
            Vérification qu'il n'y a pas déjà un procurement avec une méthode d'appro différente
        """
        proc_obj = self.env['procurement.order']
        for line in self.order_line_ids:
            proc_rs = proc_obj.search([('sol_id', '=', line.id), ('trigger_supply', '!=', line.supply_method)], limit=1)
            if proc_rs:
                raise ValidationError(_('You cannot validate the sale order because procurement %s have a different trigger supply method')%(proc_rs.name))
        
        return True
    
    
    @api.multi
    def action_progress_sale(self):
        """
            Fonction permettant de passer la vente en cours
        """
        self.check_sale()
        # Dans le cas où le mode de communication est à mail, on retourne le wizard de saisie du mail
        if self.delay_confirmation and self.sale_communication_method == 'email':
            res = self.env['mail.message'].action_send_mail(self.sale_contact_ids or self.partner_id, 'sale.order', 'confirmation', self.id)
        else:
            res = True
            self.signal_workflow('sale_validate')
            
        return res
    
    
    def action_done_sale(self):
        """
            Fonction permettant de passer la vente en terminé
            On annule tous les BL non done et les factures brouillon
            passés en paramètre
        """
        context2 = {}
        context2.update(self.env.context)
        context2['without_manage_state'] = True
        invoice_list = self.env['account.invoice']
        picking_list = self.env['stock.picking']
        for invoice_line in self.invoice_line_ids:
            if invoice_line.invoice_id.state == 'draft' and invoice_line.invoice_id not in invoice_list:
                invoice_list += invoice_line.invoice_id
        
        for picking in self.delivery_note_ids:
            if picking.state not in ('done', 'cancel') and picking not in picking_list:
                picking_list += picking
                
        invoice_list.with_context(context2).unlink()
        picking_list.wkf_cancel(manage_sale_purchase_state=False)
        picking_list.with_context(context2).unlink()
        for line in self.order_line_ids:
            if line.product_id.type == 'service' and not line.product_id.manage_service_delivery:
                line.write({
                            'delivered_qty': line.uom_qty,
                            'remaining_qty': 0,
                            })
        
        self.write({'state': 'done'}) 
        return True
    
    
    @api.one
    def action_cancel_sale(self):
        """
            Fonction permettant d'annuler la vente, ce qui supprime les picking et les
            factures non brouillon ou cancel, et repasse l'éventuelle commande ouverte terminée
            liée à "en cours"
        """
        invoices_list = []
        for line in self.order_line_ids:
            line.remaining_qty = 0
            
        for line in self.invoice_line_ids:
            if line.invoice_id.state not in ['draft', 'cancel']:
                raise ValidationError(_('There is an invoice linked to this sale which is not cancelled or draft'))
                 
            invoices_list.append(line.invoice_id)
        
        picking_list = []
        for picking in self.delivery_note_ids:
            if picking.state == 'done':
                raise ValidationError(_('There is a done picking linked to this sale'))
            
            picking_list.append(picking)
        
        self.write({'state':'cancel'})
        context2 = {}
        context2.update(self.env.context)
        context2['without_manage_state'] = True
        for invoice in list(set(invoices_list)): 
            invoice.with_context(context2).unlink()
            
        for picking in picking_list:
            picking.wkf_cancel(manage_sale_purchase_state=False)
            picking.move_ids.write({'not_usable': True})
        
        payment_list = self.env['account.voucher']
        for payment in self.payment_ids:
            if payment.state in ['draft', 'cancel']:
                payment_list += payment
        
        payment_list.unlink()  
        open_order = self.open_order_id
        if self.type == 'call' and open_order and open_order.state == 'done':
            sale_line_obj = self.env['sale.order.line']
            for line in self.order_line_ids:
                #On recherche les lignes de la commande ouverte correspondant
                open_line = sale_line_obj.search([('product_id', '=', line.product_id.id), ('sale_order_id', '=', open_order.id)])
                if open_line:
                    open_order.write({'state': 'draft'})
                    open_order.delete_workflow()
                    open_order.create_workflow()
                    open_order.signal_workflow('sale_validate')
                    break
            
        self.write({'quotation_date': False, 
                    'quotation_user_id': False, 
                    'confirmation_date': False, 
                    'confirmation_user_id': False})
            
        return True
    
    
    @api.one
    def action_draft_sale(self):
        """
            Fonction permettant de passer la vente en brouillon
            En cas de vente appelée, on repasse la vente ouverte à terminé si la quantité est la dernière
        """
        open_order = self.open_order_id
        if self.type == 'call' and open_order and open_order.state != 'done':
            uom_obj = self.env['product.uom']
            qty = 0
            sale_line_obj = self.env['sale.order.line']
            if self.order_line_ids:
                for line in self.order_line_ids:
                    #On recherche les lignes de la commande ouverte correspondant
                    open_order_lines = sale_line_obj.search([('product_id', '=', line.product_id.id), ('sale_order_id', '=', open_order.id)])
                    for open_line in open_order_lines:
                        line_qty = uom_obj._compute_qty(line.sec_uom_id.id, line.sec_uom_qty, open_line.sec_uom_id.id)
                        qty += (open_line.remaining_called_qty - line_qty) 
                
                if qty <= 0:
                    open_order.find_and_exec_done_sale()
                
        self.write({'state': 'draft', 'show_invoice_button': True})
        return True
    
    
    @api.multi
    def action_send_ar(self):
        self.write({'ar_send_date': fields.Datetime.now(), 'ar_user_id': self.env.user.id})
        return True
    
    
    @api.multi
    def action_change_sale(self):
        """
            Fonction permettant de changer la vente et de la passer en "waiting".
            On ne peut changer une vente que si elle n'est pas liée à un BL
            done, ou à une facture non draft ou non cancel
        """
        invoice_list = self.env['account.invoice']
        picking_list = self.env['stock.picking']
        payment_list = self.env['account.voucher']
        for sale in self:
            for line in self.order_line_ids:
                line.remaining_qty = 0
                
            for invoice_line in sale.invoice_line_ids:
                if invoice_line.invoice_id and invoice_line.invoice_id.state not in ['draft', 'cancel']:
                    raise ValidationError(_('You can\'t reset the sale because there is an opened or done linked invoice'))
                elif invoice_line.invoice_id not in invoice_list:
                    invoice_list += invoice_line.invoice_id
                    
            for picking in sale.delivery_note_ids:
                if picking.state == 'done':
                    raise ValidationError(_('You can\'t reset the sale because there is a done linked picking'))
                elif not picking in picking_list:
                    picking_list += picking
            
            for payment in sale.payment_ids:
                if payment.state in ['draft', 'cancel']:
                    payment_list += payment

        self.write({
                    'state': 'draft', 
                    'quotation_date': False, 
                    'quotation_user_id': False,
                    'confirmation_date': False,
                    'confirmation_user_id': False,
                    'waiting_delay': False,
                    'need_delay_validation': False,
                    })
        context2 = {}
        context2.update(self.env.context)
        context2['without_manage_state'] = True
        payment_list.unlink()
        picking_list.wkf_cancel(manage_sale_purchase_state=False)
        picking_list.with_context(context2).unlink()
        invoice_list.with_context(context2).unlink()
    
    @api.multi
    def show_sale_picking(self):
        """
            Fonction qui cherche et retourne les pickings de la vente
        """
        action_struc = {}
        action_dict = get_form_view(self, 'sale.sale_picking_action')
        sale_id = self.id
        if action_dict and action_dict.get('id') and action_dict.get('type'):
            action = self.env[action_dict['type']].browse(action_dict['id'])
            action_struc = action.read()
            action_struc[0]['context'] = {'sale_id': sale_id}
            action_struc = action_struc[0]
              
        return action_struc

    
    @api.multi
    def show_sale_invoice(self):
        """
            Fonction qui cherche et retourne les factures pour une vente
        """
        for sale in self:
            action_struc = {}
            invoice_line_list = []
            action_dict = get_form_view(self, 'sale.sale_invoice_action')
            for sale_line in sale.order_line_ids:
                invoice_line_list += [x.invoice_id.id for x in sale_line.invoice_line_ids]
                
            line_ids = list(set(invoice_line_list))
            if action_dict and action_dict.get('id') and action_dict.get('type'):
                action = self.env[action_dict['type']].browse(action_dict['id'])
                action_struc = action.read()
                action_struc[0]['context'] = {'invoice_ids': line_ids}
                action_struc = action_struc[0]
              
        return action_struc

    
    @api.multi
    def show_sale_action(self):
        """
            Fonction qui cherche et retourne les actions d'une vente
        """
        action_obj = self.env['calendar.event']
        for sale in self:
            action_struc = {}
            action_dict = get_form_view(self, 'base_openprod.see_actions')
            action_ids = action_obj.search([('sale_id', '=', sale.id)]).ids
            if action_dict and action_dict.get('id') and action_dict.get('type'):
                action = self.env[action_dict['type']].browse(action_dict['id'])
                action_struc = action.read()
                action_struc[0]['context'] = {'action_ids': action_ids}
                action_struc = action_struc[0]
              
        return action_struc
    
    
    @api.multi
    def change_sale_delivery_address(self):
        """
            Fonction qui appelle le wizard de modification des adresses
            à condition qu'aucun BL lié à la vente ne soit done
        """
        action_struc = {}
        action_dict = get_form_view(self, 'sale.action_change_delivery_address')
        for picking in self.delivery_note_ids:
            if picking.state == 'done':
                raise ValidationError(_('You can\'t change the delivery address because there is already a '
                                      'done delivery order linked to the sale'))
                
        if action_dict and action_dict.get('id') and action_dict.get('type'):
            action = self.env[action_dict['type']].browse(action_dict['id'])
            action_struc = action.read()
            action_struc[0]['context'] = {'sale_id': self.id}
            action_struc = action_struc[0]
              
        return action_struc
    
    
    @api.multi
    def change_sale_accounting_info(self):
        """
            Fonction qui appelle le wizard de modification des informations comptables
            à condition qu'aucune facture liée à la vente ne soit validée
        """
        action_struc = {}
        action_dict = get_form_view(self, 'sale.action_change_accounting_info')
        invoice_rs = [x.invoice_id for x in self.invoice_line_ids]
        invoice_rs = list(set(invoice_rs))
        for invoice in invoice_rs:
            if invoice.state != 'draft':
                raise ValidationError(_('You can\'t change the accounting information because there is already a '
                                      'validated invoice linked to the sale'))
                
        if action_dict and action_dict.get('id') and action_dict.get('type'):
            action = self.env[action_dict['type']].browse(action_dict['id'])
            action_struc = action.read()
            action_struc[0]['context'] = {'sale_id': self.id}
            action_struc = action_struc[0]
              
        return action_struc
    
    
    @api.multi
    def change_sale_note(self):
        """
            Fonction qui appelle le wizard de modification des notes
            à condition qu'aucune facture liée à la vente ne soit validée
        """
        action_struc = {}
        action_dict = get_form_view(self, 'sale.action_change_note')
        invoice_rs = [x.invoice_id for x in self.invoice_line_ids]
        invoice_rs = list(set(invoice_rs))
        for invoice in invoice_rs:
            if invoice.state != 'draft':
                raise ValidationError(_('You can\'t change the accounting information because there is already a '
                                      'validated invoice linked to the sale'))
                
        if action_dict and action_dict.get('id') and action_dict.get('type'):
            action = self.env[action_dict['type']].browse(action_dict['id'])
            action_struc = action.read()
            action_struc[0]['context'] = {'sale_id': self.id}
            action_struc = action_struc[0]
              
        return action_struc
    
    
    @api.multi
    def change_account_system(self):
        """
            Fonction qui appelle le wizard de modification du régime fiscal
            à condition qu'aucune facture liée à la vente ne soit validée
        """
        action_struc = {}
        action_dict = get_form_view(self, 'sale.action_change_account_system')
        invoice_rs = [x.invoice_id for x in self.invoice_line_ids]
        invoice_rs = list(set(invoice_rs))
        for invoice in invoice_rs:
            if invoice.state != 'draft':
                raise ValidationError(_('You can\'t change the accounting system because there is already a '
                                      'validated invoice linked to the sale'))
                
        if action_dict and action_dict.get('id') and action_dict.get('type'):
            action = self.env[action_dict['type']].browse(action_dict['id'])
            action_struc = action.read()
            action_struc[0]['context'] = {'sale_id': self.id}
            action_struc = action_struc[0]
              
        return action_struc
    
    
    def get_sale_action_vals(self):
        data_obj = self.env['ir.model.data']
        today = fields.Date.today()
        object_model, action_type_id = data_obj.get_object_reference('base_openprod', 'simple_action_type_action')
        state_action_rs = self.env['action.state'].search([('to_do_state', '=', True)], limit=1)
        if not state_action_rs:
            state_action_rs = self.env['action.state'].search([], limit=1)
            
        return {'name': _('Action for sale %s'%(self.name)),
                'description': _('Action for a sale'),
                'start_datetime': today,
                'stop_datetime': today,
                'user_id': self.env.user.id,
                'affected_user_id': self.env.user.id ,
                'state_id': state_action_rs.id,
                'sale_id': self.id,
                'type_id': action_type_id}
        
        
    @api.multi
    def create_sale_action(self):
        """
            Crée une action liée à la vente
        """
        action_obj = self.env['calendar.event']
        for sale in self:
            new_action_rcs = action_obj.create(sale.get_sale_action_vals())
            if new_action_rcs:
                action_struc = {}
                action_dict = get_form_view(self, 'base_openprod.action_see_one_action')
                if action_dict and action_dict.get('id') and action_dict.get('type'):
                    action = self.env[action_dict['type']].browse(action_dict['id'])
                    action_struc = action.read()
                    action_struc[0]['res_id'] = new_action_rcs.id
                    action_struc = action_struc[0]
                    return action_struc
            
        return True
    
    
    def create_sale(self, customer=False, so_line=None, date=False, other_data=None, forced_qty=False):
        """
            Création d'une vente
            :type self: sale.order
            :param customer: Client de la vente
            :type customer: recordset: res.partner
            :param so_line: Dictionnaire contenant autant de lignes de ventes que souhaitées
            :type so_line: dict {product: {'uom_qty': ..., 'uom_id': ..., 'sec_uom_qty': ..., 'sec_uom_id': ...}}
            :param date: Date par défaut des lignes de vente
            :type date: Date
            :param other_data: Dictionnaire permettant de passer d'autres champs ou de forcer des champs
            :type other_data: dict
            :param forced_qty: True si on souhaite entrer une qté inférieure à la qté minimale
            :type forced_qty: boolean
            :return: La vente créée
            :rtype: recordset sale.order
        """
        # Liste des champs obligatoires dans la vente
        required_fields = ['payment_term_id', 'payment_id', 'sale_account_system_id', 'sale_incoterm_id']
        vals = {}
        if not other_data:
            other_data = {}
        if customer:
            if isinstance(customer, int):
                customer = self.env['res.partner'].browse(customer)
            
            vals['partner_id'] = customer.id
        
        #On récupère les valeurs des onchanges
        #(informations du fournisseur, informations du fournisseur livré)
        vals.update(self.onchange_sale_customer(customer))
        if vals.get('invoiced_customer_id') and vals.get('delivered_customer_id') and vals.get('paid_customer_id'):
            vals.update(self.onchange_invoiced_customer_id(vals['invoiced_customer_id']))
            # Forçage du livré
            if 'forced_delivered_customer_id' in self.env.context:
                vals['delivered_customer_id'] = self.env.context['forced_delivered_customer_id']

            vals.update(self.onchange_delivered_customer_id(vals['delivered_customer_id']))
            vals.update(self.onchange_paid_customer_id(vals['paid_customer_id']))
            if vals.get('delivered_address_id'):
                vals.update(self.onchange_delivered_address_id(vals['delivered_address_id']))
                
            if vals.get('delivered_country_id'):
                if isinstance(vals['delivered_country_id'], int):
                    delivered_country = self.env['res.country'].browse(vals['delivered_country_id'])
                
                vals.update(self.onchange_delivered_country_id(vals['invoiced_customer_id'], 
                                                               delivered_country))
            
        #On récupère les valeurs forcées
        if other_data:
            vals.update(other_data)
            
        #Création de la vente
        vals = utils.transform_to_ids(self, vals)
        #On vérifie que les champs qui ne sont pas obligatoires lorsque le client est prospect
        #sont bien remplies
        for req_field in required_fields:
            if not vals.get(req_field):
                raise except_orm(_('Error'), _('The field %s is not filled in the customer form, you '
                                               'have to fill it if you want to make a sale whith this customer')%(req_field))
                
        sale = self.create(vals)
        if so_line:
            #Si le dictionnaire so_line est rempli, on va allé créer autant de ligne de vente
            #que de produits présents dans le dictionnaire
            so_line_obj = self.env['sale.order.line']
            for product, values in so_line.iteritems():
                #Si on a pas de valeur pour la date demandée, on passe la date de la fonction
                forced_price_unit = False
                if not 'requested_date' in values:
                    values['requested_date'] =  date
                    
                if 'forced_price_unit' in values:
                    forced_price_unit = values['forced_price_unit']
                    del values['forced_price_unit']
                
                so_line_rcs = so_line_obj.create_sale_order_line(sale, product, values, forced_qty=forced_qty, forced_price_unit=forced_price_unit)
                
        sale._onchange_order_line_ids()
        return sale
    
    
    @api.multi
    def get_taxes_values(self):
        tax_grouped = {}
        for line in self.order_line_ids:
            taxes = line.taxes_ids.compute_all(line.price_unit, self.currency_id, line.uoi_qty, line.product_id, self.partner_id)['taxes']
            for tax in taxes:
                val = {
                    'sale_id': self.id,
                    'name': tax['name'],
                    'tax_id': tax['id'],
                    'amount': tax['amount'],
                    'manual': False,
                    'sequence': tax['sequence'],
                    'account_id': tax['account_id'],
                }
                key = tax['id']
                if key not in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    
        return tax_grouped
    
    
    @api.multi
    def waiting_delay_button(self):
        self.write({'waiting_delay': True, 'need_delay_validation': True})
        return True
        
        
    @api.multi
    def conf_delay_button(self):
        self.check_sale()
        # Dans le cas où le mode de communication est à mail, on retourne le wizard de saisie du mail
        if self.delay_confirmation and self.sale_communication_method == 'email':
            res = self.env['mail.message'].action_send_mail(self.sale_contact_ids or self.partner_id, 'sale.order', 'confirmation', self.id)
        else: 
            res = self.signal_workflow('sale_conf_delay')        
            
        return res

        
    @api.multi
    def update_waiting_delay(self):
        for so in self:
            if not self.env['sale.order.line'].search([('sale_order_id', '=', so.id), ('scheduled_date', '=', False), ('delay_confirm', '=', True)], count=1):
                so.write({'need_delay_validation': False})
    
        return True
    
    
    @api.multi
    def wkf_waiting_delay(self):
        # Vérifie que la vente peut être validée
        self.check_sale()
        generate_picking = False
        # Vérification que la vente ait des lignes
        if not self.order_line_ids:
            raise ValidationError(_('You can\'t create a picking if there is no lines in your sale'))
        
        #On vérifie que le champ done_sale soit à False. Si ce n'est pas le cas, on ne crée pas de facture ou de picking
        #(utilisé par exemple lorsque la vente passe automatiquement de l'état "terminé" à l'état "en cours"
        if self.type != 'open' and not self.done_sale:
            self.write({'state': 'waiting_delay', 'done_sale': False})
            if self.sale_invoice_trigger_postpaid:
                self.generate_invoice(invoice_trigger='postpaid')
                
            # Si au moins une des lignes de vente n'a pas un produit de type service dont on ne gère pas la livraison, on génère le picking
            for line in self.order_line_ids:
                if (line.product_id.type != 'service') or (line.product_id.type == 'service' and line.product_id.manage_service_delivery):
                    generate_picking = True
                    break
            
            if generate_picking:
                self.action_generate_picking()
        
        return True
    
    
    @api.multi
    def wkf_waiting_conf_delay(self):
        return self.write({'state': 'waiting_conf_delay'})
    
    
    @api.multi
    def wkf_progress(self):
        picking_obj = self.env['stock.picking']
        amount_remaining_qty = 0
        for sale in self:
            # Date de départ confirmée dans les lignes de vente si elle n'est pas déjà saisie
            for line in sale.order_line_ids:
                amount_remaining_qty += line.uom_qty
                line.remaining_qty = line.uom_qty
                confirmed_departure_date = line.confirmed_departure_date
                if not confirmed_departure_date:
                    line.write({'confirmed_departure_date': line.departure_date})
                    confirmed_departure_date = line.departure_date
                
                # Date de départ confirmée dans les moves des lignes 
                line.stock_move_ids.write({'date_expected': confirmed_departure_date,
                                'date': confirmed_departure_date,
                                'priority_date': confirmed_departure_date})
     
            sale.write({'confirmation_date': fields.Datetime.now(),
                        'confirmation_user_id': self.env.user.id})
            # Récuperation de la liste des pickings de la vente pour les passer en non prévisionnel
            picking_rs = picking_obj.search([('sale_id', '=', sale.id), ('forecast', '=', True)])
            vals_write = {'forecast': False}
            if not self.block_picking_payment or self.check_paid:
                vals_write['payment_lock'] = False
                
            if not self.block_picking:
                vals_write['lock'] = False
                
            picking_rs.write(vals_write)
        
            if sale.need_picking_payment:
                sale.generate_payment('before_delivery')
                
        self.wkf_progress_state()
        return True
    
    
    @api.multi
    def wkf_progress_state(self):
        """
            Fonction permettant de passer la vente à l'état en cours, nécessaire avec les nouveaux workflows
            afin de passer une vente en cours sans recréer de picking ou de facture
        """
        self.write({'state': 'progress'})
        return True
    
    
    def pass_done_sale(self, unlink_invoice_ids=False, unlink_picking_ids=False):
        """
            Fonction qui permet de gérer automatiquement l'état 'terminé' d'une vente
                - Si la vente est en cours, que le mode de facturation n'est pas à la demande
                  et que tous les BL sont dones et les factures sont payées, on passe l'état à 'terminé'
                - Si la vente est terminée, que le mode de facturation n'est pas à la demande
                  et qu'il y a un BL non done ou une facture non payée, on repasse la vente en cours
            :type self: sale.order
            :param unlink_invoice_ids: Liste des factures qui vont être supprimées
            :type unlink_invoice_ids: List
            :param unlink_picking_ids: Liste des pickings qui vont être supprimées
            :type unlink_picking_ids: List
            :return: True
            :rtype: boolean
        """
        if self.state in ('progress', 'done'): 
            if self.sale_invoice_trigger_postpaid or self.sale_invoice_trigger_picking:
                done_sale = True
                if not unlink_invoice_ids:
                    unlink_invoice_ids = []
    
                if not unlink_picking_ids:
                    unlink_picking_ids = []
                    
                # Récupération de toutes les factures liées à la vente via les lignes de facture
                invoice_list = [invoice_line.invoice_id for invoice_line in self.invoice_line_ids]
                set_invoice_list = list(set(invoice_list))
                for invoice in set_invoice_list:
                    if invoice.id not in unlink_invoice_ids:
                        if invoice.state not in ('paid', 'cancel'):
                            done_sale = False
                            break
                    
                if done_sale:
                    #On regarde ensuite tous les pickings liés à la vente
                    #Si l'un n'est pas terminé ou annulé ou s'il est terminé mais
                    #doit être facturé, on ne passe pas l'état à 'terminé'
                    for picking in self.delivery_note_ids:
                        if picking.id not in unlink_picking_ids:
                            if picking.state not in ('done', 'cancel'):
                                done_sale = False
                                break
                            elif picking.state == 'done' and picking.invoice_state == '2binvoiced':
                                done_sale = False
                                break
                
                if done_sale and self.state == 'progress':
                    #Si la vente doit être passée en terminée, on recherche l'activité finale du workflow et 
                    #on lance ses méthodes
                    self.find_and_exec_done_sale()
                elif not done_sale and self.state == 'done':
                    self.write({'state': 'draft', 'done_sale': True})
                    self.delete_workflow()
                    self.create_workflow()
                    self.signal_workflow('sale_validate')
                            
        return True

    
    @api.model
    def create(self, vals):
        """
            On écrit le nom de la vente à partir de sa séquence en base
        """
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].get('sale.order') or '/'
        
        vals['creation_date'] = fields.Datetime.now()
        vals['creation_user_id'] = self.env.user.id
        sale = super(sale_order, self).create(vals)
        return sale
    
    
    @api.one
    def copy(self, default=None):
        """
            On vide les champs de date (confirmation, cotation...)
            ainsi que les quantités livrées et facturées
        """
        if not default:
            default = {}
        
        new_default = {
                       'ar_send_date': False,
                       'ar_user_id': False,
                       'quotation_date': False, 
                       'quotation_user_id': False,
                       'confirmation_date': False,
                       'confirmation_user_id': False,
                       'sale_invoiced_amount': 0,
                       }
        
        default.update(new_default)
        new_sale = super(sale_order, self).copy(default=default)
        context = self.env.context
        if not context.get('no_line_copy'):
            order_line_default = {
                                   'sale_order_id': new_sale.id,
                                   'delivered_qty' : 0,
                                   'remaining_qty' : 0,
                                   }
            self.order_line_ids.copy(order_line_default)
            
        return new_sale
    
    
    @api.multi
    def unlink(self):
        """
            On supprime les lignes de vente liées à la vente
            (permet de supprimer les BL liés aux lignes)
            Si la vente est une vente appelée, on repasse la vente ouverte 
            liée à "En cours"
        """
        sale_line_obj = self.env['sale.order.line']
        for sale in self:
            open_order = sale.open_order_id
            if sale.type == 'call' and open_order and open_order.state == 'done':
                for line in sale.order_line_ids:
                    #On recherche les lignes de la commande ouverte correspondant,
                    #Si on en trouve une, on repasse la vente à "en cours"
                    open_line = sale_line_obj.search([('product_id', '=', line.product_id.id), ('sale_order_id', '=', open_order.id)])
                    if open_line:
                        open_order.write({'state': 'draft'})
                        open_order.delete_workflow()
                        open_order.create_workflow()
                        open_order.signal_workflow('sale_validate')
                        break
                    
            sale.order_line_ids.unlink()
            
            
        return super(sale_order, self).unlink()
    
    
    @api.multi
    def write(self, vals=None):
        """
            On ne peut changer le type de vente si elle est appelée ou ouverte, 
            et on ne peut modifier la vente ouverte si elle est terminée
        """
        if not vals:
            vals = {}
        
        for sale in self:
            if 'type' in vals and sale.type in ['call', 'open'] and vals['type'] != sale.type:
                raise Warning(_("You can't change the type of a called or opened sale"))
            
            if 'open_order_id' in vals and sale.open_order_id.state == 'done' and sale.open_order_id.id != vals['open_order_id']:
                raise Warning(_("You can't change the opened order of a sale if the opened order is done"))
        
        res = super(sale_order, self).write(vals=vals)
        return res
    
    
    def additional_function_domain(self, arg):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de sale_order
        """
        arg0, arg1, arg_1 = False, False, False
        return arg0, arg1, arg_1
    
    
    def compute_domain_args_sale(self, args):
        """
            Fonction qui permet modifier le domain du search
        """
        args2 = []
        for arg in args:
            if isinstance(arg, str) or (isinstance(arg, list) and arg[0] in ('!', '|', '&')):
                args2.append(arg)
                continue
            
            arg0, arg1, arg_1 = self.additional_function_domain(arg)
            if arg0 and arg1:
                arg[0] = arg0
                arg[1] = arg1
                arg[-1] = arg_1
                
            args2.append(arg)

        return args2


    @api.model
    def search(self,args=None, offset=0, limit=None, order=None, count=None):
        args = args or []
        args_modified = self.compute_domain_args_sale(args)
        return super(sale_order,self).search(args=args_modified, offset=offset, limit=limit, order=order, count=count) 
    
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=1000):
        """
            Fonction name_search
        """
        args.append(('name', 'ilike', name))
        args = self.compute_domain_args_sale(args)
        recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()
    

    
class sale_common_attribute(models.Model):
    _name = 'sale.common.attribute'
    _order = 'sequence'
    
    sale_line_id = fields.Many2one('sale.order.line', string='Sale line', required=True, ondelete='cascade')
    sequence = fields.Integer(default=0, required=True)
    product_common_attribute_id = fields.Many2one('common.attribute.model', string='Attribute', required=False, ondelete='cascade')
    value = fields.Char(size=128, required=False)
    
    
    
class sale_order_line_fixed_discount(models.Model):
    _name = 'sale.order.line.fixed.discount'
    _order = 'sequence'
    _rec_name = 'descriptive'
    
    sale_line_id = fields.Many2one('sale.order.line', string='Sale', required=False, ondelete='cascade')
    invoice_line_id = fields.Many2one('account.invoice.line', string='Invoice line', required=False, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=1, required=True)
    descriptive = fields.Char(string='Descriptive', size=256, required=False)
    amount = fields.Float(string='Amount', default=0.0, required=True, digits=dp.get_precision('Product quantity'))
    
    
class sale_order_line_variable_discount(models.Model):
    _name = 'sale.order.line.variable.discount'
    _order = 'sequence'
    _rec_name = 'descriptive'

    @api.model
    def _type_get(self):
        return [
                ('cumulative', _('Cumulative')),
                ('cascade', _('Cascade')),
                       ]
    
    
    sale_line_id = fields.Many2one('sale.order.line', string='Sale', required=False, ondelete='cascade')
    invoice_line_id = fields.Many2one('account.invoice.line', string='Invoice line', required=False, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=1, required=True)
    descriptive = fields.Char(string='Descriptive', size=256, required=False)
    amount = fields.Float(string='Variable', default=0.0, required=True, digits=dp.get_precision('Product quantity'))
    type = fields.Selection('_type_get', string='Type', default='cumulative', required=True)
    