# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
from openerp.addons.base_openprod.common import get_form_view

from openerp.tools.translate import _
import math
from openerp.exceptions import except_orm, ValidationError


def is_pair(x):
    return not x % 2


def check_ean(eancode):
    if not eancode:
        return True
    
    if len(eancode) != 13:
        return False
    
    try:
        int(eancode)
    except:
        return False
    
    oddsum = 0
    evensum = 0
    eanvalue = eancode
    reversevalue = eanvalue[::-1]
    finalean = reversevalue[1:]

    for i in range(len(finalean)):
        if is_pair(i):
            oddsum += int(finalean[i])
        else:
            evensum += int(finalean[i])
            
    total = (oddsum * 3) + evensum
    check = int(10 - math.ceil(total % 10.0)) % 10
    if check != int(eancode[-1]):
        return False
    
    return True


class product_product(models.Model):
    _inherit = 'product.product'
    _description = 'Product'
    _sql_constraints = [
        ('sale_divisor_gt_zero', 'CHECK (sale_divisor!=0)', 'The sale divisor cannot be 0!')
    ]
    
    
    @api.one
    @api.depends('sale_factor', 'sale_divisor', 'uos_id', 'uom_id')
    def _compute_sale_factor_help(self):
        self.sale_factor_help = self.factor_help_compute(self.uom_id, self.uos_id, self.sale_factor, self.sale_divisor) 
        
    
    @api.one
    @api.depends('sale_factor', 'sale_divisor', 'uos_id', 'uom_id')
    def _compute_inv_sale_factor_help(self):
        self.inv_sale_factor_help = self.inv_factor_help_compute(self.uos_id, self.uom_id, self.sale_factor, self.sale_divisor) 
    
    
    def _search_search_by_cinfo(self, operator, value):
        """
            Recherche par référencement
        """ 
        query = """
            SELECT 
              product_id 
            FROM 
              product_customerinfo c
              JOIN res_partner p ON c.partner_id = p.id
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
    
    
    def _search_search_by_cname(self, operator, value):
        """
            Permet de récupérer les produits à partir d'un code/nom produit client
            et éventuellement d'un client
        """ 
        context = self.env.context
        query = """
            SELECT 
              product_id 
            FROM 
              product_customerinfo
            WHERE
              (cust_product_code ilike '%%%(value)s%%'
              OR cust_product_name ilike '%%%(value)s%%')
            """%({'value': value})
        
        if context.get('customer_sale_order') and context.get('partner_id'):
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
    def _compute_search_by_cinfo(self):
        self.search_by_cinfo = False
    
    
    @api.one
    def _compute_search_by_cname(self):
        self.search_by_cname = False
        
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    # Generalities
    ean13 = fields.Char(string='EAN 13', size=13)
    sale_responsible_id = fields.Many2one('res.users', string='Sale responsible', required=False, ondelete='restrict')
    sale_family_id = fields.Many2one('sale.family', string='Sale family', required=False, ondelete='restrict')
    sale_remainder_percentage = fields.Float(string='Remainder percentage', default=0.0, required=False, help="Below this value, during "
                        "a shipment, the system don't create rest. For example, if we send 98% of the order and we have a 5% remainder, "
                        "we don't create a rest.")
    free_sale = fields.Boolean(string='Free sale', default=False)
    
    # Sale parameters
    uos_id = fields.Many2one('product.uom', string='UoS', required=False, ondelete='restrict', help='Unit of Sale')
    uos_category_id = fields.Many2one('product.uom.category', string='UoS category', required=False, ondelete='set null')
    sale_uoi_id = fields.Many2one('product.uom', string='UoI', required=False, ondelete='restrict', help='Expressed in the sale unity')
    sale_multiple_qty = fields.Float(string='Multiple qty', digits=dp.get_precision('Product quantity'), default=0.0)
    sale_min_qty = fields.Float(string='Min qty', digits=dp.get_precision('Product quantity'), help="The minimal quantity to sale", default=0.0)
    sale_factor = fields.Float(string='Factor', default=1.0, required=False, help="The factor and the divisor work together in order to "
                           "obtain a coherent round. If we enter a factor 1 and a divisor 3 with a unity of measure in gram, we will obtain: "
                           "1 piece = 0.33g")
    sale_divisor = fields.Float(string='Divisor', default=1.0, required=False, help="The factor and the divisor work together in order to "
                           "obtain a coherent round. If we enter a factor 1 and a divisor 3 with a unity of measure in gram, we will obtain: "
                           "1 piece = 0.33g")
    sale_factor_help = fields.Char(string='Factor help', compute='_compute_sale_factor_help')
    inv_sale_factor_help = fields.Char(string='Inverse factor help', compute='_compute_inv_sale_factor_help')
    packaging_id = fields.Many2one('product.packaging', string='Packaging', required=False, ondelete='restrict')
    sale_price = fields.Float(string='Sale price', default=0.0, required=False)
    free_delivery_delay = fields.Integer(string='Engagement delay', default=0, required=False)
    default_price = fields.Float(string='Default price', default=0.0, required=False)
    delay_confirm = fields.Boolean(string='Waiting delay confirmation', default=False, help='This product need a delay confirmation')
    
    # Customers
    cinfo_ids = fields.One2many('product.customerinfo', 'product_id',  string='Customer information')
    search_by_cinfo = fields.Char(string='Customer information', size=128, store=False, compute='_compute_search_by_cinfo', search='_search_search_by_cinfo')
    search_by_cname = fields.Char(string='Customer product name/code', size=128, store=False, compute='_compute_search_by_cname', search='_search_search_by_cname')

    # Note
    printed_sale_note = fields.Text(string='Sale note')
    
    
    @api.one
    @api.constrains('uos_id', 'cinfo_ids', 'dual_unit', 'dual_unit_type', 'uom_id', 'sec_uom_id')
    def check_uos(self):
        """
            Verifie la cohérence entre l'UoM et l'UoS
            :type self: product
            :return: True
            :rtype: bool
        """
        if self.sale_ok:
            ref_categ = False
            simple_unit = True
            # Si produit de simple unité: La catégorie de référence est la catégorie de l'UoM
            if not self.dual_unit:
                ref_categ = self.uom_id.category_id.id
            # Si produit de double unité variable: La catégorie de référence est la catégorie du second l'UoM
            elif self.dual_unit_type == 'variable':
                simple_unit = False
                ref_categ = self.sec_uom_id.category_id.id
             
            if ref_categ:
                # Si vente libre verification de l'UoS de la fiche produit
                if self.free_sale:
                    if self.uos_id and self.uos_id.category_id.id != ref_categ:
                        if simple_unit:
                            raise ValidationError("The unit of sale category must be the same as the unit of measure category")
                        else:
                            raise ValidationError("The unit of sale category must be the same as the second unit of measure category")
                # Si NON vente libre verification de l'UoS des cinfo
                else:
                    for cinfo in self.cinfo_ids:
                        if cinfo.uos_id.category_id.id != ref_categ:
                            if simple_unit:
                                raise ValidationError("The unit of sale category must be the same as the unit of measure category")
                            else:
                                raise ValidationError("The unit of sale category must be the same as the second unit of measure category")
             
        return True
    
    
    @api.onchange('free_sale')
    def onchange_free_sale(self):
        if self.free_sale:
            self.uos_id = self.uom_id
        else:
            self.uos_id = False
        
        
    @api.onchange('uos_id')
    def onchange_uos_id(self):
        self.uos_category_id = self.uos_id and self.uos_id.category_id or False 
        self.sale_uoi_id = self.uos_id
    
    
    @api.one
    @api.constrains('ean13')
    def _check_ean13(self):
        if not check_ean(self.ean13):
            raise Warning(_('Error: Invalid EAN code'))


    def get_cinfo_query(self, product_id, state, partner_state, partner_id=False, property_ids=None, without_prop=False):
        where ='''s.state = '%s' AND 
                  product_id = %d '''%(state, product_id)
        
        if partner_id:
            where = '%s AND partner_id = %d'%(where, partner_id) 
        else:
            where = '''%s AND p.state = '%s' '''%(where, partner_state) 
            
        if property_ids:
            categ_prop_dict = {}
            for property_id in property_ids:
                if property_id.sale:
                    if property_id.category_id.id in categ_prop_dict:
                        categ_prop_dict[property_id.category_id.id].append(property_id.id)
                    else:
                        categ_prop_dict[property_id.category_id.id] = [property_id.id]
            
            # Selection des propriétés
            subquery = False
            for prop_ids in categ_prop_dict.values():
                if len(prop_ids) > 1:
                    if subquery:
                        subquery = '%s AND (SELECT true FROM product_customerinfo_purchase_property_rel rel join purchase_property p on p.id = rel.purchase_property_id WHERE p.sale AND s.id = rel.product_customerinfo_id AND rel.purchase_property_id IN %s LIMIT 1)'%(subquery, str(tuple(prop_ids)))
                    else:
                        subquery = '(SELECT true FROM product_customerinfo_purchase_property_rel rel join purchase_property p on p.id = rel.purchase_property_id WHERE p.sale AND s.id = rel.product_customerinfo_id AND rel.purchase_property_id IN %s LIMIT 1)'%(str(tuple(prop_ids)))
                        
                else:
                    if subquery:
                        subquery = '%s AND (SELECT true FROM product_customerinfo_purchase_property_rel rel join purchase_property p on p.id = rel.purchase_property_id WHERE p.sale AND s.id = rel.product_customerinfo_id AND rel.purchase_property_id = %d LIMIT 1)'%(subquery, prop_ids[0])
                    else:
                        subquery = '(SELECT true FROM product_customerinfo_purchase_property_rel rel join purchase_property p on p.id = rel.purchase_property_id WHERE p.sale AND s.id = rel.product_customerinfo_id AND rel.purchase_property_id = %d LIMIT 1)'%(prop_ids[0])
            if subquery:   
                where = '''%(where)s AND (%(subquery)s)
                
            '''%({'where': where, 'len': len(property_ids.ids), 'subquery': subquery})
        elif not without_prop:
            where = '%s AND not COALESCE((SELECT true FROM product_customerinfo_purchase_property_rel rel WHERE rel.product_customerinfo_id = s.id LIMIT 1), false)'%(where) 
            
        return '''
            SELECT 
              s.id
            FROM 
              product_customerinfo s 
              JOIN res_partner p ON p.id = s.partner_id
            WHERE 
                %s
            ORDER BY s.sequence, s.id
            LIMIT 1
        '''%(where)
        #--------------------------------------
#         where ='''s.state = '%s' AND 
#                   p.state = '%s' AND 
#                   product_id = %d '''%(state, partner_state, product_id)
#         if partner_id:
#             where = '%s AND partner_id = %d'%(where, partner_id) 
#         if property_ids:
#             categ_prop_dict = {}
#             for property_id in property_ids:
#                 if property_id.category_id.id in categ_prop_dict:
#                     categ_prop_dict[property_id.category_id.id].append(property_id.id)
#                 else:
#                     categ_prop_dict[property_id.category_id.id] = [property_id.id]
#             
#             # Selection des propriétés
#             subquery = False
#             for prop_ids in categ_prop_dict.keys():
#                 if len(prop_ids) > 1:
#                     if subquery:
#                         subquery = '%s OR rel.purchase_property_id IN %s'%(str(prop_ids))
#                     else:
#                         subquery = 'rel.purchase_property_id IN %s'%(str(prop_ids))
#                         
#                 else:
#                     if subquery:
#                         subquery = '%s OR rel.purchase_property_id = %d'%(subquery, prop_ids[0])
#                     else:
#                         subquery = 'rel.purchase_property_id = %d'%(prop_ids[0])
#                     
#             where = '''%(where)s AND %(len)d = (SELECT count(*) FROM product_customerinfo_purchase_property_rel rel join purchase_property p on p.id = rel.purchase_property_id WHERE p.sale and rel.product_customerinfo_id = s.id ORDER BY s.id)
#                           AND %(len)d = (SELECT count(*) FROM product_customerinfo_purchase_property_rel rel join purchase_property p on p.id = rel.purchase_property_id WHERE p.sale and rel.product_customerinfo_id = s.id AND (%(subquery)s))
#             '''%({'where': where, 'len': len(property_ids), 'subquery': subquery}) 
#         elif not without_prop:
#             where = '%s AND not (SELECT True FROM product_customerinfo_purchase_property_rel rel join purchase_property p on p.id = rel.purchase_property_id WHERE p.sale and rel.product_customerinfo_id = s.id LIMIT 1)'%(where) 
#             
#         return '''
#             SELECT 
#               s.id
#             FROM 
#               product_customerinfo s 
#               JOIN res_partner p ON p.id = s.partner_id 
#             WHERE 
#                 %s
#             LIMIT 1
#         '''%(where)
        
        
    def get_cinfo(self, partner_id=False, property_ids=False):
        """
            :param partner_id: Id d'un partner
            :type partner_id: int
            :param property_ids: Ids des propriétés d'achat
            :type property_ids: list
            :param state_dev: Permet de rechercher un product.customerinfo à l'état développement s'il y en a pas à létat actif
            :type state_dev: Boolean
            :return: Le customerinfo avec la séquence la plus basse
            :rtype: recordset
        """
        if isinstance(property_ids, list):
            property_ids = self.env['purchase.property'].browse(property_ids)
        
        self.env.cr.execute(self.get_cinfo_query(self.id, 'active', 'qualified', partner_id=partner_id, property_ids=property_ids))
        res = self.env.cr.fetchone()
        if not res:
            self.env.cr.execute(self.get_cinfo_query(self.id, 'active', 'qualified', partner_id=partner_id, property_ids=property_ids, without_prop=True))
            res = self.env.cr.fetchone()
        
        return res and self.env['product.customerinfo'].browse(res[0]) or res

    
    def get_sale_uoms(self, cinfo=False, partner_id=False, property_ids=False, with_factor=False, with_pinfo=False):
        """
            :type self: product.product
            :param partner_id: Id d'un partner
            :type partner_id: int
            :param property_ids: Ids des propriétés
            :type property_ids: list
            :param with_factor: Si True, calcul des facteurs
            :type with_factor: boolean
            :return: l'UoP et l'UoI sous forme {'uop_id': ..., 'uoi_id': ...}
            :rtype: dict
        """
        if self.free_sale:
            res = {'sec_uom_id': self.uos_id, 'uoi_id': self.sale_uoi_id}
            if with_factor:
                res.update({'factor': self.sale_factor, 'divisor': self.sale_divisor})
        else:
            if not cinfo:
                cinfo = self.get_cinfo(partner_id=partner_id, property_ids=property_ids)
                        
            if cinfo:
                res = {'sec_uom_id': cinfo.uos_id, 'uoi_id': cinfo.uoi_id}
                if with_pinfo:
                    res['cinfo_id'] = cinfo
                    
                if with_factor:
                    res.update({'factor': cinfo.factor, 'divisor': cinfo.divisor})
            else:
                res = {}
            
        return res
    
    
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
        if sale_line_rcs:
            for parameter in sale_line_rcs.parameter_ids:
                if parameter.price_unit:
                    price += parameter.price_unit      
        
        return price
    
    
    def get_price_sale(self, customer, properties=False, currency_price_return=False, qty_uom=False, uom=False, qty_uos=False, uos=False, date='', type='price', force_price=False, with_uoi=False, sale_line_rcs=False):
        """
            :param customer: recordset d'un partner
            :type customer: recordset
            :param properties: recordset de propriétés
            :type properties: recordset
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
            :return si type == pricelist: le recordset pricelist
            :rtype: recordset
            :param force_price: Permet de retourner un prix même si la quantité est inférieure à la qty du référencement pour éviter de retourner un prix à 0, on prend le prix de la première ligne
            :type force_price: Boolean
            :param with_uoi: Si on lui passe une unité de prix, va vérifier si elle est identique à l'unité de prix du 
                             produit ou du référencement, si pas le cas calcule le prix dans la nouvelle unité
            :type with_uoi: recordset de l'unite de prix
            :return si non: le prix
            :rtype: float
        """
        price = 0
        qty = 0.0
        res_pricelist = False
        product = self
        product_uoi = False
        devise_price = False
        # Si le produit est standard
        if product.free_sale:
            qty = self.env['product.uom']._compute_qty_obj(uos, qty_uos, to_uom=uom, with_raise=True)
            price, devise_price = self.get_price_sale_standard(customer, qty)
            product_uoi = product.sale_uoi_id
        else:
            if customer:
                property_ids = properties and properties.ids or False
                cus_info = self.get_cinfo(partner_id=customer.id, property_ids=property_ids)
                if cus_info:
                    pricelist_rcs = []
                    product_uoi = cus_info.uoi_id
                    if isinstance(qty_uos,float):
                        qty = qty_uos
                        if uos:
                            uop_cus = uos.id
                        else:
                            uop_cus = cus_info.uos_id.id
                            
                        if uop_cus != cus_info.uos_id.id:
                            qty = self.env['product.uom']._compute_qty(uop_cus, qty_uos, to_uom_id=cus_info.uoi_id.id, with_raise=True)
                            
                    elif isinstance(qty_uom,float):
                        if uom:
                            uom_product = uom
                        else:
                            uom_product = product.uom_id

                        qtys = product.get_qtys(qty_uom, 
                                     uom_id=uom_product, 
                                     sec_uom_id=cus_info.uos_id, 
                                     uoi_id=cus_info.uoi_id, 
                                     by_field='uom', 
                                     dual_unit=product.dual_unit, 
                                     dual_unit_type=product.dual_unit_type, 
                                     factor=cus_info.factor, 
                                     divisor=cus_info.divisor,
                                     with_raise=True,
                                     with_round=False)
                        qty = qtys.get('uoi_qty',0.0)
                    else:
                        raise except_orm('Error', 'indicate the quantity and unit of management or quantity and unit price!')
                    
                    pricelist_rcs = self.env['pricelist.customerinfo'].search([('cinfo_id', '=', cus_info.id), 
                                                                               ('min_qty', '<=', qty)], order='min_qty desc')
                    
                    if not pricelist_rcs and force_price:
                        pricelist_rcs = self.env['pricelist.customerinfo'].search([('cinfo_id', '=', cus_info.id)], order='min_qty asc')
                        
                    if pricelist_rcs:
                        if not date:
                            date = fields.Date.today()
                        for pricelist in pricelist_rcs:
                            if pricelist.date_start and pricelist.date_stop and date >= pricelist.date_start and date <= pricelist.date_stop:
                                price = pricelist.price
                                res_pricelist = pricelist
                                break
                            elif pricelist.date_start and not pricelist.date_stop and date >= pricelist.date_start:
                                price = pricelist.price
                                res_pricelist = pricelist
                                break
                            elif pricelist.date_stop and not pricelist.date_start and date <= pricelist.date_stop:
                                price = pricelist.price
                                res_pricelist = pricelist
                                break
                            elif not pricelist.date_start and not pricelist.date_stop:
                                price = pricelist.price
                                res_pricelist = pricelist
                                break
        
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
        
        
        price = self.fonction_extra_price(price, sale_line_rcs)
        
        if type == 'pricelist':
            return res_pricelist
        else:  
            if currency_price_return and devise_price:
                price = self._calcul_price_rate_devise(devise_price, price, currency_price_return)
                
            return price
        
        
    def get_price_sale_standard(self, customer, qty):
        """
            Calcule le prix des produits free_sale
        """
        #Dans le cas d'un produit libre, on récupère le prix dans la devise de la société du produit
        company = self.company_id
        devise_price = company and company.currency_id or False
        price = self.sale_price
        return price, devise_price
    
    
    def get_origin_fields(self):
        res = super(product_product, self).get_origin_fields()
        res.append('sol_id')
        return res
    
    
    def additional_function_domain(self, arg):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de product_product
        """
        arg0, arg1, arg_1 = super(product_product, self).additional_function_domain(arg)
        if arg[0] == 'sale_product_customerinfo':
            if arg[-1]:
                arg0 = 'id'
                arg1 = 'in'
                customerinfo_ids = self.env['product.customerinfo'].search([('partner_id', '=', arg[-1]), ('state', '!=', 'obsolete')])
                arg_1 = [customerinfo.product_id.id for customerinfo in customerinfo_ids]
            else:
                arg_1 = []
                
        return arg0, arg1, arg_1
    
    
    def update_args_modified(self, name, args_modified, operator='ilike'):
        """
            Permet de rechercher le produit par son code ou son nom client
        """
        args_modified = super(product_product, self).update_args_modified(name, args_modified, operator)
        context = self.env.context
        product_ids = []
        new_args = []
        if context and context.get('customer_sale_order') and context.get('partner_id'):
            cust_rcs = self.env['product.customerinfo'].search(['|', ('cust_product_code', operator, name), ('cust_product_name', operator, name), ('partner_id', '=', context['partner_id'])])
            if cust_rcs:
                product_ids.extend([sup['product_id'] for sup in cust_rcs.read_light(['product_id'])])
                new_args = ['|', ('id', 'in', product_ids)]
        
        new_args.extend(args_modified)
        return new_args



