# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from operator import itemgetter
import openerp.addons.decimal_precision as dp
from openerp.addons.base_openprod.common import _get_month_start, _get_month_stop
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm, ValidationError, UserError
import math
import re
import time
from datetime import datetime, timedelta

class product_consumption(models.Model):
    """ 
    Product consumption 
    """
    _name = 'product.consumption'
    _description = 'Product consumption'
    _rec_name = 'product_id'
    _order = 'year desc, month desc, product_id'
    #===========================================================================
    # COLUMNS
    #===========================================================================
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade', select=True)
    year = fields.Integer(size=4, required=False)
    month = fields.Integer(size=2, required=False)
    qty = fields.Float(required=True, digits=dp.get_precision('Product quantity'))
    
    
    def date_compute(self, year, month):
        if year and month:
            res = [('date', '>=', fields.Datetime.to_string(_get_month_start(year, month))),
                   ('date', '<=', fields.Datetime.to_string(_get_month_stop(year, month))),]
        else:
            now = fields.Datetime.from_string(fields.Datetime.now())
            temp = now - relativedelta(months=24)
            res = [('date', '>=', fields.Datetime.to_string(_get_month_start(temp.year, temp.month))),
                   ('date', '<=', fields.Datetime.to_string(_get_month_stop(now.year, now.month))),]

        return res
    
    
    @api.model
    def compute_all_cron(self):
        return self.compute()
    
    
    @api.multi
    def compute_all_button(self):
        return self.compute()

    
    @api.multi
    def compute_last_button(self):
        now = fields.Datetime.from_string(fields.Datetime.now())
        if now.month == 1:
            year = now.year - 1
            month = 12
        else:
            year = now.year
            month = now.month -1
            
        return self.compute(year, month)

    
    @api.multi
    def compute_line_button(self):
        return self.compute(self.year, self.month, [self.product_id.id])

    
    @api.multi
    def compute_product_button(self):
        return self.compute(product_ids=[self.product_id.id])
    
    
    def get_consumption_vals(self, months, product_id, variance=False):
        p_vals = {'critical_stock': 0.0}
        year = int(time.strftime('%Y'))
        month = int(time.strftime('%m'))
        args = [('product_id', '=', product_id), '|', ('year', '!=', year), ('month', '!=', month)]
        qtys = self.search(args, limit=max(months)).read(['qty'])
        qtys = [q['qty'] for q in qtys]
        for m in months:
            m_qtys = qtys and (len(qtys) > m and qtys[:m] or qtys) or False
            if m_qtys:
                p_vals['consumption_avg_%d'%(m)] = sum(m_qtys) / float(len(m_qtys))
            else:
                p_vals['consumption_avg_%d'%(m)] = 0.0
            
            # Variance
            if variance and m == variance:
                for qty in qtys:
                    p_vals['critical_stock'] += ((qty - p_vals['consumption_avg_%d'%(m)])) ** 2
                
                p_vals['critical_stock'] = math.sqrt(float(p_vals['critical_stock']) / len(qtys)) * 2

        return p_vals
    
            
    def compute(self, year=None, month=None, product_ids=None):
        uom_obj = self.env['product.uom']
        search_args = [('state', '=', 'done'), 
                       ('type', '=', 'out')]
        unlink_args = []
        if month:
            unlink_args.append(('month', '=', month))

        if year:
            unlink_args.append(('year', '=', year))
        
        search_args.extend(self.date_compute(year, month))
        if product_ids:
            search_args.append(('product_id', 'in', product_ids))
            unlink_args.append(('product_id', 'in', product_ids))

        self.search(unlink_args).unlink()
        datas = self.env['stock.move'].search_group(fields=['product_id', 'uom_id', 'uom_qty', 'month', 'year'], 
                                                    groupby=['product_id', 'uom_id', 'month', 'year'], 
                                                    args=search_args,
                                                    sum='uom_qty',
                                                    return_dict=True)
        vals = {}
        if datas:
            # Récupération des UdM
            uoms = {p['id']: p['uom_id'] for p in self.env['product.product'].search(
                                                                           product_ids and [('id', 'in', product_ids)] or []
                                                                           ).read(['uom_id'], load='_classic_write')}
            for data in datas:
                product_id = data['product_id']
                uom_id = data['uom_id']
                key = (product_id, data['year'], data['month'])
                if uoms[product_id] != uom_id:
                    qty = uom_obj._compute_qty(uom_id, data['uom_qty'], uoms[product_id], with_raise=True, with_round=False)
                else:
                    qty = data['uom_qty']
                    
                if key in vals:
                    vals[key] += qty
                else:
                    vals[key] = qty
                    
            for v_key, v_qty in vals.iteritems():
                self.create({
                    'product_id': v_key[0],
                    'year': v_key[1],
                    'month': v_key[2],
                    'qty': v_qty,
                })
            
        if not product_ids:
            product_ids = self.env['product.product'].search([]).ids
            
        vals_keys = vals.keys()
        now = fields.Datetime.from_string(fields.Datetime.now())
        for product_id in product_ids:
            if month and year:
                if (product_id, str(year), str(month)) not in vals_keys:
                    self.create({
                        'product_id': product_id,
                        'year': year,
                        'month': month,
                        'qty': 0.0,
                    })
                    
            else:
                i = 24
                while i:
                    compute_date = now - relativedelta(months=i)
                    temp_year = compute_date.year
                    temp_month = compute_date.month
                    if (product_id, str(temp_year), str(temp_month)) not in vals_keys:
                        self.create({
                            'product_id': product_id,
                            'year': temp_year,
                            'month': temp_month,
                            'qty': 0.0,
                        })
                        
                    i -= 1
            
        
        if product_ids:
            products_rs = self.env['product.product'].browse(product_ids)
        else:
            products_rs = self.env['product.product'].search([])
        
        for product in products_rs:
            try:
                product.write(self.get_consumption_vals([3, 6, 12], product.id, 12))
            except:
                pass
        
        return True

    @api.one
    def copy(self, default=None):
        raise except_orm(_('Error'), _('Replication is prohibited'))
        return super(product_consumption, self).copy(default)
    
    

class product_label_customer(models.Model):
    """ 
    Product label customer 
    """
    _name = 'product.label.customer'
    _description = 'Product label customer'
    _rec_name = 'product_id'
    #===========================================================================
    # COLUMNS
    #===========================================================================
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Partner', required=True, ondelete='cascade')
    label_template_id = fields.Many2one('stock.label.template', string='Label template', required=True, ondelete='cascade')
   
   
   
class product_category(models.Model):
    _inherit = "product.category"
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    common_attribute_ids = fields.Many2many('common.attribute.model', 'category_attribute_rel', 'category_id', 'common_attribute_id', string='Common attributes')
    plan_control_ids = fields.One2many('stock.quality.control', 'category_id',  string='Printed documents')
    
    
    def call_plan_control_modif(self, product_rcs=False, delete=False, ids=False, quality_documents_rs=None):
        """
            Fonction qui permet d'appeler la fonction de synchro des produits et des catégories dans le cas
            des documents imprimés
        """
        syncro_field = 'printed_doc_categ_syncro'
        document_field = 'plan_control_ids'
        doc_obj = self.env['stock.quality.control']
        list_fields = ['type', 'report_id', 'pdf_file']
        self.function_modif_quality_documents(product_rcs, delete, syncro_field, document_field, doc_obj, list_fields, ids=ids, quality_documents_rs=quality_documents_rs)
        return True
    
    
    def modif_type_quality_documents(self, field=None, product_rcs=None, delete=False, ids=False, quality_documents_rs=None):
        if field:
            if field == 'quality_control_ids':
                self.call_quality_control_modif(product_rcs=product_rcs, delete=delete, ids=ids, quality_documents_rs=quality_documents_rs)
            elif field == 'plan_control_ids':
                self.call_plan_control_modif(product_rcs=product_rcs, delete=delete, ids=ids, quality_documents_rs=quality_documents_rs)
            
        return True
    
        

class product_storage_location(models.Model):
    _name = 'product.storage.location'
    _description = 'Product storage location'
    _sql_constraints = [
        ('unique_name', 'unique(product_id,warehouse_id)', 'Error: Impossible to have more than one storage location per warehouse for a product.'),
    ]
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade', select=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True, ondelete='cascade', select=True)
    location_id = fields.Many2one('stock.location', string='Location', required=True, ondelete='restrict')
    
    
    
