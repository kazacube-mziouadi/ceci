# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError

class product_product(models.Model):
    _inherit = 'product.product'
    _description = 'Product'

    
    def _supply_method_get(self):
        res = super(product_product, self)._supply_method_get()
        res.append(('produce', _('Produce')))
        return res
   
   
    @api.one
    def _compute_tool_routing_ids(self):
        rl_ids = False
        tool_rcs = self.env['mrp.rl.tools'].search([('product_id', '=', self.id)])
        if tool_rcs:
            rl_ids = [x.routing_line_id.id for x in tool_rcs if x.routing_line_id]

        self.tool_routing_ids = rl_ids
    
    
    @api.one
    @api.depends('name')
    def _compute_nb_tool_wo(self):
        self.tool_nb_wo = 0
        
        
    def compute_production_cost_price(self, quantity=0):
        price = 0.0
        total_efficiency = 1
        bom_ids = self.env['mrp.bom']._bom_find(self.id, self.uom_id.id)
        serie_eco = quantity or self.price_qty
        if bom_ids:
            price_unit_bom, price_total_bom = bom_ids[0].function_compute_price(button=False, type='normal', product=self, serie_eco=serie_eco, 
                                                                                prod_family=False)
            
            if bom_ids[0].routing_first_id:
                price_unit_routing, ptr, ttr, wtnor = bom_ids[0].routing_first_id.function_compute_price(button=False, serie_eco=serie_eco, option_ids=False)
            else:
                price_unit_routing = bom_ids[0].routing_first_price

            price = price_unit_bom + price_unit_routing
            total_efficiency = bom_ids[0].total_efficiency or 1
        
        production_factor = self.env['technical.data.config.settings'].get_param('production_factor') or 1
        return price * production_factor / total_efficiency


    @api.one
    def _compute_production_cost_price(self):
        bom_rcs = self.env['mrp.bom']._bom_find(self.id, self.uom_id.id, options=None, no_active=False, date=False)
        if bom_rcs:
            production_cost_price = bom_rcs.production_cost_price
        else:
            production_cost_price = 0
            
        self.production_cost_price = production_cost_price
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    # Generalities
    production_manager_id = fields.Many2one('res.users', string='Technical data manager', required=False, ondelete='restrict')
    planning_manager_id = fields.Many2one('res.users', string='Planning manager', required=False, ondelete='restrict')
    price_qty = fields.Float(string='Price qty', default=1.0, required=True, digits=dp.get_precision('Product quantity'), help="Used to compute the "
                     "cost price")
    production_cost_price = fields.Float(string='Cost price', default=0.0, digits=dp.get_precision('Price technical'), required=False, compute='_compute_production_cost_price')
    
    # Parameters 
    prod_family_id = fields.Many2one('production.family', string='Production family', required=False, ondelete='restrict')
    production_delay = fields.Integer(string='Manufacturing delay', default=0, required=False, help="Informal delay. It's not used in calculations")
    production_min_qty = fields.Float(string='Manufacturing minimum quantity', digits=dp.get_precision('Product quantity'), help="Quantity used in the manufacturing orders, "
                                      "we don't produce below this quantity")
    production_multiple_qty = fields.Float(string='Manufacturing multiple', digits=dp.get_precision('Product quantity'), help="We will produce to the multiple of "
                                           "this quantity")
    bom_level = fields.Integer(string='BoM level', default=0, required=False)
    # Tools
    tool_routing_ids = fields.One2many('mrp.routing.line', compute='_compute_tool_routing_ids', string='Routing lines using this tool')