class pricelist_customerinfo(models.Model):
    '''
   Pricelist customerinfo
    '''
    _name = 'pricelist.customerinfo'
    _description = 'Pricelist customerinfo'
    _order = 'min_qty asc'
    _rec_name = 'cinfo_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    cinfo_id = fields.Many2one('product.customerinfo', string='Partner information', required=True, ondelete='cascade', select=True)
    min_qty = fields.Float(string='Quantity', default=0.0, required=True, help='The minimal quantity to trigger this rule, expressed in the customer Unit of Measure if any or in the default Unit of Measure of the product otherwise.')
    price = fields.Float(string='Unit price', default=0.0, required=True, digits=dp.get_precision('Product Price'), help='This price will be considered as a price for the customer Unit of Price if any or the default Unit of Price of the product otherwise.')
    date_start = fields.Date()
    date_stop = fields.Date()
    
    
    
class product_customerinfo(models.Model):
    """
    Product customerinfo
    """
    _name = 'product.customerinfo'
    _description = 'Product customerinfo'
    _rec_name = 'partner_id'
    _order = 'sequence, id'
    
    
    @api.one
    @api.constrains('pricelist_ids')
    def _check_date(self):
        """
            Test qu'il n'y ai pas de chevauchement entre deux liste de prix ayant la meme quantité minimum
        """
        obj_pricelist = self.env['pricelist.customerinfo']
        for line in self.pricelist_ids:
            if line.date_start and line.date_stop:
                #On vérifie que la date de fin ne soit pas inférieure à la date de début
                if line.date_start > line.date_stop:
                    raise except_orm('Error', _('You cannot have a start date superior to the end date!'))
                
                have_overlap = bool(obj_pricelist.search(['&', '&', '&',('min_qty', '=', line.min_qty),
                                                                        ('id','!=', line.id), 
                                                                        ('cinfo_id', '=', line.cinfo_id.id),
                                                                        '|', '&', ('date_start', '>=', line.date_start), 
                                                                        ('date_start', '<=', line.date_stop),
                                                                        '&', ('date_stop', '>=', line.date_start), 
                                                                        ('date_stop', '<=', line.date_stop)], limit=1))
            elif line.date_start:
                have_overlap = bool(obj_pricelist.search(['&', '&', '&',('min_qty', '=', line.min_qty),
                                                                        ('id','!=', line.id), 
                                                                        ('cinfo_id', '=', line.cinfo_id.id), 
                                                                        '|',('date_start', '>=', line.date_start), 
                                                                        ('date_stop', '>=', line.date_start)], limit=1))
            elif line.date_stop:
                have_overlap = bool(obj_pricelist.search(['&', '&', '&',('min_qty', '=', line.min_qty),
                                                                        ('id','!=', line.id), 
                                                                        ('cinfo_id', '=', line.cinfo_id.id), 
                                                                        '|',('date_start', '<=', line.date_stop), 
                                                                        ('date_stop', '<=', line.date_stop)], limit=1))
            else:
                have_overlap = bool(obj_pricelist.search(['&', '&',('min_qty', '=', line.min_qty),
                                                                   ('id','!=', line.id), 
                                                                   ('cinfo_id', '=', line.cinfo_id.id)], limit=1))
            if have_overlap:
                raise except_orm('Error', _('You cannot have 2 pricelists versions that overlap!'))
            
        return True
    
    
    @api.one
    @api.depends('factor', 'divisor', 'uos_id')
    def _compute_sale_factor_help(self):
        self.factor_help = self.env['product.product'].factor_help_compute(self.product_id.uom_id, self.uos_id, self.factor, self.divisor) 
    
    
    @api.one
    @api.depends('factor', 'divisor', 'uos_id')
    def _compute_inv_factor_help(self):
        self.inv_factor_help = self.env['product.product'].inv_factor_help_compute(self.uos_id, self.product_id.uom_id, self.factor, self.divisor)

    
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
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade', select=True)
    sequence = fields.Integer(default=1, required=True)
    partner_id = fields.Many2one('res.partner', string='Partner', required=True, ondelete='restrict', select=True)
    state = fields.Selection('_state_get', string='State', required=True, default='active')
    property_ids = fields.Many2many('purchase.property', string='Properties', domain=[('sale', '=', True)])
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, ondelete='restrict')
    company_id = fields.Many2one('res.company', string='Company', required=True, ondelete='restrict')
    cust_product_code = fields.Char(string='Customer product code', size=128, required=False)
    uos_id = fields.Many2one('product.uom', string='UoS', required=True, ondelete='restrict', help='Unit of Sale')
    uos_category_id = fields.Many2one('product.uom.category', string='UoS Category', required=False, ondelete='restrict')
    uoi_id = fields.Many2one('product.uom', string='UoI', required=True, ondelete='restrict', help='Unit of Invoice')
    multiple_qty = fields.Float(string='Multiple qty', digits=dp.get_precision('Product quantity'), help="Expressed in purchase quantity",
                                default=0.0)
    min_qty = fields.Float(string='Min qty', digits=dp.get_precision('Product quantity'), help="Expressed in purchase quantity",
                           default=0.0)
    delivery_delay = fields.Integer(string='Engagement delay', default=0, required=False, help="Expressed in working day")
    cust_product_name = fields.Char(string='Customer product name', size=128, required=False)
    packaging_id = fields.Many2one('product.packaging', string='Packaging', required=False, ondelete='restrict')
    factor = fields.Float(string='Factor', default=1.0, required=False)
    divisor = fields.Float(string='Divisor', default=1.0, required=False)
    factor_help = fields.Char(string='Factor help', compute='_compute_sale_factor_help')
    inv_factor_help = fields.Char(string='Inverse factor help', compute='_compute_inv_factor_help')
    pricelist_ids = fields.One2many('pricelist.customerinfo', 'cinfo_id', string='Pricelist', copy=True)
    flag_pricelist = fields.Boolean(string='Multiple price', compute='_compute_flag_pricelist')
    first_price = fields.Float(string='Price', compute='_compute_first_price')
    first_quantity = fields.Float(string='Quantity', compute='_compute_first_price')
    
    dual_unit = fields.Boolean(related='product_id.dual_unit', required=False, default=False, readonly=True)
    dual_unit_type = fields.Selection(related='product_id.dual_unit_type', required=False, readonly=True)
    uom_category_id = fields.Many2one('product.uom.category', string='UoM category',  related='product_id.uom_category_id', readonly=True)
    sec_uom_category_id = fields.Many2one('product.uom.category', string='Sec UoM category',  related='product_id.sec_uom_category_id', 
                                          readonly=True)
    
    # Note
    sale_note = fields.Text(string='Sale note')
    internal_note = fields.Text(string='Internal note')
    