class product_product(models.Model):
    _inherit = 'product.product'
    _description = 'Product'
    
    
    @api.one    
    def _compute_stock_level(self):
        self.virtual_stock, self.available_stock = self.get_available_stock(return_real_stock=True)
        if self.dual_unit and self.dual_unit_type == 'variable':
            self.available_stock_sec_uom = self.get_stock_level_sec_uom(self.env['stock.warehouse'].search([('included_into_the_stock', '=', True)]).ids)
        else:
            self.available_stock_sec_uom = 0.0
           
           
    @api.one
    def _compute_have_waiting_move(self):
        self.have_waiting_move = True


    def _search_have_waiting_move(self, operator, value):
        product_ids = self.env['stock.move'].search_group(fields=['product_id'], 
                                                          groupby=['product_id'], 
                                                          args=[('type', 'in', ('in', 'out')), 
                                                                ('state', '=', 'waiting')])
        if value:
            operator = 'in'    
        else:
            operator = 'not in'    
            
        return [('id', operator, product_ids)]

    
    @api.model
    def _horizon_type_get(self):
        return [('manual', 'Manual'),
                ('auto', 'Automatic')]

    
    def get_horizon(self):
        return self.horizon


    @api.one
    @api.depends('manual_horizon', 'horizon_type')
    def _compute_horizon(self):
        if self.horizon_type == 'manual':
            if self.manual_horizon >= 0:
                self.horizon = self.manual_horizon
            else:
                self.horizon = self.company_id.horizon
                
        else:
            self.horizon = self.compute_auto_horizon()

        
    @api.one
    def _compute_enhanced_price(self):
        enhanced_price = 0.0
        if self.supply_method == 'buy':
            type_valu = self.type_valuation_purchase
        else:
            type_valu = self.type_valuation_production
        
        svl_obj = self.env['stock.valuation.lot']
        sl_obj =self.env['stock.lot']
        if self.inventory_valuation == 'lot':
            price_total = 0
            qty_total = 0
            # On pondère la valo de tous les lots du produit
            for lot in sl_obj.search([('product_id', '=', self.id)]):
                valuation_rcs = svl_obj.search([('product_id', '=', self.id), ('lot_id', '=', lot.id)], order='year desc, month desc', limit=1)
                if valuation_rcs:
                    qty_total += valuation_rcs.qty_in_stock
                    if type_valu == 'real':
                        price_total += valuation_rcs.price * valuation_rcs.qty_in_stock
                    else:
                        price_total += valuation_rcs.price_theo * valuation_rcs.qty_in_stock
            
            enhanced_price = qty_total and price_total / qty_total or 0
        else:
            valuation_rcs = self.env['stock.valuation'].search([('product_id', '=', self.id)], order='year desc, month desc', limit=1)
            if valuation_rcs:
                if type_valu == 'real':
                    enhanced_price = valuation_rcs.price
                else:
                    enhanced_price = valuation_rcs.price_theo
        
        self.enhanced_price = enhanced_price
 
 
    @api.one
    @api.depends('version_historical_ids')
    def _compute_version_product(self):
        self.version_product = False
        current_date = fields.Date.today()
        i = 0
        while i < len(self.version_historical_ids) and self.version_historical_ids[i].start_date <= current_date:
            self.version_product = self.version_historical_ids[i].version
            i += 1
            
    
    #===========================================================================
    # COLUMNS
    #=========================================================================== 
    location_id = fields.Many2one('stock.location', string='Location', required=False, ondelete='restrict')
    available_stock = fields.Float(string='Stock (T0)', compute='_compute_stock_level', help="Current quantity of products."
                "In a Stock Location context, this includes goods stored in this Location, or any of its children."
                "In a Warehouse context, this includes goods stored in this Warehouse Stock Location, or any of its children."
                "In a Shop context, this includes goods stored in the Warehouse Stock Location of this Shop, or any of its children."
                "Otherwise, this includes goods stored in any Stock Location typed as 'internal'.")
    virtual_stock = fields.Float(string='Stock (T inf)', compute='_compute_stock_level', help="Forecast quantity (computed as "
                 "Amount of stock - Outgoing quantity + Incoming quantity). In a Stock Location context, this includes goods stored "
                 "in this Location, or any of its children. In a Warehouse context, this includes goods stored in this Warehouse "
                 "Stock Location, or any of its children. In a Shop context, this includes goods stored in the Warehouse Stock "
                 "Location of this Shop, or any of its children. Otherwise, this includes goods stored in any Stock Location typed "
                 "as 'internal'.")
    available_stock_sec_uom = fields.Float(string='Stock sec UoM (T0)', compute='_compute_stock_level', help="In a Stock Location "
                 "context, this includes goods stored in this Location, or any of its children. In a Warehouse context, this "
                 "includes goods stored in this Warehouse Stock Location, or any of its children. In a Shop context, this includes "
                 "goods stored in the Warehouse Stock Location of this Shop, or any of its children. Otherwise, this includes goods "
                 "stored in any Stock Location typed as 'internal'.")
    storage_location_id = fields.Many2one('stock.location', string='Storage location', required=False, ondelete='restrict', domain=[('usage', '=', 'internal')])
    storage_location_ids = fields.One2many('product.storage.location', 'product_id',  string='Storage locations')
    orderpoint_ids = fields.One2many('stock.warehouse.orderpoint', 'product_id',  string='Stock rules')
    is_always_available = fields.Boolean(string='Always available', default=False, help='If this field is checked, stock moves of this product will be always available')
    plan_control_ids = fields.One2many('stock.quality.control', 'product_id',  string='Control and plans')
    have_waiting_move = fields.Boolean(string='Have move waiting', compute='_compute_have_waiting_move', search='_search_have_waiting_move')
    low_procurement = fields.Integer(default=lambda self: self.env['stock.config.settings'].get_param('low_procurement'), required=False, help='For a product, during the material requirement planning: If ([needed quantity] / [last out move quantity]) < ([this parameter] / 100), the procurement order will be in "low procurement"')
    exclude_of_mrp = fields.Boolean(string='Exclude of the MRP', default=False, required=False, help='Exclude the product of the Material Requirement Planning')
    exclude_category_attribute = fields.Boolean(default=False)
    printed_doc_categ_syncro = fields.Boolean(string='Synchronize with the printed documents of the category.', default=True)
    is_int = fields.Boolean(string='Int', default=False)
    # Rangement
    row = fields.Char(string='Row', size=32, required=False)
    corridor = fields.Char(string='Corridor', size=32, required=False)
    shelf = fields.Char(string='Shelf', size=32, required=False)
    
    
    # Label
    label_template_id = fields.Many2one('stock.label.template', string='Label template', required=False, ondelete='restrict')
    version_historical_ids = fields.One2many('product.version.historical', 'product_id', string='Version historical')
    version_product = fields.Char(string='Version', size=32, required=False, compute='_compute_version_product')
    
    
    # Consumption
    manual_horizon = fields.Integer(string='Horizon', default=-1, required=False, help="Provide -1 to take the company's default horizon")
    horizon_type = fields.Selection('_horizon_type_get', string='Horizon type', default='manual')
    horizon = fields.Integer(string='Horizon', compute='_compute_horizon')
    last_procurement = fields.Datetime()
    consumption_avg_3 = fields.Float(string='Consumption AVG 3', digits=dp.get_precision('Product quantity'))
    consumption_avg_6 = fields.Float(string='Consumption AVG 6', digits=dp.get_precision('Product quantity'))
    consumption_avg_12 = fields.Float(string='Consumption AVG 12', digits=dp.get_precision('Product quantity'))
    critical_stock = fields.Float(string='Critical stock', digits=dp.get_precision('Product quantity'))

    # Attributs
    common_attribute_ids = fields.Many2many('common.attribute.model', 'attribute_product_rel', 'product_id', 'common_attribute_id', string='Common attributes')    
    enhanced_price = fields.Float(string='Enhanced price', compute='_compute_enhanced_price', digits=dp.get_precision('Account'))
    
    #===========================================================================
    # Onchange
    #===========================================================================
        
    @api.onchange('type')
    def _onchange_type_product(self):
        """
            Au changement du type, si le type est service par défaut la gestion des réceptions et livraisons est à Vrai
        """
        if self.type == 'service':
            self.manage_service_receipt = True
            self.manage_service_delivery = True
            self.is_always_available = True
            
        
    def compute_horizon_date(self):
        return self.env.user.company_id.partner_id.calendar_id and self.env.user.company_id.partner_id.calendar_id.get_date(fields.Date.today(), self.horizon) or False
        

    def get_default_supply_delay_purchase(self, return_date=False, hours=False):
        if return_date:
            return 0.0, False
        else:
            return 0.0
        
    
    def get_default_supply_delay_mrp(self, return_date=False, hours=False):
        if return_date:
            return 0.0, False
        else:
            return 0.0
    
    
    def get_default_supply_delay(self, return_date=False, hours=False):
        if self.supply_method == 'buy':
            return self.get_default_supply_delay_purchase(return_date=return_date, hours=hours)
        elif self.supply_method == 'produce':
            return self.get_default_supply_delay_mrp(return_date=return_date, hours=hours)
        else:
            if return_date:
                return 0.0, False
            else:
                return 0.0

    
    def compute_auto_horizon(self):
        """
            Horizon = délai d'appro * 2 avec un minimum de 10 pardéfaut
        """
        param_obj = self.env['stock.config.settings']
        return max(self.get_default_supply_delay() * int(param_obj.get_param('multi_supply_delay_horizon') or 2), int(param_obj.get_param('min_horizon') or 10))


    def get_storage_location(self, warehouse_id=False):
        """
            Retourne l'emplacement de stockage d'un produit en fonction de son entrepôt
            :type: self: product.product            
            :param warehouse_id: ID de l'entrepôt. Si vide, c'est l'entrepôt de la société de l'utilisateur qui est utilisé
            :type warehouse_id: integer
            :return: Emplacement de stockage
            :rtype: recordset: stock.location
        """
        if not warehouse_id:
            warehouse_id = self.env.user.company_id.warehouse_id.id
        
        if warehouse_id:
            res = self.env['product.storage.location'].search([
                ('warehouse_id', '=', warehouse_id),
                ('product_id', '=', self.id),
            ], limit=1).location_id
        else:
            res = self.env['stock.location']
            
        return res
        
    
    def get_common_attribute_ids(self):
        return self.exclude_category_attribute and self.common_attribute_ids or self.common_attribute_ids | self.categ_id.common_attribute_ids

        
    def stock_level_rectification(self):
        self.env.cr.execute("""
            UPDATE 
              stock_level sl 
            SET 
             uom_qty = slr.dynamic_qty
            FROM 
              stock_level_report slr 
            WHERE 
              sl.id = slr.sl_id AND 
              slr.static_qty <> slr.dynamic_qty AND 
              slr.product_id IN %s 
          """, (tuple([self.id]), ))
        return True
        
        
    def get_available_stock(self, with_horizon=False, from_date=False, to_date=False, return_real_stock=False, is_forecast=False, warehouse_id=False):    
        move_obj = self.env['stock.move']
        uom_obj = self.env['product.uom']
        warehouse_obj = self.env['stock.warehouse']
        # Si on ne cherche pas sur un entrepôt en particulier, on prend tous les entrepôts pour lesquels le stock est pris en compte
        if warehouse_id:
            warehouse_ids = [warehouse_id]
        else:
            warehouse_ids = warehouse_obj.search([('included_into_the_stock', '=', True)]).ids
            
        res = real_stock = self.get_stock_level(warehouse_ids=warehouse_ids)
        product_uom_id = self.uom_id.id
        common_args = [('state', '=', 'waiting'), ('product_id', '=', self.id), ('warehouse_id', 'in', warehouse_ids)]
        if not is_forecast:
            common_args.append(('is_forecast', '=', False))

        in_args = common_args + [('type', '=', 'in')]
        out_args = common_args + [('type', '=', 'out')]
        if with_horizon:
            horizon_date = self.compute_horizon_date()
        else:
            horizon_date = False

        if from_date:
            out_args += [('date', '>=', from_date)]
            
        if to_date:
            out_args += [('date', '<=', to_date)]
            in_args += [('date', '<=', to_date)]
            
        if horizon_date:
            out_args += [('date', '<=', horizon_date)]
        
        in_move_qtys = move_obj.search_group(fields=['uom_qty', 'uom_id'], 
                                             groupby=['uom_id'], 
                                             args=in_args,
                                             sum='uom_qty',
                                             return_dict=True)
        for in_move_qty in in_move_qtys:
            if product_uom_id == in_move_qty['uom_id']:
                res += in_move_qty['uom_qty']
            else:
                res += uom_obj._compute_qty(in_move_qty['uom_id'], in_move_qty['uom_qty'], to_uom_id=product_uom_id, with_raise=True, with_round=False)

        out_move_qtys = move_obj.search_group(fields=['uom_qty', 'uom_id'], 
                                              groupby=['uom_id'], 
                                              args=out_args,
                                              sum='uom_qty',
                                              return_dict=True)
        for out_move_qty in out_move_qtys:
            if product_uom_id == out_move_qty['uom_id']:
                res -= out_move_qty['uom_qty']
            else:
                res -= uom_obj._compute_qty(out_move_qty['uom_id'], out_move_qty['uom_qty'], to_uom_id=product_uom_id, with_raise=True, with_round=False)
            
        return return_real_stock and (res, real_stock) or res
        
        
    def get_sinfo(self, partner_id=False, property_ids=False, state_dev=False):
        return []


    def get_cinfo(self, partner_id=False, property_ids=False):
        return False
    
    
    def get_associate_procurement(self):
        self.env.cr.execute("""SELECT 
                                 p1.id, 
                                 (SELECT MIN(p2.id) FROM procurement_order p2 WHERE p1.sol_id = p2.sol_id AND p1.product_id = p2.product_id AND p2.state != 'done') 
                               FROM 
                                 procurement_order p1 
                               WHERE 
                                 p1.product_id = %s AND 
                                 p1.state != 'done' AND 
                                 p1.sol_id IS NOT NULL"""%(self.id))
        
        res = self.env.cr.fetchall()
        return {r[0]: r[1] for r in res}
    
    
    def get_reserved_stock_level_by_proc_query(self, type, clause, groupby):
        return """
        SELECT min(p.id) as procurement_id, SUM(sm.reserved_qty) AS reserved_qty
            FROM stock_move sm, procurement_order p
                WHERE sm.procurement_id = p.id
                    AND p.state != 'done'
                    AND sm.procurement_id IS NOT NULL
                    AND sm.state in %s
                    AND sm.product_id = %s
                    AND sm.is_forecast != true
                    AND sm.type = '""" + type + "' " + clause + """ 
                    GROUP BY sm.product_id """ + groupby
        
    
    def get_origin_fields(self):
        return []
    
        
    def get_reserved_stock_level_by_proc(self, associate_proc, states=('done', )):
        """
            Calcul du niveau de stock reservé pour un produit
            :type: self: product.product
            :return: Niveau de stock réservé à T0 par procurement
            :rtype: dict
        """
        # Gestion a la commande: groupement des procurement d'une même SOL ou d'un même OT pour gerer le cas plusieurs procurement pour une ligne de vente (annulation)
        origin_fields = self.get_origin_fields() # origin_fields = ['sol_id', 'origin_wo_id']
        copy_origin_fields = origin_fields[:]
        last_origin_field = False
        if copy_origin_fields:
            if len(copy_origin_fields) > 1:
                last_origin_field = copy_origin_fields[-1]
            else:
                last_origin_field = copy_origin_fields[0]
                
            clause = ' '.join([' AND p.%s IS NULL'%(f) for f in copy_origin_fields])
        else:
            clause = ''
            
        self.env.cr.execute(self.get_reserved_stock_level_by_proc_query('in', clause, ', p.id'), (tuple(states, ), self.id))
        qty_by_proc = self.env.cr.dictfetchall()
        for origin_field in origin_fields:
            groupby = ', p.%s'%(origin_field)
            if (last_origin_field and origin_field == last_origin_field) or not last_origin_field:
                self.env.cr.execute(self.get_reserved_stock_level_by_proc_query('in', ' AND p.%s IS NOT NULL'%(origin_field), groupby), (tuple(states, ), self.id))
            else:
                self.env.cr.execute(self.get_reserved_stock_level_by_proc_query('in', ' AND p.%s IS NOT NULL AND p.%s IS NULL'%(origin_field, last_origin_field), groupby), (tuple(states, ), self.id))
                
            qty_by_proc.extend(self.env.cr.dictfetchall())

        if qty_by_proc:
            res = {x['procurement_id'] in associate_proc and associate_proc[x['procurement_id']] or x['procurement_id']: x['reserved_qty'] for x in qty_by_proc}
        else:
            res = {}

        if res:
            self.env.cr.execute(self.get_reserved_stock_level_by_proc_query('out', clause, ', p.id'), (tuple(states, ), self.id))
            qty_by_proc_out = self.env.cr.dictfetchall()
            for origin_field in origin_fields:
                groupby = ', p.%s'%(origin_field)
                if last_origin_field and origin_field == last_origin_field:
                    self.env.cr.execute(self.get_reserved_stock_level_by_proc_query('out', ' AND p.%s IS NOT NULL'%(origin_field), groupby), (tuple(states, ), self.id))
                else:
                    self.env.cr.execute(self.get_reserved_stock_level_by_proc_query('out', ' AND p.%s IS NOT NULL AND p.%s IS NULL'%(origin_field, last_origin_field), groupby), (tuple(states, ), self.id))
                    
                qty_by_proc_out.extend(self.env.cr.dictfetchall())

            for x in qty_by_proc_out:
                proc_id = x['procurement_id'] in associate_proc and associate_proc[x['procurement_id']] or x['procurement_id']
                if x['reserved_qty'] and proc_id in res:
                    res[proc_id] -= x['reserved_qty']
                    
        return res
    
    
    def get_reserved_stock_level(self, warehouse_id=False):
        """
            Calcul du niveau de stock reservé pour un produit
            :type: self: product.product
            :return: Niveau de stock réservé à T0
            :rtype: float
        """
        move_obj = self.env['stock.move']
        # TODO Arthur: procurement_id.state: pas bon passer en requete ou auto_join
        common_args = [('state', '=', 'done'), ('product_id', '=', self.id), ('procurement_id', '!=', False), ('procurement_id.state', '!=', 'done')]
        if warehouse_id:
            common_args.append(('warehouse_id', '=', warehouse_id))
        
        in_args = common_args + [('type', '=', 'in')]
        out_args = common_args + [('type', '=', 'out')]
        
        in_reserved_qty = move_obj.search_group(fields=['reserved_qty'], 
                                             groupby=['product_id'], 
                                             args=in_args,
                                             sum='reserved_qty')
        
        # Il faut enlever les qty parties du stock reserve
        out_reserved_qty = move_obj.search_group(fields=['reserved_qty'], 
                                                 groupby=['product_id'], 
                                                 args=out_args,
                                                 sum='reserved_qty')        
        
        if in_reserved_qty and out_reserved_qty:
            res = in_reserved_qty[0] - out_reserved_qty[0]
        elif in_reserved_qty :
            res = in_reserved_qty[0]
        else:
            res = 0.0   
            
        return res
    
    def get_stock_level(self, consider_reservation=False, warehouse_ids=False, without_label=False):
        """
            Calcul du niveau de stock
            :type: self: product.product
            :return: Niveau de stock à T0
            :rtype: float
        """
        search_args = [('product_id', '=', self.id)]
        if warehouse_ids:
            search_args.append(('warehouse_id', 'in', warehouse_ids))
            
        res = self.env['stock.level'].search_group(fields=['uom_qty'], 
                                                   groupby=['product_id'], 
                                                   args=search_args,
                                                   sum='uom_qty')
        
        res = res and res[0] or 0
        if consider_reservation:
            res -= (self.get_reserved_stock_level() or 0.0)
        
        if without_label:
            where_query = 'sm.product_id = %s'
            where_args = [self.id]
            if warehouse_ids:
                where_query += ' AND sm.warehouse_id IN %s'
                where_args.append(tuple(warehouse_ids, ))
            
            self.env.cr.execute(
            """ SELECT 
                  sum(sml.uom_qty) 
                FROM 
                  stock_move_label sml JOIN stock_move sm ON sml.move_id = sm.id 
                WHERE
                  sm.state = 'waiting' AND
                  sm.type = 'out' AND
                  sm.trigger_supply != 'make_to_order' AND
                  %s
            """%(where_query), where_args)
            without_label_res = self.env.cr.fetchone()
            res -= without_label_res and without_label_res[0] or 0.0
        
        return res
    
    
    def get_stock_level_sec_uom(self, consider_reservation=False):
        """
            Calcul du niveau de stock en seconde UdM
            :type: self: product.product
            :return: Niveau de stock en seconde UdM à T0
            :rtype: float
        """
        stock_level = self.env['stock.level'].search([('product_id', '=', self.id)], limit=1)
        return stock_level and stock_level.sec_uom_qty or 0.0
    
    
    def get_date_last_stock_min_warehouse(self, search_criteria):
        search_criteria.append(('type', 'in', ('in', 'out')))
        stock_qty = self.get_stock_level()
        # Crée un tableau avec la quantité d'article de mouvement par jour
        today = fields.Date.today()
        qty_per_day = {today: stock_qty}
        for move in self.env['stock.move'].search(search_criteria, order='date'):
            from_date = move.date[:10]
            if move.type == 'in':
                # Les mouvements anterieurs ou égale à AJD sont considérés comme fait
                if from_date <= today:
                    qty_per_day[today] += move.get_product_uom_qty()
                else:
                    if from_date in qty_per_day:
                        qty_per_day[from_date] += move.get_product_uom_qty()
                    else:
                        qty_per_day[from_date] = move.get_product_uom_qty()
            elif move.type == 'out':
                # Les mouvements anterieurs ou égale à AJD sont considérés comme fait
                if from_date <= today:
                    qty_per_day[today] -= move.get_product_uom_qty()
                else:
                    if from_date in qty_per_day:
                        qty_per_day[from_date] -= move.get_product_uom_qty()
                    else:
                        qty_per_day[from_date] = -move.get_product_uom_qty()
                    
        return qty_per_day
    
    
    def get_date_last_stock_min_location(self, location, search_criteria):
        location_ids = self.env['stock.location'].search([('location_id', 'child_of', location.id)])
        search_criteria.extend('|',
                               '&',('location_id', 'in', location_ids),
                               '!',('location_dest_id', 'in', location_ids),
                               '&','!',('location_id', 'in', location_ids),
                               ('location_dest_id', 'in', location_ids))
        stock_qty = 0.0
        # Crée un tableau avec la quantité d'article de mouvement par jour
        today = fields.Date.today()
        qty_per_day = {today: stock_qty}
        for move in self.env['stock.move'].search(search_criteria, order='date'):
            from_date = move.date[:10]
            # Entrant
            if set(location_ids.ids).issuperset(move.location_dest_id.id):
                # Les mouvements anterieurs ou égale à AJD sont considérés comme fait
                if from_date <= today:
                    qty_per_day[today] += move.get_product_uom_qty()
                else:
                    if from_date in qty_per_day:
                        qty_per_day[from_date] += move.get_product_uom_qty()
                    else:
                        qty_per_day[from_date] = move.get_product_uom_qty()
            else:              
                # Sortant
                # Les mouvements anterieurs ou égale à AJD sont considérés comme fait
                if from_date <= today:
                    qty_per_day[today] -= move.get_product_uom_qty()
                else:
                    if from_date in qty_per_day:
                        qty_per_day[from_date] -= move.get_product_uom_qty()
                    else:
                        qty_per_day[from_date] = -move.get_product_uom_qty()
                    
        return qty_per_day
    
    
    def get_date_last_stock_min(self, location, qty_request, date_stop=False, inverse=False, is_forecast=False):
        """ 
            Retourne la derniere date à laquelle la quantité en stock passe sous la quantité passée en paramètre  
        """
        
        if isinstance(location, int):
            location = self.env['stock.location'].browse(location)
        
        # Critères de recherche
        search_criteria = [('product_id', '=', self.id),
                           ('state', '=', 'waiting'),
                           ('is_forecast', '=', is_forecast)]
        # Prise en compte de la date max
        if date_stop:
            search_criteria.insert(0, ('date', '<=', date_stop))

        # Si l'emplacement est l'emplacement de l'entrepot: séléction des in/out
        if location.id == self.env.user.company_id.warehouse_id.stock_location_id.id:
            qty_per_day = self.get_date_last_stock_min_warehouse(search_criteria)
        # Si l'emplacement n'est pas l'emplacement de l'entrepot: séléction des entrants/sortants de l'emplacement
        else:
            qty_per_day = self.get_date_last_stock_min_warehouse(location, search_criteria)
            
        qty_per_day = sorted(qty_per_day.items(), key=itemgetter(0))
        # Cheche la derniere date ou le stock passe en dessous de la regle min
        date_min = None
        qty_day_future = 0
        if inverse:
            maxi = False
            for qty_of_day in qty_per_day:
                qty_day_future += qty_of_day[1]
                if qty_request <= qty_day_future and not maxi:
                    date_min = qty_of_day[0]
                    mini = True
                elif qty_request > qty_day_future:
                    mini = False
        else:
            mini = False
            for qty_of_day in qty_per_day:
                qty_day_future += qty_of_day[1]
                if qty_request > qty_day_future and not mini:
                    date_min = qty_of_day[0]
                    mini = True
                elif qty_request < qty_day_future:
                    mini = False
                
        return date_min
    
    
    def get_orderpoint(self):
        today = fields.Date.today()
        return self.env['stock.warehouse.orderpoint'].search([
                                                         '|', ('start_date', '<=', today), ('start_date', '=', False), 
                                                         '|', ('end_date', '>=', today), ('end_date', '=', False), 
                                                         ('product_id', '=', self.id)
                                                             ])            


    def _simulate_availability_buy(self, qty, supplier_id, start_date):
        return False
    
    
    def _simulate_availability_produce(self, qty, supplier_id, option_ids, start_date):
        return False
    
        
    def simulate_availability(self, qty, supplier_id, option_ids, start_date):
        self.ensure_one()
        if self.supply_method == 'buy':
            return self._simulate_availability_buy(qty, supplier_id,start_date)
        elif self.supply_method == 'produce':
            return self._simulate_availability_produce(qty, supplier_id, option_ids, start_date)


    def do_procurement(self):
        """
            Lancement de l'approvisionnement du produit. Création d'un procurement si besoin
            :type: self: product.product
            :return: Procurement créé
            :rtype: producrement.order
        """
        op_rs = self.get_orderpoint()
        if op_rs:
            res = op_rs.do_procurement()
        else:
            res = self.do_procurement_auto()
            
        return res
    
    
    def do_procurement_auto(self, warehouse_location_rs=False, from_mrp=False):
        """
            Lancement de l'approvisionnement du produit sur stock négatif (pas de règle de stock)
            :type: self: product.product
            :return: Procurement créé
            :rtype: producrement.order
        """
        product_rs = self
        horizon_date = product_rs.compute_horizon_date()
        virtual_qty, real_qty = product_rs.get_available_stock(to_date=horizon_date, return_real_stock=True)
        if virtual_qty < 0.0:
            proc_rs = self.env['procurement.order'].create_procurement({
                    'product_id': product_rs.id, 
                    'needed_date': product_rs.get_date_last_stock_min(warehouse_location_rs or self.env.user.company_id.warehouse_id.stock_location_id, 0.0, date_stop=horizon_date), 
                    'trigger_supply': 'make_to_plan', 
                    'supply_method': product_rs.supply_method, 
                    'user_id': self.env.user.id, 
                    'from_procurement': True, 
                    'from_mrp': from_mrp, 
                    'low_procurement': product_rs.get_is_low_proc(-virtual_qty),
                    'log': 'Reason: Negative stock\nVirtual stock on the horizon qty: %.2f\nReal stock qty: %.2f'%(virtual_qty, real_qty), 
                            })
        else:
            proc_rs = self.env['procurement.order']
            
        return proc_rs


    def get_covers_move_ids(self, type, product_id, company_id, sorting_date, warehouse_id, track_label=False):
        """
            Renvoie les ids des mouvements à calculer
        """
        if type == 'out' and track_label:
            query = """
                SELECT 
                  sm.id, sum(sml.uom_qty)
                FROM 
                  stock_move sm LEFT JOIN stock_move_label sml ON sm.id = sml.move_id
                WHERE 
                  sm.type = '%s' AND
                  sm.product_id = %s AND
                  sm.company_id = %s AND
                  sm.warehouse_id = %s AND
                  sm.uom_qty > 0 AND
                  sm.is_forecast != true AND
                  sm.state = 'waiting'
                GROUP BY 
                  sm.id
                          
                ORDER BY sm.%s ASC
            """%(type, product_id, company_id, warehouse_id, sorting_date)
        else:
            query = """
                SELECT 
                  id, 0.0
                FROM 
                  stock_move 
                WHERE 
                  type = '%s' AND
                  product_id = %s AND
                  company_id = %s AND
                  warehouse_id = %s AND
                  uom_qty > 0 AND
                  is_forecast != true AND
                  state = 'waiting'
                          
                ORDER BY %s ASC
            """%(type, product_id, company_id, warehouse_id, sorting_date)
        self.env.cr.execute(query)
        res = self.env.cr.fetchall()
        if res:
            res_ids = [x[0] for x in res]
            res_dict = {x[0]: x[1] for x in res}
        else:
            res_ids = []
            res_dict = {}
            
        return res_ids, res_dict
    
    
    def delete_move_cover_rel(self, covers_type, warehouse_ids):      
        self.env.cr.execute("""DELETE FROM 
                                     stock_move_cover_rel rel
                                   WHERE
                                     product_id IS null OR
                                     in_move_id IN (SELECT id FROM stock_move WHERE product_id IN %s AND warehouse_id IN %s)
                                     """, (tuple(self.ids), tuple(warehouse_ids), ))
        return True
    
    def cover_compute(self, covers_type=False, with_delete_move_cover_rel=True, warehouse_rs=False):
        """
            Mise à jour de toutes les couvertures pour un produit
            :type: self: product.product
            :return: True
            :rtype: boolean
        """
        company = self.env.user.company_id
        sorting_date = company.cover_sorting_date
        move_obj = self.env['stock.move']
        uom_obj = self.env['product.uom']
        picking_obj = self.env['stock.picking']
        warehouse_obj = self.env['stock.warehouse']
