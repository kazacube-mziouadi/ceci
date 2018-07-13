# -*- coding: utf-8 -*-
from openerp.tools.translate import _
from openerp import models, fields, api
from openerp.exceptions import except_orm, ValidationError
import openerp.addons.decimal_precision as dp


class kit_sale_line(models.TransientModel):
    """ 
        Kit sale line for kit sale wizard
    """
    _name = 'kit.sale.line'
    _description = 'Kit sale line for kit sale wizard'
    
    @api.one
    @api.depends('uop_qty', 'unity_price')
    def _compute_total_price(self):
        """
            Fonction permettant de calculer le prix total de la ligne de vente
        """
        self.total_price = self.uop_qty * self.unity_price
    
    
    def compute_product_unity(self, product_rs=False, kit_rs=False):
        """
            Fonction permettant de récupérer les informations des unités du produit 
        """
        uom_id = False
        sec_uom_id = False
        uop_id = False
        factor = 1
        divisor = 1
        if kit_rs and product_rs:
            sale_rs = kit_rs.sale_id
            if product_rs and kit_rs:
                customer = False
                if not product_rs.free_sale:
                    customer = product_rs.get_cinfo(partner_id=sale_rs.partner_id.id, property_ids=False)
                    
                uoms = product_rs.get_uoms(pinfo=customer, partner=sale_rs.partner_id, type='out', property_ids=False, with_factor=True)
                if uoms:
                    uom_id = uoms.get('uom_id', False)
                    sec_uom_id = uoms.get('sec_uom_id', False)
                    uop_id = uoms.get('uoi_id', False)
                    factor = uoms.get('factor', 1)
                    divisor = uoms.get('divisor', 1)
            
        return uom_id, sec_uom_id, uop_id, factor, divisor
        
    
    @api.one
    @api.depends('product_id')
    def _compute_product_unity(self):
        """
            Fonction permettant de récupérer les informations des unités du produit 
        """
        kit_rs = self.kit_id
        product_rs = self.product_id
        if kit_rs and product_rs:
            uom_id, sec_uom_id, uop_id, factor, divisor = self.compute_product_unity(product_rs, kit_rs)
            
        self.uom_id = uom_id
        self.sec_uom_id = sec_uom_id
        self.uop_id = uop_id
        self.factor = factor
        self.divisor = divisor
    
        
        
    @api.one
    @api.depends('product_id', 'sec_uom_qty')
    def _compute_product_qty(self):
        """
            Fonction permettant de calculer les quantités correspondantes en unité de gestion et de prix
        """
        product_rs = self.product_id
        uom_qty = 0
        uop_qty = 0
        if product_rs and self.uom_id and self.sec_uom_id and self.uop_id:
            qtys = product_rs.get_qtys(self.sec_uom_qty, 
                                     uom_id=self.uom_id, 
                                     sec_uom_id=self.sec_uom_id, 
                                     uoi_id=self.uop_id, 
                                     by_field='sec_uom', 
                                     dual_unit=product_rs.dual_unit, 
                                     dual_unit_type=product_rs.dual_unit_type, 
                                     factor=self.factor, 
                                     divisor=self.divisor, 
                                     with_raise=True)
            if qtys:
                uom_qty = qtys.get('uom_qty', 0)
                uop_qty = qtys.get('uoi_qty', 0)
            
        self.uom_qty = uom_qty
        self.uop_qty = uop_qty
        
    
    sequence = fields.Integer(string='Sequence', default=0, required=False, readonly=True)
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='cascade', readonly=True)
    sec_uom_qty = fields.Float(string='Quantity in UoS', default=0.0, digits=dp.get_precision('Product quantity'), 
                               required=True)
    uom_qty = fields.Float(string='Quantity in UoM', default=0.0, digits=dp.get_precision('Product quantity'), 
                           required=False, compute='_compute_product_qty')
    uop_qty = fields.Float(string='Quantity in UoP', default=0.0, digits=dp.get_precision('Product quantity'), 
                           required=False, compute='_compute_product_qty', store=False)
    uom_id = fields.Many2one('product.uom', string='Measure unit', required=False, ondelete='cascade', 
                             compute='_compute_product_unity', store=False)
    sec_uom_id = fields.Many2one('product.uom', string='Sale unit', required=False, ondelete='cascade', 
                                 compute='_compute_product_unity', store=False)
    uop_id = fields.Many2one('product.uom', string='Price unit', required=False, ondelete='cascade', 
                             compute='_compute_product_unity', store=False)
    unity_price = fields.Float(string='Unity price', default=0.0, required=False)
    total_price = fields.Float(string='Total price', default=0.0, required=False, readonly=True, compute='_compute_total_price')
    kit_id = fields.Many2one('kit.sale', string='Kit', required=False, ondelete='cascade')
    factor = fields.Float(string='Factor', default=1, required=False, compute='_compute_product_unity', store=False)
    divisor = fields.Float(string='Divisor', default=1, required=False, compute='_compute_product_unity', store=False)
    
    @api.onchange('sec_uom_qty')
    def _onchange_sec_uom_qty(self):
        """
            Au changement de la quantité, on recalcule le prix
        """
        price = 0
        kit_rs = self.kit_id
        if kit_rs:
            customer_rs = kit_rs.sale_id and kit_rs.sale_id.partner_id or False
            price = self.product_id.get_price_sale(customer_rs, False, currency_price_return=kit_rs.currency_id, 
                                                qty_uos=self.sec_uom_qty, uos=self.sec_uom_id, 
                                                date=fields.Date.today(), type='price', with_uoi=self.uop_id)
            
        self.unity_price = price
    
    
    def create_kit_sale_line(self, bom_rs=False, kit_rs=False, type='desc_heading', product_id=False, currency_id=False, kit_uom_qty=0, customer_rs=False):
        """
            Fonction permettant de créer les lignes du wizard de création de kit
            :type self: kit.sale.line
            :param bom_rs: La nomenclature à partir de laquelle il faut importer les lignes
            :type bom_rs: recordset: mrp.bom
            :param kit_rs: Le kit pour lequel on souhaite créer ces lignes
            :type kit_rs: recordset: kit.sale
            :param type: Type du kit 
            :type type: char
            :param product_id: Le produit du kit
            :type product_id: recordset: product.product
            :param currency_id: La devise de la vente
            :type currency_id: recordset: res.currency
            :param kit_uom_qty: La quantité du kit en uom
            :type kit_uom_qty: float
            :param customer_rs: Le client de la vente
            :type customer_rs: recordset: res.partner
            :return: True
            :rtype: char format date
        """
        if bom_rs and kit_rs and product_id and currency_id:
            bom_qty = bom_rs.quantity
            if bom_qty > 0 and kit_uom_qty > 0:
                #En cas de vente de kit de type entête service, on va rajouter une ligne correspondant à la ligne de tête
                if type == 'serv_heading':
                    vals = {'sequence': 0,
                            'product_id': product_id.id,
                            'kit_id': kit_rs.id,
                            'sec_uom_qty': kit_rs.sec_uom_qty}
                    
                    vals['unity_price'] = product_id.get_price_sale(customer_rs, False, currency_price_return=currency_id, 
                                                                    qty_uos=vals['sec_uom_qty'], uos=kit_rs.sec_uom_id, 
                                                                    date=fields.Date.today(), type='price', with_uoi=kit_rs.uop_id)
                    self.create(vals)
                    
                for line in bom_rs.bom_ids:
                    product_rs = line.product_id
                    if not product_rs.sale_ok:
                        raise ValidationError(_("The product %s of your bom can't be sold. All the products of your bom must "
                                                "have the 'Can be sold' field checked to make a sale kit")%(product_rs.name))
                    
                    vals = {'sequence': line.sequence,
                            'product_id': product_rs.id,
                            'kit_id': kit_rs.id}
                    # On récupère les unités du produit
                    uom_id, sec_uom_id, uop_id, factor, divisor = self.compute_product_unity(product_rs, kit_rs)
                    # On calcule la quantité du produit inscrite dans la nomenclature (en UoM) que l'on
                    # convertit en UoS
                    if uom_id and sec_uom_id and uop_id and factor and divisor:
                        #On récupère la quantité nécessaire en uom pour chaque composant de la bom
                        uom_qty, efficient_unit_qty = bom_rs.compute_qty_component(line.quantity, line.round, line.efficiency, bom_qty, 
                                                                                   kit_uom_qty, line.type_component, 
                                                                                   formula=line.formula_component, args_parameters_list=[])
                        
                        qtys = product_rs.get_qtys(uom_qty, 
                                         uom_id=uom_id, 
                                         sec_uom_id=sec_uom_id, 
                                         uoi_id=uop_id, 
                                         by_field='uom', 
                                         dual_unit=product_rs.dual_unit, 
                                         dual_unit_type=product_rs.dual_unit_type, 
                                         factor=factor, 
                                         divisor=divisor, 
                                         with_raise=True)
                        if qtys:
                            vals['sec_uom_qty'] = qtys.get('sec_uom_qty', False)
                        
                        if type != 'serv_heading':
                            vals['unity_price'] = product_rs.get_price_sale(customer_rs, False, currency_price_return=currency_id, 
                                                                            qty_uos=vals.get('sec_uom_qty', 0), uos=sec_uom_id, 
                                                                            date=fields.Date.today(), type='price', with_uoi=uop_id)
                        else:
                            vals['unity_price'] = 0
                        
                        self.create(vals)
                
        return True
    
    
    