# A decommenter lorsque le partner aurra un champ currency_id
#     @api.onchange('partner_id')
#     def onchange_partner_id(self):
#         self.currency_id = self.partner_id.currency_id
        
 
    @api.onchange('uos_id')
    def onchange_uos_id(self):
        self.uos_category_id = self.uos_id and self.uos_id.category_id or False 
        self.uoi_id = self.uos_id
        
        
    def check_uom(self):
        
        return True
    
    
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        self.currency_id = self.partner_id and self.partner_id.currency_id or False
    
    
    def additional_function_domain(self, arg):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de product_customerinfo
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
        return super(product_customerinfo,self).search(args=args_modified, offset=offset, limit=limit, order=order, count=count) 
    
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=1000):
        """
            Fonction name_search
        """
        args = self.compute_domain_args_sale(args)
        return super(product_customerinfo, self).name_search(name=name, args=args, operator=operator, limit=limit)
    
    
    @api.multi
    @api.depends('partner_id', 'partner_id.name', 'partner_id.reference', 'product_id', 'product_id.code')
    def name_get(self):
        """
        """
        result = []
        for ref_cinfo in self:
            name = ''
            if ref_cinfo.product_id.code:
                name = '%s -'%(ref_cinfo.product_id.code)
                
            if ref_cinfo.partner_id.reference and ref_cinfo.partner_id.name:
                name = '%s [%s] %s'%(name, ref_cinfo.partner_id.reference, ref_cinfo.partner_id.name)
                
            result.append((ref_cinfo.id, name))
             
        return result
    
    