#         cover_rel_obj = self.env['stock.move.cover.rel']
        fields_to_read = [sorting_date, 'uom_id', 'uom_qty', 'date_expected', 'picking_id', 'reserved_qty', 'procurement_id', 'trigger_supply', 'is_confirmed']
        picking_to_up = []
        warehouse_ids = warehouse_rs and warehouse_rs.ids or warehouse_obj.search([]).ids
        # RAZ
        if with_delete_move_cover_rel:
            self.delete_move_cover_rel(covers_type, warehouse_ids)
        
        insert_query = """INSERT INTO stock_move_cover_rel 
                            (in_move_id, out_move_id, product_id, cover_qty, in_cover_percent, out_cover_percent) 
                            VALUES (%s, %s, %s, %s, %s, %s)"""
                              
        in_update_query = """UPDATE stock_move 
                               SET covers_move_percent = %s, covers_move_qty = %s, covers_stock_percent = %s, covers_stock_qty = %s, 
                                   out_date = %s, color_priority_need = %s, availability = %s, in_delta = %s
                                 WHERE id = %s"""
        out_update_query = """ UPDATE stock_move 
                                 SET covered_by_stock_percent = %s, covered_by_stock_qty = %s, covered_by_move_percent = %s, covered_by_move_qty = %s, 
                                     not_covered_percent = %s, not_covered_qty = %s, in_date = %s, color_priority_need = %s, out_delta = %s, availability = %s,
                                     is_confirmed = %s
                                   WHERE id = %s"""
                                  
        color = self.env['stock.alert.color'].search([('is_active', '=', True)], limit=1)
        for product in self:
            if not product.is_int:
                for warehouse_id in warehouse_ids:
                    procurement_in_moves = {}
                    procurement_out_moves = {}
                    associate_proc = product.get_associate_procurement()
                    round_factor = len(str(product.uom_id.rounding)) - 2
                    product_uom = product.uom_id
                    # Récupération de tous les mouvements entrants en cours
                    in_move_ids, in_move_res = self.get_covers_move_ids('in', product.id, company.id, sorting_date, warehouse_id)
                    if in_move_ids:
                        in_write = {}
                        in_moves = move_obj.browse(in_move_ids).read(fields_to_read, load='_classic_write')
