# -*- coding: utf-8 -*-
from openerp.tools.translate import _
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.addons.base_openprod import utils
from openerp.exceptions import except_orm, ValidationError, Warning
from openerp.addons.base_openprod.common import get_form_view, roundingUp
from openerp.workflow.workitem import WorkflowItem
from dateutil.relativedelta import relativedelta
from decimal import Decimal

# mapping invoice type to journal type
TYPE2JOURNAL = {
    'out_invoice': 'sale',
    'in_invoice': 'purchase',
    'out_refund': 'sale_refund',
    'in_refund': 'purchase_refund',
}

class res_currency(models.Model):
    _inherit = "res.currency"
    
    def compute_purchase_domain_args(self, args):
        #Fonction appelée par le search afin de ne pas pouvoir changer de devise
        #si on a des lignes d'achat
        args2 = []
        for arg in args:
            match = False
            if isinstance(arg, str) or (isinstance(arg, list) and arg[0] in ('!', '|', '&')):
                args2.append(arg)
                continue
            
            if arg[0] == 'purchase_order_currency_domain':
                if isinstance(arg[-1], list) and arg[-1][0]:
                    arg = ('id', '=', arg[-1][1])
                else:
                    match = True
                    
            if not match:
                args2.append(arg)
             
        return args2
 
     
    @api.model
    def search(self,args=None, offset=0, limit=None, order=None, count=None):
        #Modification du search afin de ne pas pouvoir changer de devise
        #si on a des lignes d'achat
        args = args or []
        args_modified = self.compute_purchase_domain_args(args)
        return super(res_currency,self).search(args=args_modified, offset=offset, limit=limit, order=order, count=count)
    
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=1000):
        """
            Fonction name_search de la devise
        """
        args = self.compute_purchase_domain_args(args)
        recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()
    
    

class purchase_order_line_section(models.Model):
    """ 
    Section for purchase order lines 
    """
    _name = 'purchase.order.line.section'
    _description = 'Section for purchase order lines'
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
    purchase_id = fields.Many2one('purchase.order', string='Purchase', required=False, ondelete='set null')
    
    

class purchase_family(models.Model):
    """
    Purchase Family
    """
    _name = 'purchase.family'
    _description = 'Purchase Family'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    