class parameter_dimension(models.Model):
    """ 
    Parameter Dimension 
    """
    _inherit = 'parameter.dimension'
    _description = 'Parameter Dimension'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    sale_order_line_id = fields.Many2one('sale.order.line', string='SoL', required=False, ondelete='cascade')
    model_id = fields.Many2one('parameter.dimension', required=False, ondelete='cascade')
    
    
    
class purchase_property(models.Model):
    """
    purchase property
    """
    _inherit = 'purchase.property'
    
    def compute_domain_args_customer(self, args):
        """
            Fonction appelée par le search afin de n'afficher que les propriétés des référencements client
        """
        args2 = []
        for arg in args:
            if isinstance(arg, str) or (isinstance(arg, list) and arg[0] in ('!', '|', '&')):
                args2.append(arg)
                continue
            
            if arg[0] == 'cinfo_property_product':
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
                    product_datas = self.env['product.product'].browse(product_id).read(['sale_ok', 'free_sale', 'cinfo_ids'])[0]
                    if product_datas['sale_ok'] and not product_datas['free_sale'] and product_datas['cinfo_ids']:
                        for cinfo_datas in self.env['product.customerinfo'].browse(product_datas['cinfo_ids']).read(['property_ids', 'partner_id'], load='_classic_write'):
                            if not partner_id or partner_id == cinfo_datas['partner_id']:
                                property_ids.extend(cinfo_datas['property_ids'])
                
            args2.append(arg)
            
        return args2
    

    @api.model
    def search(self,args=None, offset=0, limit=None, order=None, count=None):
        args = args or []
        args_modified = self.compute_domain_args_customer(args)
        return super(purchase_property,self).search(args=args_modified, offset=offset, limit=limit, order=order, count=count)
    
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=1000):
        if not name == '':
            args.insert(0, (self._rec_name, operator, name))
            
        recs = self.search(args, limit=limit)
        return recs.name_get()
    
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False,lazy=True):
        domain = self.compute_domain_args_customer(domain)
        return super(purchase_property, self).read_group(domain=domain, fields=fields, groupby=groupby, offset=offset, limit=limit, orderby=orderby,lazy=lazy)