#                        in_moves = move_obj.browse(in_move_ids).read_light(fields_to_read)
                        for in_move in in_moves:
                            # Dictionaire de mise à jour
                            in_write[in_move['id']] = {'covers_move_percent': 0.0,
                                                       'covers_move_qty': 0.0,
                                                       'covers_stock_percent': 100.0,
                                                       'covers_stock_qty': in_move['uom_qty'],
                                                       'out_date': None,
                                                       'color_priority_need': 0,
                                                       'is_confirmed': in_move['is_confirmed'],
                                                       'availability': 100.0,
                                                       'in_delta': 0}
                            # Si UdM différent: conversion
                            if in_move['uom_id'] != product_uom.id:
                                qty = uom_obj._compute_qty_obj(uom_obj.browse(in_move['uom_id']), in_move['uom_qty'], product_uom)
                            else:
                                qty = in_move['uom_qty']
                            
                            if in_move['procurement_id']:
                                in_move_proc_id = in_move['procurement_id'] in associate_proc and associate_proc[in_move['procurement_id']] or in_move['procurement_id']
                                if in_move_proc_id in procurement_in_moves:
                                    procurement_in_moves[in_move_proc_id].append(in_move)
                                else:
                                    procurement_in_moves[in_move_proc_id] = [in_move]
                                                    
                            if in_move['picking_id']:
                                picking_to_up.append(in_move['picking_id'])
                                
                            in_move['uom_qty'] = qty - in_move['reserved_qty'] 
                            in_move['init_uom_qty'] = qty
                    else:
                        in_moves = False
                        in_write = {}
                        
                    # Récupération de tous les mouvements sortants en cours
                    out_move_ids, out_move_res = self.get_covers_move_ids('out', product.id, company.id, sorting_date, warehouse_id, product.track_label)
                    if out_move_ids:
                        out_write = {}
                        out_moves = move_obj.browse(out_move_ids).read(fields_to_read, load='_classic_write')