#     tool_nb_wo = fields.Integer(string='Nb of tools purchased', compute='_compute_nb_tool_wo')
    
    
    def get_default_supply_delay_mrp(self, return_date=False, hours=False):
        res = self.production_delay
        if return_date:
            calendar = self.env.user.company_id.partner_id.calendar_id
            return res, calendar.get_date(fields.Date.today(), res, hours=True)
        else:
            return res
    
        
    def get_draft_mo_qty(self):
        res = 0.0
        mo_obj = self.env['mrp.manufacturingorder']
        mo_qtys = mo_obj.search_group(fields=['quantity'], 
                                       groupby=['product_id'], 
                                       args=[('state', '=', 'draft'), ('product_id', '=', self.id), ('is_forecast', '=', False)],
                                       sum='quantity',
                                       return_dict=True)
        for mo_qty in mo_qtys:
            res += mo_qty['quantity']

        return res
    
    
    def get_origin_fields(self):
        res = super(product_product, self).get_origin_fields()
        res.append('origin_wo_id')
        return res
    
    
    def _simulate_availability_produce(self, qty, supplier_id, option_ids, start_date):
        virtual_stock, available_stock = self.get_available_stock(return_real_stock=True)
        
        if virtual_stock < qty:
            bom_rs = self.env['mrp.bom']._bom_find(self.id, self.uom_id, option_ids)
            routing_rs = bom_rs.routing_ids._routing_find(options=option_ids)
            if not routing_rs:
                raise except_orm(_('Error'), _('No active routing found for BoM %s')%(bom_rs.name))
            
            # quel calendar prendre? pour l'instant celui de première ressource de première ligne de gamme
            calendar_id = self.env.user.company_id.partner_id.calendar_id
            prices_and_times = routing_rs.function_compute_price(False, qty, option_ids.ids)
            tmp_date = calendar_id.get_dates(start_date, prices_and_times[2])['end_date']
            ret = calendar_id.get_date(tmp_date, prices_and_times[3])
        # Stock réel et stock virtuel >= besoin => AJD
        elif available_stock >= qty:
            ret = start_date
        # Stock réel < besoin et stock virtuel >= besoin => Calcul date besoin
        else:
            ret = self.get_date_last_stock_min(self.env.user.company_id.warehouse_id.stock_location_id, qty, inverse=True)
                    
        return ret
    
    
    @api.multi
    def cron_calc_bom_level(self):
        # récup toutes les nomenclatures "principales" des produits produisibles
        bom_obj = self.env['mrp.bom']
        all_products = self.search([('produce_ok', '=', True)])
        if all_products:
            prod_family_ids = [x['prod_family_id'] for x in all_products.read(['prod_family_id'], load = '_class_write') if x['prod_family_id']]
        else:
            prod_family_ids = []
        
        if prod_family_ids:
            all_bom = bom_obj.search([('active', '=', True), '|', ('product_id', 'in', all_products.ids), ('prod_family_id', 'in', prod_family_ids)])
        else:
            all_bom = bom_obj.search([('active', '=', True), ('product_id', 'in', all_products.ids)])
            
        nodes = {bom.id:Node(bom.id) for bom in all_bom}
        real_bom = set()
        parents = set()
        for bom in all_bom:
            if bom.bom_id and bom.bom_id.active:
                # chercher la bom correspondante, l'ajouter aux parents
                bom_id = bom_obj._bom_find(bom.product_id.id, bom.product_id.uom_id, options=None, no_active=False, date=False)
                if bom_id and bom_id.id in nodes and bom.bom_id and bom.bom_id.id in nodes:
                    nodes[bom_id.id].parents.add(nodes[bom.bom_id.id])
                    parents.add(nodes[bom.bom_id.id])
            else:
                real_bom.add(nodes[bom.id])
                
        leafs = real_bom - parents
        
        for leaf in leafs:
            leaf.set_value(0)
        
        for node in nodes.values():
            bom = bom_obj.browse(node.name)
            if bom.bom_id:
                continue
            product = bom.product_id
            if product:
                product.write({'bom_level': node.value + 1})
            else:
                bom_obj.browse(node.name).prod_family_id.product_ids.write({'bom_level': node.value + 1})
               
                
    @api.multi
    def button_view_bom_head(self):
        """
            Bouton qui permet de voir toutes les nomenclatures qui a le produit comme composant
        """
        bom_obj = self.env['mrp.bom']
        for product in self:
            bom_ids = bom_obj.find_bom_head(product)
            
            return {
                    'name': _('BoM'),
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'mrp.bom',
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'domain': [('id', 'in', bom_ids)],
                    }
        return True
    
    
    def fonction_extra_price(self, price, sale_line_rcs):
        """
            Fonction qui permet de d'ajouter au prix unitaire des prix additionnels
            :param price: prix
            :type price: flaot
            :param sale_line_rcs: recordset d'une ligne de vente
            :type sale_line_rcs: recordset
            :return le prix
            :rtype: float
        """
        price = super(product_product, self).fonction_extra_price(price, sale_line_rcs)
        if sale_line_rcs:
            for option_lines in sale_line_rcs.option_lines_ids:
                if option_lines.price_unit:
                    price += option_lines.price_unit
        
        return price


    @api.multi
    def write(self, vals=None):
        """
            Interdiction de modifier la gestion des réceptions si le service est dans une gamme
        """
        if not vals:
            vals = {}
        
        if 'manage_service_receipt' in vals and vals['manage_service_receipt'] != True and ('type' not in vals or vals['type'] == 'service'):
            consumed_service_obj = self.env['mrp.rl.consumed.service']
            for product in self:
                consumed_service_rcs = consumed_service_obj.search([('product_id', '=', product.id)], limit=1)
                if consumed_service_rcs:
                    raise except_orm(_('Error'), _('The product (%s) is used as a service in the routing line (%s).')%(product.name, consumed_service_rcs.routing_line_id.name))
                
        return super(product_product, self).write(vals=vals)

    