class purchase_order_line(models.Model):
    """ 
    Purchase order line 
    """
    _name = 'purchase.order.line'
    _description = 'Purchase order line'
    _order = 'sequence asc'
    
    
    @api.multi
    @api.depends('name')
    def name_get(self):
        """
            On affiche : nom [sequence]
        """
        result = []
        for order_line in self:
            if order_line.purchase_order_id:
                name = '%s [%s]'%(order_line.purchase_order_id.name, order_line.sequence)
            else:    
                name = order_line.name
                 
            result.append((order_line.id, name))
             
        return result
    
    
    @api.model
    def _purchase_state_get(self):
        return [
                ('draft', _('Draft')),
                ('waiting', _('Waiting')),
                ('progress', _('In progress')),
                ('done', _('Done')),
                ('cancel', _('Cancelled')),
                       ]
    
    
    @api.model
    def _purchase_type_get(self):
        return [
                ('prototype', _('Prototype')),
                ('series', _('Series')),
                ('call', _('Called order')),
                ('open', _('Open order')),
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
    
    
    @api.one
    @api.depends('confirmed_date', 'expected_date')
    def _compute_date(self):
        """
            Fonction qui calcule le jour, la semaine, le mois et l'année de la ligne d'achat
        """
        date = False
        #On prend la date de départ confirmée
        if self.confirmed_date:
            date = fields.Date.from_string(self.confirmed_date)
        #Ou la date de départ
        elif self.expected_date:
            date = fields.Date.from_string(self.expected_date)
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
    @api.depends('product_id')
    def _compute_pol_ids(self):
        """
            On récupère toutes les lignes d'achat non terminées du produit
        """
        if self.product_id:
            list_line = []
            if self.id:
                for line in self.search([('product_id', '=', self.product_id.id), ('purchase_state', 'not in', ['done', 'cancel']), 
                                         ('id', '!=', self.id)]):
                    list_line.append(line.id)
            else:
                for line in self.search([('product_id', '=', self.product_id.id), ('purchase_state', 'not in', ['done', 'cancel'])]):
                    list_line.append(line.id)
        else:
            list_line = []
        
        self.pol_ids = list_line
    
    
    @api.one
    @api.depends('price_unit', 'uoi_qty')
    def _compute_total_price(self):
        """
            Fonction permettant de calculer le prix total de la ligne d'achat
        """
        price = self.price_unit
        taxes = self.taxes_ids.compute_all(price, self.currency_id, self.uoi_qty, product=self.product_id, partner=self.purchase_partner_id)
        total_price = taxes['total_excluded']
        self.total_price = (self.currency_id.round(total_price))
            
    
    @api.one
    @api.depends('stock_move_ids', 'stock_move_ids.state', 'expected_date', 'confirmed_date')
    def _compute_lateness(self):
        """
            Fonction permettant de savoir s'il y a du retard ou non pour la livraison
        """
        if self.product_id.type == 'service' and not self.product_id.manage_service_receipt:
            self.lateness = False
        else:
            if self.confirmed_date:
                date = self.confirmed_date
            else:
                date = self.expected_date
            
            if date < fields.Date.today():
                self.lateness = True
            else:
                self.lateness = False
    
    
    def _search_lateness(self, operator, value):
        """
            Fonction search du booléen de retard
        """ 
        query = """
            SELECT 
                line.id 
            FROM 
                purchase_order_line line 
            LEFT OUTER JOIN
                product_product product ON product.id=line.product_id
            WHERE
                line.received_qty = 0
            AND
                ((line.confirmed_date IS NOT NULL and line.confirmed_date < current_date) 
                OR
                (line.confirmed_date IS NULL and line.expected_date < current_date))
            AND
                (product.type != 'service' OR product.manage_service_receipt = true)
        """
        self.env.cr.execute(query)
        res_ids = self.env.cr.fetchall()
        return [('id', 'in', res_ids)]
    
    
    @api.one
    @api.depends('need_date', 'property_ids', 'product_id', 'purchase_partner_id.purchase_delivery_delay')
    def _compute_limit_date(self):
        """
            Fonction permettant de déterminer la date limite d'envoi
            On fait: 
            date du besoin - (délai du référencement fournisseur en jour ouvré - délai fournisseur en jour ouvré)
        """
        if self.need_date:
            #On commence par récupérer les informations du référencement fournisseur s'il y en a un
            supplier_info_delay = 0
            if self.product_id and not self.product_id.free_purchase:
                supplier = self.product_id.get_sinfo(partner_id=self.purchase_partner_id.id, property_ids=self.property_ids.ids, state_dev=False)
                supplier_info_delay = supplier and supplier.delivery_delay or 0
            
            #On récupère le délai du fournisseur
            supplier_delay = self.purchase_partner_id.purchase_delivery_delay or 0
            #On calcule la date de début
            self.limit_send_date = self.purchase_partner_id.calendar_id.get_date_inverse(self.need_date, (supplier_info_delay + supplier_delay))
        else:
            self.limit_send_date = False
    
    
    @api.one
    @api.depends('price_unit', 'uoi_qty', 'currency_id', 'purchase_order_id.creation_date',
                 'purchase_order_id.confirmation_date')
    def _compute_price_with_currency(self):
        """
            Fonction permettant de calculer le prix total de la ligne d'achat dans la devise de
            la société ainsi que le taux de conversion utilisé lors du calcul
        """
        company_currency = self.purchase_order_id.company_id.currency_id
        line_currency = self.currency_id or self.purchase_order_id.currency_id
        if line_currency and line_currency != company_currency:
            context2 = {}
            if self.purchase_order_id.confirmation_date:
                context2 = {'date': self.purchase_order_id.confirmation_date}
            else:
                context2 = {'date': self.purchase_order_id.creation_date}
            
            self.total_price_currency = line_currency.with_context(context2).compute((self.price_unit * self.uoi_qty), company_currency)
            self.currency_rate = line_currency.with_context(context2)._get_conversion_rate(line_currency, company_currency)
        
        else:
            self.total_price_currency = self.price_unit * self.uoi_qty
            self.currency_rate = 0
    
    
    @api.one
    @api.depends('purchase_order_id.called_order_ids', 'sec_uom_qty')
    def _compute_remaining_called_order_qty(self):
        """
            Fonction permettant de calculer la quantité restante à acheter d'une commande ouverte
        """
        purchase = self.purchase_order_id
        qty = 0
        #On vérifie que l'achat soit de type ouvert et qu'il ne soit pas annulé
        if purchase.purchase_type == 'open' and self.purchase_state != 'cancel':
            uom_obj = self.env['product.uom']
            #On récupère le produit et l'unité de vente de la ligne
            product_id = self.product_id and self.product_id.id
            sec_uom_rs = self.sec_uom_id 
            #On parcourt la liste des commandes appelées de l'achat
            for called_order in purchase.called_order_ids:
                if called_order.state != 'cancel':
                    #On parcourt les lignes d'achats des commandes appelées d'achat
                    for called_order_line in called_order.purchase_order_line_ids:
                        #Pour chaque ligne, si on tombe sur le même produit on ajoute cette quantité au total
                        if called_order_line.product_id and product_id == called_order_line.product_id.id:
                            qty += uom_obj._compute_qty_obj(called_order_line.sec_uom_id, called_order_line.sec_uom_qty, sec_uom_rs)
        
        remaining_qty = self.sec_uom_qty - qty
        self.remaining_called_qty = remaining_qty >= 0 and remaining_qty or 0
        
        
    @api.one
    @api.depends('stock_move_ids')
    def _compute_color_line(self):
        """
            Fonction permettant de récupérer la plus haute valeur de priorité des moves
        """
        color_priority_need_read = self.env['stock.move'].search_read([('id', 'in', self.stock_move_ids.ids)], ['color_priority_need'], limit=1, order='color_priority_need desc')
        color_priority_need = color_priority_need_read and color_priority_need_read[0]['color_priority_need'] or 0
        self.purchase_line_color = color_priority_need
    
    
    @api.one
    @api.depends('product_id', 'product_id.sinfo_ids')
    def _compute_x_four_price(self):
        """
            Fonction permettant de cocher ou décocher les champs de multiple fournisseur et multiple
            prix
        """
        product = self.product_id
        suppinfos = []
        price_lines = []
        if not product.free_purchase:
            partner = self.purchase_order_id.partner_id
            for supplierinfo in product.sinfo_ids:
                suppinfos.append(supplierinfo)
                if supplierinfo.partner_id == partner:
                    price_lines.extend(supplierinfo.pricelist_ids)
            
            self.x_four = bool(len(suppinfos) > 1) 
            self.x_price = bool(len(price_lines) > 1)
        else:
            self.x_four = False 
            self.x_price = False
            
            
    @api.one
    def _compute_supplier_info(self):
        """
            Fonction permettant de ramener le délai fournisseur du produit
        """
        product = self.product_id
        delay = 0
        # Si le produit n'est pas en achat libre on va récupérer le délai à partir du référencement fournisseur trouvé
        if not product.free_purchase:
            partner = self.purchase_order_id.partner_id
            supplierinfo = product.get_sinfo(partner_id=partner.id, property_ids=self.property_ids, state_dev=False)
            if supplierinfo:
                delay = supplierinfo.delivery_delay
                
        else:
            delay = product.free_supply_delay
        
        self.supplier_delay = delay
            
             
    def _search_color_line(self, operator, value):
        request = 'SELECT purchase_line_id FROM stock_move WHERE color_priority_need=%s ORDER BY id'%(value)
        self.env.cr.execute(request)
        res_ids = self.env.cr.fetchall()          
        return [('id', 'in', res_ids)]
    
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    # Ligne de commande
    purchase_line_color = fields.Integer(string='Color priority', default=0, required=False, compute='_compute_color_line', 
                                         store=False, search='_search_color_line')
    name = fields.Text(string='Description', required=True)
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase order', required=False, ondelete='cascade', select=True, auto_join=True)
    sequence = fields.Integer(string='Sequence', default=0, required=False)
    purchase_partner_id = fields.Many2one('res.partner', string='Partner', required=False, ondelete='restrict', 
                                      related='purchase_order_id.partner_id', store=True, readonly=True)
    purchase_state = fields.Selection('_purchase_state_get', string='State', related='purchase_order_id.state', store=True, readonly=True)
    purchase_type = fields.Selection('_purchase_type_get', string='Type', related='purchase_order_id.purchase_type', store=True, readonly=True)
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='restrict')
    sec_uom_qty = fields.Float(string='Quantity in purchase unity', default=0.0, digits=dp.get_precision('Product quantity'), required=True)
    uom_qty = fields.Float(string='Quantity in measure unit', default=0.0, digits=dp.get_precision('Product quantity'), required=True)
    uoi_qty = fields.Float(string='Quantity in price unity', default=0.0, digits=dp.get_precision('Product quantity'), required=True)
    price_unit = fields.Float(string='Price unit', default=0.0, digits=dp.get_precision('Product price'), required=True)
    sec_uom_id = fields.Many2one('product.uom', string='Purchases unity', required=True, ondelete='restrict')
    sec_uom_category_id = fields.Many2one('product.uom.category', string='Second uom category', required=False, ondelete='restrict')
    uom_id = fields.Many2one('product.uom', string='Measure unity', required=True, ondelete='restrict')
    uom_category_id = fields.Many2one('product.uom.category', string='Uom category', required=False, ondelete='restrict')
    uoi_id = fields.Many2one('product.uom', string='Price unity', required=True, ondelete='restrict')
    uoi_category_id = fields.Many2one('product.uom.category', string='Uoi category', required=False, ondelete='restrict')
    currency_id = fields.Many2one('res.currency', string='Currency', required=False, ondelete='restrict', related='purchase_order_id.currency_id', readonly=True, store=True)
    property_ids = fields.Many2many('purchase.property', string='Properties')
    taxes_ids = fields.Many2many('account.tax', 'purchase_account_tax_rel', 'purchase_order_id', 'tax_line_id', string='Taxes', 
                                 domain=[('parent_id', '=', False),('type_tax_use', '!=', 'sale')])
    section_id = fields.Many2one('purchase.order.line.section', string='Section', required=False, ondelete='restrict')
    supplier_product_name = fields.Char(string='Supplier product name', size=128, required=False)
    supplier_product_code = fields.Char(string='Supplier product code', size=128, required=False)
    expected_date = fields.Date(string='Expected date', required=True)
    confirmed_date = fields.Date(string='Confirmed date')
    x_four = fields.Boolean(string='X suppliers', default=False, compute='_compute_x_four_price', store=True)
    x_price = fields.Boolean(string='X prices', default=False, compute='_compute_x_four_price', store=True)
    factor = fields.Float(string='Factor', default=1, required=False)
    divisor = fields.Float(string='Divisor', default=1, required=False)
    source = fields.Char(string='Source', size=128, required=False)
    quantity = fields.Float(string='Quantity', default=0.0, required=False)
    limit_send_date = fields.Date(string='Limit send date', compute='_compute_limit_date', store=True)
    need_date = fields.Date(string='Need date')
    pol_ids = fields.One2many('purchase.order.line', compute='_compute_pol_ids')
    remaining_called_qty = fields.Float(string='Remaining quantity (opened order)', default=0.0, required=False, compute='_compute_remaining_called_order_qty')
    supplier_delay = fields.Integer(string='Supplier delay', compute='_compute_supplier_info')
    last_delivery_date = fields.Datetime()
    location_id = fields.Many2one('stock.location', string='Location', required=False, ondelete='restrict', help='Destination location of stock move generated by this order line')
    
    # Facturation
    invoice_line_ids = fields.One2many('account.invoice.line', 'purchase_order_line_id',  string='Invoices lines')
    
    # Notes
    order_printed_note = fields.Text(string='Product note printed on order')
    receipt_printed_note = fields.Text(string='Note printed on the receipt note')
    invoice_printed_note = fields.Text(string='Product note printed on the invoice')
    internal_note = fields.Text(string='Internal note')
    
    # Historique
    stock_move_ids = fields.One2many('stock.move', 'purchase_line_id',  string='Stock moves')
    
    # Informations supplémentaires
    guarantee = fields.Integer(string='Guarantee', default=0, required=False)
    guarantee_unity_id = fields.Many2one('product.uom', string='Guarantee unity', required=False, ondelete='restrict',
                                         domain=[('price_unit', '=', False)])
    total_price = fields.Float(string='Subtotal', default=0.0, required=False, compute='_compute_total_price', store=True)
    total_price_currency = fields.Float(string='Total price currency company', default=0.0, required=False, compute='_compute_price_with_currency', store=True)
    currency_rate = fields.Float(string='Currency rate', default=0.0, required=False, compute='_compute_price_with_currency', store=True, digits=(12,6))
    lateness = fields.Boolean(string='Lateness', default=False, compute='_compute_lateness', search='_search_lateness')
    purchase_order_date = fields.Datetime(string='Purchase order date', related='purchase_order_id.validation_date', store=True, readonly=True)
    purchaser_id = fields.Many2one('res.users', string='Purchase manager', required=False, ondelete='set null', 
                                   related='purchase_order_id.purchaser_id', store=True, readonly=True)
    company_id = fields.Many2one('res.company', string='Company', related='purchase_order_id.company_id', store=True, readonly=True)
    
    # Quantités reçues / À recevoir
    received_qty = fields.Float(string='Quantity received', default=0.0, required=False, digits=dp.get_precision('Product quantity'))
    to_received = fields.Float(string='To received', default=0.0, required=False)
    
    # Champs pour le search
    year = fields.Char(string='Year', size=4, compute='_compute_date', store=True)
    month = fields.Selection('_month_get', string='Month', compute='_compute_date', store=True)
    week_number = fields.Char(string='Week number', size=2, compute='_compute_date', store=True) 
    day = fields.Selection('_day_get', string='Day', compute='_compute_date', store=True)
    
    # Procurement
    procurement_order_ids = fields.One2many('procurement.order', 'pol_id',  string='Procurement orders')    
    procurement_deleted = fields.Boolean(default=False)
    can_be_del = fields.Boolean(string='Can be delete', default=False) # Champ utilisé pour savoir si les achats brouillons mergés sont supprimable lors de l'annulation d'un procurement
    
    # Date pour calendrier
    calendar_date = fields.Datetime(string='Calendar date')
    
    # Attente délai
    need_delay_validation = fields.Boolean(default=False, copy=False)
    waiting_delay = fields.Boolean(default=False, copy=False)
    
    # Attributs
    product_attribute_ids = fields.One2many('purchase.common.attribute', 'purchase_line_id',  string='Attributes', copy=True)
    
    
    def update_onchange_product_id_res(self, sinfo_rc):
        return {}
    
    
    def onchange_product_id(self, product_id, purchase_order, send_quantity=False, property_ids=False, force_qty=False):
        """
            Récupération des infos du produit et du supplierinfo
        """
        res = {}
        if isinstance(product_id, int):
            product_id = self.env['product.product'].browse(product_id)
            
        supplier = False
        fiscal_position = purchase_order.purchase_account_system_id
        res['product_attribute_ids'] = []
        supplier = False 
        if product_id:
            partner = purchase_order.partner_id
            taxes_list = fiscal_position and fiscal_position.map_tax(product_id.purchase_taxes_ids) or []
            res['taxes_ids'] = taxes_list
            res['internal_note'] = product_id.internal_note
            res['receipt_printed_note'] = product_id.receipt_transport_note
            res['invoice_printed_note'] = product_id.description_invoice
            res['name'] = product_id.with_context(lang=partner.lang).name
            res['guarantee'] = product_id.guarantee
            res['guarantee_unity_id'] = product_id.guarantee_unity_id.id
            if purchase_order.warehouse_id and purchase_order.warehouse_id.is_receipt_directly_storage:
                res['location_id'] = product_id.get_storage_location(purchase_order.warehouse_id.id).id
               
            # Produit en achat libre
            if product_id.free_purchase:
                res['order_printed_note'] = product_id.purchase_note
                res['supplier_delay'] = product_id.free_supply_delay
                # On récupère le multiple pour calculer la quantité minimum de produit
                if product_id.purchase_multiple_qty == 0:
                    multiple_qty = 1
                else:
                    multiple_qty = product_id.purchase_multiple_qty
                
                if not force_qty:
                    if send_quantity:
                        res['sec_uom_qty'] = roundingUp(send_quantity, multiple_qty)
                    else:
                        res['sec_uom_qty'] = roundingUp(product_id.purchase_min_qty, multiple_qty)
                        
                else:
                    res['sec_uom_qty'] = send_quantity
                    
            #Produit spécifique
            else:
                if not property_ids:
                    property_ids = self.property_ids.ids
                   
                supplier = product_id.get_sinfo(partner_id=purchase_order.partner_id.id, property_ids=property_ids, state_dev=False)
                if supplier:
                    #On récupère le multiple pour calculer la quantité minimum de produit
                    if supplier.multiple_qty == 0:
                        multiple_qty = 1
                    else:
                        multiple_qty = supplier.multiple_qty
                        
                    res['supplier_product_name'] = supplier.supp_product_name
                    res['supplier_product_code'] = supplier.supp_product_code
                    res['supplier_delay'] = supplier.delivery_delay
                    if not force_qty:
                        if send_quantity:
                            res['sec_uom_qty'] = roundingUp(send_quantity, multiple_qty)
                        else:
                            res['sec_uom_qty'] = roundingUp(supplier.min_qty, multiple_qty)
                            
                    else:
                        res['sec_uom_qty'] = send_quantity
                       
                    if product_id.purchase_note and supplier.purchase_note:
                        res['order_printed_note'] = '%s\n%s'%(product_id.purchase_note, supplier.purchase_note)
                    elif product_id.purchase_note:
                        res['order_printed_note'] = product_id.purchase_note
                    elif supplier.purchase_note:
                        res['order_printed_note'] = '%s'%(supplier.purchase_note)
                    else:
                        res['order_printed_note'] = product_id.purchase_note
                
                else:
                    res['sec_uom_qty'] = 0
            
            uoms = product_id.get_uoms(pinfo=supplier or False, partner=purchase_order.partner_id, type='in', property_ids=self.property_ids, with_factor=True)
            for k, v in uoms.iteritems():
                res[k] = v
            
            if res.get('sec_uom_id', False) and res.get('uom_id', False) and res.get('sec_uom_id', False) and res.get('uoi_id', False) and res.get('factor', False) and res.get('divisor', False):
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
                if attribute.is_visible and not attribute.is_readonly and not attribute.is_compute and not attribute.is_default_compute and attribute.purchase:
                    res['product_attribute_ids'].append([0, False, {
                                                    'sequence': attribute.sequence,
                                                    'product_common_attribute_id': attribute.id,
                                                    'value': attribute.default_value,
                                                                    }])
        else:
            res['sec_uom_qty'] = 0
            res['sec_uom_id'] = False
            res['uom_qty'] = 0
            res['uom_id'] = False
            res['uoi_qty'] = 0
            res['uoi_id'] = False
            res['price_unit'] = 0
            res['property_ids'] = False
            res['taxes_ids'] = []
            res['name'] = ''
            res['supplier_product_name'] = ''
            res['supplier_product_code'] = ''
            res['internal_note'] = ''
            res['receipt_printed_note'] = ''
            res['invoice_printed_note'] = ''
            res['guarantee'] = 0
            res['guarantee_unity_id'] = False
            res['order_printed_note'] = ''
        
        res.update(self.update_onchange_product_id_res(supplier))        
        return res
    

    @api.onchange('product_id')
    def _onchange_warning_product_id(self):
        """
            On vérifie qu'il y a bien un partenaire de saisi dans l'achat
        """
        res = {}
        if not self.purchase_order_id.partner_id:
            res['warning'] = {'title':_('Warning'), 'message':_('You must first select a supplier in the purchase order')}
            self.product_id = False
        
        return res
    
    
    @api.onchange('product_id', 'property_ids')
    def _onchange_product_id(self):
        """
            Au changement du produit, changement des UoM et du nom
        """
        res = {}
        old_sec_uom_qty = self.sec_uom_qty
        if self.product_id:
            if not self.product_id.state in ['lifeserie', 'endlife']:
                res['warning'] = {'title':_('Warning'), 'message':_('To be purchased, the product\'s state should be life serie or end life')}
                self.product_id = False
                
        res_value = self.onchange_product_id(self.product_id, self.purchase_order_id)
        for k,v in res_value.iteritems():
            self[k] = v
        
        if self.sec_uom_qty == old_sec_uom_qty:
            self.price_unit = self.product_id.get_price_purchase(
                self.purchase_order_id.partner_id, self.property_ids, currency_price_return=self.currency_id or False, 
                qty_uop=self.sec_uom_qty, uop=self.sec_uom_id, date=self.confirmed_date, type='price', 
                state_dev=False, with_uoi=self.uoi_id
            )
        
        return res
    
    @api.onchange('sec_uom_qty', 'sec_uom_id', 'property_ids')
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
                msg = {'title': _('Warning'), 'message': _('You must have Management unit and Purchase unit')}
                self.uom_qty = 0
                self.sec_uom_qty = 0
            
            if not self.product_id.free_purchase:
                supplier_info = self.product_id.get_sinfo(partner_id=self.purchase_order_id.partner_id.id, 
                                                          property_ids=self.property_ids, state_dev=False)
                if supplier_info:
                    if supplier_info.multiple_qty:
                        multiple_qty = uom_obj._compute_qty_obj(self.sec_uom_id, self.sec_uom_qty, supplier_info.uop_id)
                        if Decimal(str(multiple_qty)) % Decimal(str(supplier_info.multiple_qty)):
                            warning = True
                            msg = {'title': _('Warning'), 'message': _('The quantity is not a multiple of %f')%(supplier_info.multiple_qty)}
                    
                    if supplier_info.min_qty:
                        min_qty = uom_obj._compute_qty_obj(self.sec_uom_id, self.sec_uom_qty, supplier_info.uop_id)
                        if supplier_info.min_qty > min_qty:
                            warning = True
                            msg = {'title': _('Warning'), 'message': _('The quantity in purchase unit should be higher to the minimum quantity '
                                                                                    '(%.2f)')%(supplier_info.min_qty)}
                
                elif not supplier_info:
                    warning = True
                    msg = {'title': _('Warning'), 'message': _('There is no active referencing for this properties, this product'
                                                               ' and this supplier')}
                    self.product_id = False
                    #On vide tous les champs de la ligne
                    res_value = self.onchange_product_id(self.product_id, self.purchase_order_id)
                    for k,v in res_value.iteritems():
                        self[k] = v
                        
            else:
                if self.product_id.purchase_multiple_qty:
                    multiple_qty = uom_obj._compute_qty_obj(self.sec_uom_id, self.sec_uom_qty, self.product_id.uop_id)
                    if Decimal(str(multiple_qty)) % Decimal(str(self.product_id.purchase_multiple_qty)):
                        warning = True
                        msg = {'title': _('Warning'), 'message': _('The quantity is not a multiple of %f')%(self.product_id.purchase_multiple_qty)}
                
                if self.product_id.purchase_min_qty:
                    min_qty = uom_obj._compute_qty_obj(self.sec_uom_id, self.sec_uom_qty, self.product_id.uop_id)
                    if self.product_id.purchase_min_qty > min_qty:
                        warning = True
                        msg = {'title': _('Warning'), 'message': _('The quantity in purchase unit should be higher to the minimum quantity '
                                                                                    '(%.2f)')%(self.product_id.purchase_min_qty)}
            if self.currency_id:
                currency_rs = self.currency_id
            else:
                currency_rs = False
                
            self.price_unit = self.product_id.get_price_purchase(self.purchase_order_id.partner_id, self.property_ids, currency_price_return=currency_rs, 
                                                             qty_uop=self.sec_uom_qty, uop=self.sec_uom_id, date=self.confirmed_date, type='price', 
                                                             state_dev=False, with_uoi=self.uoi_id)
            
            for k, v in qtys.iteritems():
                self[k] = v
            
            if warning and with_warning:
                res['warning'] = msg
            
            if self.sec_uom_id:
                self.sec_uom_category_id = self.sec_uom_id.category_id.id
        
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
                res['warning'] = {'title': _('Warning'), 'message': _('You must have Management unit and Purchase unit')}
        
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
    
    
    @api.multi
    def action_change_date(self):
        """
            Fonction permettant d'appeler le wizard de modification de la date
        """
        for line in self:
            if line.purchase_order_id.state in ['done', 'cancel']:
                raise ValidationError(_('You cannot change the value of the date because the purchase is done '
                    'or cancelled'))
                 
            action_dict = get_form_view(self, 'purchase.action_replacement_confirmed_date')
            if action_dict and action_dict.get('id') and action_dict.get('type'):
                action = self.env[action_dict['type']].browse(action_dict['id'])
                action_struc = action.read()
                action_struc = action_struc[0]
                
            return action_struc
        
    
    @api.multi
    def show_purchase_line_stock_move(self):
        """
            Fonction qui cherche et retourne les mouvements de stock pour une ligne de d'achat
        """
        action_struc = {}
        action_dict = get_form_view(self, 'purchase.purchase_stock_move_action')
        if action_dict and action_dict.get('id') and action_dict.get('type'):
            action = self.env[action_dict['type']].browse(action_dict['id'])
            action_struc = action.read()
            action_struc[0]['context'] = {'purchase_line_ids': [self.id]}
            action_struc = action_struc[0]
              
        return action_struc
    
    
    @api.multi
    def show_purchase_line_invoice_line(self):
        """
            Fonction qui cherche et retourne les lignes de facture de la ligne d'achat
        """
        action_struc = {}
        action_dict = get_form_view(self, 'purchase.purchase_line_invoice_action')
        line_ids = [x.id for x in self.invoice_line_ids]
        if action_dict and action_dict.get('id') and action_dict.get('type'):
            action = self.env[action_dict['type']].browse(action_dict['id'])
            action_struc = action.read()
            action_struc[0]['context'] = {'invoice_ids': line_ids}
            action_struc = action_struc[0]
              
        return action_struc

        
    @api.multi
    def conf_delay_button(self):
        for pol in self.read(['confirmed_date', 'expected_date']):
            procurement_rs = self.env['procurement.order'].search([('pol_id', '=', pol['id'])])
            for proc in procurement_rs:
                action = self.env.ref('stock.act_confirm_date_wizard')
                if action:
                    action = action.read()[0]
                    action['context'] = {'default_pol_id': pol['id'], 
                                         'default_date': pol['confirmed_date'] or pol['expected_date']}

            return action
        
        
    def change_invoiced_amount(self, amount=0, add=False, inv_currency_rs=False, inv_date=False):
        """
            Fonction permettant d'ajouter ou d'enlever un montant au champ
            de montant de facture généré
            :type self: purchase.order.line
            :param amount: Le montant à ajouter ou à retirer
            :type amount: float
            :param add: Si on doit ajouter ou enlever le montant
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
        # On récupère la valeur initiale de la quantité facturée de l'achat
        purchase_order = self.purchase_order_id
        purchase_invoiced_amount = purchase_order.purchase_invoiced_amount
        if purchase_order.currency_id != inv_currency_rs:
            if inv_date:
                context2['date'] = inv_date
                
            amount = inv_currency_rs.with_context(context2).compute(amount, purchase_order.currency_id)
            
        if add:
            vals['purchase_invoiced_amount'] = purchase_invoiced_amount + amount
        else:
            vals['purchase_invoiced_amount'] = purchase_invoiced_amount - amount
            
        purchase_order.write(vals)
        return True
    
    
    def get_properties(self):
        if self.property_ids:
            res = ' / '.join(['%s: %s'%(x.category_id.name, x.name) for x in self.property_ids])
        else:
            res = ''
        
        return res
    
    
    @api.multi
    def open_source_procurement(self):
        """
            Fonction permettant d'afficher le procurement déclencheur
        """
        return self.env['procurement.order']._open_source_procurement([('pol_id', '=', self[0].id)])
    
    
    def do_action_on_line_cancel(self):
        return True
    
    
    @api.multi
    def compute_received_qty(self):
        """
            Fonction permettant de calculer les champs de quantités livrées, commandées
            et restantes des lignes d'achat
            :type self: purchase.order.line
            :rtype: Boolean
        """
        remaining_qty = 0
        received_qty = 0
        uom_id = self.uom_id.id
        product_id = self.product_id.id
        move_obj = self.env['stock.move']
        uom_obj = self.env['product.uom']
        move_datas = move_obj.search_group(fields=['uom_qty', 'uom_id', 'type', 'state', 'date'], 
                                 groupby=['product_id', 'uom_id', 'type', 'state'], 
                                 args=[('purchase_line_id', '=', self.id), ('product_id', '=', product_id)],
                                 sum='uom_qty',
                                 max='date',
                                 return_dict=True)
        dates = []
        for move_data in move_datas:
            if move_data['uom_id'] == uom_id:
                qty = move_data['uom_qty']
            else:
                qty = uom_obj._compute_qty(move_data['uom_id'], move_data['uom_qty'], to_uom_id=uom_id, with_raise=True, with_round=False)

            if move_data['type'] == 'in':
                # Si le move est done, on incrémente la quantité reçue
                if move_data['state'] == 'done':
                    received_qty += qty
                    dates.append(move_data['date'])
                    
                # Sinon, on incrémente la quantité restante
                elif move_data['state'] == 'waiting':
                    remaining_qty += qty
                    
            # Si le move est 'OUT' on va venir ajouter la quantité à la quantité restante
            elif move_data['type'] == 'out':
                # Si le move est done, on incrémente la quantité restante et on décrémente la quantité reçue
                if move_data['state'] == 'done':
                    received_qty -= qty
            
            
        self.write({'to_received': remaining_qty, 'received_qty': received_qty, 'last_delivery_date': dates and max(dates) or False})
        return True
    
    
    def move_other_data_subcontracting(self, move_other_data):
        """
            Fonction qui permet de rajouter des champs pour la création d'un mouvement lors dans de la validation de l'achat de soustraitance
            :param move_other_data: Un dico contenant les champs pour la création d'un mouvement lors de la validation d'un achat
            :type move_other_data: boolean
            :return: La lignee d'achat créée
            :rtype: recordset purchase.order.line
        """
        return move_other_data
        
    
    def create_purchase_order_line(self, purchase=False, product=None, values=None, first_qty=False, forced_qty=False, not_need_qty=False):
        """
            Création d'une ligne d'achat
            :type self: purchase.order.line
            :param purchase: L'achat lié à la ligne
            :type purchase: recordset: purchase.order
            :param product: Le produit de la ligne d'achat
            :type product: recordset product.product
            :param values: Les détails de la ligne d'achat (optionnel)
            :type values: dict {'uom_qty':..., 'price_unit':... }
            :param first_qty: Les détails de la ligne d'achat (optionnel), pour indiquer que l'on passe une qty en unité de gestion
            :type first_qty: value char 'uom_qty'
            :param forced_qty: True si on souhaite entrer une qté inférieure à la qté minimale
            :type forced_qty: boolean
            :param not_need_qty: True si on souhaite empêcher la ligne de prendre en compte la quantité du besoin
            :type not_need_qty: boolean
            :return: La lignee d'achat créée
            :rtype: recordset purchase.order.line
        """
        vals = {}
        if not values:
            values = {}
            
        uom_obj = self.env['product.uom']
        if purchase and product:
            multiple_qty = False
            property_ids = values.get('property_ids', False)
            if property_ids and isinstance(property_ids[0], tuple):
                property_ids = property_ids[0][-1]
                
            if isinstance(purchase, int):
                purchase = self.env['purchase.order'].browse(purchase)
            
            if isinstance(product, int):
                product = self.env['product.product'].browse(product)
                
            vals['purchase_order_id'] = purchase.id
            vals['product_id'] = product.id
            vals.update(utils.transform_to_ids(self, self.onchange_product_id(product, purchase, property_ids=property_ids)))
            # QUANTITÉS
            # Quantité en unité de gestion
            if first_qty == 'uom_qty':
                uom_obj = self.env['product.uom']
                if not_need_qty:
                    needed_qty = values.get('uom_qty', 0.0)
                else:
                    needed_qty = values.get('quantity', False) or values.get('uom_qty', 0.0)
                    
                if vals.get('uom_id') and values.get('uom_id') and vals['uom_id'] != values['uom_id']:
                    needed_qty = uom_obj._compute_qty(values['uom_id'], needed_qty, to_uom_id=vals['uom_id'], with_raise=True, with_round=False)
                    
                qtys = self.product_id.get_qtys(
                            needed_qty, 
                            uom_id=uom_obj.browse(vals.get('uom_id')), 
                            sec_uom_id=uom_obj.browse(vals.get('sec_uom_id')), 
                            uoi_id=uom_obj.browse(vals.get('uoi_id')),
                            by_field='uom', 
                            dual_unit=product.dual_unit, 
                            dual_unit_type=product.dual_unit_type, 
                            factor=vals.get('factor', 1), 
                            divisor=vals.get('divisor', 1), 
                            with_raise=True)
                
                needed_qty = qtys.get('sec_uom_qty', 0.0)
            # Quantité en unité d'achat
            else:
                if not_need_qty:
                    needed_qty = values.get('sec_uom_qty', 0.0)
                else:
                    needed_qty = values.get('quantity', False) or values.get('sec_uom_qty', 0.0)

                if vals.get('sec_uom_id') and values.get('sec_uom_id') and vals['sec_uom_id'] != values['sec_uom_id']:
                    needed_qty = uom_obj._compute_qty(values['sec_uom_id'], needed_qty, to_uom_id=vals['sec_uom_id'], with_raise=True, with_round=False)
            
            values['quantity'] = needed_qty 
            # Si quantité non forcée: prise en compte du mini et multiple
            if not forced_qty:
                # Achat libre
                if product.free_purchase:
                    # Mini
                    needed_qty = max(needed_qty, product.purchase_min_qty)
                    # Récupération multiple
                    multiple_qty = product.purchase_multiple_qty
                # Avec réferencement
                else:
                    supplier = product.get_sinfo(partner_id=purchase.partner_id.id, property_ids=property_ids, state_dev=False)
                    if supplier:
                        # Mini
                        needed_qty = max(needed_qty, supplier.min_qty)
                        # Récupération multiple
                        multiple_qty = supplier.multiple_qty
                
                # Application multiple
                if multiple_qty:
                    needed_qty = roundingUp(needed_qty, multiple_qty)
            
            values['sec_uom_qty'] = needed_qty
            
            # On récupère les valeurs "forcées"
            if values:
                vals.update(values)

            # Création de la ligne d'achat
            purchase_line = self.create(vals)
            # Lancement des onchanges de calcul des quantités et des unités
            purchase_line._onchange_sec_uom_qty(with_warning=False)
            purchase_line._onchange_uom_qty()
            purchase_line._onchange_uoi_qty()
                
            res = purchase_line
        else:
            res = False
        
        return res
        
    
    # Partie Soustraitance pour la création des réceptions des produits finis lors de la génération de picking pour la confirmation d'achat
    def create_move_pf_st(self, picking_rcs, currency_id, supplier_info):
        """
            Function pour la Soustraitance pour la création des réceptions des produits finis lors de la génération de picking pour la confirmation d'achat 
            :type self: purchase.order.line
            :param picking_rcs: Le Bon de réception
            :type picking_rcs: recordset: stock.picking
            :param currency_id: La Devise
            :type currency_id: recordset: res.currency
            :param supplier_info: Le supplier_info
            :type supplier_info: recordset: product.supplierinfo
            :return: True
        """
        return True
    
    
    def get_key_for_merge(self, field_list):
        """
            Création d'une clé pour identifier les lignes qui peuvent être mergées
            On entre ici que les champs qui n'ont pas à être identiques pour le merge
        """
        key = ''
        for field in self._fields.keys():
            if field not in field_list:
                #Dans le cas d'un O2M, on va récupérer les valeurs de chaque lignes
                #En excluant les champs tels que create_date ainsi que le champ inverse du O2M
                if isinstance(self._fields[field], fields.One2many):
                    cascade_read = self[field].read(load='_classic_write')
                    inverse_name = self._fields[field].inverse_name
                    for o2m_line in cascade_read:
                        for o2mfield, o2mvalue in o2m_line.iteritems():
                            if o2mfield not in field_list and o2mfield != inverse_name:
                                key += '%s'%(o2mvalue)
                                
                else:
                    key += '%s'%(self[field])
        
        return key
    
    
    def list_non_essential_fields(self):
        """
            Permet de faire la liste des champs qui n'empêchent pas le merge des lignes
            si différents
        """
        field_list = ['expected_date', 'need_date', 'quantity', 'sec_uom_qty', 'order_printed_note', 'receipt_printed_note',
                      'invoice_printed_note', 'internal_note', 'source', 'uom_qty', 'uoi_qty', 'sec_uom_id', 'uom_id', 'uoi_id',
                      'uom_category_id', 'sec_uom_category_id', 'uoi_category_id', 'id', 'purchase_order_id', 'create_date', 
                      'write_date', 'create_uid', 'write_uid', 'pol_ids', 'procurement_order_ids', 'currency_rate', 'purchase_line_color',
                      'total_price_currency', '__last_update', 'remaining_called_qty', 'display_name', 'day', 'total_price', 
                      'limit_send_date', 'week_number', 'month', 'year', 'sequence', 'calendar_date', 'price_unit', 'lateness']
        return field_list
    
    
    @api.multi
    def change_purchase_line_info(self):
        """
            Fonction qui appelle le wizard de modification des informations des lignes d'achat
            à condition qu'aucune facture liée à l'achat ne soit validé
        """
        action_struc = {}
        action_dict = get_form_view(self, 'purchase.action_change_purchase_line_information')
        invoice_rs = [x.invoice_id for x in self.invoice_line_ids]
        invoice_rs = list(set(invoice_rs))
        for invoice in invoice_rs:
            if invoice.state != 'draft':
                raise ValidationError(_('You can\'t change the accounting information because there is already a '
                                      'validated invoice linked to the sale'))
                
        if action_dict and action_dict.get('id') and action_dict.get('type'):
            action = self.env[action_dict['type']].browse(action_dict['id'])
            action_struc = action.read()
            action_struc[0]['context'] = {'purchase_line_id': self.id}
            action_struc = action_struc[0]
              
        return action_struc
    
    
    @api.multi
    def create_merge_lines(self, procurement_list, data):
        """
            Fonction permettant de merger plusieurs lignes d'achats en une seule
            On parcourt toutes les lignes passées et on crée un dictionnaire contenant les valeurs
            des nouvelles lignes
            :type self: purchase.order.line
            :param procurement_list: Liste des id des lignes qui possèdent un procurement à la demande
            :type list: liste d'id
            :param procurement_list: Liste des id des lignes qui possèdent un procurement à la demande
            :type list: liste d'id
            :return: le dictionnaire de lignes à merger et la liste des lignes dont le procurement est à la demande
        """
        product_uom_obj = self.env['product.uom']
        procurement_obj = self.env['procurement.order']
        make_to_order_ids = self.env['purchase.order.line']
        #Liste des champs qui n'ont pas besoin d'être les mêmes pour que les lignes
        #soient mergées
        field_list = self.list_non_essential_fields()
        #On parcourt les lignes des achats
        for line in self:
            #On récupère les ids des lignes dont le procurement est à la demande
            if line.id in procurement_list:
                make_to_order_ids += line
            else:
                #On crée une clé afin d'identifier les lignes d'achat identiques
                key = line.get_key_for_merge(field_list)
                line_key = (line.product_id, tuple(line.property_ids.ids))
                #Si la clé de la ligne ne fait pas encore parti de la liste de clés récupérées,
                #on l'ajoute à la liste
                if not data.get(key):
                    data[key] = {line_key: {'procurement': []}}
                    #On recherche le procurement associé
                    procurement_rs = procurement_obj.search([('pol_id', '=', line.id)])
                    for procurement in procurement_rs:
                        data[key][line_key]['procurement'].append(procurement)
                        #Si le procurement a la case 'prendre en compte achat brouillon' de cochée, on le récupère
                        if procurement.consider_purchase:
                            data[key][line_key]['procurement_consider_purchase'] = procurement
                        
                    #On récupère les informations de la ligne
                    for field in line._fields.keys():
                        cascade_field = False
                        if field not in ['id', 'purchase_order_id', 'create_date', 'write_date', 'create_uid', 'write_uid', 'price_unit']:
                            if isinstance(line._fields[field], fields.Many2one):
                                data[key][line_key][field] = line[field].id
                            elif isinstance(line._fields[field], fields.Many2many):
                                data[key][line_key][field] = [(6,0, [x.id for x in line[field]])]
                            elif isinstance(line._fields[field], fields.One2many):
                                #Gestion des One2many dont l'inverse_name est en ondelete cascade
                                inverse_obj = line._fields[field].comodel_name
                                inverse_name = line._fields[field].inverse_name
                                if inverse_obj and inverse_name:
                                    ondelete = self.env[inverse_obj]._fields[inverse_name].ondelete
                                    if ondelete == 'cascade':
                                        cascade_field = True
                                        
                                if cascade_field:
                                    #On récupère la valeur de chaque champ
                                    cascade_read = line[field].read(load='_classic_write')
                                    #On supprime les champs non désirés des dictionnaires du read
                                    field_list = ['create_date', 'write_uid', 'create_uid', '__last_update', 'write_date', inverse_name]
                                    for o2m_line in cascade_read:
                                        for o2m_field in field_list:
                                            if o2m_field in o2m_line.keys():
                                                del o2m_line[o2m_field]
                                                
                                    if cascade_read:
                                        data[key][line_key][field] = [(0, 0, x_vals) for x_vals in cascade_read]
                                else:
                                    data[key][line_key][field] = [(4, x.id) for x in line[field]]
                            else:
                                data[key][line_key][field] = line[field]
                    
                    if 'quantity' not in data[key][line_key] or not data[key][line_key]['quantity']:
                        data[key][line_key]['quantity'] = data[key][line_key]['sec_uom_qty']
                    
                else:
                    #On recherche le procurement associé
                    procurement_rs = procurement_obj.search([('pol_id', '=', line.id)])
                    for procurement in procurement_rs:
                        data[key][line_key]['procurement'].append(procurement)
                        #Si le procurement a la case 'prendre en compte achat brouillon' de cochée, on le récupère
                        if procurement.consider_purchase:
                            data[key][line_key]['procurement_consider_purchase'] = procurement
                            
                    #Récupération des dates, on prend la date minimum entre toutes celles entrées
                    if data[key][line_key]['expected_date'] > line.expected_date:
                        data[key][line_key]['expected_date'] = line.expected_date
                    
                    if data[key][line_key]['need_date'] > line.need_date:
                        data[key][line_key]['need_date'] = line.need_date
                    
                    #Récupération de la quantité du besoin
                    data[key][line_key]['quantity'] += line.quantity or product_uom_obj._compute_qty(data[key][line_key]['sec_uom_id'], 
                                                                                                line.sec_uom_qty, 
                                                                                                line.sec_uom_id.id, 
                                                                                                with_raise=True)
                    
                    #Calcul de la quantité en unité d'achat (conversion entre les deux unités)
                    # (qty du besoin1 + qty du besoin2)
                    # si pas de besoin QtyT= (qty du achat1 + qty du achat2)
                    data[key][line_key]['sec_uom_qty'] = data[key][line_key]['quantity']
                    
                    #Récupération des notes. S'il y en a déjà, on les concatène ensemble
                    if data[key][line_key]['order_printed_note'] and line.order_printed_note:
                        data[key][line_key]['order_printed_note'] = '%s \n --- \n%s'%(data[key][line_key]['order_printed_note'], 
                                                                                                 line.order_printed_note)
                    elif line.order_printed_note:
                        data[key][line_key]['order_printed_note'] = line.receipt_printed_note
                    
                    if data[key][line_key]['receipt_printed_note'] and line.receipt_printed_note:
                        data[key][line_key]['receipt_printed_note'] = '%s \n --- \n%s'%(data[key][line_key]['receipt_printed_note'],
                                                                                                   line.receipt_printed_note)
                    elif line.receipt_printed_note:
                        data[key][line_key]['receipt_printed_note'] = line.receipt_printed_note
                        
                    if data[key][line_key]['invoice_printed_note'] and line.invoice_printed_note:
                        data[key][line_key]['invoice_printed_note'] = '%s \n --- \n%s'%(data[key][line_key]['invoice_printed_note'],
                                                                                                   line.invoice_printed_note)
                    elif line.invoice_printed_note:
                        data[key][line_key]['invoice_printed_note'] = line.invoice_printed_note
                    
                    if data[key][line_key]['internal_note'] and line.internal_note:
                        data[key][line_key]['internal_note'] = '%s \n --- \n%s'%(data[key][line_key]['internal_note'],
                                                                                            line.internal_note)
                    elif line.internal_note:
                        data[key][line_key]['internal_note'] = line.internal_note
                        
                    if data[key][line_key]['source'] and line.source:
                        data[key][line_key]['source'] = '%s / %s'%(data[key][line_key]['source'],
                                                                            line.source)
                    elif line.source:
                        data[key][line_key]['source'] = line.source
                    
                    # point d'entrée pour surcharge
                    self.merge_line_other_actions(data[key][line_key], line)
                
                line.unlink()
                
        return data, make_to_order_ids
    
    # point d'entrée pour surcharge
    @api.model
    def merge_line_other_actions(self, merge_line, line):
        pass
    
    @api.multi
    def do_merge_lines(self):
        """
            Fonction permettant de merger plusieurs lignes achats en une seule
            Les commandes d'achats peuvent uniquement être mergées si:
            - Elles sont en brouillon
            - Elles concernent le même fournisseur
            - Elles ont la même devise
        """
        first_purchase = False
        make_to_order_ids = self.env['purchase.order.line']
        pol_ids = self.env['purchase.order.line']
        purchase_to_del = self.env['purchase.order']
        procurement_obj = self.env['procurement.order']
        purchases_list = {}
        purchase_list_to_del_rcs = self.env['purchase.order']
        data = {}
        for line in self:
            purchase_order = line.purchase_order_id
            if not purchase_order in purchases_list:
                purchases_list[purchase_order] = line
            else:
                purchases_list[purchase_order] += line
                 
        for purchase, list_lines in purchases_list.iteritems():
            pol_list = []
            if purchase.state != 'draft':
                raise except_orm(_("Error"), _('The purchase %s is not in draft')%(purchase.name))
            
            #On récupère les ids des lignes dont le procurement est à la demande
            procurement_search = procurement_obj.search([('trigger_supply', '=', 'make_to_order'), 
                                                        ('pol_id', 'in', list_lines.ids)])
            if procurement_search:
                pol_list = [procurement.pol_id.id for procurement in procurement_search if procurement.pol_id]
                
            #Variable permettant de repérer le premier passage
            first_try = False
            #On récupère le premier achat, c'est celui qui va nous servir de référence
            if not first_purchase:
                first_purchase = purchase
                first_try = True
            
            #Si ce n'est pas le premier passage dans la boucle, on vérifie que les achats puissent
            #être mergés
            if not first_try:
                merge, purchase_info = first_purchase.check_merge(purchase)
                if not merge:
                    raise except_orm(_("Error"), _('The purchase with %s has not the same value for the field "%s"'
                                          ' than the purchase reference (%s)')%(purchase_info[0], purchase_info[1], first_purchase.name))
            
            data, list_make_to_order_ids = list_lines.create_merge_lines(pol_list, data)
            make_to_order_ids += list_make_to_order_ids
            #Si l'achat est vide après la suppression de la ligne, on supprime également l'achat 
            #(sauf s'il s'agit du premier achat)
            if not purchase.purchase_order_line_ids and purchase != first_purchase:
                purchase_to_del += purchase
            else:
                purchase_list_to_del_rcs += purchase
            
        if first_purchase:
            if data:
                for product_list in data.values():
                    for product_line, values in product_list.iteritems():
                        if values.get('procurement_consider_purchase'):
                            del values['procurement_consider_purchase']
                            not_need = True
                        else:
                            if values.get('quantity'):
                                values['sec_uom_qty'] = values['quantity']
                            
                            not_need = False
                            
                        if values.get('procurement'):
                            procurement_list = values.get('procurement', [])
                            del values['procurement']
                        else:
                            procurement_list = []
                            
                        product = product_line[0]
                        po_line_id = pol_ids.create_purchase_order_line(purchase=first_purchase, 
                                                                        product=product, values=values,
                                                                        first_qty=False, forced_qty=False, 
                                                                        not_need_qty=not_need)
                        #Boucle car liste de procurements
                        for proc in procurement_list:
                            proc.write({'pol_id': po_line_id.id})
                
            # On assigne toutes les lignes d'achat dont le procurement est à la demande au premier achat
            make_to_order_ids.write({'purchase_order_id': first_purchase.id})
            for purchase_list_to_del in purchase_list_to_del_rcs:
                if not purchase_list_to_del.purchase_order_line_ids:
                    purchase_list_to_del.unlink()
                    
            purchase_to_del.unlink()
            first_purchase._onchange_purchase_order_line_ids()
            action_struc = get_form_view(self, 'purchase.purchase_order_see_form', first_purchase.id)
            return action_struc
        else:
            return  {'type': 'ir.actions.act_window_close'}
    
    
    @api.multi
    def unlink(self):
        """
            On supprime le move cancel lié à la ligne d'achat, et le BR s'il n'avait que ce move
        """
        context = self.env.context
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
            
            #On recherche l'id de l'action à partir de laquelle on supprime l'achat
            action = self.env.ref('purchase.action_purchase_order_line')
            if context.get('params'):
                if action and action.id == context['params'].get('action'):
                    purchase = line.purchase_order_id
                    if len(purchase.purchase_order_line_ids) == 1:
                        res = super(purchase_order_line, self).unlink()
                        purchase.unlink()
                        return res
        
        return super(purchase_order_line, self).unlink()
    
    
    @api.model
    def create(self, vals):
        """
            A la création de la ligne, on attribut la valeur de la date de création
            à la date du calendrier
        """
        purchase_line = super(purchase_order_line, self).create(vals)
        purchase_line.write({'calendar_date': purchase_line.create_date})
        return purchase_line
    
    
    @api.multi
    def copy(self, default=None):
        """
            On vide les champs de quantités livrées et facturées
        """
        if not default:
            default = {}
        
        new_default = {
                       'received_qty' : 0,
                       'to_received' : 0,
                       }
        default.update(new_default)
        return super(purchase_order_line, self).copy(default=default)
    


class purchase_order(models.Model):
    """ 
    Purchase order
    """
    _name = 'purchase.order'
    _inherit = 'workflow.base'
    _description = 'Purchase order'
    _order = 'id desc'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    @api.model
    def _purchase_type_get(self):
        return [
                ('prototype', _('Prototype')),
                ('series', _('Series')),
                ('call', _('Called order')),
                ('open', _('Open order')),
                       ]
    
    @api.one
    @api.depends('purchase_order_line_ids.total_price', 'tax_line_ids.amount')
    def _compute_taxes_amount(self):
        self.amount_ex_taxes = sum(line.total_price for line in self.purchase_order_line_ids)
        self.taxes = sum(line.amount for line in self.tax_line_ids)
        self.total_amount = self.amount_ex_taxes + self.taxes
    
    
    # START TO DELETE #    
    @api.model
    def _purchase_account_invoice_trigger_get(self):
        return [
            ('picking', _('To the delivery')),
            ('manual', _('On demand')),
            ('postpaid', _('On the order')),
        ]
    

    @api.model
    def _purchase_account_invoiced_on_get(self):
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
    def _purchase_invoice_postage_get(self):
        return [
                ('never', _('Never')),
                ('always', _('Always')),
                ('threshold', _('< Threshold')),
                       ]
        
        
    @api.model
    def _purchase_communication_method_get(self):
        return [
                ('fax', _('Fax')),
                ('email', _('Email')),
                       ]
    
    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('waiting', _('Waiting')),
                ('progress', _('In progress')),
                ('done', _('Done')),
                ('cancel', _('Cancelled')),
                       ]
    
    
    @api.one   
    @api.depends('purchase_order_line_ids')
    def _compute_invoice_line_ids(self):
        """
            On récupère toutes les lignes de factures liées aux lignes d'achat
        """
        invoice_line_list = []
        for line in self.purchase_order_line_ids:
            invoice_line_list.extend([x.id for x in line.invoice_line_ids])

        self.invoice_line_ids = invoice_line_list
    
    
    @api.one
    @api.depends('purchase_contact_ids', 'purchase_communication_method', 'partner_id')
    def _compute_purchase_communication_value(self):
        if self.partner_id:
            self.purchase_communication_value = self.env['res.partner'].calcul_value_com(self.purchase_contact_ids, 
                                                                                     self.partner_id, self.purchase_communication_method)
        else:
            self.purchase_communication_value = ''
    
    
    @api.one
    @api.depends('purchase_order_line_ids', 'purchase_order_line_ids.expected_date', 'purchase_order_line_ids.stock_move_ids')
    def _compute_expected_date(self):
        """
            Calcul de la date prévue
            On parcourt les moves des lignes d'achat et on prend la date maximum de ces moves
            Si les lignes n'ont pas de move, on prend la date demandée maximum dans la ligne d'achat
        """
        if self.purchase_order_line_ids:
            list_date = []
            for line in self.purchase_order_line_ids:
                if line.stock_move_ids:
                    for move in line.stock_move_ids:
                        list_date.append(move.date_expected)
                elif line.expected_date:
                    list_date.append(line.expected_date)
                        
            if list_date:            
                self.expected_date = max(list_date)
                    
        else:
            self.expected_date = False

    
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
        if self.purchase_order_line_ids:
            anticipated_invoice_list = []
            #On recherche les factures anticipées liées à l'achat
            account_line_obj = self.env['account.invoice.line']
            advanced_invoice_lines = account_line_obj.search([('purchase_order_line_id', 'in', self.purchase_order_line_ids.ids),
                                                              ('invoice_id.anticipated', '=', True)])
            if advanced_invoice_lines:
                advanced_invoice = True
                for line in advanced_invoice_lines:
                    if not line.invoice_id in anticipated_invoice_list:
                        total_amount += line.invoice_id.amount_total
                        total_without_tax += line.invoice_id.amount_untaxed
                        anticipated_invoice_list.append(line.invoice_id)
            
            #On cherche les éventuelles lignes de facture négatives liées à l'achat
            invoiced_amount_lines = account_line_obj.search([('purchase_order_line_id', 'in', self.purchase_order_line_ids.ids),
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
    @api.depends('picking_ids.state', 'picking_ids.move_ids')
    def _compute_received_amount(self):
        received_amount = 0
        for picking in self.picking_ids:
            if picking.state == 'done':
                received_amount += sum(move.uoi_qty * move.partner_price for move in picking.move_ids)
                
        self.received_amount = received_amount
        
        
    @api.one
    @api.depends('received_amount', 'total_amount', 'state', 'invoicing_method_id')
    def _compute_residual_amount(self):
        residual_amount = 0
        if self.state == 'progress':
            if self.purchase_invoice_balance_invoiced_on == 'order':
                residual_amount = self.amount_ex_taxes - self.purchase_invoiced_amount
            elif self.purchase_invoice_balance_invoiced_on == 'delivery':
                residual_amount = self.received_amount - self.purchase_invoiced_amount
                
        self.residual_amount = residual_amount
    
    
    @api.one
    @api.depends('payment_ids')
    def _compute_see_paid(self):
        """
            Permet de savoir s'il y a un paiement non annulé lié à l'achat
        """
        check_paid = False
        for payment in self.payment_ids:
            if payment.state != 'cancel':
                check_paid = True
                break
             
        self.see_paid_button = check_paid
    
    
    @api.one
    @api.depends('purchase_invoice_postage', 'purchase_threshold', 'purchase_incoterm_id', 'total_amount')
    def _compute_show_caution(self):
        """
            Permet de savoir s'il faut afficher ou non la phrase de warning des frais de transport
        """
        show_caution = False
        if self.purchase_invoice_postage != 'never' and self.purchase_incoterm_id.id != 1:
            if (self.purchase_invoice_postage == 'threshold' and self.purchase_threshold >= self.total_amount) or (self.purchase_invoice_postage == 'always'): 
                show_caution = True
             
        self.show_caution = show_caution
        
        
    @api.one
    @api.depends('invoicing_method_id')
    def _compute_block_paymen_term(self):
        self.block_picking_payment = False
        self.block_purchase_payment = False
        self.need_picking_payment = False
        self.need_purchase_payment = False
        if self.id:
            self.env.cr.execute("""
            SELECT  
              DISTINCT impl.payment_type, true as blocking
            FROM
              purchase_order s
              JOIN account_invoicing_method im ON s.invoicing_method_id = im.id
              JOIN account_invoicing_method_payment_line impl ON im.id = impl.invoicing_method_id
            WHERE
              s.id = %s AND
              impl.is_blocking
            
            UNION ALL
              
            SELECT  
                DISTINCT impl.payment_type, false as blocking
            FROM
              purchase_order s
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
                        self.need_purchase_payment = True
                        if query_res_item['blocking']:
                            self.block_purchase_payment = True
                
                
    @api.one
    @api.depends('invoicing_method_id')
    def _compute_purchase_invoice_balance(self):
        self.purchase_invoice_balance_trigger = False
        self.purchase_invoice_balance_invoiced_on = False
        if self.id:
            self.env.cr.execute("""
                SELECT
                  iml.invoice_trigger,
                  iml.account_invoiced_on
                FROM
                  purchase_order s
                  JOIN account_invoicing_method im ON s.invoicing_method_id = im.id
                  JOIN account_invoicing_method_line iml ON im.id = iml.invoicing_method_id
                WHERE
                  s.id = %s
                  AND iml.value = 'balance'
                LIMIT 1
                """%(self.id))
            
            query_res = self.env.cr.dictfetchone()
            if query_res:
                self.purchase_invoice_balance_trigger = query_res['invoice_trigger']
                self.purchase_invoice_balance_invoiced_on = query_res['account_invoiced_on']
            
        
    @api.one
    @api.depends('invoicing_method_id')
    def _compute_purchase_invoice_trigger(self):
        self.purchase_invoice_trigger_postpaid = False
        self.purchase_invoice_trigger_manual = False
        self.purchase_invoice_trigger_picking = False
        if self.id:
            self.env.cr.execute("""
            SELECT
              iml.invoice_trigger
            FROM
              purchase_order s
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
                        self.purchase_invoice_trigger_postpaid = True
                    elif query_res_item['invoice_trigger'] == 'manual':
                        self.purchase_invoice_trigger_manual = True
                    elif query_res_item['invoice_trigger'] == 'picking':
                        self.purchase_invoice_trigger_picking = True
    
            
    #===========================================================================
    # COLUMNS
    #===========================================================================
    # En-tête
    name = fields.Char(required=True, string='Order reference', default='/', readonly=True, copy=False)
    state = fields.Selection('_state_get', string='State', default='draft')
    partner_id = fields.Many2one('res.partner', string='Supplier', required=True, ondelete='restrict', select=True)
    ref_order = fields.Char(string='Supplier order reference', size=32, required=False, help="Our order reference for the supplier")
    default_expected_date = fields.Date(string='Default expected date')
    expected_date = fields.Date(string='Expected date', compute='_compute_expected_date', store=False)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, ondelete='restrict')
    purchase_type = fields.Selection('_purchase_type_get', string='Type', required=True, default='series')
    open_order_id = fields.Many2one('purchase.order', string='Open order', required=False, ondelete='restrict')
    address_id = fields.Many2one('address', string='Address', required=True, ondelete='set null')
    purchaser_id = fields.Many2one('res.users', string='Purchaser', required=False, ondelete='restrict')
    source_document = fields.Char(string='Source document', size=64, required=False)
    show_invoice_button = fields.Boolean(string='Show invoice button', default=True, copy=False)
    reminder_ok = fields.Boolean(string='Reminder done', default=False, readonly=True)
    
    # Références
    purchase_order_line_ids = fields.One2many('purchase.order.line', 'purchase_order_id',  string='Purchase order line', copy=False)
    amount_ex_taxes = fields.Float(string='Amount excluding taxes', default=0.0, required=False, compute='_compute_taxes_amount')
    taxes = fields.Float(string='taxes', default=0.0, required=False, compute='_compute_taxes_amount')
    total_amount = fields.Float(string='Total', default=0.0, required=False, compute='_compute_taxes_amount')
    received_amount = fields.Float(string='Received amount', default=0.0, required=False, compute='_compute_received_amount')
    residual_amount = fields.Float(string='Residual', default=0.0, required=False, compute='_compute_residual_amount')
    max_sequence = fields.Integer(string='Sequence max', default=10, required=False)
    tax_line_ids = fields.One2many('account.purchase.tax', 'purchase_id',  string='Taxes update', copy=True)
    
    # Adresse
    invoiced_by_id = fields.Many2one('res.partner', string='Invoiced by', required=True, ondelete='restrict')
    delivered_by_id = fields.Many2one('res.partner', string='Delivered by', required=True, ondelete='restrict')
    invoiced_address_id = fields.Many2one('address', string='Invoicing address', required=True, ondelete='restrict')
    paid_to_id = fields.Many2one('res.partner', string='Paid to', required=True, ondelete='restrict')
    location_id = fields.Many2one('stock.location', string='Location', required=True, ondelete='restrict',
                                  default=lambda self:self.env.user.company_id.warehouse_id.input_location_id)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True, ondelete='restrict',
                                  default=lambda self:self.env.user.company_id.warehouse_id)
    delivered_supplier_id = fields.Many2one('res.partner', string='Delivered partner', required=True, ondelete='restrict',
                                            default=lambda self:self.env.user.company_id.partner_id.id, 
                                            domain=['&', '&',('state', 'not in', ['prospect', 'stopped']), ('is_company', '=', True), 
                                                    '|', ('is_supplier', '=', True),
                                                    '&', ('can_be_delivered', '=', True), ('is_customer', '=', True)])
    delivered_name = fields.Char(string='Name', size=32, required=True)
    delivered_street = fields.Char(string='Street', size=32, required=False)
    delivered_street2 = fields.Char(string='Street 2', size=32, required=False)
    delivered_street3 = fields.Char(string='Street 3', size=32, required=False)
    delivered_zip = fields.Char(string='Zip', size=24, required=False)
    delivered_city = fields.Char(string='City', size=32, required=False)
    delivered_region_id = fields.Many2one('res.region', string='Region', required=False, ondelete='restrict')
    delivered_country_id = fields.Many2one('res.country', string='Country', required=True, ondelete='restrict')
    delivered_address_id = fields.Many2one('address', string='Delivered address', required=True, ondelete='restrict')
    
    # Comptabilité
    payment_id = fields.Many2one('payment.method', string='Payment', ondelete='restrict')
    payment_term_id = fields.Many2one('account.payment.term', string='Payment term', required=True, ondelete='restrict')
    block_picking = fields.Boolean(string='Block receipt', default=False, copy=False, help="Check if you want to block manually " "the picking. You will have to unlock manually the picking.")
    see_paid_button = fields.Boolean(string='See paid button', default=False, copy=False, compute='_compute_see_paid', store=True)
    discount = fields.Boolean(string='Discount', default=False)
    discount_value = fields.Float(string='Discount value in percentage', default=0.0, required=False)
    max_delay = fields.Integer(string='Maximal delay applicated', default=0, required=False)
    purchase_account_system_id = fields.Many2one('account.fiscal.position', string='Account system', required=True, ondelete='restrict')
    
    invoicing_method_id = fields.Many2one('account.invoicing.method', string='Invoicing method', required=True, ondelete='restrict', help='Comes from the supplier who invoicing the order')
    manual_hide_invoice_button = fields.Boolean(default=False, copy=False)
    check_paid = fields.Boolean(string='Paid', default=False, copy=False)
    need_purchase_payment = fields.Boolean(compute='_compute_block_paymen_term')
    block_purchase_payment = fields.Boolean(compute='_compute_block_paymen_term')
    block_picking_payment = fields.Boolean(compute='_compute_block_paymen_term')
    need_picking_payment = fields.Boolean(compute='_compute_block_paymen_term')
    # Facturation
    purchase_invoice_balance_invoiced_on = fields.Char(compute='_compute_purchase_invoice_balance')
    purchase_invoice_balance_trigger = fields.Char(compute='_compute_purchase_invoice_balance')
    purchase_invoice_trigger_manual = fields.Boolean(compute='_compute_purchase_invoice_trigger')
    purchase_invoice_trigger_picking = fields.Boolean(compute='_compute_purchase_invoice_trigger')
    purchase_invoice_trigger_postpaid = fields.Boolean(compute='_compute_purchase_invoice_trigger')

    # START TO DELETE #
    payment_type = fields.Selection('_payment_type_get', string='Payment type', required=False, default='after_invoicing', related='payment_term_id.payment_type', store=False, readonly=True)
    check_paid_invoice = fields.Boolean(string='Paid invoice', default=False, copy=False)
    check_paid_purchase = fields.Boolean(string='Paid purchase', default=False, copy=False)
    purchase_account_invoice_trigger = fields.Selection('_purchase_account_invoice_trigger_get', string='Invoicing method trigger', required=False)
    purchase_account_invoiced_on = fields.Selection('_purchase_account_invoiced_on_get', string='Invoiced on', required=False, help='This field '
                                                ' indicates if the invoice on the basis of quantities actually delivered or on the basis'
                                                ' of quantities ordered (can be useful in case of flat rate, for example)')
    # END TO DELETE #
    
    # Delivery
    show_caution = fields.Boolean(compute='_compute_show_caution', string='Show caution', store=False)
    purchase_incoterm_id = fields.Many2one('stock.incoterms', string='Incoterm', required=False, ondelete='restrict', help='Incoterm which '
                                       'stands for \'International Commercial terms\' implies its a series of purchases terms which are used '
                                       'in the commercial transaction.')
    purchase_invoice_postage = fields.Selection('_purchase_invoice_postage_get', string='Invoice postage', required=False)
    purchase_threshold = fields.Float(string='Threshold', default=0.0, required=False)
    purchase_forwarding_agent_id = fields.Many2one('res.partner', string='Forwarding Agent', required=False, ondelete='restrict', 
                                               domain=[('is_company', '=', True)])
    receipt_note_and_date = fields.Boolean(string='Make picking for each receipt date', default=False)
    partial_purchase_delivery = fields.Boolean(string='Partial receipt', default=False)
    generate_purchase_rest = fields.Boolean(string='Generate purchase rest', default=False)

    # Historique
    company_id = fields.Many2one('res.company', string='Company', required=False, ondelete='restrict', readonly=True, 
                                 default=lambda self:self.env.user.company_id)
    invoice_line_ids = fields.One2many('account.invoice.line', compute='_compute_invoice_line_ids')
    picking_ids = fields.One2many('stock.picking', 'purchase_id',  string='Picking')
    advanced_invoice = fields.Boolean(string='Has an advanced invoice', default=False, compute='_compute_advanced_amount', 
                                      store=False)
    advanced_amount = fields.Float(string='Advanced invoice amount', default=0.0, required=False, 
                                   compute='_compute_advanced_amount', store=False)
    advanced_amount_without_tax = fields.Float(string='Advanced invoice amount without taxes', default=0.0, required=False, 
                                   compute='_compute_advanced_amount', store=False)
    remaining_advanced_amount = fields.Float(string='Remaining advanced invoice amount', default=0.0, required=False,
                                             compute='_compute_advanced_amount', store=False)
    
    # Communication
    receipt_demand_date = fields.Date(string='Receipt demand', readonly=True, copy=False)
    receipt_demand_user_id = fields.Many2one('res.users', string='User', required=False, ondelete='restrict', readonly=True, copy=False)
    quotation_date = fields.Date(string='Quotation date', readonly=True, copy=False)
    quotation_user_id = fields.Many2one('res.users', string='User', required=False, ondelete='restrict', copy=False)
    creation_date = fields.Datetime(string='Creation date', required=False)
    confirmation_date = fields.Datetime(string='Confirmation date', readonly=True, copy=False)
    confirmation_user_id = fields.Many2one('res.users', string='User', required=False, ondelete='restrict', copy=False)
    validation_date = fields.Datetime(string='Validation date', readonly=True, copy=False)
    validation_user_id = fields.Many2one('res.users', string='User', required=False, ondelete='restrict', copy=False)
    purchase_communication_method = fields.Selection('_purchase_communication_method_get', string='Communication method')
    purchase_contact_ids = fields.Many2many('res.partner', 'purchase_contact_id_purchase_rel', 'purchase_order_id', 'contact_id', 
                                            string='Contacts', help='If you choose a contact, the communication value will refer to its coordinates')
    #Champ conservé pour la reprise des données, à supprimer plus tard
    purchase_contact_id = fields.Many2one('res.partner', string='Contact', required=False, ondelete='restrict', help='If you choose a contact, '
                                      'the communication value will refer to its coordinates')
    purchase_communication_value = fields.Char(string='Communication value', compute='_compute_purchase_communication_value')
    receipt_demand_flag = fields.Boolean(string='Request RD', default=False)
    supplier_reminder = fields.Boolean(string='Supplier reminder', default=False)
    mail_ids = fields.One2many('mail.mail', 'purchase_id',  string='Mails', readonly=True)
    
    # Commandes appellées
    called_order_ids = fields.One2many('purchase.order', 'open_order_id', string='Called orders', readonly=True)
    
    # Notes
    inter_note = fields.Text(string='Intern note / Preparation note')
    invoice_note = fields.Html(string='Invoice note')
    delivery_note = fields.Html(string='Note printed on delivery note')
    supplier_note = fields.Html(string='Supplier note')
    
    # Montant facturé
    purchase_invoiced_amount = fields.Float(string='Invoiced amount', default=0.0, required=False, digits=dp.get_precision('Product price'), readonly=True, copy=False)

    # Procurement
    procurement_deleted = fields.Boolean(string='Procurement order deleted', default=False)
    
    #Paiements
    payment_ids = fields.One2many('account.voucher', 'purchase_id',  string='Payments', help="The automatic payments linked to the purchase")
    
    
#     @api.one
#     @api.constrains('purchase_account_invoice_trigger', 'purchase_account_invoiced_on', 'payment_type')
#     def _check_purchase_invoiced_on(self):
#         """
#             Vérifie que le déclenchement de la facturation soit cohérent avec le type de facturation
#         """
#         #On vérifie que le mode de déclenchement est à la livraison si la facturation est sur les quantités livrées
#         if self.purchase_account_invoiced_on == 'delivery' and self.purchase_account_invoice_trigger  not in ['picking', 'manual']:
#             raise Warning(_('Error ! You cannot have an invoice in the receipted quantities if the invoice trigger is not on the '
#                             'picking (accounting tab)'))
#              
#         if self.purchase_account_invoiced_on == 'order':
#             if self.payment_type in ['before_validation', 'before_delivery'] and self.purchase_account_invoice_trigger not in ['postpaid', 'manual']:
#                 raise Warning(_('Error ! You cannot have an invoice in the ordered quantities if the invoice trigger is not in the order or manual'))

    
    @api.one
    @api.constrains('state', 'block_purchase_payment')    
    def _check_blocked_purchase_order(self):
        """
            Verifie que l'achat ne puisse pas être validé si il est bloqué
        """
        if self.block_purchase_payment and self.state in ('progress', 'done') and not self.check_paid:
            raise Warning(_('Error ! You cannot validate a blocked purchase due to payment'))
        
        
    @api.one
    @api.constrains('partial_purchase_delivery', 'generate_purchase_rest')    
    def _check_partial_delivery(self):
        """
            Verifie que le booléen de génération de reliquat soit bien décoché si celui
            de livraison incomplète l'es aussi 
        """
        if self.generate_purchase_rest and not self.partial_purchase_delivery:
            raise Warning(_('Error ! You cannot generate rest if you don\'t accept partial delivery'))
            
        return True
    
    
    @api.one
    @api.constrains('purchase_type', 'purchase_order_line_ids', 'open_order_id')    
    def _check_called_order(self):
        """
            Dans le cas d'une commande appelée, vérifie que les produits de l'achat sont les mêmes
            que ceux de la commande ouverte attachée. Il peut y avoir moins de produits mais pas
            plus.
        """
        diff_list = False
        if self.purchase_type == 'call' and self.open_order_id:
            open_list_ids = []
            call_list_ids = []
            #On récupère les ids des produits de la commande ouverte
            for open_line in self.open_order_id.purchase_order_line_ids:
                open_list_ids.append(open_line.product_id.id)
             
            #On récupère les ids des produits de l'achat actuel
            for line in self.purchase_order_line_ids:
                call_list_ids.append(line.product_id.id)
            
            if call_list_ids and open_list_ids:
                diff_list = set(call_list_ids) - set(open_list_ids)
            
            if diff_list:
                raise Warning(_('Error ! You cannot have products in your purchase that are not present in the opened order'))
             
        return True
    
    
    @api.onchange('location_id')
    def _onchange_location_id(self):
        self.warehouse_id = self.location_id.warehouse_id

        
    @api.onchange('warehouse_id')
    def _onchange_warehouse_id(self):
        self.location_id = self.warehouse_id.input_location_id


#     @api.onchange('purchase_account_invoiced_on', 'payment_type')
#     def _onchange_purchase_account_invoiced_on(self):
#         """
#             On modifie la méthode de déclenchement de facturation en fonction du type de paiement
#             et du type de facturation (qtés livrées ou commandées)
#         """
#         if self.purchase_account_invoiced_on == 'delivery':
#             self.purchase_account_invoice_trigger = 'picking'
#         elif self.purchase_account_invoiced_on == 'order' and self.payment_type != 'after_invoicing' and self.purchase_account_invoice_trigger != 'manual':
#             self.purchase_account_invoice_trigger = 'postpaid'
            
    
#     @api.onchange('purchase_account_invoice_trigger')
#     def _onchange_purchase_account_invoice_trigger(self):
#         """
#             Si on passe le mode de déclenchement en manuel ou à la commande, on sélectionne la facturation sur 
#             quantités commandées
#             Si on passe le mode de déclenchement à la livraison, on sélectionne la facturation sur 
#             quantités livrées
#         """
#         if self.purchase_account_invoice_trigger in ['manual','postpaid']:
#             self.purchase_account_invoiced_on = 'order'
#         elif self.purchase_account_invoice_trigger == 'picking' and self.payment_type != 'after_invoicing':
#             self.purchase_account_invoiced_on = 'delivery'
    

    def onchange_purchase_order_line_ids(self, from_real_onchange=True):
        # Récupération de la séquence
        res = {}
        seq_list = []
        for line in self.purchase_order_line_ids:
            seq_list.append(line.sequence)
        
        max_sequence = max(seq_list or [0])
        res['max_sequence'] = max_sequence + 10
        #Calcul des taxes
        taxes_grouped = self.get_taxes_values()
        tax_lines = self.env['account.purchase.tax']
        tax_line_obj = self.env['account.purchase.tax']
        for tax in taxes_grouped.values():
            if from_real_onchange:
                tax_lines += tax_line_obj.new(tax)
            else:
                tax_lines += tax_line_obj.create(tax)
        
        if from_real_onchange:    
            res['tax_line_ids'] = tax_lines
        else:
            res['tax_line_ids'] = [(6, 0, tax_lines.ids)]
        
        return res
        
    
    @api.onchange('purchase_order_line_ids')
    def _onchange_purchase_order_line_ids(self):
        """
            On stocke la valeur de la plus haute séquence afin d'envoyer par défaut la bonne séquence 
            aux lignes d'achat
            On calcule les taxes des lignes
        """
        for k, v in self.onchange_purchase_order_line_ids().iteritems():
            self[k] = v
            
    
    def onchange_purchase_supplier(self, partner):
        """
            Récupération des infos du fournisseur
        """
        res = {}
        partner_obj = self.env['res.partner']
        if isinstance(partner, int):
            partner = partner_obj.browse(partner)
        
        if partner:
            #On récupère les informations du fournisseur
            res['currency_id'] = partner.currency_id.id
            res['receipt_demand_flag'] = partner.purchase_receipt_demand
            res['supplier_reminder'] = partner.supplier_reminder
            res['address_id'] = partner.address_id.id
            res['purchase_account_system_id'] = partner.supplier_account_position_id.id
            res['purchase_contact_ids'] = [(4, contact_id) for contact_id in partner.purchase_contact_ids.ids]
            res['invoicing_method_id'] = partner.purchase_invoicing_method_id.id
            if partner.purchase_communication_method in ['fax', 'email']:
                res['purchase_communication_method'] = partner.purchase_communication_method
            else:
                res['purchase_communication_method'] = False
            
            infos = {'purchase_delivery': True, 'purchase_paid': True, 'purchase_invoiced': True}
            info_dict = partner.get_partner_address(infos, return_id=True)
            if isinstance(info_dict, dict):
                #On récupère les partenaires livreurs, payés et factureurs
                res['delivered_by_id'] = info_dict.get('purchase_delivery_partner', partner.id)
                res['invoiced_by_id'] = info_dict.get('purchase_invoiced_partner', partner.id)
                res['paid_to_id'] = info_dict.get('purchase_pay_partner', partner.id)
                res['invoiced_address_id'] = info_dict.get('purchase_invoiced_address', partner.address_id.id)
                
            res['supplier_note'] = partner.note_purchase_header
            res['delivery_note'] = partner.note_receipt_order
            res['invoice_note'] = partner.sale_invoice_note
            res['inter_note'] = partner.internal_note
            res['payment_id'] = partner.purchase_payment_method_id.id
            res['payment_term_id'] = partner.property_supplier_payment_term_id.id
            res['discount'] = partner.purchase_discount_management
            res['discount_value'] = partner.purchase_discount_value
            res['max_delay'] = partner.purchase_max_delay
            res['partial_purchase_delivery'] = partner.partial_purchase_delivery
            res['generate_purchase_rest'] = partner.generate_purchase_rest
            res['purchaser_id'] = partner.purchaser_id.id
            res.update(partner.get_purchase_transport_fields(return_id=True))
        else:
            res['currency_id'] = False
            res['purchase_account_system_id'] = False
            res['purchase_contact_id'] = [(5)]
            res['purchase_communication_method'] = False
            res['supplier_note'] = ''
            res['delivery_note'] = ''
            res['invoice_note'] = ''
            res['inter_note'] = ''
            res['payment_id'] = False
            res['payment_term_id'] = False
            res['discount'] = False
            res['discount_value'] = 0
            res['max_delay'] = 0
            res['invoicing_method_id'] = False
            res.update(partner_obj.get_purchase_transport_fields(return_id=True))
        
        return res
    
    
    @api.onchange('partner_id')
    def _onchange_purchase_supplier(self):
        """
            Au changement de fournisseur, on va récupérer toutes les informations le concernant:
            les notes de sa fiche, les méthodes de communications, les infos de livraison...
        """
        partner = self.partner_id
        if partner:
            if partner.state != 'qualified':
                self.partner_id = False
                res2 = {'warning': {}}
                res2['warning'] = {'title': _('Warning'), 'message': _('The selected partner is not qualified to order, his state '
                                                                      'must be "qualified"')}
                return res2
            
            res = self.onchange_purchase_supplier(partner)
            for k,v in res.iteritems():
                self[k] = v
            
            
    def onchange_delivered_supplier(self, delivered_supplier):
        """
            Récupération des infos du partner livré
        """
        res = {}
        if isinstance(delivered_supplier, int):
            delivered_supplier = self.env['res.partner'].browse(delivered_supplier)
        
        if delivered_supplier:
            res['delivered_address_id'] = delivered_supplier.address_id.id
        else:
            res['delivered_address_id'] = False
        
        return res
        
    
    @api.onchange('delivered_supplier_id', 'partner_id')
    def _onchange_delivered_supplier(self):
        """
            Au changement du livré, on récupère son adresse principale
        """
        res = self.onchange_delivered_supplier(self.delivered_supplier_id)
        for k,v in res.iteritems():
            self[k] = v
    

    def onchange_invoiced_by_id(self, invoiced_by_supplier):
        """
            Récupération des infos du client facturé
        """
        res = {}
        res_partner_obj = self.env['res.partner']
        if isinstance(invoiced_by_supplier, int):
            invoiced_by_supplier = res_partner_obj.browse(invoiced_by_supplier)
        
        if invoiced_by_supplier and invoiced_by_supplier.is_company:
            res['invoicing_method_id'] = invoiced_by_supplier.purchase_invoicing_method_id.id
        else:
            res['invoicing_method_id'] = False
        
        return res
    
    
    @api.onchange('invoiced_by_id')
    def _onchange_invoiced_by_id(self):
        """
            Warnings et récupérations d'informations du fournisseur factureur
        """
        res = {}
        if self.invoiced_by_id:
            if self.invoiced_by_id.state != 'qualified':
                res['warning'] = {'title': _('Warning'), 'message': _('The selected supplier who made the invoice is not qualified, '
                                                                      'his state must be "qualified"')}
                self.invoiced_by_id = False
                self.invoiced_address_id = False
                self.invoicing_method_id = False
                return res
            
            partner_verif = self.env['res.partner.purchase.type'].search([('partner_type', '=', 'invoiced_by'), 
                                                                 ('partner_type_id', '=', self.invoiced_by_id.id),
                                                                 ('partner_id', '=', self.partner_id.id)], limit=1)
            if not partner_verif and self.invoiced_by_id != self.partner_id:
                res['warning'] = {'title': _('Warning'), 'message': _('The selected supplier who made the invoice is not linked to the partner'
                                                                      ' of the purchase')}
                self.invoiced_by_id = False
                self.invoiced_address_id = False
                self.invoicing_method_id = False
                return res
            
            invoiced_supplier = self.invoiced_by_id
            res2 = self.onchange_invoiced_by_id(invoiced_supplier)
            for k,v in res2.iteritems():
                self[k] = v
        
        return res


    def onchange_delivered_address_id(self, delivered_address):
        """
            Récupération des infos de l'adresse de livraison
        """
        res = {}
        if isinstance(delivered_address, int):
            delivered_address = self.env['address'].browse(delivered_address)
        
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
    
    
    def onchange_delivered_by_supplier_id(self, delivery_supplier, delivery_info=False):
        """
            Récupération des infos du client livreur
        """
        res = {}
        res_partner_obj = self.env['res.partner']
        if isinstance(delivery_supplier, int):
            delivery_supplier = res_partner_obj.browse(delivery_supplier)
            
        if delivery_supplier and delivery_supplier.is_company and delivery_supplier.is_supplier:
                res.update(delivery_supplier.get_purchase_transport_fields(return_id=True))
                res['purchase_account_system_id'] = delivery_supplier.supplier_account_position_id.id
        else:
            res['purchase_account_system_id'] = False
            res.update(res_partner_obj.get_purchase_transport_fields(return_id=True))
        
        return res
    
    
    @api.onchange('delivered_by_id')
    def _onchange_delivered_by_supplier_id(self):
        """
            Warnings et récupérations d'informations du fournisseur livreur
        """
        res = {}
        if self.delivered_by_id:
            if self.delivered_by_id.state != 'qualified':
                res['warning'] = {'title': _('Warning'), 'message': _('The selected delivery supplier is not qualified '
                                                                      'his state must be "qualified"')}
                self.purchase_account_system_id = False
                self.delivered_by_id = False
                self.purchase_incoterm_id = False
                self.purchase_invoice_postage = False
                self.purchase_threshold = False
                self.purchase_forwarding_agent_id = False
                return res
            
            partner_verif = self.env['res.partner.purchase.type'].search([('partner_type', '=', 'delivered_by'), 
                                                                 ('partner_type_id', '=', self.delivered_by_id.id),
                                                                 ('partner_id', '=', self.partner_id.id)], limit=1)
            if not partner_verif and self.delivered_by_id != self.partner_id:
                res['warning'] = {'title': _('Warning'), 'message': _('The selected delivery supplier is not in the delivery list of the partner'
                                                                      ' who orders')}
                self.purchase_account_system_id = False
                self.delivered_by_id = False
                self.purchase_incoterm_id = False
                self.purchase_invoice_postage = False
                self.purchase_threshold = False
                self.purchase_forwarding_agent_id = False
                return res
            
            delivery_supplier = self.delivered_by_id
            res2 = self.onchange_delivered_by_supplier_id(delivery_supplier)
            for k,v in res2.iteritems():
                self[k] = v
        
        return res
    
    
    def onchange_paid_to_id(self, paid_to_supplier):
        """
            Récupération des infos du fournisseur payé
        """
        res = {}
        if isinstance(paid_to_supplier, int):
            paid_to_supplier = self.env['res.partner'].browse(paid_to_supplier)
        
        if paid_to_supplier and paid_to_supplier.is_company and paid_to_supplier.is_supplier:
            res['payment_id'] = paid_to_supplier.purchase_payment_method_id.id
            
            res['payment_term_id'] = paid_to_supplier.property_supplier_payment_term_id.id
            res['discount'] = paid_to_supplier.purchase_discount_management
            res['discount_value'] = paid_to_supplier.purchase_discount_value
            res['max_delay'] = paid_to_supplier.purchase_max_delay
        else:
            res['payment_id'] = False
            res['payment_term_id'] = False
            res['discount'] = False
            res['discount_value'] = 0
            res['max_delay'] = 0
        
        return res
            
    
    @api.onchange('paid_to_id')
    def _onchange_paid_to_id(self):
        """
            Warnings et récupérations d'informations du fournisseur payé
        """
        res = {}
        if self.paid_to_id:
            if self.paid_to_id.state != 'qualified':
                res['warning'] = {'title': _('Warning'), 'message': _('The supplier selected to be paid is not qualified, '
                                                                      'his state must be "qualified"')}
                self.paid_to_id = False
                self.payment_id = False
                self.payment_term_id = False
                self.discount = False
                self.discount_value = 0
                self.max_delay = 0
                return res
            
            partner_verif = self.env['res.partner.purchase.type'].search([('partner_type', '=', 'paid_to'), 
                                                                 ('partner_type_id', '=', self.paid_to_id.id),
                                                                 ('partner_id', '=', self.partner_id.id)], limit=1)
            if not partner_verif and self.paid_to_id != self.partner_id:
                res['warning'] = {'title': _('Warning'), 'message': _('The supplier selected to be paid is not in the '
                                                                      'paid list of the partner who orders')}
                self.paid_to_id = False
                self.payment_id = False
                self.payment_term_id = False
                self.discount = False
                self.discount_value = 0
                self.max_delay = 0
                return res
            
            res2 = self.onchange_paid_to_id(self.paid_to_id)
            for k,v in res2.iteritems():
                self[k] = v
        
        return res
    
    
    @api.onchange('delivered_address_id')
    def _onchange_delivered_address_id(self):
        """
            Au changement d'adresse de livraison, on récupère tous les détails de l'adresse
        """
        res = self.onchange_delivered_address_id(self.delivered_address_id)
        for k,v in res.iteritems():
            self[k] = v
    
    
    @api.onchange('delivered_country_id')
    def _onchange_delivered_country_id(self):
        """
            Si on change de pays, on vide le champ de la région
        """
        if self.delivered_country_id != self.delivered_region_id.country_id:
            self.delivered_region_id = False
    
    
    @api.multi
    def purchase_change_account_system(self):
        """
            Fonction qui appelle le wizard de modification du régime fiscal
            à condition qu'aucune facture liée à l'achat ne soit validée
        """
        action_struc = {}
        action_dict = get_form_view(self, 'purchase.action_purchase_change_account_system')
        invoice_rs = [x.invoice_id for x in self.invoice_line_ids]
        invoice_rs = list(set(invoice_rs))
        for invoice in invoice_rs:
            if invoice.state != 'draft':
                raise ValidationError(_('You can\'t change the accounting system because there is already a '
                                      'validated invoice linked to the purchase'))
                
        if action_dict and action_dict.get('id') and action_dict.get('type'):
            action = self.env[action_dict['type']].browse(action_dict['id'])
            action_struc = action.read()
            action_struc[0]['context'] = {'purchase_id': self.id}
            action_struc = action_struc[0]
              
        return action_struc
    
    
    @api.multi
    def change_purchase_note(self):
        """
            Fonction qui appelle le wizard de modification des notes
            à condition qu'aucune facture liée à l'achat ne soit validée
        """
        action_struc = {}
        action_dict = get_form_view(self, 'purchase.action_purchase_change_note')
        invoice_rs = [x.invoice_id for x in self.invoice_line_ids]
        invoice_rs = list(set(invoice_rs))
        for invoice in invoice_rs:
            if invoice.state != 'draft':
                raise ValidationError(_('You can\'t change the accounting information because there is already a '
                                      'validated invoice linked to the purchase'))
                
        if action_dict and action_dict.get('id') and action_dict.get('type'):
            action = self.env[action_dict['type']].browse(action_dict['id'])
            action_struc = action.read()
            action_struc[0]['context'] = {'purchase_id': self.id}
            action_struc = action_struc[0]
              
        return action_struc
    
    
    @api.one
    def action_generate_payment(self):
        return self.generate_payment('before_validation')
    
    
    @api.one
    def generate_payment(self, payment_type):
        """
            Fonction permettant de créer le paiement lié à l'achat
        """
        # S'il n'y a pas de lignes d'achat envoie d'un message d'erreur
        if not self.purchase_order_line_ids:
            raise ValidationError(_('There is no lines on your purchase!'))
            
        # Récupération de toutes les valeurs du paiement
        journal_obj = self.env['account.journal']
        payment_rate = 1
        today = fields.Date.today()
        period_rs = self.env['account.period'].find(today)
        currency_rs = self.currency_id or False
        # Récupération du journal par défaut du paiement. S'il n'y en a pas: premier trouvé
        journal_rs = journal_obj.search([('is_default', '=', True), ('type', 'in', ['cash', 'bank'])], limit=1)
        if not journal_rs:
            journal_rs = journal_obj.search([('type', 'in', ['cash', 'bank'])], limit=1)
        
        payment_rate_currency_rs = journal_rs and journal_rs.currency or currency_rs
        if journal_rs and period_rs and currency_rs:
            currency_rate = currency_rs.rate
            if currency_rate != 0:
                payment_rate = payment_rate_currency_rs.rate / currency_rate
            
            total_amount = self.invoicing_method_id.get_total_amount('payment', payment_type, self.total_amount)
            if payment_rate_currency_rs != currency_rs:
                total_amount = currency_rs.compute(total_amount, payment_rate_currency_rs)
            else:
                total_amount = total_amount
            
            account_partner_id = self.partner_id.property_account_payable_id and self.partner_id.property_account_payable_id.id or False
            vals = {'partner_id': self.partner_id.id,
                    'account_partner_id': account_partner_id,
                    'amount': total_amount,
                    'journal_id': journal_rs.id,
                    'date': today,
                    'name': self.name,
                    'period_id': period_rs.id,
                    'payment_rate_currency_id': payment_rate_currency_rs.id,
                    'company_id': self.company_id.id,
                    'payment_rate': payment_rate,
                    'payment_option': 'without_writeoff',
                    'currency_id': currency_rs.id,
                    'account_id': journal_rs.default_debit_account_id.id,
                    'purchase_id': self.id,
                    'type': 'payment'}
            
            self.env['account.voucher'].create(vals)
            
        return True
    
    
    def change_invoice_button_display(self, display=True):
        """
            Fonction permettant de cacher le bouton de génération de facture
        """
        self.write({'manual_hide_invoice_button': not bool(display)})


    @api.multi
    def generate_invoice_button(self):
        return self.generate_invoice(invoice_trigger='manual')
    
    
    @api.one
    def generate_invoice(self, invoice_trigger=False):
        """
            Fonction permettant de créer la facture liée à l'achat
        """
        if self.purchase_order_line_ids:
            context2 = {'force_invoice_price': True}
            context2.update(self.env.context)
            company = self.company_id or self.env.context.get('company_id', self.env.user.company_id) 
            domain = [
                ('type', 'in', filter(None, map(TYPE2JOURNAL.get, ['in_invoice']))),
                ('company_id', '=', company.id),
            ]
            journal = self.env['account.journal'].search(domain, limit=1)
            invoice_line_obj = self.env['account.invoice.line']
            invoice_obj = self.env['account.invoice']
            payment_term_id = self.payment_term_id.id
            if invoice_trigger:
                balance = (invoice_trigger == self.purchase_invoice_balance_trigger)
                invoicing_method_line_rs = self.env['account.invoicing.method.line'].search([('invoice_trigger', '=', invoice_trigger), 
                                                                                             ('invoicing_method_id', '=', self.invoicing_method_id.id)], limit=1)
                if invoicing_method_line_rs and invoicing_method_line_rs.payment_term_id:
                    payment_term_id = invoicing_method_line_rs.payment_term_id.id
                    
            else:
                balance = True
            
            # Desactivation du bouton de facturation manuelle si on lance une facture balance ou la facturation manuelle
            if balance or invoice_trigger == 'manual':
                self.write({'show_invoice_button': False})
                
            if journal:
                other_data = {'fiscal_position_id': self.purchase_account_system_id.id,
                              'currency_id': self.currency_id.id,
                              'company_id': company.id,
                              'delivery_partner_id': self.delivered_by_id.id,
                              'partner_order_id': self.partner_id.id,
                              'address_id': self.delivered_address_id.id,
                              'note_invoice_intern': self.inter_note,
                              'note_invoice_header': self.invoice_note,
                              'payment_term_id': self.payment_term_id.id,
                              'discount_management': self.discount,
                              'discount_value': self.discount_value,
                              'max_delay': self.max_delay,
                              'payment_method_id': self.payment_id.id,
                              'payment_term_id': payment_term_id,
                              'invoice_trigger': invoice_trigger,
                              'auto_anticipated': not balance,
                              'paid_by_id': self.paid_to_id.id,
                              'journal_id': journal.id,
                              'origin': self.name_get()[0][1]}
                invoice_id = self.env['account.invoice'].create_invoice(self.invoiced_by_id, self.invoiced_by_id.address_id, 'in_invoice', other_data)
                # Gestion de la facturation des lignes d'achat
                # Gestion des facture anticipées en pourcentage
                invoicing_method_percentage = self.invoicing_method_id.get_invoice_percentage(invoice_trigger)
                if invoicing_method_percentage:
                    for line in self.purchase_order_line_ids:
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
                                      'purchase_section_id': line.section_id.id,
                                      'customer_product_name': line.supplier_product_name,
                                      'customer_product_code': line.supplier_product_code,
                                      'purchase_order_line_id': line.id,
                                      'note_invoice_header': line.invoice_printed_note}
                        invoice_line_obj.with_context(context2).create_invoice_line(invoice_id.id, line.product_id, True, other_data)
                    
                # Gestion des facture anticipées en montant fixe
                if self.purchase_order_line_ids:
                    other_data = {'purchase_order_line_id': self.purchase_order_line_ids[0].id} 
                else:
                    other_data = None
                    
                for fixed_amount, product_id in self.invoicing_method_id.get_invoice_fixed_amount(invoice_trigger):
                    invoice_line_obj.with_context(context2).create_invoice_line(invoice_id.id, product_id, from_invoice=True, other_data=other_data, forced_price_unit=fixed_amount, forced_uoi_qty=1.0)
                
                invoice_id._onchange_invoice_line_ids()
            # Gestion des factures anticipées
            if self.remaining_advanced_amount:
                invoice_obj.generate_anticipated_invoice_line('purchase', invoice_id, self.remaining_advanced_amount, self)
                
            # 2ème boucle car doit etre lancé apres generate_anticipated_invoice_line
            for line in self.purchase_order_line_ids:
                if balance:
                    invoice_obj.generate_auto_anticipated_invoice_line('purchase', invoice_id, line)
                    
        else:
            raise ValidationError(_('You can\'t create an invoice if there is no lines in your purchase'))
        
        return True
    
    
    @api.one
    def action_generate_picking(self):
        """
            Fonction permettant de générer un picking et des moves
        """
        move_obj = self.env['stock.move']
        picking_obj = self.env['stock.picking']
        proc_obj = self.env['procurement.order']
        # Récuperation des valeurs de base de la vente
        picking_id = False
        # État de facturation
        if self.purchase_invoice_trigger_picking:
            state = '2binvoiced'
        else:
            state = 'none'

        # Type du picking
        move_and_picking_type = self.env.context.get('force_purchase_picking_type', 'in')