#                         out_moves = move_obj.browse(out_move_ids).read_light(fields_to_read)
                        for out_move in out_moves[:]:
                            # Dictionaire de mise à jour
                            out_vals = {'covered_by_move_percent': 0.0,
                                        'covered_by_move_qty': 0.0,
                                        'not_covered_percent': 0.0,
                                        'not_covered_qty': 0.0,
                                        'uom_qty': out_move['uom_qty'],
                                        'trigger_supply': out_move['trigger_supply'],
                                        'in_date': None,
                                        'color_priority_need': 0,
                                        'out_delta': 0,
                                        'label_qty': (out_move['trigger_supply'] != 'make_to_order') and out_move_res.get(out_move['id'], 0.0) or 0.0,
                                        'is_confirmed': True}
                            if product.is_always_available:
                                out_vals['covered_by_stock_percent'] = 100.0
                                out_vals['covered_by_stock_qty'] = out_move['uom_qty']
                            else:
                                out_vals['covered_by_stock_percent'] = 0.0
                                out_vals['covered_by_stock_qty'] = 0.0

                            out_write[out_move['id']] = out_vals
                            # Si UdM différent: conversion
                            if out_move['uom_id'] != product_uom.id:
                                qty = uom_obj._compute_qty_obj(uom_obj.browse(out_move['uom_id']), out_move['uom_qty'], product_uom)
                            else:
                                qty = out_move['uom_qty']
                            
                            if out_move['procurement_id']:
                                out_move_proc_id = out_move['procurement_id'] in associate_proc and associate_proc[out_move['procurement_id']] or out_move['procurement_id']
                                if out_move_proc_id in procurement_out_moves:
                                    procurement_out_moves[out_move_proc_id].append(out_move)
                                else:
                                    procurement_out_moves[out_move_proc_id] = [out_move]
                                              
                            if out_move['picking_id']:
                                picking_to_up.append(out_move['picking_id'])
                                
                            out_move['uom_qty'] = qty
                            out_move['init_uom_qty'] = qty
    
                    else:
                        out_moves = False
                        out_write = {}

                        
                    # Matière toujours disponible
                    if not product.is_always_available:
                        cover_rel_dict = {}
                        for in_move in in_move_ids:
                            for out_move in out_move_ids:
                                cover_rel_dict[in_move, out_move] = {'in_move_id': in_move, 
                                                                     'out_move_id': out_move, 
                                                                     'product_id': product.id,
                                                                     'cover_qty': 0.0, 
                                                                     'in_cover_percent': 0.0,
                                                                     'out_cover_percent': 0.0}
                            
                        #===============================================================
                        # COUVERTURE PAR LE STOCK
                        #===============================================================
                        # Stock réservé
                        for procurement_id, reserved_qty in product.get_reserved_stock_level_by_proc(associate_proc).iteritems():
                            while reserved_qty > 0.0:
                                if not procurement_out_moves.get(procurement_id, False):
                                    break
                                
                                prev_qty = reserved_qty
                                reserved_qty -= procurement_out_moves[procurement_id][0]['reserved_qty']
                                # Si le stock réservé couvre totalement le mouvement OUT: 100%
                                if reserved_qty >= 0:
                                    out_write[procurement_out_moves[procurement_id][0]['id']]['covered_by_stock_percent'] += procurement_out_moves[procurement_id][0]['reserved_qty'] * 100 / procurement_out_moves[procurement_id][0]['init_uom_qty']
                                    out_write[procurement_out_moves[procurement_id][0]['id']]['covered_by_stock_qty'] += procurement_out_moves[procurement_id][0]['reserved_qty']
                                    del procurement_out_moves[procurement_id][0]
                                # Si le stock réservé ne couvre pas totalement le mouvement OUT: x%
                                else:
                                    procurement_out_moves[procurement_id][0]['reserved_qty'] -= prev_qty
                                    out_write[procurement_out_moves[procurement_id][0]['id']]['covered_by_stock_percent'] += prev_qty * 100 / procurement_out_moves[procurement_id][0]['init_uom_qty']
                                    out_write[procurement_out_moves[procurement_id][0]['id']]['covered_by_stock_qty'] += prev_qty

                        if out_moves:
                            out_moves = [m for m in out_moves if m['trigger_supply'] != 'make_to_order']
                            
                        # Stock non réservé
                        if out_moves:
                            # Mouvements avec étiquettes associées
                            if product.track_label:
                                index_to_del = []
                                for i in range(len(out_moves)):
                                    if out_moves[i]['id'] in out_write and out_write[out_moves[i]['id']]['label_qty']:
                                        out_moves[i]['uom_qty'] -= out_write[out_moves[i]['id']]['label_qty']
                                        out_write[out_moves[i]['id']]['covered_by_stock_percent'] += out_write[out_moves[i]['id']]['label_qty'] * 100 / out_moves[i]['init_uom_qty']
                                        out_write[out_moves[i]['id']]['covered_by_stock_qty'] += out_write[out_moves[i]['id']]['label_qty']
                                        out_write[out_moves[i]['id']]['label_qty'] = 0.0
                                        if out_moves[i]['uom_qty'] <= 0.0:
                                            index_to_del.append(i)
                                
                                index_to_del.reverse()
                                for j in index_to_del:
                                    del out_moves[j]
                                
                            stock_qty = product.get_stock_level(True, [warehouse_id], without_label=product.track_label)
                            while stock_qty > 0.0:
                                if not out_moves:
                                    break
                                
                                if out_moves[0]['trigger_supply'] == 'make_to_order':
                                    del out_moves[0]
                                    continue
                                
                                prev_qty = stock_qty
                                stock_qty -= out_moves[0]['uom_qty']
                                # Si le stock couvre totalement le mouvement OUT: 100%
                                if stock_qty >= 0:
                                    out_write[out_moves[0]['id']]['covered_by_stock_percent'] += out_moves[0]['uom_qty'] * 100 / out_moves[0]['init_uom_qty']
                                    out_write[out_moves[0]['id']]['covered_by_stock_qty'] += out_moves[0]['uom_qty']
                                    del out_moves[0]
                                # Si le stock ne couvre pas totalement le mouvement OUT: x%
                                else:
                                    out_moves[0]['uom_qty'] -= prev_qty
                                    out_write[out_moves[0]['id']]['covered_by_stock_percent'] += prev_qty * 100 / out_moves[0]['init_uom_qty']
                                    out_write[out_moves[0]['id']]['covered_by_stock_qty'] += prev_qty
                        
                        #===============================================================
                        # COUVERTURE PAR LES MOUVEMENTS
                        #===============================================================
                        # Mouvements réservés
                        for procurement_id, reserved_qty in product.get_reserved_stock_level_by_proc(associate_proc, states=('waiting', )).iteritems():
                            if procurement_id in procurement_in_moves:
                                for in_move in procurement_in_moves[procurement_id]:
                                    first = True
                                    while in_move['reserved_qty'] > 0:
                                        if not procurement_out_moves.get(procurement_id, False):
                                            break
                                        
                                        if first:
                                            in_write[in_move['id']]['out_date'] = procurement_out_moves[procurement_id][0]['date_expected']
                                            in_write[in_move['id']]['in_delta'] = (fields.Date.from_string(in_move['date_expected']) - fields.Date.from_string(procurement_out_moves[procurement_id][0]['date_expected'])).days
                                            if color:
                                                if color.move_1_active and color.move_1_min <= in_write[in_move['id']]['in_delta'] <= color.move_1_max:
                                                    in_write[in_move['id']]['color_priority_need'] = 3
                                                elif color.move_2_active and color.move_2_min <= in_write[in_move['id']]['in_delta'] <= color.move_2_max:
                                                    in_write[in_move['id']]['color_priority_need'] = 2
                                                elif color.move_3_active and color.move_3_min <= in_write[in_move['id']]['in_delta'] <= color.move_3_max:
                                                    in_write[in_move['id']]['color_priority_need'] = 1
                                            
                                            first = False
            
                                        old_qty = in_move['reserved_qty']
                                        in_move['reserved_qty'] -= procurement_out_moves[procurement_id][0]['reserved_qty']
                                        
                                        # Si au moins un des mouvements IN non confirmé et que le mouvement OUT n'est pas sur stock alors le mouvement OUT est non confirmé 
                                        if not in_move['is_confirmed'] and out_write[procurement_out_moves[procurement_id][0]['id']]['is_confirmed'] and out_write[procurement_out_moves[procurement_id][0]['id']]['trigger_supply'] != 'make_to_plan':
                                            out_write[procurement_out_moves[procurement_id][0]['id']]['is_confirmed'] = False
                                            
                                        # Si le mouvement IN couvre totalement le mouvement OUT
                                        if in_move['reserved_qty'] >= 0:
                                            cover_qty = procurement_out_moves[procurement_id][0]['reserved_qty']
                                            # MAJ OUT
                                            out_cover_percent = cover_qty * 100 / procurement_out_moves[procurement_id][0]['init_uom_qty']
                                            out_write[procurement_out_moves[procurement_id][0]['id']]['covered_by_move_percent'] += out_cover_percent
                                            out_write[procurement_out_moves[procurement_id][0]['id']]['covered_by_move_qty'] += cover_qty
                                            out_write[procurement_out_moves[procurement_id][0]['id']]['in_date'] = in_move['date_expected']
                                            out_write[procurement_out_moves[procurement_id][0]['id']]['out_delta'] = (fields.Date.from_string(in_move['date_expected']) - fields.Date.from_string(procurement_out_moves[procurement_id][0]['date_expected'])).days
                                            if color:
                                                if color.move_1_active and color.move_1_min <= out_write[procurement_out_moves[procurement_id][0]['id']]['out_delta'] <= color.move_1_max:
                                                    out_write[procurement_out_moves[procurement_id][0]['id']]['color_priority_need'] = 3
                                                elif color.move_2_active and color.move_2_min <= out_write[procurement_out_moves[procurement_id][0]['id']]['out_delta'] <= color.move_2_max:
                                                    out_write[procurement_out_moves[procurement_id][0]['id']]['color_priority_need'] = 2
                                                elif color.move_3_active and color.move_3_min <= out_write[procurement_out_moves[procurement_id][0]['id']]['out_delta'] <= color.move_3_max:
                                                    out_write[procurement_out_moves[procurement_id][0]['id']]['color_priority_need'] = 1
                                                
                                            # MAJ IN
                                            in_cover_percent = cover_qty * 100 / in_move['init_uom_qty']
                                            in_write[in_move['id']]['covers_move_percent'] += in_cover_percent
                                            in_write[in_move['id']]['covers_move_qty'] += cover_qty
                                            in_write[in_move['id']]['covers_stock_percent'] -= in_cover_percent
                                            in_write[in_move['id']]['covers_stock_qty'] -= cover_qty
                                            cover_rel_dict[in_move['id'], procurement_out_moves[procurement_id][0]['id']]['cover_qty'] += cover_qty
                                            cover_rel_dict[in_move['id'], procurement_out_moves[procurement_id][0]['id']]['in_cover_percent'] += in_cover_percent
                                            cover_rel_dict[in_move['id'], procurement_out_moves[procurement_id][0]['id']]['out_cover_percent'] += out_cover_percent
                                            
                                            del procurement_out_moves[procurement_id][0]
                                        # Si le mouvement IN ne couvre pas totalement le mouvement OUT
                                        else:
                                            cover_qty = old_qty
                                            # MAJ OUT
                                            out_cover_percent = cover_qty * 100 / procurement_out_moves[procurement_id][0]['init_uom_qty']
                                            out_write[procurement_out_moves[procurement_id][0]['id']]['covered_by_move_percent'] += out_cover_percent
                                            out_write[procurement_out_moves[procurement_id][0]['id']]['covered_by_move_qty'] += cover_qty
                                            # MAJ IN
                                            in_cover_percent = cover_qty * 100 / in_move['init_uom_qty']
                                            in_write[in_move['id']]['covers_move_percent'] = 100.0
                                            in_write[in_move['id']]['covers_move_qty'] = in_move['init_uom_qty']
                                            in_write[in_move['id']]['covers_stock_percent'] = 0.0
                                            in_write[in_move['id']]['covers_stock_qty'] = 0.0
                                            cover_rel_dict[in_move['id'], procurement_out_moves[procurement_id][0]['id']]['cover_qty'] += cover_qty
                                            cover_rel_dict[in_move['id'], procurement_out_moves[procurement_id][0]['id']]['in_cover_percent'] += in_cover_percent
                                            cover_rel_dict[in_move['id'], procurement_out_moves[procurement_id][0]['id']]['out_cover_percent'] += out_cover_percent
            
                                            procurement_out_moves[procurement_id][0]['reserved_qty'] -= cover_qty
                                            
                                    if not procurement_out_moves.get(procurement_id, False):
                                        break
                                        
                        # Mouvements non réservés
                        if in_moves:
                            for in_move in in_moves:
                                first = True
                                while in_move['uom_qty'] > 0:
                                    if not out_moves:
                                        break
                                    
                                    if first:
                                        in_write[in_move['id']]['out_date'] = out_moves[0]['date_expected']
                                        in_write[in_move['id']]['in_delta'] = (fields.Date.from_string(in_move['date_expected']) - fields.Date.from_string(out_moves[0]['date_expected'])).days
                                        if color:
                                            if color.move_1_active and color.move_1_min <= in_write[in_move['id']]['in_delta'] <= color.move_1_max:
                                                in_write[in_move['id']]['color_priority_need'] = 3
                                            elif color.move_2_active and color.move_2_min <= in_write[in_move['id']]['in_delta'] <= color.move_2_max:
                                                in_write[in_move['id']]['color_priority_need'] = 2
                                            elif color.move_3_active and color.move_3_min <= in_write[in_move['id']]['in_delta'] <= color.move_3_max:
                                                in_write[in_move['id']]['color_priority_need'] = 1
                                        
                                        first = False
        
                                    old_qty = in_move['uom_qty']
                                    in_move['uom_qty'] -= out_moves[0]['uom_qty']
                                    # Si au moins un des mouvements IN non confirmé et que le mouvement OUT n'est pas sur stock alors le mouvement OUT est non confirmé
                                    if not in_move['is_confirmed'] and out_write[out_moves[0]['id']]['is_confirmed'] and out_write[out_moves[0]['id']]['trigger_supply'] != 'make_to_plan':
                                        out_write[out_moves[0]['id']]['is_confirmed'] = False
                                        
                                    # Si le mouvement IN couvre totalement le mouvement OUT
                                    if in_move['uom_qty'] >= 0:
                                        cover_qty = out_moves[0]['uom_qty']
                                        # MAJ OUT
                                        out_cover_percent = cover_qty * 100 / out_moves[0]['init_uom_qty']
                                        out_write[out_moves[0]['id']]['covered_by_move_percent'] += out_cover_percent
                                        out_write[out_moves[0]['id']]['covered_by_move_qty'] += cover_qty
                                        out_write[out_moves[0]['id']]['in_date'] = in_move['date_expected']
                                        out_write[out_moves[0]['id']]['out_delta'] = (fields.Date.from_string(in_move['date_expected']) - fields.Date.from_string(out_moves[0]['date_expected'])).days
                                        if color:
                                            if color.move_1_active and color.move_1_min <= out_write[out_moves[0]['id']]['out_delta'] <= color.move_1_max:
                                                out_write[out_moves[0]['id']]['color_priority_need'] = 3
                                            elif color.move_2_active and color.move_2_min <= out_write[out_moves[0]['id']]['out_delta'] <= color.move_2_max:
                                                out_write[out_moves[0]['id']]['color_priority_need'] = 2
                                            elif color.move_3_active and color.move_3_min <= out_write[out_moves[0]['id']]['out_delta'] <= color.move_3_max:
                                                out_write[out_moves[0]['id']]['color_priority_need'] = 1
                                            
                                        # MAJ IN
                                        in_cover_percent = cover_qty * 100 / in_move['init_uom_qty']
                                        in_write[in_move['id']]['covers_move_percent'] += in_cover_percent
                                        in_write[in_move['id']]['covers_move_qty'] += cover_qty
                                        in_write[in_move['id']]['covers_stock_percent'] -= in_cover_percent
                                        in_write[in_move['id']]['covers_stock_qty'] -= cover_qty
                                        cover_rel_dict[in_move['id'], out_moves[0]['id']]['cover_qty'] += cover_qty
                                        cover_rel_dict[in_move['id'], out_moves[0]['id']]['in_cover_percent'] += in_cover_percent
                                        cover_rel_dict[in_move['id'], out_moves[0]['id']]['out_cover_percent'] += out_cover_percent
                                        del out_moves[0]
                                    # Si le mouvement IN ne couvre pas totalement le mouvement OUT
                                    else:
                                        cover_qty = old_qty
                                        # MAJ OUT
                                        out_cover_percent = cover_qty * 100 / out_moves[0]['init_uom_qty']
                                        out_write[out_moves[0]['id']]['covered_by_move_percent'] += out_cover_percent
                                        out_write[out_moves[0]['id']]['covered_by_move_qty'] += cover_qty
                                        # MAJ IN
                                        in_cover_percent = cover_qty * 100 / in_move['init_uom_qty']
                                        in_write[in_move['id']]['covers_move_percent'] = 100.0
                                        in_write[in_move['id']]['covers_move_qty'] = in_move['init_uom_qty']
                                        in_write[in_move['id']]['covers_stock_percent'] = 0.0
                                        in_write[in_move['id']]['covers_stock_qty'] = 0.0
                                        cover_rel_dict[in_move['id'], out_moves[0]['id']]['cover_qty'] += cover_qty
                                        cover_rel_dict[in_move['id'], out_moves[0]['id']]['in_cover_percent'] += in_cover_percent
                                        cover_rel_dict[in_move['id'], out_moves[0]['id']]['out_cover_percent'] += out_cover_percent
        
                                        out_moves[0]['uom_qty'] -= cover_qty
                                        
                                if not out_moves: 
                                    break
                        
                        # MAJ de la table de relation
                        # SQL pour performance
        #                 for vals in cover_rel_dict.values():
        #                     cover_rel_obj.create(vals)
                        self.env.cr.executemany(insert_query, [(x['in_move_id'], 
                                                                x['out_move_id'], 
                                                                x['product_id'], 
                                                                x['cover_qty'], 
                                                                x['in_cover_percent'], 
                                                                x['out_cover_percent']) for x in cover_rel_dict.values()])
    
                    # MAJ des mouvements sortants
                    # SQL pour performance
    #                 for move_id, move_vals in out_write.iteritems():
    #                     move_vals['not_covered_qty'] = move_vals['uom_qty'] - move_vals['covered_by_move_qty'] - move_vals['covered_by_stock_qty']
    #                     move_vals['not_covered_percent'] = max(100 - move_vals['covered_by_move_percent'] - move_vals['covered_by_stock_percent'], 0.0)
    #                     if move_vals['not_covered_percent']:
    #                         move_vals['color_priority_need'] = 4
    #                           
    #                     move_vals['availability'] = move_vals['covered_by_stock_percent']
    #                     del move_vals['uom_qty']
    #                     move_obj.browse(move_id).write(move_vals, with_covers=False)
                    for move_id, move_vals in out_write.iteritems():
                        move_vals['not_covered_qty'] = move_vals['uom_qty'] - move_vals['covered_by_move_qty'] - move_vals['covered_by_stock_qty']
                        move_vals['not_covered_percent'] = round(max(100 - move_vals['covered_by_move_percent'] - move_vals['covered_by_stock_percent'], 0.0), round_factor)
                        if move_vals['not_covered_percent']:
                            move_vals['color_priority_need'] = 4
                            move_vals['is_confirmed'] = False
                             
                        move_vals['availability'] = move_vals['covered_by_stock_percent']
                        del move_vals['uom_qty']
                        del move_vals['trigger_supply']
                        out_write[move_id] = move_vals
    
                    self.env.cr.executemany(out_update_query, [(x[1]['covered_by_stock_percent'], 
                                                                x[1]['covered_by_stock_qty'], 
                                                                x[1]['covered_by_move_percent'], 
                                                                x[1]['covered_by_move_qty'], 
                                                                x[1]['not_covered_percent'], 
                                                                x[1]['not_covered_qty'], 
                                                                x[1]['in_date'], 
                                                                x[1]['color_priority_need'], 
                                                                x[1]['out_delta'], 
                                                                x[1]['availability'], 
                                                                x[1]['is_confirmed'], 
                                                                x[0]) for x in out_write.iteritems()])
                    
                    # MAJ des mouvements entrants
                    # SQL pour performance
    #                 for move_id, move_vals in in_write.iteritems():
    #                     move_obj.browse(move_id).write(move_vals, with_covers=False)
                    self.env.cr.executemany(in_update_query, [(x[1]['covers_move_percent'], 
                                                               x[1]['covers_move_qty'], 
                                                               x[1]['covers_stock_percent'], 
                                                               x[1]['covers_stock_qty'], 
                                                               x[1]['out_date'], 
                                                               x[1]['color_priority_need'], 
                                                               x[1]['availability'], 
                                                               x[1]['in_delta'], 
                                                               x[0]) for x in in_write.iteritems()])
                
                # MAJ des covers des pickings
                if picking_to_up:
                    picking_to_up = list(set(picking_to_up))
                    picking_to_up_rs = picking_obj.browse(picking_to_up)