class Node(object):
    """ Used for calculation of BoM level """
    def __init__(self, name):
        self.parents = set()
        self.value = -1
        self.name = name


    def set_value(self, value):
        if value > self.value:
            self.value = value
            for parent in self.parents:
                parent.set_value(value + 1)
    
    
    def __repr__(self):
        return "Bom %d, parents [%s]" % (self.name, ", ".join((str(par.name) for par in self.parents)))
    
    
    
class parameter_dimension(models.Model):
    """ 
        Paramater Dimension 
    """
    _inherit = 'parameter.dimension'
    _description = 'Paramater Dimension'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    mo_id = fields.Many2one('mrp.manufacturingorder', string='MO', required=False, ondelete='cascade')
    prod_family_id = fields.Many2one('production.family', string='Production family', required=False, ondelete='restrict')
    


class quality_control_product(models.Model):
    """ 
        Quality Control Product
    """
    _inherit = 'quality.control.product'
    _description = 'Quality Control Product'

    #===========================================================================
    # COLUMNS
    #===========================================================================
    routing_line_id = fields.Many2one('mrp.routing.line', string='Routing Line', required=False, ondelete='cascade')



class production_family(models.Model):
    """ 
        Production family
    """
    _name = 'production.family'
    _description = 'Production family'
    
    
    def compute_production_cost_price(self):
        price = 0.0
        total_efficiency = 1
        bom_ids = self.env['mrp.bom'].search([('prod_family_id', '=', self.id), ('type', '=', 'family')])
        if bom_ids:
            price = bom_ids[0].price_unit + bom_ids[0].routing_first_price
            total_efficiency = bom_ids[0].total_efficiency or 1
        
        production_factor = self.env['technical.data.config.settings'].get_param('production_factor') or 1
        return price * production_factor / total_efficiency


    @api.one
    def _compute_production_cost_price(self):
        self.production_cost_price = self.compute_production_cost_price()
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Name', size=256, required=True)
    product_ids = fields.One2many('product.product', 'prod_family_id',  string='Products')
    uom_id = fields.Many2one('product.uom', string='UoM', required=True, ondelete='restrict')
    parameter_ids = fields.One2many('parameter.dimension', 'prod_family_id',  string='Parameters', copy=True)
    price_qty = fields.Float(string='Price qty', default=1.0, required=True, digits=dp.get_precision('Product quantity'), help="Used to compute the cost price")
    production_cost_price = fields.Float(string='Cost price', default=0.0, digits=dp.get_precision('Price technical'), required=False, compute='_compute_production_cost_price')
    
    
    
class stock_quality_control(models.Model):
    _inherit = 'stock.quality.control'
    
    @api.model
    def _type_get(self):
        res = super(stock_quality_control, self)._type_get()
        res.extend([('pdf_production', _('Production (PDF)')),
                    ('jasper_production', _('Production (Jasper)'))])
        return res
    
    
    
class product_supplierinfo(models.Model):
    _inherit = 'product.supplierinfo'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    
    customs_duties = fields.Float(string='Customs duties (%)', default=0.0, required=False)
    other_expenses = fields.Float(string='Other expenses (%)', default=0.0, required=False)