class kit_sale(models.TransientModel):
    """ 
        Wizard to create a kit sale
    """
    _name = 'kit.sale'
    _description = 'Wizard to create a kit sale'
    _rec_name = 'product_id'
    
    @api.model
    def _type_get(self):
        return [
                ('desc_heading', _('Descriptive heading')),
                ('serv_heading', _('Service heading')),
                ('without_heading', _('Without heading')),
                       ]
    
    
    @api.one
    @api.depends('product_id')
    def _compute_product_unity(self):
        """
            Fonction permettant de récupérer les informations des unités du produit 
        """
        product_rs = self.product_id
        sale_rs = self.sale_id
        uom_id = False
        sec_uom_id = False
        uop_id = False
        factor = 1
        divisor = 1
        if product_rs:
            customer = False
            if not product_rs.free_sale:
                customer = product_rs.get_cinfo(partner_id=sale_rs.partner_id.id, property_ids=False)
                
            uoms = product_rs.get_uoms(pinfo=customer, partner=sale_rs.partner_id, type='out', property_ids=False, with_factor=True)
            if uoms:
                uom_id = uoms.get('uom_id', False)
                sec_uom_id = uoms.get('sec_uom_id', False)
                uop_id = uoms.get('uoi_id', False)
                factor = uoms.get('factor', 1)
                divisor = uoms.get('divisor', 1)
            
        self.uom_id = uom_id
        self.sec_uom_id = sec_uom_id
        self.uop_id = uop_id
        self.factor = factor
        self.divisor = divisor
        
        
    @api.one
    @api.depends('product_id', 'sec_uom_qty')
    def _compute_product_qty(self):
        """
            Fonction permettant de calculer les quantités correspondantes en unité de gestion et de prix
        """
        product_rs = self.product_id
        uom_qty = 0
        uop_qty = 0
        if product_rs and self.uom_id and self.sec_uom_id and self.uop_id:
            qtys = product_rs.get_qtys(self.sec_uom_qty, 
                                     uom_id=self.uom_id, 
                                     sec_uom_id=self.sec_uom_id, 
                                     uoi_id=self.uop_id, 
                                     by_field='sec_uom', 
                                     dual_unit=product_rs.dual_unit, 
                                     dual_unit_type=product_rs.dual_unit_type, 
                                     factor=self.factor, 
                                     divisor=self.divisor, 
                                     with_raise=True)
            if qtys:
                uom_qty = qtys.get('uom_qty', 0)
                uop_qty = qtys.get('uoi_qty', 0)
            
        self.uom_qty = uom_qty
        self.uop_qty = uop_qty
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade', 
                                 domain=[('type', '=', 'service'), ('sale_ok', '=', True),('manage_service_delivery', '=', True)])
    sale_id = fields.Many2one('sale.order', string='Sale', required=False, ondelete='cascade')
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True, ondelete='cascade')
    bom_id = fields.Many2one('mrp.bom', string='Bom', required=True, ondelete='cascade')
    sec_uom_qty = fields.Float(string='Quantity in sale unity', default=0.0, digits=dp.get_precision('Product quantity'), 
                               required=True)
    uom_qty = fields.Float(string='Quantity in measure unit', default=0.0, digits=dp.get_precision('Product quantity'), 
                           required=False, compute='_compute_product_qty')
    uop_qty = fields.Float(string='Quantity in price unity', default=0.0, digits=dp.get_precision('Product quantity'), 
                           required=False, compute='_compute_product_qty', store=False)
    type = fields.Selection('_type_get', string='Type', default='desc_heading', required=True)
    uom_id = fields.Many2one('product.uom', string='Measure unit', required=False, ondelete='cascade', 
                                 readonly=True, compute='_compute_product_unity', store=False)
    sec_uom_id = fields.Many2one('product.uom', string='Sale unit', required=False, ondelete='cascade', 
                                 readonly=True, compute='_compute_product_unity', store=False)
    uop_id = fields.Many2one('product.uom', string='Price unit', required=False, ondelete='cascade', 
                                 readonly=True, compute='_compute_product_unity', store=False)
    factor = fields.Float(string='Factor', default=1, required=False, compute='_compute_product_unity', store=False)
    divisor = fields.Float(string='Divisor', default=1, required=False, compute='_compute_product_unity', store=False)
    section_id = fields.Many2one('sale.order.line.section', string='Section', required=False, ondelete='cascade')
    line_ids = fields.One2many('kit.sale.line', 'kit_id',  string='Lines')
    requested_date = fields.Date(string='Requested date', required=True)
    
    @api.model
    def default_get(self, fields_list):
        """
            Récupération des informations de la ligne
        """
        res = super(kit_sale, self).default_get(fields_list=fields_list)
        context = self.env.context
        if context.get('active_model', '') == 'sale.order' and context.get('active_id', False):
            sale_rs = self.env['sale.order'].browse(context['active_id'])
            res['sale_id'] = sale_rs.id
            res['currency_id'] = sale_rs.currency_id.id
            res['requested_date'] = sale_rs.requested_date
                    
        return res
    
    
    @api.onchange('type')
    def _onchange_type(self):
        """
            Au changement du type, on vide la section s'il n'y a pas besoin d'en avoir
        """
        if self.type != 'desc_heading':
            self.section_id = False
            
        
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
            Au changement du produit, on cherche la première nomenclature active du produit et
            on ramène l'unité de vente
        """
        product_rs = self.product_id
        sale_rs = self.sale_id
        sec_uom_id = False
        bom_id = False
        if product_rs and sale_rs:
            # Recherche de l'unité de vente
            if product_rs.free_sale:
                sec_uom_id = product_rs.uos_id and product_rs.uos_id.id or False
            else:
                customer_rs = sale_rs.partner_id
                search_args_gen = [('product_id', '=', product_rs.id),
                                   ('state', '=', 'active'),
                                   ('partner_id', '=', customer_rs.id)]
                search_args = search_args_gen + [('property_ids', '=', False)]
                cusinfo_obj = self.env['product.customerinfo']
                # On recherche le référencement client du produit sans propriété
                customer_info_rs = cusinfo_obj.search(search_args, order='sequence asc', limit=1)
                # Si on en a pas trouvé, on recherche un référencement client avec propriété
                customer_info_rs = cusinfo_obj.search(search_args_gen, order='sequence asc', limit=1)
                if customer_info_rs:
                    sec_uom_id = customer_info_rs.uos_id and customer_info_rs.uos_id.id or False
                
            # Recherche d'une nomenclature active
            bom_rs = self.env['mrp.bom'].search([('product_id', '=', product_rs.id), ('type', '=', 'kit'), ('state', '=', 'active')], limit=1)
            if bom_rs:
                bom_id = bom_rs.id
            
        self.sec_uom_id = sec_uom_id
        self.bom_id = bom_id
    
    
    @api.multi
    def create_kit_sale(self):
        """
            Fonction permettant la création des lignes de vente à partir des lignes du kit 
        """
        product = self.product_id
        sale = self.sale_id
        if product and sale:
            if not product.manage_service_delivery or product.type != 'service' or not product.sale_ok:
                raise ValidationError(_('To create a kit, your product must be a sold service which manage delivery!'))
            
            if not self.line_ids:
                raise ValidationError(_('You must create lines with the import button to create a kit sale'))
            
            sale_line_obj = self.env['sale.order.line']
            section = self.section_id
            requested_date = self.requested_date
            for line in self.line_ids:
                line_product = line.product_id
                values = {'sec_uom_qty': line.sec_uom_qty, 'requested_date': requested_date, 'section_id': section.id}
                sale_line_obj.create_sale_order_line(sale, line_product, values, forced_qty=True, forced_price_unit=line.unity_price)
        
        #Calcul des taxes
        sale._onchange_order_line_ids()
        return {'type':'ir.actions.act_window_view_reload'}
    
    
    @api.multi
    def import_kit_sale_line(self):
        """
            Fonction permettant la création des lignes de kit à afficher dans le wizard
        """
        res = True
        if self.bom_id:
            self.line_ids = [(5, 0)]
            self.env['kit.sale.line'].create_kit_sale_line(bom_rs=self.bom_id, kit_rs=self, type=self.type, product_id=self.product_id, 
                                                           currency_id=self.currency_id, kit_uom_qty=self.uom_qty, customer_rs=self.sale_id.partner_id)
            
        
        data_pool = self.env['ir.model.data']
        action_model, action_id = data_pool.get_object_reference('kit_sale', 'action_generate_kit_sale')
        if action_model:
            action_pool = self.env[action_model]
            action = action_pool.browse(action_id).read()[0]
            action['res_id'] = self.id
            res = action
        
        return res
