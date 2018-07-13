# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm, ValidationError
import time



class product_product(models.Model):
    _inherit = 'product.product'
    _description = 'Product'
    _sql_constraints = [
        ('purchase_divisor_gt_zero', 'CHECK (purchase_divisor!=0)', 'The purchase divisor cannot be 0!')
    ]
    
    @api.one
    @api.depends('purchase_factor', 'purchase_divisor', 'uop_id')
    def _compute_purchase_factor_help(self):
        self.purchase_factor_help = self.factor_help_compute(self.uom_id, self.uop_id, self.purchase_factor, self.purchase_divisor) 
    
    
    @api.one
    @api.depends('purchase_factor', 'purchase_divisor', 'uop_id')
    def _compute_inv_purchase_factor_help(self):
        self.inv_purchase_factor_help = self.inv_factor_help_compute(self.uop_id, self.uom_id, self.purchase_factor, self.purchase_divisor)
        
    
    @api.one
    def _compute_purchase_cost_price(self):
        """
            Champ fonction du prix d'achat du produit selon sa méthode de coût
        """
        self.purchase_cost_price = self.compute_purchase_cost_price()
    
    
    def compute_purchase_cost_price(self):
        """
            Fonction qui permet de calculer le prix d'achat du produit selon sa méthode de coût
        """
        price = 0.0
        #On récupère le prix de la valorisation
        if self.cost_method == 'valuation':
            price =  self.enhanced_price
        #On va chercher le prix selon le fournisseur dans le référencement fournisseur on ne récupère donc pas le prix dans ce champ
        elif self.cost_method == 'supplier_pl':
            price = 0.0
        #On va chercher le prix de la premère séquence du référencement fournisseur
        elif self.cost_method == 'supplier_pl_eoq':
            #On récupère le premier référencement par rapport à la séquence
            sinfo_ids = self.env['product.supplierinfo'].search([('product_id','=',self.id)], order = 'sequence asc', limit=1)
            if sinfo_ids:
                #On récupère la première liste de prix
                sec_uom_id = sinfo_ids[0].uop_id
                uoi_id = sinfo_ids[0].uoi_id
                factor= sinfo_ids[0].factor
                divisor= sinfo_ids[0].divisor
                eoqs = self.get_qtys(self.eoq, 
                                     uom_id=self.uom_id, 
                                     sec_uom_id=sec_uom_id, 
                                     uoi_id=uoi_id, 
                                     by_field= 'uom', 
                                     dual_unit= self.dual_unit, 
                                     dual_unit_type= self.dual_unit_type, 
                                     factor=factor, 
                                     divisor=divisor,
                                     with_raise=False,
                                     with_round=False)
                eoq_uoi = eoqs.get('uoi_qty',0.0)
                price_ids = self.env['pricelist.supplierinfo'].search([('sinfo_id','=',sinfo_ids[0].id),('min_qty','<=',eoq_uoi)], order = 'min_qty desc', limit=1)
                if not price_ids:
                    price_ids = self.env['pricelist.supplierinfo'].search([('sinfo_id','=',sinfo_ids[0].id)], order = 'min_qty asc', limit=1)
                if price_ids:
                    price_sup = price_ids[0].price
                    devise = sinfo_ids[0].currency_id
                    #On transforme le prix en unité de gestion
                    prices = self.get_qtys_unit(price_sup, 
                                     uom_id= self.uom_id, 
                                     sec_uom_id= sec_uom_id, 
                                     uoi_id= uoi_id, 
                                     by_field= 'uoi', 
                                     dual_unit= self.dual_unit, 
                                     dual_unit_type= self.dual_unit_type, 
                                     factor= factor, 
                                     divisor= divisor,
                                     with_raise=False,
                                     with_round=False)
                    price = prices.get('uom_qty',0.0)
                    #On transforme le prix dans la bonne devise si besoin
                    if devise and self.company_id and self.company_id.currency_id and self.company_id.currency_id.id != devise.id:
                        price = self._calcul_price_rate_devise(devise, price, self.company_id.currency_id)
                                            
        elif self.cost_method == 'last_purchase':
            # On récupère le dernier achat
            price = 0.0
            line_purchase_rcs = self.env['purchase.order.line'].search([('product_id','=',self.id), ('purchase_state', 'not in', ('draft', 'waiting', 'cancel'))], order='id desc', limit=1)
            if line_purchase_rcs:
                sinfo_ids = self.env['product.supplierinfo'].search([('partner_id','=',line_purchase_rcs.purchase_order_id.partner_id.id), ('product_id','=',self.id)], order = 'sequence asc', limit=1)
                devise = line_purchase_rcs[0].currency_id
                price_purchase = line_purchase_rcs[0].price_unit
                sec_uom_id = line_purchase_rcs[0].sec_uom_id
                uoi_id = line_purchase_rcs[0].uoi_id
                factor= sinfo_ids and sinfo_ids[0].factor or self.purchase_factor
                divisor= sinfo_ids and sinfo_ids[0].divisor or self.purchase_divisor
                #On transforme le prix en unité de gestion
                prices = self.get_qtys_unit(price_purchase, 
                                 uom_id= self.uom_id, 
                                 sec_uom_id= sec_uom_id, 
                                 uoi_id= uoi_id, 
                                 by_field= 'uoi', 
                                 dual_unit= self.dual_unit, 
                                 dual_unit_type= self.dual_unit_type, 
                                 factor= factor, 
                                 divisor= divisor,
                                 with_raise=False,
                                 with_round=False)
                price = prices.get('uom_qty',0.0)
                #On transforme le prix dans la bonne devise si besoin
                if devise and self.company_id and self.company_id.currency_id and self.company_id.currency_id.id != devise.id:
                    price = self._calcul_price_rate_devise(devise, price, self.company_id.currency_id)
        
        elif self.cost_method == 'last_10_purchase':
            # On récupère les 10 dernier achat
            price = 0
            line_purchase_rcs = self.env['purchase.order.line'].search([('product_id','=',self.id), ('purchase_state', 'not in', ('draft', 'waiting', 'cancel'))], order='id desc', limit=10)
            i = 0
            for line_purchase in line_purchase_rcs:
                sinfo_ids = self.env['product.supplierinfo'].search([('partner_id','=',line_purchase.purchase_order_id.partner_id.id), ('product_id','=',self.id)], order = 'sequence asc', limit=1)
                devise = line_purchase.currency_id
                price_purchase = line_purchase.price_unit
                sec_uom_id = line_purchase.sec_uom_id
                uoi_id = line_purchase.uoi_id
                factor= sinfo_ids and sinfo_ids[0].factor or self.purchase_factor
                divisor= sinfo_ids and sinfo_ids[0].divisor or self.purchase_divisor
                #On transforme le prix en unité de gestion
                prices = self.get_qtys_unit(price_purchase, 
                                 uom_id= self.uom_id, 
                                 sec_uom_id= sec_uom_id, 
                                 uoi_id= uoi_id, 
                                 by_field= 'uoi', 
                                 dual_unit= self.dual_unit, 
                                 dual_unit_type= self.dual_unit_type, 
                                 factor= factor, 
                                 divisor= divisor,
                                 with_raise=False,
                                 with_round=False)
                price_temp = prices.get('uom_qty',0.0)
                #On transforme le prix dans la bonne devise si besoin
                if devise and self.company_id and self.company_id.currency_id and self.company_id.currency_id.id != devise.id:
                    price_temp = self._calcul_price_rate_devise(devise, price_temp, self.company_id.currency_id)
                
                price += price_temp
                i += 1
            
            if price and i:
                price = price / i
            
        
        elif self.cost_method == 'manual':
            price =  self.purchase_cost_price_manual
        
        purchase_factor = self.env['technical.data.config.settings'].get_param('purchase_factor') or 1
        return price * purchase_factor
    
    
    @api.model
    def _cost_method_get(self):
        return [
                    ('valuation', _('Valuation')),
                    ('supplier_pl', _('Supplier price-list')),
                    ('supplier_pl_eoq', _('Supplier price-list with EOQ')),
                    ('last_purchase', _('Last purchase')),
                    ('last_10_purchase', _('Last 10 purchases')),
                    ('manual', _('Manual')),
                       ]
    
    
    @api.one
    def _compute_nb_purchased_tool(self):
        """
            Fonction permettant de récupérer la quantité du produit
            acheté s'il s'agit d'un outil technique
        """
        qty = 0.0
        if self.id and self.type == 'tech_tool':
            product_uom_id = self.uom_id.id
            pol_qtys = self.env['purchase.order.line'].search_group(fields=['uom_qty', 'uom_id'],
                                            groupby=['uom_id'],
                                            args=[('purchase_order_id.state', 'not in', ('draft', 'cancel')),
                                                  ('product_id', '=', self.id),
                                                  ('purchase_type', '!=', 'open')],
                                            sum='uom_qty',
                                            return_dict=True)
            for pol_qty in pol_qtys:
                if product_uom_id == pol_qty['uom_id']:
                    qty += pol_qty['uom_qty']
                else:
                    qty += self.env['product.uom']._compute_qty(pol_qty['uom_id'], pol_qty['uom_qty'], 
                                                                to_uom_id=self.uom_id.id, with_raise=True, with_round=False)

        self.nb_purchased_tool =  qty 
    

    def _search_search_by_sinfo(self, operator, value):
        """
            Recherche par référencement
        """ 
        query = """
            SELECT 
              product_id 
            FROM 
              product_supplierinfo s
              JOIN res_partner p ON s.partner_id = p.id
            WHERE
              p.name ilike '%%%(value)s%%'
              OR p.reference ilike '%%%(value)s%%'
            """%({'value': value})
        self.env.cr.execute(query)
        res_ids = self.env.cr.fetchall()
        if res_ids:
            res = [x[0] for x in res_ids]
        else:
            res = []
            
        return [('id', 'in', res)]
    
    
    @api.one
    def _compute_search_by_sinfo(self):
        self.search_by_sinfo = False
    

    def _search_search_by_sname(self, operator, value):
        """
            Permet de récupérer les produits à partir d'un code/nom produit fournisseur
            et éventuellement d'un fournisseur
        """ 
        context = self.env.context
        query = """
            SELECT 
              product_id 
            FROM 
              product_supplierinfo
            WHERE
              (supp_product_code ilike '%%%(value)s%%'
              OR supp_product_name ilike '%%%(value)s%%')
            """%({'value': value})
        
        if context.get('supplier_purchase_order') and context.get('partner_id'):
            where_partner = " AND partner_id = %s"%(context['partner_id'])
            query = "%s %s"%(query, where_partner)
            
        self.env.cr.execute(query)
        res_ids = self.env.cr.fetchall()
        if res_ids:
            res = [x[0] for x in res_ids]
        else:
            res = []
            
        return [('id', 'in', res)]
    
    
    @api.one
    def _compute_search_by_sname(self):
        self.search_by_sname = False
        
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    # Generalities
    eig_code = fields.Char(string='Economic Interest Group', size=32, required=False, help="This is the Economic Interest Group code, "
                    "corresponding to the common code when passing by a central purchasing")
    purchase_responsible_id = fields.Many2one('res.users', string='Purchase responsible', required=False, ondelete='restrict', help="Supply "
                    "manager. When the scheduler will launch a purchase request, it will be to its name.")
    purchase_family_id = fields.Many2one('purchase.family', string='Purchase family', required=False, ondelete='restrict', help="Correspond "
                    "with the products categories for purchases")
    purchase_remainder_percentage = fields.Float(string='Remainder percentage', default=0.0, required=False, help="During a partial "
                    "shipment, if the remainder is less than or equal to this field, the remainder will be disabled by default")
    free_purchase = fields.Boolean(string='Free purchase', default=False)
    eoq = fields.Float(string='Economic order quantity', default=1.0, required=False)
    cost_method = fields.Selection('_cost_method_get', string='Cost method', required=False)
    purchase_cost_price = fields.Float(string='Cost price', default=0.0, digits=dp.get_precision('Product Price'), required=False, compute='_compute_purchase_cost_price', store=False)
    purchase_cost_price_manual = fields.Float(string='Cost price', default=0.0, digits=dp.get_precision('Product Price'), required=False)
    
    # Purchase parameters
    uop_id = fields.Many2one('product.uom', string='UoP', required=False, ondelete='restrict', help='Unit of Purchase')
    uop_category_id = fields.Many2one('product.uom.category', string='UoP category', required=False, ondelete='set null')
    purchase_uoi_id = fields.Many2one('product.uom', string='UoI', required=False, ondelete='restrict', help='Unit of Invoice')
    purchase_multiple_qty = fields.Float(string='Multiple qty', digits=dp.get_precision('Product quantity'), help="Expressed in "
                    "the purchase unit", default=0.0)
    purchase_min_qty = fields.Float(string='Min qty', digits=dp.get_precision('Product quantity'), default=0.0, help="This value is optional "
                    "and not be filled in a systematic way. It must be filled for some references when good reasons justify it's use. "
                    "This is the preferential quantity that we wish to supply. This value is used by the system to make supply proposition." 
                    "To propose a supply quantity, the system consider the maximum between:\n"
                    "-the need (minimum stock - virtual stock)\n"
                    "-the supply minimum for the referent supplier\n"
                    "-the economic order quantity\n"
                    "The system round up the result to the superior multiple if the referent supplier imposed the respect of a multiple. "
                    "Be careful to only use this value when this is necessary (poor value for the product, reception control complex and "
                    "costly, production request to supply lots with a given size). This value allows to increase the ordered quantities "
                    "in some products. This value must be used with intelligence (and only when necessary) because it increase your stock "
                    "level.")
    purchase_factor = fields.Float(string='Factor', default=1.0, required=False)
    purchase_divisor = fields.Float(string='Divisor', default=1.0, required=False)
    purchase_factor_help = fields.Char(string='Factor help', compute='_compute_purchase_factor_help')
    inv_purchase_factor_help = fields.Char(string='Inverse factor help', compute='_compute_inv_purchase_factor_help')
    packaging_id = fields.Many2one('product.packaging', string='Packaging', required=False, ondelete='restrict')
    default_price = fields.Float(string='Default price', default=0.0, required=False)
    free_supply_delay = fields.Integer(string='Supply delay', default=0, required=False)

    # Suppliers    
    sinfo_ids = fields.One2many('product.supplierinfo', 'product_id',  string='Supplier information')
    search_by_sinfo = fields.Char(string='Supplier information', size=128, store=False, compute='_compute_search_by_sinfo', search='_search_search_by_sinfo')
    search_by_sname = fields.Char(string='Supplier product name/code', size=128, store=False, compute='_compute_search_by_sname', search='_search_search_by_sname')

    # Note
    purchase_note = fields.Text(string='Purchase note')
    
    # Outils techniques
    nb_purchased_tool = fields.Integer(string='Nb of purchased tools', compute='_compute_nb_purchased_tool')
        
        
    @api.one
    @api.constrains('uop_id', 'sinfo_ids', 'dual_unit', 'dual_unit_type', 'uom_id', 'sec_uom_id')
    def check_uop(self):
        """
            Verifie la cohérence entre l'UoM et l'UoP
            :type self: product
            :return: True
            :rtype: bool
        """
        if self.purchase_ok:
            ref_categ = False
            simple = True
            # Si produit de simple unité: La catégorie de référence est la catégorie de l'UoM
            if not self.dual_unit:
                ref_categ = self.uom_id.category_id.id
            # Si produit de double unité variable: La catégorie de référence est la catégorie du second l'UoM
            elif self.dual_unit_type == 'variable':
                simple = False
                ref_categ = self.sec_uom_id.category_id.id
             
            if ref_categ:
                # Si achat libre verification de l'UoP de la fiche produit
                if self.free_purchase:
                    if self.uop_id and self.uop_id.category_id.id != ref_categ:
                        if simple:
                            raise ValidationError("The unit of purchase category must be the same as the unit of measure category")
                        else:
                            raise ValidationError("The unit of purchase category must be the same as the second unit of measure category")
                # Si NON achat libre verification de l'UoP des sinfo
                else:
                    for sinfo in self.sinfo_ids:
                        if sinfo.uop_id.category_id.id != ref_categ:
                            if simple:
                                raise ValidationError("The unit of purchase category must be the same as the unit of measure category")
                            else:
                                raise ValidationError("The unit of purchase category must be the same as the second unit of measure category")
             
        return True
        
        
    @api.onchange('free_purchase')
    def onchange_free_purchase(self):
        """
            Si achat libre coché: UoP de la fiche produit = UoM
            Si achat libre décoché: UoP de la fiche produit vidé
        """
        if self.free_purchase:
            self.uop_id = self.uom_id
        else:
            self.uop_id = False
        
        
    @api.onchange('uop_id')
    def onchange_uop_id(self):
        """
            Mise à jour de l'UoI et de la catégorie au auchangement de l'UoP
        """
        self.uop_category_id = self.uop_id and self.uop_id.category_id or False 
        self.purchase_uoi_id = self.uop_id
        
        
    def get_default_supply_delay_purchase(self, return_date=False, hours=False):
        if self.free_purchase:
            if return_date:
                calendar = self.env.user.company_id.partner_id.calendar_id
                res = self.free_supply_delay, calendar.get_date(fields.Date.today(), self.free_supply_delay, hours=hours)
            else:
                res = self.free_supply_delay
                
        elif self.sinfo_ids:
            sinfo = self.sinfo_ids[0]
            if return_date:
                calendar = sinfo.partner_id.calendar_id
                res = sinfo.delivery_delay, calendar.get_date(fields.Date.today(), sinfo.delivery_delay, hours=hours)
            else:
                res = sinfo.delivery_delay
            
        else:
            res = super(product_product, self).get_default_supply_delay_purchase(return_date=return_date)
            
        return res

        
    def get_sinfo_query(self, product_id, state, partner_state, partner_id=False, property_ids=None, without_prop=False):
        where ='''s.state = '%s' AND 
                  p.state = '%s' AND 
                  product_id = %d '''%(state, partner_state, product_id)
        if partner_id:
            where = '%s AND partner_id = %d'%(where, partner_id) 
        if property_ids:
            categ_prop_dict = {}
            for property_id in property_ids:
                if property_id.purchase:
                    if property_id.category_id.id in categ_prop_dict:
                        categ_prop_dict[property_id.category_id.id].append(property_id.id)
                    else:
                        categ_prop_dict[property_id.category_id.id] = [property_id.id]
            
            # Selection des propriétés
            subquery = False
            for prop_ids in categ_prop_dict.values():
                if len(prop_ids) > 1:
                    if subquery:
                        subquery = '%s AND (SELECT true FROM product_supplierinfo_purchase_property_rel rel where s.id = rel.product_supplierinfo_id and rel.purchase_property_id IN %s LIMIT 1)'%(subquery, str(tuple(prop_ids)))
                    else:
                        subquery = '(SELECT true FROM product_supplierinfo_purchase_property_rel rel where s.id = rel.product_supplierinfo_id and rel.purchase_property_id IN %s LIMIT 1)'%(str(tuple(prop_ids)))
                        
                else:
                    if subquery:
                        subquery = '%s AND (SELECT true FROM product_supplierinfo_purchase_property_rel rel where s.id = rel.product_supplierinfo_id and rel.purchase_property_id = %d LIMIT 1)'%(subquery, prop_ids[0])
                    else:
                        subquery = '(SELECT true FROM product_supplierinfo_purchase_property_rel rel where s.id = rel.product_supplierinfo_id and rel.purchase_property_id = %d LIMIT 1)'%(prop_ids[0])
            if subquery:   
                where = '''%(where)s AND (%(subquery)s)
                
            '''%({'where': where, 'len': len(property_ids.ids), 'subquery': subquery})
        elif not without_prop:
            where = '%s AND not COALESCE((SELECT true FROM product_supplierinfo_purchase_property_rel rel WHERE rel.product_supplierinfo_id = s.id LIMIT 1), false)'%(where) 
            
        return '''
            SELECT 
              s.id
            FROM 
              product_supplierinfo s 
              JOIN res_partner p ON p.id = s.partner_id
            WHERE 
                %s
            ORDER BY s.sequence, s.id
            LIMIT 1
        '''%(where)
        
        
    def get_sinfo(self, partner_id=False, property_ids=False, state_dev=False):
        """
            :param partner_id: Id d'un partner
            :type partner_id: int
            :param property_ids: Ids des propriétés d'achat
            :type property_ids: list
            :param state_dev: Permet de rechercher un product.supplierinfo à l'état développement s'il y en a pas à létat actif
            :type state_dev: Boolean
            :return: Le supplierinfo avec la séquence la plus basse
            :rtype: recordset
        """
        if isinstance(property_ids, list):
            property_ids = self.env['purchase.property'].browse(property_ids)

        self.env.cr.execute(self.get_sinfo_query(self.id, 'active', 'qualified', partner_id=partner_id, property_ids=property_ids))
        res = self.env.cr.fetchone()
        if not res:
            self.env.cr.execute(self.get_sinfo_query(self.id, 'active', 'qualified', partner_id=partner_id, property_ids=property_ids, without_prop=True))
            res = self.env.cr.fetchone()
            
        if not res and state_dev:
            self.env.cr.execute(self.get_sinfo_query(self.id, 'development', 'qualified', partner_id=partner_id, property_ids=property_ids))
        
        return res and self.env['product.supplierinfo'].browse(res[0]) or res
    
    
    def get_purchase_uoms(self, sinfo=False, partner_id=False, property_ids=False, with_factor=False, with_pinfo=False):
        """
            :type self: product.product
            :param partner_id: Id d'un partner
            :type partner_id: int
            :param property_ids: Id des propriétés
            :type property_ids: Many2many
            :param with_factor: Si True, calcul des facteurs
            :type with_factor: boolean
            :return: l'UoP et l'UoI sous forme {'uop_id': ..., 'uoi_id': ...}
            :rtype: dict
        """
        if self.free_purchase:
            res = {'sec_uom_id': self.uop_id, 'uoi_id': self.purchase_uoi_id}
            if with_factor:
                res.update({'factor': self.purchase_factor, 'divisor': self.purchase_divisor})
        else:
            if not sinfo:
                sinfo = self.get_sinfo(partner_id=partner_id, property_ids=property_ids, state_dev=False)
                        
            if sinfo:
                res = {'sec_uom_id': sinfo.uop_id, 'uoi_id': sinfo.uoi_id}
                if with_pinfo:
                    res['sinfo_id'] = sinfo
                
                if with_factor:
                    res.update({'factor': sinfo.factor, 'divisor': sinfo.divisor})
            else:
                res = {}
            
        return res

    
    def get_price_purchase(self, supplier, properties=False, currency_price_return=False, qty_uom=False, uom=False, qty_uop=False, uop=False, date='', type='price', force_price=False, state_dev=False, with_uoi=False):
        """
            :param supplier: recordset d'un partner
            :type supplier: recordset
            :param properties: Id des propriétés
            :type properties: Many2many
            :param currency_price_return: recordset de la devise dans laquelle on souhaite retouner le prix
            :type currency_price_return: recordset
            :param qty_uom: quantité en unité de gestion
            :type qty_uom: float
            :param uom: recordset de l'unité de gestion
            :type uom: recordset
            :param qty_uop: quantité en unité d'achat
            :type qty_uop: float
            :param uop: recordset de l'unite d'achat
            :type uop: recordset
            :param date: date pour la liste de prix
            :type date: date
            :param type: type si l'on veut retourner un prix ou l'id de la pricelist
            :type type: string
            :param force_price: Permet de retourner un prix même si la quantité est inférieure à la qty du référencement pour éviter de retourner un prix à 0, on prend le prix de la première ligne
            :type force_price: Boolean
            :param state_dev: Permet de rechercher dans les listes prix à l'état développement s'il y en a pas à létat actif
            :type state_dev: Boolean
            :return si type == pricelist: le recordset pricelist
            :rtype: recordset
            :param with_uoi: Si on lui passe une unité de prix, va vérifier si elle est identique à l'unité de prix du 
                             produit ou du référencement, si pas le cas calcule le prix dans la nouvelle unité
            :type with_uoi: recordset de l'unite de prix
            :return si non: le prix
            :rtype: float
        """
        price = 0
        res_pricelist = False
        qty = 0.0
        product = self
        devise_price = False
        product_uoi = False
        #Si le produit est standard
        if product.free_purchase:
            price = product.default_price
            product_uoi = product.purchase_uoi_id
            #Dans le cas d'un produit libre, on récupère le prix dans la devise de la société du produit
            company = product.company_id
            devise_price = company and company.currency_id or False
        else:
            if supplier:
                property_ids = properties and properties.ids or False
                supp_info = self.get_sinfo(partner_id=supplier.id, property_ids=property_ids, state_dev=state_dev)
                if supp_info:
                    pricelist_rcs = []
                    product_uoi = supp_info.uoi_id
                    devise_price = supp_info.currency_id
                    if isinstance(qty_uop,float):
                        qty = qty_uop
                        if uop:
                            uop_supp = isinstance(uop, int) and uop or uop.id
                        else:
                            uop_supp = supp_info.uop_id.id
                        if uop_supp != supp_info.uop_id.id:
                            qty = self.env['product.uom']._compute_qty(uop_supp, qty_uop, to_uom_id=supp_info.uoi_id.id, with_raise=True)
                    elif isinstance(qty_uom,float):
                        if uom:
                            uom_product = uom
                        else:
                            uom_product = product.uom_id
                        qtys = product.get_qtys(qty_uom, 
                                     uom_id=uom_product, 
                                     sec_uom_id=supp_info.uop_id, 
                                     uoi_id=supp_info.uoi_id, 
                                     by_field='uom', 
                                     dual_unit=product.dual_unit, 
                                     dual_unit_type=product.dual_unit_type, 
                                     factor=supp_info.factor, 
                                     divisor=supp_info.divisor,
                                     with_raise=True,
                                     with_round=False)
                        qty = qtys.get('sec_uom_qty',0.0)
                    else:
                        raise except_orm('Error', 'indicate the quantity and unit of management or quantity and unit price!')
                    
                    qty = supp_info.return_qty_gergonne(qty)
                    if not date:
                        date = fields.Date.today()
                        
                    pricelist_rcs = self.env['pricelist.supplierinfo'].search([
                                       '&', '&', '&', 
                                       '|', ('date_start', '<=', date), ('date_start', '=', False),
                                       '|', ('date_stop', '>=', date), ('date_stop', '=', False),
                                       ('sinfo_id', '=', supp_info.id), 
                                       ('min_qty', '<=', qty)
                                   ], limit=1, order='min_qty desc')
                    
                    if not pricelist_rcs and force_price:
                        pricelist_rcs = self.env['pricelist.supplierinfo'].search([
                                           '&', '&', 
                                           '|', ('date_start', '<=', date), ('date_start', '=', False),
                                           '|', ('date_stop', '>=', date), ('date_stop', '=', False),
                                           ('sinfo_id', '=', supp_info.id)
                                        ], limit=1, order='min_qty asc')
                    
                    if pricelist_rcs:
                        price = pricelist_rcs.price
                        res_pricelist = pricelist_rcs
        
        #Si l'unité de prix demandée est différente de l'unité de prix du produit, on 
        #recalcule le prix dans la nouvelle unité 
        if with_uoi and product_uoi and product_uoi != with_uoi:
            #On commence par passer le prix dans l'unité de référence
            if product_uoi.type == 'smaller':
                price /= product_uoi.factor
            elif product_uoi.type == 'bigger':
                price *= product_uoi.factor
            
            #Puis on calcule le nouveau prix en prenant en compte la nouvelle
            #unité de prix
            if with_uoi.type == 'bigger':
                price /= with_uoi.factor
            elif with_uoi.type == 'smaller':
                price *= with_uoi.factor
        
        if type == 'pricelist':
            return res_pricelist
        else:  
            if currency_price_return and devise_price:
                price = self._calcul_price_rate_devise(devise_price, price, currency_price_return)
                
            return price
    

    def _simulate_availability_buy(self, qty, supplier_id, start_date):
        """
            Fonction qui permet des calculer la date de disponibilité de la simulation
        """
        virtual_stock, available_stock = self.get_available_stock(return_real_stock=True)
        # Stock virtuel < besoin => delai fournisseur
        if virtual_stock < qty:
            if supplier_id:
                calendar = supplier_id.calendar_id
                ret = calendar.get_date(fields.Date.today(), self.get_sinfo(supplier_id).delivery_delay)
            else:
                calendar = self.env.user.company_id.partner_id.calendar_id
                ret = calendar.get_date(fields.Date.today(), self.get_default_supply_delay_purchase())
        # Stock réel et stock virtuel >= besoin => AJD
        elif available_stock >= qty:
            ret = fields.Datetime.now()
        # Stock réel < besoin et stock virtuel >= besoin => Calcul date besoin
        else:
            ret = self.get_date_last_stock_min(self.env.user.company_id.warehouse_id.stock_location_id, qty, inverse=True)
                    
        return ret
    
    
    def get_draft_purchase_qty(self):
        """
            Renvoie la quantité d'achat brouillon (hors commandes ouvertes)
        """
        res = 0.0
        pol_obj = self.env['purchase.order.line']
        uom_obj = self.env['product.uom']
        product_uom_id = self.uom_id.id
        pol_qtys = pol_obj.search_group(fields=['uom_qty', 'uom_id'],
                                        groupby=['uom_id'],
                                        args=[('purchase_order_id.state', '=', 'draft'),
                                              ('product_id', '=', self.id),
                                              ('purchase_type', '!=', 'open')],
                                        sum='uom_qty',
                                        return_dict=True)
        for pol_qty in pol_qtys:
            if product_uom_id == pol_qty['uom_id']:
                res += pol_qty['uom_qty']
            else:
                res += uom_obj._compute_qty(pol_qty['uom_id'], pol_qty['uom_qty'], to_uom_id=self.uom_id.id, with_raise=True, with_round=False)

        return res 
    
    def additional_function_domain(self, arg):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de mrp_routing_line
        """
        arg0, arg1, arg_1 = super(product_product, self).additional_function_domain(arg)
        if arg[0] == 'purchase_product_supplierinfo':
            if arg[-1]:
                arg0 = 'id'
                arg1 = 'in'
                product_ids = self.env['product.supplierinfo'].search_group(fields=['product_id'], 
                                                                            groupby=['product_id'], 
                                                                            args=[('partner_id', '=', arg[-1]), ('state', '!=', 'obsolete')])
                arg_1 = product_ids
            else:
                arg_1 = []
                
        return arg0, arg1, arg_1
    
    
    def update_args_modified(self, name, args_modified, operator='ilike'):
        """
            Permet de rechercher le produit par son code ou son nom fournisseur
        """
        args_modified = super(product_product, self).update_args_modified(name, args_modified, operator)
        context = self.env.context
        product_ids = []
        new_args = []
        if context and context.get('supplier_purchase_order') and context.get('partner_id'):
            sup_rcs = self.env['product.supplierinfo'].search(['|', ('supp_product_code', operator, name), ('supp_product_name', operator, name), ('partner_id', '=', context['partner_id'])])
            if sup_rcs:
                product_ids.extend([sup['product_id'] for sup in sup_rcs.read_light(['product_id'])])
                new_args = ['|', ('id', 'in', product_ids)]
        
        new_args.extend(args_modified)
        return new_args
    
    
    @api.multi
    def write(self, vals=None):
        """
            Méthode de coût ne peut pas être basée sur la liste fournisseur s'il est achat libre
        """
        res = super(product_product, self).write(vals=vals)
        for product in self:
            if product.cost_method in ('supplier_pl', 'supplier_pl_eoq') and product.free_purchase:
                raise except_orm('Error', _('The product can not have a cost method based on the supplier lists if free purchase.'))
                
        return res
    
    
    @api.model
    def create(self, vals):
        res = super(product_product, self).create(vals=vals)
        if res.cost_method in ('supplier_pl', 'supplier_pl_eoq') and res.free_purchase:
            raise except_orm('Error', _('The product can not have a cost method based on the supplier lists if free purchase.'))
            
        return res
    
        
        
class pricelist_supplierinfo(models.Model):
    """
    Pricelist supplierinfo
    """
    _name = 'pricelist.supplierinfo'
    _description = 'Pricelist supplierinfo'
    _order = 'min_qty asc'
    _rec_name = 'sinfo_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    sinfo_id = fields.Many2one('product.supplierinfo', string='Partner information', required=True, ondelete='cascade', select=True)
    min_qty = fields.Float(string='Quantity', default=0.0, required=True, select=True, help='The minimal quantity to trigger this rule, expressed in the supplier Unit of Measure if any or in the default Unit of Measure of the product otherwise.')
    price = fields.Float(string='Unit price', default=0.0, required=True, digits=dp.get_precision('Product Price'), help='This price will be considered as a price for the supplier Unit of price if any or the default Unit of Price of the product otherwise.')
    date_start = fields.Date(select=True)
    date_stop = fields.Date(select=True)



class product_supplierinfo(models.Model):
    '''
   Product supplierinfo
    '''
    _name = 'product.supplierinfo'
    _description = 'Product supplierinfo'
    _rec_name = 'partner_id'
    _order = 'sequence, id'
    
    @api.one
    @api.constrains('pricelist_ids')
    def _check_date(self):
        """
            Test qu'il n'y ai pas de chevauchement entre deux liste de prix ayant la meme quantité minimum
        """
        obj_pricelist = self.env['pricelist.supplierinfo']
        for line in self.pricelist_ids:
            if line.date_start and line.date_stop:
                #On vérifie que la date de fin ne soit pas inférieure à la date de début
                if line.date_start > line.date_stop:
                    raise except_orm('Error', _('You cannot have a start date superior to the end date!'))
                
                have_overlap = bool(obj_pricelist.search(['&', '&', '&',('min_qty', '=', line.min_qty),
                                                                        ('id','!=', line.id), 
                                                                        ('sinfo_id', '=', line.sinfo_id.id),
                                                                        '|', '&', ('date_start', '>=', line.date_start), 
                                                                        ('date_start', '<=', line.date_stop),
                                                                        '&', ('date_stop', '>=', line.date_start), 
                                                                        ('date_stop', '<=', line.date_stop)], limit=1))
            elif line.date_start:
                have_overlap = bool(obj_pricelist.search(['&', '&', '&',('min_qty', '=', line.min_qty),
                                                                        ('id','!=', line.id), 
                                                                        ('sinfo_id', '=', line.sinfo_id.id), 
                                                                        '|',('date_start', '>=', line.date_start), 
                                                                        ('date_stop', '>=', line.date_start)], limit=1))
            elif line.date_stop:
                have_overlap = bool(obj_pricelist.search(['&', '&', '&',('min_qty', '=', line.min_qty),
                                                                        ('id','!=', line.id), 
                                                                        ('sinfo_id', '=', line.sinfo_id.id), 
                                                                        '|',('date_start', '<=', line.date_stop), 
                                                                        ('date_stop', '<=', line.date_stop)], limit=1))
            else:
                have_overlap = bool(obj_pricelist.search(['&', '&',('min_qty', '=', line.min_qty),
                                                                   ('id','!=', line.id), 
                                                                   ('sinfo_id', '=', line.sinfo_id.id)], limit=1))
            if have_overlap:
                raise except_orm('Error', _('You cannot have 2 pricelists versions that overlap!'))
            
        return True
    
    
    @api.one
    @api.depends('factor', 'divisor', 'uoi_id')
    def _compute_purchase_factor_help(self):
        self.factor_help = self.env['product.product'].factor_help_compute(self.product_id.uom_id, self.uop_id, self.factor, self.divisor) 
    
    
    @api.one
    @api.depends('factor', 'divisor', 'uoi_id')
    def _compute_inv_sale_factor_help(self):
        self.inv_factor_help = self.env['product.product'].inv_factor_help_compute(self.uop_id, self.product_id.uom_id, self.factor, self.divisor)

    
    @api.model
    def _state_get(self):
        return [
                    ('active', _('Active')),
                    ('development', _('In development')),
                    ('obsolete', _('Obsolete')),
                       ]


    @api.one
    @api.depends('pricelist_ids')
    def _compute_flag_pricelist(self):
        """
            On coche le booléen si on détecte plusieurs lignes de prix
            correspondant à la date du jour
        """
        now = fields.Date.today()
        count = 0
        for price in self.pricelist_ids:
            if not price.date_start and not price.date_stop:
                count += 1
            elif price.date_start and price.date_stop and price.date_start <= now <= price.date_stop:
                count += 1
            elif price.date_start and not price.date_stop and price.date_start <= now:
                count += 1
            elif not price.date_start and price.date_stop and price.date_stop >= now:
                count += 1
            
        if count > 1:
            self.flag_pricelist = True
        else:
            self.flag_pricelist = False
            
            
    @api.one
    @api.depends('pricelist_ids')
    def _compute_first_price(self):
        """
            Permet de calculer la première quantité et et le premier prix trouvés
            correspondant à la date du jour 
        """
        now = fields.Date.today()
        first_price = 0
        first_quantity = 0
        for price in self.pricelist_ids:
            if not price.date_start and not price.date_stop:
                first_price = price.price
                first_quantity = price.min_qty
                break
            elif price.date_start and price.date_stop and price.date_start <= now <= price.date_stop:
                first_price = price.price
                first_quantity = price.min_qty
                break
            elif price.date_start and not price.date_stop and price.date_start <= now:
                first_price = price.price
                first_quantity = price.min_qty
                break
            elif not price.date_start and price.date_stop and price.date_stop >= now:
                first_price = price.price
                first_quantity = price.min_qty
                break
            
        self.first_price = first_price
        self.first_quantity = first_quantity
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    # General
    product_id = fields.Many2one('product.product', string='Product', required=True, select=True, ondelete='cascade')
    sequence = fields.Integer(default=1, required=True)
    partner_id = fields.Many2one('res.partner', string='Partner', required=True, select=True, auto_join=True, ondelete='restrict')
    state = fields.Selection('_state_get', string='State', required=True, select=True, default='active')
    property_ids = fields.Many2many('purchase.property', string='Properties', domain=[('purchase', '=', True)])
    imposed_by_id = fields.Many2one('res.partner', string='Imposed by', required=False, ondelete='restrict', domain=[('is_customer', '=', True)])
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, ondelete='restrict')
    company_id = fields.Many2one('res.company', string='Company', required=True, ondelete='restrict')
    supp_product_code = fields.Char(string='Supplier product code', size=128, required=False)
    uop_id = fields.Many2one('product.uom', string='UoP', required=True, ondelete='restrict', help='Unit of Purchase')
    uop_category_id = fields.Many2one('product.uom.category', string='UoP category', required=False, ondelete='restrict')
    uoi_id = fields.Many2one('product.uom', string='UoI', required=True, ondelete='restrict', help='Unit of Invoice')
    multiple_qty = fields.Float(string='Multiple qty', digits=dp.get_precision('Product quantity'), help="Expressed in purchase quantity",
                                default=0.0)
    min_qty = fields.Float(string='Min qty', digits=dp.get_precision('Product quantity'), help="Expressed in purchase quantity",
                           default=0.0)
    delivery_delay = fields.Integer(string='Delivery delay', default=0, required=False, help="Expressed in working day")
    supp_product_name = fields.Char(string='Supplier product name', size=128, required=False)
    packaging_id = fields.Many2one('product.packaging', string='Packaging', required=False, ondelete='restrict')
    factor = fields.Float(string='Factor', default=1.0, required=False)
    divisor = fields.Float(string='Divisor', default=1.0, required=False)
    factor_help = fields.Char(string='Factor help', compute='_compute_purchase_factor_help')
    inv_factor_help = fields.Char(string='Inverse factor help', compute='_compute_inv_sale_factor_help')
    pricelist_ids = fields.One2many('pricelist.supplierinfo', 'sinfo_id',  string='Pricelist', copy=True)
    flag_pricelist = fields.Boolean(string='Multiple price', compute='_compute_flag_pricelist')
    first_price = fields.Float(string='Price', compute='_compute_first_price')
    first_quantity = fields.Float(string='Quantity', compute='_compute_first_price')
    
    dual_unit = fields.Boolean(related='product_id.dual_unit', default=False, required=False, readonly=True)
    dual_unit_type = fields.Selection(related='product_id.dual_unit_type', required=False, readonly=True)
    sec_uom_category_id = fields.Many2one('product.uom.category', string='Sec UoM category',  related='product_id.sec_uom_category_id', 
                                          readonly=True)
    uom_category_id = fields.Many2one('product.uom.category', string='UoM category',  related='product_id.uom_category_id', readonly=True)
    
    # Note
    purchase_note = fields.Text(string='Purchase note')
    internal_note = fields.Text(string='Internal note')
    

# A decommenter lorsque le partner aurra un champ currency_id
#     @api.onchange('partner_id')
#     def onchange_partner_id(self):
#         self.currency_id = self.partner_id.currency_id
    
    
    @api.onchange('uop_id')
    def onchange_uop_id(self):
        self.uop_category_id = self.uop_id and self.uop_id.category_id or False 
        self.uoi_id = self.uop_id
        
        
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        self.currency_id = self.partner_id and self.partner_id.currency_id or False
    
    
    def additional_function_domain(self, arg):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de product_supplierinfo
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
        return super(product_supplierinfo,self).search(args=args_modified, offset=offset, limit=limit, order=order, count=count) 
    
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=1000):
        """
            Fonction name_search
        """
        args = self.compute_domain_args_sale(args)
        return super(product_supplierinfo, self).name_search(name=name, args=args, operator=operator, limit=limit)
    
    
    def return_qty_gergonne(self, qty):
        """
            Fonction pour gergonne qui permet de choisir le max entre la qty du besoin, la qty eoq du composant et la qty min du reférencement pour choisir le prix dans le référencement
        """
        return qty
    
    
    @api.multi
    @api.depends('partner_id', 'partner_id.name', 'partner_id.reference', 'product_id', 'product_id.code')
    def name_get(self):
        """
        """
        result = []
        for ref_sinfo in self:
            name = ''
            if ref_sinfo.product_id.code:
                name = '%s -'%(ref_sinfo.product_id.code)
                
            if ref_sinfo.partner_id.reference and ref_sinfo.partner_id.name:
                name = '%s [%s] %s'%(name, ref_sinfo.partner_id.reference, ref_sinfo.partner_id.name)
                
            result.append((ref_sinfo.id, name))
             
        return result


class purchase_property(models.Model):
    """
    purchase property
    """
    _inherit = 'purchase.property'
    def compute_domain_args_supplier(self, args):
        """
            Fonction appelée par le search afin de n'afficher que les propriétés des référencements fournisseurs
        """
        args2 = []
        for arg in args:
            if isinstance(arg, str) or (isinstance(arg, list) and arg[0] in ('!', '|', '&')):
                args2.append(arg)
                continue
            
            if arg[0] == 'sinfo_property_product':
                arg[0] = 'id'
                if isinstance(arg[-1], (tuple, list)):
                    product_id = arg[-1][0]
                    partner_id = arg[-1][1]
                else:
                    product_id = arg[-1]
                    partner_id = False
                    
                property_ids = []
                arg[-1] = property_ids
                if product_id:
                    product_datas = self.env['product.product'].browse(product_id).read(['purchase_ok', 'free_purchase', 'sinfo_ids'])[0]
                    if product_datas['purchase_ok'] and not product_datas['free_purchase'] and product_datas['sinfo_ids']:
                        for sinfo_datas in self.env['product.supplierinfo'].browse(product_datas['sinfo_ids']).read(['property_ids', 'partner_id'], load='_classic_write'):
                            if not partner_id or partner_id == sinfo_datas['partner_id']:
                                property_ids.extend(sinfo_datas['property_ids'])
                
            args2.append(arg)
            
        return args2
    

    @api.model
    def search(self,args=None, offset=0, limit=None, order=None, count=None):
        args = args or []
        args_modified = self.compute_domain_args_supplier(args)
        return super(purchase_property,self).search(args=args_modified, offset=offset, limit=limit, order=order, count=count)
    
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=1000):
        if not name == '':
            args.insert(0, (self._rec_name, operator, name))
            
        recs = self.search(args, limit=limit)
        return recs.name_get()
    
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False,lazy=True):
        domain = self.compute_domain_args_supplier(domain)
        return super(purchase_property, self).read_group(domain=domain, fields=fields, groupby=groupby, offset=offset, limit=limit, orderby=orderby,lazy=lazy)