#                     picking_to_up_rs.compute_availability()
                    picking_to_up_rs.compute_color_priority_need()
                
        return True
    
    
    def get_last_move_qty(self):
        """
            Retourne la qté du dernier mouvement terminé sortant en UdM du produit
        """
        res = 0.0
        self.env.cr.execute(""" SELECT sm.uom_qty AS qty, sm.uom_id AS move_uom, p.uom_id AS product_uom 
                                FROM stock_move sm 
                                  JOIN product_product p ON p.id = sm.product_id
                                WHERE p.id = %s 
                                  AND sm.state = 'done' 
                                ORDER BY sm.date DESC 
                                LIMIT 1"""%((self.id, )))
        q_res = self.env.cr.dictfetchone()
        if q_res:
            if q_res['move_uom'] != q_res['product_uom']:
                res = self.env['product_uom']._compute_qty(q_res['move_uom'], q_res['qty'], to_uom_id=q_res['product_uom'])
            else:
                res = q_res['qty']
                
        return res
    
    
    def get_is_low_proc(self, needed_qty):
        """
            Retourne Vrai si ([Qté du besoin / Qté du dernier mouvement terminé sortant]) < ([Low procurement] / 100))
        """
        res = False
        if self.low_procurement:
            last_move_qty = self.get_last_move_qty()
            if last_move_qty:
                res = (needed_qty / last_move_qty * 100) < self.low_procurement

        return res
    
    
    def get_max_virtual_stock_warehouse(self, warehouse_to_exclude_ids=[], to_date=False, with_warehouse_not_included=False):
        """
            Retourne l'entrepôt qui a le plus de stock virtuel pour ce produit 
        """
        qty_per_wh = {}
        args = [('id', 'not in', warehouse_to_exclude_ids)]
        if not with_warehouse_not_included:
            args.append(('included_into_the_stock', '=', True))
        
        for warehouse in self.env['stock.warehouse'].search(args):
            qty = self.get_available_stock(warehouse_id=warehouse.id, to_date=to_date)
            if qty > 0:
                qty_per_wh[qty] = warehouse.id
            
        if qty_per_wh:
            max_qty = max(qty_per_wh.keys())
            if max_qty:
                res = qty_per_wh[max_qty], max_qty
            else:
                res = False, 0.0
                
        else:
            res = False, 0.0
            
        return res
    
    
    @api.multi
    def show_warehouse_stock_level(self):
        wiz_obj = self.env['show.warehouse.stock.level']
        line_vals = []
        vals = {'product_id': self[0].id, 'line_ids': line_vals}
        for warehouse in self.env['stock.warehouse'].search([]):
            virtual_stock, available_stock = self.get_available_stock(return_real_stock=True, warehouse_id=warehouse.id)
            line_vals.append([0, 0, {
                                 'warehouse_id': warehouse.id,
                                 'available_stock': available_stock,
                                 'virtual_stock': virtual_stock,
                                     }])
        
        wiz_id = wiz_obj.create(vals)
        if wiz_id:
            res = {
                'name': _('Create attributes'),
                'view_type': 'form',
                'view_mode': 'form',
                'context': {'dialog_size': 'medium'},
                'res_model': 'show.warehouse.stock.level',
                'res_id': wiz_id.id,
                'type': 'ir.actions.act_window',
                'target': 'new'
            }
        else:
            res = False
        
        return res
    
    
    def return_stock_graph_view(self, cr, uid, ctx={}, context=None):
        """
            Fonction qui cherche et retourne le graphique des stocks d'un produit
        """
        data_pool = self.pool.get('ir.model.data')
        action = {}
        action_model, action_id = data_pool.get_object_reference(cr, uid, 'stock', "product_graph_stock_action")
        if action_model:
            action_pool = self.pool.get(action_model)
            action = action_pool.read(cr, uid, action_id, context = context)
            action['context'] = ctx
            if action.get('domain'):
                old_domain = eval(action['domain'])
                old_domain.append(('product_id', '=', ctx.get('default_product_id', False)))
                action['domain'] = str(old_domain)
            else:
                action['domain'] = "[('product_id', '=', %s)]"%(ctx.get('default_product_id', False))
                
        return action
    
    
    def show_graph(self, cr, uid, ids, context=None):
        """
            Fonction appelée par le bouton de graphique de stock. permet d'appeler le graphique des stocks du produit
        """
        act = self.return_stock_graph_view(cr, uid, ctx={'default_product_id': ids[0]}, context=None)
        return act
    
    
    def return_stock_move_view(self, cr, uid, ctx={}, context=None):
        """
            Fonction qui cherche et retourne les mouvements de stock pour un produit
        """
        data_pool = self.pool.get('ir.model.data')
        action = {}
        action_model, action_id = data_pool.get_object_reference(cr, uid, 'stock', "product_stock_move_action")
        if action_model:
            action_pool = self.pool.get(action_model)
            action = action_pool.read(cr, uid, action_id, context = context)
            action['context'] = ctx
            
        return action
    
    
    def show_stock_move(self, cr, uid, ids, context=None):
        """
            Fonction appelée par le bouton de mouvement de stock du produit
        """
        act = self.return_stock_move_view(cr, uid, ctx={'product_id': ids[0]}, context=None)
        return act
        
        
    @api.model
    def create(self, vals):
        modif_control = False
        if 'categ_id' in vals and vals['categ_id']:
            if 'control_categ_syncro' in vals and vals['control_categ_syncro']:
                modif_control = True
        
        # Contrainte pour ne pas avoir dans la config du produit trigger_supply = make_to_plan et exclude_of_mrp = True
        if 'exclude_of_mrp' in vals and vals['exclude_of_mrp'] and 'trigger_supply' in vals and vals['trigger_supply'] == 'make_to_plan':
            raise except_orm(_('Error'), _('The product may not have the supply trigger "make to plan" and have exclude of mrp checked'))
        
        product = super(product_product, self).create(vals)
        for warehouse in self.env['stock.warehouse'].search([]):
            self.env['stock.level'].create({'product_id': product.id, 'warehouse_id': warehouse.id})
            
        if modif_control:
            product.categ_id.modif_type_quality_documents(field='quality_control_ids', product_rcs=product, delete=False)
                
        return product
    
    
    @api.multi
    def write(self, vals=None):
        """
            Interdiction de changer de catégorie
        """
        modif_control = False
        if not vals:
            vals = {}
        
        for product in self:
            if 'track_label' in vals and vals['track_label'] != product.track_label:
                if (('available_stock' in vals and vals['available_stock']) or ('available_stock' not in vals and product.available_stock)):
                    raise except_orm(_('Impossible to change track label if available stock is different 0'))
        
            if ('printed_doc_categ_syncro' in vals and vals['printed_doc_categ_syncro']) or \
            (not 'printed_doc_categ_syncro' in vals and product.printed_doc_categ_syncro and 'categ_id' in vals and vals['categ_id']):
                modif_control = True
            
            # Contrainte pour ne pas avoir dans la config du produit trigger_supply = make_to_plan et exclude_of_mrp = True
            error_param_exclude_of_mrp = False
            if ('exclude_of_mrp' in vals and vals['exclude_of_mrp']) or ('trigger_supply' in vals and vals['trigger_supply'] == 'make_to_plan'):
                if ('exclude_of_mrp' in vals and vals['exclude_of_mrp']) and (('trigger_supply' not in vals and product.trigger_supply == 'make_to_plan') or  ('trigger_supply' in vals and vals['trigger_supply'] == 'make_to_plan')):
                    error_param_exclude_of_mrp = True
                elif 'exclude_of_mrp' not in vals and product.exclude_of_mrp and 'trigger_supply' in vals and vals['trigger_supply'] == 'make_to_plan':
                    error_param_exclude_of_mrp = True
            
            if error_param_exclude_of_mrp:
                raise except_orm(_('Error'), _('The product may not have the supply trigger "make to plan" and have exclude of mrp checked'))
            
        res = super(product_product, self).write(vals=vals) 
        if modif_control:
            for product in self:
                product.categ_id.modif_type_quality_documents(field='plan_control_ids', product_rcs=product, delete=False)
                if 'uom_id' in vals and vals['uom_id']:
                    self.env.cr.execute("""UPDATE 
                                         stock_level sl 
                                       SET 
                                         uom_qty = slr.dynamic_qty
                                       FROM 
                                         stock_level_report slr 
                                       WHERE 
                                         sl.id = slr.sl_id AND 
                                         slr.static_qty <> slr.dynamic_qty AND 
                                         slr.product_id IN %s """, (tuple([product.id]), ))
        
        if 'uom_id' in vals and vals['uom_id']:
            self.env.cr.execute("""UPDATE 
                                     stock_level sl 
                                   SET 
                                     uom_qty = slr.dynamic_qty
                                   FROM 
                                     stock_level_report slr 
                                   WHERE 
                                     sl.id = slr.sl_id AND 
                                     slr.static_qty <> slr.dynamic_qty AND 
                                     slr.product_id IN %s """, (tuple(self.ids), ))

        return res
    
    
        