#         if self.block_picking_payment or self.block_picking:
#             payment_lock = True
#         else:
#             payment_lock = False
            
        currency_id = self.currency_id.id    
        other_data = {'purchase_id': self.id,
                      'is_partial': self.partial_purchase_delivery,
                      'manage_scrap': self.generate_purchase_rest,
                      'internal_note': self.inter_note,
                      'printed_note': self.delivery_note,
                      'invoice_state': state,
                      'origin': self.source_document,
                      'incoterm_id': self.purchase_incoterm_id.id,
                      'forwarding_agent_id': self.purchase_forwarding_agent_id.id,
                      'threshold': self.purchase_threshold,
                      'invoice_postage': self.purchase_invoice_postage,
                      'address_name': self.delivered_name,
                      'street': self.delivered_street,
                      'street2': self.delivered_street2,
                      'street3': self.delivered_street3,
                      'zip': self.delivered_zip,
                      'city': self.delivered_city,
                      'region_id': self.delivered_region_id and self.delivered_region_id.id or False,
                      'country_id': self.delivered_country_id.id,
                      'address_id': self.delivered_address_id.id,
                      'payment_lock': (self.block_picking_payment and not self.check_paid),
                      'lock': self.block_picking}
        # Si la case 'Faire autant de BR que de date de livraison' n'est pas cochée, création d'un picking et des moves associés aux lignes d'achats
        if not self.receipt_note_and_date:
            picking_id = picking_obj.create_picking(type=move_and_picking_type, partner=self.delivered_by_id, 
                                                     product_qty_uom={}, other_data=other_data)
            for line in self.purchase_order_line_ids:
                if (line.product_id.type != 'service') or (line.product_id.type == 'service' and \
                                                           line.product_id.manage_service_receipt):
                    supplier_info = line.product_id.get_sinfo(partner_id=line.purchase_order_id.partner_id.id,
                                                               property_ids=line.property_ids.ids, state_dev=False)
                    if line.confirmed_date:
                        date = line.confirmed_date
                    else:
                        date = line.expected_date
                        
                    move_other_data = {'sequence': line.sequence,
                                       'purchase_line_id': line.id,
                                       'name': line.name,
                                       'uom_id': line.uom_id.id,
                                       'sec_uom_qty': line.sec_uom_qty,
                                       'sec_uom_id': line.sec_uom_id.id,
                                       'uoi_qty': line.uoi_qty,
                                       'uoi_id': line.uoi_id.id,
                                       'date_expected': line.confirmed_date,
                                       'date': line.confirmed_date,
                                       'priority_date': line.confirmed_date,
                                       'initial_uom_qty': line.uom_qty,
                                       'note': line.internal_note,
                                       'partner_price': line.price_unit,
                                       'currency_id': currency_id,
                                       'factor': line.factor,
                                       'divisor': line.divisor,
                                       'sinfo_id': supplier_info and supplier_info.id or False,
                                       'date_expected': date,
                                       'date': date,
                                       'priority_date': date,
                                       'origin': line.name_get()[0][1],
                                       'note': line.receipt_printed_note}
                    
                    proc_rs = proc_obj.search([('pol_id', '=', line.id), ('state', '!=', 'cancel')], limit=1)
                    if proc_rs:
                        move_other_data['procurement_id'] = proc_rs.id
                        move_other_data['reserved_qty'] = proc_rs.uom_qty
                        move_other_data['trigger_supply'] = proc_rs.trigger_supply
                    
                    if line.product_id.type == 'service' and line.product_id.manage_service_receipt:
                        if not self.warehouse_id.service_location_id:
                            raise ValidationError('There is no service location in your company')
                         
                        move_other_data['location_dest_id'] = self.warehouse_id.service_location_id.id
                    
                    move_other_data = line.move_other_data_subcontracting(move_other_data)
                    if move_and_picking_type == 'out':
                        src_location = False
                        dst_location = self.warehouse_id.supplier_location_id.id
                    else:
                        dst_location = line.location_id and line.location_id.id or \
                                       line.purchase_order_id and line.purchase_order_id.location_id and line.purchase_order_id.location_id.id or \
                                       False
                        #Si le partenaire a un emplacement fournisseur défini on récupère celui-ci sinon on récupère l'emplacement fournisseur de l'entrepôt la société
                        if line.purchase_order_id.delivered_by_id and line.purchase_order_id.delivered_by_id.supplier_location_id:
                            src_location = line.purchase_order_id.delivered_by_id.supplier_location_id.id
                        else:
                            src_location = self.warehouse_id.supplier_location_id and self.warehouse_id.supplier_location_id.id or False
                        
                    move_obj.create_move(line.product_id, qty=line.uom_qty, type=move_and_picking_type, other_data=move_other_data,
                                          picking=picking_id, dst_location=dst_location, src_location=src_location)
                    
                    # Partie Soustraitance pour la création des réceptions des produits finis
                    line.create_move_pf_st(picking_id, currency_id, supplier_info)
                    
                    
            picking_id.wkf_waiting()
        #Si on a coché la case 'Faire autant de BL que de date de réception', on crée autant de picking
        #qu'il y a de date confirmée dans les lignes d'achat
        else:
            date_line = {}
            for line in self.purchase_order_line_ids:
                if line.confirmed_date:
                    if line.confirmed_date in date_line:
                        date_line[line.confirmed_date].append(line)
                    else:
                        date_line[line.confirmed_date] = [line]
                
                elif line.expected_date:
                    if line.expected_date in date_line:
                        date_line[line.expected_date].append(line)
                    else:
                        date_line[line.expected_date] = [line]
                
            for date, purchase_lines in date_line.iteritems():
                picking_id = picking_obj.create_picking(type=move_and_picking_type, partner=self.delivered_by_id, 
                                                     product_qty_uom={}, other_data=other_data)
                for purchase_line in purchase_lines:
                    if (line.product_id.type != 'service') or (line.product_id.type == 'service' and \
                                                           line.product_id.manage_service_receipt):
                        supplier_info = line.product_id.get_sinfo(partner_id=line.purchase_order_id.partner_id.id,
                                                               property_ids=line.property_ids.ids, state_dev=False)
                        move_other_data = {
                                           'sequence': line.sequence,
                                           'purchase_line_id': purchase_line.id,
                                           'name': purchase_line.name,
                                           'uom_id': purchase_line.uom_id.id,
                                           'sec_uom_qty': purchase_line.sec_uom_qty,
                                           'sec_uom_id': purchase_line.sec_uom_id.id,
                                           'uoi_qty': purchase_line.uoi_qty,
                                           'uoi_id': purchase_line.uoi_id.id,
                                           'date_expected': date,
                                           'date': date,
                                           'priority_date': date,
                                           'initial_uom_qty': purchase_line.uom_qty,
                                           'note': purchase_line.internal_note,
                                           'partner_price': line.price_unit,
                                           'currency_id': currency_id,
                                           'factor': line.factor,
                                           'divisor': line.divisor,
                                           'sinfo_id': supplier_info and supplier_info.id or False,
                                           'note': line.receipt_printed_note,
                                           }
                        if line.product_id.type == 'service' and line.product_id.manage_service_receipt:
                            if not self.warehouse_id.service_location_id:
                                raise ValidationError('There is no service location in your company')
                             
                            move_other_data['location_dest_id'] = self.warehouse_id.service_location_id.id
                        
                        move_other_data = line.move_other_data_subcontracting(move_other_data)
                        if move_and_picking_type == 'out':
                            src_location = False
                            dst_location = self.warehouse_id.supplier_location_id.id
                        else:
                            dst_location = line.purchase_order_id and line.purchase_order_id.location_id and line.purchase_order_id.location_id.id or False
                            #Si le partenaire a un emplacement fournisseur défini on récupère celui-ci sinon on récupère l'emplacement fournisseur de l'entrepôt de la société
                            if line.purchase_order_id.delivered_by_id and line.purchase_order_id.delivered_by_id.supplier_location_id:
                                src_location = line.purchase_order_id.delivered_by_id.supplier_location_id.id
                            else:
                                src_location = self.warehouse_id.supplier_location_id and self.warehouse_id.supplier_location_id.id or False
                            
                            src_location = line.purchase_order_id and line.purchase_order_id.delivered_by_id and line.purchase_order_id.delivered_by_id.supplier_location_id and line.purchase_order_id.delivered_by_id.supplier_location_id.id or False
                            
                        move_obj.create_move(purchase_line.product_id, qty=purchase_line.uom_qty, type=move_and_picking_type, other_data=move_other_data,
                                              picking=picking_id, dst_location=dst_location,src_location=src_location)
                        
                        # Partie Soustraitance pour la création des réceptions des produits finis
                        line.create_move_pf_st(picking_id, currency_id, supplier_info)
                        
                picking_id.wkf_waiting()
                
        return True
    
            
    @api.multi
    def action_call_again(self):
        """
            Fonction permettant d'afficher l'email de relance
        """
        if self.purchase_communication_method == 'email' and self.purchase_contact_ids:
            return self.env['mail.message'].action_send_mail(self.purchase_contact_ids, 'purchase.order', 'reminder', 
                                                             self.id)
        else:
            return self.env['mail.message'].action_send_mail(self.partner_id, 'purchase.order', 'reminder', 
                                                             self.id)
    
            
    def get_purchase_action_vals(self):
        data_obj = self.env['ir.model.data']
        today = fields.Date.today()
        object_model, action_type_id = data_obj.get_object_reference('base_openprod', 'simple_action_type_action')
        state_action_rs = self.env['action.state'].search([('to_do_state', '=', True)], limit=1)
        if not state_action_rs:
            state_action_rs = self.env['action.state'].search([], limit=1)
            
        return {'name': _('Action for purchase %s'%(self.name)),
                   'description': _('Action for a purchase'),
                   'start_datetime': today,
                   'stop_datetime': today,
                   'user_id': self.env.user.id,
                   'affected_user_id': self.env.user.id,
                   'state_id': state_action_rs.id,
                   'purchase_id': self.id,
                   'type_id': action_type_id}
        
        
    @api.multi
    def create_purchase_action(self):
        """
            Crée une action liée à l'achat
        """
        action_obj = self.env['calendar.event']
        for purchase in self:
            new_action_rcs = action_obj.create(purchase.get_purchase_action_vals())
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
            
            
    def change_confirmed_date(self, new_date):
        """
            Fonction qui modifie la date de confirmation de l'achat et modifie celles
            des lignes d'achat et des moves liés
        """
        if new_date:
            move_obj = self.env['stock.move']
            self.write({'confirmation_date': fields.Datetime.now(), 
                            'confirmation_user_id': self.env.user.id})
            for line in self.purchase_order_line_ids:
                if not line.confirmed_date:
                    line.write({'confirmed_date': new_date})
                    #On recherche et modifie le ou les moves liés à la ligne d'achat
                    move_rcs = move_obj.search([('purchase_line_id', '=', line.id), ('state', 'not in', ('done', 'cancel'))])
                    move_rcs.write({
                                    'date_expected': new_date, 
                                    'date': new_date,
                                    'priority_date': new_date,
                                    'is_confirmed': True
                                    })
                    move_rcs.update_covers()
                    
        return True
    
    
    def find_and_exec_done_purchase(self):
        """
            Fonction permettant de trouver l'activité avant l'activité terminée de l'achat et d'éxécuter son action
        """
        result = True
        object_model, object_id = self.env['ir.model.data'].get_object_reference('purchase', 'act_done_purchase')
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
    def action_waiting_purchase(self):
        """
            Fonction permettant de passer l'achat en attente
        """
        return self.write({
                           'quotation_date': fields.Date.today(),
                           'quotation_user_id': self.env.user.id,
                           'state': 'waiting',
                           })
    
    
    @api.multi
    def action_progress_purchase(self):
        """
            Fonction permettant de passer l'achat en cours
        """
        generate_picking = False
        if self.purchase_type != 'open':
            if not self.purchase_order_line_ids:
                raise ValidationError(_('You can\'t create a picking if there is no lines in your purchase'))
            
            if self.purchase_invoice_trigger_postpaid:
                self.generate_invoice(invoice_trigger='postpaid')
           
            for line in self.purchase_order_line_ids:
                if (line.product_id.type != 'service') or (line.product_id.type == 'service' and line.product_id.manage_service_receipt):
                    generate_picking = True
                    break
                
            purchase_data = {}
            if not self.validation_date:
                purchase_data['validation_date'] = fields.Datetime.now()
            
            if not self.validation_date:
                purchase_data['validation_user_id'] = self.env.user.id
            
            if purchase_data:
                self.write(purchase_data)
                
            if generate_picking:
                self.action_generate_picking()
            elif self.purchase_invoice_trigger_picking:
                raise ValidationError(_('You can\'t have a purchase invoiced on the delivery if all the lines are linked to a service which not manage receipts'))
        
            if self.need_picking_payment:
                self.generate_payment('before_delivery')
                
        return True
        
        
    @api.multi
    def action_progress_purchase_state(self):
        """
            Fonction permettant de passer l'achat à l'état en cours, nécessaire avec les nouveaux workflows
            afin de passer un achat en cours sans recréer de picking ou de facture
        """
        self.write({'state': 'progress'})
        return True

    
    def action_done_purchase(self):
        """
            Fonction permettant de passer l'achat en terminé
            On annule tous les BL non done et les factures brouillon
        """
        context2 = {}
        context2.update(self.env.context)
        context2['without_manage_state'] = True
        invoice_list = self.env['account.invoice']
        picking_list = self.env['stock.picking']
        for invoice_line in self.invoice_line_ids:
            if not invoice_line.invoice_id in invoice_list and invoice_line.invoice_id.state == 'draft':
                invoice_list += invoice_line.invoice_id
                
        for picking in self.picking_ids:
            if picking.state not in ('done', 'cancel') and picking not in picking_list:
                picking_list += picking
                
        invoice_list.with_context(context2).unlink()
        picking_list.wkf_cancel(manage_sale_purchase_state=False)
        picking_list.with_context(context2).unlink()
        for line in self.purchase_order_line_ids:
            if line.product_id.type == 'service' and not line.product_id.manage_service_receipt:
                line.write({
                            'received_qty': line.uom_qty,
                            'to_received': 0,
                            })
        
        self.write({'state': 'done'})    
        return True
    
    
    @api.one
    def wkf_cancel(self):
        """
            Fonction permettant de supprimer un picking et des moves liés à un achat
            et de passer l'achat en 'Brouillon'
            On passe également l'éventuelle commande ouverte en "En cours" si elle est "Terminée"
        """
        invoice_list = self.env['account.invoice']
        picking_list = self.env['stock.picking']
        payment_list = self.env['account.voucher']
        for line in self.invoice_line_ids:
            if line.invoice_id.state not in ['draft', 'cancel']:
                raise ValidationError(_('There is an invoice linked to this purchase which '
                                       'is not cancelled or draft'))
            elif not line.invoice_id in invoice_list:
                invoice_list += line.invoice_id
        
        for line in self.purchase_order_line_ids:
            for move in line.stock_move_ids:
                if not move.picking_id in picking_list and move.picking_id.state != 'done':
                    picking_list += move.picking_id
                elif move.picking_id.state == 'done':
                    raise ValidationError(_('There is a done picking linked to this purchase'))
                
                
        for payment in self.payment_ids:
            if payment.state in ['draft', 'cancel']:
                payment_list += payment
        
        self.write({'state':'cancel'})
        for line in self.purchase_order_line_ids:
            line.do_action_on_line_cancel()
            
        context2 = {}
        context2.update(self.env.context)
        context2['without_manage_state'] = True
        payment_list.unlink()  
        invoice_list.with_context(context2).unlink()
        picking_list.wkf_cancel(manage_sale_purchase_state=False)
        open_order = self.open_order_id
        if self.purchase_type == 'call' and open_order and open_order.state == 'done':
            purchase_line_obj = self.env['purchase.order.line']
            for line in self.purchase_order_line_ids:
                #On recherche les lignes de la commande ouverte correspondant,
                #Si on en trouve, on passe la commande ouverte à "en cours"
                open_line = purchase_line_obj.search([('product_id', '=', line.product_id.id), ('purchase_order_id', '=', open_order.id)])
                if open_line:
                    open_order.write({'state': 'draft'})
                    open_order.delete_workflow()
                    open_order.create_workflow()
                    open_order.signal_workflow('purchase_validate')
                    break
                
        self.write({
                    'quotation_date': False,
                    'quotation_user_id': False,
                    'validation_date': False,
                    'validation_user_id': False ,
                    'confirmation_date': False,
                    'confirmation_user_id': False,  
                    'receipt_demand_date': False,
                    'receipt_demand_user_id': False,   
                    })
            
        return True
    
    
    @api.one
    def action_draft_purchase(self):
        """
            Fonction permettant de passer l'achat en brouillon
            En cas d'achat appelé, on repasse l'achat ouvert à terminé si la quantité est la dernière 
        """
        result = True
        open_order = self.open_order_id
        if self.purchase_type == 'call' and open_order and open_order.state != 'done':
            uom_obj = self.env['product.uom']
            qty = 0
            purchase_line_obj = self.env['purchase.order.line']
            if self.purchase_order_line_ids:
                for line in self.purchase_order_line_ids:
                    # Recherche des lignes de la commande ouverte correspondant
                    open_order_lines = purchase_line_obj.search([('product_id', '=', line.product_id.id), ('purchase_order_id', '=', open_order.id)])
                    for open_line in open_order_lines:
                        line_qty = uom_obj._compute_qty(line.sec_uom_id.id, line.sec_uom_qty, open_line.sec_uom_id.id)
                        qty += (open_line.remaining_called_qty - line_qty)
                    
                if qty <= 0:
                    # Si l'achat doit être passé en terminé, recherche de l'activité finale du workflow lancement de ses méthodes
                    open_order.find_and_exec_done_purchase()
        
        self.write({'state': 'draft', 'show_invoice_button': True})
        return result
    
    
    @api.one
    def action_receipt_demand(self):
        """
            Fonction permettant d'écrire dans l'achat la date de réception de l'AR
        """
        self.write({'receipt_demand_date': fields.Date.today(), 'receipt_demand_user_id': self.env.user.id})
        return True
    
    
    @api.multi
    def action_confirm_delay(self):
        """
            Fonction permettant d'afficher le wizard de confirmation de date
        """
        action_struc = {}
        action_dict = get_form_view(self, 'purchase.action_select_confirm_date')
        if action_dict and action_dict.get('id') and action_dict.get('type'):
            action = self.env[action_dict['type']].browse(action_dict['id'])
            action_struc = action.read()[0]
                  
        return action_struc
    
    
    @api.multi
    def action_change_purchase(self):
        """
            Fonction permettant de changer l'achat et de le passer en "waiting".
            On ne peut changer un achat que s'il n'est pas lié à un BL
            done, ou à une facture non draft ou non cancel
        """
        invoice_list = self.env['account.invoice']
        picking_list = self.env['stock.picking']
        payment_list = self.env['account.voucher']
        for purchase in self:
            for invoice_line in purchase.invoice_line_ids:
                if invoice_line.invoice_id and invoice_line.invoice_id.state not in ['draft', 'cancel']:
                    raise ValidationError(_('You can\'t change the purchase because there is an opened or '
                    'done linked invoice'))
                elif invoice_line.invoice_id not in invoice_list:
                    invoice_list += invoice_line.invoice_id
             
            for line in purchase.purchase_order_line_ids:
                for move in line.stock_move_ids:
                    if not move.picking_id in picking_list and move.picking_id.state != 'done':
                        picking_list += move.picking_id
                    elif move.picking_id.state == 'done':
                        raise ValidationError(_('You can\'t change the purchase because there is a done linked '
                                          'picking'))
                
            for payment in self.payment_ids:
                if payment.state in ['draft', 'cancel']:
                    payment_list += payment
        
        context2 = {}
        context2.update(self.env.context)
        context2['without_manage_state'] = True
        payment_list.unlink()  
        picking_list.wkf_cancel(manage_sale_purchase_state=False)
        picking_list.with_context(context2).unlink()
        invoice_list.with_context(context2).unlink()
        self.write({
            'state': 'draft', 
            'quotation_date': False, 
            'quotation_user_id': False,
            'validation_date': False, 
            'validation_user_id': False,
            'receipt_demand_date': False, 
            'receipt_demand_user_id': False,
        })
        for purchase in self:
            for line in self.purchase_order_line_ids:
                line.do_action_on_line_cancel()
     
    
    @api.multi
    def show_purchase_picking(self):
        """
            Fonction qui cherche et retourne les pickings de l'achat
        """
        action_struc = {}
        action_dict = get_form_view(self, 'purchase.purchase_picking_action')
        purchase_id = self.id
        if action_dict and action_dict.get('id') and action_dict.get('type'):
            action = self.env[action_dict['type']].browse(action_dict['id'])
            action_struc = action.read()
            action_struc[0]['context'] = {'purchase_id': purchase_id}
            action_struc = action_struc[0]
              
        return action_struc

    
    @api.multi
    def show_purchase_invoice(self):
        """
            Fonction qui cherche et retourne les factures pour un achat
        """
        for purchase in self:
            action_struc = {}
            invoice_line_list = []
            action_dict = get_form_view(self, 'purchase.purchase_invoice_action')
            for purchase_line in purchase.purchase_order_line_ids:
                invoice_line_list += [x.invoice_id.id for x in purchase_line.invoice_line_ids]
                
            line_ids = list(set(invoice_line_list))
            if action_dict and action_dict.get('id') and action_dict.get('type'):
                action = self.env[action_dict['type']].browse(action_dict['id'])
                action_struc = action.read()
                action_struc[0]['context'] = {'invoice_ids': line_ids}
                action_struc = action_struc[0]
              
        return action_struc

    
    @api.multi
    def show_purchase_action(self):
        """
            Fonction qui cherche et retourne les actions d'un achat
        """
        action_obj = self.env['calendar.event']
        for purchase in self:
            action_struc = {}
            action_dict = get_form_view(self, 'base_openprod.see_actions')
            action_ids = action_obj.search([('purchase_id', '=', purchase.id)]).ids
            if action_dict and action_dict.get('id') and action_dict.get('type'):
                action = self.env[action_dict['type']].browse(action_dict['id'])
                action_struc = action.read()
                action_struc[0]['context'] = {'action_ids': action_ids}
                action_struc = action_struc[0]
              
        return action_struc
    
    
    def update_other_data(self, other_data, supplier_rc):
        return {}
    
    
    def create_purchase(self, supplier=False, po_line=None, date=False, other_data=None, first_qty=False, forced_qty=False, not_need_qty=False):
        """
            Création d'un achat
            :type self: purchase.order
            :param supplier: Fournisseur de l'achat
            :type supplier: recordset: res.partner
            :param po_line: Dictionnaire contenant autant de lignes d'achats que souhaitées
            :type po_line: dict {product: {'uom_qty': ..., 'uom_id': ..., 'sec_uom_qty': ..., 'sec_uom_id': ...}}
            :param date: Date par défaut des lignes d'achat
            :type date: Date
            :param other_data: Dictionnaire permetant de passer d'autres champs ou de forcer des champs
            :type other_data: dict
            :param first_qty: Les détails de la ligne d'achat (optionnel), pour indiquer que l'on passe une qty en unité de gestion
            :type first_qty: value char 'uom_qty'
            :param forced_qty: True si on souhaite entrer une qté inférieure à la qté minimale
            :type forced_qty: boolean
            :return: L'achat créé
            :rtype: recordset purchase.order
        """
        #On fait une liste des champs qui sont obligatoires dans l'achat
        required_fields = ['invoicing_method_id', 'payment_id', 'payment_term_id', 'purchase_account_system_id']
        vals = {}
        if not other_data:
            other_data = {}
            
        if supplier:
            if isinstance(supplier, int):
                supplier = self.env['res.partner'].browse(supplier)
            
            vals['partner_id'] = supplier.id
            vals['purchase_type'] = 'series'
        
        other_data.update(self.update_other_data(other_data, supplier))
        #Si on a une valeur forcée pour le fournisseur livré, on la récupère, sinon 
        #on prend le partenaire lié à la société de l'employé
        if other_data.get('delivered_supplier_id'):
            delivered_supplier = other_data['delivered_supplier_id']
        else:
            delivered_supplier = self.env.user.company_id.partner_id
        
        #On récupère les valeurs des onchanges
        #(informations du fournisseur, informations du fournisseur livré)
        vals.update(self.onchange_purchase_supplier(supplier))
        vals.update(self.onchange_delivered_supplier(delivered_supplier))
        if vals.get('paid_to_id') and vals.get('invoiced_by_id') and vals.get('delivered_by_id'):
            vals.update(self.onchange_delivered_by_supplier_id(vals['delivered_by_id']))
            vals.update(self.onchange_paid_to_id(vals['paid_to_id']))
            vals.update(self.onchange_invoiced_by_id(vals['invoiced_by_id']))
        
        #Si on a une valeur forcée pour l'adresse livrée, on la récupère, sinon 
        #on prend l'adresse ramenée par le onchange
        if other_data.get('delivered_address_id'):
            delivered_address = other_data['delivered_address_id']
        else:
            delivered_address = vals.get('delivered_address_id', False)
            
        vals.update(self.onchange_delivered_address_id(delivered_address))
        #On récupère les valeurs forcées
        if other_data:
            vals.update(other_data)
        
        #On vérifie que les champs qui ne sont pas obligatoires lorsque le fournisseur est prospect
        #sont bien remplies
        for req_fields in required_fields:
            if not vals.get(req_fields):
                raise except_orm(_('Error'), _('The field %s is not filled in the supplier form, you '
                                               'have to fill it if you want to make a purchase whith this supplier')%(req_fields))
                
        #Création de l'achat
        purchase = self.create(vals)
        if po_line:
            #Si le dictionnaire po_line est rempli, on va allé créer autant de ligne d'achat
            #que de produits présents dans le dictionnaire
            po_line_obj = self.env['purchase.order.line']
            for product, values in po_line.iteritems():
                #Si on a pas de valeur pour la date demandée, on passe la date de la fonction
                if not 'expected_date' in values:
                    values['expected_date'] = date or fields.Date.today()
                    
                po_line_obj.create_purchase_order_line(purchase, product, values, first_qty=first_qty, forced_qty=forced_qty, not_need_qty=not_need_qty)
        
        purchase.write(purchase.onchange_purchase_order_line_ids(from_real_onchange=False))
        return purchase
    
    
    def check_merge(self, purchase_to_check=False):
        """
            Fonction permettant de vérifier que les achats peuvent être mergés
            :type self: purchase.order
            :param purchases_to_check: Achat que l'on souhaite tester
            :type purchases_to_check: recordset: purchase.order
            :return: Si les achats peuvent être mergés ou l'achat et le champ qui ne peuvent pas l'être
            :rtype: dict
        """
        match = True
        field = ''
        purchase_info = ()
        #Liste de champs devant être équivalents
        if purchase_to_check:
            fields_checked = [
                              'partner_id',
                              'currency_id',
                              'purchase_type',
                              'delivered_supplier_id',
                              'location_id',
                              'purchase_account_system_id',
                              'invoicing_method_id',
                              'payment_id',
                              'payment_term_id',
                              'discount',
                              'discount_value',
                              'max_delay',
                              'purchase_incoterm_id',
                              ]
            for k in fields_checked:
                if self[k] != purchase_to_check[k]:
                    match = False
                    field = k
                    break
                
            if not match:
                purchase_info = (purchase_to_check.name, field)
                
        return match, purchase_info
    
    
    @api.multi
    def do_merge(self):
        """
            Fonction permettant de merger plusieurs achats en un seul
            Les commandes d'achats peuvent uniquement être mergées si:
            - Elles sont en brouillon
            - Elles concernent le même fournisseur
            - Elles ont la même devise
        """
        first_purchase = False
        purchase_line_obj = self.env['purchase.order.line']
        procurement_obj = self.env['procurement.order']
        make_to_order_ids = self.env['purchase.order.line']
        data = {}
        for purchase in self:
            pol_list = []
            if purchase.state != 'draft':
                raise except_orm(_("Error"), _('The purchase %s is not in draft')%(purchase.name))
            
            #On récupère les ids des lignes dont le procurement est à la demande
            procurement_search = procurement_obj.search([('trigger_supply', '=', 'make_to_order'), 
                                                        ('pol_id', 'in', purchase.purchase_order_line_ids.ids)])
            if procurement_search:
                pol_list = [procurement.pol_id.id for procurement in procurement_search if procurement.pol_id]
                
            #On récupère le premier achat, c'est celui qui va nous servir de référence
            if not first_purchase:
                first_purchase = purchase
                first_try = True
            else:
                #Variable permettant de repérer le premier passage
                first_try = False
                
            #Si ce n'est pas le premier passage dans la boucle, on vérifie que les achats puissent
            #être mergés
            if not first_try:
                merge, purchase_info = first_purchase.check_merge(purchase)
                if not merge:
                    raise except_orm(_("Error"), _('The purchase with %s has not the same value for the field "%s"'
                                          ' than the purchase reference (%s)')%(purchase_info[0], purchase_info[1], first_purchase.name))
            
            data, new_make_to_order_ids = purchase.purchase_order_line_ids.create_merge_lines(pol_list, data)
            make_to_order_ids += new_make_to_order_ids
        
        if first_purchase:
            ctx = self.env.context.copy()
            ctx['no_line_copy'] = True
            new_purchase = first_purchase.with_context(ctx).copy({'purchase_order_line_ids': None})
            if data:
                for product_list in data.values():
                    for product_line, values in product_list.iteritems():
                        if values.get('procurement_consider_purchase'):
                            del values['procurement_consider_purchase']
                            not_need = True
                        else:
                            if values.get('quantity'):
                                values['sec_uom_qty'] = values['quantity']
                            
                            not_need = False
                        
                        if values.get('procurement'):
                            procurement_list = values.get('procurement', [])
                            del values['procurement']
                        else:
                            procurement_list = []
                            
                        product = product_line[0]
                        po_line_id = purchase_line_obj.create_purchase_order_line(purchase=new_purchase, product=product,
                                                                                   values=values, first_qty=False, 
                                                                                   forced_qty=False, not_need_qty=not_need)
                        #Boucle car liste de procurement
                        for proc in procurement_list:
                            proc.write({'pol_id': po_line_id.id})
                
            #On assigne toutes les lignes d'achat dont le procurement est à la demande au premier achat
            make_to_order_ids.write({'purchase_order_id': new_purchase.id})
            self.unlink()
            new_purchase._onchange_purchase_order_line_ids()
            action_struc = get_form_view(self, 'purchase.purchase_order_see_form', new_purchase.id)
            return action_struc
        else:
            return  {'type': 'ir.actions.act_window_close'}
        
    
    @api.model
    def check_supplier_reminder(self):
        """
            Fonction appelée par un cron, on récupère tous les achats en cours
            qui nécessitent une relance et on crée une action pour l'utilisateur
        """
        action_obj = self.env['calendar.event']
        data_obj = self.env['ir.model.data']
        purchase_ids = self.search([('reminder_ok', '=', False), 
                                    ('state', '=', 'progress'), 
                                    ('supplier_reminder', '=', True), 
                                    ('confirmation_date', '=', False),
                                    ('purchase_type', '!=', 'open')])
        company_calendar = self.env.user.company_id.partner_id and self.env.user.company_id.partner_id.calendar_id 
        today = fields.Date.today()
        state_action_rs = self.env['action.state'].search([('to_do_state', '=', True)], limit=1)
        if not state_action_rs:
            state_action_rs = self.env['action.state'].search([], limit=1)
            
        for purchase in purchase_ids:
            if purchase.partner_id and purchase.validation_date:
                str_limit_date = company_calendar.get_date(purchase.validation_date, purchase.partner_id.reminder_delay)
                if str_limit_date:
                    date_limit_date = fields.Datetime.from_string(str_limit_date)
                    limit_date = fields.Date.to_string(date_limit_date.date())
                    date_to = fields.Date.to_string(fields.Date.from_string(today) + relativedelta(days=1))
                    if limit_date <= today:
                        object_model, action_type_id = data_obj.get_object_reference('base_openprod', 'simple_action_type_action')
                        vals = {
                               'name': _('Reminder %s / %s'%(purchase.name, purchase.partner_id.name)),
                               'description': _('Reminder supplier because the purchase is not confirmed'),
                               'start_datetime': today,
                               'start_date': today,
                               'stop_datetime': date_to,
                               'stop_date': date_to,
                               'user_id': self.env.user.id,
                               'affected_user_id': purchase.purchaser_id and purchase.purchaser_id.id or self.env.user.id,
                               'state_id': state_action_rs.id,
                               'purchase_id': purchase.id,
                               'type_id': action_type_id,
                               }
                        action_obj.create(vals)
                        purchase.reminder_ok = True
            
        return True
    
    
    @api.multi
    def get_taxes_values(self):
        tax_grouped = {}
        for line in self.purchase_order_line_ids:
            taxes = line.taxes_ids.compute_all(line.price_unit, self.currency_id, line.uoi_qty, line.product_id, self.partner_id)['taxes']
            for tax in taxes:
                val = {
                    'purchase_id': self.id,
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
    
    
    def pass_done_purchase(self, unlink_invoice_ids=False, unlink_picking_ids=False):
        """
            Fonction qui permet de gérer automatiquement l'état 'terminé' d'un achat:
                - Si l'achat est en cours, que le mode de facturation n'est pas à la demande
                  et que tous les BR sont dones et les factures sont payées, on passe l'état à 'terminé'
                - Si l'achat est terminé, que le mode de facturation n'est pas à la demande
                  et qu'il y a un BR non done ou une facture non payée, on repasse la vente en cours
            :type self: purchase.order
            :param unlink_invoice_ids: Liste des factures qui vont être supprimées
            :type unlink_invoice_ids: List
            :param unlink_picking_ids: Liste des pickings qui vont être supprimées
            :type unlink_picking_ids: List
            :return: True
            :rtype: boolean
        """
        result = True
        if self.state in ('done', 'progress'):
            if self.purchase_invoice_trigger_postpaid or self.purchase_invoice_trigger_picking:
                done_purchase = True
                if not unlink_invoice_ids:
                    unlink_invoice_ids = []
    
                if not unlink_picking_ids:
                    unlink_picking_ids = []
                    
                #On commence par récupérer toutes les factures liées à l'achat via les lignes
                #de facture
                invoice_list = [invoice_line.invoice_id for invoice_line in self.invoice_line_ids]
                set_invoice_list = list(set(invoice_list))
                for invoice in set_invoice_list:
                    if invoice.id not in unlink_invoice_ids:
                        if invoice.read(['state'])[0]['state'] not in ('paid', 'cancel'):
                            done_purchase = False
                            break
                    
                if done_purchase:
                    #On regarde ensuite tous les pickings liés à l'achat
                    #Si l'un n'est pas terminé ou annulé ou s'il est terminé mais
                    #doit être facturé, on ne passe pas l'état à 'terminé'
                    for picking in self.picking_ids:
                        if picking.id not in unlink_picking_ids:
                            state = picking.read(['state'])[0]['state']
                            if state not in ('done', 'cancel'):
                                done_purchase = False
                                break
                            elif state == 'done' and picking.invoice_state == '2binvoiced':
                                done_purchase = False
                                break
                
                if done_purchase and self.state == 'progress':
                    #Si l'achat doit être passé en terminé, on recherche l'activité finale du workflow et 
                    #on lance ses méthodes
                    self.find_and_exec_done_purchase()
                        
                elif not done_purchase and self.state == 'done':
                    #Si l'achat doit être repassé en cours, on supprime le workflow et on passe 
                    #le signal de la transition de draft à commande validée
                    self.write({'state': 'draft'})
                    self.delete_workflow()
                    self.create_workflow()
                    self.signal_workflow('purchase_validate')
                            
        return result
    
    
    @api.model
    def create(self, vals):
        """
            On écrit le nom de l'achat à partir de sa séquence en base
        """
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].get('purchase.order') or '/'
        
        vals['creation_date'] = fields.Datetime.now()
        purchase = super(purchase_order, self).create(vals)
        return purchase


    @api.multi
    def unlink(self):
        """
            On vérifie que l'achat est bien en brouillon ou annulé,
            On supprime d'abord les pickings brouillon ou annulés liés à l'achat
            Si l'achat est lié à un achat ouvert, on repasse celui-ci en "en cours"
            s'il était en terminé
        """
        purchase_line_obj = self.env['purchase.order.line']
        for po in self:
            if po.state not in ('draft', 'cancel'):
                raise except_orm(_('Error'), _('Impossible to delete a purchase order if its state is not draft or cancel.'))
            
            for picking in po.picking_ids:
                if picking.state not in ('draft', 'cancel'):
                    raise except_orm(_('Error'), _('Impossible to delete the purchase picking if its state is not draft or cancel.'))
                else:
                    picking.unlink()
            
            open_order = po.open_order_id
            if po.purchase_type == 'call' and open_order and open_order.state == 'done':
                for line in po.purchase_order_line_ids:
                    #On recherche les lignes de la commande ouverte correspondant,
                    #Si on en trouve une, on repasse l'achat à "en cours"
                    open_line = purchase_line_obj.search([('product_id', '=', line.product_id.id), ('purchase_order_id', '=', open_order.id)])
                    if open_line:
                        open_order.write({'state': 'draft'})
                        open_order.delete_workflow()
                        open_order.create_workflow()
                        open_order.signal_workflow('purchase_validate')
                        break
        
        return super(purchase_order, self).unlink()
    
    
    @api.one
    def copy(self, default=None):
        """
            On vide les quantités reçues et facturées
        """
        if not default:
            default = {}
        
        new_purchase = super(purchase_order, self).copy(default=default)
        context = self.env.context
        if not context.get('no_line_copy'):
            order_line_default = {
                                   'purchase_order_id': new_purchase.id,
                                   'received_qty' : 0,
                                   'to_received' : 0,
                                   }
            self.purchase_order_line_ids.copy(order_line_default)
            
        return new_purchase
    
    
    @api.multi
    def write(self, vals=None):
        """
            On ne peut changer le type de l'achat si il est appelé ou ouvert, 
            et on ne peut modifier l'achat ouvert si il est terminé
        """
        if not vals:
            vals = {}
        
        for purchase in self:
            if 'purchase_type' in vals and purchase.purchase_type in ['call', 'open'] and vals['purchase_type'] != purchase.purchase_type:
                raise Warning(_("You can't change the type of a called or opened purchase"))
            
            if 'open_order_id' in vals and purchase.open_order_id.state == 'done' and purchase.open_order_id.id != vals['open_order_id']:
                raise Warning(_("You can't change the opened order of a purchase if the opened order is done"))
        
        res = super(purchase_order, self).write(vals=vals)
        return res
    
    
    def additional_function_domain(self, arg):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de purchase_order
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
        return super(purchase_order,self).search(args=args_modified, offset=offset, limit=limit, order=order, count=count) 
    
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=1000):
        """
            Fonction name_search
        """
        args.append(('name', 'ilike', name))
        args = self.compute_domain_args_sale(args)
        recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()
    
    
    
class purchase_common_attribute(models.Model):
    _name = 'purchase.common.attribute'
    _order = 'sequence'
    
    purchase_line_id = fields.Many2one('purchase.order.line', string='Purchase line', required=True, ondelete='cascade')
    sequence = fields.Integer(default=0, required=True)
    product_common_attribute_id = fields.Many2one('common.attribute.model', string='Attribute', required=False, ondelete='cascade')
    value = fields.Char(size=128, required=False)