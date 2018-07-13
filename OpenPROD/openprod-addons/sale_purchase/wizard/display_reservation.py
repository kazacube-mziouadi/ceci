# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
import openerp.addons.decimal_precision as dp
from openerp.tools.sql import drop_view_if_exists
from dateutil.relativedelta import relativedelta
from datetime import datetime,date
from openerp.addons.base_openprod.common import get_form_view

class stock_move_reserve(models.Model):
    """ 
        Stock move report
    """
    _name="stock.move.reserve"
    _description="Stock outgoing report"
    _rec_name = 'product_id'
    _order = 'date asc'
    
    @api.model
    def _type_get(self):
        return [
                ('in', _('IN')),
                ('out', _('OUT')),
                       ]
    
    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('waiting', _('Waiting')),
                ('done', _('Done')),
                ('cancel', _('Cancel')),
                       ]
        
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='set null')
    qty = fields.Float(string='Quantity', default=0.0, required=False, digits=dp.get_precision('Product quantity'))
    uom_id = fields.Many2one('product.uom', string='UoM', required=False, ondelete='set null')
    date = fields.Date(string='Date')
    sale_order_id = fields.Many2one('sale.order', string='Sale order', required=False, ondelete='set null')
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase order', required=False, ondelete='set null')
    qty_in_stock = fields.Float(string='Quantity in stock', default=0.0, required=False, digits=dp.get_precision('Product quantity'))
    type = fields.Selection('_type_get', string="Type")
    state = fields.Selection('_state_get', string='State')
    
    
class stock_reserve_report(models.Model):
    """ 
        Stock reserve report
    """
    _name="stock.reserve.report"
    _description="Stock outgoing report"
    _auto = False
    _log_access = False
    _rec_name = 'product_id'
    _order = 'date asc'
    
    
    @api.model
    def _type_get(self):
        return [
                ('in', _('IN')),
                ('out', _('OUT')),
                ('int', _('INTERNAL')),
                ('ext', _('EXTERNAL')),
                       ]
    
    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('waiting', _('Waiting')),
                ('done', _('Done')),
                ('cancel', _('Cancel')),
                       ]
        
    
    @api.one
    @api.depends('qty')
    def _compute_qty_in_stock(self):
        """
            Fonction qui calcule la quantité en stock en fonction du stock du produit
        """
        
        self.qty_in_stock = 0
        
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='restrict')
    qty = fields.Float(string='Quantity', default=0.0, required=False, digits=dp.get_precision('Product quantity'))
    uom_id = fields.Many2one('product.uom', string='UoM', required=False, ondelete='set null')
    date = fields.Date(string='Date')
    sale_order_id = fields.Many2one('sale.order', string='Sale order', required=False, ondelete='set null')
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase order', required=False, ondelete='restrict')
    qty_in_stock = fields.Float(string='Quantity in stock', default=0.0, required=False, digits=dp.get_precision('Product quantity'),
                                compute='_compute_qty_in_stock')
    type = fields.Selection('_type_get', string="Type")
    state = fields.Selection('_state_get', string='State')
    
    
    def init(self, cr):
        drop_view_if_exists(cr, 'stock_reserve_report')
        cr.execute("""
            create or replace view stock_reserve_report as (
                SELECT
                    m.id as id,
                    m.product_id as product_id,
                    m.uom_id as uom_id,
                    m.date as date,
                    so.id as sale_order_id,
                    po.id as purchase_order_id,
                    m.uom_qty as qty,
                    m.type as type,
                    m.state as state
                FROM 
                  stock_move m
                LEFT JOIN sale_order_line s
                    ON (s.id = m.sale_line_id)
                LEFT JOIN sale_order so
                    ON (so.id = s.sale_order_id)
                LEFT JOIN purchase_order_line p
                    ON (p.id = m.purchase_line_id)
                LEFT JOIN purchase_order po
                    ON (po.id = p.purchase_order_id)
                WHERE m.is_forecast != true
            )""")
        
#     def unlink(self, cr, uid, ids, context={}):
#         raise osv.except_osv(_('Error !'), _('You cannot delete any record!'))



