# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
from openerp.tools.float_utils import float_compare
from openerp.tools.misc import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.exceptions import except_orm, ValidationError, UserError
from openerp.addons.base_openprod import utils
from openerp.addons.base_openprod.common import get_form_view, hash_list
from operator import itemgetter

from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrule, MONTHLY
from dateutil.parser import parse
from decimal import Decimal
import pytz


INTERVAL_TYPES = {
    'work_days': lambda interval: relativedelta(days=interval),
    'days': lambda interval: relativedelta(days=interval),
    'hours': lambda interval: relativedelta(hours=interval),
    'weeks': lambda interval: relativedelta(days=7 * interval),
    'months': lambda interval: relativedelta(months=interval),
    'minutes': lambda interval: relativedelta(minutes=interval),
}


def convert_tz(date, t_from, t_to):
    date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
    tz = pytz.timezone(t_from)
    date_user = tz.localize(date)
    tz1 = pytz.timezone(t_to)
    date_final = date_user.astimezone(tz1)
    return date_final


class stock_incoterms(models.Model):
    """ 
    Incoterms
    """
    _name = 'stock.incoterms'
    _description = 'Incoterms'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Name', size=64, required=True, help='Incoterms are series of sales terms.They are '
                       'used to divide transaction costs and responsibilities between buyer and seller and reflect'
                       ' state-of-the-art transportation practices.')
    code = fields.Char(string='Code', size=3, required=False, help='Code for Incoterms')
    active = fields.Boolean(string='Active', default=True, help='By unchecking the active field, you may hide an INCOTERM without deleting it.')


    @api.multi
    def name_get(self):
        res = []
        for incoterm in self:
            if incoterm.code:
                new_name = '[%s] %s'%(incoterm.code, incoterm.name)
            else:
                new_name = incoterm.name
                
            res.append((incoterm.id, new_name))
            
        return res
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=1000):
        """
            Fonction name_search de la nomenclature
        """
        recs = False
        if name:
            recs = self.search([('code',operator,name)]+ args, limit=limit)
            
            if not recs:
                recs = self.search([('name', operator, '%'+name+'%')] + args, limit=limit)
        
        else:
            recs = self.search(args, limit=limit)
            
        return recs.name_get()
    
    
    
class stock_lot(models.Model):
    """ 
    Stock Lot 
    """
    _name = 'stock.lot'
    _description = 'Stock Lot'
    
    @api.one
    @api.depends('uom_qty')
    def _compute_qtys(self):
        self.uom_qty = 0.0
        self.sec_uom_qty = 0.0

    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True, readonly=False, default='/')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='restrict')
    uom_qty = fields.Float(compute='_compute_qtys', string='UoM qty', digits=dp.get_precision('Product quantity'))
    uom_id = fields.Many2one('product.uom', related='product_id.uom_id', string='UoM', readonly=True)
    sec_uom_qty = fields.Float(compute='_compute_qtys', string='Second UoM qty', digits=dp.get_precision('Product quantity'))
    sec_uom_id = fields.Many2one('product.uom', related='product_id.sec_uom_id', string='Second UoM', readonly=True)
    supplier_lot_number = fields.Char(size=64)
    expiry_date = fields.Date()
    removal_date = fields.Date()
    is_expiry_date = fields.Boolean(related='product_id.is_expiry_date', default=False, readonly=True)
    total_mrp_rm_cost = fields.Float(string='Total material first cost', default=0.0, digits=(12,12))
    total_mrp_produce_cost = fields.Float(string='Total produce cost', default=0.0, digits=(12,12))
    qty_produce = fields.Float(string='Qty produce', default=0.0, digits=(12,12))

    def compute_date(self, start_date, day, month, year):
        res = False
        if start_date:
            res = datetime.strptime(start_date, DEFAULT_SERVER_DATE_FORMAT)
            res = res + relativedelta(days=day or 0) + relativedelta(months=month or 0) + relativedelta(years=year or 0)
            res = res.strftime(DEFAULT_SERVER_DATE_FORMAT)
            
        return res


    @api.model
    def create(self, vals):
        """
            Création du name avec compteur
        """
        if 'name' not in vals or vals.get('name') == '/':
            vals['name'] = self.env['ir.sequence'].get('stock.lot')
        
        today = fields.Date.today()
        product = self.env['product.product'].browse(vals['product_id'])
        if product.is_expiry_date and product.expiry_type == 'automatic':
            vals['expiry_date'] = self.compute_date(today, product.expiry_day, product.expiry_month, product.expiry_year)
            vals['removal_date'] = self.compute_date(today, product.removal_day, product.removal_month, product.removal_year)
            
        return super(stock_lot, self).create(vals=vals)
    
    
    def additional_function_domain(self, arg):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de stock_picking
        """
        arg0, arg1, arg_1 = False, False, False
        return arg0, arg1, arg_1
    
    
    def compute_domain_args_stock_lot(self, args):
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
        args_modified = self.compute_domain_args_stock_lot(args)
        return super(stock_lot,self).search(args=args_modified, offset=offset, limit=limit, order=order, count=count) 
    
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=1000):
        """
            Fonction name_search
        """
        args.append(('name', 'ilike', name))
        args = self.compute_domain_args_stock_lot(args)
        recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()
    
    
    
class stock_picking(models.Model):
    """ 
    Stock picking 
    """
    _name = 'stock.picking'
    _description = 'Stock picking'
    
    
    @api.model
    def _type_get(self):
        return [
                ('in', _('IN')),
                ('out', _('OUT')),
                    ]

    
    @api.model
    def _invoice_state_get(self):
        return [
                ('2binvoiced', _('To be invoiced')),
                ('invoiced', _('Invoiced')),
                ('none', _('Not applicable')),
                       ]

        
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('waiting', _('Waiting')),
                ('done', _('Done')),
                ('cancel', _('Cancel')),
                       ]

    
    @api.model
    def _invoice_postage_get(self):
        return [
                ('never', _('Never')),
                ('always', _('Always')),
                ('threshold', _('< Threshold')),
                       ]
        
        
    def compute_field_availability(self):
        """
            Minimum de la disponibilité de tous les mouvements 
        """
        if self.type == 'out':
            availability = min([m.availability for m in self.move_ids if m.state not in ('done', 'cancel')] or [0.0])
        else:
            availability = 0.0
        
        return availability
    
    
    @api.one
    def _compute_availability(self):
        """
            Minimum de la disponibilité de tous les mouvements 
        """
        self.availability = self.compute_field_availability()
    
    
    def _search_availability(self, operator, value):
        """
            Fonction search de la disponibilité de l'ot
        """ 
        picking_rcs = self.search([('state', 'not in', ('done','cancel'))])
        picking_ids = []
        for picking in picking_rcs:
            availability = picking.compute_field_availability()
            if value == 100 and availability >= 100:
                picking_ids.append(picking.id)
            elif value == 0.1 and availability < 100 and availability > 0:
                picking_ids.append(picking.id)
            else:
                pass
            
        return [('id', 'in', picking_ids)]


    def _get_states(self):
        return {'done': [('readonly', True)], 'cancel': [('readonly', True)], 'waiting': [('readonly', True)]}
    
    
    @api.one   
    @api.depends('move_ids')
    def _compute_stock_quality_control_ids(self):
        """
            Si on a indiqué qu'on gérait les documents sur les pickings dans les paramètres, 
            On récupère toutes les lignes de documents imprimés des moves
        """
        manage_documents = self.env['stock.config.settings'].get_param('manage_picking_document') or False
        quality_control_list = []
        if manage_documents and self.id:
            query = "SELECT document_id FROM move_document_openprod_rel WHERE move_id in (SELECT id FROM stock_move WHERE picking_id = %s)"%(self.id) 
            self.env.cr.execute(query)
            quality_control_list = [x[0] for x in self.env.cr.fetchall()]  

        self.quality_control_ids = quality_control_list
        
        
    @api.one   
    @api.depends('move_ids')
    def _compute_manage_documents(self):
        """
            On récupère toutes les lignes de factures liées aux lignes d'achat
        """
        self.manage_documents = self.env['stock.config.settings'].get_param('manage_picking_document') or False

    
    @api.one
    @api.depends()
    def _compute_is_not_company_warehouse(self):
        self.is_not_company_warehouse = False
        
        
    def _search_is_not_company_warehouse(self, operator, value):
        return [('warehouse_id', '=', self.env.user.company_id.warehouse_id.id)]
         
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True, readonly=True, default='/')
    state = fields.Selection('_state_get', required=True, select=True, default='draft', copy=False)
    move_ids = fields.One2many('stock.move', 'picking_id',  string='Stock moves', states=_get_states, copy=True, domain=[('not_usable', '=', False)])
    type = fields.Selection('_type_get')
    backorder_id = fields.Many2one('stock.picking', string='Back order of', required=False, ondelete='restrict', states=_get_states)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=False, ondelete='restrict', states=_get_states)
    origin = fields.Char(string='Origin', size=128, required=False, states=_get_states)
    date = fields.Datetime(default=lambda self: fields.Datetime.now(), states=_get_states)
    date_expected = fields.Date(default=lambda self: fields.Date.today(), states=_get_states)
    date_create = fields.Datetime(string='Create date', readonly=True, default=lambda self: fields.Datetime.now(), states=_get_states)
    partner_id = fields.Many2one('res.partner', string='Partner', required=False, ondelete='restrict', states=_get_states)
    availability = fields.Float(compute='_compute_availability', search='_search_availability')
    invoice_state = fields.Selection('_invoice_state_get', states=_get_states, required=True, default='2binvoiced')
    company_id = fields.Many2one('res.company', string='Company', required=True, ondelete='restrict', select=True, default=lambda self: self.env.user.company_id, states=_get_states)    
    is_return = fields.Boolean(string='Return', default=False)
    is_partial = fields.Boolean(string='Partial', default=False)
    manage_scrap = fields.Boolean(default=False)
    lock = fields.Boolean(default=False)
    payment_lock = fields.Boolean(default=False)
    invoice_auto = fields.Boolean(string='Invoice auto', default=False, help='If this field is checked, invoice will be created when the picking will be done')
    print_packaging_list = fields.Boolean(string='Print packaging list', default=False, help='If this field is checked, the packaging list will be printed on reports')
    internal_note = fields.Text()
    printed_note = fields.Html()
    manage_documents = fields.Boolean(string='Manage documents', compute='_compute_manage_documents', store=False)
    quality_control_ids = fields.Many2many('document.openprod', 'picking_document_openprod_rel', 'picking_id', 'document_id',  string='Printed documents', copy=True, 
                                           compute='_compute_stock_quality_control_ids')
    color_priority_need = fields.Integer(default=0, required=False, readonly=True)
    picking_external = fields.Char(string='External picking', size=256, required=False)
    
    # Douanes
    total_weight = fields.Float(string='Total weight', default=0.0, required=False)
    weight_unit_id = fields.Many2one('product.uom', string='Unity', required=False, ondelete='restrict')
    total_volume = fields.Float(string='Total volume', default=0.0, required=False)
    volume_unit_id = fields.Many2one('product.uom', string='Unity', required=False, ondelete='restrict')
    nb_pallet_package = fields.Integer(string='Number of pallet package', default=0, required=False)
    insurance_value = fields.Float(string='Insurance value', default=0.0, required=False)
    insurance_currency_id = fields.Many2one('res.currency', string='Currency', required=False, ondelete='restrict')
    
    # Adresse
    address_id = fields.Many2one('address', string='Address', required=False, ondelete='restrict')
    address_contact_id = fields.Many2one('res.partner', string='Contact', required=False, ondelete='restrict')
    address_name = fields.Char(string='Name', required=False)
    street = fields.Char(string='Street', size=128, required=False)
    street2 = fields.Char(string='Street 2', size=128, required=False)
    street3 = fields.Char(string='Street 3', size=128, required=False)
    zip = fields.Char(string='Zip', size=24, required=False)
    city = fields.Char(string='City', size=128, required=False)
    region_id = fields.Many2one('res.region', string='Region', required=False, ondelete='restrict')
    country_id = fields.Many2one('res.country', string='Country', required=True, ondelete='restrict')
    
    # Transport
    incoterm_id = fields.Many2one('stock.incoterms', string='Incoterm', required=False, ondelete='restrict', help='Incoterm which stands commercial transaction.')
    invoice_postage = fields.Selection('_invoice_postage_get', string='Invoice postage', default='never')
    threshold = fields.Float(string='Threshold', default=0.0, required=False)
    forwarding_agent_id = fields.Many2one('res.partner', string='Forwarding Agent', required=False, ondelete='restrict')
    delivery_delay = fields.Integer(string='Delivery delay', default=0, required=False)
    
    is_automatic = fields.Boolean(string='Automatic', default=False, states=_get_states, help='If this field is checked, when a stock move will be processed, the corresponding stock move of transfer request will also be processed')
    is_not_company_warehouse = fields.Boolean(compute='_compute_is_not_company_warehouse', search='_search_is_not_company_warehouse')
    
    forecast = fields.Boolean(default=False)
    
    
    @api.one
    @api.constrains('lock', 'payment_lock', 'state')    
    def _check_blocked_stock_picking(self):
        """
            Verifie que le picking ne puisse pas être traité s'il est bloqué
        """
        if (self.lock or self.payment_lock) and self.state in ('2bshipped', 'done'):
            raise Warning(_('Error ! You cannot process a blocked picking (informations tab)'))
    
    
    @api.one
    @api.constrains('is_partial', 'manage_scrap')    
    def _check_partial_picking(self):
        """
            Verifie que le booléen de génération de reliquat soit bien décoché si celui
            de livraison partielle l'es aussi 
        """
        if self.manage_scrap and not self.is_partial:
            raise Warning(_('Error ! You cannot generate rest if you don\'t accept partial delivery'))
            
        return True
    
    
    @api.onchange('partner_id')
    def onchange_parter_id(self):
        if self.type == 'out':
            if self.partner_id.is_company and self.partner_id.is_supplier:
                self.address_id = self.partner_id.address_id and self.partner_id.address_id.id
            else:
                # Adresse
                address = self.partner_id.get_partner_address({'delivery': True})
                if address:
                    self.address_id = address.get('delivery_address', False)
                else:
                    self.address_id = False

            # Transport
            for k, v in self.get_transport_files(self.partner_id).iteritems():
                self[k] = v
    
    
    @api.onchange('country_id')
    def _onchange_country_id(self):
        """
            Si on change de pays, on vide le champ de la région
        """
        if self.region_id and self.region_id.country_id != self.country_id:
            self.region_id = False
            
            
    @api.onchange('company_id')
    def _onchange_company_id(self):
        """
            Dans le cas d'un BR, lors de la sélection de la société, on récupère son adresse
        """
        if self.type == 'in':
            partner_company = self.company_id and self.company_id.partner_id or False
            if partner_company:
                self.address_id = partner_company.address_id and partner_company.address_id.id or False
            else:
                self.address_id = False
                 
                 
    @api.onchange('invoice_state')
    def _onchange_invoice_state(self):
        """
            Dans le cas d'un BR, lors de la sélection de la société, on récupère son adresse
        """
        res = {'value': {}, 'warning': {}}
        if self.type == 'in':
            res['warning'] = {'title': _('Warning'), 'message': _('Warning if the picking is linked to a purchase this can have a consequence on the invoice.!')}
        elif self.type == 'out':
            res['warning'] = {'title': _('Warning'), 'message': _('Warning if the picking is linked to a sale this can have a consequence on the invoice.!')}
        
        return res
            
    @api.onchange('address_id')
    def onchange_address_id(self):
        for k, v in self.address_id.get_fields().iteritems():
            self[k] = v


    def get_transport_files(self, partner):       
        return {
            'incoterm_id': partner.sale_incoterm_id.id,
            'invoice_postage': partner.sale_invoice_postage, 
            'forwarding_agent_id': partner.sale_forwarding_agent_id.id,
            'delivery_delay': partner.sale_delivery_delay,
                } 
    
    
    @api.one
    def check_cancel(self):
        """
            Passe le picking cancel si tous les mouvements sont cancel
        """
        if not self.env['stock.move'].search([('picking_id', '=', self.id), ('state', '!=', 'cancel')], limit=1):
            self.wkf_cancel(with_move=False)
        
        return True
    
    
    @api.one
    def compute_date_expected(self):
        """
            Recalcul de la date du picking au changement du move: Si réception: date_expected=max(date_expected des mouvements)
                                                                  Si livraison: date_expected=min(date_expected des mouvements)  
        """
        if self.type == 'in':
            date_expected = self.env['stock.move'].search_read([('picking_id', '=', self.id), ('state', '!=', 'cancel')], ['date_expected'], limit=1, order='date_expected desc')
            date_expected = date_expected and date_expected[0]['date_expected'] or False
        elif self.type == 'out':
            date_expected = self.env['stock.move'].search_read([('picking_id', '=', self.id), ('state', '!=', 'cancel')], ['date_expected'], limit=1, order='date_expected asc')
            date_expected = date_expected and date_expected[0]['date_expected'] or False
        else:
            date_expected = False
            
        if date_expected != self.date_expected:
            self.write({'date_expected': date_expected})
        
        return True


    @api.one
    def compute_date(self):
        """
            Recalcul de la date du picking au changement du move: Si réception: date=max(date des mouvements)
                                                                  Si livraison: date=min(date des mouvements)  
        """
        if self.type == 'in':
            date = self.env['stock.move'].search_read([('picking_id', '=', self.id), ('state', '!=', 'cancel')], ['date'], limit=1, order='date desc')
            date = date and date[0]['date'] or False
        elif self.type == 'out':
            date = self.env['stock.move'].search_read([('picking_id', '=', self.id), ('state', '!=', 'cancel')], ['date'], limit=1, order='date asc')
            date = date and date[0]['date'] or False
    
        if date != self.date:
            self.write({'date': date})
        
        return True
    
    
    @api.one
    def compute_availability(self):
        """
            Recalcul de la dispo du picking au changement du move: Si réception: dispo=max(dispo des mouvements)
                                                                   Si livraison: dispo=min(dispo des mouvements)  
        """
        if self.type == 'in':
            availability = self.env['stock.move'].search_read([('picking_id', '=', self.id), ('state', '!=', 'cancel')], ['availability'], limit=1, order='availability desc')
            availability = availability and availability[0]['availability'] or False
        elif self.type == 'out':
            availability = self.env['stock.move'].search_read([('picking_id', '=', self.id), ('state', '!=', 'cancel')], ['availability'], limit=1, order='availability asc')
            availability = availability and availability[0]['availability'] or False
    
        if availability != self.availability:
            self.write({'availability': availability})
        
        return True
    
    
    @api.one
    def compute_color_priority_need(self):
        """
            Recalcul de la couleur du picking au changement du move: color_priority_need=max(color_priority_need des mouvements)
        """
#         color_priority_need = self.env['stock.move'].search_read([('picking_id', '=', self.id), 
#                                                                   ('state', '!=', 'cancel')], ['color_priority_need'], limit=1, order='color_priority_need desc')
#         color_priority_need = color_priority_need and color_priority_need[0]['color_priority_need'] or False
        self.env.cr.execute("SELECT color_priority_need FROM stock_move WHERE state != 'cancel' and picking_id=%s ORDER BY color_priority_need desc"%(self.id))
        res = self.env.cr.dictfetchone()
        if res:
            color_priority_need = res['color_priority_need']
            if color_priority_need != self.read_light(['color_priority_need'])[0]['color_priority_need']:
                self.write({'color_priority_need': color_priority_need})
        
        return True
    
    
    def get_invoice_state(self):
        """
            Méthode redéfinie dans sale_purchase pour forcer l'invoice_state à 'none' en cas de facturation sur quantité commandée
            :type self: stock.picking
            :return: État de facturation
            :rtype: char
        """
        if self.invoice_state == 'none':
            invoice_state = 'none'
        else:
            invoice_state = '2binvoiced'
        
        return invoice_state
    
    
    def do_partial_auto(self):
        for picking_rc in self:
            picking_rc.do_partial(self.env['stock.partial.picking'].with_context({
                'active_id': picking_rc.id,
                'active_ids': [picking_rc.id],
                'active_model': 'stock.picking'
            }).create({}).line_ids)
        
        return True
            
            
    def do_partial(self, lines, make_done=True, transfer_origin_move_rc=False):
        """
            Traite un picking en créant un reliquat si besoin
            :type self: stock.picking
            :param lines: Lignes de wizard de traitement du picking (chaque ligne représente un mouvement)
            :type lines: recordset list: stock.partial.picking.line
            :return: Nouveau picking si reliquat. Sinon False
            :rtype: recordset: stock.picking
        """
        new_picking = False
        move_to_done = self.env['stock.move']
        move_to_copy = {}
        processed_moves = self.env['stock.move']
        move_to_transfert = self.env['stock.move']
        move_to_cancel = self.env['stock.move']
        manage_scrap = self.manage_scrap
        ctx = self.env.context.copy()
        for line in lines:
            line_manage_scrap = line.manage_scrap
            move = line.move_id
            processed_moves += move
            if line.uom_qty > 0:
                if line.uom_qty > move.uom_qty:
                    move.write({'uom_qty': line.uom_qty,
                                'sec_uom_qty': line.sec_uom_qty,
                                'uoi_qty': line.uoi_qty}, update_transfer_move=True)
                    move_to_done += move
                elif line.uom_qty < move.uom_qty:
                    if not self.is_partial:
                        raise except_orm(_('Error'), _('Please check the "partial" field in the picking, if you do not use the whole quantity.'))
                    
                    if line_manage_scrap:
                        new_uom_qty = move.uom_qty - line.uom_qty
                        new_sec_uom_qty = max(move.sec_uom_qty - line.sec_uom_qty, 0.0)
                        new_uoi_qty = max(move.uoi_qty - line.uoi_qty, 0.0)
                        move_to_copy[move] = {'uom_qty': new_uom_qty, 
                                              'sec_uom_qty': new_sec_uom_qty, 
                                              'uoi_qty': new_uoi_qty}

                    move.write({'uom_qty': line.uom_qty,
                                'sec_uom_qty': line.sec_uom_qty,
                                'uoi_qty': line.uoi_qty}, update_transfer_move=True)
                    move_to_done += move
                        
                else:
                    if move.is_variable_double_unit:
                        move.write({'sec_uom_qty': line.sec_uom_qty,
                                    'uoi_qty': line.uoi_qty}, update_transfer_move=True)
                        
                    move_to_done += move
                    
            elif line_manage_scrap:
                if 'transfer_move_scrap' in ctx:
                    ctx['transfer_move_scrap'].append(move.id)
                else:
                    ctx['transfer_move_scrap'] = [move.id]
                    
                move_to_transfert += move
            else:
                move_to_cancel += move
        
        if manage_scrap:
            move_to_transfert += self.move_ids - processed_moves
        else:
            move_to_cancel += self.move_ids - processed_moves
        
        if move_to_copy or move_to_transfert:
            invoice_state =  self.get_invoice_state()
            new_picking = self.copy({'backorder_id': self.id, 'move_ids': False, 'invoice_state': invoice_state})
            if new_picking:
                for move, vals in move_to_copy.iteritems():
                    vals['picking_id'] = new_picking.id
                    if transfer_origin_move_rc:
                        vals['transfer_move_id'] = transfer_origin_move_rc.id
                        
                    move.copy(vals)
            
                if move_to_transfert:
                    move_to_transfert.write({'picking_id': new_picking.id})
                    
            new_picking.wkf_waiting()
        
        if move_to_done and make_done:
            move_to_done.with_context(ctx).wkf_done()
        
        if move_to_cancel:
            move_to_cancel.wkf_cancel()
        
        if make_done:
            self.wkf_done()
            label_rcs = self.env['stock.label']
            for move_label in self.env['stock.move.label'].search([('move_id', 'in', self.move_ids.ids), ('label_id', '!=', False)]):
                if move_label.label_id.template_id.is_reprint_done:
                    label_rcs += move_label.label_id
            
            if label_rcs:
                ctx = self.env.context.copy()
                ctx['jasper'] = {}
                ctx['jasper']['reprint'] = True
                label_rcs.with_context(ctx).do_print_label()
         
        else:
            label_rcs = self.env['stock.label']
            for move_label in self.env['stock.move.label'].search([('move_id', 'in', self.move_ids.ids), ('label_id', '!=', False)]):
                if move_label.label_id.template_id.is_reprint_valid:
                    label_rcs += move_label.label_id
            
            if label_rcs:
                ctx = self.env.context.copy()
                ctx['jasper'] = {}
                ctx['jasper']['reprint'] = True
                label_rcs.with_context(ctx).do_print_label()   
            
        return new_picking
    
    
    def copy_return_move_st(self, vals):
        """
            Fonction qui permet de déconnecter les mouvements de retour lors de leur copy des ots de soustraitance.
            :param vals: Dico pour la copy du mouvement
            :type vals: dico
        """
        return vals
    
    
    def do_return(self, lines, expected_return, expected_date, note, invoice_state):
        """
            Crée un retour de picking et éventuellement son re-retour
            :type self: stock.picking
            :param lines: Ligne de wizard de retour (chaque ligne représente un mouvement)
            :type lines: stock.return.picking.line
            :param expected_return: Création d'un re-retour si coché
            :type expected_return: boolean
            :param expected_date: Date du re-retour
            :type expected_date: date
            :param note: Note propagée sur le retour
            :type note: text
            :return: Picking de retour
            :rtype: recordset: stock.picking
        """
        new_picking = False
        new_return_picking = False
        return_move_to_copy = {}
        move_to_copy = {}
        move_list = self.env['stock.move']
        context = self.env.context  
        nonconformity = False
        return_location_dest_id = False
        if 'nonconformity_id' in context:  
            nonconformity = self.env['nonconformity.file'].browse(context['nonconformity_id'])
            nonconformity.write({'is_return_product': True})
        
        # Nouveau type
        if self.type == 'in':
            new_type = 'out'
        elif self.type == 'out':
            new_type = 'in'
        else:
            new_type = self.type
        
        for line in lines:
            move = line.move_id
            if line.uom_qty > 0:
                move_list += move
                location_id = move.location_dest_id.id
                location_dest_id_init = move.location_id.id
                if new_type == 'in':
                    location_dest_id = move.warehouse_id and move.warehouse_id.input_location_id and move.warehouse_id.input_location_id.id or move.location_id.id
                else:
                    location_dest_id = location_dest_id_init
                    
                if nonconformity:
                    if nonconformity.type in ('post_reception', 'reception'):
                        if move.picking_id and move.picking_id.type == 'in':
                            if (move.location_dest_id.usage != 'internal' and move.location_id.usage == 'internal') or (move.location_id.usage == 'internal' and move.location_dest_id.usage == 'internal'):
                                return_location_dest_id = move.location_id.id
                                if move.sinfo_id and move.sinfo_id.partner_id and move.sinfo_id.partner_id.supplier_location_id:
                                    location_dest_id = move.sinfo_id.partner_id.supplier_location_id.id
                                else:
                                    location_dest_id = move.warehouse_id.supplier_location_id.id
                            
                            elif (move.location_id.usage != 'internal' and move.location_dest_id.usage != 'internal'):
                                return_location_dest_id =  move.warehouse_id.input_location_id.id
                                if move.sinfo_id and move.sinfo_id.partner_id and move.sinfo_id.partner_id.supplier_location_id:
                                    location_dest_id = move.sinfo_id.partner_id.supplier_location_id.id
                                else:
                                    location_dest_id = move.warehouse_id.supplier_location_id.id
                                
                move_to_copy[move] = {'uom_qty': line.uom_qty,
                                      'sec_uom_qty': line.sec_uom_qty,
                                      'uoi_qty': line.uoi_qty,
                                      'location_id': location_id,
                                      'location_dest_id': location_dest_id,
                                      'trigger_supply': 'without_stock',
                                      'label_rcs': line.label_id,
                                      'is_return': True,}
                # Re retour
                if expected_return:
                    if nonconformity and return_location_dest_id and nonconformity.type in ('post_reception', 'reception'):
                        location_id = return_location_dest_id
                        
                    return_move_to_copy[move] = {'is_return': True, 
                                                 'uom_qty': line.uom_qty,
                                                 'sec_uom_qty': line.sec_uom_qty,
                                                 'uoi_qty': line.uoi_qty,
                                                 'location_dest_id': location_id,
                                                 'location_id': location_dest_id_init,
                                                 'trigger_supply': 'without_stock'}
        
        if move_to_copy:
            # Création du retour
            origin_return = _('Return picking %s')%(self.name)
            copy_vals = {'type': new_type, 
                         'is_return': True, 
                         'move_ids':False, 
                         'invoice_state': invoice_state, 
                         'origin': origin_return,
                         'picking_external': ''}
            if note:
                copy_vals['internal_note'] = note
                
            new_picking = self.copy(copy_vals)
            # Création des mouvements du retour
            if new_picking:
                for move, vals in move_to_copy.iteritems():
                    vals['picking_id'] = new_picking.id
                    if 'label_rcs' in vals:
                        label_rcs = vals['label_rcs']
                        del vals['label_rcs']
                        
                    vals = self.copy_return_move_st(vals)
                    copy_move = move.copy(vals)
                    if label_rcs:
                        dict_label_qty = {}
                        dict_label_qty[label_rcs] = (label_rcs.origin_uom_qty, label_rcs.origin_sec_uom_qty)
                        copy_move.assign_label(label_rcs, dict_label_qty=dict_label_qty,  with_scrap=False)
        
        # Re retour
        if return_move_to_copy:
            # Création du re-retour
            origin_return_return = _('Return of return picking %s')%(new_picking.name)
            if not expected_date:
                expected_date = fields.Datetime.now()
                
            new_return_picking = self.copy({'is_return': False, 
                                            'date': expected_date, 
                                            'date_expected': expected_date, 
                                            'date_create': expected_date, 
                                            'move_ids':False, 
                                            'invoice_state': invoice_state, 
                                            'origin': origin_return_return,
                                            'picking_external': ''})
            # Création des mouvements du re-retour
            if new_return_picking:
                for move, vals in return_move_to_copy.iteritems():
                    vals.update({'is_return': True, 
                                 'picking_id': new_return_picking.id, 
                                 'date': expected_date, 
                                 'date_expected': expected_date, 
                                 'priority_date': expected_date})
                    
                    if move.warehouse_id:
                        if move.type == 'in' and move.warehouse_id.input_location_id:
                            vals['location_dest_id'] = move.warehouse_id.input_location_id.id
                    
                    vals = self.copy_return_move_st(vals)
                    move.copy(vals)
        
        if new_picking:
            new_picking.wkf_waiting()
        
        if new_return_picking:
            new_return_picking.wkf_waiting()
        
        return new_picking


    @api.multi
    def update_covers(self):
        """
            Recalcul des couvertures
        """
        product_rs = self.env['product.product']
        for picking in self:
            for move in picking.move_ids:
                product_rs |= move.product_id
            
        return product_rs.cover_compute()

    
    def get_form_view(self):
        """
            Retourne une action avec la vue form par défaut en fonction du type
            :type self: stock.picking
            :return: Action
            :rtype: dict
        """
        action = self.env.ref('stock.act_stock_picking_%s'%(self.type))
        if action:
            action = action.read()[0]
            if action.get('views'):
                for index,item in enumerate(action['views']):
                    if item[-1] == 'form':
                        del action['views'][index]
                        action['views'].insert(0, item)
            action['res_id'] = self.id
            action['view_mode'] = 'form'
            
        return action 
        
    
    def create_picking(self, type, partner=False, product_qty_uom=None, date=False, warehouse_rs=False, other_data=None):
        """
            Mise à jour des stock
            :type self: stock.picking
            :param type: Type du picking. Valeurs possibles: (in, out)
            :type type: string
            :param partner: Partner du picking
            :type partner: recordset: res.partner
            :param product_qty_uom: Liste des produits, qté, udm des mouvements à créer
            :type product_qty_uom: dict: {product: {'variable': ..., 'uom_qty': ..., 'uom_id': ..., 'sec_uom_qty': ..., 'sec_uom_id': ...}}
            :param date: Date optionnel. Date entrée dans date prévue, date et date de priorité
            :type date: string au format '%Y-%m-%d %H:%M:%S' ou '%Y-%m-%d'
            :param warehouse_rs: Entrepôt
            :type warehouse_rs: recordset: stock.warehouse
            :param other_data: Dictionnaire permetant de passer d'autres champs ou de forcer des champs
            :type other_data: dict
            :return: True
            :rtype: boolean
        """
        vals = {'type': type}
        if date:
            vals['date'] = date
            vals['date_expected'] = date 
                 
        if partner:
            vals['partner_id'] = partner.id
            if type == 'out':
                # Transport
                vals.update(self.get_transport_files(partner))
                # Adresse
                address = partner.get_partner_address({'delivery': True})
                if address:
                    address_id = address.get('delivery_address', False)
                    if not address_id and address.values():
                        address_id = address.values()[0]
                        
                    if address_id:
                        vals['address_id'] = address_id.id
                        addr_vals = utils.transform_to_ids(self, address_id.get_fields(partner))
                        vals.update(addr_vals)
        else:
            vals['invoice_state'] = 'none'
            
        if type == 'in':
            company_partner = self.env.user.company_id.partner_id
            if company_partner:
                address_id = company_partner.address_id
                vals['address_id'] = address_id.id
                addr_vals = utils.transform_to_ids(self, address_id.get_fields(company_partner))
                vals.update(addr_vals)
                    
        if other_data:
            vals.update(other_data)
            
        picking = self.create(vals)
        if product_qty_uom:
            for product, data in product_qty_uom.iteritems():
                location_dest_id=False
                if type == 'in' and warehouse_rs and warehouse_rs.is_receipt_directly_storage:
                        storage_location_rc = product.get_storage_location(warehouse_id=warehouse_rs.id)
                        if storage_location_rc:
                            location_dest_id = storage_location_rc.id
                    
                self.env['stock.move'].create_move(product,
                                                   dst_location=location_dest_id,
                                                   qty=data['uom_qty'], 
                                                   uom=data['uom_id'], 
                                                   sec_qty=data['sec_uom_qty'], 
                                                   sec_uom=data['sec_uom_id'], 
                                                   type=type, 
                                                   date=date, 
                                                   picking=picking, 
                                                   partner=partner, 
                                                   with_price=True,
                                                   warehouse_rs=warehouse_rs)
            
        return picking
    
    
    @api.multi
    def create_invoice(self):
        """
            Fonction permettant de créer la facture liée au picking
            Prévue pour être surchargée dans sale_purchase
        """
        return self.env['account.invoice']
    
    
    @api.multi
    def button_create_invoice(self):
        """
            Bouton qui permet de créer la facture à partir d'un picking et qui retourne la facture créée
        """
        return True
    
    
    @api.multi
    def print_picking(self):
        """
            Fonction associée au bouton du picking, permet d'imprimer
            des pickings
        """
        return True
      
      
    def do_print_picking(self):
        """ 
            Fonction permettant d'imprimer le picking ainsi que les controles et plans liés aux produits
            du picking
        """
        return True
    
    
    @api.multi
    def reopen(self, keep_move_dates=False):
        """
            On réouvre le picking s'il n'y a pas de factures validées liées
            Si le picking est lié à des factures brouillon, on les annule
        """
        for line in self.move_ids:
            invoice_state = line.invoice_line_id.invoice_id and line.invoice_line_id.invoice_id.state or False
            if invoice_state and invoice_state not in ('draft', 'cancel'):
                #Dans le cas d'un BL, si la facture a été annulée on permet la réouverture du picking
                if not (line.type == 'out' and invoice_state == 'cancel'):
                    raise ValidationError(_('You can\'t reopen the picking because there is an opened or done linked invoice'))
                    
            else:
                if line.invoice_line_id.invoice_id.internal_number:
                    if line.invoice_line_id.invoice_id.state == 'draft':
                        line.invoice_line_id.invoice_id.signal_workflow('invoice_cancel')

                    line.write({'invoice_line_id': False})
                else:
                    line.invoice_line_id.invoice_id.unlink()

        if self.invoice_state == 'invoiced':
            self.invoice_state = '2binvoiced'
        
        context = self.env.context
        context2 = {}
        context2.update(context)
        context2['reopen_picking'] = True
        self.env.context = context2
        self.with_context(context2).wkf_cancel(keep_move_dates=keep_move_dates)
        self.with_context(context2).wkf_draft()
        return True
    
    
    def manage_sale_purchase_state(self, unlink_picking_ids=False):
        """
            Gestion de l'état des ventes et des achats liés au picking
            :type self: stock.picking
            :return: True
            :rtype: boolean
        """
        return True

    
    @api.multi
    def wkf_draft(self):
        """
            État à done draft
        """
        self.move_ids.wkf_draft_with_aggregate()
        self.write({'state': 'draft'})
        self.manage_sale_purchase_state()
    
    
    @api.multi
    def wkf_waiting(self):
        """
            État à done waiting
        """
        for picking_rs in self:
            move_rs = self.env['stock.move'].search([('picking_id', 'in', self.ids), ('state', '=', 'draft')])
            move_rs.wkf_waiting()
            warehouse_id = False
            for move in move_rs:
                if warehouse_id:
                    if warehouse_id != move.warehouse_id.id:
                        raise ValidationError(_('Impossible to have different warehouses in a picking.'))
                                                 
                else:
                    warehouse_id = move.warehouse_id.id
                
            picking_rs.write({'state': 'waiting', 'warehouse_id': warehouse_id})
    
    
    @api.multi
    def wkf_done(self):
        """
            État à done date
        """
        #On modifie le context pour le traitement des quantités livrées (vente)
        context = self.env.context
        context2 = {}
        context2.update(context)
        context2['treat_picking'] = True
        self.env.context = context2
        for picking in self:
            if picking.invoice_auto and picking.invoice_state == '2binvoiced':
                picking.create_invoice()
            
            if not picking.move_ids:
                raise except_orm(_('Error'), _('You can not done a picking if there is no movement'))
            
            
            if picking.type == 'in' and picking.state == 'done' and not picking.picking_external:
                raise Warning(_('Error ! You need to set the external picking to close the picking'))
            
        self.write({'state': 'done', 'color_priority_need': 0})
        self.manage_sale_purchase_state()
        
        
    @api.multi
    def wkf_cancel(self, with_move=True, manage_sale_purchase_state=True, keep_move_dates=False):
        """
            État à cancel
        """
        move_obj = self.env['stock.move']
        for picking in self:
            #On recherche tous les moves liés au picking (nécessaire à cause du domaine sur not_usable)
            move_rs = move_obj.search([('picking_id', '=', picking.id)])
            picking_type = picking.type
            for line in move_rs:
                invoice_state = line.invoice_line_id.invoice_id and line.invoice_line_id.invoice_id.state
                if invoice_state and invoice_state != 'draft':
                    if not (picking_type == 'out' and invoice_state == 'cancel'):
                        raise ValidationError(_('You can\'t cancel the picking because there is an opened or done linked invoice'))
                else:
                    line.invoice_line_id.invoice_id.unlink()
            
            if picking.invoice_state == 'invoiced':
                picking.invoice_state = '2binvoiced'
                
            if with_move:
                move_rs.wkf_cancel(with_cancel_picking=False, keep_dates=keep_move_dates)
                
        #Gestion de la modification des quantités commandées, reçues etc..
        context = self.env.context
        context2 = {}
        context2.update(context)
        context2['treat_picking'] = True
        self.env.context = context2
        self.write({'state': 'cancel', 'color_priority_need': 0})
        if manage_sale_purchase_state:
            self.manage_sale_purchase_state()
    
    
    @api.multi
    def unlink(self):
        move_obj = self.env['stock.move']
        context = self.env.context
        for picking in self:
            if picking.state == 'done':
                raise except_orm(_('Error'), _('Impossible to delete a stock picking in state done.'))
            else:
                #On recherche tous les moves liés au picking (nécessaire à cause du domaine sur not_usable)
                move_rs = move_obj.search([('picking_id', '=', picking.id)])
                move_rs.unlink()
            
            if not context.get('without_manage_state'):
                picking.manage_sale_purchase_state([picking.id])
            
        return super(stock_picking, self).unlink()


    @api.model
    def create(self, vals):
        """
            Création du name Ex: OUT/00241
        """
        if 'name' not in vals or vals.get('name') == '/':
            vals['name'] = self.env['ir.sequence'].get('stock.picking.%s'%(vals['type']))
        
        res = super(stock_picking, self).create(vals=vals)
        res.manage_sale_purchase_state()
        return res
    
    
    @api.multi
    def copy(self, default=None):
        """
            Création du name Ex: OUT/00241
        """
        if not default:
            default = {}
              
        if 'name' not in default or default.get('name') == '/':
            default['name'] = self.env['ir.sequence'].get('stock.picking.%s'%(default.get('type', False) or self.type))
        
        default['picking_external'] = ''
        return super(stock_picking, self).copy(default=default)
    
    
    def additional_function_domain(self, arg):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de stock_picking
        """
        arg0, arg1, arg_1 = False, False, False
        return arg0, arg1, arg_1
    
    
    def compute_domain_args_resource(self, args):
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
        args_modified = self.compute_domain_args_resource(args)
        return super(stock_picking,self).search(args=args_modified, offset=offset, limit=limit, order=order, count=count) 
    
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=1000):
        """
            Fonction name_search
        """
        args.append(('name', 'ilike', name))
        args = self.compute_domain_args_resource(args)
        recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()
    
    
    
class stock_level(models.Model):
    """ 
    Stock level 
    """
    _name = 'stock.level'
    _description = 'Stock level'
    _rec_name = 'product_id'
    

    @api.model
    def _get_default_warehouse(self):
        return self.env.user.company_id.warehouse_id
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    uom_qty = fields.Float(string='UoM qty', required=True, digits=dp.get_precision('Product quantity'), default=0.0)
    sec_uom_qty = fields.Float(string='Second UoM qty', required=True, digits=dp.get_precision('Product quantity'), default=0.0)
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade', select=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True, ondelete='cascade', default=_get_default_warehouse)

    def update_stock_level(self, product, qty, sec_qty, move_type, warehouse_id, action, uom=False, sec_uom=False):
        """
            Mise à jour des stock
            :type self: stock.picking
            :param product: Produit à mettre à jour
            :type product: recordset: product.product
            :param qty: Quantité du mouvement
            :type qty: float
            :param qty: Seconde quantité du mouvement
            :type qty: float
            :param move_type: Type du mouvement (in ou out)
            :type move_type: string
            :param action: Action du mouvement (passage à l'état done ou cancel)
            :type action: string
            :param uom: UoM de la quantité
            :type uom: recordset: product.uom
            :param uom: UoM de la seconde quantité
            :type uom: recordset: product.uom
            :return: True
            :rtype: boolean
        """
        stock_level = self.search([('product_id', '=', product.id), ('warehouse_id', '=', warehouse_id)])
        if not stock_level:
            stock_level = self.create({'product_id': product.id, 'warehouse_id': warehouse_id})

        is_variable_double_unit = product.dual_unit and product.dual_unit_type == 'variable' or False
        if stock_level:
            vals = {}
            if move_type == 'in':
                uom_obj = self.env['product.uom']
                if uom and uom != product.uom_id:
                    qty = uom_obj._compute_qty_obj(uom, qty, product.uom_id, with_round=False)
                    if is_variable_double_unit and sec_uom and sec_uom != product.sec_uom_id:
                        sec_qty = uom_obj._compute_qty_obj(sec_uom, sec_qty, product.sec_uom_id, with_round=False)
                    
                if action == 'done':
                    vals = {'uom_qty': stock_level.uom_qty + qty}
                    if is_variable_double_unit:
                        vals['sec_uom_qty'] = stock_level.sec_uom_qty + sec_qty
                        
                elif action == 'cancel':            
                    vals = {'uom_qty': stock_level.uom_qty - qty}
                    if is_variable_double_unit:
                        vals['sec_uom_qty'] = stock_level.sec_uom_qty - sec_qty
                    
            elif move_type == 'out':
                uom_obj = self.env['product.uom']
                if uom and uom != product.uom_id:
                    qty = uom_obj._compute_qty_obj(uom, qty, product.uom_id, with_round=False)
                    if is_variable_double_unit and sec_uom and sec_uom != product.sec_uom_id:
                        sec_qty = uom_obj._compute_qty_obj(sec_uom, sec_qty, product.sec_uom_id, with_round=False)
                    
                if action == 'done':
                    vals = {'uom_qty': stock_level.uom_qty - qty}
                    if is_variable_double_unit:
                        vals['sec_uom_qty'] = stock_level.sec_uom_qty - sec_qty
                        
                elif action == 'cancel':
                    vals = {'uom_qty': stock_level.uom_qty + qty}
                    if is_variable_double_unit:
                        vals['sec_uom_qty'] = stock_level.sec_uom_qty + sec_qty
            
            if vals:
                stock_level.write(vals)
                
        return True
    


class stock_move_cover_rel(models.Model):
    """ 
        Stock move cover relation 
    """
        
    _name = 'stock.move.cover.rel'
    _description = 'Stock move cover relation'
    _log_create = False
    #===========================================================================
    # COLUMNS
    #===========================================================================
    out_move_id = fields.Many2one('stock.move', required=True, ondelete='cascade')
    in_move_id = fields.Many2one('stock.move', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', required=False, ondelete='cascade')
    cover_qty = fields.Float(digits=dp.get_precision('Product quantity'), default=0.0)
    in_cover_percent = fields.Float(default=0.0)
    out_cover_percent = fields.Float(default=0.0)



class stock_move(models.Model):
    """
    Stock Move
    """
    _name = 'stock.move'
    _description = 'Stock Move'
    _order = 'date_expected desc, id'
    _log_create = False
        
    
    @api.one
    @api.depends('picking_id', 'location_id', 'location_dest_id', 'location_id.usage', 'location_dest_id.usage')
    def _compute_type(self):
        """
            Calcul du type du mouvement
            :type self: stock.move
            :return: Type du mouvement (in (entrant), out (sortant), ext (externe) ou int (interne))
            :rtype: string
        """
        location_obj = self.env['stock.location']
        internal_types = location_obj.get_internal_usages()
        external_types = location_obj.get_external_usages()
        if self.location_id.usage in internal_types and self.location_dest_id.usage in external_types: 
            self.type = 'out'
        elif self.location_id.usage in external_types and self.location_dest_id.usage in internal_types: 
            self.type = 'in'
        elif self.location_id.usage in external_types and self.location_dest_id.usage in external_types: 
            self.type = 'ext'
        elif self.location_id.usage in internal_types and self.location_dest_id.usage in internal_types: 
            self.type = 'int'
        else:
            self.type = ''
            
            
    @api.one
    @api.depends()
    def _compute_covers(self):
        """
            Récupération des valeurs de couverture dans la table de relation entre move et move
        """
        rel_rs = False
        if self.env.context.get('monitoring_move_id') and self.env.context.get('monitoring_product_id'):
            if self.env.context.get('monitoring_move_type') == 'in':
                rel_rs = self.env['stock.move.cover.rel'].search([('product_id', '=', self.env.context['monitoring_product_id']),
                                                                  ('in_move_id', '=', self.env.context['monitoring_move_id']),
                                                                  ('out_move_id', '=', self.id)], limit=1)
            elif self.env.context.get('monitoring_move_type') == 'out':
                rel_rs = self.env['stock.move.cover.rel'].search([('product_id', '=', self.env.context['monitoring_product_id']),
                                                                  ('in_move_id', '=', self.id),
                                                                  ('out_move_id', '=', self.env.context['monitoring_move_id'])], limit=1)
        
        if rel_rs:
            self.cover_qty = rel_rs.cover_qty
            self.in_cover_percent = rel_rs.in_cover_percent
            self.out_cover_percent = rel_rs.out_cover_percent
        else:
            self.cover_qty = 0.0 
            self.out_cover_percent = 0.0
            self.in_cover_percent = 0.0


    def _default_location_id(self, warehouse_rs=False):
        res = False
        if 'picking_type' in self.env.context:
            if self.env.context['picking_type'] == 'in':
                if warehouse_rs:
                    res = warehouse_rs.supplier_location_id
                else:
                    res = self.env.user.company_id.warehouse_id.supplier_location_id or \
                          self.env['stock.location'].search([('usage', '=', 'supplier')], limit=1)
                    
            elif self.env.context['picking_type'] == 'out':
                if warehouse_rs:
                    res = warehouse_rs.delivery_location_id
                else:
                    res = self.env.user.company_id.warehouse_id.delivery_location_id or \
                          self.env['stock.location'].search([('usage', '=', 'internal')], limit=1)
            
        return res
        
    
    def _default_location_dest_id(self, warehouse_rs=False):
        res = False
        if 'picking_type' in self.env.context:
            if self.env.context['picking_type'] == 'in':
                if warehouse_rs:
                    res = warehouse_rs.input_location_id
                else:
                    res = self.env.user.company_id.warehouse_id.input_location_id or \
                          self.env['stock.location'].search([('usage', '=', 'internal')], limit=1)
                    
            elif self.env.context['picking_type'] == 'out':
                if warehouse_rs:
                    res = warehouse_rs.customer_location_id
                else:
                    res = self.env.user.company_id.warehouse_id.customer_location_id or \
                          self.env['stock.location'].search([('usage', '=', 'customer')], limit=1)
            
        return res
    
        
    @api.model
    def _state_get(self):
        return [
            ('draft', _('Draft')),
            ('waiting', _('Waiting')),
            ('done', _('Done')),
            ('cancel', _('Cancel')),
               ]


    @api.model
    def _type_get(self):
        return [
            ('in', _('Incoming')),
            ('out', _('Outgoing')),
            ('int', _('Internal')),
            ('ext', _('External')),
               ]


    @api.model
    def _supply_method_get(self):
        return [
            ('buy', _('Buy')),
               ]


    @api.model
    def _trigger_supply_get(self):
        return [
            ('make_to_plan', _('On scheduler')),
            ('make_to_order', _('On demand')),
            ('make_to_order_with_stock', _('On demand with stock')),
            ('without_stock', _('None')),
               ]


    def _get_states(self):
        return {
            'waiting': [('readonly', True)], 
            'done': [('readonly', True)], 
            'cancel': [('readonly', True)], 
                }


    @api.multi
    def name_get(self):
        """
            Name get du mouvement
        """
        return [(m.id, '%s (id: %d)'%(m.origin or '/', m.id)) for m in self]
    
    
    @api.one
    @api.depends('product_id', 'product_id.track_label', 'product_id.track_in_lot', 'product_id.track_out_lot', 'product_id.categ_id')
    def _get_product_fields(self):
        product_read = self.product_id and self.product_id.read(['track_label', 'track_in_lot', 'track_out_lot', 'categ_id'], load='_classic_write')[0]
        if product_read:
            self.track_in_lot_product = product_read['track_in_lot']
            self.track_out_lot_product = product_read['track_out_lot']
            self.track_label_product = product_read['track_label']
            self.product_category_id = product_read['categ_id']
        else:
            self.track_in_lot_product = False
            self.track_out_lot_product = False
            self.track_label_product = False
            self.product_category_id = False
            

    @api.model
    def _type_qty_get(self):
        return [
            ('fixed', _('Fixed')),
            ('variable', _('Variable')),
            ('formula', _('Formula')),
        ]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True, states=_get_states)
    origin = fields.Char(required=False, size=128, states=_get_states)
    product_id = fields.Many2one('product.product', string='Product', required=True, select=True, ondelete='restrict', states=_get_states)
    product_category_id = fields.Many2one('product.category', string='Product category', compute='_get_product_fields', required=False, ondelete='restrict', 
                                          store=True, domain=[('type', '!=', 'view')])
    location_id = fields.Many2one('stock.location', string='Src location', required=True, select=True, ondelete='restrict', states=_get_states, default=_default_location_id)
    location_dest_id = fields.Many2one('stock.location', string='Dest location', required=True, select=True, ondelete='restrict', states=_get_states, default=_default_location_dest_id)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=False, ondelete='restrict', states=_get_states)
    company_id = fields.Many2one('res.company', string='Company', required=True, ondelete='restrict', select=True, default=lambda self: self.env.user.company_id, states=_get_states)
    picking_id = fields.Many2one('stock.picking', string='Picking', required=False, ondelete='restrict', states=_get_states, select=True, auto_join=True)
    availability = fields.Float(default=0.0, compute=False)
    state = fields.Selection('_state_get', required=True, select=True, default='draft', copy=False)
    type = fields.Selection('_type_get', select=True, compute='_compute_type', store=True, states=_get_states)
    theo_price = fields.Float(default=0.0, digits=dp.get_precision('Account'), readonly=True, string='Theorical price')
    partner_price = fields.Float(default=0.0, digits=dp.get_precision('Account'), states=_get_states)
    currency_id = fields.Many2one('res.currency', string='Partner currency', required=False, ondelete='restrict', states=_get_states)
    freight_price = fields.Float(default=0.0, digits=dp.get_precision('Account'), states=_get_states, string='Freight price')
    freight_currency_id = fields.Many2one('res.currency', string='Freight currency', required=False, ondelete='restrict', states=_get_states)
    sequence = fields.Integer(default=1, states=_get_states)
    note = fields.Text(states=_get_states)
    control_ids = fields.Many2many('document.openprod', 'move_document_openprod_rel', 'move_id', 'document_id',  string='Printed documents', copy=True)
    invoice_line_id = fields.Many2one('account.invoice.line', string='Invoice line', required=False, ondelete='set null', copy=False)
    supply_method = fields.Selection('_supply_method_get', string='Supply method', required=True, default='buy', states=_get_states, 
                    help="Produce will generate production order or tasks, according to the product type. Buy will trigger purchase orders when requested.")
    trigger_supply = fields.Selection('_trigger_supply_get', string='Trigger supply', required=True, default='make_to_plan', states=_get_states, help="'On scheduler': When needed, " 
                        "the system take from the stock or wait until re-supplying. 'On demand': When needed, purchase or produce the product for the procurement "
                        "request. 'On demand with stock': During the order, the system will substract the virtual quantity to the stock if needed. 'None':"
                        "Select if you don't want automatic supplying proposition from the system. CAUTION: If 'None' is selected, the system does not make "
                        "supply proposition even if it observes an insufficient need and stock. There is an out of stock risk.")
    is_return = fields.Boolean(string='Return', default=False)
    is_not_billable = fields.Boolean(string='Not billable', default=False)
    
    # Quantités
    uom_qty = fields.Float(string='UoM qty', required=True, select=True, digits=dp.get_precision('Product quantity'), default=0.0, states=_get_states)
    sec_uom_qty = fields.Float(string='Second UoM qty', required=True, digits=dp.get_precision('Product quantity'), default=0.0, states=_get_states)
    uoi_qty = fields.Float(string='UoI qty', required=True, digits=dp.get_precision('Product quantity'), default=0.0, states=_get_states)
    initial_uom_qty = fields.Float(string='Initial UoM qty', required=True, digits=dp.get_precision('Product quantity'), default=0.0, states=_get_states)
    initial_sec_uom_qty = fields.Float(string='Initial second UoM qty', digits=dp.get_precision('Product quantity'), default=0.0, states=_get_states)
    initial_uoi_qty = fields.Float(string='Initial UoI qty', digits=dp.get_precision('Product quantity'), default=0.0, states=_get_states)
    
    # UoM
    uom_id = fields.Many2one('product.uom', string='UoM', required=True, ondelete='restrict', states=_get_states)
    sec_uom_id = fields.Many2one('product.uom', string='Second UoM', required=True, ondelete='restrict', states=_get_states)
    uoi_id = fields.Many2one('product.uom', string='UoI', required=True, ondelete='restrict', states=_get_states)
    sec_uom_category_id = fields.Many2one('product.uom.category', string='Category', related='sec_uom_id.category_id', required=False, ondelete='restrict', 
                                          readonly=True)
    initial_uom_id = fields.Many2one('product.uom', string='Initial UoM', required=True, ondelete='restrict', states=_get_states)
    initial_sec_uom_id = fields.Many2one('product.uom', string='Initial second UoM', required=False, ondelete='restrict', states=_get_states)
    initial_uoi_id = fields.Many2one('product.uom', string='Initial UoI', required=False, ondelete='restrict', states=_get_states)
    
    # Calcul double unité
    dual_unit = fields.Boolean(string='Dual unit', help="Check if you want manage a dual unit for this product", default=False)
    dual_unit_type = fields.Selection(string='Dual unit type', selection=[('fixed', 'Fixed'), ('variable', 'Variable')], default='fixed')
    factor = fields.Float(default=1.0)
    divisor = fields.Float(default=1.0)
    is_variable_double_unit = fields.Boolean(default=False)

    # Dates
    date = fields.Datetime(default=lambda self: fields.Datetime.now(), select=True, states=_get_states)
    date_expected = fields.Date(default=lambda self: fields.Date.today(), states=_get_states)
    priority_date = fields.Datetime(default=lambda self: fields.Datetime.now(), states=_get_states)
    done_date = fields.Datetime()
    date_create = fields.Datetime(string='Create date', readonly=True, default=lambda self: fields.Datetime.now())
    # TODO: voir si transformer month en champ sélection
    month = fields.Char(size=2, required=False)
    year = fields.Char(size=4, required=False)
    week = fields.Char(size=2, required=False)
    
    inventory_id = fields.Many2one('stock.inventory', string='Inventory', required=False, ondelete='restrict')
    inventory_label_id = fields.Many2one('stock.inventory.label', string='Inventory Label', required=False, ondelete='restrict')
   
    # Cover
        # Sotant
    in_move_ids = fields.Many2many('stock.move', 'stock_move_cover_rel', 'out_move_id', 'in_move_id', string='IN moves', readonly=True)
    covered_by_stock_percent = fields.Float(string='Covered by stock (%)', default=0.0, readonly=True)
    covered_by_stock_qty = fields.Float(string='Covered by stock (qty)', default=0.0, readonly=True)
    covered_by_move_percent = fields.Float(string='Covered by incoming move (%)', default=0.0, readonly=True)
    covered_by_move_qty = fields.Float(string='Covered by incoming move (qty)', default=0.0, readonly=True)
    not_covered_percent = fields.Float(string='Not covered (%)', default=0.0, readonly=True)
    not_covered_qty = fields.Float(string='Not covered (qty)', default=0.0, readonly=True)
    in_date = fields.Date('IN date', readonly=True)
    out_delta = fields.Integer(string='Delta', default=0, required=False, readonly=True)
    
        # Entrant
    out_move_ids = fields.Many2many('stock.move', 'stock_move_cover_rel', 'in_move_id', 'out_move_id', string='OUT moves', readonly=True)
    covers_move_percent = fields.Float(string='Covers outgoing move (%)', default=0.0, readonly=True)
    covers_move_qty = fields.Float(string='Covers outgoing move (qty)', default=0.0, readonly=True)
    covers_stock_percent = fields.Float(string='Covers stock (%)', default=0.0, readonly=True)
    covers_stock_qty = fields.Float(string='Covers stock (qty)', default=0.0, readonly=True)
    out_date = fields.Date('OUT date', readonly=True)
    in_delta = fields.Integer(string='Delta', default=0, required=False, readonly=True)

    cover_qty = fields.Float(digits=dp.get_precision('Product quantity'), default=0.0, compute='_compute_covers')
    in_cover_percent = fields.Float(default=0.0, compute='_compute_covers', help="Percentage of incoming movement used by the outgoing movement")
    out_cover_percent = fields.Float(default=0.0, compute='_compute_covers', help="Percentage of outgoing movement covered by the incoming movement")
    color_priority_need = fields.Integer(default=0, required=False, readonly=True)
    force_covers_display_in = fields.Boolean(string='Force covers display IN', default=False)
    force_covers_display_out = fields.Boolean(string='Force covers display OUT', default=False)

    is_confirmed = fields.Boolean(string='Confirmed', default=False, help='Incoming move:\n\tThe field is checked when the procurement (purchase order or work order) is planned\nOutgoing move:\n\tThe field is checked when all moves who covers this move are confirmed')
    is_forecast = fields.Boolean(string='Forecast', default=False, states=_get_states)
    
    # Labels
    move_label_ids = fields.One2many('stock.move.label', 'move_id',  string='Labels', copy=True)
    valid_label = fields.Boolean(default=False, copy=False, readonly=True)
    track_label_product = fields.Boolean(string="Track Label Product", compute='_get_product_fields', store=True)

    # Lots
    move_lot_ids = fields.One2many('stock.move.lot', 'move_id',  string='Lots', copy=True)
    track_out_lot_product = fields.Boolean(string='Track OUT lot', compute='_get_product_fields', store=True)
    track_in_lot_product = fields.Boolean(string='Track IN lot', compute='_get_product_fields', store=True)

    # Procurement
    procurement_id = fields.Many2one('procurement.order', string='Procurement order', required=False, select=True, ondelete='set null', states=_get_states)
    reserved_qty = fields.Float(string='Reserved qty', required=False, digits=dp.get_precision('Product quantity'), default=0.0, readonly=True)
    history_id = fields.Many2one('stock.move.history', string='History', required=False, ondelete='restrict', select=True, copy=False)
    not_usable = fields.Boolean(default=False, copy=False)
    
    # Déclaration quality
    control_declaration_id = fields.Many2one('quality.control.declaration', string='Quality Control Declaration', ondelete='set null', copy=False)
    post_control_declaration_id = fields.Many2one('quality.control.declaration', string='Post Quality Control Declaration', ondelete='set null', copy=False)
    nonconformity_file_ids = fields.One2many('nonconformity.file', 'move_id', string='Nonconformity File', copy=False)
    is_control_declaration_recep = fields.Boolean(string='Reception Control quality', default=False)
    is_recalculate_frequency_control = fields.Boolean(string='Recalculate frequency control', default=False)
    is_principal_quality = fields.Boolean(string='is_principal_quality', default=True)
    move_hs_id = fields.Many2one('stock.move', string='Move HS', required=False, ondelete='set null', select=True, copy=False)
    move_quarantine_id = fields.Many2one('stock.move', string='Move quarantine', required=False, ondelete='set null', select=True, copy=False)
    no_control = fields.Boolean(string='No control', default=False)
    
    # Transfert
    transfer_id = fields.Many2one('stock.transfer.request', string='Transfer', required=False, ondelete='restrict', select=True)
    transfer_move_id = fields.Many2one('stock.move', string='Transfer move (IN)', required=False, ondelete='set null', copy=False, select=True)
    out_transfer_move_id = fields.Many2one('stock.move', string='Transfer move (OUT)', required=False, ondelete='set null', copy=True, select=True)
    
    #Production
    type_qty = fields.Selection('_type_qty_get', string='Type', default='variable')
    parameter_ids = fields.One2many('stock.move.parameter', 'move_id', string='Parameters', copy=True)
    
    def onchange_product_id(self, product_id, move_type=False):
        if isinstance(product_id, int):
            product_id = self.env['product.product'].browse(product_id)
        
        res = {}
        res['uom_id'] = product_id.uom_id
        res['name'] = product_id.name
        res['dual_unit'] = product_id.dual_unit
        res['dual_unit_type'] = product_id.dual_unit_type
        res['supply_method'] = product_id.supply_method
        res['trigger_supply'] = product_id.trigger_supply
        res['is_variable_double_unit'] = res['dual_unit'] and res['dual_unit_type'] == 'variable' or False 
        res['is_control_declaration_recep'] = False
        if product_id and (self.type == 'in' or self.type == 'int'):
            qcp_rcs = self.env['quality.control.product'].search([('type', 'in', ('reception', 'all')), ('product_id', '=', product_id.id)], limit=1)
            if qcp_rcs:
                res['is_control_declaration_recep'] = True
        
        # Gestion des documents imprimés
        manage_documents = self.env['stock.config.settings'].get_param('manage_picking_document') or False
        if manage_documents and product_id:
            if not move_type: 
                move_type = self.type
                
            if move_type == 'in':
                printed_type = 'pdf_receipt'
            elif move_type == 'out':
                printed_type = 'pdf_delivery'
            else:
                printed_type = ''
            
            res['control_ids'] = []
            for printed_doc in product_id.plan_control_ids:
                if printed_doc.type == printed_type and printed_doc.pdf_file:
                    res['control_ids'].extend([(4, printed_doc.pdf_file.id)])
        
        uoms = product_id.get_uoms(type=self.type, with_factor=True)
        for k, v in uoms.iteritems():
            res[k] = v
        
        return res
    
    
    @api.onchange('product_id', 'type')
    def _onchange_product_id(self):
        """
            Au changement du produit, changement des UoM et du nom
        """
        res = self.onchange_product_id(self.product_id)
        for k,v in res.iteritems():
            self[k] = v
    
    
    @api.onchange('uom_qty', 'uom_id')
    def _onchange_uom_qty(self):
        res = self.onchange_uom_qty(self.uom_qty, self.uom_id, self.sec_uom_id, self.uoi_id, self.dual_unit, self.dual_unit_type, self.factor, self.divisor)
        for k,v in res.iteritems():
            self[k] = v
          
    
    def onchange_uom_qty(self, uom_qty, uom_id, sec_uom_id, uoi_id, dual_unit, dual_unit_type, factor, divisor):
        """
            Au changement de la qty, changement des autres qty
        """
        res = {}
        qtys = self.product_id.get_qtys(uom_qty, 
                                 uom_id=uom_id, 
                                 sec_uom_id=sec_uom_id, 
                                 uoi_id=uoi_id, 
                                 by_field='uom', 
                                 dual_unit=dual_unit, 
                                 dual_unit_type=dual_unit_type, 
                                 factor=factor, 
                                 divisor=divisor,
                                 with_raise=True)
        
        for k, v in qtys.iteritems():
            if k in ('uop_id', 'uos_id'):
                res['sec_uom_id'] = v
            else:
                res[k] = v
        
        return res
    
        
    @api.onchange('sec_uom_qty', 'sec_uom_id')
    def _onchange_sec_uom_qty(self):
        """
            Au changement de la qty, changement des autres qty et de la catégorie pour le domaine
        """
        qtys = self.product_id.get_qtys(self.sec_uom_qty, 
                                 uom_id=self.uom_id, 
                                 sec_uom_id=self.sec_uom_id, 
                                 uoi_id=self.uoi_id, 
                                 by_field='sec_uom', 
                                 dual_unit=self.dual_unit, 
                                 dual_unit_type=self.dual_unit_type, 
                                 factor=self.factor, 
                                 divisor=self.divisor, 
                                 with_raise=True)
        
        for k, v in qtys.iteritems():
            self[k] = v
            
        self.sec_uom_category_id = self.sec_uom_id.category_id
            
            
    @api.onchange('uoi_qty', 'uoi_id')
    def _onchange_uoi_qty(self):
        """
            Au changement de la qty, changement des autres qty
        """
        qtys = self.product_id.get_qtys(self.uoi_qty, 
                                 uom_id=self.uom_id, 
                                 sec_uom_id=self.sec_uom_id, 
                                 uoi_id=self.uoi_id, 
                                 by_field='uoi', 
                                 dual_unit=self.dual_unit, 
                                 dual_unit_type=self.dual_unit_type, 
                                 factor=self.factor, 
                                 divisor=self.divisor, 
                                 with_raise=True)
        
        for k, v in qtys.iteritems():
            self[k] = v

    
    @api.onchange('date_expected')
    def _onchange_date_expected(self):
        self.date = self.date_expected
        
    
    def get_product_uom_qty(self, with_raise=False, with_round=False):
        """
            Calcul de la quantité du mouvement en UdM du produit
            :param: with_raise: Optionnel (False par défaut): Si vrai et pas la même catégorie entre les deux UoM: raise
            :type: with_raise: boolean
            :param: with_round: Optionnel (True par défaut): Si vrai, arrondi de la quantité par rapport aux arrondis des UoM
            :type: with_round: boolean
            :return: Quantité du mouvement en UdM du produit
            :rtype: float
        """
        if self.uom_id.id == self.product_id.uom_id.id:
            res = self.uom_qty
        else:
            res = self.env['product.uom']._compute_qty_obj(self.uom_id, self.uom_qty, self.product_id.uom_id, with_raise=with_raise, with_round=with_round)
        
        return res
    
    
    def get_product_sec_uom_qty(self, with_raise=False, with_round=False):
        """
            Calcul de la quantité du mouvement en seconde UdM du produit
            :param: with_raise: Optionnel (False par défaut): Si vrai et pas la même catégorie entre les deux UoM: raise
            :type: with_raise: boolean
            :param: with_round: Optionnel (True par défaut): Si vrai, arrondi de la quantité par rapport aux arrondis des UoM
            :type: with_round: boolean
            :return: Quantité du mouvement en seconde UdM du produit
            :rtype: float
        """
        if self.sec_uom_id.id == self.product_id.sec_uom_id.id:
            res = self.sec_uom_qty
        else:
            res = self.env['product.uom']._compute_qty_obj(self.sec_uom_id, self.sec_uom_qty, self.product_id.sec_uom_id, with_raise=with_raise, with_round=with_round)
        
        return res
    
    
    def get_label_qty(self):
        """
            Calcul des sommes des lignes d'étiquttes du mouvement (move_label) en première et seconde unité
            :return: Sommes des lignes d'étiquttes du mouvement (move_label) en première et seconde unité
            :rtype: dict: {'uom_qty': 0.0, 'sec_uom_qty': 0.0}
        """
        return self.env['stock.move.label'].search_group(fields=['uom_qty', 'sec_uom_qty'], 
                                                         groupby=[], 
                                                         args=[('move_id', '=', self.id)],
                                                         sum=['uom_qty', 'sec_uom_qty'],
                                                         return_dict=True,
                                                         without_order=True)
    
    
    @api.multi
    def generate_nonconformity_manual(self):
        """
            Generer fiche de non-conformité manuelle
        """
        nonconformity_obj = self.env['nonconformity.file']
        for move in self:
            nonconformity_rcs = nonconformity_obj.generate_manual(move)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Nonconformity File',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'nonconformity.file',
                'res_id': nonconformity_rcs.id,
                'target': 'current',
            }
        
        return True    
        
        
    @api.multi
    def update_covers(self):
        """
            Recalcul des couvertures
        """
        product_rs = self.env['product.product']
        for move in self:
            product_rs |= move.product_id
        
        return product_rs.cover_compute()
    

    def change_date(self, new_date):
        self.write({
            'date_expected': new_date, 
            'date': new_date,
            'priority_date': new_date
        })
        return self.update_covers()

    
    
    def assign_label(self, labels, dict_label_qty=None, with_scrap=True, with_write=False, with_move=True, inactive=False):
        """
            Affectation des étiquettes au mouvement
            :type self: stock.move
            :param labels: Étiquettes à affecter
            :type labels: recordsets: stock.label
            :param with_scrap: Si vrai et que la qté des étiquettes affectées est inferieur au mouvement: création d'un reliquat
            :type with_scrap: boolean
            :param with_write: Si vrai et que la qté des étiquettes affectées est différente de celles du mouvement: MAJ des qtés du mouvement
            :type with_write: boolean
            :param with_move: Si vrai et que l'étiquette ne se trouve pas dans le même emplacement que le mouvement: mouvement de l'étiquette
            :type with_move: boolean
            :return: True
            :rtype: bool
        """
        new_move = self.env['stock.move']
        move_label_obj = self.env['stock.move.label']
        move = self
        ctx = self.env.context.copy()
        # Mouvement des étiquettes si elles ne sont pas dans l'emplacement d'ou part le mouvement
        if with_move:
            location = move.location_id
            for label in labels:
                if label.location_id.id != location.id:
                    label.with_context(ctx).move(location)
        
        # Création des étiquettes
        move, qty = move_label_obj.create_move_label(labels, move_rs=move, dict_label_qty=dict_label_qty)
        
        if with_write:
            # Double unité variable
            if move.is_variable_double_unit:
                # Calcule qty avec la somme des étiquettes dans le mouvement
                qty_dict = move_label_obj.search_group(fields=['uom_qty', 'sec_uom_qty'], 
                                                              groupby=[], 
                                                              args=[('move_id', '=', move.id)],
                                                              sum=['uom_qty', 'sec_uom_qty'],
                                                              return_dict=True,
                                                              without_order=True)
                if qty_dict and qty_dict[0]:
                    qty = 'uom_qty' in qty_dict[0] and qty_dict[0]['uom_qty'] or 0.0
                    sec_qty =  'sec_uom_qty' in qty_dict[0] and qty_dict[0]['sec_uom_qty'] or 0.0
                else:
                    qty = 0.0
                    sec_qty = 0.0
                    
                # Comparaison des quantités 
                if move.uom_id != move.product_id.uom_id:
                    qty = move.uom_id._compute_qty_obj(move.product_id.uom_id, qty, move.uom_id, with_raise=False, with_round=False)
    
                if move.sec_uom_id != move.product_id.sec_uom_id:
                    sec_qty = move.uom_id._compute_qty_obj(move.product_id.sec_uom_id, sec_qty, move.sec_uom_id, with_raise=False, with_round=False)
        
                uoi_qty_factor = move.uoi_qty / (move.sec_uom_qty or 1.0)
                old_move_qty = move.uom_qty 
                old_move_sec_qty = move.sec_uom_qty 
                move.write({
                    'uom_qty': qty,
                    'sec_uom_qty': sec_qty,
                    'uoi_qty': sec_qty * uoi_qty_factor,
                            }, update_transfer_move=True)
                
                if with_scrap and qty < old_move_qty:
                    # Reliquat
                    diff =  old_move_qty - qty
                    sec_diff =  old_move_sec_qty - sec_qty
                    new_move = move.copy({
                            'uom_qty': diff,
                            'sec_uom_qty': sec_diff,
                            'uoi_qty': sec_diff * uoi_qty_factor,
                            'picking_id': move.picking_id.id
                                   })
                    
            # Simple unité et double unité fixe
            else:
                # Calcule qty avec la somme des étiquettes dans le mouvement
                qty_dict = move_label_obj.search_group(fields=['uom_qty'], 
                                                              groupby=[], 
                                                              args=[('move_id', '=', move.id)],
                                                              sum='uom_qty',
                                                              return_dict=True,
                                                              without_order=True)
                qty = qty_dict and qty_dict[0] and 'uom_qty' in qty_dict[0] and qty_dict[0]['uom_qty'] or 0.0
                # Comparaison de la quantités 
                if move.uom_id != move.product_id.uom_id:
                    qty = move.uom_id._compute_qty_obj(move.product_id.uom_id, qty, move.uom_id, with_raise=False, with_round=False)
        
                sec_uom_qty_factor = move.sec_uom_qty / (move.uom_qty or 1.0)
                uoi_qty_factor = move.uoi_qty / (move.uom_qty or 1.0)
                old_move_qty = move.uom_qty 
                move.write({
                    'uom_qty': qty,
                    'sec_uom_qty': qty * sec_uom_qty_factor,
                    'uoi_qty': qty * uoi_qty_factor,
                            }, update_transfer_move=True)
                
                if  with_scrap and qty < old_move_qty:
                    # Reliquat
                    diff =  old_move_qty - qty
                    new_move = move.copy({
                            'uom_qty': diff,
                            'sec_uom_qty': diff * sec_uom_qty_factor,
                            'uoi_qty': diff * uoi_qty_factor,
                            'picking_id': move.picking_id.id
                                   })
            
            if new_move:
                if move.state in ('waiting', 'done'):
                    new_move.wkf_waiting()
                    
                if move.state == 'done':
                    new_move.wkf_done()
        
        move.prioritizing()
        return new_move
    
    
    @api.multi
    def unprepare(self):
        move_label_rs = self.env['stock.move.label'].search([('move_id', 'in', self.ids)])
        if move_label_rs:
            move_label_rs.unlink()
        
        return True
    
    
    def create_move_label(self, label, qty, src_location, dest_location, sec_qty=None, move_rs=None, done=True):
        """
            Création d'un move_label et un mouvement de stock
            :type self: stock.move
            :param label: Étiquettes à affecter
            :type label: recordset: stock.label
            :param qty: Quantité de l'étiquette
            :type qty: float
            :param src_location: Emplacement source
            :type src_location: recordsets: stock.location
            :param dest_location: Emplacement de destination
            :type dest_location: recordset: stock.location
            :param done: Passage du mouvement à done si True
            :type done: bool
            :return: Mouvement créé
            :rtype: recordset: stock.move
        """
        if not move_rs:
            move_rs = self.create_move(label.product_id, src_location, dest_location, qty=qty, sec_qty=sec_qty, other_data={'valid_label':True})
        elif not move_rs.valid_label:
            move_rs.write({'valid_label': True}, with_covers=False)
            
        self.env['stock.move.label'].create({'move_id': move_rs.id, 
                                             'uom_qty': qty, 
                                             'sec_uom_qty': sec_qty, 
                                             'label_id': label.id})
        if done:
            move_rs.wkf_waiting()
            move_rs.wkf_done()
            
        return move_rs
    
        
    def get_attributes_const(self):
        res = {
            'product': self.product_id,
            'move': self,
            'picking': self.picking_id
               }

        return res
    
    
    def get_procurement(self):
        """
            Renvoie le procurement du mouvement ainsi que les procurement des mouvements du même historique
        """
        res = self.env['procurement.order']
        if self.history_id:
            for h_move in self.search([('history_id', '=', self.history_id.id)]):
                if h_move.procurement_id and h_move.procurement_id.state != 'cancel':
                    res |= h_move.procurement_id
                    
        else:
            res = self.procurement_id

        return res
    
    
    def manage_sale_purchase_qty(self):
        """
            Gestion des quantités livrées et restantes de la vente 
            ou de l'achat lié au move
            :type self: stock.move
            :param quantity: Quantité à retirer ou à ajouter
            :type quantity: float
            :param add: Si on doit ajouter la quantité ou l'enlever
            :type add: boolean
            :return: True
            :rtype: boolean
        """
        return True
    
    
    @api.multi
    def button_post_control_open(self):
        """
            Ouvre le post contrôle
            :type self: stock.move
            :return: True
            :rtype: bool
        """
        res = False
        move_rc = self[0]
        if move_rc.post_control_declaration_id:
            action = self.env.ref('stock.act_quality_control_declaration_reception_id')
            if action:
                res = action.read([])[0]
                res['res_id'] = move_rc.post_control_declaration_id.id
                if res.get('views'):
                    res['views'].reverse()
                    
        return res
    
    
    @api.multi
    def prioritizing(self):
        company = self.env.user.company_id
        sorting_date = company.cover_sorting_date
        for move in self:
            prev_move_rs = self.search([('product_id', '=', move.product_id.id), ('state', '=', 'waiting')], order='%s asc'%(sorting_date), limit=1)
            if prev_move_rs:
                prev_date = fields.Datetime.from_string(prev_move_rs[0][sorting_date])
                move.write({sorting_date: fields.Datetime.to_string(prev_date - timedelta(days=1))})
        
        return True
    
    
    @api.one
    def validate_label(self):
        """
            Vérifie la cohérence des quantités et valide les étiquettes si le mouvement est terminé
            :type self: stock.move
            :return: True
            :rtype: bool
        """
        vals = {'valid_label': True}
        move_label_ids = self.move_label_ids
        label_sum = move_label_ids and sum([move_label.uom_qty for move_label in move_label_ids]) or 0.0
        
        # Conversion qty en UdM produit si besoin
        move_qty = self.get_product_uom_qty()
        delta = float_compare(label_sum, move_qty, self.product_id.uom_id.rounding)
        if delta != 0:
            if delta == -1:
                raise except_orm(_('Error'), _('Sum of label quantities cannot be lower than move product quantity.'))
            else:
                raise except_orm(_('Error'), _('Sum of label quantities cannot be greater than move product quantity.'))

        # Seconde unité
        if self.is_variable_double_unit:
            sec_label_sum = move_label_ids and sum([move_label.sec_uom_qty for move_label in move_label_ids]) or 0.0
            sec_move_qty = self.get_product_sec_uom_qty()
            delta = float_compare(sec_label_sum, sec_move_qty, self.product_id.sec_uom_id.rounding)
            if delta != 0:
                if delta == -1:
                    raise except_orm(_('Error'), _('Sum of label second quantities cannot be lower than move product quantity.'))
                else:
                    raise except_orm(_('Error'), _('Sum of label second quantities cannot be greater than move product quantity.'))
        
        self.write(vals)
        if self.state == 'done': 
            move_label_ids.update_labels(self, 'done')
            
        return True
    
    
    def _prepare_procurement_from_move(self):
        datas = self.read(['product_id', 'date', 'trigger_supply', 'supply_method', 'is_forecast'], load='_classic_write')
        return {'product_id': datas[0]['product_id'], 
                'needed_date': datas[0]['date'], 
                'trigger_supply': datas[0]['trigger_supply'], 
                'supply_method': datas[0]['supply_method'], 
                'is_forecast': datas[0]['is_forecast'], 
                'user_id': self.env.user.id, 
                'move_id': self.id}


    def create_procurement_from_move(self, automatic_purchase=True, with_covers=True):
        """
            Création d'un procurement depuis un mouvement
        """
        vals = self._prepare_procurement_from_move()
        vals.update(self.update_procurement_vals())
        if self.supply_method == 'buy':
            vals['automatic'] = automatic_purchase
        else:
            vals['automatic'] = True
            
        proc_rs = self.env['procurement.order'].create(vals)
        if proc_rs:
            self.write({'procurement_id': proc_rs.id}, with_covers=with_covers)
            if proc_rs.automatic and not proc_rs.low_procurement:
                proc_rs.do_default_procurement() 
        
        return proc_rs
    
    
    def aggregate_move_quality(self):
        """
            Fonction qualité qui permet de merger les mouvement HS et quarantine avec le mouvement OK
        """
        
        uom_obj = self.env['product.uom']
        move_unlink_rcs = self.env['stock.move']
        move_rcs = self.env['stock.move']
        for move in self:
            if (move.move_quarantine_id or move.move_hs_id) and (move.control_declaration_id or move.post_control_declaration_id):
                if move.control_declaration_id and move.control_declaration_id.move_ids:
                    move_rcs |= move.control_declaration_id.move_ids
                    
                if move.post_control_declaration_id and move.post_control_declaration_id.post_move_ids:
                    move_rcs |= move.post_control_declaration_id.post_move_ids
                
                move_rcs -= move
                if move_rcs:
                    uom_qty = move.uom_qty
                    uom_qty_init = move.uom_qty or 1.0
                    for move_rc in move_rcs:
                        if move.state == 'cancel':
                            if move_rc.state != 'cancel':
                                move_rc.wkf_cancel()
                                
                            move_unlink_rcs += move_rc
                            uom_qty += move_rc.uom_qty
                    
                    if move.sec_uom_qty:
                        sec_uom_qty = uom_qty * move.sec_uom_qty / uom_qty_init
                    else:
                        sec_uom_qty = uom_obj._compute_qty_obj(move.uom_id, uom_qty, move.sec_uom_id, with_raise=False, with_round=False)
                    
                    if move.uoi_qty:
                        uoi_qty =  uom_qty * move.uoi_qty / uom_qty_init
                    else:
                        uoi_qty = uom_obj._compute_qty_obj(move.uom_id, uom_qty, move.uoi_id, with_raise=False, with_round=False)
                    
                    if uom_qty != uom_qty_init:
                        move.write({'uom_qty': uom_qty, 'sec_uom_qty': sec_uom_qty, 'uoi_qty': uoi_qty})
            
            if move.control_declaration_id and move.control_declaration_id.move_init_id == move:
                move.control_declaration_id.unlink()
            
            if move.post_control_declaration_id and move.post_control_declaration_id.move_init_id == move:
                move.post_control_declaration_id.unlink()
                
        return move_unlink_rcs
    
    
    def do_partial_picking(self, uom_qty, origin_move_rc=False):
        """
            Gestion des quantités livrées et restantes de la vente 
            ou de l'achat lié au move
            :type self: stock.move
            :param uom_qty: Quantité à traiter
            :type uom_qty: float
            :return: True
            :rtype: boolean
        """
        move = self
        if uom_qty and move.picking_id and move.uom_qty:
            factor =  uom_qty / move.uom_qty
            ctx = self.env.context.copy()
            ctx.update({'active_id': move.picking_id.id,
                         'active_ids': [move.picking_id.id],
                         'active_model': 'stock.picking'})
            partial_picking_rs = self.env['stock.partial.picking'].with_context(ctx).create({})
            for line in partial_picking_rs.line_ids:
                if line.move_id.id != move.id:
                    uom_qty = line.move_id.uom_qty * factor 
                    
                write_vals = {'uom_qty': uom_qty}
                write_vals.update(line.onchange_uom_qty(uom_qty))
                if line.move_id.id != move.id and move.id in self.env.context.get('transfer_move_scrap', []):
                    write_vals['manage_scrap'] = True
                    
                line.write(write_vals)
                
            partial_picking_rs.picking_id.do_partial(partial_picking_rs.line_ids, transfer_origin_move_rc=origin_move_rc)
                
        return True
    
    
    @api.multi
    def reopen(self):
        for move in self:
            ctx2 = self.env.context.copy()
            ctx2['reopen'] = True
            if move.state != 'cancel':
                move.with_context(ctx2).wkf_cancel()
            
            new_move_created, move = move.wkf_draft()
        
        return new_move_created, move
    

    @api.multi
    def wkf_draft_with_aggregate(self, move_already_compute=None):
        """
            Méthode à appeler si plusieurs ids dont certains à aggreger (Pour qualité)
        """
        if move_already_compute is None:
            move_already_compute = []
            
        move_to_draft = self
        for move in self:
            if move.id not in move_already_compute: 
                move_already_compute.append(move.id)
                move_unlink_rcs = move.aggregate_move_quality()
                if move_unlink_rcs:
                    move_to_draft -= move_unlink_rcs 
                    move_unlink_rcs.unlink()
                    return move_to_draft.wkf_draft_with_aggregate(move_already_compute=move_already_compute)
        
        return self.wkf_draft()
    
    
    def create_move_history(self, not_usable=False):
        for move in self.read(['product_id'], load='_classic_write'):
            self.env.cr.execute("""
            INSERT INTO 
              stock_move_history 
                (create_uid, create_date, product_id)
              VALUES
                (%d, now(), %d)
              RETURNING id
            """%(self.env.uid, move['product_id']))
            res = self.env.cr.fetchone()
            if res and res[0]:
                self.env.cr.execute("""
                    UPDATE
                      stock_move
                    SET
                      not_usable=%s,
                      history_id=%d
                    WHERE
                      id = %d
                """%(not_usable and 'true' or 'false', res[0], move['id']))
             
        return True
            
    
    @api.multi
    def wkf_draft_button(self):
        new_move_created, move = self.wkf_draft()
        res = True
        if new_move_created and move:
            action = self.env.ref('stock.act_move')
            if action:
                action = action.read()[0]
                action['views'] = []
                action['view_mode'] = 'form,tree'
                action['target'] = 'new'
                action['res_id'] = move.id
                res = action
                    
        return res
        
        
    @api.multi
    def wkf_draft(self):
        pickings = self.env['stock.picking']
        new_move_created = False
        move_rcs = self.env['stock.move']
        for move in self:
            if move.not_usable:
                raise except_orm(_('Error'), _('Impossible to make this stock move in state draft. An alternative stock move was already created'))
                
            #Partie qualité
            move_unlink_rcs = move.aggregate_move_quality()
            if move_unlink_rcs:
                move_unlink_rcs.unlink()

            if not self.env.context.get('without_duplicate', False) and move.type == 'out':
                if not move.history_id:
                    move.create_move_history()

                old_move = move
                move_tmp = move.with_context(copy_label=True).copy({'procurement_id': False, 'history_id': move.history_id.id})
                move_rcs |= move_tmp
                move = move_tmp
                old_move.write({'not_usable': True})
                new_move_created = True
            
            move.write({
                    'state': 'draft', 
                    'valid_label': False,
                    'initial_uom_qty': move.uom_qty,
                    'initial_sec_uom_qty': move.sec_uom_qty,
                    'initial_uoi_qty': move.uoi_qty,
                    'initial_uom_id': move.uom_id.id,
                    'initial_sec_uom_id': move.sec_uom_id.id,
                    'initial_uoi_id': move.uoi_id.id,
                    'is_recalculate_frequency_control': False
                        })
            # MAJ des quantités réservées (procurement)
            if move.type in ('in', 'out') and move.procurement_id:
                move.procurement_id.update_reserved_qtys()
                    
            if move.picking_id:
                pickings |= move.picking_id 
             
        if pickings:
            pickings.compute_date()
            pickings.compute_date_expected()
        
        return new_move_created, move_rcs


    def update_procurement_vals(self):
        return {}
    
    
    def get_common_attributes(self, label=None):
        """
            Méthode redéfinie par mrp et purchase pour avoir les attributs par défaut changés par 
            les ventes ou les achats.
        """
        if label:
            res = {x.name: x.value for x in label.attribute_ids}
        else:
            res = self.get_default_attributes()
            
        return res

    
    def get_default_attributes(self):
        """
            Méthode redéfinie par mrp et purchase pour avoir les attributs par défaut changés par 
            les ventes ou les achats.
        """
        return {x.name: x.default_value for x in self.product_id.get_common_attribute_ids()}
    
    
    def get_covers_type(self, move_vals=False):
        return 'normal'
    
    
    def update_warehouse(self, with_covers=False):
        if self.type == 'in':
            self.write({'warehouse_id': self.location_dest_id.warehouse_id.id}, with_covers=with_covers)
        else:
            self.write({'warehouse_id': self.location_id.warehouse_id.id}, with_covers=with_covers)
            
        return True
        
        
    def create_transfer_move(self, in_picking_rs=False):
        if not in_picking_rs:
            in_picking_rs = self.env['stock.picking'].create_picking('in', 
                                               partner=self.transfer_id.partner_id or self.env.user.company_id.partner_id, 
                                               date=self.transfer_id.need_date,
                                               other_data = {'invoice_state': self.transfer_id.is_billable and '2binvoiced' or 'none',
                                                             'is_partial': True,
                                                             'manage_scrap': True,
                                                             'is_automatic': self.transfer_id.is_automatic,
                                                             'origin': _('Transfer request')})
            
        move_id = self.copy({'location_id': self.location_dest_id.id,
                             'location_dest_id': self.transfer_id.warehouse_dest_id.input_location_id.id,
                             'type': 'in',
                             'transfer_move_id': False,
                             'transfer_id': self.transfer_id.id,
                             'out_transfer_move_id': self.id,
                             'subc_origin_move_id': self.subc_origin_move_id.id,
                             'picking_id': in_picking_rs.id})
        in_picking_rs.wkf_waiting()
        return move_id.id

    
    def need_procurement(self):
        """
        Le mouvement nécessite un procurement si il appartient à un picking ou un OT
        """
        if self.trigger_supply != 'make_to_order' or self.picking_id:
            res = True
        else:
            res = False
            
        return res
    
    
    def do_action_on_out_move_waiting(self):
        return True
    
    
    def do_action_on_out_move_cancel(self):
        return True
    
    
    def do_action_on_out_move_unlink(self):
        return True
    
    
    @api.multi
    def wkf_waiting(self, automatic_purchase=True):
        """
            Waiting du mouvement
        """
        # Verification qu'il n'y ai pas d'étiquettes déjà réservées
        if self.ids:
            self.env.cr.execute('''
                    SELECT
                      l.name
                    FROM 
                      stock_move_label sml
                      JOIN stock_label l ON sml.label_id = l.id
                    WHERE
                      sml.move_id IN %s AND
                      l.state = 'reserved' ''', (tuple(self.ids), ))
            already_reserved_label = self.env.cr.fetchall()  
            if already_reserved_label:
                raise except_orm(_('Error'), _('One or several labels are already reserved: %s')%(', '.join([x[0] for x in already_reserved_label])))
            
        self.write({'state': 'waiting'}, with_covers=False)
        for move in self:
            proc_rs = False
            # Entrepot
            move.update_warehouse()
                    
            if move.type == 'out':
                # Gestion des transferts (Bien laisser cette ligne avant proc_rs.update_cancel_procurement())
                if move.transfer_id and not move.transfer_move_id:
                    move.write({'transfer_move_id': move.create_transfer_move()})

                # Gestion des historiques (Bien laisser cette ligne avant proc_rs.update_cancel_procurement())
                if move.history_id and move.history_id.product_id.id != move.product_id.id:
                    self.write({'history_id': False})
                
                move.do_action_on_out_move_waiting()
                
            # Gestion du procurement
            if move.trigger_supply in ('make_to_order', 'make_to_order_with_stock') and move.type == 'out' and ((move.supply_method == 'buy' and move.warehouse_id.generate_procurement_buy) or (move.supply_method == 'produce' and move.warehouse_id.generate_procurement_produce)):
                # Si le mouvement a déjà un procurement
                # Read car sinon il browse tous les mouvements du self à chaque itération à cet endroit. Bug de l'ORM?
                proc_id = move.read(['procurement_id'], load='_classic_write')[0]['procurement_id']
                if proc_id:
                    proc_rs = self.env['procurement.order'].browse(proc_id)
                    # SI le movement à un procurement cancel
                    if move.procurement_id.state == 'cancel':
                        proc_rs.update_cancel_procurement()
                        
                    # Si il n'est pas cancel: le mouvement est rattaché au procurement
                    if not move.procurement_id.move_id or move.procurement_id.move_id.state == 'cancel':
                        move.procurement_id.write({'move_id': move.id})
                    
                # Sinon, création d'un procurement
                elif move.need_procurement():
                    proc_rs = move.create_procurement_from_move(automatic_purchase=automatic_purchase, with_covers=False)
                
                if proc_rs:
                    proc_rs.update_supply_procurement_deleted()
                    
            if move.type in ('in', 'out'): 
                # MAJ des quantités réservées (procurement)
                if not proc_rs:
                    proc_rs = move.procurement_id
                    
                if proc_rs:
                    proc_rs.update_reserved_qtys()
    
            # Impossible de faire un mouvement interne inter entrepot
            elif move.type == 'int':
                if move.location_id.warehouse_id.id != move.location_dest_id.warehouse_id.id:
                    raise except_orm(_('Error'), _('Impossible to move products directly from a warehouse to another.'))
                
            # Réservation des étiquettes
            if move.type != 'in':
                for move_label in move.move_label_ids:
                    move_label.label_id.wkf_reserved(move.location_id, move.id, move_label.uom_qty)
            
            move.manage_sale_purchase_qty()
            
        if self.ids:
            self.update_covers()
            
        return True
    
    
    def do_action_on_wkf_done(self):
        return True
    
    
    @api.multi
    def wkf_done(self):
        """
            État à done date à la date du jour, MAJ de stock_level et des étiquettes 
        """
        now = fields.Datetime.now()
        stock_level_obj = self.env['stock.level']
        for move in self:
            # Interdiction si prévisionnel:
            if move.is_forecast:
                raise except_orm(_('Error'), _('Impossible to make done a forecast stock move')) 
            
            # Interdiction de traiter un mouvement en double unité variable dont la seconde quantité est de 0:
            if not self.env.context.get('force_done') and move.type in ('in', 'out') and move.is_variable_double_unit and not move.sec_uom_qty:
                raise except_orm(_('Error'), _('Impossible to make done stock move of product %s: the second UoM quantity cannot be 0')%(move.product_id.name)) 
            
            # Interdiction si out, pas de dispo et pas admin:
            if move.type == 'out' and \
               self.env.user != self.sudo().env.user and \
               move.product_id.type == 'stockable' and \
               not self.env.context.get('force_done') and \
               float_compare(move.uom_qty, move.covered_by_stock_qty, self.env['decimal.precision'].precision_get('Product quantity')) > 0:
                raise except_orm(_('Error'), _('Impossible to make done an OUT stock move of product %s without stock quantity (Stock: %.2f, move: %.2f.)')%(move.product_id.name, move.covered_by_stock_qty, move.uom_qty)) 

            done_date = move.done_date or now
            # Contrainte qualité
            move.constraint_move_quality_wkf_done()
            # Conversion qty en UdM produit si besoin
            move_qty = move.get_product_uom_qty()
            move_sec_qty = move.get_product_sec_uom_qty()
            # MAJ du stock
            stock_level_obj.update_stock_level(move.product_id, move_qty, move_sec_qty, move.type, move.warehouse_id.id, 'done')

#             if move.product_id. and not move.valid_label
#                 raise except_orm(_('Error'), _('You must create/affect labels to move this product.')) 
            
            # MAJ des quantités réservées (procurement)
            if move.procurement_id:
                if move.type in ('in', 'out'):
                    move.procurement_id.update_reserved_qtys()
                    if move.type == 'out':
                        if not self.search([('id', '!=', move.id), 
                                            ('state', 'not in', ('done', 'cancel')),
                                            ('type', '=', 'out'),
                                            ('procurement_id', '=', move.procurement_id.id)], limit=1):
                            
                            move.procurement_id.wkf_done()
            
            # Déclaration de prod si move de soustraitance et que le produit est le produit final ou le int
            move.declaration_production('done')
            move.write({'state': 'done', 'date': done_date, 'availability': 100.0, 'color_priority_need': 0})
            if move.location_id.usage == 'view' or move.location_dest_id.usage == 'view':
                raise except_orm(_('Error'), _('Impossible to move products from or to a location of the type view.'))
            
            # Liste UM
            um_label_rcs = self.env['stock.label']
            # MAJ des étiquettes
            move_label_ids = move.move_label_ids
            if move_label_ids:
                if move.type == 'out':
                    for move_label_uc in move.move_label_ids:
                        um_label_rcs |= move_label_uc.label_id.um_label_id                    
                
                move_label_ids.write({'done_date': done_date})
                if not move.valid_label:
                    move.validate_label()
                else:
                    move_label_ids.update_labels(move, 'done')
            
            # Suppression de l'UM
            um_label_rcs.delete_um_labels()
            
            # Transfert
            if move.transfer_move_id and move.move_label_ids:
                if move.transfer_move_id.move_label_ids:
                    move.transfer_move_id.move_label_ids.unlink()
                    
                move.move_label_ids.copy({'move_id': move.transfer_move_id.id})

            if move.transfer_id:
                if move.type == 'in' and not move.transfer_id.is_automatic:
                    move_rs = self.search([('transfer_move_id', '=', move.id)], limit=1)
                    if not move_rs or move_rs.state != 'done':
                        raise except_orm(_('Error'), _('Impossible to make done an incoming warehouse transfer move without make done the outgoing move'))
                
                if move.transfer_id.is_automatic:
                    transfer_move_rs = False
                    origin_move_rc = False
                    # origin_move_rc est ajouté pour lié le reliquat du IN au reliquat du OUT en cas de transfert
                    # S'il n'est pas mis, le reliquat du OUT n'étant pas lié au reliquat du IN recrée un reliquat IN en double
                    # Context pour éviter une boucle (IN qui traite le OUT qui essaye de retraiter le IN, ....)
                    if not self.env.context.get('from_automatic_transfer'):
                        if move.type == 'in':
                            transfer_move_rs = self.search([('transfer_move_id', '=', move.id)], limit=1)
                            origin_move_rc = move
                        elif move.type == 'out':
                            transfer_move_rs = move.transfer_move_id
                        
                        if transfer_move_rs:
                            transfer_move_rs.with_context(from_automatic_transfer=True).do_partial_picking(move.uom_qty, origin_move_rc=origin_move_rc)
            
            # Qualité post 
            if move.product_id and (move.type == 'in' or move.type == 'int') and move.is_principal_quality:
                move.move_post_quality_wkf_done()
                
            # Calcule du prix théorique
            # TODO THOMAS: utilisation de purchase_line_id
            if move.type == 'in' and move.purchase_line_id:
                theo_price = move.compute_price_purchase_theo_move()
                move.write({'theo_price': theo_price})
                move.compute_price_theo_real_wosub()
            
            # Calcule de prix theo et reel dans les sous produits des ots
            move.compute_price_sub_product_move()
            move.manage_sale_purchase_qty()
            
            move.do_action_on_wkf_done()
            
        return True
    
    
    def compute_price_purchase_theo_move(self):
        """
            Fonction qui permet de calculer le prix théorique d'un mouvement entrant
            Pour les ots le prix est calculer dans la déclaration de prod ou le calcul de coût dans l'OF
        """
        move = self
        theo_price = 0
        # TODO THOMAS: utilisation de purchase_line_id
        if move.purchase_line_id:
            if move.product_id.cost_method =='supplier_pl':
                partner = move.purchase_line_id.purchase_partner_id
                currency_rs = move.currency_id
                sec_uom_id = move.sec_uom_id or False
                theo_price = move.product_id.get_price_purchase(partner, currency_price_return=currency_rs, qty_uop=move.sec_uom_qty, 
                                                               uop=sec_uom_id, type='price', state_dev=False)
            else:
                theo_price = move.product_id.purchase_cost_price
            
        return theo_price
    
    
    def compute_price_sub_product_move(self):
        """
            Fonction qui permet de calculer le prix théorique et réel dans les sous produits des ots
        """
        return True
    
    
    def compute_price_theo_real_wosub(self):
        """
            Fonction qui permet de calculer le prix théorique et réel d'un mouvement entrant de produit final d'un ot de soustraitance
        """
        return True
        
    
    def constraint_move_quality_wkf_done(self):
        """
            Fonction qui permet de vérifier que le controle qualité a été fait
            Elle est redéfinit dans le module MRP
        """
        move = self
        if move.type == 'in' and move.is_control_declaration_recep and not move.is_recalculate_frequency_control and not move.control_declaration_id and not move.no_control:
                raise except_orm(_('Error'), _('Please make a quality declaration for the product %s')%(move.product_id.name))
        elif move.type == 'in' and move.is_control_declaration_recep and move.control_declaration_id and not move.no_control:
            error_qty = False
            if Decimal(str(move.initial_uom_qty)) != Decimal(str(move.control_declaration_id.get_quantity('qty_ok')+move.control_declaration_id.get_quantity('qty_hs')+move.control_declaration_id.get_quantity('qty_quarantine'))):
                error_qty = True
                if move.control_declaration_id:
                    sum_qty = sum([x.uom_qty for x in move.control_declaration_id.move_ids])
                    if Decimal(str(sum_qty)) == Decimal(str(move.control_declaration_id.get_quantity('qty_ok')+move.control_declaration_id.get_quantity('qty_hs')+move.control_declaration_id.get_quantity('qty_quarantine'))):
                        error_qty = False

            if error_qty:
                raise except_orm(_('Error'), _('Please make a quality declaration for the product %s')%(move.product_id.name))
        
        return True
    
    
    def move_post_quality_wkf_done(self):
        """
            Fonction qui permet de générer la qualité post
            Elle est redéfinit dans le module MRP
        """
        move = self
        control_declaration_obj = self.env['quality.control.declaration']
        qcp_rcs = False
        type_declaration = 'post_reception'
        name_declaration = 'Post %s' %(move.name)
        if move.picking_id:
            name_declaration = '%s %s' %(move.picking_id.name, name_declaration)
            qcp_rcs = self.env['quality.control.product'].search([('type', '=', 'post_reception'), ('product_id', '=', move.product_id.id)])
            
        if qcp_rcs:
            nb_label = 0
            if move.move_label_ids:
                nb_label = len(move.move_label_ids.ids)
            
            partner_id = move.picking_id and move.picking_id.partner_id and move.picking_id.partner_id.id or False
            post_control_declaration_rcs = control_declaration_obj.generate_control_declaration(qcp_rcs, 
                                                                                                move.uom_qty, 
                                                                                                type_declaration=type_declaration, 
                                                                                                type_control=type_declaration, 
                                                                                                date=fields.Datetime.now(), 
                                                                                                name_declaration=name_declaration, 
                                                                                                move_init_rcs=move, 
                                                                                                product_rcs = move.product_id,
                                                                                                partner_id = partner_id, 
                                                                                                quantity_label=nb_label)
            if post_control_declaration_rcs:
                post_control_declaration_rcs.write({'qty_label': nb_label})
                move.write({'post_control_declaration_id': post_control_declaration_rcs.id})
            else:
                move.recalculate_frequency_quality_main(post_control=True)
                move.write({'is_recalculate_frequency_control': True})

        return True
    
    
    def recalculate_frequency_quality_main(self, post_control=False):
        move = self
        if ((move.control_declaration_id and not post_control) or (move.post_control_declaration_id and post_control)) and (move.type == 'in' or move.type == 'int'):
            controle_product_rcs = self.env['quality.control.product']
            controle_product_obj = self.env['quality.control.product']
            if move.post_control_declaration_id:
                control_declaration = move.post_control_declaration_id
            else:
                control_declaration = move.control_declaration_id    
                
            if control_declaration.product_id:
                product_declaration = control_declaration.product_id
                control_ids = [line.control_id.id for line in control_declaration.line_control_ids if line.control_id]
                if control_ids:
                    args_control_product = [('product_id', '=', product_declaration.id), ('control_id', 'in', control_ids)]
                    search_controle_product_rcs = controle_product_obj.search(args_control_product)
                    if search_controle_product_rcs:
                        controle_product_rcs |= search_controle_product_rcs
                      
            move.recalculate_frequency_quality(move.uom_qty, 
                                            controle_product_rcs=controle_product_rcs, 
                                            date=control_declaration.date, 
                                            control_declaration_rcs=control_declaration, 
                                            post_control=post_control)
                
        elif (move.type == 'in' or move.type == 'int'):
            controle_product_rcs = self.env['quality.control.product']
            partner_id = move.move_partner()
            for quality_control in move.product_id.quality_control_ids:
                if (not quality_control.partner_id or (partner_id and quality_control.partner_id.id != partner_id)) and quality_control.control_id:
                    controle_product_rcs |= quality_control

            if controle_product_rcs:
                move.recalculate_frequency_quality(move.uom_qty, 
                                                    controle_product_rcs=controle_product_rcs, 
                                                    date=False, 
                                                    control_declaration_rcs=False, 
                                                    post_control=post_control)
                
        return True
    
    
    def recalculate_frequency_quality(self, qty,  controle_product_rcs=False, date=False, control_declaration_rcs=False, post_control=False):
        """
            Fonction qui permet de recalculer les prochaines fréquences pour les controles qualités
            :param: move_id: Mouvement
            :type: move_id: int
            :return: Retourne True
            :rtype: True
        """
        if qty > 0:
            date_inter = date or fields.Datetime.now()
            for controle_product in controle_product_rcs:
                if (post_control and controle_product.type in ('post_reception', 'post_intern')) or (not post_control and controle_product.type not in ('post_reception', 'post_intern')):
                    if controle_product.control_id:
                        control = controle_product.control_id
                        if control.frequency_type == 'all':
                            remaining = 1 + controle_product.int_next_frequency
                            if remaining < 0:
                                int_next_frequency = remaining * -1
                            elif remaining == 0:
                                int_next_frequency = 0
                            else:
                                int_next_frequency = remaining % (controle_product.frequency_value or 1)
                            
                            controle_product.write({'int_next_frequency': int_next_frequency})
                        elif control.frequency_type in ('piece', 'label'):
                            quantity = qty
                            if control.frequency_type == 'label':
                                if control_declaration_rcs:
                                    quantity = control_declaration_rcs.qty_label
                                elif self.move_label_ids:
                                    quantity = len(self.move_label_ids)
                                else:
                                    quantity = 0
                            
                            remaining = quantity + controle_product.int_next_frequency
                            if remaining < 0:
                                int_next_frequency = remaining * -1
                            elif remaining == 0:
                                int_next_frequency = 0
                            else:
                                int_next_frequency = remaining % (controle_product.frequency_value or 1)
                            
                            controle_product.write({'int_next_frequency': int_next_frequency})   
                        elif control.frequency_date_type == 'date':
                            if control.frequency_date_type == 'hour':
                                type = 'hours'
                            elif control.frequency_date_type == 'day':
                                type = 'work_days'
                            elif control.frequency_date_type == 'week':
                                type = 'weeks'
                            else:
                                type = 'months'
                                
                            date = datetime.strptime(date_inter, DEFAULT_SERVER_DATETIME_FORMAT)
                            date += INTERVAL_TYPES[type](controle_product.frequency_value)
                            date_next_frequency = date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                            controle_product.write({'date_next_frequency': date_next_frequency})   
            
        return True
    
    
    def move_partner(self):
        if self.picking_id:
            partner_id = self.picking_id.partner_id and self.picking_id.partner_id.id or False
        else:
            partner_id = False
            
        return partner_id
    
            
    @api.multi
    def wkf_cancel_button(self):
        return self.wkf_cancel()
        
        
    @api.multi
    def wkf_cancel(self, with_cancel_picking=True, keep_dates=False, cancel_procurement=True):
        """
            État à cancel et update de stock_level et des étiquettes
        """
        pickings = self.env['stock.picking']
        control_declaration_obj = self.env['quality.control.declaration']
        for move in self:
            write_vals = {'state': 'cancel', 'is_confirmed': False, 'color_priority_need': 0}
            # MAJ des quantités réservées (procurement)
            update_reserved_qtys = False
            
            # 
            control_declaration_rcs = control_declaration_obj.search([('move_init_id', '=', move.id)])
            for control_declaration_rc in control_declaration_rcs:
                if control_declaration_rc.move_control_id:
                    control_declaration_rc.move_control_id.wkf_cancel()
                    control_declaration_rc.move_control_id.unlink()
                    
            if move.type in ('in', 'out') and move.procurement_id:
                update_reserved_qtys = True
                if move.type == 'out':
                    if cancel_procurement:
                        move.procurement_id.wkf_cancel()
                        
                    # Transfert
                    if move.transfer_move_id:
                        transfer_move_rs = self.search([('out_transfer_move_id', '=', move.id)])
                        if transfer_move_rs:
                            transfer_move_rs.wkf_cancel()
                            
                        write_vals['transfer_move_id'] = False
                        
            # Conversion qty en UdM produit si besoin
            move_qty = move.get_product_uom_qty()
            move_sec_qty = move.get_product_sec_uom_qty()
            if move.state == 'done':
                self.env['stock.level'].update_stock_level(move.product_id, move_qty, move_sec_qty, move.type, move.warehouse_id.id, 'cancel')
                move.move_label_ids.update_labels(move, 'cancel')
                if keep_dates:
                    write_vals['done_date'] = move.date
                else:
                    write_vals['done_date'] = False
                    
            elif move.state == 'waiting':
                for move_label in move.move_label_ids:
                    if move_label.label_id and move_label.label_id.state == 'reserved':
                        move_label.label_id.wkf_unreserved()
                
            if move.picking_id:
                pickings += move.picking_id 
        
            # Annulation Déclaration de prod si move de soustraitance et que le produit est le produit final ou le int que le move était done
            move.declaration_production('cancel')
            move.write(write_vals, with_covers=not update_reserved_qtys)
            
            if move.type in ('in', 'out'):
                move.do_action_on_out_move_cancel()
                move.product_id.cover_compute(covers_type=move.get_covers_type())
                if move.procurement_id and cancel_procurement:
                    move.procurement_id.update_reserved_qtys()
                
            if move.is_principal_quality and not self.env.context.get('reopen', False) and not self.env.context.get('reopen_picking', False):
                move.control_declaration_id.unlink()
                move.post_control_declaration_id.unlink()
            
            move.manage_sale_purchase_qty()
            
        if pickings:
            pickings.compute_date()
            pickings.compute_date_expected()
            if with_cancel_picking:
                pickings.check_cancel()
            
        return True 
    
    
    @api.model
    def create(self, vals):
        """
            Au create du mouvement: remplissage des quantités initiales
        """
        vals['initial_uom_qty'] = vals.get('uom_qty')
        vals['initial_sec_uom_qty'] = vals.get('sec_uom_qty')
        vals['initial_uoi_qty'] = vals.get('uoi_qty')
        vals['initial_uom_id'] = vals.get('uom_id')
        vals['initial_sec_uom_id'] = vals.get('sec_uom_id')
        vals['initial_uoi_id'] = vals.get('uoi_id')
        if vals.get('date', False):
            date = fields.Datetime.from_string(vals['date'])
        else:
            date = fields.Datetime.from_string(fields.Datetime.now())
        
        vals['month'] = date.month
        vals['year'] = date.year
        isocal = date.isocalendar()
        #On récupère le numéro de semaine
        if len(str(isocal[1])) == 1:
            week_number = '0%s'%(str(isocal[1]))
        else:
            week_number = str(isocal[1])
            
        vals['week'] = week_number
        
        res = super(stock_move, self).create(vals)
        if 'picking_id' in vals:
            picking = self.env['stock.picking'].browse(vals['picking_id'])
            picking.compute_date()
            picking.compute_date_expected()
        
        move_datas = res.read(['product_id', 'type'], load='_classic_write')[0]
        if move_datas and move_datas['product_id'] and (move_datas['type'] == 'in' or move_datas['type'] == 'int'):
            qcp_rcs = self.env['quality.control.product'].search([('type', 'in', ('reception', 'all')), ('product_id', '=', move_datas['product_id'])], limit=1)
            if qcp_rcs:
                res.write({'is_control_declaration_recep': True, 'is_recalculate_frequency_control': False, 'control_declaration_id': False, 'post_control_declaration_id': False})
        
        return res
    
    
    def get_write_query(self):
        return """
            SELECT
              sm.id as "id",
              sm.product_id as "product_id",
              sm.state as "state",
              sm.transfer_move_id as "transfer_move_id",
              sm.picking_id as "picking_id",
              proc.id as "procurement_id",
              proc.state as "procurement_state"
            FROM
              stock_move sm
              LEFT OUTER JOIN procurement_order proc ON sm.procurement_id = proc.id
            WHERE
              sm.id IN (%s)
        """
        
    
    @api.one
    def write(self, vals, with_covers=True, update_transfer_move=False):
        """
            Au write du mouvement: recalcul des couvertures
        """
        # MAJ du mois
        if 'date' in vals:
            if vals['date']:
                date = fields.Datetime.from_string(vals['date'])
                vals['month'] = date.month
                vals['year'] = date.year
                isocal = date.isocalendar()
                # Numéro de semaine
                if len(str(isocal[1])) == 1:
                    week_number = '0%s'%(str(isocal[1]))
                else:
                    week_number = str(isocal[1])
                    
                vals['week'] = week_number
                
            else:
                vals['month'] = ''
                vals['year'] = ''
                vals['week'] = ''
        
        if 'partner_price' in vals and self.state == 'done':
            if self.company_id and self.company_id.limit_modif_move > self.date:
                raise except_orm(_('Error'), _('Yyou can not modify the movement because modification deadline is %s.')%(self.date))
            
        res = super(stock_move, self).write(vals)
        self.env.cr.execute(self.get_write_query(), tuple(self.ids, ), )
        move_vals = self.env.cr.dictfetchone()
#         if with_covers and ('state' in vals or self.read(['state'])[0]['state'] == 'waiting'):
        if with_covers and ('state' in vals or move_vals['state'] == 'waiting'):
            if 'location_id' in vals and 'location_dest_id' in vals:
                covers_type = False
            else:
                covers_type = self.get_covers_type(move_vals)
                
            self.env['product.product'].browse(move_vals['product_id']).cover_compute(covers_type=covers_type)

        if 'date' in vals:
            # MAJ de la date de besoin du procurement
            if vals.get('procurement_id'):
                procurement = self.env['procurement.order'].browse(vals['procurement_id'])
                procurement_id = procurement.id
                procurement_state = procurement.state
            elif 'procurement_id' not in vals and move_vals['procurement_id']:
                procurement = self.env['procurement.order'].browse(move_vals['procurement_id'])
                procurement_id = move_vals['procurement_id']
                procurement_state = move_vals['procurement_state']
            else:
                procurement = False
                procurement_id = False
                procurement_state = False
            
            if procurement_id and procurement_state in ('draft', 'exception'):
                procurement.write({'needed_date': vals['date']})
                
            # MAJ de la date du picking
            date_pickings = self.env['stock.picking']
            if vals.get('picking_id'):
                date_pickings += self.env['stock.picking'].browse(vals['picking_id'])
            else:
                if move_vals['picking_id']:
                    date_pickings += self.env['stock.picking'].browse(move_vals['picking_id'])
            
            date_pickings.compute_date()

        if 'date_expected' in vals or vals.get('state') or vals.get('picking_id'):
            date_expected_pickings = self.env['stock.picking']
            if vals.get('picking_id'):
                date_expected_pickings += self.env['stock.picking'].browse(vals['picking_id'])
            else:
                if move_vals['picking_id']:
                    date_expected_pickings += self.env['stock.picking'].browse(move_vals['picking_id'])
                
                date_expected_pickings.compute_date_expected()
                        
        # Transfert
        if update_transfer_move:
            if move_vals['transfer_move_id']:
                transfer_move_id = self.browse(move_vals['transfer_move_id'])
                if transfer_move_id.state == 'waiting':
                    transfer_move_id.wkf_cancel(with_cancel_picking=False)
                    transfer_move_id.wkf_draft()
                    transfer_move_id.write(vals)
                    transfer_move_id.wkf_waiting()
            
        return res
    
    
    @api.multi
    def unlink(self):
        for move in self:
            if move.state not in ('draft', 'cancel'):
                raise except_orm(_('Error'), _('Impossible to delete a stock move if its state is not draft or cancel.'))

            if move.type == 'out': 
                move.do_action_on_out_move_unlink()
                if move.procurement_id:
                    move.procurement_id.unlink(with_raise=True)
            
        return super(stock_move, self).unlink()
   
   
    @api.multi
    def copy(self, default=None):
        """
            À la copie du mouvement, changement du mois par rapport à la date
        """
        if not default:
            default = {}
            
        if not self.env.context.get('copy_label', False) and 'move_label_ids' not in default:
            default['move_label_ids'] = []
            
        if default.get('date', False):
            date = fields.Datetime.from_string(default['date'])
            default['month'] = date.month
            default['year'] = date.year
            isocal = date.isocalendar()
            #On récupère le numéro de semaine
            if len(str(isocal[1])) == 1:
                week_number = '0%s'%(str(isocal[1]))
            else:
                week_number = str(isocal[1])
                
            default['week'] = week_number
           
        return super(stock_move, self).copy(default=default)
    
    
    
    def declaration_production(self, future_state):
        """
            Fonction de déclaration de prod si move ST
        """
        return True
    
    
    def create_move(self, product, src_location=False, dst_location=False, qty=0, uom=None, sec_qty=None, sec_uom=None, type=False, date=False, other_data=None, picking=False, partner=False, with_price=False, in_product_uom=False, warehouse_rs=False, label_rcs=False):
        """
            Création d'un mouvement avec les valeurs par défaut récupérées par les onchange
            :type self: stock.move
            :param product_id: Produit du mouvement
            :type product_id: recordset: product.product
            :param src_location: id de l'emplacement source
            :type src_location: integer
            :param dst_location: id de l'emplacement de destination
            :type dst_location: integer
            :param qty: Quantité du mouvement
            :type qty: float
            :param uom: UdM de qty
            :type uom: recordset: product.uom
            :param sec_qty: Seconde quantité du mouvement (Pour les produits variables)
            :type sec_qty: float
            :param sec_uom: Second UdM (Pour les produits variables)
            :type sec_uom: recordset: product.uom
            :param type: Type (in ou out)
            :type type: string
            :param date: Date optionnel. Date entrée dans date prévue, date et date de priorité
            :type date: string au format '%Y-%m-%d %H:%M:%S' ou '%Y-%m-%d'
            :param other_data: Type (in ou out)
            :type other_data: string
            :param picking: Picking auquel le mouvement est attaché
            :type picking: recordset: stock.picking
            :param in_product_uom: Paramètre qui permet de créer le mouvement dans l'unité du produit
            :type in_product_uom: boolean param
            :param label_rcs: Étiquettes à affecter au mouvement
            :type label_rcs: recordset: stock.move
            :return: Mouvement créé
            :rtype: recordset: stock.move
        """
        if product:
            if not src_location and type:
                src_location = self.with_context(picking_type=type)._default_location_id(warehouse_rs=warehouse_rs)
            
            if not src_location:
                raise except_orm(_('Error'), _('Cannot create stock move without src location.'))
                
            if not dst_location and type:
                dst_location = self.with_context(picking_type=type)._default_location_dest_id(warehouse_rs=warehouse_rs)
                
            if not dst_location:
                raise except_orm(_('Error'), _('Cannot create stock move without dest location.'))
            
            # Mise à jour des UoM avec le onchange du produit
            vals = self.onchange_product_id(product.id, type)
            vals['product_id'] = product.id
            vals['location_id'] = src_location
            vals['location_dest_id'] = dst_location
            
            if date:
                vals['date'] = date
                vals['date_expected'] = date
                vals['priority_date'] = date
                
            if picking:
                vals['picking_id'] = picking.id
            
            if uom is None:
                uom = product.uom_id
                vals['uom_id'] = uom.id
            
            if in_product_uom:
                if uom.id == product.uom_id.id:
                    vals['uom_qty'] = qty
                else:
                    vals['uom_qty'] = self.env['product.uom']._compute_qty_obj(uom, qty, product.uom_id, with_raise=True, with_round=False)
                    uom = product.uom_id
                    vals['uom_id'] = uom.id
                    
            else:
                vals['uom_qty'] = qty
                
            uoms_and_qtys = product.get_uoms_and_qtys(vals['uom_qty'], 
                                      uom_id=uom, 
                                      sec_uom_id=False, 
                                      uoi_id=False, 
                                      by_field='uom', 
                                      type=type,
                                      dual_unit=product.dual_unit, 
                                      dual_unit_type=product.dual_unit_type, 
                                      factor=1.0, 
                                      divisor=1.0,
                                      partner=partner,
                                      with_raise=True,
                                      with_factor=True,
                                      with_pinfo=True)
            for k, v in uoms_and_qtys.iteritems():
                vals[k] = v
            
            # Gestion de la double unité variable
            if sec_qty is not None:
                vals['sec_uom_qty'] = sec_qty
                if sec_uom is None:
                    sec_uom = product.sec_uom_id
                    
                vals['sec_uom_id'] = sec_uom.id
                qtys = product.get_qtys(sec_qty, 
                                        uom_id=vals['uom_id'], 
                                        sec_uom_id=sec_uom, 
                                        uoi_id=vals['uoi_id'], 
                                        by_field='sec_uom', 
                                        dual_unit=product.dual_unit, 
                                        dual_unit_type=product.dual_unit_type, 
                                        factor=1.0, 
                                        divisor=1.0, 
                                        with_raise=True)
                
                for k, v in qtys.iteritems():
                    vals[k] = v
            
            if with_price and 'sec_uom_qty' in vals and 'sec_uom_id' in vals:
                if type == 'in':
                    if not partner:
                        partner = vals.get('sinfo_id', False) and vals['sinfo_id'].partner_id or False
                        
                    currency_rs = partner and partner.currency_id or False
                    if currency_rs:
                        vals['currency_id'] = currency_rs.id
                        
                    vals['partner_price'] = product.get_price_purchase(partner, currency_price_return=currency_rs, qty_uop=vals['sec_uom_qty'], 
                                                               uop=vals['sec_uom_id'], type='price', state_dev=False)
                elif type == 'out':
                    if not partner:
                        partner = vals.get('cinfo_id', False) and vals['cinfo_id'].partner_id or False
                    
                    currency_rs = partner and partner.currency_id or False
                    if currency_rs:
                        vals['currency_id'] = currency_rs.id
                        
                    vals['partner_price'] = product.get_price_sale(partner, currency_price_return=currency_rs, qty_uos=vals['sec_uom_qty'], uos=vals['sec_uom_id'], type='price')
                
            # Transforme les recordset en ids
            vals = utils.transform_to_ids(self, vals)
            
            if other_data:
                vals.update(other_data)
                if 'currency_id' in vals:
                    vals['freight_currency_id'] = vals['currency_id']

            res = self.create(vals)
            if res and label_rcs:
                self.env['stock.move.label'].create_move_label(label_rcs, move_rs=res)
                
        else:
            raise except_orm(_('Error'), _('Cannot create stock move without a product.'))
    
        return res
        
        
    def create_move_scanner(self, product_id, src_location, dst_location, qty=0, uom=None):
        """
            Création d'un mouvement avec les valeurs par défaut récupérées par les onchange
            :type self: stock.move
            :param product_id: Produit du mouvement
            :type product_id: recordset: product.product
            :param src_location: id de l'emplacement source
            :type src_location: integer
            :param dst_location: id de l'emplacement de destination
            :type dst_location: integer
            :param qty: Quantité du mouvement
            :type qty: float
            :param uom: UdM de qty
            :type uom: recordset: product.uom
            :return Type du mouvement (in (entrant), out (sortant), ext (externe) ou int (interne))
            :rtype string
        """
        if product_id and src_location and dst_location:
            product_obj = self.env['product.product']
            
            # onchange product_id
            vals = self.onchange_product_id(product_id)
            vals['product_id'] = product_id
            vals['location_id'] = src_location
            vals['location_dest_id'] = dst_location
            
            product_rs = product_obj.browse(product_id)
            if uom is None:
                uom = product_rs.uom_id
                vals['uom_id'] = uom.id
            
            vals['uom_qty'] = qty
            # onchange qty uom
            qtys = product_rs.get_qtys(vals['uom_qty'], 
                             uom_id=uom, 
                             sec_uom_id=vals.get('sec_uom_id', False), 
                             uoi_id=vals.get('uoi_id', False), 
                             by_field='uom', 
                             dual_unit=product_rs.dual_unit, 
                             dual_unit_type=product_rs.dual_unit_type, 
                             factor=1.0, 
                             divisor=1.0,
                             with_raise=True)
            for k, v in qtys.iteritems():
                if k in ('uop_id', 'uos_id'):
                    vals['sec_uom_id'] = v
                else:
                    vals[k] = v
                    
            # onchange sec_uom_qty
            qtys = product_rs.get_qtys(vals['sec_uom_qty'], 
                             uom_id=uom, 
                             sec_uom_id=vals.get('sec_uom_id', False), 
                             uoi_id=vals.get('uoi_id', False), 
                             by_field='sec_uom', 
                             dual_unit=product_rs.dual_unit, 
                             dual_unit_type=product_rs.dual_unit_type, 
                             factor=1.0, 
                             divisor=1.0,
                             with_raise=True)
            for k, v in qtys.iteritems():
                if k in ('uop_id', 'uos_id'):
                    vals['sec_uom_id'] = v
                else:
                    vals[k] = v
            
            # transform recordset to ids
            vals = utils.transform_to_ids(self, vals)

            res = self.create(vals)
        
        else:
            raise except_orm(_('Error'), _('Cannot create stock move without a product.'))
    
        return res

    
    def split_light(self, coeff, wo_rest_qty=0, wo_new_qty=0, component_done_qty=0, new_wo_incoming_rcs= False, new_wo_outgoing_rcs=False, force_type_variable=False, wo_rcs=False, sec_uom_qty=0, modify_init_qtys=False):
        """
            Split des mouvements de productions ( composants ou produit de fab ou sous produit)
            :type self: Liste des recordset des mouvements
            :param coeff: Le coefficient diviseur pour la division du mouvement
            :type coeff: Float
            :return: Un dico contenant la liste des recordset des mouvements modifiés et des mouvements créés
            :rtype: dico contenant move_rcs':Liste recordset stock.move et'new_move_rcs':Liste recordset stock.move
        """
        move_dic = {'move_rcs':False, 'new_move_rcs':False}
        bom_obj = self.env['mrp.bom']
        uom_obj = self.env['product.uom']
        for move in self:
            if coeff > 0: 
                if move.type_qty == 'formula' and not force_type_variable and move.parameter_ids:   
                    parameter_rcs = move.parameter_ids[0]
                    # Calcul uom_qty
                    wo_product_rcs = wo_rcs and wo_rcs.final_product_id or move.product_id
                    new_uom_qty, efficient_new_uom_qty = bom_obj.compute_qty_component(parameter_rcs.qty_component, parameter_rcs.round_component, parameter_rcs.eff_component, 
                                                                                       parameter_rcs.qty_bom, wo_new_qty, parameter_rcs.type_component, 
                                                                                       formula= parameter_rcs.formula_component, args_parameters_list=[('mo_id', '=', wo_rcs.mo_id.id)])
                    coeff_new_qty = new_uom_qty and move.uom_qty / new_uom_qty or move.uom_qty
                    rest_uom_qty, efficient_rest_uom_qty = bom_obj.compute_qty_component(parameter_rcs.qty_component, parameter_rcs.round_component, parameter_rcs.eff_component, 
                                                                                         parameter_rcs.qty_bom, wo_rest_qty, parameter_rcs.type_component, 
                                                                                         formula= parameter_rcs.formula_component, args_parameters_list=[('mo_id', '=', wo_rcs.mo_id.id)])
                    coeff_rest_qty = rest_uom_qty and move.uom_qty / rest_uom_qty or move.uom_qty
                    
                    # Calcul sec_uom_qty
                    # Si double unité variable
                    if move.is_variable_double_unit:
                        new_sec_uom_qty = sec_uom_qty
                        rest_sec_uom_qty = 0
                    else:
                        new_sec_uom_qty = move.sec_uom_qty/coeff_new_qty
                        rest_sec_uom_qty = move.sec_uom_qty - new_sec_uom_qty
                    # Calcul uoi_qty
                    # Si double unité variable
                    if move.is_variable_double_unit:
                        new_uoi_qty = uom_obj._compute_qty_obj(move.sec_uom_id, new_sec_uom_qty, move.uoi_id)
                        rest_uoi_qty = 0
                    else:
                        new_uoi_qty = move.uoi_qty/coeff_new_qty
                        rest_uoi_qty = move.uoi_qty - new_uoi_qty
                    
                elif move.type_qty == 'variable' or (move.type_qty == 'formula' and force_type_variable):
                    # Calcul uom_qty
                    new_uom_qty = move.uom_qty/coeff
                    if coeff == 1:
                        new_uom_qty = coeff
                    
                    rest_uom_qty = move.uom_qty - new_uom_qty
                    # Calcul sec_uom_qty
                    # Si double unité variable
                    if move.is_variable_double_unit:
                        new_sec_uom_qty = sec_uom_qty
                        rest_sec_uom_qty = 0
                    else:
                        new_sec_uom_qty = move.sec_uom_qty/coeff
                        if coeff == 1:
                            new_sec_uom_qty = coeff
                        rest_sec_uom_qty = move.sec_uom_qty - new_sec_uom_qty
                    # Calcul uoi_qty
                    if move.is_variable_double_unit:
                        new_uoi_qty = uom_obj._compute_qty_obj(move.sec_uom_id, new_sec_uom_qty, move.uoi_id)
                        rest_uoi_qty = 0
                    else:
                        new_uoi_qty = move.uoi_qty/coeff
                        if coeff == 1:
                            new_uoi_qty = coeff
                        rest_uoi_qty = move.uoi_qty - new_uoi_qty
                
                else:
                    # Calcul uom_qty
                    new_uom_qty = move.uom_qty
                    rest_uom_qty = move.uom_qty
                    # Calcul sec_uom_qty
                    new_sec_uom_qty = move.sec_uom_qty
                    rest_sec_uom_qty = move.sec_uom_qty
                    # Calcul uoi_qty
                    new_uoi_qty = move.uoi_qty
                    rest_uoi_qty = move.uoi_qty
                    
                # Modification du move
                write_vals = {'uom_qty': new_uom_qty,
                              'sec_uom_qty': new_sec_uom_qty,
                              'uoi_qty': new_uoi_qty}
                if modify_init_qtys:
                    write_vals.update({'initial_uom_qty': new_uom_qty,
                                       'initial_sec_uom_qty': new_sec_uom_qty,
                                       'initial_uoi_qty': new_uoi_qty})
                    
                move.write(write_vals)
                
                # Creation du nouveau move
                vals = {'uom_qty': rest_uom_qty,
                        'sec_uom_qty': rest_sec_uom_qty,
                        'uoi_qty': rest_uoi_qty}
                if new_wo_incoming_rcs:
                    vals['wo_incoming_id'] = new_wo_incoming_rcs.id
                
                if new_wo_outgoing_rcs:
                    vals['wo_outgoing_id'] = new_wo_outgoing_rcs.id
                    
                ctx2 = self.env.context.copy()
                if 'default_type' in ctx2:
                    del ctx2['default_type']
                    
                new_move_rcs = move.with_context(ctx2).copy(vals)
                if new_wo_incoming_rcs and new_wo_incoming_rcs.state != 'draft' or new_wo_outgoing_rcs and new_wo_outgoing_rcs.state != 'draft':
                    new_move_rcs.wkf_waiting()
                
                # Remplir dico
                if move_dic['move_rcs']:
                    move_dic['move_rcs'] += move
                else:
                    move_dic['move_rcs'] = move
                
                if move_dic['new_move_rcs']:
                    move_dic['new_move_rcs'] += new_move_rcs
                else:
                    move_dic['new_move_rcs'] = new_move_rcs
            
        return move_dic
    
    
    @api.multi
    def change_product(self, product_id):
        old_state = self.state
        self.reopen()
        self.write({'product_id': product_id})
        self._onchange_product_id()
        if self.state != old_state:
            self.wkf_waiting()
            if self.state != old_state:
                self.wkf_done()
    
    
    def split_move_ok_hs_quarantine(self, qty_ok, qty_hs, qty_quarantine, sec_qty_ok=0, sec_qty_hs=0, sec_qty_quarantine=0, post_quality=False):
        move_ok_rcs = False
        move_hs_rcs = False
        move_quarantine_rcs = False
        uom_obj = self.env['product.uom']
        qty_move = self.uom_qty
        if (qty_ok or qty_hs or qty_quarantine) and qty_move:
            if Decimal(str(qty_move)) != Decimal(str(qty_ok + qty_hs + qty_quarantine)):
#                 error_qty = True
                if self.control_declaration_id:
                    sum_qty = sum([x.uom_qty for x in self.control_declaration_id.move_ids])
                    if not(Decimal(str(sum_qty)) == Decimal(str(qty_ok + qty_hs + qty_quarantine))):
                        qty_ok = sum_qty - (qty_hs + qty_quarantine)
                        
#                 if error_qty:
#                     raise except_orm(_('Error'), _('The stock move quantity is not equal to the sum of the OK, HS and quarantine quantities.'))
            
            if qty_ok == qty_move:
                move_ok_rcs = self
            elif qty_hs == qty_move:
                move_hs_rcs = self
            elif qty_quarantine == qty_move:
                move_quarantine_rcs = self
            else:
                if qty_ok:
                    dico_move_inter = self.split_light(qty_move/qty_ok, force_type_variable=True, sec_uom_qty=sec_qty_ok, modify_init_qtys=True)
                    move_ok_rcs = dico_move_inter['move_rcs']
                    if qty_quarantine:
                        if qty_quarantine == dico_move_inter['new_move_rcs'].uom_qty:
                            move_quarantine_rcs = dico_move_inter['new_move_rcs']
                            vals_move_quarantine_rcs = {'is_principal_quality': False}
                            if move_quarantine_rcs.is_variable_double_unit:
                                vals_move_quarantine_rcs['sec_uom_qty'] = sec_qty_quarantine
                                vals_move_quarantine_rcs['uoi_qty'] = uom_obj._compute_qty_obj(move_quarantine_rcs.sec_uom_id, sec_qty_quarantine, move_quarantine_rcs.uoi_id)
                                
                            move_quarantine_rcs.write(vals_move_quarantine_rcs)
                        else:
                            dico_move_inter2 = dico_move_inter['new_move_rcs'].split_light(dico_move_inter['new_move_rcs'].uom_qty/qty_quarantine, force_type_variable=True, sec_uom_qty=sec_qty_quarantine, modify_init_qtys=True)
                            move_quarantine_rcs = dico_move_inter2['move_rcs']
                            move_quarantine_rcs.write({'is_principal_quality': False})
                            move_hs_rcs = dico_move_inter2['new_move_rcs']
                            vals_move_hs_rcs = {'is_principal_quality': False}
                            if move_hs_rcs.is_variable_double_unit:
                                vals_move_hs_rcs['sec_uom_qty'] = sec_qty_hs
                                vals_move_hs_rcs['uoi_qty'] = uom_obj._compute_qty_obj(move_hs_rcs.sec_uom_id, sec_qty_hs, move_hs_rcs.uoi_id)
                            
                            move_hs_rcs.write(vals_move_hs_rcs)
                    else:
                        move_hs_rcs = dico_move_inter['new_move_rcs']
                        vals_move_hs_rcs = {'is_principal_quality': False}
                        if move_hs_rcs.is_variable_double_unit:
                            vals_move_hs_rcs['sec_uom_qty'] = sec_qty_hs
                            vals_move_hs_rcs['uoi_qty'] = uom_obj._compute_qty_obj(move_hs_rcs.sec_uom_id, sec_qty_hs, move_hs_rcs.uoi_id)
                        
                        move_hs_rcs.write(vals_move_hs_rcs)
                
                else:
                    dico_move_inter = self.split_light(qty_move/qty_quarantine, force_type_variable=True, sec_uom_qty=sec_qty_quarantine, modify_init_qtys=True)
                    move_quarantine_rcs = dico_move_inter['move_rcs']
                    move_hs_rcs = dico_move_inter['new_move_rcs']
                    vals_move_hs_rcs = {'is_principal_quality': False}
                    if move_hs_rcs.is_variable_double_unit:
                        vals_move_hs_rcs['sec_uom_qty'] = sec_qty_hs
                        vals_move_hs_rcs['uoi_qty'] = uom_obj._compute_qty_obj(move_hs_rcs.sec_uom_id, sec_qty_hs, move_hs_rcs.uoi_id)
                    
                    move_hs_rcs.write(vals_move_hs_rcs)
                
                if self.track_label_product and move_quarantine_rcs and move_ok_rcs:
                    move_label_ids = [x.id for x in move_ok_rcs.move_label_ids if x.for_quarantine]
                    if move_label_ids:
                        self.env['stock.move.label'].browse(move_label_ids).write({'move_id': move_quarantine_rcs.id})
        
        if move_hs_rcs and move_hs_rcs.state == 'draft':
            if move_hs_rcs.company_id and move_hs_rcs.company_id.warehouse_id.hs_location_id:
                name_hs = _('HS')
                name = '%s %s' %(move_hs_rcs.product_id.name, name_hs)
                vals_hs = {'location_dest_id': move_hs_rcs.company_id.warehouse_id.hs_location_id.id, 'name': name}
                if post_quality and move_ok_rcs:
                    vals_hs['location_id'] = move_ok_rcs.location_dest_id.id
                    
                move_hs_rcs.write(vals_hs)
            else:
                raise except_orm(_('Error'), _('No HS location in company.'))
        
        if move_quarantine_rcs and move_quarantine_rcs.state == 'draft':
            if move_quarantine_rcs.company_id and move_quarantine_rcs.company_id.warehouse_id.quarantine_location_id:
                name_quarantine = _('Quarantine')
                name = '%s %s' %(move_quarantine_rcs.product_id.name, name_quarantine)
                vals_quarantine = {'location_dest_id': move_quarantine_rcs.company_id.warehouse_id.quarantine_location_id.id, 'name': name}
                if post_quality and move_ok_rcs:
                    vals_quarantine['location_id'] = move_ok_rcs.location_dest_id.id
                    
                move_quarantine_rcs.write(vals_quarantine)
            else:
                raise except_orm(_('Error'), _('No Quarantine location in company.'))
            
        return move_ok_rcs, move_hs_rcs, move_quarantine_rcs
    
    
    @api.multi
    def create_declaration(self):
        control_declaration_obj = self.env['quality.control.declaration']
        for move in self:
            if move.control_declaration_id:
                control_declaration_rcs = move.control_declaration_id
            else:
                name_declaration = '%s' %(move.name)
                if move.picking_id:
                    name_declaration = '%s %s' %(move.picking_id.name, name_declaration)
                
                partner_id = move.picking_id and move.picking_id.partner_id and move.picking_id.partner_id.id or False
                quality_control_ids = move.product_id.quality_control_ids
                control_declaration_rcs = control_declaration_obj.generate_control_declaration(quality_control_ids, 
                                                                                               move.uom_qty, 
                                                                                               type_declaration='reception', 
                                                                                               type_control='reception', 
                                                                                               date=fields.Datetime.now(), 
                                                                                               name_declaration=name_declaration, 
                                                                                               move_init_rcs=move, 
                                                                                               partner_id = partner_id,
                                                                                               product_rcs=move.product_id)
            
                if control_declaration_rcs:
                    move.write({'control_declaration_id': control_declaration_rcs.id})
                else:
                    move.recalculate_frequency_quality_main(post_control=False)
                    move.write({'is_recalculate_frequency_control': True})
            
            if control_declaration_rcs:
                ctx2 = self.env.context.copy()
                ctx2['type_control_all'] = control_declaration_rcs.type_control
                return {
                        'name': _('Quality Control Declaration'),
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'quality.control.declaration',
                        'type': 'ir.actions.act_window',
                        'target': 'stack',
                        'res_id': control_declaration_rcs.id,
                        'nodestroy': True,
                        'context': ctx2
                        }
            else:
                msg = _('No quality control statement to make for this reception')
                return self.env['message.wizard'].create_message(msg=msg)
        return True
    
    
    
class stock_warehouse(models.Model):
    """
    Stock warehouse
    """
    _inherit = 'stock.warehouse'
    #===========================================================================
    # COLUMNS
    #===========================================================================
    stock_location_id = fields.Many2one('stock.location', string='Default stock location', required=False, ondelete='restrict', default=lambda self: self.env.ref('stock_location.location_stock'))
    input_location_id = fields.Many2one('stock.location', string='Input location', required=False, ondelete='restrict', default=lambda self: self.env.ref('stock_location.location_stock'))
    delivery_location_id = fields.Many2one('stock.location', string='Delivery location', required=False, ondelete='restrict', default=lambda self: self.env.ref('stock_location.location_stock'))
    service_location_id = fields.Many2one('stock.location', string='Service location', required=False, ondelete='restrict')
    quarantine_location_id = fields.Many2one('stock.location', string='Quarantine location', required=False, ondelete='restrict')
    control_location_id = fields.Many2one('stock.location', string='Control location', required=False, ondelete='restrict')
    hs_location_id = fields.Many2one('stock.location', string='Scrap location', required=False, ondelete='restrict')
    customer_location_id = fields.Many2one('stock.location', string='Customer location', required=False, ondelete='restrict', default=lambda self: self.env.ref('stock_location.stock_location_customers'))
    supplier_location_id = fields.Many2one('stock.location', string='Supplier location', required=False, ondelete='restrict', default=lambda self: self.env.ref('stock_location.stock_location_suppliers'))
    generate_procurement_produce = fields.Boolean(string='Generate procurement (produce)', default=True, help='If this field is checked, OUT stock moves of produce product will generate a procurement order')
    generate_procurement_buy = fields.Boolean(string='Generate procurement (buy)', default=True, help='If this field is checked, OUT stock moves of buy product will generate a procurement order')
    included_into_the_stock = fields.Boolean(default=True, help='If this field is checked, the stock level of this warehouse will be included at the total stock level')
    included_into_the_valorization = fields.Boolean(default=True, help='If this field is checked, the stock level of this warehouse will be included at the stock valorization')
    is_produce_directly_storage = fields.Boolean(string='Produce directly in the storage location', default=False)
    is_consume_directly_storage = fields.Boolean(string='Consume directly in the storage location', default=False)
    is_receipt_directly_storage = fields.Boolean(string='Receipt directly in the storage location', default=False)
    
    
    @api.model
    def create(self, vals):
        warehouse = super(stock_warehouse, self).create(vals)
        # Remplissage de la table stock level pour cet entrepot (SQL pour perf)
        self.env.cr.execute("""
            INSERT INTO
              stock_level 
              (create_date, create_uid, product_id, warehouse_id, uom_qty, sec_uom_qty) 
              (SELECT now(), %s, id, %s, 0.0, 0.0 FROM product_product)"""%(self.env.user.id, warehouse.id))
        return warehouse
    
    
    
class stock_warehouse_orderpoint(models.Model):
    """
    Stock rule
    """
    _name = 'stock.warehouse.orderpoint'
    _description = 'Stock rule'
    

    @api.one
    @api.depends('product_id')
    def _compute_uom_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id
        else:
            self.uom_id = False

    
    @api.model
    def _qtys_type_get(self):
        return [
                ('automatic', _('Automatic')),
                ('manual', _('Manual')),
                       ]


    def get_min_qty(self):
        consumption_file = self.product_id[self.env['stock.config.settings'].get_param('stock_rule_consumption_field') or 'consumption_avg_3'] or 0
        return consumption_file / 22 * self.product_id.get_default_supply_delay() + (self.product_id.critical_stock or 0)
    
    
    def get_max_qty(self):
        consumption_file = self.product_id[self.env['stock.config.settings'].get_param('stock_rule_consumption_field') or 'consumption_avg_3'] or 0
        return consumption_file / 22 * self.product_id.horizon + (self.product_id.critical_stock or 0)
    

    @api.one
    @api.depends('qtys_type', 'min_qty', 'max_qty')
    def _compute_qtys(self):
        if self.qtys_type == 'manual':
            self.min_qty = self.manual_min_qty
            self.max_qty = self.manual_max_qty
        else:
            self.min_qty = self.get_min_qty()
            self.max_qty = max(self.get_max_qty(), self.min_qty)

    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char('Name', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='restrict', select=True)
    location_id = fields.Many2one('stock.location', string='Location', required=True, ondelete='restrict')
    uom_id = fields.Many2one('product.uom', string='UoM', compute='_compute_uom_id')
    qtys_type = fields.Selection('_qtys_type_get', string='Type', required=True, default='manual')
    min_qty = fields.Float(compute='_compute_qtys', digits=dp.get_precision('Product quantity'))
    max_qty = fields.Float(compute='_compute_qtys', digits=dp.get_precision('Product quantity'))
    manual_min_qty = fields.Float(string='Min qty', default=0, digits=dp.get_precision('Product quantity'))
    manual_max_qty = fields.Float(string='Max qty', digits=dp.get_precision('Product quantity'))
    last_proc_id = fields.Many2one('procurement.order', string='Last procurement', required=False, ondelete='set null')
    last_procurement_date = fields.Datetime()
    start_date = fields.Date()
    end_date = fields.Date()
    is_active = fields.Boolean(string='Active', default=True)
    company_id = fields.Many2one('res.company', string='Company', required=False, ondelete='restrict', default=lambda self:self.env.user.company_id)
    
    @api.one
    @api.constrains('start_date', 'end_date', 'is_active', 'product_id', 'location_id')
    def _check_overlap(self):
        if self.is_active:
            if self.start_date and self.end_date:
                overlap_op = self.search(['&', '&', '&', ('is_active', '=', True),
                                                         ('id','!=', self.id), 
                                                         ('product_id', '=', self.product_id.id),
                                                         ('location_id', '=', self.location_id.id),
                                                         '|', '&', ('start_date', '>=', self.start_date), 
                                                         ('start_date', '<=', self.end_date),
                                                         '&', ('end_date', '>=', self.start_date), 
                                                         ('end_date', '<=', self.end_date)], limit=1)
            elif self.start_date:
                overlap_op = self.search(['&', '&', '&', ('is_active', '=', True),
                                                         ('id','!=', self.id), 
                                                         ('product_id', '=', self.product_id.id),
                                                         ('location_id', '=', self.location_id.id),
                                                         '|',('start_date', '>=', self.start_date), 
                                                         ('end_date', '>=', self.start_date)], limit=1)
            elif self.end_date:
                overlap_op = self.search(['&', '&', '&', ('is_active', '=', True),
                                                         ('id','!=', self.id), 
                                                         ('product_id', '=', self.product_id.id),
                                                         ('location_id', '=', self.location_id.id),
                                                         '|',('start_date', '<=', self.end_date), 
                                                         ('end_date', '<=', self.end_date)], limit=1)
            else:
                overlap_op = self.search(['&', '&', '&', ('is_active', '=', True),
                                                         ('id','!=', self.id), 
                                                         ('location_id', '=', self.location_id.id),
                                                         ('product_id', '=', self.product_id.id)], limit=1)
                
            if overlap_op:
                raise Warning(_('%s and %s can not overlap.')%(self.name, overlap_op.name))
                
        return True
    
    
    def update_last_proc(self, procurement_id):
        return self.write({'last_proc_id': procurement_id, 'last_procurement_date': fields.Datetime.now()})
    
    
    def do_procurement(self, warehouse_location_rs=False, from_mrp=False):
        op_rs = self
        product_rs = op_rs.product_id
        horizon_date = product_rs.compute_horizon_date()
        virtual_qty, real_qty = product_rs.get_available_stock(to_date=horizon_date, return_real_stock=True)
        if virtual_qty < op_rs.min_qty:
            proc_qty = op_rs.max_qty - virtual_qty
            proc_rs = self.env['procurement.order'].create_procurement({
                    'product_id': product_rs.id, 
                    'needed_date': product_rs.get_date_last_stock_min(warehouse_location_rs or self.env.user.company_id.warehouse_id.stock_location_id, proc_qty, date_stop=horizon_date), 
                    'trigger_supply': 'make_to_plan', 
                    'supply_method': product_rs.supply_method, 
                    'user_id': self.env.user.id, 
                    'from_procurement': True, 
                    'low_procurement': product_rs.get_is_low_proc(proc_qty),
                    'orderpoint_id': op_rs.id, 
                    'from_mrp': from_mrp, 
                    'log': 'Reason: Stock rule (Min: %.2f, Max: %.2f, ID: %d)\nVirtual stock on the horizon qty: %.2f\nReal stock qty: %.2f\nNeeded qty: %.2f'%(op_rs.min_qty, 
                                                                                                                                                                op_rs.max_qty, 
                                                                                                                                                                op_rs.id, 
                                                                                                                                                                virtual_qty, 
                                                                                                                                                                real_qty, 
                                                                                                                                                                proc_qty), 
                            })
            op_rs.update_last_proc(proc_rs.id)
        else:
            proc_rs = self.env['procurement.order']
            
        return proc_rs
    

    @api.one
    def copy(self, default=None):
        if default is None:
            default = {'is_active': False}
        elif 'is_active' not in default:
            default['is_active'] = False

        return super(stock_warehouse_orderpoint, self).copy(default=default)



class procurement_order(models.Model):
    """ 
    Procurement order 
    """
    _name = 'procurement.order'
    _description = 'Procurement order'

        
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('exception', _('Exception')),
                ('progress', _('Progress')),
                ('done', _('Done')),
                ('cancel', _('Cancel')),
                       ]


    @api.model
    def _supply_method_get(self):
        return [
            ('buy', _('Buy')),
               ]


    @api.model
    def _trigger_supply_get(self):
        return [
            ('make_to_plan', _('On scheduler')),
            ('make_to_order', _('On demand')),
            ('make_to_order_with_stock', _('On demand with stock')),
            ('without_stock', _('None')),
               ]
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True, default='/')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='restrict', select=True)
    move_id = fields.Many2one('stock.move', string='OUT Move', required=False, ondelete='set null', select=True)
    move_ids = fields.One2many('stock.move', 'procurement_id', string='Stock moves')
    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='restrict')
    responsible_id = fields.Many2one('res.users', string='Responsible', required=False, ondelete='restrict')
    date = fields.Datetime(string='Create date', default=lambda self: fields.Datetime.now(), select=True)
    needed_date = fields.Date(string='Needed date')
    transfer_id = fields.Many2one('stock.transfer.request', string='Transfer', required=False, ondelete='set null')
    
    # Quantités besoin
#     needed_uom_qty = fields.Float(string='UoM qty', required=True, digits=dp.get_precision('Product quantity'))
#     needed_sec_uom_qty = fields.Float(string='Second UoM qty', required=False, digits=dp.get_precision('Product quantity'))
    
    # UoM besoin
#     needed_uom_id = fields.Many2one('product.uom', string='UoM', required=True, ondelete='restrict')
#     needed_sec_uom_id = fields.Many2one('product.uom', string='Second UoM', required=False, ondelete='restrict')
    reserved_qty = fields.Float(string='Reserved qty', required=False, digits=dp.get_precision('Product quantity'), readonly=True)

    # Quantités appro
    uom_qty = fields.Float(string='UoM qty', required=False, default=0, digits=dp.get_precision('Product quantity'))
    sec_uom_qty = fields.Float(string='Second UoM qty', required=False, default=0, digits=dp.get_precision('Product quantity'))
    
    # UoM appro
    uom_id = fields.Many2one('product.uom', string='UoM', required=False, ondelete='restrict')
    sec_uom_id = fields.Many2one('product.uom', string='Second UoM', required=False, ondelete='restrict')

    supply_method = fields.Selection('_supply_method_get', string='Supply method', required=True, default='buy', 
                    help="Produce will generate production order or tasks, according to the product type. Buy will trigger purchase orders when requested.")
    trigger_supply = fields.Selection('_trigger_supply_get', string='Trigger supply', required=True, default='make_to_plan', help="'On scheduler': When needed, " 
                        "the system take from the stock or wait until re-supplying. 'On demand': When needed, purchase or produce the product for the procurement "
                        "request. 'On demand with stock': During the order, the system will substract the virtual quantity to the stock if needed. 'None':"
                        "Select if you don't want automatic supplying proposition from the system. CAUTION: If 'None' is selected, the system does not make "
                        "supply proposition even if it observes an insufficient need and stock. There is an out of stock risk.")
    procurement_priority = fields.Boolean(default=False, help="If this field is checked, move's covers will be computed on procurement order in priority")
    orderpoint_id = fields.Many2one('stock.warehouse.orderpoint', string='Orderpoint', required=False, ondelete='restrict', copy=False)
    automatic = fields.Boolean(default=lambda self:self.env['stock.config.settings'].get_param('automatic_procurement'), help="If this field is checked, purchase orders or manufacturing orders will be automatically created when procurement order creation")
    from_procurement = fields.Boolean(default=False)
    error = fields.Text(string='Error', copy=False)
    log = fields.Text(string='Log', copy=False)
    waiting_delay = fields.Boolean(default=False, copy=False)
    low_procurement = fields.Boolean(default=False, help='True if during the Material Requirement Planning: ([needed quantity] / [last outgoing move quantity]) < ([this parameter] / 100)')
    is_forecast = fields.Boolean(string='Forecast', default=False)
    from_mrp = fields.Boolean(string='From Material Requirement Planning', default=False)
    state = fields.Selection('_state_get', required=True, select=True, default='draft', copy=False)


    def get_draft_qtys(self, action=False):
        return 0
    
    
#     def get_proc_to_compute_by_move(self):
#         return self

    
    def get_proc_to_compute(self):
#         if with_cancel:
#             with_cancel_where = " AND proc.state != 'cancel'"  
#         else:
#             with_cancel_where = ''
        self.env.cr.execute('''SELECT 
                                sm.history_id
                              FROM
                                procurement_order proc
                                JOIN stock_move sm on proc.move_id = sm.id
                                JOIN stock_move_history h on sm.history_id = h.id
                              WHERE
                                proc.id = %s'''%(self.id, ))
            
        h_id = self.env.cr.fetchall()
        res = False
        if h_id:
            res = self.search([('move_id.history_id', '=', h_id[0][0])])
        
        if not res:        
            res = self
            
        return res
    
    
    def compute_qty_to_procure(self, action=False, warehouse_id=False):
        """
            Calcul de la quantité à commander
        """
#         # À la demande
#         if self.trigger_supply == 'make_to_order':
#             res = max(-self.get_available_stock('uom_qty', ('waiting', 'done', )), 0)
#         # À la demande avec prise en compte du stock: Somme de tous les stock virtuels de tous les procurements de l'appro
#         elif self.trigger_supply == 'make_to_order_with_stock':
#             res = max(-sum([x.get_available_stock('uom_qty', ('waiting', 'done', )) for x in self.get_proc_to_compute()]), 0)
#             # min(-stock virtuel (-les OT ou achats draft si coché), quantité de la commande) 
#             res = min(max(-self.product_id.get_available_stock() - self.get_draft_qtys(action=action), 0), res)

        # Somme de tous les stock virtuels de tous les procurements de l'appro
        if self.trigger_supply in ('make_to_order', 'make_to_order_with_stock'):
            # Sur commande: quantité de la commande 
            res = max(-sum([x.get_available_stock('uom_qty', ('waiting', 'done', )) for x in self.get_proc_to_compute()]), 0)
            # Si sur stock: min entre res et le stock virtuel moins les drafts
            if self.trigger_supply ==  'make_to_order_with_stock':
                # Sur commande en tenant compte du stock: min(-stock virtuel, quantité de la commande) 
                res = min(max(-self.product_id.get_available_stock(warehouse_id=warehouse_id) - self.get_draft_qtys(action=action), 0), res)

        # Sur plannificateur: Règle de stock max - stock virtuel
        elif self.trigger_supply == 'make_to_plan':
            stock_qty = self.product_id.get_available_stock(to_date=self.product_id.compute_horizon_date(), warehouse_id=warehouse_id) + self.get_draft_qtys(action=action)
            if self.orderpoint_id:
                res = max(self.orderpoint_id.max_qty - stock_qty, 0)
            else:
                res = max(-stock_qty, 0)
                
        return res

    
    def update_delay(self, date=False, with_raise=True):
        return True


    def update_supply_procurement_deleted(self):
        """
            Verification des flag appro supprimé dans les procurement de la même appro
        """
        all_proc_rs = self.get_proc_to_compute()
        for proc_rs in all_proc_rs:
            proc_rs.update_procurement_deleted()
            
        return True
    
    
    def update_cancel_procurement(self):
        """
            Au passage du mouvement à waiting, si le procurement est cancel: 
              - Appro du procurement
              - Verification des flag appro supprimé dans les procurement de la même appro
        """
        self.do_default_procurement(overwrite=False)
        self.wkf_progress()
        self.update_supply_procurement_deleted()
        return True
    
    
    def get_done_qty(self):
        """
            Retourne la quantité la somme des quantités des mouvement OUT done du procurement
        """
        done_out_sum = 0.0 
        for move in self.env['stock.move'].search([('procurement_id', '=', self.id), ('state', '=', 'done'), ('type', '=', 'out')], order='date'):
            done_out_sum += move.get_product_uom_qty()
                 
        return done_out_sum


    def get_reserved_qty(self, done_out_sum=0.0):
        """
            Retourne la quantité réservée restante: quantité réservée du procurement - somme(quantités des mouvement OUT done)
        """
        if not done_out_sum:
            done_out_sum = self.get_done_qty()
                 
        return self.uom_qty - done_out_sum


    def get_available_stock(self, field, states):    
        move_obj = self.env['stock.move']
        uom_obj = self.env['product.uom']
        res = 0
        product_uom_id = self.uom_id.id
        in_args = [('type', '=', 'in'), ('state', 'in', states), ('product_id', '=', self.product_id.id), ('procurement_id', '=', self.id)]
        out_args = [('type', '=', 'out'), ('state', 'in', states), ('product_id', '=', self.product_id.id), ('procurement_id', '=', self.id)]
        in_move_qtys = move_obj.search_group(fields=[field, 'uom_id'], 
                                             groupby=['uom_id'], 
                                             args=in_args,
                                             sum=field,
                                             return_dict=True)
        for in_move_qty in in_move_qtys:
            if product_uom_id == in_move_qty['uom_id']:
                res += in_move_qty[field]
            else:
                res += uom_obj._compute_qty(in_move_qty['uom_id'], in_move_qty[field], to_uom_id=product_uom_id, with_raise=True, with_round=False)

        out_move_qtys = move_obj.search_group(fields=[field, 'uom_id'], 
                                              groupby=['uom_id'], 
                                              args=out_args,
                                              sum=field,
                                              return_dict=True)
        for out_move_qty in out_move_qtys:
            if product_uom_id == out_move_qty['uom_id']:
                res -= out_move_qty[field]
            else:
                res -= uom_obj._compute_qty(out_move_qty['uom_id'], out_move_qty[field], to_uom_id=product_uom_id, with_raise=True, with_round=False)
                
        return res
    
    
    def _open_source_procurement(self, search_arg):
        """
            Fonction permettant d'afficher le procurement déclencheur
        """
        res = False
        move_obj = self.env['stock.move']
        proc_rs = self.env['procurement.order'].search(search_arg)
        for proc in proc_rs:
            if proc.move_id.history_id:
                move_rs = move_obj.search([('history_id', '=', proc.move_id.history_id.id)])
                for move in move_rs:
                    if move.procurement_id:
                        proc_rs |= move.procurement_id
            
        if proc_rs:
            action = self.env.ref('stock.act_procurement_order')
            if action:
                action = action.read()[0]
                action['context'] = {} 
                action['views'] = [] 
                action['view_mode'] = 'tree,form' 
                action['domain'] = [('id', 'in', proc_rs.ids)]
                res = action
                
        return res
    
    
    def one_history_proc_not_cancel(self):
        for proc in self:
            if proc.state not in ('cancel', 'draft'):
                return True
                    
        return False

    
    @api.multi
    def update_reserved_qtys(self):
        """
            Mise à jour des quantitées réservées des mouvements IN 
        """
        # Affectation aux mouvements done
#         done_qty = self.get_done_qty()
#         in_reserved_qty = out_reserved_qty = self.get_reserved_qty(done_qty)

        move_obj = self.env['stock.move']
        proc_rs = self.get_proc_to_compute()
        if (self.procurement_priority or self.trigger_supply == 'make_to_order') and proc_rs.one_history_proc_not_cancel():
            uom_qty = 0
            for proc in proc_rs:
                uom_qty += proc.uom_qty
                
            in_reserved_qty = out_reserved_qty = uom_qty
            reception = 0
            if in_reserved_qty > 0:
                # IN Done
                for move in move_obj.search([('procurement_id', 'in', proc_rs.ids), ('state', '=', 'done'), ('type', '=', 'in')], order='date'):
                    qty = move.get_product_uom_qty()# - done_qty
                    if qty < in_reserved_qty:
                        if move.reserved_qty != qty:
                            move.write({'reserved_qty': qty})
                            
                        in_reserved_qty -= qty
                        reception += qty
                    else:
                        if move.reserved_qty != in_reserved_qty:
                            move.write({'reserved_qty': in_reserved_qty})
                            
                        reception += in_reserved_qty
                        in_reserved_qty = 0
    
                # OUT Done
                delivered_qty = 0
                for move in move_obj.search([('procurement_id', 'in', proc_rs.ids), ('state', '=', 'done'), ('type', '=', 'out')], order='date'):
                    qty = move.get_product_uom_qty()# - done_qty
                    if qty < min(out_reserved_qty, reception):
                        # Enlever ce qui est done a hauteur de ce qui est recu 
                        if move.reserved_qty != qty:
                            move.write({'reserved_qty': qty})
                            
                        out_reserved_qty -= qty
                        delivered_qty += qty
                    else:
                        min_qty = min(out_reserved_qty, reception)
                        if move.reserved_qty != min_qty:
                            move.write({'reserved_qty': min_qty})
                            
                        out_reserved_qty -= min(out_reserved_qty, reception) # on met a 0 ou a la qty reservé - qty receptionné
                        delivered_qty += min(out_reserved_qty, reception)
                
                # Si il reste de la quantité: affectation aux mouvements en cours
                # IN not Done
                to_receive = 0
                for move in move_obj.search([('procurement_id', 'in', proc_rs.ids), ('state', 'not in', ('done', 'cancel')), ('type', '=', 'in')], order='date'):
                    qty = move.get_product_uom_qty()
                    if qty < in_reserved_qty:
                        if move.reserved_qty != qty:
                            move.write({'reserved_qty': qty})
                            
                        in_reserved_qty -= qty
                        to_receive += qty
                    else:
                        if move.reserved_qty != in_reserved_qty:
                            move.write({'reserved_qty': in_reserved_qty})
                            
                        to_receive += in_reserved_qty
                        in_reserved_qty = 0
                        
                remaining_reserved_qty = to_receive + reception - delivered_qty
                # OUT not Done
                for move in move_obj.search([('procurement_id', 'in', proc_rs.ids), ('state', 'not in', ('done', 'cancel')), ('type', '=', 'out')], order='date desc'):
                    qty = move.get_product_uom_qty()
                    # Inféreur ou egale a la qantité rentrante, on peut pas reserver plus les qty entrante
                    if qty < min(out_reserved_qty, remaining_reserved_qty):
                        if move.reserved_qty != qty:
                            move.write({'reserved_qty': qty})
                            
                        out_reserved_qty -= qty
                    else:
                        qty_min = min(out_reserved_qty, remaining_reserved_qty)
                        if move.reserved_qty != qty:
                            move.write({'reserved_qty': qty_min})
                            
                        out_reserved_qty = 0 
        else:
            move_rs = move_obj.search([('procurement_id', 'in', proc_rs.ids), 
                                       ('type', 'in', ('in', 'out')), 
                                       ('reserved_qty', '!=', 0.0)])
            if move_rs:
                move_rs.write({'reserved_qty': 0.0})
            
        return True
    
    
    def get_op_ids(self, limit_date, supply_method, level=False):
        today = fields.Date.today()
        if isinstance(level, int):
            if level == 0:
                level_condition = 'AND (p.bom_level = 0 OR p.bom_level is null)'
            else:
                level_condition = 'AND p.bom_level = %d'%(level)
            
        else:
            level_condition = ''
            
        query = """SELECT op.id from stock_warehouse_orderpoint op, product_product p 
                      WHERE op.product_id = p.id
                        AND (op.start_date <= '%(today)s' OR op.start_date is null)
                        AND (op.end_date >= '%(today)s' OR op.end_date is null)
                        AND p.state IN %(p_states)s
                        AND p.type = 'stockable'
                        %(level_condition)s
                        AND p.supply_method = '%(supply_method)s'
                        AND (p.last_procurement is null OR p.last_procurement < '%(limit_date)s')
                       """% {'today': today, 
                             'supply_method': supply_method, 
                             'limit_date': limit_date, 
                             'level_condition': level_condition, 
                             'p_states': str(self.env['product.product'].get_available_states())}

        self.env.cr.execute(query)
        q_res = self.env.cr.fetchall()
        if q_res:
            res = [x[0] for x in q_res]
        else:
            res = []
        
        return res
    
    
    def get_auto_procurement_args(self, already_compute_ids, type, limit_date):
        return [
            ('id', 'not in', already_compute_ids),
            ('state', 'in', self.env['product.product'].get_available_states()),
            ('trigger_supply', '!=', 'without_stock'),
            ('supply_method', '=', type),
            ('exclude_of_mrp', '=', False),
            ('type', '=', 'stockable'),
            '|', ('last_procurement', '=', False), 
            ('last_procurement', '<', limit_date)
        ]

    @api.multi
    def test_do_all_procurement(self):
        self.do_all_procurement('produce')
        return self.do_all_procurement('buy')


    @api.model
    def do_all_procurement(self, type):
        print 'Procurement start (%s)'%(type)
        if type == 'produce':
            product_obj = self.env['product.product']
            product_obj.cron_calc_bom_level()
            product_rs = product_obj.search([('state', 'in', product_obj.get_available_states()),
                                             ('trigger_supply', '!=', 'without_stock'),
                                             ('supply_method', '=', type),
                                             ('exclude_of_mrp', '=', False),
                                             ('type', '=', 'stockable')],
                                            order='bom_level desc',
                                            limit=1)
            if product_rs:
                bom_level = product_rs.read(['bom_level'])[0]['bom_level']
            else:
                bom_level = 0
                
            for level in range(bom_level, -1, -1):
                self._do_all_procurement(type, level=level, from_mrp=True)
                
        else:
            self._do_all_procurement(type, from_mrp=True)


    @api.model
    def _do_all_procurement(self, type, level=False, from_mrp=False):
        """
            Approvisionnement automatique sur tous les produit (méthode lancée par le cron)
        """
        already_compute_ids = []
        product_to_commit = self.env['product.product']
        op_obj = self.env['stock.warehouse.orderpoint']
        warehouse_location_rs = self.env.user.company_id.warehouse_id.stock_location_id
        # Création de limit_date: maintenant - (intervalle du cron / 2)
        # Cette date sert à ne pas reselectionner les produits déjà calculés en cas de plantage pendant l'execution du procurement
        next_date = now = datetime.utcnow()
        # Une demi journé par défaut
        delta_second = 86400
        cron = self.env.ref('stock.ir_cron_procurement_%s'%(type)) 
        if cron:
            next_date -= INTERVAL_TYPES[cron.interval_type](cron.interval_number)
            delta = now - next_date
            delta_second = delta.days * 86400 + delta.seconds
        
        limit_date = now - relativedelta(seconds=delta_second / 2)
        limit_date = limit_date.strftime('%Y-%m-%d %H:%M:%S')
        
        # Règle de stock
        created_proc_ids = []
        op_ids = self.get_op_ids(limit_date, type, level=level)
        for op in op_obj.browse(op_ids):
            product_rs = op.product_id
            # Supression des anciens
            self.search([('state', '!=', 'done'), 
                         ('from_procurement', '=', True), 
                         ('product_id', '=', product_rs.id)]).unlink(with_raise=False)
            proc_rs = op.do_procurement(warehouse_location_rs, from_mrp=from_mrp)
            if proc_rs:
                created_proc_ids.append(proc_rs.id)
                
            already_compute_ids.append(product_rs.id)
            product_to_commit += product_rs
            
            if not len(product_to_commit) % 100:
                self.env.cr.execute('UPDATE product_product SET last_procurement=now() at time zone \'utc\' WHERE id IN %s', (tuple(product_to_commit.ids), ))
#                 product_to_commit.write({'last_procurement': fields.Datetime.now()})
                product_to_commit = self.env['product.product']
                created_proc_ids = []
                self.env.cr.commit()
                
        if product_to_commit:
            self.env.cr.execute('UPDATE product_product SET last_procurement=now() at time zone \'utc\' WHERE id IN %s', (tuple(product_to_commit.ids), ))
            product_to_commit = self.env['product.product']
            created_proc_ids = []
            self.env.cr.commit()
                
        # Automatique
        product_args = self.get_auto_procurement_args(already_compute_ids, type, limit_date)
        if isinstance(level, int):
            if level == 0:
                product_args.extend(['|', ('bom_level', '=', 0), ('bom_level', '=', False)])
            else:
                product_args.append(('bom_level', '=', level))

        for product_rs in self.env['product.product'].search(product_args):
            # Supression des anciens
            self.search([('state', '!=', 'done'), 
                         ('from_procurement', '=', True), 
                         ('product_id', '=', product_rs.id)]).unlink(with_raise=False)
            proc_rs = product_rs.do_procurement_auto(from_mrp=from_mrp)
            if proc_rs:
                created_proc_ids.append(proc_rs.id)
                
            product_to_commit += product_rs
            if not len(product_to_commit) % 100:
                self.env.cr.execute('UPDATE product_product SET last_procurement=now() at time zone \'utc\' WHERE id IN %s', (tuple(product_to_commit.ids), ))
                product_to_commit = self.env['product.product']
                created_proc_ids = []
                self.env.cr.commit()
                
        if product_to_commit:
            self.env.cr.execute('UPDATE product_product SET last_procurement=now() at time zone \'utc\' WHERE id IN %s', (tuple(product_to_commit.ids), ))
            product_to_commit = self.env['product.product']
            created_proc_ids = []
            self.env.cr.commit()
            
        return True

    
    def update_procurement_deleted(self):
        """
            Méthode déstinée à être surchargé par purchase et mrp
            Enlève le booléen procurement_deleted de l'ordre d'approvisionnement (PO ou MO)
        """
        return False
    
    
    def check_auto_validate(self):
        return True
    
    
    @api.multi
    def create_warehouse_transfer(self):
        try:
            warehouse_dest_id = self.move_id.warehouse_id.id
            if not warehouse_dest_id:
                warehouse_dest_id = self.env.user.company_id.warehouse_id.id

            qty = self.compute_qty_to_procure('transfer', self.move_id.warehouse_id.id)
            # Besoin d'un appro pour cet entrepôt
            if qty > 0:
                # Besoin d'un appro seulement dans l'entrepot: appro par transfert
                horizon = self.product_id.compute_horizon_date()
                if self.trigger_supply == 'make_to_plan':
                    to_date = horizon
                else:
                    to_date = False
                
                warehouse_id, warehouse_qty = self.product_id.get_max_virtual_stock_warehouse([warehouse_dest_id], to_date)
                if qty <= warehouse_qty:
                    transfer_obj = self.env['stock.transfer.request']
                    need_date = self.needed_date or fields.Date.today()
                    if warehouse_id:
                        transfer_rs = transfer_obj.create({'product_id': self.product_id.id,
                                                           'origin': self.name,
                                                           'warehouse_id': warehouse_id,
                                                           'warehouse_dest_id': warehouse_dest_id,
                                                           'uom_qty': qty,
                                                           'uom_id': self.product_id.uom_id.id,
                                                           'needed_uom_qty': qty,
                                                           'needed_uom_id': self.product_id.uom_id.id,
                                                           'need_date': need_date,
                                                           'departure_date': transfer_obj.get_departure_date(need_date, warehouse_id=warehouse_id, warehouse_dest_id=warehouse_dest_id)})
                        if transfer_rs:
                            self.write({'transfer_id': transfer_rs.id, 
                                        'uom_qty': qty, 
                                        'uom_id': self.product_id.uom_id.id})
                        
                    # Appro par achat ou OT
                    else:
                        transfer_rs = False
                        
                # Appro par achat ou OT
                else:
                    transfer_rs = False

            # Pas besoin d'appro pour cet entrepôt
            else:
                if self.check_auto_validate():
                    # Pb avcec le code ci-dessous: Stock virtuel superieur à la demande dans l'entrepot mais inférieur au total
                    self.update_delay(fields.Date.today(), with_raise=False)
                    if self.state in ('draft', 'exception'):
                        if self.env['stock.move'].search([('state', 'not in', ('done', 'cancel')),
                                                          ('type', '=', 'out'),
                                                          ('procurement_id', '=', self.id)], limit=1):
                            self.wkf_progress()
                        else:
                            self.wkf_done()
                 
                transfer_rs = True
                
        except Exception as e:
            transfer_rs = True
            error = ''
            if e and isinstance(e.args, tuple):
                for i in e.args:
                    if error:
                        error = '%s\n%s'%(error, i)
                    else:
                        error = i
                        
                self.write({'error': error, 'state': 'exception'})
                
        return transfer_rs
    
    
    @api.multi
    def unlink_warehouse_transfer(self):
        for proc in self:
            if proc.transfer_id:
                proc.transfer_id.wkf_cancel()
        
        return True
    
    
    def do_default_procurement(self, overwrite=True):
        """
             Méthode surchargée par purchase et mrp
        """
        transfer_rs = False
        if not self.is_forecast and (overwrite or not self.transfer_id):
            transfer_rs = self.create_warehouse_transfer()
        
        return transfer_rs and True
    
    
    def do_action_on_unlink(self, with_raise=False):
        """
            Méthode déstinée à être surchargé par purchase et mrp
        """
        return self
    
    
    def create_procurement(self, vals):
        """
            Méthode de création du procurement. Génère les appro si nécessaire
        """
        proc_rs = self.create(vals)
        if proc_rs.automatic and not proc_rs.low_procurement:
            proc_rs.do_default_procurement() 
        
        return proc_rs
    
    
    @api.multi
    def wkf_draft(self):
        """
            État à done draft
        """
        self.write({'state': 'draft'})
    
    
    @api.multi
    def wkf_progress(self):
        """
            État à done progress
        """
        self.update_reserved_qtys()
        self.update_procurement_deleted()
        self.write({'state': 'progress'})
    
    
    @api.multi
    def wkf_done(self):
        """
            État à done date
        """
        self.write({'state': 'done'})
        
        
    def do_action_on_cancel(self):
        if self.transfer_id:
            self.transfer_id.wkf_cancel()
            self.move_id.write({'procurement_id': False})
            
        return True
        
        
    @api.multi
    def wkf_cancel(self):
        """
            État à cancel
        """
        for proc in self.get_proc_to_compute():
            proc.do_action_on_cancel()
            
        self.write({'state': 'cancel'}) 
    
    
    @api.model
    def create(self, vals):
        """
            On écrit le nom de la vente à partir de sa séquence en base
        """
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].get('procurement.order') or '/'

        res = super(procurement_order, self).create(vals)
        return res 
    
    
    @api.one
    def copy(self, default=None):
        raise UserError(_('Duplication prohibited.'))
        return super(procurement_order, self).copy(default=default)
    
    
    @api.multi
    def unlink(self, cascade=True, with_raise=True):
        """
            
        """
        if cascade:
            self = self.do_action_on_unlink(with_raise=with_raise)
            
        return super(procurement_order, self).unlink()  
    
    
    
class stock_quality_control(models.Model):
    """ 
    Stock quality control
    """
    _name = 'stock.quality.control'
    _description = 'Stock quality control'
    _rec_name = "product_id"
            
    
    @api.model
    def _type_get(self):
        return [
                ('jasper_receipt', _('Jasper receipt')),
                ('jasper_delivery', _('Jasper delivery')),
                ('pdf_receipt', _('PDF receipt')),
                ('pdf_delivery', _('PDF delivery')),
                       ]
            
    #===========================================================================
    # COLUMNS
    #===========================================================================
    type = fields.Selection('_type_get', string='Type', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='cascade')
    pdf_file = fields.Many2one('document.openprod', string='Document', required=False, ondelete='restrict')
    report_id = fields.Many2one('ir.actions.report.xml', string='Report', required=False, ondelete='restrict')
    category_id = fields.Many2one('product.category', string='Category', required=False, ondelete='cascade', 
                                  domain=[('type', '!=', 'view')])
    parent_id = fields.Many2one('stock.quality.control', string='Parent', required=False, ondelete='set null')
    
    @api.multi
    def write(self, vals=None):
        res = super(stock_quality_control, self).write(vals=vals)
        category_ids = []
        for control in self:
            if control.category_id and control.category_id.id not in category_ids:
                category_ids.append(control.category_id.id)
                control.category_id.modif_type_quality_documents(field='plan_control_ids', product_rcs=False, delete=False)
            
        return res
    
    
    @api.model
    def create(self, vals):
        res = super(stock_quality_control, self).create(vals=vals)
        if res.category_id:
            res.category_id.modif_type_quality_documents(field='plan_control_ids', product_rcs=False, delete=False)
            
        return res
    
    @api.multi
    def unlink(self):
        category_ids = []
        for control in self:
            if control.category_id and control.category_id.id not in category_ids:
                category_ids.append(control.category_id.id)
                control.category_id.modif_type_quality_documents(field='plan_control_ids', product_rcs=False, delete=True, ids=self.ids)
                
        return super(stock_quality_control, self).unlink()

    
    
class stock_alert_color(models.Model):
    """ 
    Stock alert 
    """
    _name = 'stock.alert.color'
    _description = 'Stock alert'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char('Name', size=32, default='Colors configuration')
    is_active = fields.Boolean(string='Active', default=False)
    # Priority 1 (red)
    move_1_active = fields.Boolean('Active')
    move_1_min = fields.Integer('Minimum')
    move_1_max = fields.Integer('Maximum')
    # Priority 2 (orange)
    move_2_active = fields.Boolean('Active')
    move_2_min = fields.Integer('Minimum')
    move_2_max = fields.Integer('Maximum')
    # Priority 3 (green)
    move_3_active = fields.Boolean('Active')
    move_3_min = fields.Integer('Minimum')
    move_3_max = fields.Integer('Maximum')

#     # Priority 1 (red)
#     wo_1_active = fields.Boolean('Active')
#     wo_1_min = fields.Integer('Minimum')
#     wo_1_max = fields.Integer('Maximum')
#     # Priority 2 (orange)
#     wo_2_active = fields.Boolean('Active')
#     wo_2_min = fields.Integer('Minimum')
#     wo_2_max = fields.Integer('Maximum')
#     # Priority 3 (green)
#     wo_3_active = fields.Boolean('Active')
#     wo_3_min = fields.Integer('Minimum')
#     wo_3_max = fields.Integer('Maximum')
#     
#     # Priority 1 (red)
#     purchase_1_active = fields.Boolean('Active')
#     purchase_1_min = fields.Integer('Minimum')
#     purchase_1_max = fields.Integer('Maximum')
#     # Priority 2 (orange)
#     purchase_2_active = fields.Boolean('Active')
#     purchase_2_min = fields.Integer('Minimum')
#     purchase_2_max = fields.Integer('Maximum')
#     # Priority 3 (green)
#     purchase_3_active = fields.Boolean('Active')
#     purchase_3_min = fields.Integer('Minimum')
#     purchase_3_max = fields.Integer('Maximum')
# 
#     # Priority 1 (red)
#     sale_1_active = fields.Boolean('Active')
#     sale_1_min = fields.Integer('Minimum')
#     sale_1_max = fields.Integer('Maximum')
#     # Priority 2 (orange)
#     sale_2_active = fields.Boolean('Active')
#     sale_2_min = fields.Integer('Minimum')
#     sale_2_max = fields.Integer('Maximum')
#     # Priority 3 (green)
#     sale_3_active = fields.Boolean('Active')
#     sale_3_min = fields.Integer('Minimum')
#     sale_3_max = fields.Integer('Maximum')


    @api.multi
    def copy(self, default=None):
        """
            Actif à False à la copie
        """
        if not default:
            default = {}
            
        default['is_active'] = False
        return super(stock_alert_color, self).copy(default=default)


    @api.multi
    def write(self, vals=None):
        """
            Interdiction d'avoir plusieurs enregistrements actifs
        """
        if not vals:
            vals = {}
        
        if vals.get('is_active', False) and self.search([('is_active', '=', True)], limit=1):
            raise ValidationError(_('You cannot create several active record.'))
            
        return super(stock_alert_color, self).write(vals)



class stock_label_template(models.Model):
    """ 
    Label template
    """
    _name = 'stock.label.template'
    _description = 'Label template'
    
    @api.model
    def _type_get(self):
        return [
            ('uc', _('UC')),
            ('um', _('UM')),
        ]

    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    sequence_id = fields.Many2one('ir.sequence', string='Sequence', required=True, ondelete='restrict')
    type = fields.Selection('_type_get', default='uc', required=True)
    counterpart_location_id = fields.Many2one('stock.location', string='Counterpart location', required=False, ondelete='restrict', help='Counterpart location that could be used to a label closing or a label balancing for example.')
    is_theorical_comuption = fields.Boolean(string='Theoretical consumption', default=False)
    is_delete_um = fields.Boolean(string='Delete UM', default=False)
    generate_label_in_advance = fields.Boolean(default=False, help='If this field is checked, label will create directly on picking vizualisation')
    is_reprint_done = fields.Boolean(string='Reprint done', default=False, help='stock_label_template.is_reprint_done.help')
    is_reprint_valid = fields.Boolean(string='Reprint valid', default=False, help='stock_label_template.is_reprint_valid.help')
    


class stock_label(models.Model):
    """ 
    Label 
    """
    _name = 'stock.label'
    _description = 'Label'
    
    def _auto_init(self, cr, context=None):
        """
            On ne peut pas avoir deux étiquettes avec le même nom mise à part '/'
        """
        res = super(stock_label, self)._auto_init(cr, context=context)
        cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = \'label_name_unique\'')
        if not cr.fetchone():
            cr.execute('CREATE UNIQUE INDEX label_name_unique ON stock_label (name) WHERE name != \'/\'')
               
        return res
    
    
    @api.model
    def _type_get(self):
        return [
                ('uc', _('UC')),
                ('um', _('UM')),
                       ]
    
    
    @api.model
    def _state_get(self):
        return [
            ('draft', _('Draft')),
            ('available', _('Available')),
            ('reserved', _('Reserved')),
            ('control', _('Control')),
            ('quarantine', _('Quarantine')),
            ('inactive', _('Inactive')),
                   ]


    def _get_states(self):
        return {
            'draft': [('readonly', True)], 
            'available': [('readonly', True)], 
            'reserved': [('readonly', True)], 
            'control': [('readonly', True)], 
            'quarantine': [('readonly', True)], 
            'inactive': [('readonly', True)], 
                }
        
    def _get_states_attribute(self):
        return {
            'draft': [('readonly', False)], 
            'available': [('readonly', False)], 
            'reserved': [('readonly', False)], 
            'control': [('readonly', False)], 
            'quarantine': [('readonly', False)], 
            'inactive': [('readonly', False)], 
                }


    @api.multi
    def _compute_expiry_date(self):
        # SQL pour performences
        self.env.cr.execute("""
                            SELECT 
                              label.id, 
                              lot.expiry_date, 
                              lot.removal_date
                            FROM 
                              stock_label label 
                              LEFT JOIN stock_lot lot ON label.lot_id = lot.id 
                            WHERE 
                              (lot.expiry_date IS NOT NULL OR lot.removal_date IS NOT NULL) 
                              AND label.id IN %s 
                             """, (tuple(self.ids),))
        res = self.env.cr.dictfetchall()
        res = {x['id']: x for x in res}
        for label in self:
            if label.id in res:
                label.expiry_date = res[label.id]['expiry_date']
                label.removal_date = res[label.id]['removal_date']
            else:
                label.expiry_date = False
                label.removal_date = False
                
        return True
    
    
    def _search_expiry_date(self, operator, value):
        """
            Fonction search de la disponibilité de l'ot
        """ 
        label_ids = []
        self.env.cr.execute("""
                            SELECT 
                                label.id, 
                                lot.expiry_date
                            FROM 
                                stock_label label 
                                LEFT JOIN stock_lot lot ON label.lot_id = lot.id 
                            WHERE 
                                lot.expiry_date IS NOT NULL AND
                                lot.expiry_date < now() AND
                                label.id IN (select id from stock_label where is_active = true)
                             """)
        res = self.env.cr.dictfetchall()
        if res:
            label_ids = [x['id'] for x in res]
            
        return [('id', 'in', label_ids)]  
    
    
    @api.one
    def _compute_origin_qtys(self):
        move_label = self.env['stock.move.label'].search([('label_id', '=', self.id)], order='done_date asc', limit=1)
        self.origin_uom_qty = move_label and move_label.uom_qty or 0.0
        self.origin_sec_uom_qty = move_label and move_label.sec_uom_qty or 0.0
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True, default='/', copy=False, states=_get_states)
    template_id = fields.Many2one('stock.label.template', string='Template', required=True, ondelete='restrict', states=_get_states)
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='restrict', states=_get_states)
    uom_qty = fields.Float(string='UoM qty', required=False, digits=dp.get_precision('Product quantity'), default=0.0, copy=False, readonly=True)
    uom_id = fields.Many2one('product.uom', string='UoM', readonly=True, ondelete='restrict')
    sec_uom_qty = fields.Float(string='Second UoM qty', required=False, digits=dp.get_precision('Product quantity'), default=0.0, copy=False, readonly=True)
    sec_uom_id = fields.Many2one('product.uom', string='Second UoM', readonly=True, ondelete='restrict')
    location_id = fields.Many2one('stock.location', string='Location', ondelete='restrict', readonly=True, copy=False)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', readonly=True, required=False, ondelete='restrict')
    lot_id = fields.Many2one('stock.lot', string='Lot', ondelete='restrict', readonly=True)
    is_active = fields.Boolean(string='Active', default=False, copy=False, readonly=True)
    state = fields.Selection('_state_get', required=True, default='draft', copy=False, readonly=True)
    type = fields.Selection(selection='_type_get', related='template_id.type', store=True, readonly=True)
    last_move_id = fields.Many2one('stock.move', string='Last stock move', required=False, ondelete='restrict', copy=False, readonly=True)
    first_move_id = fields.Many2one('stock.move', string='First stock move', required=False, ondelete='restrict', copy=False, readonly=True, select=True)
    um_label_id = fields.Many2one('stock.label', string='UM', required=False, ondelete='restrict', readonly=True)
    uc_label_ids = fields.One2many('stock.label', 'um_label_id',  string='UC labels', readonly=True)
    attribute_ids = fields.One2many('common.attribute', 'uc_label_id', string='Attributes', states=_get_states_attribute)
    expiry_date = fields.Date(compute='_compute_expiry_date', search='_search_expiry_date')
    removal_date = fields.Date(compute='_compute_expiry_date')
    is_variable_double_unit = fields.Boolean(default=False, states=_get_states)
    create_date = fields.Date(string='Create Date')
    origin_label_id = fields.Many2one('stock.label', string='Origin label', required=False, ondelete='restrict', readonly=True)
    origin_uom_qty = fields.Float(string='Origin UoM qty', compute='_compute_origin_qtys', digits=dp.get_precision('Product quantity'))
    origin_sec_uom_qty = fields.Float(string='Origin sec UoM qty', compute='_compute_origin_qtys', digits=dp.get_precision('Product quantity'))
    is_before_create = fields.Boolean(string='Before create', default=False)
    printed_qty = fields.Float(string='Printed qty', required=False, digits=dp.get_precision('Product quantity'), default=0.0)
    is_delete_um = fields.Boolean(string='Delete UM', default=False)
    print_date = fields.Datetime(string='Print date')
    print_user_id = fields.Many2one('res.users', string='Print user', required=False, ondelete='restrict')
    print_nb = fields.Integer(string='Print nb', default=0, required=False)
    
    
    @api.multi
    def get_available_qty(self, move_id):
        query = """
            SELECT
              l.uom_qty - COALESCE(sum(ml.uom_qty), 0)
              FROM
                stock_move_label ml
                JOIN stock_label l ON ml.label_id = l.id
                JOIN stock_move m ON ml.move_id = m.id
              WHERE
                m.state = 'waiting'
                AND l.id = %s
                AND m.id != %s
              GROUP BY l.id
              """
        self.env.cr.execute(query, (self.id, move_id))
        res = self.env.cr.fetchone()
        # Pas sous la forme res and res[0] or self.uom_qty car si res=0.0 on souhaite renvoyer 0
        if res:
            res = res[0]
        else:
            res = self.uom_qty
        
        return res
    
    
    @api.one
    def delete_um_labels(self):
        if self.is_delete_um and self.uc_label_ids:
            self.unlink()
        
        return True
      
    
    @api.multi
    def move(self, location=False, location_id=False, label_ids=False, done=True):
        """
            Mouvement d'étiquette
            :param self: Liste des étiquettes à mettre à jour
            :type self: stock.label
            :param location: Emplacement de destination
            :type location: recordset: stock.location
            :param location_id: Emplacement de destination (au cas ou location n'est pas remplis)
            :type location_id: integer
            :param label_ids: Liste des étiquettes à mettre à jour (au cas ou location n'est pas une liste de rs)
            :type label_ids: list
            :return: mouvement créé
            :rtype: stock.move
        """
        if not self and label_ids:
            self = self.browse(label_ids)
        else:
            if not self:
                raise except_orm(_('Error'), _('No labels found.'))
        
        if not location and not location_id:
            raise except_orm(_('Error'), _('No location found.'))    
        
        ctx = self.env.context.copy()
        if not ctx.get('authorize_return', False):
            for label in self:
                if label.state in ('draft', 'inactive'):
                    raise except_orm(_('Error'), _('You can not move a label if it is inactive or draft.'))
        
        move, qty = self.env['stock.move.label'].create_move_label(self, location and location.id or location_id)
        if move and done:
            if ctx.get('label_move_done_date'):
                move.write({'done_date': ctx['label_move_done_date']})
                
            move.wkf_waiting()
            move.wkf_done()
            
        return move

    
    def refresh(self):
        """
            Recalcule la quantité, l'emplacement, l'état et le champ active d'une étiquette ou de toutes les étiquettes d'un produit
            :param self: Liste des étiquettes à mettre à jour
            :type self: stock.label
            :return: True
            :rtype: boolean
        """
        # Update des étiquettes actives avec la vue postgres
        query = """ 
        UPDATE 
            stock_label l
        SET
            is_active=true, 
            state=CASE WHEN location.control THEN 'control'
                       WHEN location.quarantine THEN 'quarantine' 
                       ELSE 'available'
                  END,
            uom_qty=(SELECT sum(uom_qty) FROM location_label_report WHERE label_id = l.id), 
            location_id = r.location_id,
            warehouse_id = r.warehouse_id,
            write_date = now(),
            write_uid = %s
        FROM 
            location_label_report r
            JOIN stock_location location ON location.id = r.location_id 
        WHERE
            r.label_id = l.id
            AND r.uom_qty > 0
            AND l.id IN %s
        RETURNING l.id
        """
        self.env.cr.execute(query, (self.env.user.id, tuple(self.ids, ), ))
        res = self.env.cr.fetchall()
        if res:
            res = [x[0] for x in res]
            # Update des étiquettes réservées
            query = """ 
            UPDATE 
                stock_label l
            SET
                state='reserved'
            FROM 
                stock_move_label ml
                JOIN stock_move m ON ml.move_id = m.id
                JOIN stock_location location ON location.id = m.location_id 
            WHERE
                m.state = 'waiting'
                AND ml.label_id = l.id
                AND l.state = 'available'
                AND l.id IN %s
                AND (NOT location.control OR location.control is null)
                AND (NOT location.quarantine OR location.control is null)
            RETURNING l.id
            """
            self.env.cr.execute(query, (tuple(res), ))
            ids_to_update = list(set(self.ids) - set(res))
        else:
            ids_to_update = self.ids
            
        # Update des autres étiquettes (inactives)
        if ids_to_update:
            self.env.cr.execute("""
            UPDATE 
              stock_label 
            SET 
              write_date=now(), 
              write_uid=%s, 
              is_active=false, 
              state='inactive', 
              uom_qty=0.0 
            WHERE 
              id in %s
            """, (self.env.user.id, tuple(ids_to_update), ))
            
        
        return True
    
    
    @api.multi
    def close(self):
        """
            Mouvement d'étiquette
            :param self: Liste des étiquettes à mettre à jour
            :type self: stock.label
            :return: True
            :rtype: boolean
        """
        location_labels = {}
        for label in self:
            if label.template_id.counterpart_location_id in location_labels:
                location_labels[label.template_id.counterpart_location_id] += label
            else:
                location_labels[label.template_id.counterpart_location_id] = label
                
        for location, labels in location_labels.iteritems():
            labels.move(location)
            
        return True
    
    
    def create_um(self, label_template_rs=False, data=None):
        """
            Création d'une UM en auto
        """
        if not label_template_rs:
            label_template_rs = self.env['stock.label.template'].search([('type', '=', 'um')], limit=1)
        
        if label_template_rs:
            vals = {'template_id': label_template_rs.id}
            if data:
                vals.update(data)
                
            new_um_rs = self.create(vals)
            new_um_rs.wkf_available()
        else:
            new_um_rs = False
            
        return new_um_rs
    
    
    def balancing(self, qty, location=False, move_rs=None, done=True, counterpart_location_id=False, is_variable_double_unit=False, sec_qty=False):
        """
            Equilibrage d'étiquette: Permet de faire le/les mouvement(s) nécessaire(s) pour avoir 
            l'étiquette demandée à la quantité demandée pour l'emplacement demandé
            :param self: Liste des étiquettes à mettre à jour
            :type self: stock.label
            :param qty: Quantité finale
            :type qty: float
            :param location: Si remplis: mouvement de l'étiquette vers cet emplacement
            :type location: recordset: stock.location
            :param counterpart_location_id: Si remplis, utilisé en emplacement de contrepartie sinon, utilisation ce celui du modèle d'étiquette 
            :type counterpart_location_id: int
            :return: liste des mouvements créés
            :rtype: stock.move
        """
        move_create_rcs = self.env['stock.move']
        move_obj = self.with_context({'force_done': True}).env['stock.move']
        if not counterpart_location_id:
            counterpart_location_id = self.template_id.counterpart_location_id.id
            
        # Si l'étiquette est active
        if self.is_active:
            # Si on passe un mouvement et que son emplacement source n'est pas le même que celui de l'étiquette, mouvement de cette étiquette 
            if move_rs and move_rs.location_id != self.location_id:
                self.move(location=move_rs.location_id)
            
            # Double unité
            if is_variable_double_unit:
                # Si les deux quantités demandées sont inférieur aux deux quantités de l'étiquette: mouvement sortant
                if (qty < self.uom_qty or qty == self.uom_qty) and (sec_qty < self.sec_uom_qty or sec_qty == self.sec_uom_qty):
                    diff_qty = self.uom_qty - qty
                    diff_sec_qty = self.sec_uom_qty - sec_qty
                    move_create_rcs += move_obj.create_move_label(self, diff_qty, self.location_id.id, counterpart_location_id, move_rs=move_rs, done=done, sec_qty=diff_sec_qty)
                # Si les deux quantités demandées sont supérieur aux deux quantités de l'étiquette: mouvement entrant
                elif (qty > self.uom_qty or qty == self.uom_qty) and (sec_qty > self.sec_uom_qty or sec_qty == self.sec_uom_qty):
                    diff_qty = qty - self.uom_qty
                    diff_sec_qty = sec_qty - self.sec_uom_qty
                    move_create_rcs += move_obj.create_move_label(self, diff_qty, counterpart_location_id, self.location_id.id, done=done, sec_qty=diff_sec_qty)
                # Si qté UdM demandée < qté UdM étiquette et qté sec. UdM demandée > qté sec. UdM étiquette: mouvement sortant UdM et mouvement entrant sec. UdM 
                elif qty < self.uom_qty and sec_qty > self.sec_uom_qty:
                    diff_qty = self.uom_qty - qty
                    move_create_rcs += move_obj.create_move_label(self, diff_qty, self.location_id.id, counterpart_location_id, move_rs=move_rs, done=done, sec_qty=0)
                    diff_sec_qty = sec_qty - self.sec_uom_qty 
                    move_create_rcs += move_obj.create_move_label(self, 0, counterpart_location_id, self.location_id.id, done=done, sec_qty=diff_sec_qty)
                # Si qté UdM demandée > qté UdM étiquette et qté sec. UdM demandée < qté sec. UdM étiquette: mouvement entrant UdM et mouvement sortant sec. UdM 
                elif qty > self.uom_qty and sec_qty < self.sec_uom_qty :
                    diff_qty = qty - self.uom_qty
                    move_create_rcs += move_obj.create_move_label(self, diff_qty, counterpart_location_id, self.location_id.id, done=done, sec_qty=0)
                    diff_sec_qty = self.sec_uom_qty - sec_qty
                    move_create_rcs += move_obj.create_move_label(self, 0, self.location_id.id, counterpart_location_id, move_rs=move_rs, done=done, sec_qty=diff_sec_qty)
            # Simple unitée
            else:
                # Si la quantité demandée est inférieur à la quantité de l'étiquette: mouvement sortant
                if qty < self.uom_qty:
                    diff_qty = self.uom_qty - qty
                    move_create_rcs += move_obj.create_move_label(self, diff_qty, self.location_id.id, counterpart_location_id, move_rs=move_rs, done=done)
                # Si la quantité demandée est supérieur à la quantité de l'étiquette: mouvement entrant
                elif qty > self.uom_qty:
                    diff_qty = qty - self.uom_qty
                    move_create_rcs += move_obj.create_move_label(self, diff_qty, counterpart_location_id, self.location_id.id, done=done)
            
            if location:
                move_create_rcs += self.with_context({'force_done': True}).move(location=location, done=done)
                
        elif qty:
            if not location:
                location = self.last_move_id.location_id
                
            # Soustraction au cas ou une des deux quantité n'est pas à 0 
            if is_variable_double_unit:
                move_create_rcs += move_obj.create_move_label(self, qty - self.uom_qty, counterpart_location_id, location.id, done=done, sec_qty=sec_qty - self.sec_uom_qty)
            else:
                move_create_rcs += move_obj.create_move_label(self, qty - self.uom_qty, counterpart_location_id, location.id, done=done)
                
            
        return move_create_rcs

    
    @api.multi 
    def equal_split(self, number, is_variable_double_unit):
        """
            Split d'étiquette
            :param self: Liste des étiquettes à mettre à jour
            :type self: stock.label
            :param number: Nouveau nombre d'étiquettes à créer à partir de celle-ci
            :type number: float
            :return: True
            :rtype: boolean
        """
        if number:
            label_number = number - 1
            for label in self:
                new_qty = label.uom_qty / float(number)
                sec_new_qty = label.sec_uom_qty / float(number)
                for dummy in range(label_number):
                    new_label = label.copy(default={'origin_label_id': label.id})
                    new_label.balancing(new_qty, location=label.location_id, is_variable_double_unit=is_variable_double_unit, sec_qty=sec_new_qty)
                    
                label.balancing(new_qty, is_variable_double_unit=is_variable_double_unit, sec_qty=sec_new_qty)
            
        return True


    @api.multi
    def split(self, remaining_qty, sec_remaining_qty, is_variable_double_unit):
        """
            Split d'étiquette
            :param self: Liste des étiquettes à mettre à jour
            :type self: stock.label
            :param remaining_qty: Quantité restante (UdM)
            :type remaining_qty: float
            :param sec_remaining_qty: Quantité restante (Sec. UdM)
            :type sec_remaining_qty: float
            :param is_variable_double_unit: Permet de savoir si le produit est en double unité variable
            :type is_variable_double_unit: boolean
            :return: True
            :rtype: boolean
        """
        if remaining_qty <= 0 or (is_variable_double_unit and sec_remaining_qty <= 0):
            raise except_orm(_('Error'), _('Remaining qty must be greater than 0.'))
        
        for label in self:
            sec_new_qty = 0.0
            new_qty = label.uom_qty - remaining_qty
            if new_qty > 0:
                # Gestion de la double unité variable
                if is_variable_double_unit:
                    sec_new_qty = label.sec_uom_qty - sec_remaining_qty
                    if sec_new_qty <= 0:
                        raise except_orm(_('Error'), _('Remaining qty must be lower than %.2f.')%(label.sec_uom_qty))                

                new_label = label.copy(default={'origin_label_id': label.id})
                new_label.balancing(new_qty, location=label.location_id, is_variable_double_unit=is_variable_double_unit, sec_qty=sec_new_qty)
                label.balancing(remaining_qty, is_variable_double_unit=is_variable_double_unit, sec_qty=sec_remaining_qty)
            else:
                raise except_orm(_('Error'), _('Remaining qty must be lower than %.2f.')%(label.uom_qty))                
            
        return True
    
    
    def recursion_traceability_downstream(self, rec=True):
        """
            Retourne les étiquettes qui se composent des étiquettes passées en paramètre (traçabilité aval)
            :param self: Liste des étiquettes
            :type self: stock.label
            :param rec: True si l'on veux les étiquettes sur plusieurs niveau. False si on ne veut que le premier niveau
            :type rec: boolean
            :return: Liste des ids des étiquettes
            :rtype: list
        """
        self.env.cr.execute("""
        SELECT
          distinct final_label.id
        FROM
          stock_label final_label
          JOIN stock_move_label final_move_label ON final_move_label.label_id = final_label.id
          JOIN stock_move final_move ON final_move_label.move_id = final_move.id
          JOIN mrp_workorder wo ON final_move.wo_outgoing_id IN (select id FROM mrp_workorder where mo_id = wo.mo_id)
          JOIN stock_move init_move ON init_move.wo_incoming_id IN (select id FROM mrp_workorder where mo_id = wo.mo_id)
          JOIN stock_move_label init_move_label ON init_move_label.move_id = init_move.id
          JOIN stock_label init_label ON init_move_label.label_id = init_label.id
        WHERE
          init_label.id IN %s
        """, [tuple(self.ids)])
        
        query_res = [x[0] for x in self.env.cr.fetchall()]
        res = query_res
        if rec and query_res:
            res.extend(self.browse(query_res).recursion_traceability_downstream(rec=rec))
        
        return list(set(res))
        

    @api.multi
    def wkf_draft(self):
        self.write({'state': 'draft', 'is_active': False})


    @api.one
    def wkf_available(self):
        vals = {'state': 'available', 'is_active': True}
        if self.name == '/':
            vals['name'] = self.template_id.sequence_id.next_by_id()
            
        self.write(vals)


    @api.multi
    def wkf_reserved(self, move_location_id, move_id, uom_qty):        
        """
            Passage de l'étiquette en état réservé si elle n'est pas dans l'un des états suivant: Contrôle, Quarantaine, Résrervé
            Erreur si on essaye de passer un mouvement Contrôle ou quarantaine réservé alors que l'emplacement source du mouvement n'est pas control ou quanrantine
            :param self: Liste des étiquettes à mettre à jour
            :type self: stock.label
            :param move_location_id: Empalcement source du mouvement
            :type move_location_id: stock.location
        """
        for label in self.read(['state', 'name']):
            err = False
            write = True
            if label['state'] == 'reserved':
                # Si la demande viens de la consommation: Test selon la quantité réservée et non l'état
                # (Possibilité d'affecter plusieurs fois l'étiquette avec une partie de la quantité)
                if not self.env.context.get('wkf_reserved_from_consumtion', False) or self.browse(label['id']).get_available_qty(move_id) <= 0:
                    err = True
                
            elif label['state'] == 'control':
                write = False
                if not move_location_id.control:
                    err = True
                    
            elif label['state'] == 'quarantine':
                write = False
                if not move_location_id.quarantine:
                    err = True
                    
            if err:
                raise except_orm(_('Error !'), _('Label %s cannot be reserved. Its state is %s')%(label['name'], label['state']))
            elif write:
                self.browse(label['id']).write({'state': 'reserved'})


    @api.multi
    def wkf_control(self):
        self.write({'state': 'control'})


    @api.multi
    def wkf_quarantine(self):
        self.write({'state': 'quarantine'})


    @api.multi
    def wkf_unreserved(self, forced_qty=False):
        for label in self:
            qty = forced_qty or label.uom_qty 
            if qty > 0:
                label.wkf_available()
            else:
                label.wkf_inactive()


    @api.multi
    def wkf_inactive(self):
        self.write({'state': 'inactive', 'is_active': False, 'uom_qty': 0.0, 'sec_uom_qty': 0.0, 'um_label_id': False})
    
    
    @api.multi
    def do_print_label(self, send_printer_list=None, send_printer_id=None):
        return True
    
    
    @api.multi
    def unlink(self):
        if self.env['stock.move.label'].search([('label_id', 'in', self.ids)]):
            raise except_orm(_('Error !'), _('Impossible to delete a record used in a stock move'))
        
        return super(stock_label, self).unlink()
        
        
    @api.multi
    def show_traceability_upstream(self):
        self.ensure_one()
        self.env['traceability.wizard'].build_traceability_upstream(label_id=self.id)
        return {
                'view_type': 'tree',
                'view_mode': 'tree',
                'res_model': 'traceability.wizard',
                'domain': [('initial_label_id', '=', self.id), ('parent_id', '=', False)],
                'target': 'new',
                'type': 'ir.actions.act_window',
        }
        
        
    @api.multi
    def show_traceability_downstream(self):
        self.ensure_one()
        self.env['traceability.wizard'].build_traceability_downstream(label_id=self.id)
        return {
                'view_type': 'tree',
                'view_mode': 'tree',
                'res_model': 'traceability.wizard',
                'domain': [('initial_label_id', '=', self.id), ('parent_id', '=', False)],
                'target': 'new',
                'type': 'ir.actions.act_window',
        }
    
    
    def assign_um_label(self, um_label):
        """
            Fonction qui rattache une UM à une UC
        """
#         for label in self:
#             if label.location_id.id != uc_label.location_id.id:
#                 label.move(uc_label.location_id)
        location_id = um_label.uc_label_ids and um_label.uc_label_ids[0].location_id.id or False
        for uc_label in self:
            if not location_id:
                location_id = uc_label.location_id.id
            
            if location_id != uc_label.location_id.id:
                raise  except_orm(_('Error'), _('All labels on the UM must be in the same location.'))
            
        self.write({'um_label_id': um_label.id})
        return True
    
    @api.multi
    def button_unassign_um_label(self):
        """
            Fonction qui détacher une UM à une UC
        """
        self.write({'um_label_id': False})
        return {'type':'ir.actions.act_window_view_reload'}
    
    
    def additional_function_domain(self, arg):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de mrp_routing_line
        """
        arg0, arg1, arg_1 = False, False, False
        if arg and arg[0] == 'quality_label_ids':
            arg0 = 'id'
            arg1 = arg[1]
            arg_1 = arg[-1] and arg[-1][0] and arg[-1][0][-1] or []
            
        return arg0, arg1, arg_1
    
    
    def compute_domain_args_resource(self, args):
        #Pour ne pas pouvoir sélectionner dans les catégories des lignes de gammes deux fois la même ressource
        #Et permet également dans le wizard de déclaration des temps d'avoir les ressources associées au wo entré
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
    def search(self, args=None, offset=0, limit=None, order=None, count=None):
        args = args or []
        args_modified = self.compute_domain_args_resource(args)
        return super(stock_label, self).search(args=args_modified, offset=offset, limit=limit, order=order, count=count) 
    
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=1000):
        """
            Fonction name_search
        """
        args.append(('name', 'ilike', name))
        args = self.compute_domain_args_resource(args)
        recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()
    

    
class stock_move_lot(models.Model):
    """ 
    Move lot
    """
    _name = 'stock.move.lot'
    _description = 'Move lot'
    _rec_name = 'move_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    move_id = fields.Many2one('stock.move', string='Move', required=True, ondelete='cascade', select=True)
    lot_id = fields.Many2one('stock.lot', string='Lot', required=False, ondelete='cascade', select=True)
    
    
    
class stock_move_label(models.Model):
    """ 
    Move label 
    """
    _name = 'stock.move.label'
    _description = 'Move label'
    _rec_name = 'move_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    move_id = fields.Many2one('stock.move', string='Move', required=True, ondelete='cascade', select=True)
    label_id = fields.Many2one('stock.label', string='Label', required=False, ondelete='cascade', select=True)
    uom_qty = fields.Float(string='UoM qty', required=False, digits=dp.get_precision('Product quantity'), default=0.0)
    uom_id = fields.Many2one('product.uom', string='UoM', readonly=True, ondelete='cascade')
    sec_uom_qty = fields.Float(string='Second UoM qty', required=False, digits=dp.get_precision('Product quantity'), default=0.0)
    sec_uom_id = fields.Many2one('product.uom', string='Second UoM', readonly=True, ondelete='cascade')
    for_quarantine = fields.Boolean(string='For quarantine', default=False)
    done_date = fields.Datetime()
    is_variable_double_unit = fields.Boolean(default=False)
    
    
    def create_move_label(self, label_rs, location_dest_id=False, move_rs=False, dict_label_qty=None, inactive=False, other_data=None):
        """
            Création d'un move_label et éventuellement de son mouvement associé
            :type self: stock.move.label
            :param label_rs: Étiquettes
            :type label_rs: recordsets: stock.label
            :param location_dest_id: Emplacement de destination pour création du mouvement si move_rs est vide
            :type location_dest_id: recordset: stock.location
            :param move_rs: Mouvement de stock. Si vide: création d'un mouvement
            :type move_rs: recordset: stock.move
            :return: True
            :rtype: boolean
        """
        qty = 0.0
        if move_rs:
            move_rcs = move_rs
            if dict_label_qty:
                for l in dict_label_qty:
                    qty += dict_label_qty[l][0]
                    vals = {
                         'move_id': move_rs.id,
                         'uom_qty': dict_label_qty[l][0],
                         'sec_uom_qty': dict_label_qty[l][1],
                         'label_id': l.id,
                         'is_variable_double_unit': move_rs.is_variable_double_unit,
                                 }
                    if other_data:
                        vals.update(other_data)
                        
                    self.create(vals)
            else:
                for l in label_rs:
                    if l.state == 'inactive':
                        l_qty = l.origin_uom_qty
                        l_sec_qty = l.origin_sec_uom_qty
                    else:
                        l_qty = l.uom_qty
                        l_sec_qty = l.sec_uom_qty

                    qty += l_qty
                    vals = {
                         'move_id': move_rs.id,
                         'uom_qty': l_qty,
                         'sec_uom_qty': l_sec_qty,
                         'label_id': l.id,
                         'is_variable_double_unit': move_rs.is_variable_double_unit,
                                 }
                    if other_data:
                        vals.update(other_data)
                        
                    self.create(vals)
        else:
            # Création d'un dictionnaire avec la liste d'étiquettes par emplacement pour réduire le nombre de mouvement
            location_label = {}
            # Création d'un dictionnaire avec la quantité par emplacement pour réduire le nombre de mouvement
            location_qty = {}
            move_rcs = move_obj = self.env['stock.move']
            for label in label_rs:
                if (label.location_id.id, label.product_id) in location_label:
                    location_label[label.location_id.id, label.product_id].append(label)
                    location_qty[label.location_id.id, label.product_id] += label.uom_qty
                else:
                    location_label[label.location_id.id, label.product_id] = [label]
                    location_qty[label.location_id.id, label.product_id] = label.uom_qty

            for location_product_id, labels in location_label.iteritems():
                move_rs = move_obj.create_move(location_product_id[1], location_product_id[0], location_dest_id, location_qty[location_product_id], other_data={'valid_label': True})
                move_rcs |= move_rs 
                for l in labels:
                    qty += l.uom_qty
                    vals = {
                      'move_id': move_rs.id,
                      'uom_qty': l.uom_qty,
                      'sec_uom_qty': l.sec_uom_qty,
                      'label_id': l.id,
                      'is_variable_double_unit': move_rs.read(['is_variable_double_unit'])[0]['is_variable_double_unit'],
                                  }
                    
                    if other_data:
                        vals.update(other_data)
                        
                    self.create(vals)
            
        return move_rcs, qty
    
    
    def compute_last_move(self, move):
        # TODO: SQL pour perf
        res = self.search([('label_id', '=', self.label_id.id),
                           ('move_id.location_dest_id', '=', move.location_id.id), 
                           ('move_id.state', '=', 'done'),
                           ('move_id.type', '!=', 'out'),
                           ('move_id', '!=', self.move_id.id),
                            ], order='done_date desc', limit=1)
        if not res:
            res = self.search([('label_id', '=', self.label_id.id),
                               ('move_id.state', '=', 'done'),
                               ('move_id.type', '!=', 'out'),
                               ('move_id', '!=', self.move_id.id),
                                ], order='done_date desc', limit=1)
            
        return res.move_id
    
    
    @api.one
    def update_labels(self, move, action):
        """
            Mise à jour des étiquettes d'un mouvement
            :type self: stock.move.label
            :param move: Mouvement des étiquettes à mettre à jour
            :type move: recordset: stock.move
            :param action: Action du mouvement: valeurs possibles: (draft, done, cancel)
            :type action: string
            :return: True
            :rtype: boolean
        """
        dp_obj = self.env['decimal.precision']
        if self.label_id.state == 'draft':
            self.label_id.wkf_available()
        
        new_location = False
        if self.label_id.state in ('reserved', 'quarantine', 'control'):
            # Condition faite pour éviter le passage de l'état de l'étiquette de reservé à inactive alors que l'on veut incrémenter sa quantité 
            if move.type == 'in' and action == 'done':
                forced_qty = self.uom_qty + self.label_id.uom_qty
            else:
                forced_qty = False
                 
            self.label_id.wkf_unreserved(forced_qty=forced_qty)
        
        # Si le mouvement passe à done
        if action == 'done':
            vals = {'last_move_id': move.id}
                
            # Mouvement entrant
            if move.type == 'in':
                vals['location_id'] = move.location_dest_id.id
                vals['warehouse_id'] = move.location_dest_id.warehouse_id.id
                new_location = move.location_dest_id
#                 vals['um_label_id'] = move.um_label_dest_id.id
                vals['uom_qty'] = self.uom_qty + self.label_id.uom_qty
                if move.is_variable_double_unit:
                    vals['sec_uom_qty'] = self.sec_uom_qty + self.label_id.sec_uom_qty
                    
                if self.uom_qty and self.label_id.state in ('inactive'):
                    self.label_id.wkf_available()
                
                if not self.label_id.first_move_id:
                    vals['first_move_id'] = move.id
                
            else:
                # Interdiction de faire un done si l'étiquette n'est pas dans l'emplacement source du mouvement
                if move.location_id.id != self.label_id.location_id.id:
                    raise except_orm(_('Error'), _('Label %s is not in location %s (Stock move with id %d).')%(self.label_id.name, self.label_id.location_id.name, move.id))
                
                # Mouvement sortant
                if move.type == 'out':
                    delta = float_compare(self.label_id.uom_qty, self.uom_qty, precision_digits=dp_obj.precision_get('Product quantity'))
                    # Si la quantité de l'étiquette est supérieur à la quantité du mouvement: soustraction de la quantité du mouvement à la quantité de l'étiquette
                    if delta == 1:
                        vals['uom_qty'] = self.label_id.uom_qty - self.uom_qty
                        if move.is_variable_double_unit:
                            vals['sec_uom_qty'] = self.label_id.sec_uom_qty - self.sec_uom_qty
                            
                    # Si la quantité de l'étiquette est inférieur ou égale à la quantité du mouvement: désactivation de l'étiquette
                    else:
                        # Impossible de traiter un mouvement avec une quantité de move_label > à la quantité de l'étiquette
                        if self.label_id.uom_qty < self.uom_qty:
                            raise except_orm(_('Error'), _('Label quantity cannot be negative (Label %s, Stock move with id %d).')%(self.label_id.name, move.id))
                        
                        vals['location_id'] = move.location_dest_id.id
                        self.label_id.wkf_inactive()
                        
                else:
                    vals['location_id'] = move.location_dest_id.id
                    vals['warehouse_id'] = move.location_dest_id.warehouse_id.id
                    new_location = move.location_dest_id
#                     vals['um_label_id'] = move.um_label_dest_id.id
            
            self.label_id.write(vals)
        # Si le mouvement passe à cancel
        elif action == 'cancel':
            if self.label_id.last_move_id.id and self.label_id.last_move_id.id == move.id:
                last_move = self.compute_last_move(move)
                if last_move:
                    vals = {'last_move_id': last_move.id}
                else:
                    vals = {'last_move_id': False}
                     
                # Mouvement sortant
                if move.type == 'out':
                    vals['location_id'] = move.location_id.id
                    vals['warehouse_id'] = move.location_id.warehouse_id.id
                    new_location = move.location_id
#                     vals['um_label_id'] = move.um_label_id.id
                    vals['uom_qty'] = self.uom_qty + self.label_id.uom_qty
                    if move.is_variable_double_unit:
                        vals['sec_uom_qty'] = self.sec_uom_qty + self.label_id.sec_uom_qty
                        
                    if self.uom_qty and self.label_id.state == 'inactive':
                        self.label_id.wkf_available()
                        
                # Mouvement entrant
                elif move.type == 'in':
                    delta = float_compare(self.label_id.uom_qty, self.uom_qty, precision_digits=dp_obj.precision_get('Product quantity'))
                    # Si la quantité de l'étiquette est supérieur à la quantité du mouvement: soustraction de la quantité du mouvement à la quantité de l'étiquette
                    if delta == 1:
                        vals['uom_qty'] = self.label_id.uom_qty - self.uom_qty
                        if move.is_variable_double_unit:
                            vals['sec_uom_qty'] = self.label_id.sec_uom_qty - self.sec_uom_qty
                        
                    # Si la quantité de l'étiquette est inférieur ou égale à la quantité du mouvement: désactivation de l'étiquette
                    else:
                        self.label_id.wkf_inactive()
                        
                else:
                    vals['location_id'] = move.location_id.id
                    vals['warehouse_id'] = move.location_id.warehouse_id.id
                    new_location = move.location_id
#                     vals['um_label_id'] = move.um_label_id.id
                    
            else:
                raise except_orm(_('Error'), _('The stock move with id %d is not the last stock move of label %s.')%(move.id, self.label_id.name))
                        
            self.label_id.write(vals)
        
        if new_location:
            if new_location.control:
                self.label_id.wkf_control()
            elif new_location.quarantine:
                self.label_id.wkf_quarantine()
                
        return True
    
    
    @api.multi
    def unlink_button(self):
        self.unlink()
        return {'type': 'ir.actions.act_window_view_reload'}
    
    
    @api.model
    def create(self, vals):
        """
        
        """
        res = super(stock_move_label, self).create(vals=vals)
        if vals.get('label_id') and vals.get('move_id') and not self.env.context.get('override_reserved_test', False):
            move = self.env['stock.move'].browse(vals['move_id'])
            if move.state == 'waiting':
                self.env['stock.label'].browse(vals['label_id']).wkf_reserved(move.location_id, move.id, vals.get('uom_qty', 0.0))
            
        return res
    
    
    @api.multi
    def write(self, vals):
        """
        
        """
        res = super(stock_move_label, self).write(vals=vals)
        if vals.get('label_id'):
            label_obj = self.env['stock.label']
            for move_label in self:
                if move_label.move_id.state == 'waiting':
                    label_obj.browse(vals.get('label_id', move_label.label_id.id)).wkf_reserved(move_label.move_id.location_id,
                                                                                                move_label.move_id.id, 
                                                                                                vals.get('uom_qty', self.uom_qty))
            
        return res
    
    
    @api.multi
    def unlink(self):
        """
        
        """
        for move_label in self:
            if move_label.move_id.read(['state'])[0]['state'] == 'waiting':
                move_label.label_id.wkf_unreserved()
            
        return super(stock_move_label, self).unlink()
    
    
    
class stock_valuation(models.Model):
    """ 
    Valuation 
    """
    _name = 'stock.valuation'
    _description = 'Valuation'
    
    @api.model
    def _month_get(self):
        return [
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

    
    def _supply_method_get(self):
        return [
            ('buy', _('Buy')),
               ]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    month = fields.Selection('_month_get', string='Month', required=True)
    year = fields.Char(string='Year', size=4, required=True)
    depreciation_coeff = fields.Float(string="Depreciation Coefficient", required=True, default=1)
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='restrict')
    qty_in_stock = fields.Float(digits=dp.get_precision('Product quantity'), default=0.0)
    valuation = fields.Float(string='Valuation', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    price = fields.Float(string='Price', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    deprecated_valuation = fields.Float(string='Deprecated Valuation', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    deprecated_price = fields.Float(string='Deprecated price', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    last_qty = fields.Float(digits=dp.get_precision('Product quantity'), default=0.0)
    last_valuation = fields.Float(string='Last valuation', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    last_price = fields.Float(string='Last Price', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    valuation_gap = fields.Float(string='Valuation Gap', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    price_gap = fields.Float(string='Price Gap', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    price_gap_percent = fields.Float(string='Price Gap Percent', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    valuation_gap_percent = fields.Float(string='Valuation Gap Percent', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    supply_method = fields.Selection('_supply_method_get', string='Supply method', required=True, default='buy', 
                        help="Produce will generate production order or tasks, according to the product type. Buy will trigger purchase orders when requested.")
    valuation_theo = fields.Float(string='Valuation', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    price_theo = fields.Float(string='Price', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    deprecated_valuation_theo = fields.Float(string='Deprecated Valuation', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    deprecated_price_theo = fields.Float(string='Deprecated price', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    last_valuation_theo = fields.Float(string='Last valuation', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    last_price_theo = fields.Float(string='Last Price', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    valuation_gap_theo = fields.Float(string='Valuation Gap', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    price_gap_theo = fields.Float(string='Price Gap', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    price_gap_percent_theo = fields.Float(string='Price Gap Percent', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    valuation_gap_percent_theo = fields.Float(string='Valuation Gap Percent', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=False, ondelete='restrict')
    comment = fields.Char(string='Comment', size=256, required=False)
    uom_id = fields.Many2one('product.uom', string='UoM', required=False, ondelete='restrict')
    
    
    def _get_depreciation_coeff(self, moves_for_period):
        depreciation_coeff = 1
        if len(moves_for_period):
            config_obj = self.env['stock.config.settings']
            date_last_move = datetime.strptime(moves_for_period[0].date, DEFAULT_SERVER_DATETIME_FORMAT).date()
            if date_last_move - date.today() >  timedelta(days=365*2):
                depreciation_coeff = config_obj.get_param('depreciation_coeff_2y')
            elif date_last_move - date.today() >  timedelta(days=365):
                depreciation_coeff = config_obj.get_param('depreciation_coeff_1y')
        return depreciation_coeff
    
    
    def _get_price_pmp(self, moves, last_valuation_id, uom_obj, product=False, svam_dico=None):
        """
            Fonction qui permet de calculer le PMP sur une liste de mouvement et la valo du mois précédent la première date du mouvement
            :param moves: Recordset de mouvement
            :type move: recordset: stock.move
            :param last_valuation_id: valo du mois précédent la première date du mouvement
            :type last_valuation_id: recordset: stock.valuation
            :param svam_dico: Utilisé dans l'objet stock_valuation_account_move permet de passer un dico avec toutes les valeurs permettant de créer une pièce comptable et ses écritures
            :type svam_dico: dico
            :return: True
            :rtype: tuple
        
        """
        price = last_valuation_id['price']
        price_theo = last_valuation_id['price_theo']
        qty = last_valuation_id['qty_in_stock']
        uom_last = 'uom_id' in last_valuation_id and last_valuation_id['uom_id']
        account_move_obj = self.env['account.move']
        period_obj = self.env['account.period']
        account_move_rcs = self.env['account.move']
        lot_obj = self.env['stock.lot']
        uom_obj = self.env['product.uom']
        if uom_last and uom_last.id != product.uom_id.id:
            price = price * 1 / uom_obj._compute_qty_obj(uom_last, 1, product.uom_id)
            price_theo = price_theo * 1 / uom_obj._compute_qty_obj(uom_last, 1, product.uom_id)
            qty = uom_obj._compute_qty_obj(uom_last, qty, product.uom_id)
            
        for move in moves:
            freight_price = 0
            if move.freight_price:
                if move.freight_currency_id:
                    freight_price = move.freight_currency_id.compute(move.freight_price, move.company_id.currency_id)
                else:
                    freight_price = move.freight_price
            
            uom_qty = move.get_product_uom_qty()
            if move.type == 'in' and move.partner_price and (qty + uom_qty) and move.uoi_qty:
                if move.currency_id:                            
                    price_curr_comp = move.currency_id.compute(move.partner_price, move.company_id.currency_id)
                else:
                    price_curr_comp = move.partner_price
                
                
                price_curr_comp_uom_move = price_curr_comp * move.uoi_qty / move.uom_qty
                price_curr_comp_uom = price_curr_comp_uom_move * move.uom_qty / uom_qty
                price = (price*qty + price_curr_comp_uom*uom_qty + freight_price)/(qty + uom_qty)
            
            if move.type == 'in' and move.theo_price and (qty + move.uom_qty) and move.uoi_qty:
                if move.currency_id:
                    price_curr_comp_theo = move.currency_id.compute(move.theo_price, move.company_id.currency_id)
                else:
                    price_curr_comp_theo = move.theo_price
                    
                price_curr_comp_uom_move_theo = price_curr_comp_theo * move.uoi_qty / move.uom_qty 
                price_curr_comp_uom_theo = price_curr_comp_uom_move_theo * move.uom_qty / uom_qty
                price_theo = (price_theo*qty + price_curr_comp_uom_theo*uom_qty + freight_price)/(qty + uom_qty)
                
            qty = qty + uom_qty * (-1 if move.type == 'out' else 1)
            # Partie permetant à l'object stock_valuation_account_move de créer une pièce comptable et ses écritures
            if svam_dico and \
               (('account_stock_in_id' in svam_dico and svam_dico['account_stock_in_id'] and 'account_stock_out_id' in svam_dico and svam_dico['account_stock_out_id'] and 'account_stock_value_in_id' in svam_dico and svam_dico['account_stock_value_in_id'] and 'account_stock_value_out_id' in svam_dico and svam_dico['account_stock_value_out_id']) or \
               ('account_material_purchase_id' in svam_dico and svam_dico['account_material_purchase_id'] and 'account_applied_overhead_id' in svam_dico and svam_dico['account_applied_overhead_id'] and 'account_work_in_progress_id' in svam_dico and svam_dico['account_work_in_progress_id'] and 'account_finish_good_inv_id' in svam_dico and svam_dico['account_finish_good_inv_id'])):
                if 'is_lot' in svam_dico and svam_dico['is_lot']:
                    self.env.cr.execute(""" 
                        select 
                            sum(uom_qty) as uom_qty
                        from 
                            stock_move_label 
                        where 
                            move_id = %s and
                            label_id in (select 
                                    id
                                    from 
                                    stock_label
                                    where
                                    lot_id = %s)
                        group by 
                            move_id """, (move.id, svam_dico['lot_id']))
                    res_product_lot_sql = self.env.cr.dictfetchall()
                    uom_qty = [res_product_lot['uom_qty'] for res_product_lot in res_product_lot_sql][0]
                
                account_move_rcs = self.function_accounting_entry_us(svam_dico, price, uom_qty, move, qty, price_theo, account_move_rcs, 
                                                                      account_move_obj, period_obj, lot_obj)
        if svam_dico:
            return account_move_rcs
        
        return (price, price_theo, qty)
    
    
    def function_accounting_entry_us(self, svam_dico, price, uom_qty, move, qty, price_theo, account_move_rcs, account_move_obj, period_obj, lot_obj):
        return account_move_rcs
    
    
    def _clean_records(self, product_id, month, year, warehouse_id=False, model=''):
        list_search = []
        if model:
            if warehouse_id:
                list_search.append(('warehouse_id', '=', warehouse_id))
            
            if product_id:
                list_search.append(('product_id', '=', product_id.id))
                
            list_search.extend([ '|',
                                 ('year', '>', year),
                                 '&',
                                 ('month', '>=', month),
                                 ('year', '=', year)])
        
            current_valuation = self.env[model].search(list_search)
            current_valuation.unlink()
     
     
    @api.model
    def calculate_for_product(self, product_id, month, year, warehouse_id, method="pmp", clean=True):
        uom_obj = self.env['product.uom']
        move_obj = self.env['stock.move']
        date_start = parse(' '.join((year, month, '01')))
        if clean:
            self._clean_records(product_id, month, year, warehouse_id=warehouse_id, model='stock.valuation')
        
        for date_start in rrule(MONTHLY, dtstart=date_start, until=datetime.now()):
            date_end = date_start + relativedelta(day=1, months=+1, days=-1)
            
            last_month = date_start + relativedelta(months=-1)
            last_valuation_id = self.search([('product_id', '=', product_id.id), ('month', '=', str(last_month.month).zfill(2)), ('year', '=', last_month.year), ('warehouse_id', '=', warehouse_id)])
            if not len(last_valuation_id):
                last_valuation_id = self.default_get(('qty_in_stock', 'valuation', 'price', 'valuation_theo', 'price_theo', 'uom_id'))
            
            
            date_start_move = '%s 00:00:00'%(date_start.strftime('%Y-%m-%d'))
            date_end_move = '%s 23:59:59'%(date_end.strftime('%Y-%m-%d'))
            if self.env.user.company_id.tz:
                date_start_move = convert_tz(date_start_move, self.env.user.company_id.tz, 'UTC').strftime('%Y-%m-%d %H:%M:%S')
                date_end_move = convert_tz(date_end_move, self.env.user.company_id.tz, 'UTC').strftime('%Y-%m-%d %H:%M:%S')
            
            moves_for_period = move_obj.search([
                                                  ('date', '>=', date_start_move),
                                                  ('date', '<=', date_end_move),
                                                  ('product_id', '=', product_id.id),
                                                  ('state', '=', 'done'),
                                                  ('type', 'in', ['in', 'out']),
                                                  ('warehouse_id', '=', warehouse_id)
                                                  ], order="date ASC")
            depreciation_coeff = self._get_depreciation_coeff(moves_for_period)
            price, price_theo, qty = self._get_price_pmp(moves_for_period, last_valuation_id, uom_obj, product=product_id)
            valuation = qty * price
            price_gap = price - last_valuation_id['price']
            valuation_gap = valuation - last_valuation_id['valuation']
            valuation_theo = qty * price_theo
            price_gap_theo = price_theo - last_valuation_id['price_theo']
            valuation_gap_theo = valuation - last_valuation_id['valuation_theo']
            vals_valuation = {
                         'month': str(date_start.month).zfill(2),
                         'year': date_start.year,
                         'depreciation_coeff': depreciation_coeff,
                         'product_id': product_id.id,
                         'uom_id': product_id.uom_id.id,
                         'qty_in_stock': qty,
                         'valuation': valuation,
                         'valuation_theo': valuation_theo,
                         'price': price,
                         'price_theo': price_theo,
                         'deprecated_valuation': valuation * depreciation_coeff,
                         'deprecated_valuation_theo': valuation_theo * depreciation_coeff,
                         'deprecated_price': price * depreciation_coeff,
                         'deprecated_price_theo': price_theo * depreciation_coeff,
                         'last_qty': last_valuation_id['qty_in_stock'],
                         'last_valuation': last_valuation_id['valuation'],
                         'last_valuation_theo': last_valuation_id['valuation_theo'],
                         'last_price': last_valuation_id['price'],
                         'last_price_theo': last_valuation_id['price_theo'],
                         'valuation_gap': valuation_gap,
                         'valuation_gap_theo': valuation_gap_theo,
                         'price_gap': price_gap,
                         'price_gap_theo': price_gap_theo,
                         'price_gap_percent': 100 * price_gap / last_valuation_id['price'] if last_valuation_id['price'] else 0,
                         'price_gap_percent_theo': 100 * price_gap_theo / last_valuation_id['price_theo'] if last_valuation_id['price_theo'] else 0,
                         'valuation_gap_percent': 100 * valuation_gap / last_valuation_id['valuation'] if last_valuation_id['valuation'] else 0,
                         'valuation_gap_percent_theo': 100 * valuation_gap_theo / last_valuation_id['valuation_theo'] if last_valuation_id['valuation_theo'] else 0,
                         'supply_method': product_id.supply_method,
                         'warehouse_id': warehouse_id}
            
            if vals_valuation['qty_in_stock']:
                self.create(vals_valuation)
        
        
    @api.model
    def calculate_all_products(self, month, year, warehouse_id):
        self._clean_records(None, month, year, warehouse_id=warehouse_id, model='stock.valuation')
        for product_id in self.env['product.product'].search([('is_int', '!=', True), ('type', '=', 'stockable')]):
            self.calculate_for_product(product_id, month, year, warehouse_id)
            
    
    @api.model
    def cron_calculate_all_products(self):
        """
            Cron qui lance la création des lignes de PMP sur le mois précédent
        """
        product_obj = self.env['product.product']
        last_month = datetime.strptime(fields.Date.today(), "%Y-%m-%d") - relativedelta(months=1)
        for warehouse in self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)]):
            self._clean_records(None, str(last_month.month).zfill(2), str(last_month.year), warehouse_id=warehouse.id, model='stock.valuation')
            for product_id in product_obj.search([('is_int', '!=', True), ('type', '=', 'stockable')]):
                self.calculate_for_product(product_id, str(last_month.month).zfill(2), str(last_month.year), warehouse.id)




class stock_valuation_lot(models.Model):
    """ 
        Valuation Lot
    """
    _name = 'stock.valuation.lot'
    _description = 'Valuation.lot'
    
    
    @api.model
    def _month_get(self):
        return [
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
    
    
    def _supply_method_get(self):
        return [
            ('buy', _('Buy')),
               ]

    #===========================================================================
    # COLUMNS
    #===========================================================================
    month = fields.Selection('_month_get', string='Month', required=True)
    year = fields.Char(string='Year', size=4, required=True)
    depreciation_coeff = fields.Float(string="Depreciation Coefficient", required=True, default=1)
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='restrict')
    lot_id = fields.Many2one('stock.lot', string='Lot', required=True, ondelete='restrict')
    qty_in_stock = fields.Float(digits=dp.get_precision('Product quantity'), default=0.0)
    valuation = fields.Float(string='Valuation', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    price = fields.Float(string='Price', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    deprecated_valuation = fields.Float(string='Deprecated Valuation', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    deprecated_price = fields.Float(string='Deprecated price', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    last_qty = fields.Float(digits=dp.get_precision('Product quantity'), default=0.0)
    last_valuation = fields.Float(string='Last valuation', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    last_price = fields.Float(string='Last Price', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    valuation_gap = fields.Float(string='Valuation Gap', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    price_gap = fields.Float(string='Price Gap', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    price_gap_percent = fields.Float(string='Price Gap Percent', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    valuation_gap_percent = fields.Float(string='Valuation Gap Percent', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    supply_method = fields.Selection('_supply_method_get', string='Supply method', required=True, default='buy', 
                        help="Produce will generate production order or tasks, according to the product type. Buy will trigger purchase orders when requested.")
    valuation_theo = fields.Float(string='Valuation', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    price_theo = fields.Float(string='Price', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    deprecated_valuation_theo = fields.Float(string='Deprecated Valuation', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    deprecated_price_theo = fields.Float(string='Deprecated price', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    last_valuation_theo = fields.Float(string='Last valuation', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    last_price_theo = fields.Float(string='Last Price', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    valuation_gap_theo = fields.Float(string='Valuation Gap', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    price_gap_theo = fields.Float(string='Price Gap', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    price_gap_percent_theo = fields.Float(string='Price Gap Percent', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    valuation_gap_percent_theo = fields.Float(string='Valuation Gap Percent', default=0.0, digits=dp.get_precision('Valuation'), required=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=False, ondelete='restrict')
    comment = fields.Char(string='Comment', size=256, required=False)
    uom_id = fields.Many2one('product.uom', string='UoM', required=False, ondelete='restrict')
    
    #===========================================================================
    # FUCTIONS
    #===========================================================================
    def _clean_records(self, product_ids, month, year, warehouse_id=False, model=''):
        """
            Fonction qui permet de supprimer les lignes de valorisations par lots avant de créer les nouvelles
        """
        if model:
            list_search = []
            if warehouse_id:
                list_search.append(('warehouse_id', '=', warehouse_id))
            
            if product_ids:
                list_search.append(('product_id', 'in', product_ids))
                
            list_search.extend([ '|',
                                 ('year', '>', year),
                                 '&',
                                 ('month', '>=', month),
                                 ('year', '=', year)])

            current_valuation = self.env[model].search(list_search)
            current_valuation.unlink()
    
    
    def _get_depreciation_coeff(self, move_date):
        """
            Fonction qui permet de calculer la dépréciation
        """
        depreciation_coeff = 1
        config_obj = self.env['stock.config.settings']
        date_last_move = datetime.strptime(move_date, DEFAULT_SERVER_DATETIME_FORMAT).date()
        if date_last_move - date.today() >  timedelta(days=365*2):
            depreciation_coeff = config_obj.get_param('depreciation_coeff_2y')
        elif date_last_move - date.today() >  timedelta(days=365):
            depreciation_coeff = config_obj.get_param('depreciation_coeff_1y')
        return depreciation_coeff
    
    
    @api.model
    def calculate_for_products(self, product_ids, month, year, company_id, warehouse_id, clean=True):
        """
            Fonction qui permet de calculer la valorisation par lot
        """
        uom_obj = self.env['product.uom']
        if clean:
            self._clean_records(product_ids, month, year, warehouse_id=warehouse_id, model='stock.valuation.lot')
        
        if product_ids:
            date_start = parse(' '.join((year, month, '01')))
            for date_start in rrule(MONTHLY, dtstart=date_start, until=datetime.now()):
                date_end = date_start + relativedelta(day=1, months=+1, days=-1)
                
                date_start_move = '%s 00:00:00'%(date_start.strftime('%Y-%m-%d'))
                date_end_move = '%s 23:59:59'%(date_end.strftime('%Y-%m-%d'))
                if self.env.user.company_id.tz:
                    date_start_move = convert_tz(date_start_move, self.env.user.company_id.tz, 'UTC').strftime('%Y-%m-%d %H:%M:%S')
                    date_end_move = convert_tz(date_end_move, self.env.user.company_id.tz, 'UTC').strftime('%Y-%m-%d %H:%M:%S')
                    
                # Requête qui va aider à générer les lignes
                self.env.cr.execute("""--requete qui calcule tout sauf les prix
                                        SELECT
                                            false as create_with_price,
                                            false as line_partner_price,
                                            false as line_theo_price,
                                            label.lot_id,
                                            max(product.id) as product_id,
                                            max(product.supply_method) as supply_method,
                                            extract(month from max(move.date)) as month,
                                            extract(year from max(move.date)) as year,
                                            min(move.date) as min_date,  
                                            sum(move_label.uom_qty) as sum_move_label,              
                                            0.0 as price_unit_real_uom,
                                            0.0 as price_unit_theo_uom,
                                            sum(case
                                                    when move.type = 'in' then (move_label.uom_qty* (product.product_uom_factor/move_label.label_uom_factor))                                        
                                                    when move.type = 'out' then (-move_label.uom_qty* (product.product_uom_factor/move_label.label_uom_factor))                       
                                                    else 0
                                                end) qty_uom,
                                            (SELECT
                                            price
                                            FROM
                                            stock_valuation_lot
                                            WHERE
                                            product_id = max(product.id) AND
                                            lot_id = label.lot_id AND
                                            month::int = (select extract(month from max(move.date) - interval '1 month')) AND
                                            (case
                                                when (select extract(month from max(move.date) - interval '1 month')) = 12 
                                                then (select extract(year from max(move.date) - interval '1 year'))
                                                else (select extract(year from max(move.date)))
                                            end) = year::int) last_valuation_lot_price,
                                            (SELECT
                                            valuation
                                            FROM
                                            stock_valuation_lot
                                            WHERE
                                            product_id = max(product.id) AND
                                            lot_id = label.lot_id AND
                                            month::int = (select extract(month from max(move.date) - interval '1 month')) AND
                                            (case
                                                when (select extract(month from max(move.date) - interval '1 month')) = 12 
                                                then (select extract(year from max(move.date) - interval '1 year'))
                                                else (select extract(year from max(move.date)))
                                            end) = year::int) last_valuation_lot_valuation,
                                            (SELECT
                                            price_theo
                                            FROM
                                            stock_valuation_lot
                                            WHERE
                                            product_id = max(product.id) AND
                                            lot_id = label.lot_id AND
                                            month::int = (select extract(month from max(move.date) - interval '1 month')) AND
                                            (case
                                                when (select extract(month from max(move.date) - interval '1 month')) = 12 
                                                then (select extract(year from max(move.date) - interval '1 year'))
                                                else (select extract(year from max(move.date)))
                                            end) = year::int) last_valuation_lot_price_theo,
                                            (SELECT
                                            valuation_theo
                                            FROM
                                            stock_valuation_lot
                                            WHERE
                                            product_id = max(product.id) AND
                                            lot_id = label.lot_id AND
                                            month::int = (select extract(month from max(move.date) - interval '1 month')) AND
                                            (case
                                                when (select extract(month from max(move.date) - interval '1 month')) = 12 
                                                then (select extract(year from max(move.date) - interval '1 year'))
                                                else (select extract(year from max(move.date)))
                                            end) = year::int) last_valuation_lot_valuation_theo,
                                            (SELECT
                                            qty_in_stock
                                            FROM
                                            stock_valuation_lot
                                            WHERE
                                            product_id = max(product.id) AND
                                            lot_id = label.lot_id AND
                                            month::int = (select extract(month from max(move.date) - interval '1 month')) AND
                                            (case
                                                when (select extract(month from max(move.date) - interval '1 month')) = 12 
                                                then (select extract(year from max(move.date) - interval '1 year'))
                                                else (select extract(year from max(move.date)))
                                            end) = year::int) last_valuation_lot_qty_in_stock,
                                            (SELECT
                                            uom_id
                                            FROM
                                            stock_valuation_lot
                                            WHERE
                                            product_id = max(product.id) AND
                                            lot_id = label.lot_id AND
                                            month::int = (select extract(month from max(move.date) - interval '1 month')) AND
                                            (case
                                                when (select extract(month from max(move.date) - interval '1 month')) = 12 
                                                then (select extract(year from max(move.date) - interval '1 year'))
                                                else (select extract(year from max(move.date)))
                                            end) = year::int) last_valuation_lot_uom,
                                            max(product.uom_id) as uom_id
                                        
                                        FROM    
                                            (SELECT
                                                stock_move.id,
                                                stock_move.type,                                   
                                                stock_move.uom_qty,
                                                stock_move.uoi_qty,
                                                stock_move.uom_id,
                                                stock_move.uoi_id,
                                                stock_move.product_id,
                                                stock_move.date                                            
                                            FROM
                                                stock_move,
                                                (SELECT
                                                    id,
                                                    currency_id
                                                FROM
                                                    res_company
                                                WHERE
                                                    id = %s) company
                                            WHERE
                                                product_id in %s AND
                                                state = 'done' AND
                                                type in ('in', 'out') AND
                                                date >= %s AND
                                                date <= %s AND
                                                warehouse_id = %s
                                            ORDER BY
                                                date asc ) move,
                                            (SELECT
                                                move_id,
                                                label_id,
                                                uom_qty,
                                                (select factor from product_uom where id = stock_move_label.uom_id) as label_uom_factor
                                            FROM
                                                stock_move_label) move_label,
                                            (SELECT
                                                id,
                                                lot_id
                                            FROM
                                                stock_label) label,
                                            (SELECT
                                                id,
                                                uom_id,                                        
                                                supply_method,
                                                (select factor from product_uom where id = product_product.uom_id) as product_uom_factor
                                            FROM
                                                product_product
                                            WHERE
                                                id in %s) product
                                            
                                        WHERE
                                            move.id = move_label.move_id AND
                                            label.id = move_label.label_id AND
                                            product.id = move.product_id     
                                            
                                        GROUP by
                                            label.lot_id
                                        
                                        
                                        union all
                                        
                            --requete pour calculer le prix reel
                            --on retourne le prix total et la quantite qui a permis de faire le total
                                        SELECT
                                            false as create_with_price,
                                            true as line_partner_price,
                                            false as line_theo_price,
                                            label.lot_id,
                                            null as product_id,
                                            null as supply_method,
                                            null as month,
                                            null as year,
                                            null as min_date,  
                                            sum(move_label.uom_qty) as sum_move_label,              
                                            sum(case
                                            when move.uom_qty > 0 and move_label.uom_qty > 0 and product.product_uom_factor != 0
                                                then (((move.partner_price*move.rate_company/move.rate_price) * move.uoi_qty +  
                                                        ((move.freight_price*move.rate_company/move.rate_freight_price)/move.uom_qty) * move_label.uom_qty) / 
                                                        (move.uom_qty / move_label.uom_qty)) * (move_uom_factor / product.product_uom_factor)
                                                else 0
                                            end) price_unit_real_uom,
                                            0.0 price_unit_theo_uom,
                                            sum(move_label.uom_qty* (product.product_uom_factor/move_label.label_uom_factor) ) as qty_uom,
                                            null as last_valuation_lot_price,
                                            null as last_valuation_lot_valuation,
                                            null as last_valuation_lot_price_theo,
                                            null as last_valuation_lot_valuation_theo,
                                            null as last_valuation_lot_qty_in_stock,
                                            null as last_valuation_lot_uom,
                                            max(product.uom_id) as uom_id
                                        
                                        FROM    
                                            (SELECT
                                                stock_move.id,
                                                stock_move.type,
                                                stock_move.currency_id,
                                                (case    
                                                    when (select rcr.rate from res_currency_rate rcr where rcr.currency_id = company.currency_id and (rcr.company_id is null or rcr.company_id = company.id) and rcr.name <= stock_move.date order by rcr.name asc limit 1) is not null
                                                    then (select rcr.rate from res_currency_rate rcr where rcr.currency_id = company.currency_id and (rcr.company_id is null or rcr.company_id = company.id) and rcr.name <= stock_move.date order by rcr.name asc limit 1)
                                                    else 1
                                                end) as rate_company,
                                                (case    
                                                    when stock_move.currency_id is not null and (select rcr.rate from res_currency_rate rcr where rcr.currency_id = stock_move.currency_id and (rcr.company_id is null or rcr.company_id = company.id) and rcr.name <= stock_move.date order by rcr.name asc limit 1) is not null
                                                    then (select rcr.rate from res_currency_rate rcr where rcr.currency_id = stock_move.currency_id and (rcr.company_id is null or rcr.company_id = company.id) and rcr.name <= stock_move.date order by rcr.name asc limit 1)
                                                    else 1
                                                end) as rate_price,
                                                stock_move.theo_price,
                                                stock_move.partner_price,
                                                stock_move.freight_currency_id,
                                                (case    
                                                    when stock_move.freight_currency_id is not null and (select rcr.rate from res_currency_rate rcr where rcr.currency_id = stock_move.freight_currency_id and (rcr.company_id is null or rcr.company_id = company.id) and rcr.name <= stock_move.date order by rcr.name asc limit 1) is not null
                                                    then (select rcr.rate from res_currency_rate rcr where rcr.currency_id = stock_move.freight_currency_id and (rcr.company_id is null or rcr.company_id = company.id) and rcr.name <= stock_move.date order by rcr.name asc limit 1)
                                                    else 1
                                                end) as rate_freight_price,
                                                stock_move.freight_price,
                                                stock_move.uom_qty,
                                                stock_move.uoi_qty,
                                                stock_move.uom_id,
                                                stock_move.uoi_id,
                                                stock_move.product_id,
                                                stock_move.date,
                                                (select factor from product_uom where id = stock_move.uom_id) as move_uom_factor                                 
                                            FROM
                                                stock_move,
                                                (SELECT
                                                    id,
                                                    currency_id
                                                FROM
                                                    res_company
                                                WHERE
                                                    id = %s) company
                                            WHERE
                                                product_id in %s AND
                                                state = 'done' AND
                                                type = 'in' AND
                                                date >= %s AND
                                                date <= %s AND
                                                warehouse_id = %s AND
                                                partner_price != 0
                                        
                                            ORDER BY
                                                date asc ) move,
                                            (SELECT
                                                move_id,
                                                label_id,
                                                uom_qty,
                                                (select factor from product_uom where id = stock_move_label.uom_id) as label_uom_factor
                                                FROM
                                                stock_move_label) move_label,
                                            (SELECT
                                                id,
                                                lot_id
                                            FROM
                                                stock_label) label,
                                            (SELECT
                                                id,
                                                uom_id,
                                                supply_method,
                                                (select factor from product_uom where id = product_product.uom_id) as product_uom_factor
                                            FROM
                                                product_product
                                            WHERE
                                            id in %s) product
                                            
                                        WHERE
                                            move.id = move_label.move_id AND
                                            label.id = move_label.label_id AND
                                            product.id = move.product_id     
                                            
                                        GROUP by
                                            label.lot_id
                                        
                                        
                                        union all
                                        
                            --requete pour calculer le prix theorique
                            --on retourne le prix total et la quantite qui a permis de faire le total
                                        SELECT
                                            false as create_with_price,
                                            false as line_partner_price,
                                            true as line_theo_price,
                                            label.lot_id,
                                            null as product_id,
                                            null as supply_method,
                                            null as month,
                                            null as year,
                                            null as min_date,        
                                            sum(move_label.uom_qty) as sum_move_label,       
                                            0.0 price_unit_real_uom,
                                            sum(case
                                                when move.uom_qty > 0 and move_label.uom_qty > 0 and product.product_uom_factor != 0
                                                    then (((move.theo_price*move.rate_company/rate_price) * move.uoi_qty +  
                                                           ((move.freight_price*move.rate_company/move.rate_freight_price)/move.uom_qty) * move_label.uom_qty) / 
                                                           (move.uom_qty / move_label.uom_qty))* (move_uom_factor / product.product_uom_factor) 
                                                else 0
                                                end) price_unit_theo_uom,
                                            sum(move_label.uom_qty* (product.product_uom_factor/move_label.label_uom_factor)) as qty_uom,
                                            null as last_valuation_lot_price,
                                            null as last_valuation_lot_valuation,
                                            null as last_valuation_lot_price_theo,
                                            null as last_valuation_lot_valuation_theo,
                                            null as last_valuation_lot_qty_in_stock,
                                            null as last_valuation_lot_uom,
                                            max(product.uom_id) as uom_id
                                        
                                        FROM    
                                            (SELECT
                                                stock_move.id,
                                                stock_move.type,
                                                stock_move.currency_id,
                                                (case    
                                                    when (select rcr.rate from res_currency_rate rcr where rcr.currency_id = company.currency_id and (rcr.company_id is null or rcr.company_id = company.id) and rcr.name <= stock_move.date order by rcr.name asc limit 1) is not null
                                                        then (select rcr.rate from res_currency_rate rcr where rcr.currency_id = company.currency_id and (rcr.company_id is null or rcr.company_id = company.id) and rcr.name <= stock_move.date order by rcr.name asc limit 1)
                                                    else 1
                                                end) as rate_company,
                                                (case    
                                                    when stock_move.currency_id is not null and (select rcr.rate from res_currency_rate rcr where rcr.currency_id = stock_move.currency_id and (rcr.company_id is null or rcr.company_id = company.id) and rcr.name <= stock_move.date order by rcr.name asc limit 1) is not null
                                                        then (select rcr.rate from res_currency_rate rcr where rcr.currency_id = stock_move.currency_id and (rcr.company_id is null or rcr.company_id = company.id) and rcr.name <= stock_move.date order by rcr.name asc limit 1)
                                                    else 1
                                                end) as rate_price,
                                                stock_move.theo_price,
                                                stock_move.partner_price,
                                                stock_move.freight_currency_id,
                                                (case    
                                                    when stock_move.freight_currency_id is not null and (select rcr.rate from res_currency_rate rcr where rcr.currency_id = stock_move.freight_currency_id and (rcr.company_id is null or rcr.company_id = company.id) and rcr.name <= stock_move.date order by rcr.name asc limit 1) is not null
                                                    then (select rcr.rate from res_currency_rate rcr where rcr.currency_id = stock_move.freight_currency_id and (rcr.company_id is null or rcr.company_id = company.id) and rcr.name <= stock_move.date order by rcr.name asc limit 1)
                                                    else 1
                                                end) as rate_freight_price,
                                                stock_move.freight_price,
                                                stock_move.uom_qty,
                                                stock_move.uoi_qty,
                                                stock_move.uom_id,
                                                stock_move.uoi_id,
                                                stock_move.product_id,
                                                stock_move.date,
                                                (select factor from product_uom where id = stock_move.uom_id) as move_uom_factor
                                                
                                            FROM
                                                stock_move,
                                                (SELECT
                                                    id,
                                                    currency_id
                                                FROM
                                                    res_company
                                                WHERE
                                                    id = %s) company
                                            WHERE
                                                product_id in %s AND
                                                state = 'done' AND
                                                type = 'in' AND
                                                date >= %s AND
                                                date <= %s AND
                                                warehouse_id = %s AND
                                                theo_price != 0
                                        
                                            ORDER BY
                                                date asc ) move,
                                            (SELECT
                                                move_id,
                                                label_id,
                                                uom_qty,
                                                (select factor from product_uom where id = stock_move_label.uom_id) as label_uom_factor
                                            FROM
                                                stock_move_label) move_label,
                                            (SELECT
                                                id,
                                                lot_id
                                            FROM
                                                stock_label) label,
                                            (SELECT
                                                id,
                                                uom_id,                                          
                                                supply_method,
                                                (select factor from product_uom where id = product_product.uom_id) as product_uom_factor
                                            FROM
                                                product_product
                                            WHERE
                                                id in %s) product
                                            
                                        WHERE
                                            move.id = move_label.move_id AND
                                            label.id = move_label.label_id AND
                                            product.id = move.product_id     
                                            
                                        GROUP by
                                            label.lot_id""", (company_id, tuple(product_ids), date_start_move, date_end_move, warehouse_id, tuple(product_ids), 
                                                              company_id, tuple(product_ids), date_start_move, date_end_move, warehouse_id, tuple(product_ids), 
                                                              company_id, tuple(product_ids), date_start_move, date_end_move, warehouse_id, tuple(product_ids)))
                
                dico_res_request = self.env.cr.dictfetchall()
                lot_ids = self.create_lines(dico_res_request, date_start, warehouse_id, uom_obj)
                if not lot_ids:
                    lot_ids = [0] 
                # Requete qui aide à créer les lignes des lots précédents qui n'ont pas eu de mouvement dans le mois
                self.env.cr.execute("""SELECT
                                        true as create_with_price,
                                        false as line_partner_price,
                                        true as line_theo_price,
                                        lot_id,
                                        price_theo,
                                        product_id,
                                        supply_method,
                                        extract(month from %s) as month,
                                        extract(year from %s) as year,
                                        %s as min_date,
                                        0 as sum_move_label,
                                        price as price_unit_real_uom,
                                        price_theo as price_unit_theo_uom,
                                        0 as qty_uom,
                                        price as last_valuation_lot_price,
                                        valuation as last_valuation_lot_valuation,
                                        price_theo as last_valuation_lot_price_theo,
                                        valuation_theo as last_valuation_lot_valuation_theo,
                                        qty_in_stock as last_valuation_lot_qty_in_stock    ,
                                        stock_valuation_lot.uom_id as last_valuation_lot_uom ,
                                        (select uom_id from product_product where id = product_id) as uom_id                           
                                    FROM
                                        stock_valuation_lot
                                    WHERE
                                        product_id in %s AND
                                        lot_id not in %s AND
                                        warehouse_id = %s AND
                                        month::int = (select extract(month from %s - interval '1 month')) AND
                                        (case
                                            when (select extract(month from %s - interval '1 month')) = 12 
                                            then (select extract(year from %s - interval '1 year'))
                                            else (select extract(year from %s))
                                        end) = year::int""", (date_start, date_start, date_start, tuple(product_ids), tuple(lot_ids), warehouse_id, date_start, date_start, date_start, date_start))
                dico_res_request2 = self.env.cr.dictfetchall()
                self.create_lines(dico_res_request2, date_start, warehouse_id, uom_obj)
            
        
    def create_lines(self, dico_res_request, date_start, warehouse_id, uom_obj):
        """
            Fonction qui créé les lignes de valorisations par lots
        """
        lot_ids = []
        dico_vals_lots = {}
        for res_request in dico_res_request:
            res_request['qty_uom'] = res_request['qty_uom'] or 0
            if res_request['create_with_price'] == True or (res_request['line_partner_price'] == False and res_request['line_theo_price'] == False):
                # Les prix ne sont pas gérés dans cette boucle sauf si les lots n'ont pas eu de mouvement dans le mois
                depreciation_coeff = self._get_depreciation_coeff(res_request['min_date'])
                last_qty_in_stock = res_request['last_valuation_lot_qty_in_stock'] or 0
                last_price = res_request['last_valuation_lot_price'] or 0
                last_price_theo = res_request['last_valuation_lot_price_theo'] or 0
                if res_request['last_valuation_lot_uom'] and res_request['last_valuation_lot_uom'] != res_request['uom_id']:
                    last_price = last_price * 1 / uom_obj._compute_qty(res_request['last_valuation_lot_uom'], 1, res_request['uom_id'])
                    last_price_theo = last_price_theo * 1 / uom_obj._compute_qty(res_request['last_valuation_lot_uom'], 1, res_request['uom_id'])
                    last_qty_in_stock = uom_obj._compute_qty(res_request['last_valuation_lot_uom'], last_qty_in_stock, res_request['uom_id'])
                
                qty = res_request['qty_uom'] + last_qty_in_stock
                last_valuation = res_request['last_valuation_lot_valuation'] or 0
                last_valuation_theo = res_request['last_valuation_lot_valuation_theo'] or 0
                price_unit_real_uom = res_request['price_unit_real_uom'] and res_request['sum_move_label'] and res_request['price_unit_real_uom']/res_request['sum_move_label'] or last_price
                price_unit_theo_uom = res_request['price_unit_theo_uom'] and res_request['sum_move_label'] and res_request['price_unit_theo_uom']/res_request['sum_move_label'] or last_price_theo
                
                if last_price and last_qty_in_stock and (res_request['qty_uom'] + last_qty_in_stock) != 0:
                    price = (price_unit_real_uom * res_request['qty_uom'] + last_price * last_qty_in_stock) / (res_request['qty_uom'] + last_qty_in_stock)
                else:
                    price = price_unit_real_uom
                
                if last_price_theo and last_qty_in_stock and (res_request['qty_uom'] + last_qty_in_stock) != 0:
                    price_theo = (price_unit_theo_uom * res_request['qty_uom'] + last_price_theo * last_qty_in_stock) / (res_request['qty_uom'] + last_qty_in_stock)
                else:
                    price_theo = price_unit_theo_uom
                    
                valuation = qty * price
                valuation_theo = qty * price_theo
                price_gap = price - last_price
                price_gap_theo = price_theo - last_price_theo
                valuation_gap = valuation - last_valuation
                valuation_gap_theo = valuation_theo - last_valuation_theo
                vals_valuation = {
                             'month': str(date_start.month).zfill(2),
                             'year': date_start.year,
                             'depreciation_coeff': depreciation_coeff,
                             'product_id': res_request['product_id'],
                             'qty_in_stock': qty,
                             'valuation': valuation,
                             'valuation_theo': valuation_theo,
                             'price': price,
                             'price_theo': price_theo,
                             'lot_id': res_request['lot_id'],
                             'deprecated_valuation': valuation * depreciation_coeff,
                             'deprecated_valuation_theo': valuation_theo * depreciation_coeff,
                             'deprecated_price': price * depreciation_coeff,
                             'deprecated_price_theo': price_theo * depreciation_coeff,
                             'last_qty': last_qty_in_stock,
                             'last_valuation': last_valuation,
                             'last_valuation_theo': last_valuation_theo,
                             'last_price': last_price,
                             'last_price_theo': last_price_theo,
                             'valuation_gap': valuation_gap,
                             'valuation_gap_theo': valuation_gap_theo,
                             'price_gap': price_gap,
                             'price_gap_theo': price_gap_theo,
                             'price_gap_percent': 100 * price_gap / last_price if last_price else 0,
                             'price_gap_percent_theo': 100 * price_gap_theo / last_price_theo if last_price_theo else 0,
                             'valuation_gap_percent': 100 * valuation_gap / last_valuation if last_valuation else 0,
                             'valuation_gap_percent_theo': 100 * valuation_gap_theo / last_valuation_theo if last_valuation_theo else 0,
                             'supply_method': res_request['supply_method'],
                             'warehouse_id': warehouse_id,
                             'uom_id': res_request['uom_id']}
                
                if vals_valuation['qty_in_stock']:
                    valu_create = self.create(vals_valuation)
                    dico_vals_lots[res_request['lot_id']] = valu_create
                    lot_ids.append(res_request['lot_id'])
                    
            elif res_request['line_partner_price'] and dico_vals_lots and res_request['lot_id'] in dico_vals_lots:
                # Gestion du prix réel si les lots ont eu un mouvement dans le mois
                depreciation_coeff = dico_vals_lots[res_request['lot_id']].depreciation_coeff
                last_qty_in_stock = dico_vals_lots[res_request['lot_id']].last_qty
                qty = dico_vals_lots[res_request['lot_id']].qty_in_stock
                last_price = dico_vals_lots[res_request['lot_id']].last_price
                last_valuation = dico_vals_lots[res_request['lot_id']].last_valuation
                # Pour les requêtes de prix le prix retourné n'est pas unitaire mais total et la quantité correspont à la quantité total retournée par cette même requete
                price_total_real_uom = res_request['price_unit_real_uom']
                qty_total_uom_for_price = res_request['sum_move_label']
                price_unit_real_uom = qty_total_uom_for_price and price_total_real_uom / qty_total_uom_for_price or 0
                qty_uom = qty - last_qty_in_stock
                if qty_uom < 0:
                    qty_uom = qty_uom * -1
                if last_price and last_qty_in_stock and (qty_uom + last_qty_in_stock) !=0:
                    price = (price_unit_real_uom * qty_uom + last_price * last_qty_in_stock) / (qty_uom + last_qty_in_stock)
                else:
                    price = price_unit_real_uom
                
                valuation = qty * price
                price_gap = price - last_price
                valuation_gap = valuation - last_valuation
                vals_valuation = {
                     'valuation': valuation,
                     'price': price,
                     'deprecated_valuation': valuation * depreciation_coeff,
                     'deprecated_price': price * depreciation_coeff,
                     'valuation_gap': valuation_gap,
                     'price_gap': price_gap,
                     'price_gap_percent': 100 * price_gap / last_price if last_price else 0,
                     'valuation_gap_percent': 100 * valuation_gap / last_valuation if last_valuation else 0,
                }
                dico_vals_lots[res_request['lot_id']].write(vals_valuation)
            
            elif res_request['line_theo_price'] and dico_vals_lots and res_request['lot_id'] in dico_vals_lots:
                # Gestion du prix théo si les lots ont eu un mouvement dans le mois
                depreciation_coeff = dico_vals_lots[res_request['lot_id']].depreciation_coeff
                last_qty_in_stock = dico_vals_lots[res_request['lot_id']].last_qty
                qty = dico_vals_lots[res_request['lot_id']].qty_in_stock
                last_price_theo = dico_vals_lots[res_request['lot_id']].last_price_theo
                last_valuation_theo = dico_vals_lots[res_request['lot_id']].last_valuation_theo
                # Pour les requêtes de prix le prix retourné n'est pas unitaire mais total et la quantité correspont à la quantité total retournée par cette même requete
                price_unit_theo_uom = res_request['price_unit_theo_uom']
                qty_total_uom_for_price = res_request['sum_move_label']
                price_unit_theo_uom = qty_total_uom_for_price and price_unit_theo_uom / qty_total_uom_for_price or 0
                qty_uom = qty - last_qty_in_stock
                if qty_uom < 0:
                    qty_uom = qty_uom * -1
                if last_price_theo and last_qty_in_stock and (qty_uom + last_qty_in_stock) != 0:
                    price_theo = (price_unit_theo_uom * qty_uom + last_price_theo * last_qty_in_stock) / (qty_uom + last_qty_in_stock)
                else:
                    price_theo = price_unit_theo_uom
                
                valuation_theo = qty * price_theo
                price_gap_theo = price_theo - last_price_theo
                valuation_gap_theo = valuation_theo - last_valuation_theo
                
                vals_valuation = {
                     'valuation_theo': valuation_theo,
                     'price_theo': price_theo,
                     'deprecated_valuation_theo': valuation_theo * depreciation_coeff,
                     'deprecated_price_theo': price_theo * depreciation_coeff,
                     'valuation_gap_theo': valuation_gap_theo,
                     'price_gap_theo': price_gap_theo,
                     'price_gap_percent_theo': 100 * price_gap_theo / last_price_theo if last_price_theo else 0,
                     'valuation_gap_percent_theo': 100 * valuation_gap_theo / last_valuation_theo if last_valuation_theo else 0,
                }
                dico_vals_lots[res_request['lot_id']].write(vals_valuation)
            
        return lot_ids
    
    
    @api.model
    def cron_calculate_all_products(self):
        """
            Cron qui lance la création des lignes de PMP par lot sur le mois précédent
        """
        product_obj = self.env['product.product']
        last_month = datetime.strptime(fields.Date.today(), "%Y-%m-%d") - relativedelta(months=1)
        for warehouse in self.env['stock.warehouse'].search([('company_id', '=', self.env.user.company_id.id)]):
            self.calculate_for_products(product_obj.search([('is_int', '!=', True), ('type', '=', 'stockable'), ('track_label', '=', True)]).ids, str(last_month.month).zfill(2), str(last_month.year),
                                         self.env.user.company_id.id, warehouse.id)
    


class assists_inventory(models.Model):
    """ 
       assists with inventory entry
    """
    _name = 'assists.inventory'
    _description = 'Assists with inventory entry'

    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('validate', _('Validate')),
                ('cancel', _('Cancel')),
                       ]
    

    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    date = fields.Date(string='Date', default=lambda self: fields.Date.today(), required=True)
    user_id = fields.Many2one('res.users', string='Users', required=True, ondelete='restrict', default=lambda self: self.env.user.id)
    state = fields.Selection('_state_get', string='State', default='draft')
    line_ids = fields.One2many('assists.inventory.line', 'ai_id',  string='Lines')
    inventory_id = fields.Many2one('stock.inventory', string='Inventory', required=True, ondelete='cascade')

    
    #===========================================================================
    # Button
    #===========================================================================
    @api.multi
    def wkf_validate(self):
        sil_obj = self.env['stock.inventory.line']
        product_obj = self.env['product.product']
        uom_obj = self.env['product.uom']
        move_obj = self.env['stock.move']
        for assits in self:
            inventory = assits.inventory_id
            for line in assits.line_ids:
                sil_rcs = sil_obj.search([('inventory_id', '=', inventory.id), 
                                            ('product_id', '=', line.product_id.id),
                                            ('location_id', '=', line.location_id.id)], limit=1)
                
                if sil_rcs:
                    vals = {'make_inventory': True,
                            'assists_line_id': line.id}
                    
                    if sil_rcs.theoretical_qty != line.qty:
                        vals['quantity'] = line.qty
                        vals['to_update'] = True
                    
                    if sil_rcs.uom_id != line.uom_id:
                        vals['uom_id'] = line.uom_id.id
                        vals['to_update'] = True
                        
                    sil_rcs.write(vals)
                else:
                    theoretical_qty = 0
                    uom_id = False
                    location_id = line.location_id.id
                    product_id = line.product_id.id
                    in_args = [('location_dest_id','=', location_id),('state','=','done'), ('date', '<=', self.inventory_id.date), ('product_id', '=', product_id)]
                    out_args = [('location_id','=', location_id), ('state','=','done'), ('date', '<=', self.inventory_id.date), ('product_id', '=', product_id)]
                    datas = line.location_id.get_location_product_qty(product_obj, uom_obj, move_obj, in_args=in_args, out_args=out_args)
                    uom_id = line.product_id.uom_id.id
                    if datas:
                        theoretical_qty = datas[(product_id, location_id)]['theoretical_qty_inv']
                        uom_id = datas[(product_id, location_id)]['uom_id']
                    
                    vals_line = {
                                 'inventory_id': inventory.id,
                                 'theoretical_qty_inv': theoretical_qty,
                                 'location_id': line.location_id.id,
                                 'product_id': line.product_id.id,
                                 'quantity': line.qty,
                                 'uom_id': uom_id,
                                 'origin_uom_id': uom_id,
                                 'to_update': True,
                                 'make_inventory': True,
                                 'assists_line_id': line.id
                                 }
                    
                    sil_rcs.create(vals_line)
                
            assits.write({'state': 'validate'})
        
        return {'type':'ir.actions.act_window_view_reload'}
    
    
    @api.multi
    def button_open_assits_inventory(self):
        for assits in self:
            if assits.inventory_id.state not in ('draft', 'waiting'):
                raise except_orm(_('Error'), _('Inventory must be draft or waiting.'))
                
            return { 
                'type': 'ir.actions.act_window',
                'name': 'Assists inventory',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'assists.inventory',
                'res_id': assits.id,
                'target': 'new', }
    
    
    @api.multi
    def button_save(self):
        return True
    
    
    @api.multi
    def wkf_draft(self):
        self.write({'state': 'draft'})
    
    
    @api.multi
    def wkf_cancel(self):
        for assits in self:
            line_rcs = self.env['assists.inventory.line']
            for line in assits.line_ids:
                line_rcs |= line
            
            if line_rcs:
                for inv_line in self.env['stock.inventory.line'].search([('assists_line_id', 'in', line_rcs.ids)]):
                    inv_line.write({
                                    'to_update': False,
                                    'make_inventory': False,
                                    'quantity': inv_line.theoretical_qty,
                                    'uom_id': inv_line.origin_uom_id.id,
                                    })
        
        self.write({'state': 'cancel'})
        return {'type':'ir.actions.act_window_view_reload'}
    
    
    
class assists_inventory_line(models.Model):
    """ 
       Line assists with inventory entry
    """
    _name = 'assists.inventory.line'
    _description = 'Line assists with inventory entry'    
    _rec_name = 'product_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    ai_id = fields.Many2one('assists.inventory', string='WAI', required=False, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    location_id = fields.Many2one('stock.location', string='Location', required=True, ondelete='cascade')
    qty = fields.Float(string='Qty', default=None, required=True)
    uom_id = fields.Many2one('product.uom', string='UoM', required=True, ondelete='cascade')
    uom_category_id = fields.Many2one('product.uom.category', string='Category', required=False, ondelete='cascade')
    
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('product_id')
    def _onchange_date(self):
        self.uom_id = self.product_id and self.product_id.uom_id.id or False
        self.uom_category_id = self.product_id and self.product_id.uom_id.category_id.id or False
    
    

class stock_inventory(models.Model):
    """ 
    Inventory 
    """
    _name = 'stock.inventory'
    _description = 'Inventory'
    
    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('waiting', _('Waiting for validation')),
                ('done', _('Validated')),
                ('cancel', _('Cancelled')),
                       ]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    date = fields.Datetime(string='Inventory Date', default=lambda self: fields.Datetime.now(), required=True)
    line_ids = fields.One2many('stock.inventory.line', 'inventory_id',  string='Inventories')
    move_ids = fields.One2many('stock.move', 'inventory_id',  string='Moves')
    state = fields.Selection('_state_get', string='State', default='draft')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id, required=True, ondelete='restrict')
    location_id = fields.Many2one('stock.location', string='Location', required=False, ondelete='restrict')
    move_date = fields.Datetime(string='Move date', default=lambda self: fields.Datetime.now(), required=True)
    assists_inventory_ids = fields.One2many('assists.inventory', 'inventory_id',  string='Assists inventory')
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('date')
    def _onchange_date(self):
        self.move_date = self.date
        
        
    #===========================================================================
    # Boutons
    #===========================================================================
    @api.multi
    def wkf_draft(self):
        for inventory in self:
            if inventory.move_ids:
                inventory.move_ids.wkf_cancel()
                inventory.move_ids.unlink()
            
            inventory.line_ids.write({'update1': False})
                
        self.write({'state': 'draft'})
    
    
    @api.multi
    def wkf_waiting(self):
        self.write({'state': 'waiting'})
    
    
    @api.multi
    def wkf_done(self):
        inv_line_obj = self.env['stock.inventory.line']
        for inventory in self:
            inventory.button_compute_qty_line()
            inventory.create_move_inventory()
            inventory.validation_move_inventory()
            il_rcs = inv_line_obj.search([('inventory_id', '=', inventory.id), ('to_update', '=', True)])
            if il_rcs:
                il_rcs.write({'update1': True})

        self.write({'state': 'done'})
        
    
    @api.multi
    def wkf_cancel(self):
        self.write({'state': 'cancel'})
        for inventory in self:
            if inventory.move_ids:
                inventory.move_ids.wkf_cancel()
    
    
    @api.multi
    def button_del_line(self):
        """
            Bouton qui supprime les lignes d'inventaire
        """
        for inventory in self:
            if inventory.line_ids and inventory.state in ('draft', 'cancel', 'line_confirm'):
                inventory.line_ids.unlink()
        
        return {'type': 'ir.actions.act_window_close'}


    @api.multi
    def button_importation(self):
        """
            Bouton qui génère les lignes d'inventaire
        """
        location_obj = self.env['stock.location']
        inventory_line_obj = self.env['stock.inventory.line']
        product_obj = self.env['product.product']
        uom_obj = self.env['product.uom']
        move_obj = self.env['stock.move']
        for inventory in self:
            if inventory.state != 'draft':
                raise except_orm(_('Error'), _('Inventory must be draft.'))
            
            if not inventory.location_id:
                raise except_orm(_('Error'), _('Please select a location.'))
            # Recherche la liste des emplacements fils
            location_rcs = location_obj.search([('location_id', 'child_of', [inventory.location_id.id])], order="id")
            if location_rcs:
                if inventory.location_id.id not in location_rcs.ids:
                    location_rcs += inventory.location_id
            else:
                location_rcs = inventory.location_id
    
            res = {}
            flag = False
            
            # Calcul de la quantité des produits dans par emplacement
            for location in location_rcs:
                in_args = [('location_dest_id', '=', location.id),('state', '=', 'done'), ('date', '<=', inventory.date), ('track_label_product', '=', False)]
                out_args = [('location_id', '=', location.id), ('state', '=', 'done'), ('date', '<=', inventory.date), ('track_label_product', '=', False)]
                datas = location.get_location_product_qty(product_obj, uom_obj, move_obj, in_args=in_args, out_args=out_args)
                if datas:
                    flag = True
                    res[location.id] = datas

            if not flag:
                raise except_orm(_('Error'), _('No product in this location.'))
            
            # Création des lignes
            for stock_move in res.values():
                for stock_move_details in stock_move.values():
                    stock_move_details.update({'inventory_id': inventory.id})
                    domain = []
                    for field, value in stock_move_details.items():
                        domain.append((field, '=', value))
    
                    line_rcs = inventory_line_obj.search(domain)
                    if not line_rcs:
                        inventory_line_obj.create(stock_move_details)

        return {'type': 'ir.actions.act_window_close'}
    
    
    @api.multi
    def button_to_update(self):
        """
            Bouton qui permet de sélectionner les lignes d'inventaire à mettre à jour
        """
        for inventory in self:
            line_rcs = self.env['stock.inventory.line']
            for line in inventory.line_ids:
                if line.theoretical_qty != line.quantity:
                    line_rcs += line
        
            if line_rcs:
                line_rcs.write({'to_update': True})
    
    
    @api.multi
    def button_compute_qty_line(self):
        """
            Bouton qui permet de recalculer la qté
        """
        product_obj = self.env['product.product']
        uom_obj = self.env['product.uom']
        move_obj = self.env['stock.move']
        for inventory in self:
            for line in inventory.line_ids:
                in_args = [('product_id', '=', line.product_id.id), ('location_dest_id', '=', line.location_id.id), ('state', '=', 'done'), ('date', '<=', inventory.date), ('track_label_product', '=', False)]
                out_args = [('product_id', '=', line.product_id.id), ('location_id', '=', line.location_id.id), ('state', '=', 'done'), ('date', '<=', inventory.date), ('track_label_product', '=', False)]
                datas = line.location_id.get_location_product_qty(product_obj, uom_obj, move_obj, in_args=in_args, out_args=out_args)
                if datas and (line.product_id.id, line.location_id.id) in datas:
                    quantity = datas[(line.product_id.id, line.location_id.id)]['theoretical_qty_inv']
                    uom_id = datas[(line.product_id.id, line.location_id.id)]['uom_id']
                    line.write({'theoretical_qty_inv': quantity, 'uom_id': uom_id, 'origin_uom_id': uom_id})
                    
        return True


    @api.multi
    def button_create_assits_inventory(self):
        for inventory in self:
            name = '%s %s'%(inventory.name, fields.Date.today())
            assits = self.env['assists.inventory'].create({'name':name, 'inventory_id': inventory.id})
            return { 
                'type': 'ir.actions.act_window',
                'name': 'Assists inventory',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'assists.inventory',
                'res_id': assits.id,
                'target': 'new', }
            
            
    #===========================================================================
    # Function
    #===========================================================================
    def create_move_inventory(self):
        """
            Fonction qui crée les mouvements de l'inventaire
        """
        move_obj = self.env['stock.move']
        move_rcs = self.env['stock.move']
        inventory_location_rcs = self.env['stock.location'].search([('usage', '=', 'inventory')], limit=1)
        if not inventory_location_rcs:
            raise except_orm(_('Error'), _('There is not configure inventory location.'))
        
        move_date = self.move_date
        for line in self.line_ids:
            origin =  _('Inventory %s'%(self.name))
            if line.theoretical_qty_inv > line.quantity and line.to_update:
                qty = line.theoretical_qty_inv - line.quantity
                move_rcs += move_obj.create_move(line.product_id, line.location_id.id, inventory_location_rcs.id, type='out', qty=qty, uom=line.uom_id, date=move_date,
                                      other_data={'inventory_id': self.id, 'done_date': move_date, 
                                                  'origin': origin, 'no_control': True}, in_product_uom=True)
                
            elif line.theoretical_qty_inv < line.quantity and line.to_update:
                qty = line.quantity - line.theoretical_qty_inv
                move_rcs += move_obj.create_move(line.product_id, inventory_location_rcs.id, line.location_id.id, type='in', qty=qty, uom=line.uom_id, date=move_date,
                                      other_data={'inventory_id': self.id, 'done_date': move_date,
                                                  'origin': origin, 'no_control': True}, in_product_uom=True)
        
        return True
    
    
    def validation_move_inventory(self):
        """
            Fonction qui valide les mouvements de l'inventaire
        """
        context = self.env.context.copy()
        context['force_done'] = True
        if self.move_ids:
            move_rcs = self.move_ids.filtered(lambda m: m.state == 'draft')
            move_rcs.wkf_waiting()
            move_rcs.with_context(context).wkf_done()
#             move_rcs.write({'date': self.move_date})
        else:
            raise except_orm(_('Error'), _('No quantity in the lines has been changed, please return to the state line to confirm and check the lines you want to change.'))
        
        return True

        
    
class stock_invetory_line(models.Model):
    """ 
        Inventory Line 
    """
    _name = 'stock.inventory.line'
    _description = 'Inventory Line'
    _rec_name = 'product_id'
    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('waiting', _('Waiting for validation')),
                ('done', _('Validated')),
                ('cancel', _('Cancelled')),
                       ]
        

    @api.one
    def _compute_qtys(self):
        self.theoretical_qty = self.theoretical_qty_inv
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    inventory_id = fields.Many2one('stock.inventory', string='Inventory', required=False, ondelete='restrict')
    state = fields.Selection('_state_get', string='State', related='inventory_id.state', default='draft', readonly=True)
    location_id = fields.Many2one('stock.location', string='Location', required=False, ondelete='restrict')
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='restrict')
    quantity = fields.Float(string='Quantity', default=0.0, required=False)
    theoretical_qty = fields.Float(string='Theorical Quantity', compute='_compute_qtys', default=0.0, required=False)
    theoretical_qty_inv = fields.Float(string='Theorical Quantity', default=0.0, required=False)
    uom_id = fields.Many2one('product.uom', string='UoM', required=False, ondelete='restrict')
    origin_uom_id = fields.Many2one('product.uom', string='Origin UoM', required=False, ondelete='restrict')
    automatic = fields.Boolean(string='Automatic', default=False)
    make_inventory = fields.Boolean(string='Make inventory', default=False)
    to_update = fields.Boolean(string='To Update', default=False)
    update1 = fields.Boolean(string='Update', default=False)
    assists_line_id = fields.Many2one('assists.inventory.line', string='Assists line', required=False, ondelete='set null')
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('product_id', 'location_id')
    def _onchange_product_id(self):
        product_obj = self.env['product.product']
        uom_obj = self.env['product.uom']
        move_obj = self.env['stock.move']
        quantity = 0
        uom_id = False
        if self.product_id and self.location_id and self.inventory_id:
            location_id = self.location_id.id
            product_id = self.product_id.id
            in_args = [('location_dest_id','=', location_id),('state','=','done'), ('date', '<=', self.inventory_id.date), ('product_id', '=', product_id)]
            out_args = [('location_id','=', location_id), ('state','=','done'), ('date', '<=', self.inventory_id.date), ('product_id', '=', product_id)]
            datas = self.location_id.get_location_product_qty(product_obj, uom_obj, move_obj, in_args=in_args, out_args=out_args)
            uom_id = self.product_id.uom_id.id
            if datas:
                quantity = datas[(self.product_id.id, self.location_id.id)]['theoretical_qty_inv']
                uom_id = datas[(self.product_id.id, self.location_id.id)]['uom_id']
                
        self.quantity = quantity
        self.theoretical_qty = quantity
        self.theoretical_qty_inv = quantity
        self.uom_id = uom_id
        self.origin_uom_id = uom_id
        
        

class quality_control_declaration(models.Model):
    """ 
        Quality Control Declaration
    """
    _name = 'quality.control.declaration'
    _description = 'Quality Control Declaration'
    
    @api.model
    def _type_get(self):
        return [
            ('manual', _('Manual')),
            ('reception', _('Reception')),
#                 ('delivery', _('Delivery')),
            ('intern', _('Production')),
            ('post_reception', _('Post Reception')),
            ('post_intern', _('Post production')),
                   ]

    
    @api.model
    def _state_get(self):
        return [
            ('draft', _('Draft')),
            ('progress', _('Progress')),
            ('done', _('Done')),
            ('cancel', _('Cancel')),
                   ]
    
    
    @api.model
    def _type_control_get(self):
        return [
            ('numeric', _('Numeric')),
            ('text', _('Text')),
            ('selection', _('Selection')),
            ('only_result', _('Only result')),
            ('all', _('All'))
                   ]
        
        
    def _get_states(self):
        return {
            'draft': [('readonly', False)], 
            'progress': [('readonly', True)], 
            'done': [('readonly', True)], 
            'cancel': [('readonly', True)], 
                }
        
        
    def _get_qtys_states(self):
        return {
            'draft': [('readonly', False)], 
            'progress': [('readonly', False)], 
            'done': [('readonly', True)], 
            'cancel': [('readonly', True)], 
                }
        

    @api.one
    @api.depends('ok_label_ids', 'hs_label_ids', 'quarantine_label_ids')
    def _compute_label_qtys(self):
        label_obj = self.env['stock.label']
        # OK
        qty_dict = label_obj.search_group(fields=['uom_qty'], 
                                          groupby=[], 
                                          args=[('id', 'in', self.ok_label_ids.ids)],
                                          sum='uom_qty',
                                          return_dict=True,
                                          without_order=True)
        self.label_qty_ok = qty_dict and qty_dict[0] and 'uom_qty' in qty_dict[0] and qty_dict[0]['uom_qty'] or 0.0
        # HS
        qty_dict = label_obj.search_group(fields=['uom_qty'], 
                                          groupby=[], 
                                          args=[('id', 'in', self.hs_label_ids.ids)],
                                          sum='uom_qty',
                                          return_dict=True,
                                          without_order=True)
        self.label_qty_hs = qty_dict and qty_dict[0] and 'uom_qty' in qty_dict[0] and qty_dict[0]['uom_qty'] or 0.0
        # Quarantaine
        qty_dict = label_obj.search_group(fields=['uom_qty'], 
                                          groupby=[], 
                                          args=[('id', 'in', self.quarantine_label_ids.ids)],
                                          sum='uom_qty',
                                          return_dict=True,
                                          without_order=True)
        self.label_qty_quarantine = qty_dict and qty_dict[0] and 'uom_qty' in qty_dict[0] and qty_dict[0]['uom_qty'] or 0.0
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    move_ids = fields.One2many('stock.move', 'control_declaration_id',  string='Moves')
    post_move_ids = fields.One2many('stock.move', 'post_control_declaration_id',  string='Post moves')
    move_init_id = fields.Many2one('stock.move',  string='Move Init', ondelete='set null')
    move_control_id = fields.Many2one('stock.move', string='Control move', ondelete='set null')
    
    qty_ok = fields.Float(string='Qty OK', default=0.0, required=True, digits=dp.get_precision('Product quantity'), states=_get_qtys_states)
    qty_hs = fields.Float(string='Qty HS', default=0.0, required=True, digits=dp.get_precision('Product quantity'), states=_get_qtys_states)
    qty_quarantine = fields.Float(string='Qty Quarantine', default=0.0, required=True, digits=dp.get_precision('Product quantity'), states=_get_qtys_states)
    
    label_qty_ok = fields.Float(string='Qty OK', digits=dp.get_precision('Product quantity'), compute='_compute_label_qtys')
    label_qty_hs = fields.Float(string='Qty HS', digits=dp.get_precision('Product quantity'), compute='_compute_label_qtys')
    label_qty_quarantine = fields.Float(string='Qty quarantine', digits=dp.get_precision('Product quantity'), compute='_compute_label_qtys')
    
    qty_label = fields.Float(string='Qty label', default=0.0, required=False, states=_get_qtys_states)
    max_qty = fields.Float(string='Qty Total', default=0.0, required=True, states=_get_qtys_states)
    date = fields.Datetime(string='Date', states=_get_states)
    location_id = fields.Many2one('stock.location', string='Location', required=True, ondelete='restrict', states=_get_states)
    location_dest_id = fields.Many2one('stock.location', string='Dest. location', required=False, ondelete='restrict', help='If this field is filled, the OK quantity of product will be moved in this location', states=_get_qtys_states)
    line_result_ids = fields.One2many('quality.control.declaration.line.result', 'declaration_id', string='Lines result', states={'draft': [('readonly', True)], 
                                                                                                                                   'progress': [('readonly', False)], 
                                                                                                                                   'done': [('readonly', True)], 
                                                                                                                                    'cancel': [('readonly', True)]})
    line_control_ids = fields.One2many('quality.control.declaration.line.control', 'declaration_id', string='Lines control', states=_get_states)
    name = fields.Char(string='Name', size=256, required=True, states=_get_states)
    nc_quarantine = fields.Boolean(string='Generate Quarantine Qty NC file', default=False, states=_get_qtys_states)
    nc_hs = fields.Boolean(string='Generate HS Qty NC file', default=False, states=_get_qtys_states)
    type = fields.Selection('_type_get', string='Type', default='manual', required=True, states=_get_states)
    nonconformity_ids = fields.One2many('nonconformity.file', 'declaration_id',  string='Nonconformity')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade', states=_get_states)
    product_track_label = fields.Boolean(related='product_id.track_label', store=True)
    is_validate = fields.Boolean(string='Validate', default=False, copy=False)
    user_id = fields.Many2one('res.users', string='User', required=True, default=lambda self: self.env.user.id, ondelete='restrict', states=_get_states)
    type_control = fields.Selection('_type_control_get', string='Type control', default='all', states=_get_states)
    ok_label_ids = fields.Many2many('stock.label', 'control_label_rel', 'control_id', 'label_id', string='Labels', states=_get_qtys_states)
    hs_label_ids = fields.Many2many('stock.label', 'control_hs_label_rel', 'control_id', 'label_id', string='HS labels', states=_get_qtys_states)
    quarantine_label_ids = fields.Many2many('stock.label', 'control_quarantine_label_rel', 'control_id', 'label_id', string='Quarantine labels', states=_get_qtys_states)
    state = fields.Selection('_state_get', string='State', default='draft')
    resource_id = fields.Many2one('mrp.resource', string='Responsible', required=False, ondelete='restrict')
    
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('qty_hs', 'hs_label_ids')
    def _onchange_qty_hs(self):
        if self.qty_hs > 0 or self.label_qty_hs > 0:
            self.nc_hs = True
        else:
            self.nc_hs = False
            
            
    @api.onchange('qty_quarantine', 'quarantine_label_ids')
    def _onchange_qty_quarantine(self):
        if self.qty_quarantine or self.label_qty_quarantine > 0:
            self.nc_quarantine = True
        else:
            self.nc_quarantine = False
        
        
    @api.onchange('line_result_ids')
    def _onchange_line_result_ids(self):
        types = ('ok', 'hs', 'quarantine')
        for line in self.line_result_ids:
            if line.label_id:
                for label_type in types:
                    if line.result == label_type:
                        if line.label_id not in self['%s_label_ids'%(label_type)]:
                            self['%s_label_ids'%(label_type)] = [(4, line.label_id.id)]
                    else:
                        if line.label_id in self['%s_label_ids'%(label_type)]:
                            self['%s_label_ids'%(label_type)] = [(3, line.label_id.id)]
                        
        
    @api.onchange('max_qty')
    def _onchange_max_qty(self):
        self.line_result_ids = False
        
        
    #===========================================================================
    # Boutons
    #===========================================================================
    
    def get_quantity(self, field):
        return self.product_track_label and self['label_%s'%(field)] or self[field]
    
    
    @api.multi
    def generate_move(self):
        move_label_obj = self.env['stock.move.label']
        move_obj = self.env['stock.move']
        hs_move_rs = self.env['stock.move']
        quarantine_move_rs = self.env['stock.move']
        ok_move_rs = self.env['stock.move']
        for qcd in self:
            warehouse_rs = qcd.location_id.warehouse_id
            if qcd.get_quantity('qty_hs'):
                if warehouse_rs.hs_location_id:
                    hs_move_rs += move_obj.create_move(qcd.product_id, 
                                                       src_location=qcd.location_id, 
                                                       dst_location=warehouse_rs.hs_location_id, 
                                                       qty=qcd.get_quantity('qty_hs'), 
                                                       uom=qcd.product_id.uom_id, 
                                                       type='out',
                                                       other_data={'is_principal_quality': False})
                    if self.product_track_label and hs_move_rs:
                        for hs_label in self.hs_label_ids:
                            move_label_obj.create_move_label(hs_label, move_rs=hs_move_rs)
                            
                else:
                    raise except_orm(_('Error'), _('No HS location in company.'))
                
            if qcd.get_quantity('qty_quarantine'):
                if warehouse_rs.quarantine_location_id:
                    quarantine_move_rs += move_obj.create_move(qcd.product_id, 
                                                               src_location=qcd.location_id, 
                                                               dst_location=warehouse_rs.quarantine_location_id, 
                                                               qty=qcd.get_quantity('qty_quarantine'), 
                                                               uom=qcd.product_id.uom_id, 
                                                               type='out',
                                                               other_data={'is_principal_quality': False})
                    if self.product_track_label and quarantine_move_rs:
                        for quarantine_label in self.quarantine_label_ids:
                            move_label_obj.create_move_label(quarantine_label, move_rs=quarantine_move_rs)
                            
                else:
                    raise except_orm(_('Error'), _('No Quarantine location in company.'))
            
            if qcd.get_quantity('qty_ok') and qcd.location_dest_id:
                ok_move_rs += move_obj.create_move(qcd.product_id, 
                                                   src_location=qcd.location_id, 
                                                   dst_location=qcd.location_dest_id, 
                                                   qty=qcd.get_quantity('qty_ok'), 
                                                   uom=qcd.product_id.uom_id,
                                                   other_data={'is_principal_quality': False})
                if self.product_track_label and ok_move_rs:
                    for ok_label in self.ok_label_ids:
                        move_label_obj.create_move_label(ok_label, move_rs=ok_move_rs)
            
        return ok_move_rs, hs_move_rs, quarantine_move_rs
        
    
    @api.multi
    def validate(self):
        if 'default_type' in self.env.context:
            ctx = self.env.context.copy()
            del ctx['default_type']
            self = self.with_context(ctx)
            
        for qcd in self:
            if not self.line_result_ids:
                raise ValidationError(_('No result lines. Please, generate it'))
            
            qty_total = qcd.get_quantity('qty_ok') + qcd.get_quantity('qty_quarantine') + qcd.get_quantity('qty_hs')
            if qty_total != qcd.max_qty:
                raise except_orm(_('Error'), _('The sum of the quantities Ok, quarantine and HS should be equal to %f')%(qcd.max_qty))
            
            # Les créations de mouvement pour un contrôle de production sont gérés directement dans le wizard de déclaration de production
            if qcd.type == 'intern':
                # Si de type production, état à cancel au cas ou le wizard de déclaration de prod est fermé
                qcd.with_context(keep_line_result=True).wkf_cancel()
            else:
                post_control = not qcd.type == 'reception' 
                # À partir du mouvement existant de réception
                if qcd.type == 'reception':
                    move_ok_rcs, move_hs_rcs, move_quarantine_rcs = qcd.move_init_id.split_move_ok_hs_quarantine(qcd.get_quantity('qty_ok'), qcd.get_quantity('qty_hs'), qcd.get_quantity('qty_quarantine'), post_quality=post_control)
                # À partir des informations de la déclaration de contrôle (emplacement, quantités, ...)
                else:
                    move_ok_rcs, move_hs_rcs, move_quarantine_rcs = qcd.generate_move()
                
                partner_id = qcd.move_init_id.move_partner()
                vals = {}
                if move_hs_rcs:
                    vals['move_hs_id'] = move_hs_rcs.id
                    move_hs_rcs.write({'is_control_declaration_recep': False})
                    if qcd.move_init_id.state in ('waiting', 'done') or not qcd.move_init_id:
                        move_hs_rcs.wkf_waiting()
                    if qcd.move_init_id.state == 'done' or not qcd.move_init_id:
                        move_hs_rcs.prioritizing()
                        move_hs_rcs.refresh()
                        move_hs_rcs.wkf_done()
                
                if move_quarantine_rcs:
                    vals['move_quarantine_id'] = move_quarantine_rcs.id
                    move_quarantine_rcs.write({'is_control_declaration_recep': False})
                    if qcd.move_init_id.state in ('waiting', 'done') or not qcd.move_init_id:
                        move_quarantine_rcs.wkf_waiting()
                    if qcd.move_init_id.state == 'done' or not qcd.move_init_id:
                        move_quarantine_rcs.wkf_done()
                        
                if move_ok_rcs:
                    move_ok_rcs.write({'is_control_declaration_recep': False})
                    if qcd.move_init_id.state in ('waiting', 'done') or not qcd.move_init_id:
                        move_ok_rcs.wkf_waiting()
                    if qcd.move_init_id.state == 'done' or not qcd.move_init_id:
                        move_ok_rcs.wkf_done()
                        
                if vals:
                    qcd.move_init_id.write(vals)
                
                # Assignation des mouvements pour la qualité
                qcd.assign_move_quality(move_ok_rcs=move_ok_rcs, move_hs_rcs=move_hs_rcs, move_quarantine_rcs=move_quarantine_rcs, control_declaration_rcs=qcd, post_control=post_control, partner_id=partner_id)
                # Cas où le bouton est appelé depuis le wizard
                if qcd.move_init_id.picking_id and qcd.type == 'reception':
                    qcd.wkf_done()
                    # Remet a jour la vue derniere le wizard
                    return {'type':'ir.actions.act_window_view_reload'}
                    
                qcd.wkf_done()  
                  
        return {'type': 'ir.actions.act_window_close'}
    
    
    @api.multi
    def button_regenerate_control_declaration_wiz(self):
        """
            Button qui permet de régénérer les lignes par rapport au tableau de controle contenu dans la liste de contrôle
        """
        for declaration in self:
            dict_control = {}
            for line_control in declaration.line_control_ids:
                values = line_control.nb_quality_control(int_next_frequency=0, date_next_frequency='', quantity=declaration.max_qty, date=declaration.date, quantity_label=declaration.qty_label)
                dict_control[line_control.control_id] = values
            
            declaration.generate_control_declaration(None, declaration.max_qty, type_declaration=declaration.type, 
                                                     type_control=declaration.type, date=declaration.date, 
                                                     name_declaration='', partner_id=False, move_init_rcs=False, 
                                                     product_rcs=declaration.product_id, dict_control=dict_control, 
                                                     regenerate=True, quantity_label=declaration.qty_label)
            
        return {'type': 'ir.actions.act_window_dialog_reload'} 
    
    
    @api.multi
    def button_regenerate_control_declaration(self):
        """
            Button qui permet de régénérer les lignes par rapport au tableau de controle contenu dans la liste de contrôle
        """
        for declaration in self:
            dict_control = {}
            for line_control in declaration.line_control_ids:
                values = line_control.nb_quality_control(int_next_frequency=0, date_next_frequency='', quantity=declaration.max_qty, date=declaration.date, quantity_label=declaration.qty_label)
                dict_control[line_control.control_id] = values
            
            if dict_control:
                declaration.generate_control_declaration(None, declaration.max_qty, type_declaration=declaration.type, 
                                                         type_control=declaration.type, date=declaration.date, name_declaration='', 
                                                         partner_id=False, move_init_rcs=False, product_rcs=declaration.product_id, 
                                                         dict_control=dict_control, regenerate=True, quantity_label=declaration.qty_label)
            
        return {'type': 'ir.actions.act_window_reload'} 
    
    
    def control_link_move_wo(self, type_declaration, move_init_rcs, control, wo_rcs):
        res = {}
        if type_declaration in ('delivery', 'reception'):
            res['move_id'] = move_init_rcs and move_init_rcs.id or False 
        
        return res
    
    
    def generate_control_declaration(self, quality_control_ids, qty, type_declaration='intern', type_control='all', date='', name_declaration='', partner_id=False, move_init_rcs=False, 
                                     product_rcs=False, dict_control=False, regenerate=False, wo_rcs=False, quantity_label=0, location_rs=False, location_dest_rs=False):
        """
            Fonction qui permet de créer la déclaration de controle 
            :type: self: quality.control
            :param: quality_control_ids: La liste des controles
            :type: quality_control_ids: recordset: quality.control.product
            :param: type_declaration: Le type de déclaration
            :type: type_declaration: selection
            :param: type_control: Le type de control
            :type: type_control: selection
            :param: qty: Qté du produit
            :type: qty: float
            :param: move_id: Mouvement
            :type: move_id: int
            :param: date: Date du controle
            :type: date: datetime
            :param: name_declaration: Nom que l'on souhaite donner à la déclaration de controle
            :type: name_declaration: char
            :param: partner_id: Partner
            :type: partner_id: int
            :param: move_init_rcs: Movement initial de la déclaration
            :type: move_init_rcs: recordset: stock.move
            :param: location_rs: Permet de forcer l'emplacement du contrôle
            :type: location_rs: recordset: stock.location
            :param: location_dest_rs: Permet de forcer l'emplacement du contrôle
            :type: location_dest_rs: recordset: stock.location
            :return: Retourne l'id de la déclaration de controle créér
            :rtype: integer
        """
        res = False
        vals = {'max_qty': qty}
        vals['name'] = name_declaration or 'No Name'
        vals['date'] = date or fields.Datetime.now()
        vals['type'] = type_declaration
        list_line_control = []
        list_line_result = []
        nb_sample = 0
        type_control_all = ''
        if not dict_control:
            dict_control = quality_control_ids.product_quality_control(type_control, partner_id=partner_id, quantity=qty, date=vals['date'], quantity_label=quantity_label)

        if dict_control:
            #Création des échantillons en utilisant le nombre le plus grand de controle à faire
            dico_sample = sorted(dict_control.values(), key=itemgetter('nb'))[-1]
            nb_sample = dico_sample['nb']
            frequency_sample = dico_sample['frequency']
#             if nb_sample:
#                 y = 0
#                 while y < nb_sample:
#                     y += 1
#                     sequence_name = _('Sample %d')%(y)
#                     vals_line.append((0, 0, {'sequence': y, 'line_control_ids': [], 'sequence_name': sequence_name,}))
            
            for control in dict_control:
                # Creation des lignes de controles
                vals_control = {'control_id': control.id,
                                'frequency_type': control.frequency_type,
                                'frequency_value': dict_control[control]['frequency_value'],
                                'int_next_frequency': dict_control[control]['nb_start']}
                list_line_control.append((0, 0, vals_control))
                # Creation des lignes de résultats
                product_id = product_rcs and product_rcs.id or False
                vals_result = {'control_id': control.id,
                               'description': control.description,
                               'product_id': product_rcs and product_rcs.id,
                               'min': control._compute_formula_numeric(product_id, 'min'),
                               'max': control._compute_formula_numeric(product_id, 'max'),
                               'date': date,
                               'type_control': control.type_control,
                               'control_value_ids': [(4, x.id) for x in control.control_value_ids],
                               'text_value': control.text_value}
                if not type_control_all:
                    type_control_all = control.type_control
                elif type_control_all == control.type_control:
                    pass
                else:
                    type_control_all = 'all'
                    
                # Lien vers les Mouvements ou OTs
                vals_result_move_wo = self.control_link_move_wo(type_declaration, move_init_rcs, control, wo_rcs)
                if vals_result_move_wo:
                    vals_result.update(vals_result_move_wo)
                    
                # Si le nombre de controle est égale au nombre d'échantillons
                if dict_control[control]['nb'] == nb_sample:
                    list_position = 0
                    while list_position != nb_sample:
                        vals_result_inter = {}
                        vals_result_inter.update(vals_result)
                        if regenerate:
                            if self.ok_label_ids and list_position < len(self.ok_label_ids):
                                    vals_result_inter['label_id'] = self.ok_label_ids[list_position].id
                                    
                        else:
                            if move_init_rcs and move_init_rcs.move_label_ids:
                                if move_init_rcs.move_label_ids and list_position < len(move_init_rcs.move_label_ids):
                                    vals_result_inter['label_id'] = move_init_rcs.move_label_ids[list_position].label_id.id
                                 
                        list_position += 1
                        vals_result_inter['sequence'] = list_position
                        vals_result_inter['sample'] = _('Sample %d')%(list_position)
                        list_line_result.append((0, 0, vals_result_inter))
                # Si non
                else:
                    if dict_control[control]['frequency'] > 0:
                        sequence_sample = 0
                        do_nb_control = 0
                        nb_pieces = frequency_sample
                        y = dict_control[control]['nb_start']
                        while qty > nb_pieces:
                            if y <= nb_pieces:
                                y += dict_control[control]['frequency']
                                vals_result_inter = {}
                                vals_result_inter.update(vals_result)
                                if regenerate:
                                    if self.ok_label_ids and list_position < len(self.ok_label_ids):
                                            vals_result_inter['label_id'] = self.ok_label_ids[list_position].id
                                            
                                else:
                                    if move_init_rcs and move_init_rcs.move_label_ids:
                                        if move_init_rcs.move_label_ids and list_position < len(move_init_rcs.move_label_ids):
                                            vals_result_inter['label_id'] = move_init_rcs.move_label_ids[list_position].label_id.id
                                            
                                list_position = sequence_sample + 1
                                vals_result_inter['sequence'] = list_position
                                vals_result_inter['sample'] = _('Sample %d')%(list_position)
                                list_line_result.append((0, 0, vals_result_inter))
                                do_nb_control += 1
                            
                            nb_pieces += frequency_sample
                            sequence_sample += 1
                        
                        if do_nb_control != dict_control[control]['nb']:
                            vals_result_inter = {}
                            vals_result_inter.update(vals_result)
                            vals_result_inter['sequence'] = nb_sample
                            vals_result_inter['sample'] = _('Sample %d')%(nb_sample)
                            list_line_result.append((0, 0, vals_result_inter))
                            
                    else:
                        vals_result_inter = {}
                        vals_result_inter.update(vals_result)
                        if regenerate:
                            if self.ok_label_ids and 0 < len(self.ok_label_ids):
                                    vals_result_inter['label_id'] = self.ok_label_ids[0].id
                                    
                        else:
                            if move_init_rcs and move_init_rcs.move_label_ids:
                                if move_init_rcs.move_label_ids and 0 < len(move_init_rcs.move_label_ids):
                                    vals_result_inter['label_id'] = move_init_rcs.move_label_ids[0].label_id.id
                                            
                        vals_result_inter['sequence'] = 1
                        vals_result_inter['sample'] = _('Sample %d')%(1)
                        list_line_result.append((0, 0, vals_result_inter))
                        
#             vals['qty_ok'] = qty - nb_sample  
            vals['qty_ok'] = 0   
            if type_control_all:
                vals['type_control'] = type_control_all
                
            if location_rs:
                vals['location_id'] = location_rs.id
                
            if location_dest_rs:
                vals['location_dest_id'] = location_dest_rs.id
                
            if list_line_result:
                vals['line_result_ids'] = list_line_result
            
            if list_line_control:
                vals['line_control_ids'] = list_line_control
            
            if move_init_rcs:
                vals['move_init_id'] = move_init_rcs.id
                if move_init_rcs and move_init_rcs.move_label_ids:
                    vals['ok_label_ids'] = [(6, 0, [ml.label_id.id for ml in move_init_rcs.move_label_ids])]
            
            if product_rcs:
                vals['product_id'] = product_rcs.id
            
            if type_declaration in ('post_reception', 'post_intern'):
                post_control = True
            else:
                post_control = False
            
            if not regenerate:
                res = self.create(vals)
                # Recalcul les fréquences pour les prochaines qualité
                move_init_rcs.recalculate_frequency_quality_main(post_control=post_control)
                res.wkf_progress()
            else:
                self.line_result_ids.unlink()
                if 'line_result_ids' in vals and vals['line_result_ids']:
                    self.write({'line_result_ids': vals['line_result_ids'], 'type_control': vals['type_control'], 'date': vals['date']})
                
                # Recalcul les fréquences pour les prochaines qualité
                if self.move_init_id:
                    self.move_init_id.recalculate_frequency_quality_main(post_control=post_control)
            
                self.wkf_progress()
             
        return res
    
    
    def assign_move_quality(self, move_ok_rcs=False, move_hs_rcs=False, move_quarantine_rcs=False, control_declaration_rcs=False, post_control=False, partner_id=False):
        """
            Fonction qui permet de liéer un mouvement à la déclaration de controle et/ou de recalculer les prochaines fréquences pour les controles qualités
            :type: self: quality.control.declaration
            :param: move_id: Mouvement
            :type: move_id: int
            :return: Retourne True
            :rtype: True
        """
        if control_declaration_rcs:
            # Création des fichiers de non conformités
            if control_declaration_rcs.nc_hs or control_declaration_rcs.nc_quarantine:
                vals_nonconformity = {'partner_id': partner_id}
                if move_hs_rcs:
                    gwcd_move_hs_rcs = move_hs_rcs
                else:
                    gwcd_move_hs_rcs = control_declaration_rcs.move_init_id.move_hs_id
                
                if move_quarantine_rcs:
                    gwcd_move_quarantine_rcs = move_quarantine_rcs
                else:
                    gwcd_move_quarantine_rcs = control_declaration_rcs.move_init_id.move_quarantine_id
                      
                self.env['nonconformity.file'].generate_with_control_declaration(control_declaration_rcs, 
                                                                                 move_hs_rcs=gwcd_move_hs_rcs, 
                                                                                 move_quarantine_rcs=gwcd_move_quarantine_rcs, 
                                                                                 type=control_declaration_rcs.type, 
                                                                                 vals=vals_nonconformity)
                
            if post_control:
                if move_ok_rcs:      
                    move_ok_rcs.write({'post_control_declaration_id': control_declaration_rcs.id})
                    
                if move_hs_rcs and not move_hs_rcs.control_declaration_id:
                    move_hs_rcs.write({'post_control_declaration_id': control_declaration_rcs.id})
                    
                if move_quarantine_rcs and not move_quarantine_rcs.control_declaration_id:
                    move_quarantine_rcs.write({'post_control_declaration_id': control_declaration_rcs.id})
            else:
                if move_ok_rcs:      
                    move_ok_rcs.write({'control_declaration_id': control_declaration_rcs.id})
                    
                if move_hs_rcs:
                    move_hs_rcs.write({'control_declaration_id': control_declaration_rcs.id})
                    
                if move_quarantine_rcs:
                    move_quarantine_rcs.write({'control_declaration_id': control_declaration_rcs.id})
    
    
    @api.multi
    def wkf_draft(self):
        """
            État à draft
        """
        self.write({'state': 'draft', 'is_validate': False})
    
    
    @api.multi
    def wkf_progress(self):
        """
            État à progress
        """
        self.write({'state': 'progress', 'is_validate': True})
        
        
    @api.multi
    def wkf_done(self):
        """
            État à done
        """
        self.write({'state': 'done'})
        
        
    @api.multi
    def wkf_cancel(self):
        """
            État à cancel
        """
        self.write({'state': 'cancel'})
        move_obj = self.env['stock.move']
        for control_rc in self:
            if not self.env.context.get('keep_line_result'):
                control_rc.line_result_ids.unlink()
                
            if control_rc.post_move_ids:
                move_rcs = move_obj.search([('post_control_declaration_id', '=', control_rc.id), ('is_principal_quality', '!=', True)], order='date desc')
                if move_rcs:
                    move_rcs.wkf_cancel()
                    move_rcs.unlink()

    
    
    @api.model
    def create(self, vals):
        if vals.get('move_init_id'):
            type_declaration = vals.get('type', '')
            if not vals.get('location_id'):
                if type_declaration.startswith('post_'):
                    vals['location_id'] = self.env['stock.move'].browse(vals['move_init_id']).read(['location_dest_id'], load='_classic_write')[0]['location_dest_id']
                else:
                    vals['location_id'] = self.env['stock.move'].browse(vals['move_init_id']).read(['location_id'], load='_classic_write')[0]['location_id']
                
        return super(quality_control_declaration, self).create(vals)
    
    
    @api.multi
    def unlink(self):
        """
        """
        for declaration in self:
            if declaration.move_control_id:
                declaration.move_control_id.wkf_cancel()
                declaration.move_control_id.unlink()
                
            if declaration.move_ids:
                declararation_rcs = self.env['quality.control.declaration']
                for move in declaration.move_ids:
                    if move.post_control_declaration_id not in declararation_rcs:
                        declararation_rcs += move.post_control_declaration_id
                        
                    move.write({'post_control_declaration_id': False})
                
                if declararation_rcs:
                    declararation_rcs.unlink()
                    
            elif declaration.post_move_ids:
                declararation_rcs = self.env['quality.control.declaration']
                for move in declaration.move_ids:
                    if move.post_control_declaration_id not in declararation_rcs:
                        declararation_rcs += move.post_control_declaration_id
                        
                    move.write({'post_control_declaration_id': False})
                
                if declararation_rcs:
                    declararation_rcs.unlink()
                    
        return super(quality_control_declaration, self).unlink()
    


class quality_control_declaration_line_control(models.Model):
    """ 
        Quality Control Declaration Lines Control
    """
    _name = 'quality.control.declaration.line.control'
    _description = 'Quality Control Declaration Lines Control'
    _rec_name = 'control_id'   
    
    
    @api.model
    def _frequency_type_get(self):
        return [
                ('all', _('Each declaration')),
                ('hour', _('Hour')),
                ('day', _('Day')),
                ('week', _('Week')),
                ('month', _('Month')),
                ('piece', _('Piece')),
                ('label', _('Label')),
                       ]
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    declaration_id = fields.Many2one('quality.control.declaration', string='Declaration', required=False, ondelete='cascade')
    control_id = fields.Many2one('quality.control', string='Control', required=True, ondelete='restrict', select=True)
    frequency_type = fields.Selection('_frequency_type_get', string='Frequency', default='all', required=True)
    frequency_value = fields.Integer(string='Frequency Value', default=0)
    int_next_frequency = fields.Integer(string='Integer next frequency', default=0, required=False)
    
    
    @api.onchange('control_id')
    def _onchange_control_id(self):
        if self.control_id.frequency_type == 'time':
            self.frequency_type = self.control_id.frequency_date_type
        else:
            self.frequency_type = self.control_id.frequency_type
            
        if self.control_id.frequency_mode == 'formula':
            self.frequency_value = self.env['quality.control.product'].compute_value_formula(self.control_id.formula, args_parameters_list=[('product_id', '=', self.declaration_id.product_id.id)])
        else:
            self.frequency_value = self.control_id.frequency_manual
    
    
    #===========================================================================
    # FUNCTION
    #===========================================================================
    def nb_quality_control(self, int_next_frequency=0, date_next_frequency='', quantity=0, date='',quantity_label=0):
        """ 
            Fonction qui permet de retourner le nombre de fois que le controle qualitée doit être fait 
            :type: self: quality.control
            :param: type: Le type de control
            :type: type: selection
            :param: quantity: Qté du produit
            :type: quantity: float
            :param: date: Date du controle
            :type: date: datetime
            :return: Retourne le nombre de controle à faire
            :rtype: dico avec le nombre de controle à faire + la fréquence du controle si pas par pièce on retourne -1 + le nombre à laquel on commence le controle
        """
        res = {'nb': 0, 'frequency': -1, 'nb_start': 0, 'frequency_value': 0}
        if not int_next_frequency:
            int_next_frequency = self.int_next_frequency
        
        if self.frequency_type == 'all' and (int_next_frequency + 1) >= self.frequency_value:
            res = {'nb': 1, 'frequency': -1, 'nb_start': 0, 'frequency_value': 0}
        elif self.frequency_type in ('piece', 'label'):
            if self.frequency_type == 'label':
                quantity = quantity_label
            
            if (int_next_frequency + quantity) >= self.frequency_value:
                nb = 1
                nb_start = self.frequency_value - int_next_frequency
                remaining = quantity + int_next_frequency - self.frequency_value
                divisor = remaining / (self.frequency_value or 1)
                if divisor > 0:
                    nb += int(divisor)
                
                res = {'nb': nb, 'frequency': self.frequency_value, 'nb_start': nb_start, 'frequency_value': self.frequency_value}      
        elif self.frequency_type != 'all':
            if not date_next_frequency or date and date > date_next_frequency:
                res = {'nb': 1, 'frequency': -1, 'nb_start': 0, 'frequency_value': 0}
        
        return res
    
    

class quality_control_declaration_line_result(models.Model):
    """ 
        Quality Control Declaration Lines Result
    """
    _name = 'quality.control.declaration.line.result'
    _description = 'Quality Control Declaration Lines Result'
    _rec_name = 'control_id'
    
    @api.one
    def _get_plan_binary_filesystem(self):
        attachment_obj = self.env['ir.attachment']
        attachment_rs = attachment_obj.search([('res_model','=',self._name),('res_id','=',self.id),('binary_field','=','plan')])
        if attachment_rs:
            self['plan'] = attachment_rs[0].datas
    
    
    @api.one
    def _set_plan_binary_filesystem(self):
        attachment_obj = self.env['ir.attachment']
        attachment_rs = attachment_obj.search([('res_model','=',self._name),('res_id','=',self.id),('binary_field','=','plan'),('is_binary_field','=',True)])
        if self.plan:
            if attachment_rs:
                attachment_rs.datas = self.plan
            else:
                attachment_obj.create({'res_model': self._name, 'res_id': self.id, 'name': 'plan datas' , 'is_binary_field': True, 'binary_field': 'plan', 'datas': self.plan, 'datas_fname':'plan datas'})
        else:
            attachment_rs.unlink()

    
    @api.model
    def _result_get(self):
        return [
                ('ok', _('OK')),
                ('quarantine', _('Quarantine')),
                ('hs', _('HS')),
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
    
    
    @api.one
    @api.depends('date')
    def _compute_date(self):
        """
        Fonction qui calcule la semaine, le mois et l'année de la date
        """
        if self.date:
            date = '%s'%(self.date[0:10])
            date = datetime.strptime(date, '%Y-%m-%d')
            isocal = date.isocalendar()
            
            # Sur 2 caractères
            if len(str(isocal[1])) == 1:
                self.week_number = '0%s'%(str(isocal[1]))
            else:
                self.week_number = str(isocal[1])
            
            # Sur 2 caractères
            if len(str(date.month)) == 1:
                self.month = '0%s'%(str(date.month))
            else:
                self.month = str(date.month)
                
            self.year = str(isocal[0])
        else:
            self.week_number = '00'
            self.month = '00'
            self.year = '0'
    
    @api.one
    @api.depends('move_id', 'move_id.picking_id')
    def _compute_pincking(self):
        self.picking_id = self.move_id and self.move_id.picking_id.id or False

    
    @api.model
    def _type_control_get(self):
        return [
                ('numeric', _('Numeric')),
                ('text', _('Text')),
                ('selection', _('Selection')),
                ('only_result', _('Only result')),
                       ]
    

    #===========================================================================
    # COLUMNS
    #===========================================================================
    declaration_id = fields.Many2one('quality.control.declaration', string='Declaration', required=False, ondelete='cascade')
    control_id = fields.Many2one('quality.control', string='Control', required=True, ondelete='restrict', select=True, readonly=True)
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='restrict', select=True)
    sequence = fields.Integer(string='Sequence', default=0, required=False)
    sample = fields.Char(string='Sample', size=256, required=True, readonly=True)
    move_id = fields.Many2one('stock.move', string='Move', required=False, ondelete='cascade')
    picking_id = fields.Many2one('stock.picking', string='Picking', compute='_compute_pincking', store=True)
    description = fields.Text(string='Description')
    plan = fields.Binary(related='control_id.plan', string='Plan/Picture', help='help')
    min = fields.Float(string='Min', readonly=1)
    max = fields.Float(string='Max', readonly=1)
    value_target = fields.Float(string='Value Target', default=None)
    result = fields.Selection('_result_get', string='Result', default='ok')
    user_id = fields.Many2one('res.users', string='User', required=True, default=lambda self: self.env.user.id, ondelete='restrict')
    type_control = fields.Selection('_type_control_get', string='Type control', default='numeric', readonly=True)
    control_value_ids = fields.Many2many('quality.control.value', 'declaration_quality_control_quality_control_value_rel', 'declaration_control_id', 'control_value_id', string='Controls values', readonly=1)
    result_control_value_id = fields.Many2one('quality.control.value', string='Result control value')
    text_value = fields.Char(string='Text value', size=256, required=False, readonly=True)
    result_text_value = fields.Char(string='Result text value', size=256, required=False)
    is_validate = fields.Boolean(string='is_validate', related='declaration_id.is_validate')
    #Date
    date = fields.Datetime(string='Create date', default=lambda self: fields.Datetime.now())
    month = fields.Selection('_month_get', string='Month', compute='_compute_date', store=True)
    week_number = fields.Char(string='Week number', size=2, compute='_compute_date', store=True) 
    year = fields.Char(string='Year', size=4, compute='_compute_date', store=True)
    label_id = fields.Many2one('stock.label', string='Labels', ondelete='restrict')
    is_hs = fields.Boolean(string='HS', default=False)
    is_quarantine = fields.Boolean(string='Quarantine', default=False)
    
    
    #===========================================================================
    # Buttons
    #===========================================================================
    @api.multi
    def button_save_true(self):
        return True
    
    @api.multi
    def return_view_form(self):
        for qcdlc in self:
            data_pool = self.env['ir.model.data']
            action_model, action_id = data_pool.get_object_reference('stock', 'act_quality_control_declaration_line_result_id_view_stack')
            #Puis on va passer l'id à la vue pour pouvoir l'afficher dans la vue form
            if action_model:
                action_pool = self.env[action_model]
                action = action_pool.browse(action_id).read()[0]
                action['res_id'] = qcdlc.id
                res = action
                return res



class nonconformity_file(models.Model):
    """ 
        Nonconformity File 
    """
    _name = 'nonconformity.file'
    _description = 'Nonconformity File'
    _inherit = 'workflow.base'
    _rec_name = 'product_id'
    
    @api.model
    def _origin_type_get(self):
        return [
            ('reception', _('Reception')),
#             ('delivery', _('Delivery')),
            ('intern', _('Production')),
            ('post_reception', _('Post Reception')),
            ('post_intern', _('Post production')),
            ('manual', _('Manual')),
               ]
        
        
    @api.model
    def _state_get(self):
        return [
            ('draft', _('Draft')),
            ('validated', _('Validated')),
            ('progress', _('In progress')),
            ('done', _('Done')),
            ('cancel', _('Cancelled')),
               ]
        
        
    def _get_states(self):
        return {
            'progress': [('readonly', True)], 
            'done': [('readonly', True)], 
            'cancel': [('readonly', True)], 
                }
        
    
    @api.model
    def _type_get(self):
        return [
                ('partner', 'Partner'),
                ('product', 'Product'),
                       ]
        
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    move_id = fields.Many2one('stock.move', string='Move', required=False, ondelete='cascade', states=_get_states)
    product_id = fields.Many2one('product.product', string='Product', required=False, states=_get_states)
    qty = fields.Float(string='Qty', required=False, states=_get_states)
    partner_id = fields.Many2one('res.partner', string='Partner', required=False, ondelete='restrict', states=_get_states)
    cause_id = fields.Many2one('nonconformity.cause', string='Cause', required=False, ondelete='restrict', states=_get_states)
    origin_type = fields.Selection('_origin_type_get', string='Origin type', default='manual', states=_get_states)
    origin = fields.Char(size=128, required=False)
    create_date = fields.Date(string='Create Date', states=_get_states)
    limit_date = fields.Date(string='Treatment Limit Date', states=_get_states)
    end_date = fields.Date(string='Treatment End Date', states=_get_states)
    state = fields.Selection('_state_get', string='State', default='draft')
    declaration_id = fields.Many2one('quality.control.declaration', string='Declaration', required=False, ondelete='cascade', states=_get_states)
    is_return_product = fields.Boolean(string='Returned product', default=False, states=_get_states)
    type = fields.Selection('_type_get', required=True, default='product', states=_get_states)
    # Analyse
    description = fields.Text(string='Description', states=_get_states)
    attachment_ids = fields.Many2many('document.openprod', 'nonconformity_document_openprod_rel', 'nonconformity_file_id', 'document_id', string='Attachments', copy=True, states=_get_states)
    # Action
    user_event_ids = fields.One2many('calendar.event', 'nonconformity_file_id', string='Actions', states=_get_states)
    # Mails
    mail_ids = fields.One2many('mail.mail', 'res_id', string='Mails', domain=[("model", "=", "nonconformity.file")], readonly=True)
    # Notes
    note_ids = fields.One2many('note.openprod', 'nonconformity_file_id', string='Notes', states=_get_states)

    
    #===========================================================================
    # Buttons
    #===========================================================================
    @api.multi
    def wkf_draft(self):
        """
            État à draft
        """
        self.write({'state': 'draft'})
    
    
    @api.multi
    def wkf_progress(self):
        """
            État à progress
        """
        self.write({'state': 'progress'})
        
        
    @api.multi
    def wkf_validated(self):
        """
            État à validated
        """
        self.write({'state': 'validated'})
    
    
    @api.multi
    def wkf_done(self):
        """
            État à done
        """
        self.write({'state': 'done'})
        
        
    @api.multi
    def wkf_cancel(self):
        """
            État à cancel
        """
        self.write({'state': 'cancel'})
    
    
    @api.multi
    def action_send_mail(self):
        for nonconformity in self:
            return self.env['mail.message'].action_send_mail(nonconformity.partner_id, 'nonconformity.file', '', nonconformity.id)
    
    
    @api.multi
    def button_return_move(self):
        for nonconformity in self:
            picking_id = nonconformity.move_id and nonconformity.move_id.picking_id and nonconformity.move_id.picking_id.id or False
            move_ids = nonconformity.move_id.id
            return {'name': _('Return picking'),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'stock.return.picking',
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'nodestroy': True,
                    'context': {'move_ids': move_ids, 'picking_id': picking_id, 'nonconformity_id': nonconformity.id}}
            
        return True

        
    #===========================================================================
    # Fonctions
    #===========================================================================
    def generate_with_control_declaration(self, control_declaration_rcs, move_hs_rcs=False, move_quarantine_rcs=False, type='intern', vals=None):
        nonconformity_hs_rcs = False
        nonconformity_quarantine_rcs = False
        if not vals:
            vals = {}
            
        partner_id = control_declaration_rcs.move_init_id and \
                     control_declaration_rcs.move_init_id.picking_id and \
                     control_declaration_rcs.move_init_id.picking_id.partner_id and \
                     control_declaration_rcs.move_init_id.picking_id.partner_id.id or False
        if control_declaration_rcs.nc_hs and move_hs_rcs:
            vals_hs = {'move_id': move_hs_rcs.id,
                       'product_id': move_hs_rcs.product_id.id,
                       'qty': move_hs_rcs.uom_qty,
                       'origin_type': type,
                       'origin': _('HS'),
                       'declaration_id': control_declaration_rcs.id,
                       'partner_id': partner_id}
            vals.update(vals_hs)
            nonconformity_hs_rcs = self.create(vals)
       
        if control_declaration_rcs.nc_quarantine and move_quarantine_rcs:
            vals_quarantine = {'move_id': move_quarantine_rcs.id,
                               'product_id': move_quarantine_rcs.product_id.id,
                               'qty': move_quarantine_rcs.uom_qty,
                               'origin': _('Quarantine'),
                               'origin_type': type,
                               'declaration_id': control_declaration_rcs.id,
                               'partner_id': partner_id}
            vals.update(vals_quarantine)
            nonconformity_quarantine_rcs = self.create(vals) 
        
        return nonconformity_hs_rcs, nonconformity_quarantine_rcs 
    
    
    def generate_manual(self, move):
        partner_id = move.picking_id and move.picking_id.partner_id and move.picking_id.partner_id.id or False
        vals = {'move_id': move.id,
                'product_id': move.product_id.id,
                'qty': move.uom_qty,
                'type': 'manual',
                'create_date': fields.Date.today(),
                'partner_id': partner_id}
        nonconformity_rcs = self.create(vals)  
        return nonconformity_rcs

        

class nonconformity_cause(models.Model):
    """ 
        Nonconformity Cause 
    """
    _name = 'nonconformity.cause'
    _description = 'Nonconformity Cause'
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Name', size=256, required=True)



class assists_inventory_label(models.Model):
    """ 
       assists with inventory entry label
    """
    _name = 'assists.inventory.label'
    _description = 'Assists with inventory entry label'

    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('validate', _('Validate')),
                ('cancel', _('Cancel')),
                       ]
    

    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    date = fields.Date(string='Date', default=lambda self: fields.Date.today(), required=True)
    user_id = fields.Many2one('res.users', string='Users', required=True, ondelete='restrict', default=lambda self: self.env.user.id)
    state = fields.Selection('_state_get', string='State', default='draft')
    line_ids = fields.One2many('assists.inventory.label.line', 'ail_id',  string='Lines')
    inventory_label_id = fields.Many2one('stock.inventory.label', string='Inventory label', required=True, ondelete='cascade')

    
    #===========================================================================
    # Button
    #===========================================================================
    @api.multi
    def wkf_validate(self):
        sill_obj = self.env['stock.inventory.label.line']
        for assits in self:
            inventory_label = assits.inventory_label_id
            for line in assits.line_ids:
                sill_rcs = sill_obj.search([('inventory_label_id', '=', inventory_label.id), 
                                            ('label_id', '=', line.label_id.id)], limit=1)
                
                if sill_rcs:
                    vals = {'make_inventory': True,
                            'assists_line_id': line.id}
                    
                    if sill_rcs.current_qty != line.qty:
                        vals['new_qty'] = line.qty
                        vals['to_update'] = True
                    
                    if sill_rcs.current_location_id.id != line.location_id.id:
                        vals['new_location_id'] = line.location_id.id
                        vals['to_update'] = True
                        
                    sill_rcs.write(vals)
                else:
                    vals_line = {
                                 'inventory_label_id': inventory_label.id,
                                 'label_id': line.label_id.id,
                                 'current_qty_inv': line.label_id.uom_qty,
                                 'new_qty': line.qty,
                                 'to_update': True,
                                 'make_inventory': True,
                                 'assists_line_id': line.id
                                 }
                    
                    if line.label_id.location_id.id != line.location_id.id and line.qty != 0:
                        vals_line['new_location_id'] = line.location_id.id
                    
                    sill_rcs.create(vals_line)
                
            assits.write({'state': 'validate'})
        
        return {'type':'ir.actions.act_window_view_reload'}
    
            
    @api.multi
    def button_open_assits_inventory(self):
        for assits in self:
            if assits.inventory_label_id.state not in ('draft','waiting'):
                raise except_orm(_('Error'), _('Inventory must be draft or waiting.'))
                
            return { 
                'type': 'ir.actions.act_window',
                'name': 'Assists inventory',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'assists.inventory.label',
                'res_id': assits.id,
                'target': 'new', }
    
    
    @api.multi
    def button_save(self):
        return True
    
    
    @api.multi
    def wkf_draft(self):
        self.write({'state': 'draft'})
    
    
    @api.multi
    def wkf_cancel(self):
        for assits in self:
            line_rcs = self.env['assists.inventory.label.line']
            for line in assits.line_ids:
                line_rcs |= line
            
            if line_rcs:
                for inv_line in self.env['stock.inventory.label.line'].search([('assists_line_id', 'in', line_rcs.ids)]):
                    inv_line.write({
                                    'to_update': False,
                                    'make_inventory': False,
                                    'current_qty_inv': inv_line.label_id.uom_qty,
                                    'new_qty': inv_line.label_id.uom_qty,
                                    'new_location_id': False,
                                    })
        
        self.write({'state': 'cancel'})
        return {'type':'ir.actions.act_window_view_reload'}
    
    
    
class assists_inventory_label_line(models.Model):
    """ 
       Line assists with inventory entry label
    """
    _name = 'assists.inventory.label.line'
    _description = 'Line assists with inventory entry label'    
    _rec_name = 'label_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    ail_id = fields.Many2one('assists.inventory.label', string='WAIL', required=False, ondelete='cascade')
    label_id = fields.Many2one('stock.label', string='Label', required=True, ondelete='cascade')
    location_id = fields.Many2one('stock.location', string='Location', required=False, ondelete='cascade')
    qty = fields.Float(string='Qty', default=None, required=True)
        
        
    
class stock_inventory_label(models.Model):
    """ 
        Inventory Label
    """
    _name = 'stock.inventory.label'
    _description = 'Inventory Label'
    

    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('waiting', _('Waiting for validation')),
                ('done', _('Validated')),
                ('cancel', _('Cancelled')),
                       ]
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    date = fields.Datetime(string='Inventory Date', default=lambda self: fields.Datetime.now(), required=True)
    line_ids = fields.One2many('stock.inventory.label.line', 'inventory_label_id',  string='Inventories')
    move_ids = fields.One2many('stock.move', 'inventory_label_id',  string='Moves')
    state = fields.Selection('_state_get', string='State', default='draft')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id, required=True, ondelete='restrict')
    location_id = fields.Many2one('stock.location', string='Location', required=False, ondelete='restrict')
    move_date = fields.Datetime(string='Move date', default=lambda self: fields.Datetime.now(), required=True)
    assists_inventory_ids = fields.One2many('assists.inventory.label', 'inventory_label_id',  string='Assists inventory')
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('date')
    def _onchange_date(self):
        self.move_date = self.date
        
        
    #===========================================================================
    # Boutons
    #===========================================================================
    @api.multi
    def wkf_draft(self):
        for inventory in self:
            if inventory.move_ids:
                inventory.move_ids.wkf_cancel()
                inventory.move_ids.unlink()
            
            inventory.line_ids.write({'update1': False})
            
        self.write({'state': 'draft'})
    
    
    @api.multi
    def wkf_waiting(self):
        self.write({'state': 'waiting'})
    
    
    @api.multi
    def wkf_done(self):
        inv_label_line_obj = self.env['stock.inventory.label.line']
        for inventory in self:
            inventory.button_compute_qty_line()
            inventory.create_move_inventory_label()
            inventory.validation_move_inventory_label()
            ill_rcs = inv_label_line_obj.search([('inventory_label_id', '=', inventory.id), ('to_update', '=', True)])
            if ill_rcs:
                ill_rcs.write({'update1': True})

        self.write({'state': 'done'})

    
    @api.multi
    def wkf_cancel(self):
        self.write({'state': 'cancel'})
        for inventory in self:
            if inventory.move_ids:
                inventory.move_ids.wkf_cancel()
    
    
    @api.multi
    def button_del_line(self):
        for inventory in self:
            if inventory.line_ids and inventory.state in ('draft', 'cancel', 'line_confirm'):
                inventory.line_ids.unlink()
        
        return {'type': 'ir.actions.act_window_close'}


    @api.multi
    def button_importation(self):
        """
            Bouton qui génère les lignes d'inventaire
        """
        location_obj = self.env['stock.location']
        inventory_label_line_obj = self.env['stock.inventory.label.line']
        label_obj = self.env['stock.label']
        self.button_del_line()
        for inventory in self:
            if inventory.state != 'draft':
                raise except_orm(_('Error'), _('Inventory must be draft.'))
            
            if inventory.location_id:
                # Recherche la liste des emplacements fils
                location_rcs = location_obj.search([('location_id', 'child_of', [inventory.location_id.id])], order="id")
                if location_rcs:
                    if inventory.location_id.id not in location_rcs.ids:
                        location_rcs += inventory.location_id
                        
                    location_ids = location_rcs and location_rcs.ids
                else:
                    location_rcs = inventory.location_id
                    location_ids = [inventory.location_id.id]
            
            else:
                location_ids = []

            #  par emplacement
            if location_ids:
                label_rcs = self.env['stock.label']
                for location in location_ids:
                    label_rcs_int = label_obj.search([('location_id','=',location), ('is_active', '=', True)])
                    if label_rcs_int:
                        label_rcs += label_rcs_int
                        
            else:
                label_rcs = label_obj.search([('is_active', '=', True)])
            
            if not label_rcs:
                raise except_orm(_('Error'), _('No active label.'))
            
            # Création des lignes
            existing_label_ids = [x.label_id.id for x in inventory.line_ids if x.label_id]
            for label in label_rcs:
                if label.id not in existing_label_ids:
                    label_read = label.read(['uom_qty'], load='_classic_write')[0]
                    vals_line = {'inventory_label_id': inventory.id,
                                 'automatic': True,
                                 'label_id': label_read['id'],
                                 'current_qty_inv': label_read['uom_qty'],
                                 'new_qty': label_read['uom_qty']}
                    inventory_label_line_obj.create(vals_line)
            
            inventory.write({'date': fields.Datetime.now(), 'move_date': fields.Datetime.now()})
            
        return {'type': 'ir.actions.act_window_close'}
    
    
    @api.multi
    def button_to_update(self):
        for inventory in self:
            line_rcs = self.env['stock.inventory.label.line']
            for line in inventory.line_ids:
                if (line.current_qty != line.new_qty and (line.new_qty !=0 or line.make_inventory)) or line.new_location_id:
                    line_rcs += line
        
            if line_rcs:
                line_rcs.write({'to_update': True})
    
    
    @api.multi
    def button_compute_qty_line(self):
        """
            Bouton qui permet de recalculer la qté
        """
        for inventory in self:
            for line in inventory.line_ids:
                line.write({'current_qty_inv': line.label_id.uom_qty, 'uom_id': line.label_id.uom_id.id})
                    
        return True
    
    
    @api.multi
    def button_create_assits_inventory(self):
        for inventory in self:
            name = '%s %s'%(inventory.name, fields.Date.today())
            assits = self.env['assists.inventory.label'].create({'name':name, 'inventory_label_id': inventory.id})
            return { 
                'type': 'ir.actions.act_window',
                'name': 'Assists inventory',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'assists.inventory.label',
                'res_id': assits.id,
                'target': 'new', }
    
    
    #===========================================================================
    # Fonction
    #===========================================================================
    def create_move_inventory_label(self):
        """
            Fonction qui crée les mouvements de l'inventaire
        """
        inventory_location_rcs = self.env['stock.location'].search([('usage', '=', 'inventory')], limit=1)
        move_label_obj = self.env['stock.move.label']
        if not inventory_location_rcs:
            raise except_orm(_('Error'), _('There is not configure inventory location.'))
        
        move_date = self.move_date
        for line in self.line_ids:
            if line.to_update:
                origin =  _('Inventory %s'%(self.name))
                if line.new_location_id and line.current_location_id and line.new_location_id.id != line.current_location_id.id:
                    location_dest_rcs = line.new_location_id
                else:
                    location_dest_rcs = False
                
                move_label_ids = move_label_obj.search([('label_id', '=', line.label_id.id), ('done_date', '>=', move_date)], limit=1)
                if move_label_ids:
                    raise except_orm(_('Error'), _('There is a movement label %s of higher on the date you have chosen.')%(line.label_id.name))
                    
                if line.current_location_id:
                    move_rcs = line.label_id.balancing(line.new_qty, location=location_dest_rcs, move_rs=None, counterpart_location_id=inventory_location_rcs.id)
                    move_rcs.write({'inventory_label_id': self.id, 'origin': origin, 'date': move_date, 'priority_date': move_date, 
                                    'date_expected': move_date,  'done_date': move_date, 'no_control': True})
                
        return True
    
    
    def validation_move_inventory_label(self):
        """
            Fonction qui valide les mouvements de l'inventaire
        """
        if self.move_ids:
            move_rcs = self.move_ids.filtered(lambda m: m.state == 'draft')
            move_rcs.wkf_waiting()
            move_rcs.wkf_done()
#             move_rcs.write({'date': self.move_date})
        else:
            raise except_orm(_('Error'), _('No amount in the lines has been changed.'))
        
        return True

        
    
class stock_invetory_label_line(models.Model):
    """ 
        Inventory Label Line 
    """
    _name = 'stock.inventory.label.line'
    _description = 'Inventory Label Line'
    _rec_name = 'label_id'
    

    @api.one
    @api.depends('label_id')
    def _compute_label(self):
        self.current_location_id = self.label_id and self.label_id.location_id and self.label_id.location_id.id or False
        self.product_id = self.label_id and self.label_id.product_id and self.label_id.product_id.id or False
        self.uom_id = self.label_id and self.label_id.uom_id and self.label_id.uom_id.id or False
    
    
    @api.one
    @api.depends('current_qty_inv')
    def _compute_qty(self):
        self.current_qty = self.current_qty_inv
        
    @api.one
    @api.depends('new_qty', 'current_qty', 'make_inventory')
    def _compute_qty_error(self):
        if self.current_qty != self.new_qty and (self.make_inventory or self.to_update):
            self.qty_error = True
        else:
            self.qty_error = False
    
    
    @api.one
    @api.depends('current_location_id', 'new_location_id', 'make_inventory')
    def _compute_location_error(self):
        if self.current_location_id and self.new_location_id and self.new_location_id.id != self.current_location_id.id and (self.make_inventory or self.to_update):
            self.location_error = True
        else:
            self.location_error = False     
    
    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('waiting', _('Waiting for validation')),
                ('done', _('Validated')),
                ('cancel', _('Cancelled')),
                       ]
           
            
    #===========================================================================
    # COLUMNS
    #===========================================================================
    inventory_label_id = fields.Many2one('stock.inventory.label', string='Inventory', required=False, ondelete='cascade')
    label_id = fields.Many2one('stock.label', string='Label', required=True, ondelete='restrict')
    product_id = fields.Many2one('product.product', string='Product', compute='_compute_label', store=True)
    current_qty = fields.Float(string='Current Quantity', compute='_compute_qty', store=True)
    current_qty_inv = fields.Float(string='Current Quantity Invisible', default=0.0)
    current_location_id = fields.Many2one('stock.location', string='Current location', compute='_compute_label', store=True)
    uom_id = fields.Many2one('product.uom', string='UoM', compute='_compute_label', ondelete='restrict', store=True)
    new_qty = fields.Float(string='New Quantity', default=0.0, required=False)
    new_location_id = fields.Many2one('stock.location', string='New location', ondelete='restrict')
    make_inventory = fields.Boolean(string='Make inventory', default=False)
    qty_error = fields.Boolean(string='Qty error', compute='_compute_qty_error', store=True)
    location_error = fields.Boolean(string='Location error', compute='_compute_location_error', store=True)
    to_update = fields.Boolean(string='To Update', default=False)
    update1 = fields.Boolean(string='Update', default=False)
    automatic = fields.Boolean(string='Automatic', default=False)
    state = fields.Selection('_state_get', string='State', related='inventory_label_id.state', default='draft', readonly=True)
    assists_line_id = fields.Many2one('assists.inventory.label.line', string='Assists line', required=False, ondelete='set null')
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('label_id')
    def _onchange_label_id(self):
        self.current_qty_inv = self.label_id and self.label_id.uom_qty or 0.0 
             
    
    
class common_attribute(models.Model):
    _name = 'common.attribute'
    
    @api.one
    @api.depends('uc_label_id')
    def _compute_active_label(self):
        self.name = True

    
    def _search_active_label(self, operator, value):
        self.env.cr.execute('SELECT c.id FROM common_attribute c JOIN stock_label l on c.uc_label_id = l.id WHERE l.is_active')
        return [('id', 'in', self.env.cr.fetchall())]
    
    
    uc_label_id = fields.Many2one('stock.label', string='UC Label', ondelete='cascade', domain=[('type', '=', 'uc')], select=True)
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='restrict', select=True)
    name = fields.Char(size=64, required=True)
    label = fields.Char(size=64, required=False)
    value = fields.Text(group_operator='sum', allow_sum=True)
    label_uom_qty = fields.Float(related='uc_label_id.uom_qty', string='Quantity', required=False, readonly=True)
    label_uom_id = fields.Many2one(related='uc_label_id.uom_id', string='UoM', required=False, readonly=True)
    active_label = fields.Boolean(string='Active label', compute='_compute_active_label', search='_search_active_label')


    @api.multi
    def unlink(self):
        # Évite un bug qui supprimer les attributs avant d'essayer de les affecter à la ligne
        if self.env.context.get('without_unlink_attributes'):
            res = False
        else:
            res = super(common_attribute, self).unlink()
            
        return res
    
        
        
class stock_move_parameter(models.Model):
    """ 
    Stock Move Parameter 
    """
    _name = 'stock.move.parameter'
    _description = 'Stock Move Parameter'
    _rec_name = 'move_id'
    
    @api.model
    def _type_component_get(self):
        return [
                ('fixed', _('Fixed')),
                ('variable', _('Variable')),
                ('formula', _('Formula')),
                       ]
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    move_id = fields.Many2one('stock.move', string='Move', required=False, ondelete='cascade')
    type_component = fields.Selection('_type_component_get', string='Type component', required=False)
    formula_component = fields.Text(string='Formula Qty')
    qty_bom = fields.Float(string='Qty BoM', default=0.0, required=False)
    qty_component = fields.Float(string='Qty component', default=0.0, required=False)
    round_component = fields.Float(string='Round component', default=0.0, required=False)
    eff_component = fields.Float(string='Eff component', default=0.0, required=False)
    property_ids = fields.Many2many('purchase.property', string='Properties')



class warehouse_transfer_delay(models.Model):
    _name = 'warehouse.transfer.delay'
    _sql_constraints = [
        ('warehouse_uniq', 'unique(warehouse_id, warehouse_dest_id)', 'Transfer already exists'),
    ]
    #===========================================================================
    # COLUMNS
    #===========================================================================
    warehouse_id = fields.Many2one('stock.warehouse', string='Src. warehouse', required=True, select=True, ondelete='restrict')
    warehouse_dest_id = fields.Many2one('stock.warehouse', string='Dest. warehouse', required=True, select=True, ondelete='restrict')
    delay = fields.Integer(default=0, required=True)
    
    def get(self, warehouse_id, warehouse_dest_id):
        this = self.search([('warehouse_id', '=', warehouse_id), ('warehouse_dest_id', '=', warehouse_dest_id)], limit=1)
        if this:
            res = this.read(['delay'])
            res = res and res[0]['delay'] or 0
        else:
            res = 0
            
        return res
    
    
class stock_transfer_request(models.Model):
    """ 
        Stock transfer request
    """
    _name = 'stock.transfer.request'
    _description = 'Warehouse transfer request'
    
        
    @api.model
    def _state_get(self):
        return [
            ('draft', 'Draft'),
            ('done', 'Done'),
            ('cancel', 'Cancel'),
               ]


    def _get_states(self):
        return {
            'done': [('readonly', True)], 
            'cancel': [('readonly', True)], 
                }


    @api.multi
    def name_get(self):
        """
            Name get du transfert
        """
        return [(m.id, '%s (id: %d)'%(m.origin or '/', m.id)) for m in self]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    origin = fields.Char(required=False, size=128, states=_get_states)
    product_id = fields.Many2one('product.product', string='Product', required=True, select=True, ondelete='restrict', states=_get_states)
    warehouse_id = fields.Many2one('stock.warehouse', string='Src. warehouse', required=True, ondelete='restrict', states=_get_states)
    warehouse_dest_id = fields.Many2one('stock.warehouse', string='Dest. warehouse', required=True, ondelete='restrict', states=_get_states)
    is_automatic = fields.Boolean(string='Automatic', default=False, states=_get_states, help='If this field is checked, when a stock move will be processed, the corresponding stock move will also be processed')
    state = fields.Selection('_state_get', required=True, default='draft', copy=False)
    uom_qty = fields.Float(string='Quantity', required=True, digits=dp.get_precision('Product quantity'), default=0.0, states=_get_states)
    uom_id = fields.Many2one('product.uom', string='UoM', required=True, ondelete='restrict', states=_get_states)
    needed_uom_qty = fields.Float(string='Needed quantity', required=True, digits=dp.get_precision('Product quantity'), default=0.0, states=_get_states)
    needed_uom_id = fields.Many2one('product.uom', string='UoM', required=True, ondelete='restrict', states=_get_states)
    need_date = fields.Date(default=lambda self: fields.Date.today(), required=True, states=_get_states)
    departure_date = fields.Date(default=lambda self: fields.Date.today(), required=True, states=_get_states)
    procurement_id = fields.Many2one('procurement.order', string='Procurement', required=False, ondelete='restrict')
    in_move_ids = fields.One2many('stock.move', 'transfer_id',  string='IN stock moves', domain=[('type', '=', 'in')])
    out_move_ids = fields.One2many('stock.move', 'transfer_id',  string='OUT stock moves', domain=[('type', '=', 'out')])
    
    price = fields.Float(string='Price', digits=dp.get_precision('Product price'))
    is_billable = fields.Boolean(string='Billable', default=False)
    partner_id = fields.Many2one('res.partner', string='Partner', required=False, ondelete='cascade', domain=[('is_company', '=', True)])
    label_ids = fields.Many2many('stock.label', 'stock_transfer_label_rel', 'transfer_id', 'label_id',  string='Labels')
    

    def get_departure_date(self, need_date, warehouse_id=False, warehouse_dest_id=False):
        warehouse_transfer_delay_obj = self.env['warehouse.transfer.delay']
        transfer_factor = self.env['stock.config.settings'].get_param('warehouse_transfer_factor')
        res = self.env.user.company_id.transport_calendar_id.get_date_inverse(need_date or fields.Date.today(), 
                                                                              transfer_factor * warehouse_transfer_delay_obj.get(warehouse_id or self.warehouse_id.id, 
                                                                                                                                 warehouse_dest_id or self.warehouse_dest_id.id))
        return res
        
    
    @api.onchange('need_date')
    def _onchange_need_date(self):
        self.departure_date = self.get_departure_date(self.need_date)
        
        
    @api.multi
    def create_transfer_move(self, picking):
        res = self.env['stock.move']
        move_obj = self.env['stock.move']
        transfer_location_rs = self.env['stock.location'].get_transfer_location(with_raise=True)
        for transfer in self:
            move_rc = move_obj.create_move(transfer.product_id, 
                                        src_location=transfer.warehouse_id.delivery_location_id.id, 
                                        dst_location=transfer_location_rs.id, 
                                        qty=transfer.uom_qty, 
                                        uom=transfer.uom_id, 
                                        sec_qty=None, 
                                        sec_uom=None, 
                                        type='out', 
                                        date=transfer.departure_date, 
                                        picking=picking, 
                                        partner=picking.partner_id, 
                                        with_price=True,
                                        other_data={
                                            'transfer_id': transfer.id, 
                                            'partner_price': transfer.price, 
                                            'currency_id': picking.partner_id.currency_id.id
                                        })
            res |= move_rc
            if transfer.label_ids and move_rc:
                move_rc.assign_label(transfer.label_ids, dict_label_qty=None, with_scrap=False, with_write=False, with_move=True, inactive=False)
        
        return res
        
        
    @api.multi
    def affect_to_picking(self, picking_rs):
        """
            Crée et affecte le mouvement de transfert
        """
        if picking_rs:
            for transfer in self:
                move_rs = transfer.create_transfer_move(picking_rs)
                if move_rs:
                    move_rs.wkf_waiting()
                    
                transfer.wkf_done()
                
        return True
        

    @api.multi
    def create_transfer_picking_button(self):
        return self.create_transfer_picking()
            
    
    def create_transfer_picking(self, without_waiting=False):
        """
            Crée un transfert entre deux entrepôts de la société
        """
        picking_obj = self.env['stock.picking']
        company_partner_rs = self.env.user.company_id.partner_id
        for transfer in self:
            picking_rs = picking_obj.create_picking('out', 
                                                    partner=transfer.partner_id or company_partner_rs, 
                                                    date=transfer.departure_date,
                                                    other_data = {'is_automatic': transfer.is_automatic,
                                                                  'is_partial': True,
                                                                  'manage_scrap': True,
                                                                  'invoice_state': transfer.is_billable and '2binvoiced' or 'none',
                                                                  'origin': _('Transfer request')})
        
            if picking_rs:
                transfer.create_transfer_move(picking_rs)
                if not without_waiting:
                    picking_rs.wkf_waiting()
                
            transfer.wkf_done()
            
        return picking_rs
   
   
    @api.multi
    def open_source_procurement(self):
        """
            Fonction permettant d'afficher le procurement déclencheur
        """
        return self.env['procurement.order']._open_source_procurement(('transfer_id', '=', self[0].id))
     
    
    @api.multi
    def take_out_picking(self):
        """
            Enlève les mouvements OUT des pickings auxquels ils sont affectés et les annule
        """
        move_rs = self.env['stock.move'].search([('transfer_id', 'in', self.ids), ('state', 'in', ('draft', 'waiting')), ('type', '=', 'out')])  
        move_rs.write({'picking_id': False})
        self.wkf_cancel(move_rs)
        return True
    
    
    def wkf_cancel(self, move_rs=None):
        move_obj = self.env['stock.move']
        if not move_rs:
            move_rs = move_obj.search([('transfer_id', 'in', self.ids), ('state', 'in', ('draft', 'waiting')), ('type', '=', 'out')])
            
        if move_rs:  
            move_rs.wkf_cancel()
            
        self.write({'state': 'cancel'})
        return True
    
    
    @api.multi
    def wkf_cancel_button(self):
        return self.wkf_cancel()
    
    
    @api.multi
    def wkf_done(self):
        self.write({'state': 'done'})
        return True
    
    
    @api.multi
    def wkf_draft(self):
        self.write({'state': 'draft'})
        return True
    


class stock_location(models.Model):
    """ 
    Stock Location
    """
    _inherit = 'stock.location'
    
    
    def get_transfer_location(self, with_raise=False):
        transfert_location_rc = self.search([('usage', '=', 'transit')], limit=1)
        if not transfert_location_rc and with_raise:
            raise except_orm(_('Error'), _('No transit location found.'))
        
        return transfert_location_rc
    
    
    def get_location_product_qty(self, product_obj, uom_obj, move_obj, in_args=None, out_args=None):
        """
            Permet de calculer la quantité dans un emplacement
            :type self: stock.inventory
            :param self: L'emplacement de base sur lequel on cherche la qty
            :type self: id: stock.location
            :type product_obj: product.product
            :type uom_obj: product.uom
            :type move_obj: stock.move
            :param in_args: Liste des arguments pour le search des mouvements entrant dans l'emplacement (location_dest_id) qty positive
            :type in_args: list d'argument
            :param out_args: Liste des arguments pour le search des mouvements sortant dans l'emplacement (location_id) qty négative
            :type out_args: list d'argument
            :return: On retourne un dico avec comme clé (product_id, location_id) et comme valeur {'product_id': product_id, 
                                                                                             'location_id': location_id, 
                                                                                             'theoretical_qty': theoretical_qty, 
                                                                                             'theoretical_qty_inv': theoretical_qty_inv,
                                                                                             'uom_id': uom_id, 
                                                                                             'quantity': quantity}
            :rtype: dico
        """
        location = self
        if not location:
            raise except_orm(_('Error'), _('Compulsory Location.'))
            
        datas = {}
        if in_args:
            in_move_qtys = move_obj.search_group(fields=['uom_qty', 'uom_id','product_id'], 
                                     groupby=['product_id', 'uom_id'], 
                                     args=in_args,
                                     sum='uom_qty',
                                     return_dict=True)
            
            product_in_ids = list(set([x['product_id'] for x in in_move_qtys]))
            product_in_uom_dict = {x['id']: x['uom_id'] for x in product_obj.browse(product_in_ids).read(['uom_id'], load='_classic_write')}
            for in_move_qty in in_move_qtys:
                prod_id = in_move_qty['product_id']
                if product_in_uom_dict[prod_id] != in_move_qty['uom_id']:
                    qty = uom_obj._compute_qty(in_move_qty['uom_id'], in_move_qty['uom_qty'], to_uom_id=product_in_uom_dict[prod_id], with_raise=True, with_round=False)
                else:
                    qty = in_move_qty['uom_qty']
                    
                if datas.get((prod_id, location.id)):
                    datas[(prod_id, location.id)]['theoretical_qty'] += qty
                    datas[(prod_id, location.id)]['quantity'] += qty
                    datas[(prod_id, location.id)]['theoretical_qty_inv'] += qty
                else:
                    datas[(prod_id, location.id)] = {'product_id': in_move_qty['product_id'], 'location_id': location.id, 'theoretical_qty': qty, 
                                                  'theoretical_qty_inv': qty, 'uom_id': product_in_uom_dict[prod_id], 'origin_uom_id': product_in_uom_dict[prod_id], 'quantity': qty, 'automatic':True}
                    
        if out_args:   
            out_move_qtys = move_obj.search_group(fields=['uom_qty', 'uom_id','product_id'], 
                                     groupby=['product_id', 'uom_id'], 
                                     args=out_args,
                                     sum='uom_qty',
                                     return_dict=True)
            
            product_out_ids = list(set([x['product_id'] for x in out_move_qtys]))
            product_out_uom_dict = {x['id']: x['uom_id'] for x in product_obj.browse(product_out_ids).read(['uom_id'], load='_classic_write')}
            for out_move_qty in out_move_qtys:
                prod_id = out_move_qty['product_id']
                if product_out_uom_dict[prod_id] != out_move_qty['uom_id']:
                    qty = -uom_obj._compute_qty(out_move_qty['uom_id'], out_move_qty['uom_qty'], to_uom_id=product_out_uom_dict[prod_id], with_raise=True, with_round=False)
                else:
                    qty = -out_move_qty['uom_qty']
                    
                if datas.get((prod_id, location.id)):
                    datas[(prod_id, location.id)]['theoretical_qty'] += qty
                    datas[(prod_id, location.id)]['quantity'] += qty
                    datas[(prod_id, location.id)]['theoretical_qty_inv'] += qty
                else:
                    datas[(prod_id, location.id)] = {'product_id': out_move_qty['product_id'], 'location_id': location.id, 'theoretical_qty': qty, 
                                                  'theoretical_qty_inv': qty, 'uom_id': product_out_uom_dict[prod_id], 'origin_uom_id': product_out_uom_dict[prod_id], 'quantity': qty, 'automatic':True}    
                   
        return datas
    
        
    
    @api.multi
    def write(self, vals=None):
        """
            Interdiction de changer de d'entrepôt ou de type si l'emplacement est utilisé dans un mouvement
        """
        if not vals:
            vals = {}

        if 'usage' in vals:
            if vals['usage'] != 'view':
                if self.search([('location_id', 'in', self.ids)], limit=1):
                    raise UserError(_('Impossible to change type: this location have one or several child(s).'))
                
        if 'warehouse_id' in vals or 'usage' in vals:
            if self.env['stock.move'].search(['|', ('location_id', 'in', self.ids),
                                                   ('location_dest_id', 'in', self.ids)], limit=1):
                raise UserError(_('Impossible to change location type or warehouse if location is used by a stock move.'))
            
        return super(stock_location, self).write(vals=vals)



class stock_move_history(models.Model):
    """ 
        Stock move history
    """
    _name = 'stock.move.history'
    _description = 'Stock move history'
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade', select=True)   