class common_attribute_category(models.Model):
    _name = 'common.attribute.category'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(size=64, required=True)
    common_attribute_model_ids = fields.One2many('common.attribute.model', 'category_id', string='Attributes')
    
        
        
class common_attribute_model(models.Model):
    _name = 'common.attribute.model'
    _order = 'sequence,label'
    _rec_name = 'label'
    
    
    @api.model
    def _type_get(self):
        return [
            ('char', 'Char'),
            ('float', 'Float'),
               ]
        
    
    category_id = fields.Many2one('common.attribute.category', string='Category', required=False, ondelete='restrict', select=True)
    product_ids = fields.Many2many('product.product', 'attribute_product_rel', 'common_attribute_id', 'product_id', string='Products')    
    sequence = fields.Integer(default=0, required=True)
    label = fields.Char(size=64, required=True)
    name = fields.Char(size=64, required=True, select=True)
    default_value = fields.Char(size=128, required=False)
    note = fields.Text()    
    type = fields.Selection('_type_get', default='char')
    is_quantity = fields.Boolean(string='Quantity', default=False)
    is_visible = fields.Boolean(string='Visible', default=True)
    is_required = fields.Boolean(string='Required', default=False)
    is_readonly = fields.Boolean(string='Readonly', default=False)
    is_compute = fields.Boolean(string='Compute', default=False)
    is_default_compute = fields.Boolean(string='Computed default value', default=False)
    is_unique = fields.Boolean(string='Unique', default=False)
    is_printable = fields.Boolean(string='Printable', default=False)
    sale = fields.Boolean(default=False)
    production = fields.Boolean(default=False)
    purchase = fields.Boolean(default=False)
    receipt = fields.Boolean(default=False)
    function = fields.Text(help="""
Using attributes
-----------------------
For example, to use the length attribute value, 
you must written attr['length']

You can also use linked object and all of these fields with the keyword const
Usable const:
  - product: Product
  - picking: Stock picking
  - move: Stock move
  - po : Purchase order
  - pol: Purchase order line
  - supplier: supplier of PO
  - mo: Manufacturing order
  - wo: Work order
  - customer: Customer of MO
  - so: Sale order 
  - sol: Sale order line*
  - final_product: final product of MO
Example:
 'Product: ' + const['product'].name + ' Picking partner: ' + const['picking'].partner_id.name


Operations syntax
--------------------------
Operations must be written in the programming language "Python"
https://docs.python.org/2.7/


Search in a table
-----------------------
It is possible to search in a table with the function table_search().
This function needs 3 parameters:
  - table: table on which search
  - filter: search domain
  - field: field returned by the function
  
Example:
 This example return the name of a product from its code.
 table_search(table='product.product', domain=[('code', '=', attr['code'])], field='name')""")

    
    @api.one
    @api.constrains('name')
    def _check_function(self):
        if re.search("[^a-z0-9_]+", self.name) != None:
            raise Warning(_('Name must be ASCII'))
    
    
    @api.onchange('label')
    def onchange_label(self):
        if self.label:
            self.name = '_'.join(self.label.lower().split()).encode('ascii', 'replace').replace('?', '_')
        else:
            self.name = ''
            
            
    @api.onchange('is_default_compute')
    def onchange_is_default_compute(self):
        if self.is_default_compute:
            self.is_compute = False
    
    
    @api.onchange('is_compute')
    def onchange_is_compute(self):
        if self.is_compute:
            self.is_default_compute = False
    
    
    @api.onchange('name')
    def onchange_name(self):
        w = {}
        v = {}
        if re.search("[^a-z0-9_]+", self.name) != None:
            w = {'title': 'Error', 'message': 'Name must be ASCII'}
            self.name = '_'.join(self.label.lower().split()).encode('ascii', 'replace').replace('?', '_')
             
        return {'warning': w, 'value': v}
    
    
    
class product_version_historical(models.Model):
    """
    product version historical
    """
    _name = 'product.version.historical'
    _description = 'Product version historical'
    _order = 'start_date asc'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    product_id = fields.Many2one('product.product', string='Product', ondelete='cascade')
    start_date = fields.Date(string='Start date', required=True)
    version = fields.Char(string='Version', required=True)
    