class display_reservation(models.TransientModel):
    """ 
        Wizard to show reservations for the selected product
    """
    _name = 'display.reservation'
    _description = 'Wizard to show reservations for the selected product'
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(display_reservation, self).default_get(fields_list=fields_list)
        context = self.env.context
        if context.get('reservation_product_id'):
            product_id = context['reservation_product_id']
        elif context.get('active_model') == 'stock.move' and context.get('active_id', False):
            product_id = self.env['stock.move'].browse(context['active_id']).read(['product_id'], load='_classic_write')[0]['product_id']
        else:
            product_id = False
            
        if product_id:
            res['product_id'] = product_id
            res['display_reservation'] = True
            res['from_default'] = True
            res['stock_move_ids'] = self.get_stock_moves_reserve(product_id, forecast=False)
            res['forecast_stock_move_ids'] = self.get_stock_moves_reserve(product_id, forecast=True)
            res['week_move_ids'],end_date = self._prepare_week_line_ids(product_id)
            res['month_move_ids'] = self._prepare_month_line_ids(product_id, end_date)
            res['graph_stock_move_ids'] = [x.id for x in self.env['stock.move'].search([('state', 'not in', ['draft', 'cancel']),('is_forecast','=',False),('product_id', '=', product_id)])]
        
        return res
    
    
    @api.one
    @api.depends('product_id')
    def _compute_graph_stock_move(self):
        """
            On récupère les moves du produit sélectionné pour afficher le graphique
        """
        self.graph_stock_move_ids = [x.id for x in self.env['stock.move'].search([('state', 'not in', ['draft', 'cancel']),
                                                                                  ('is_forecast','=',False),
                                                                                  ('product_id', '=', self.product_id.id)])]
    
    
    def get_week_dates(self, week, year):
        """
            Renvoie la date de début et la date de fin d'une semaine
        """
        res = {'start_date': False, 'end_date': False}
        week_date = datetime.strptime('%04d-%02d-1' % (year, week), '%Y-%W-%w')
        if date(year, 1, 4).isoweekday() > 4:
            res['start_date'] = fields.Datetime.to_string(week_date - relativedelta(days=7))
            res['end_date'] = fields.Datetime.to_string(week_date - relativedelta(seconds=1))
        else:
            res['start_date'] = fields.Datetime.to_string(week_date)
            res['end_date'] = fields.Datetime.to_string(week_date + relativedelta(days=7) - relativedelta(seconds=1))
            
        return res
    
    
    def get_month_dates(self, month, year):
        """
            Renvoie la date de début et la date de fin d'un mois
        """
        res = {'start_date': False, 'end_date': False}
        res['start_date'] = '%04d-%02d-01 00:00:00'%(year, month)
        res['end_date'] = fields.Datetime.to_string((fields.Datetime.from_string(res['start_date']) + relativedelta(months=1)) - relativedelta(seconds=1))
        return res
    
    
    def get_reservation_per_date(self, product, start_date=False, end_date=False, start_operator='>=', end_operator='<='):
        """
            Renvoie la quantité de reservation d'un produit en fonction d'une date de début (optionnelle) et une date de fin (optionnelle) 
            Fait éventuellement la conversion entre deux unités
        """
        uom_obj = self.env['product.uom']
        if isinstance(product, int):
            product = self.env['product.product'].browse(product)
        
        search_args = [('product_id', '=', product.id), ('type', '=', 'out'), ('state', '!=', 'cancel')]
        if start_date:
            search_args.append(('date', start_operator, start_date))
            
        if end_date:
            search_args.append(('date', end_operator, end_date))
        
        reserve_qty = 0.0
        reserve_ids = self.env['stock.reserve.report'].search(search_args)
        for reserve in reserve_ids:
            if reserve.uom_id and reserve.uom_id.id != product.uom_id.id and reserve.uom_id.category_id.id == product.uom_id.category_id.id:
                reserve_qty += uom_obj._compute_qty(reserve.uom_id.id, reserve.qty, product.uom_id.id)
            else:
                reserve_qty += reserve.qty
                    
        return reserve_qty
    
    
    def _prepare_week_line_ids(self, product):
        res2 = []
        res = []
        end_date = False
        now = fields.Datetime.from_string(fields.Datetime.now())
        for i in range(5):
            compute_date = (now - relativedelta(weeks=i))
            week = compute_date.isocalendar()[1]
            year = compute_date.isocalendar()[0]
            dates = self.get_week_dates(week, year)
            qty = self.get_reservation_per_date(product, dates['start_date'], dates['end_date'])
            res2.append({'week': str(week),
                        'year': str(year),
                        'qty': qty})
            end_date = dates['end_date']
        
        if res2:
            res2 = sorted(res2, key=lambda records: records['week']) 
            for record in res2:
                res.append((0, 0, record))
            
        return res, end_date
    
    
    def _prepare_month_line_ids(self, product, start_date=False):
        res = []
        now = fields.Datetime.from_string(fields.Datetime.now())
        first = True
        for i in range(5):
            compute_date = ((start_date and fields.Datetime.from_string(start_date) or now) + relativedelta(months=i))
            month = compute_date.month
            year = compute_date.year
            dates = self.get_month_dates(month, year)
            if first and start_date and start_date >= dates['start_date']:
                qty = self.get_reservation_per_date(product, start_date, dates['end_date'])
                first = False
            else:
                qty = self.get_reservation_per_date(product, dates['start_date'], dates['end_date'])
                
            res.append((0, 0, {'month': str(month),
                        'year': str(year),
                        'qty': qty}))
            
        return res

    
    def values_stock_move_reserve(self, move, stock_quantity):
        values = {
                  'date': move.date,
                  'product_id': move.product_id.id,
                  'qty': move.get_product_uom_qty(),
                  'uom_id': move.uom_id.id,
                  'type': move.type,
                  'sale_order_id': move.sale_line_id and  move.sale_line_id.sale_order_id.id or False,
                  'purchase_order_id': move.purchase_line_id and move.purchase_line_id.purchase_order_id.id or False,
                  'outgoing_wo_id': move.wo_outgoing_id.id,
                  'incoming_wo_id': move.wo_incoming_id.id,
                  'qty_in_stock': stock_quantity,
                  'state': move.state,
                  }
        return values
    

    def get_stock_moves_reserve(self, product_id, forecast=False):
        stock_move_list = []
        product = self.env['product.product'].browse(product_id)
        first_move = False
        stock_quantity = 0
        move_reserve_obj = self.env['stock.move.reserve']
        args = [('product_id', '=', product_id),
               ('state', 'not in', ('done', 'cancel')),
               ('type', 'in', ('in', 'out'))]
        if forecast:
            args.append(('is_forecast','=', True))
        else:
            args.append(('is_forecast','=', False))
            
        research_moves = self.env['stock.move'].search(args, order='date asc')
        for move in research_moves:
            if not first_move:
                stock_quantity = product.available_stock
                first_move = True
            
            if move.type == 'in':
                stock_quantity += move.get_product_uom_qty()
            elif move.type == 'out':
                stock_quantity -= move.get_product_uom_qty()
                
            values = self.values_stock_move_reserve(move, stock_quantity)
            reserve = move_reserve_obj.create(values)
            stock_move_list.append(reserve.id)
            
        return stock_move_list
    
    
    @api.multi
    def update_product_id(self):
        """
            Fonction qui met à jour la vue pour un autre produit
        """
        action_struc = {}
        action_dict = get_form_view(self, 'sale_purchase.action_display_reservation')
        product_id = self.product_id.id
        if action_dict and action_dict.get('id') and action_dict.get('type'):
            action = self.env[action_dict['type']].browse(action_dict['id'])
            action_struc = action.read()
            action_struc[0]['context'] = {'reservation_product_id': product_id}
            action_struc = action_struc[0]
              
        return action_struc
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='set null')
    stock = fields.Float(string='Stock', default=0.0, required=False, related='product_id.available_stock', readonly=True)
    virtual_stock = fields.Float(string='Virtual stock', default=0.0, required=False, related='product_id.virtual_stock', 
                                 readonly=True)
    week_move_ids = fields.One2many('display.reservation.week.line', 'display_reservation_id', string='Week moves',
                                    readonly=True)
    month_move_ids = fields.One2many('display.reservation.month.line', 'display_reservation_id', string='Month moves',
                                    readonly=True)
    stock_move_ids = fields.Many2many('stock.move.reserve', 'stock_move_reserve_reservation_rel', 'visualisation_id', 
                                      'stock_move_id', string='Stock moves', readonly=True)
    forecast_stock_move_ids = fields.Many2many('stock.move.reserve', 'forecast_stock_move_reserve_reservation_rel', 'visualisation_id', 
                                      'forecast_stock_move_id', string='Forecast stock moves', readonly=True)
    graph_stock_move_ids = fields.One2many('stock.move', compute='_compute_graph_stock_move')
    display_reservation = fields.Boolean(string='Display reservation', default=False)
    from_default = fields.Boolean(string='From default', default=False)
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
            On cache les onglets de réservation si on change de produit
        """
        if not self.from_default:
            self.display_reservation = False
        else:
            self.from_default = False
        
        

class display_reservation_week_line(models.TransientModel):
    """ 
        Wizard to show reservations for the selected product for weeks
    """
    _name = 'display.reservation.week.line'
    _description = 'Wizard to show reservations for the selected product for weeks'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    display_reservation_id = fields.Many2one('display.reservation', string='Display reservation', required=True, 
                                             ondelete='cascade')
    year = fields.Char(string='Year', size=4, required=False)
    week = fields.Char(string='Week', size=2, required=False)
    qty = fields.Float(string='Quantity', default=0.0, required=False, digits=dp.get_precision('Product quantity'))



class display_reservation_month_line(models.TransientModel):
    """ 
        Wizard to show reservations for the selected product for months
    """
    _name = 'display.reservation.month.line'
    _description = 'Wizard to show reservations for the selected product for months'
    
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
                ('12', _('December'))
                       ]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    display_reservation_id = fields.Many2one('display.reservation', string='Display reservation', required=True, 
                                             ondelete='cascade')
    year = fields.Char(string='Year', size=4, required=False)
    month = fields.Selection('_month_get', string='Month')
    qty = fields.Float(string='Quantity', default=0.0, required=False, digits=dp.get_precision('Product quantity'),
                       readonly=True)