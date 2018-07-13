# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.tools.float_utils import float_compare, float_round
import re
import openerp.addons.decimal_precision as dp
from openerp.exceptions import Warning, except_orm, ValidationError
from _common import rounding
from openerp.addons.base_openprod import utils
    
    
    
class product_uom_category(models.Model):
    """ UoM Category """
    _name = 'product.uom.category'
    _description = 'UoM'
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Name', required=True, size=128, translate=True)
    
    _sql_constraints = [
        ('unique_name', 'UNIQUE(name)', 'The category uom name must be unique!'),
    ]
    
    @api.multi
    def copy(self, default=None):
        """
            Ajout de "copy" à la fin du nom
        """
        if not default:
            default = {}
            
        if 'name' not in default:
            default['name'] = '%s copy'%self.name
            
        return super(product_uom_category, self).copy(default=default)



class product_sizing(models.Model):
    """ Product sizing """
    _name = 'product.sizing'
    _description = 'Product sizing'
    _rec_name = 'product_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='restrict')
    height = fields.Float(string='Height (in cm)', default=0.0, required=False)
    width = fields.Float(string='Width (in cm)', default=0.0, required=False)
    depth = fields.Float(string='Depth (in cm)', default=0.0, required=False)
    
    

class product_packaging(models.Model):
    """Product packaging"""
    _name = 'product.packaging'
    _description = 'Product packaging'
    
    @api.one
    @api.depends('parcel_qty', 'layer_nb', 'parcel_per_layer_nb')
    def _compute_total_qty(self):
        self.total_qty = self.parcel_qty * self.layer_nb * self.parcel_per_layer_nb

    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    total_qty = fields.Float(string='Quantity', digits=dp.get_precision('Product quantity'), compute='_compute_total_qty')
    price = fields.Float(string='Price', default=0.0, digits=dp.get_precision('Account'), required=False)
    note = fields.Text(string='Note')
    parcel_qty = fields.Float(string='Qty per parcel', default=0.0, required=False)
    parcel_sizing_id = fields.Many2one('product.sizing', string='Sizing', required=True, ondelete='restrict')
    layer_nb = fields.Float(string='Layer number', default=0.0, required=False)
    pallet_sizing_id = fields.Many2one('product.sizing', string='Sizing', required=True, ondelete='restrict')
    parcel_per_layer_nb = fields.Float(string='Parcel per layer nb', default=0.0, required=False)
    
    
class product_uom(models.Model):
    """ UoM """
    _name = 'product.uom'
    _description = 'UoM'

    def factor_inv_compute(self, factor):
        return factor and (1.0 / factor) or 0.0

    @api.model
    def _type_get(self):
        return [
            ('bigger', _('Bigger than the reference Unit of Measure')),
            ('reference', _('Reference Unit of Measure for this category')),
            ('smaller', _('Smaller than the reference Unit of Measure')),
               ]
    
    @api.one
    @api.depends('factor')
    def _compute_factor_inv(self):
        self.factor_inv = self.factor_inv_compute(self.factor)
        
    @api.one
    @api.depends('factor')
    def _write_factor_inv(self):
        self.write({'factor': self.factor_inv_compute(self.factor_inv)})
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Name', required=True, size=128, translate=True)
    category_id = fields.Many2one('product.uom.category', string='Category', required=True, ondelete='restrict')
    factor = fields.Float(string='Ratio', default=1.0, required=False, digits=(12, 12),
                          help='How much bigger or smaller this unit is compared to the reference Unit of Measure for this category:\n 1 * (reference unit) = ratio * (this unit)')
    factor_inv = fields.Float(string='Bigger Ratio', digits=(12, 12), compute='_compute_factor_inv', inverse='_write_factor_inv')
    type = fields.Selection('_type_get', string='Type', default='reference', required=True)
    rounding = fields.Float(string='Rounding Precision', digits=(12, 6), required=True, default=0.01,
                            help='The computed quantity will be a multiple of this value. Use 1.0 for a Unit of Measure that cannot be further split, such as a piece.')
    active = fields.Boolean(string='Active', default=True)
    price_unit = fields.Boolean(string='Price unity', default=True)
    management_unit = fields.Boolean(string='Management unit', default=True)
        
    _sql_constraints = [
        ('factor_gt_zero', 'CHECK (factor!=0)', 'The conversion ratio for a unit of measure cannot be 0!'),
        ('unique_name', 'UNIQUE(name)', 'The partner title name must be unique!'),
    ]
    
    def _compute_qty(self, from_uom_id, qty, to_uom_id=False, with_raise=False, with_round=False):
        """
            Calcul la quantité en fonction de deux uom avec ou sans arrondie
            :type: self: product.uom
            :param: from_uom_id: UoM dans lequel est exprimé qty
            :type: from_uom_id: integer
            :param: qty: Quantité à convertir
            :type: qty: float
            :param: to_uom_id: UoM dans lequel doit être convertie la quantité
            :type: to_uom_id: integer
            :param: with_raise: Optionnel (False par défaut): Si vrai et pas la même catégorie entre les deux UoM: raise
            :type: with_raise: boolean
            :param: with_round: Optionnel (True par défaut): Si vrai, arrondi de la quantité par rapport aux arrondis des UoM
            :type: with_round: boolean
            :return: Quantité calculée
            :rtype: float
        """

        if not from_uom_id or not qty or not to_uom_id:
            return qty
        
        uoms = self.browse([from_uom_id, to_uom_id])
        if uoms[0].id == from_uom_id:
            from_unit, to_unit = uoms[0], uoms[-1]
        else:
            from_unit, to_unit = uoms[-1], uoms[0]
            
        return self._compute_qty_obj(from_unit, qty, to_unit, with_raise=with_raise, with_round=with_round)


    def _compute_qty_obj(self, from_uom, qty, to_uom, with_raise=False, with_round=False):
        """
            Calcul la quantité en fonction de deux uom avec ou sans arrondie
            :type: self: product.uom
            :param: from_uom_id: UoM dans lequel est exprimé qty
            :type: from_uom_id: recordset: product.uom
            :param: qty: Quantité à convertir
            :type: qty: float
            :param: to_uom_id: UoM dans lequel doit être convertie la quantité
            :type: to_uom_id: recordset: product.uom
            :param: with_raise: Optionnel (False par défaut): Si vrai et pas la même catégorie entre les deux UoM: raise
            :type: with_raise: boolean
            :param: with_round: Optionnel (True par défaut): Si vrai, arrondi de la quantité par rapport aux arrondis des UoM
            :type: with_round: boolean
            :return: Quantité calculée
            :rtype: float
        """
        if not from_uom or not qty or not to_uom:
            return qty
        
        if from_uom.category_id.id <> to_uom.category_id.id:
            if with_raise:
                raise Warning(_('Conversion from Product UoM %s to Default UoM %s is not possible as they both belong to different Category!.') % (from_uom.name, to_uom.name))
            else:
                return qty
        if to_uom:
            if with_round:
                amount = qty / from_uom.factor
                amount = rounding(amount * to_uom.factor, to_uom.rounding)
            else:
                amount = qty * to_uom.factor / from_uom.factor 
            
        return amount
    
    
    def check_consistance(self, qty):
        """
            Verification de la cohérence entre la quantité et la précision de l'UoM.
            Le float_compare(float_round()) permet de s'affranchir des pb de float python 
            :type: self: product.uom
            :param: qty: Quantité à tester
            :type: qty: float
            :return: qty: float
            :rtype: boolean
        """
        dp_obj = self.env['decimal.precision']
        precision = dp_obj.precision_get('Product quantity')
        return not bool(float_compare(float_round(qty, precision_rounding=self.rounding), qty, precision_digits=precision))
    
    
    @api.model
    def create(self, vals):
        if 'factor_inv' in vals:
            if vals['factor_inv'] != 1:
                vals['factor'] = self.factor_inv_compute(vals['factor_inv'])
                
            del(vals['factor_inv'])
            
        return super(product_uom, self).create(vals)
    
    
    @api.multi
    def copy(self, default=None):
        """
            Ajout de "copy" à la fin du nom
        """
        if not default:
            default = {}
            
        if 'name' not in default:
            default['name'] = '%s copy'%self.name
            
        return super(product_uom, self).copy(default=default)
    
    
    
class product_category(models.Model):
    """ Product category """
    _name = "product.category"
    _description = "Product Category"
    _parent_name = "parent_id"
    _parent_store = True
    _parent_order = 'sequence, name'
    _order = 'parent_left'
    
    def get_complete_name(self):
        """
            Complete name = "parent_name / name"
        """
        if self.parent_id:
            name = '%s / %s'%(self.parent_id.get_complete_name(), self.name)
        else:
            name = self.name
            
        return name


    @api.one
    @api.depends('name')
    def _compute_display_name(self):
        self.display_name = self.get_complete_name()

    
    @api.model
    def _type_get(self):
        return [
                    ('view', _('View')),
                    ('normal', _('Normal')),
                       ]

    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(size=64, required=True, select=True)
    display_name = fields.Char(size=64, string='Complete Path', compute='_compute_display_name')
#     complete_name = fields.Char(string='Name', size=64, compute='_compute_complete_name')
    parent_id = fields.Many2one('product.category', string='Parent category', required=False, ondelete='cascade', select=True, domain="[('type', '!=', 'normal')]")
    child_ids = fields.One2many('product.category', 'parent_id',  string='Child categories')
    sequence = fields.Integer(default=1, required=True)
    type = fields.Selection('_type_get', required=True, help="""A view type is a virtual category used to create a hierarchical structures for your categories.
                                                                   \n* You cannot select a view type in products.""")
    parent_left = fields.Integer(string='Parent left', select=True)
    parent_right = fields.Integer(string='Parent right', select=True)
    quality_control_ids = fields.One2many('quality.control.product', 'category_id',  string='Quality Control')
    
    _sql_constraints = [
        ('unique_name', 'UNIQUE(name,parent_id)', 'The product category name must be unique!'),
    ]
    
    @api.multi
    @api.constrains('parent_id')    
    def _check_recursion(self):
        """
            Verifie la non recursivité (100 niveaux maximum)
        """
        level = 100
        ids = self.ids
        while len(ids):
            self._cr.execute('select distinct parent_id from product_category where id IN %s',(tuple(ids),))
            ids = filter(None, map(lambda x:x[0], self._cr.fetchall()))
            if not level:
                raise Warning(_('Error ! You cannot create recursive categories.'))
            
            level -= 1
            
        return True
    
    @api.one
    @api.constrains('parent_id')
    def _check_parent_type(self):
        """
        Une catégorie de type normal ne peut avoir des enfants (catégorie parent que de type vue)
        """
        if self.parent_id.type == 'normal':
            raise ValidationError(_('Parent category can\'t be of type normal'))
    
    @api.one
    @api.constrains('type')
    def _check_supply_method(self):
        """
            On ne peut changer une catégorie en type vue si elle est affectée à des produits
        """
        if self.type == 'view':
            product_ids = self.env['product.product'].search([('categ_id', '=', self.id)])
            if product_ids:
                raise Warning(_("Error ! You cannot change the type in 'view' if some products are links to this category ."))
    
    @api.one
    @api.constrains('type')
    def _check_type_and_children(self):
        """
        On ne peut changer de type de catégorie que selon les condition suivantes :
            Normal => vue si aucun produit est affecté a cette catégorie
            Vue => normal => aucun enfant
        """
        if self.type == 'view':
            product_child_ids = self.env['product.product'].search([('categ_id', '=', self.id)])
            if len(product_child_ids):
                raise ValidationError(_('A view category can\'t have products attached to it'))
        elif self.type == 'normal' and len(self.child_ids):
            raise ValidationError(_('A normal category can\'t have children'))


    def child_get(self, cr, uid, ids):
        return [ids]
    
    
    def call_quality_control_modif(self, product_rcs=False, delete=False, ids=False, quality_documents_rs=None):
        """
            Fonction qui permet d'appeler la fonction de synchro des produits et des catégories dans le cas
            des plans de contrôles
        """
        syncro_field = 'control_categ_syncro'
        document_field = 'quality_control_ids'
        doc_obj = self.env['quality.control.product']
        list_fields = ['type', 'control_id', 'partner_id']
        self.function_modif_quality_documents(product_rcs, delete, syncro_field, document_field, doc_obj, list_fields, ids=ids, quality_documents_rs=quality_documents_rs)
        return True
    
    
    def function_modif_quality_documents(self, product_rcs=False, delete=False, syncro_field=None, document_field=None, doc_obj=None, list_fields=None, ids=None, quality_documents_rs=None):
        """
            Fonction qui permet de faire la synchro des controles et des plans internes entre les produits et la catégorie
        """
        # Si pas de produit passé en récupère tous les produits qui ont cette catégorie et qui ont les champs de synchro à vrai
        if syncro_field and document_field and doc_obj!=None and list_fields:
            if not product_rcs:
                search_args = [('categ_id', '=', self.id), (syncro_field, '=', True)]
                product_rcs = self.env['product.product'].search(search_args)
                
            if not quality_documents_rs:
                quality_documents_rs = self[document_field]
            
            if product_rcs and quality_documents_rs and not delete:
                product_ids = product_rcs.ids
                # On boucle sur les documents qualité
                for quality_document in quality_documents_rs:
                    # On recherche le contrôle qualité dans les produits pour faire la synchro 
                    doc_rcs = doc_obj.search([('product_id', 'in', product_ids), ('parent_id', '=', quality_document.id)])
                    # Permet de lister tous les produits qui sont synchronisés
                    product_inter_ids = []
                    if doc_rcs:
                        product_inter_ids = [x.product_id.id for x in doc_rcs]
                        write_vals = {}
                        for field in list_fields:
                            write_vals[field] = quality_document[field]
                        
                        write_vals = utils.transform_to_ids(doc_obj, write_vals)
                        doc_rcs.write(write_vals)
                    
                    # On liste tous les produits qui n'ont pas été synchro pour créer les documents
                    product_create_ids = list(set(product_ids) - set(product_inter_ids))
                    for product_create_id in product_create_ids:
                        quality_document.copy({'parent_id': quality_document.id, 'category_id': False, 'product_id': product_create_id})
            
            if product_rcs:
                # On supprime les documents qui ne sont pas liés à la catégorie
                args_delete = [('product_id', 'in', product_rcs.ids)]
                delete_quality_documents_rs = self[document_field]
                if delete and ids:
                    args_delete.append(('parent_id', 'in', ids))
                elif delete_quality_documents_rs:
                    args_delete.append(('parent_id', 'not in', delete_quality_documents_rs.ids))
                
                delete_qc_rcs = doc_obj.search(args_delete)
                if delete_qc_rcs:
                    delete_qc_rcs.unlink()
            
        return True
    
    
    def modif_type_quality_documents(self, field=None, product_rcs=None, delete=False, ids=False, quality_documents_rs=None):
        if field:
            if field == 'quality_control_ids':
                self.call_quality_control_modif(product_rcs=product_rcs, delete=delete, ids=ids, quality_documents_rs=quality_documents_rs)
                
        return True
    
    
    @api.multi
    def copy(self, default=None):
        """
            Ajout de "copy" à la fin du nom
        """
        if not default:
            default = {}
            
        if 'name' not in default:
            default['name'] = '%s copy'%self.name
            
        return super(product_category, self).copy(default=default)
    
    
    
class product_template(models.Model):
    """ Product template """
    _name = 'product.template'
    _description = 'Product template'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    product_variant_ids = fields.Boolean(string='product_variant_ids', default=False)
    categ_id = fields.Boolean(string='categ_id', default=False)
    
    
    
class product_product(models.Model):
    """ Product """
    _name = 'product.product'
    _description = 'Product'
    _inherit= 'workflow.base'
    _order = 'code'
    _sql_constraints = [
        ('uniq_code', 'unique(code)', 'The code must be unique.'),
        ('track_constraint', 'CHECK(track_label=false OR (track_label=true AND track_in_lot=false AND track_out_lot=false))', 'Impossible to set traceability by label and by lot on a same product'),
    ]
    
    
    @api.multi
    @api.depends('name')
    def name_get(self):
        """
            On affiche [code] nom
        """
        result = []
        for product in self:
            if product.code and product.name:
                name = '[%s] %s'%(product.code, product.name)
            else:    
                name = product.name
                 
            result.append((product.id, name))
             
        return result
    
    
    def get_states(self):
        return [
            ('dev', _('Development')),
            ('lifeserie', _('Life serie')),
            ('endlife', _('End life')),
            ('obsolete', _('Obsolete'))
        ]
        
    
    def _type_get(self):
        return [
            ('stockable', _('Stockable')),
            ('service', _('Service')),
            ('tech_tool', _('Technical tool')),
        ]

    
    def _supply_method_get(self):
        return [
            ('buy', _('Buy')),
        ]


    def _trigger_supply_get(self):
        return [
            ('make_to_plan', _('On scheduler')),
            ('make_to_order', _('On demand')),
            ('make_to_order_with_stock', _('On demand with stock')),
            ('without_stock', _('None')),
        ]
 
 
    @api.one
    @api.depends('')
    def _compute_tool_nb_purchased(self):
        self.tool_nb_purchased = 0
        
        
    @api.model
    def _expiry_type_get(self):
        return [
                ('manual', _('Manual')),
                ('automatic', _('Automatic')),
        ]
        
        
    @api.one
    def _get_picture_binary_filesystem(self):
        attachment_obj = self.env['ir.attachment']
        attachment_rs = attachment_obj.search([('res_model','=',self._name),('res_id','=',self.id),('binary_field','=','picture')])
        if attachment_rs:
            self.picture = attachment_rs[0].datas
        else:
            self.picture = False
    
    
    @api.one
    def _set_picture_binary_filesystem(self):
        attachment_obj = self.env['ir.attachment']
        attachment_rs = attachment_obj.search([('res_model','=',self._name),('res_id','=',self.id),('binary_field','=','picture'),('is_binary_field','=',True)])
        if self.picture:
            if attachment_rs:
                attachment_rs.datas = self.picture
            else:
                attachment_obj.create({'res_model': self._name, 'res_id': self.id, 'name': 'picture datas' , 'is_binary_field': True, 'binary_field': 'picture', 'datas': self.picture, 'datas_fname':'picture datas'})
                
        else:
            attachment_rs.unlink()
        
        
    @api.model
    def _limit_type_get(self):
        return [
                ('use_by', _('Use by')),
                ('best_before', _('Best before')),
                       ]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    #En-tête
    picture = fields.Binary(string='Picture', compute='_get_picture_binary_filesystem', inverse='_set_picture_binary_filesystem')
#     tmpl_id = fields.Many2one('product.template', string='string', required=False, ondelete='restrict')
    name = fields.Char(string='Name', required=True, size=60)
    active = fields.Boolean(default=True)
    code = fields.Char(string='Code', default=lambda self: self.env['ir.sequence'].get('product.product'), required=True, size=32, help='The code must be unique')
    uom_id = fields.Many2one('product.uom', string='Unit of measure', required=True)
    uom_category_id = fields.Many2one('product.uom.category', string='UoM category', related='uom_id.category_id', readonly=True)
    sec_uom_id = fields.Many2one('product.uom', string='Second unit of measure', required=False)
    sec_uom_category_id = fields.Many2one('product.uom.category', string='Sec UoM category',  related='sec_uom_id.category_id', readonly=True)
    dual_unit = fields.Boolean(string='Dual unit', default=False, help="Check if you want manage a dual unit for this product")
    dual_unit_type = fields.Selection(string='Dual unit type', selection=[('fixed', 'Fixed'), ('variable', 'Variable')], default='fixed')
    state = fields.Selection(string='State', selection='get_states', required=True, default='dev', help="The product management can be made in function of his life "
                        "cycle. In other words, we have several options according to the status: In development, we can buy the product, produced it, but not sale it. "
                        "In life serie, we can produce, buy and sale the product. In the end of his life, we can't produce or buy the product but we can sale it. When the " 
                        "product is obsolete, we can't produce, buy or sale the product. If there is no choice here, we can't do anything.")
    categ_id = fields.Many2one('product.category', string='Category', required=True, domain=[('type', '!=', 'view')], ondelete='restrict')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id)
    is_no_unlink = fields.Boolean(string='No unlink', default=False)
    # Approvisionnement 
    type = fields.Selection('_type_get', string='Product type', required=True, default='stockable', help="This field enables to define the product type. A product with a "
                            "'Stockable product' type can be received and put in stock. A product with a 'Service' type only create a voucher to paid in reception, "
                            "can't be put in stock and can't have a classification.")
    supply_method = fields.Selection('_supply_method_get', string='Supply method', required=True, default='buy', 
                        help="Produce will generate production order or tasks, according to the product type. Buy will trigger purchase orders when requested.")
    trigger_supply = fields.Selection('_trigger_supply_get', string='Trigger supply', required=True, default='make_to_plan', help="'On scheduler': When needed, " 
                        "the system take from the stock or wait until re-supplying. 'On demand': When needed, purchase or produce the product for the procurement "
                        "request. 'On demand with stock': During the order, the system will substract the virtual quantity to the stock if needed. 'None':"
                        "Select if you don't want automatic supplying proposition from the system. CAUTION: If 'None' is selected, the system does not make "
                        "supply proposition even if it observes an insufficient need and stock. There is an out of stock risk.")
#     supply_frequency = fields.Integer(string='Supply frequency', default=1, required=True, help="Enables to define the scheduler calculation frequency in working day")
    sale_ok = fields.Boolean(string='Can be sold', default=False, help="Determine if the product is visible in the products list during the product choice in a sale order.")
    purchase_ok = fields.Boolean(string='Can be purchased', default=False, help="Determine if the product is visible in the products list during the product choice "
                                 "in a purchase order.")
    produce_ok = fields.Boolean(string='Can be produced', default=False)
    customer_material = fields.Boolean(string='Customer material', default=False, help="This fiels enables to define if the product is supplied by a customer. A customer "
                        "material is supplied at value 0 (no stock value). A customer material is necessarily a stockable product whose supply method is 'Buy'. A customer "
                        "material can't be product.")
    manage_service_receipt = fields.Boolean(string='Manage receipts', default=False, help="If checked, there will be a reception of service during the order")
    manage_service_delivery = fields.Boolean(string='Manage deliveries', default=False, help="If checked, there will be a delivery of service during the order")
    
    # Outil technique
    partner_id = fields.Many2one('res.partner', string='Partner', required=False, ondelete='restrict')
    
    # Qualité
    is_expiry_date = fields.Boolean(string='Product with expiry date', default=False)
    limit_type = fields.Selection('_limit_type_get', string='Limit type')
    expiry_type = fields.Selection('_expiry_type_get', string='Expiry and removal date type')
    expiry_year = fields.Integer(string='Year')
    expiry_month = fields.Integer(string='Month')
    expiry_day = fields.Integer(string='Day')
    removal_year = fields.Integer(string='Year')
    removal_month = fields.Integer(string='Month')
    removal_day = fields.Integer(string='Day')
    track_in_lot = fields.Boolean(string='Track IN lots', default=False)
    track_out_lot = fields.Boolean(string='Track OUT lots', default=False)
    track_label = fields.Boolean(string='Follow with labels', default=False, help="If this field is checked, no move without UC label can be completed")
    conformity_certificate = fields.Boolean(string='Conformity certificate', default=False, help="To check if there is a conformity certificate for the delivery or the receipt")
    rohs_logo = fields.Boolean(string='ROHS logo', default=False)
    regulatory_auto_logo = fields.Boolean(string='Regulatory automobile logo', default=False)
    gross_weight = fields.Float(string='Gross weight', default=0.0, required=False)
    net_weight = fields.Float(string='Net weight', default=0.0, required=False)
    guarantee = fields.Integer(string='Guarantee', default=0, required=False)
    guarantee_unity_id = fields.Many2one('product.uom', string='Guarantee unity', required=False, ondelete='restrict')
        
    #Parameters
    internal_note = fields.Text(string='Internal note')
    parameter_ids = fields.One2many('parameter.dimension', 'product_id',  string='Parameters')
    
    #Vente
    transport_note = fields.Text(string='Note printed on the delivery note')
    #Achat 
    receipt_transport_note = fields.Text(string='Note printed on the receipt note')
    
    #Qualité
    control_categ_syncro = fields.Boolean(string="Synchronize with the controls of the category", default=True)
    quality_control_ids = fields.One2many('quality.control.product', 'product_id',  string='Quality Control')
    internal_plan_ids = fields.Many2many('document.openprod', 'internal_plan_document_openprod_rel', 'product_id', 'document_id', string='Internal documents', copy=False)

    
    @api.one
    @api.constrains('purchase_ok', 'produce_ok', 'supply_method')
    def _check_supply_method(self):
        """
            Verification de la cohérence entre les cases a cocher et la méthode de fourniture
        """
        if self.supply_method == 'buy' and not self.purchase_ok:
            raise Warning(_('The product can not be purchased'))
        elif self.supply_method == 'produce' and not self.produce_ok:
            raise Warning(_('The product can not be produced'))
        
        
    @api.one
    @api.constrains('is_expiry_date', 'track_label')
    def _check_track_label(self):
        """
            Si on a un produit avec une date d'expiration, il doit être suivi avec des étiquettes
        """
        if self.is_expiry_date and not self.track_label:
            raise Warning(_('If your product has an expiry date, you must track it with labels'))
        
    @api.one
    @api.constrains('categ_id')
    def _check_categ_type(self):
        """
            categ_id.type != view
        """
        if self.categ_id.type == 'view':
            raise ValidationError(_('Products can\'t belong to a `View` category'))
    
    
#     @api.onchange('produce_ok')
#     def _onchange_produce_ok(self):
#         """
#             Lorsqu'on coche "Peut être produit", on passe la méthode de fourniture à "produce"
#         """
#         if self.produce_ok:
#             self.supply_method = 'produce'


    @api.onchange('uom_id')
    def _onchange_uom_id(self):
        """
            Au changement de l'UoM, changement de la catégorie
        """
        self.uom_category_id = self.uom_id and self.uom_id.category_id or False
        
        
    @api.onchange('type')
    def _onchange_type_product(self):
        """
            Au changement du type, si le type est service par défaut la gestion des réceptions et livraisons est à Vrai
        """
        if self.type == 'service':
            self.manage_service_receipt = True
            self.manage_service_delivery = True
        
        
    @api.onchange('sec_uom_id')
    def _onchange_sec_uom_id(self):
        """
            Au changement du 2ème UoM, changement de la 2ème catégorie
        """
        self.sec_uom_category_id = self.sec_uom_id and self.sec_uom_id.category_id.id or False
    
    
    @api.onchange('dual_unit')
    def _onchange_dual_unit(self):
        """
            Au changement de la case a cocher double unité, initialisation ou suppression du type de double unité
        """
        if self.dual_unit:
            self.dual_unit_type = 'fixed'
        else:
            self.dual_unit_type = False
            
            
    @api.onchange('supply_method')
    def _onchange_supply_method(self):
        """
            Au changement de la méthode de fourniture, changement des cases à cocher en conséquence
        """
        if self.supply_method == 'produce':
            self.produce_ok = True
        elif self.supply_method == 'buy':
            self.purchase_ok = True
            
            
    @api.onchange('dual_unit_type')
    def _onchange_dual_unit_type(self):
        """
            Si double unité passe de variable à fixe: suppression du 2ème UoM
        """
        if self.dual_unit_type == 'fixed':
            self.sec_uom_id = False
            
            
    @api.onchange('is_expiry_date')
    def _onchange_is_expiry_date(self):
        """
            Si on a un produit avec une date d'expiration, il doit être suivi avec des étiquettes
        """
        if self.is_expiry_date:
            self.track_label = True
            
            
    @api.onchange('track_label')
    def _onchange_track_label(self):
        if self.track_label:
            self.track_in_lot = False
            self.track_out_lot = False

    
    @api.onchange('track_in_lot', 'track_out_lot')
    def _onchange_track_lot(self):
        if self.track_in_lot or self.track_out_lot:
            self.track_label = False
            
    
    def factor_help_compute(self, product_uom, second_uom, factor, divisor):
        """
            Calcul un champ char pour aider à comprendre le facteur et le diviseur
            :type: self: product.product
            :param: product_uom: Premier UoM
            :type: product_uom: recordset: product.uom
            :param: second_uom: Second UoM
            :type: second_uom: recordset: product.uom
            :type: factor: float
            :type: divisor: float
            :return: Aide mise en forme
            :rtype: char
        """
        if product_uom and second_uom:
            if not divisor:
                divisor = 1
            
            if not factor:
                factor = 1
            
            res = '1.0000 %s = %.4f %s'%(product_uom.name, 1 * factor / divisor, second_uom.name)
        else:
            res = ''
            
        return res
    
    
    def inv_factor_help_compute(self, second_uom, product_uom, factor, divisor):
        """
            Calcul un champ char pour aider à comprendre le facteur et le diviseur 
            (inverse du factor help)
            :type: self: product.product
            :param: product_uom: Second UoM
            :type: product_uom: recordset: product.uom
            :param: second_uom: Premier UoM
            :type: second_uom: recordset: product.uom
            :type: factor: float
            :type: divisor: float
            :return: Aide mise en forme
            :rtype: char
        """
        if second_uom and product_uom:
            if not factor:
                factor = 1
            
            res = '1.0000 %s = %.4f %s'%(second_uom.name, 1 * divisor / factor, product_uom.name)
        else:
            res = ''
            
        return res
    
    
    def get_available_states(self):
        return ('lifeserie', 'endlife')
    
    
    def get_purchase_transport_fields(self):
        return {}
    
    
    def get_sale_transport_fields(self):
        return {}
    
    
    def get_sale_uoms(self, cinfo=False, partner_id=False, property_ids=False, with_factor=False):
        return {}

    
    def get_purchase_uoms(self, cinfo=False, partner_id=False, property_ids=False, with_factor=False):
        return {}
        
        
    def get_uoms(self, partner=False, pinfo=False, type=False, property_ids=False, with_factor=False, with_pinfo=False):
        """
            Renvoie les UoM du produit
        """
        res = {'uom_id': self.uom_id, 'sec_uom_id': self.uom_id, 'uoi_id': self.uom_id}
        if self.dual_unit and self.dual_unit_type == 'variable':
            res.update({'sec_uom_id': self.sec_uom_id, 'uoi_id': self.sec_uom_id})
            
        if type == 'in' and self.purchase_ok:
            res.update(self.get_purchase_uoms(sinfo=pinfo, partner_id=partner and partner.id or False, with_factor=with_factor, with_pinfo=with_pinfo))
        elif type == 'out' and self.sale_ok:
            res.update(self.get_sale_uoms(cinfo=pinfo, partner_id=partner and partner.id or False, property_ids=property_ids, with_factor=with_factor, with_pinfo=with_pinfo))
            
        return res
    
    
    def get_qtys(self, qty, uom_id=None, sec_uom_id=None, uoi_id=None, by_field='uom', dual_unit=None, dual_unit_type=None, factor=1, divisor=1, with_raise=False, with_round=False):
        """
            Calcul des quantités en UoM, second UoM et UoI
            :type: self: product.product
            :param: uom_id: Premier UoM
            :type: uom_id: recordset: product.uom
            :param: sec_uom_id: Second UoM
            :type: sec_uom_id: recordset: product.uom
            :param: uoi_id: UoI
            :type: uoi_id: recordset: product.uom
            :param: by_field: UoM d'origine parmis ['uom', 'sec_uom', 'uoi']
            :type: by_field: char
            :param: dual_unit: Double unité. Si non remplis prend celui du produit
            :type: dual_unit: boolean
            :param: dual_unit_type: type de double unité parmis ['fixed', 'variable']. Si non remplis prend celui du produit
            :type: dual_unit_type: char
            :type: factor: float
            :type: divisor: float
            :return: Résultats des qtés
            :rtype: dict
        """
        if not dual_unit:
            dual_unit = self.dual_unit
            
        if not dual_unit_type:
            dual_unit_type = self.dual_unit_type
    
        res = {}
        uom_obj = self.env['product.uom']
        # Simple unité
        if not dual_unit:
            # Depuis UoM
            if by_field == 'uom' and uom_id:
                if sec_uom_id:
                    res['sec_uom_qty'] = uom_obj._compute_qty_obj(uom_id, qty, sec_uom_id, with_raise=with_raise, with_round=with_round)
                if uoi_id:
                    res['uoi_qty'] = uom_obj._compute_qty_obj(uom_id, qty, uoi_id, with_raise=with_raise, with_round=with_round)
            # Depuis Second UoM
            elif by_field == 'sec_uom' and sec_uom_id:
                if uom_id:
                    res['uom_qty'] = uom_obj._compute_qty_obj(sec_uom_id, qty, uom_id, with_raise=with_raise, with_round=with_round)
                if uoi_id:
                    res['uoi_qty'] = uom_obj._compute_qty_obj(sec_uom_id, qty, uoi_id, with_raise=with_raise, with_round=with_round)
            # Depuis UoI
            elif by_field == 'uoi' and uoi_id:
                if uom_id:
                    res['uom_qty'] = uom_obj._compute_qty_obj(uoi_id, qty, uom_id, with_raise=with_raise, with_round=with_round)
                if sec_uom_id:
                    res['sec_uom_qty'] = uom_obj._compute_qty_obj(uoi_id, qty, sec_uom_id, with_raise=with_raise, with_round=with_round)
        # Double unité
        else:
            # Fixe
            if dual_unit_type == 'fixed':
                # Depuis UoM
                if by_field == 'uom':
                    res['sec_uom_qty'] = qty * factor / divisor
                    if uoi_id and sec_uom_id and res['sec_uom_qty']:
                        res['uoi_qty'] = uom_obj._compute_qty_obj(sec_uom_id, res['sec_uom_qty'], uoi_id, with_raise=with_raise, with_round=with_round)
                # Depuis Second UoM
                elif by_field == 'sec_uom':
                    res['uom_qty'] = qty * divisor / factor
                    if uoi_id:
                        res['uoi_qty'] = uom_obj._compute_qty_obj(sec_uom_id, qty, uoi_id, with_raise=with_raise, with_round=with_round)
                # Depuis UoI
                elif by_field == 'uoi' and uoi_id:
                    if sec_uom_id:
                        res['sec_uom_qty'] = uom_obj._compute_qty_obj(uoi_id, qty, sec_uom_id, with_raise=with_raise, with_round=with_round) 
                        
                    if res['sec_uom_qty']:
                        res['uom_qty'] = res['sec_uom_qty'] * divisor / factor
                    else:
                        res['uom_qty'] = 0.0
                        
            # Variable
            elif dual_unit_type == 'variable':
                # Depuis UoM: les autres qtys restent à 0
                if uoi_id and sec_uom_id:
                    # Depuis Second UoM
                    if by_field == 'sec_uom' :
                        res['uoi_qty'] = uom_obj._compute_qty_obj(sec_uom_id, qty, uoi_id, with_raise=with_raise, with_round=with_round)
                        
                    # Depuis UoI
                    elif by_field == 'uoi':
                        res['sec_uom_qty'] = uom_obj._compute_qty_obj(uoi_id, qty, sec_uom_id, with_raise=with_raise, with_round=with_round) 
                        
        return res
    
    
    def get_qtys_unit(self, qty, uom_id=None, sec_uom_id=None, uoi_id=None, by_field='uom', dual_unit=None, dual_unit_type=None, factor=1, divisor=1, with_raise=False, with_round=False):
        """
            Calcul des quantités Unitaire en UoM, second UoM et UoI
            :type: self: product.product
            :param: uom_id: Premier UoM
            :type: uom_id: recordset: product.uom
            :param: sec_uom_id: Second UoM
            :type: sec_uom_id: recordset: product.uom
            :param: uoi_id: UoI
            :type: uoi_id: recordset: product.uom
            :param: by_field: UoM d'origine parmis ['uom', 'sec_uom', 'uoi']
            :type: by_field: char
            :param: dual_unit: Double unité. Si non remplis prend celui du produit
            :type: dual_unit: boolean
            :param: dual_unit_type: type de double unité parmis ['fixed', 'variable']. Si non remplis prend celui du produit
            :type: dual_unit_type: char
            :type: factor: float
            :type: divisor: float
            :return: Résultats des qtés unit
            :rtype: dict
        """
        res = {}
        qtys = self.get_qtys(qty, 
                             uom_id=uom_id, 
                             sec_uom_id=sec_uom_id, 
                             uoi_id=uoi_id, 
                             by_field=by_field, 
                             dual_unit=dual_unit, 
                             dual_unit_type=dual_unit_type, 
                             factor=factor, 
                             divisor=divisor,
                             with_raise=with_raise,
                             with_round=with_round)
        
        
        if by_field == 'uom':
            if 'sec_uom_qty' in qtys:
                res['sec_uom_qty'] = qtys['sec_uom_qty'] != 0 and qty*qty/qtys['sec_uom_qty'] or qty
            else:
                res['sec_uom_qty'] = qty
            
            if 'uoi_qty' in qtys:
                res['uoi_qty'] = qtys['uoi_qty'] != 0 and qty*qty/qtys['uoi_qty'] or qty
            else:
                res['uoi_qty'] = qty
        elif by_field == 'sec_uom':
            if 'uom_qty' in qtys:
                res['uom_qty'] = qtys['uom_qty'] != 0 and qty*qty/qtys['uom_qty'] or qty
            else:
                res['uom_qty'] = qty
                
            if 'uoi_qty' in qtys:
                res['uoi_qty'] =  qtys['uoi_qty'] != 0 and qty*qty/qtys['uoi_qty'] or qty
            else:
                res['uoi_qty'] = qty
        elif by_field == 'uoi':
            if 'uom_qty' in qtys:
                res['uom_qty'] = qtys['uom_qty'] != 0 and qty*qty/qtys['uom_qty'] or qty
            else:
                res['uom_qty'] = qty
                
            if 'sec_uom_qty' in qtys:
                res['sec_uom_qty'] = qtys['sec_uom_qty'] != 0 and qty*qty/qtys['sec_uom_qty'] or qty
            else:
                res['sec_uom_qty'] = qty
            
        return res
        
        
    
        
    def get_uoms_and_qtys(self, qty=0.0, uom_id=None, sec_uom_id=None, uoi_id=None, by_field='uom', dual_unit=None, dual_unit_type=None, factor=1, divisor=1, with_raise=True, partner=False, pinfo=False, type=False, with_factor=False, with_pinfo=False):
        res = self.get_uoms(partner=partner, pinfo=pinfo, type=type, with_factor=with_factor, with_pinfo=with_pinfo)
        if by_field == 'uom' and uom_id:
            res['uom_id'] = uom_id
        elif by_field == 'sec_uom' and sec_uom_id:
            res['sec_uom_id'] = sec_uom_id
        elif by_field == 'uoi' and uoi_id:
            res['uoi_id'] = uoi_id
            
        res.update(self.get_qtys(qty=qty, 
                                 uom_id=res['uom_id'], 
                                 sec_uom_id=res['sec_uom_id'], 
                                 uoi_id=res['uoi_id'], 
                                 by_field=by_field, 
                                 dual_unit=dual_unit, 
                                 dual_unit_type=dual_unit_type, 
                                 factor=res.get('factor', factor), 
                                 divisor=res.get('divisor', divisor), 
                                 with_raise=with_raise))
        return res
    
    
    def _calcul_price_rate_devise(self, devise_from, price, devise_to):
        """
             Permet de modifier le prix d'une devise à une autre
            :param devise_from: recordset de la devise du prix de base
            :type devise_from: recordset
            :param price: prix
            :type price: float
            :param devise_to: recordset de la devise du prix à retourner
            :type devise_to: recordset
        """
        if devise_from and devise_to:
            price = price * devise_to.rate / devise_from.rate
        return price
    
    
    @api.multi
    def write(self, vals=None):
        """
            Interdiction de changer de catégorie
        """
        if not vals:
            vals = {}
        
        uom_obj = self.env['product.uom']
        categ_obj = self.env['product.category']
        for product in self:
            change_dual_unit = 'dual_unit' in vals and vals['dual_unit'] != product.dual_unit
            change_dual_unit_type = 'dual_unit_type' in vals and vals['dual_unit_type'] != product.dual_unit_type
            if (change_dual_unit or change_dual_unit_type) and not self.env.context.get('force_change_dual_unit'):
                raise Warning(_('Impossible to change dual unit type. Please contact an administrator'))
            
            if 'uom_id' in vals and uom_obj.browse(vals['uom_id']).category_id.id != product.uom_category_id.id:
                raise Warning(_("New UoM must belong to same UoM category '%s' as the old UoM")%(product.uom_category_id.name))

            if product.sec_uom_id and 'sec_uom_id' in vals and uom_obj.browse(vals['sec_uom_id']).category_id.id != product.sec_uom_category_id.id:
                raise Warning(_("New second UoM must belong to same UoM category '%s' as the old second UoM")%(product.sec_uom_category_id.name))
            
            #Gestion de la récupération des documents de la qualité (plans internes, controles...)
            if ('control_categ_syncro' in vals and vals['control_categ_syncro']) or \
            (not 'control_categ_syncro' in vals and product.control_categ_syncro and 'categ_id' in vals and vals['categ_id']):
                categ = ('categ_id' in vals and categ_obj.browse(vals['categ_id'])) or product.categ_id
                categ.modif_type_quality_documents(field='quality_control_ids', product_rcs=product, delete=False)
                
        res = super(product_product, self).write(vals=vals)
            
        return res
    
    
    @api.model
    def create(self, vals):
        if not vals:
            vals = {}
        
        modif_plan_control = False
        if 'categ_id' in vals and vals['categ_id']:
            if 'control_categ_syncro' in vals and vals['control_categ_syncro']:
                modif_plan_control = True
            
        res = super(product_product, self).create(vals=vals)
        if modif_plan_control:
            res.categ_id.modif_type_quality_documents(field='quality_control_ids', product_rcs=res, delete=False)
            
        return res
    
    
    @api.multi
    def unlink(self):
        for product in self:
            if product.is_no_unlink:
                raise Warning(_('You can not delete this product because the field can not be deleted is checked'))
            
        return super(product_product, self).unlink()
    
    
    @api.multi
    def copy(self, default=None):
        """
            Ajout de "copy" à la fin du nom
        """
        context = self.env.context
        if not 'copy_by_button' in context:
            raise Warning(_('Please use the button "Copy product" to duplicate a product'))
        
        if not default:
            default = {}
            
        if 'code' not in default:
            default['code'] = self.env['ir.sequence'].get('product.product') or '%s copy'%self.code
            
        if 'name' not in default:
            default['name'] = '%s copy'%self.name
            
        return super(product_product, self).copy(default=default)
    
    
    def additional_function_domain(self, arg):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de mrp_routing_line
        """
        arg0, arg1, arg_1 = False, False, False
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
    
    
    def update_args_modified(self, name, args_modified, operator='ilike'):
        """
            Fonction destinée à être surchargée par les achats et les ventes
        """
        return args_modified

    
    @api.model
    def search(self, args=None, offset=0, limit=None, order=None, count=None):
        """
            Modification du search afin de n'afficher que les produits ayant le partenaire en référencement
        """
        args = args or []
        args_modified = self.compute_domain_args_resource(args)
        res = super(product_product, self).search(args=args_modified, offset=offset, limit=limit, order=order, count=count)
        return res
    
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=1000):
        args = args or []
        if name:
            args = ['|', ('name', operator, name), ('code', operator, name)] + args
        
        args_modified = self.compute_domain_args_resource(args)
        updated_args = self.update_args_modified(name, args_modified, operator)
        recs = self.search(updated_args, limit=limit)
        return recs.name_get()
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False,lazy=True):
        domain = self.compute_domain_args_resource(domain)
        return super(product_product, self).read_group(domain=domain, fields=fields, groupby=groupby, offset=offset, limit=limit, orderby=orderby,lazy=lazy)
    
    

class quality_control(models.Model):
    """ 
        Quality Control 
    """
    _name = 'quality.control'
    _description = 'Quality Control'
    
    
    @api.one
    def _get_plan_binary_filesystem(self):
        attachment_obj = self.env['ir.attachment']
        attachment_rs = attachment_obj.search([('res_model','=',self._name),('res_id','=',self.id), ('binary_field','=','plan')])
        if attachment_rs:
            self['plan'] = attachment_rs[0].datas
    
    @api.one
    def _set_plan_binary_filesystem(self):
        attachment_obj = self.env['ir.attachment']
        attachment_rs = attachment_obj.search([('res_model','=',self._name), ('res_id','=',self.id), ('binary_field','=','plan'), ('is_binary_field','=',True)])
        if self.plan:
            if attachment_rs:
                attachment_rs.datas = self.plan
            else:
                
                attachment_obj.create({'res_model': self._name, 'res_id': self.id, 'name': 'plan datas' , 'is_binary_field': True, 'binary_field': 'plan', 
                                       'datas': self.plan, 'datas_fname':'plan datas', 'type': 'binary'})
        else:
            attachment_rs.unlink()
        
        
    @api.model
    def _frequency_type_get(self):
        return [
                ('all', _('Each declaration')),
                ('time', _('Period of time')),
                ('piece', _('Piece')),
                ('label', _('Label')),
                       ]
        
    @api.model
    def _frequency_date_type_get(self):
        return [
                ('hour', _('Hour')),
                ('day', _('Day')),
                ('week', _('Week')),
                ('month', _('Month')),
                       ]
    
    
    @api.model
    def _type_get(self):
        return [
                ('all', _('All')),
                ('reception', _('Reception')),
#                 ('delivery', _('Delivery')),
                ('intern', _('Production')),
                ('post_reception', _('Post Reception')),
                ('post_intern', _('Post production')),
                       ]
    
    @api.model
    def _frequency_mode_get(self):
        return [
                ('manual', _('Manual')),
                ('formula', _('Formula')),
                       ]


    @api.model
    def _type_numeric_get(self):
        return [
                ('manual', _('Manual')),
                ('formula', _('Formula')),
                       ]
        

    @api.model
    def _type_control_get(self):
        return [
                ('numeric', _('Numeric')),
                ('text', _('Text')),
                ('selection', _('Selection')),
                ('only_result', _('Only result')),
                       ]
    
    
    def _compute_formula_numeric(self, product_id, field='min'):
        min = 0
        max = 0
        if self.type_numeric == 'formula':
            if not product_id:
                pass
            else:
                min = self.compute_value_formula(self.formula_numeric_min, args_parameters_list=[('product_id', '=', product_id)])
                max = self.compute_value_formula(self.formula_numeric_max, args_parameters_list=[('product_id', '=', product_id)])
        else:
            min = self.min_manual
            max = self.max_manual
        
        if field == 'min':
            return min
        else:
            return max
    
    
    def compute_value_formula(self, formula, args_parameters_list=[]):
        """
            Fonction qui permet de calculer la valeur d'une formule et des paramètres
        """
        qty = 0
        if formula:
            try:
                exp = re.compile("""param\[['"][^'"]{0,}['"]\]{1}""")
                param_obj = self.env['parameter.dimension']
                param_list = exp.findall(formula)
                param = {}
                if param_list:
                    param_list = list(set(param_list))
                    for v in param_list:
                        v = v[7:-2]
                        args_parameter = [('name', '=', v)]
                        if args_parameters_list:
                            args_parameter.extend(args_parameters_list)
                            
                        param_ids = param_obj.search(args_parameter, limit=1)
                        if param_ids:
                            param[v] = param_ids[0].value
                        else:
                            raise except_orm(_('Error'), _('No parameter (%s) in product.')%(v))
                       
                qty = eval(formula)
            except:
                qty = 0.0
        return qty
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    description = fields.Text(string='Description')
    plan = fields.Binary(string='Plan/Picture', compute='_get_plan_binary_filesystem', inverse='_set_plan_binary_filesystem', help='help')
    type_numeric = fields.Selection('_type_numeric_get', string='Type')
    formula_numeric_min = fields.Text(string='Formula min', help="""If the type is formula you can put in the formula of defined parameters\nHere is the unit time\nThe default parameter values are taken from the product file (Use the formula param[ 'parameter name'])\nexample:\n    220 * 12/11\n    param['width1'] / param['length1'] + 5""")
    formula_numeric_max = fields.Text(string='Formula max', help="""If the type is formula you can put in the formula of defined parameters\nHere is the unit time\nThe default parameter values are taken from the product file (Use the formula param[ 'parameter name'])\nexample:\n    220 * 12/11\n    param['width1'] / param['length1'] + 5""")
    min_manual = fields.Float(string='Min', size=256)
    max_manual = fields.Float(string='Max', size=256)
    frequency_type = fields.Selection('_frequency_type_get', default='all', required=True)
    frequency_date_type = fields.Selection('_frequency_date_type_get', string='Period type', default='month', required=True)
    frequency_mode = fields.Selection('_frequency_mode_get', default='manual', required=True)
    frequency_manual = fields.Integer(default=1)
    formula = fields.Text(string='Formula', help="""If the type is formula you can put in the formula of defined parameters\nHere is the unit time\nThe default parameter values are taken from the product file (Use the formula param[ 'parameter name'])\nexample:\n    220 * 12/11\n    param['width1'] / param['length1'] + 5""")
    type = fields.Selection('_type_get', string='Type', default='all', required=True)
    type_control = fields.Selection('_type_control_get', string='Type control', default='numeric', required=True)
    control_value_ids = fields.Many2many('quality.control.value', 'quality_control_quality_control_value_rel', 'control_id', 'control_value_id', string='Controls values')
    text_value = fields.Char(string='Text value', size=256, required=False)
    
    
    def nb_quality_control(self, control_product, type='all', quantity=0, date='', quantity_label=0):
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
        if self.type == 'all' or type == self.type:
            if self.frequency_type == 'all' and (control_product.int_next_frequency + 1) >= control_product.frequency_value:
                res = {'nb': 1, 'frequency': -1, 'nb_start': 0, 'frequency_value': 0}
            elif self.frequency_type in ('piece', 'label'):
                if self.frequency_type == 'label':
                    quantity = quantity_label
                    
                if (control_product.int_next_frequency + quantity) >= control_product.frequency_value:
                    nb = 1
                    nb_start = control_product.frequency_value - control_product.int_next_frequency
                    remaining = quantity + control_product.int_next_frequency - control_product.frequency_value
                    divisor = remaining / (control_product.frequency_value or 1)
                    if divisor > 0:
                        nb += int(divisor)
                    
                    res = {'nb': nb, 'frequency': control_product.frequency_value, 'nb_start': nb_start, 'frequency_value': control_product.frequency_value}
                        
            elif self.frequency_type != 'all':
                if not control_product.date_next_frequency or date and date > control_product.date_next_frequency:
                    res = {'nb': 1, 'frequency': -1, 'nb_start': 0, 'frequency_value': 0}
        
        return res
    
    
    
    @api.multi
    def write(self, vals=None):
        res = super(quality_control, self).write(vals=vals)
        for qual_control in self:
            if qual_control.frequency_type == 'label' and qual_control.type not in ('post_reception', 'post_intern'):
                raise except_orm(_('Error'), _('We can not do is control the label other than on post type (%s).')%(qual_control.name))
            
        return res
    
    
    @api.model
    def create(self, vals):
        res = super(quality_control, self).create(vals=vals)
        if res.frequency_type == 'label' and res.type not in ('post_reception', 'post_intern'):
            raise except_orm(_('Error'), _('We can not do is control the label other than on post type (%s).')%(res.name))
            
        return res
    
        
    
class quality_control_value(models.Model):
    """ 
        Quality Control Value
    """
    _name = 'quality.control.value'
    _description = 'Quality Control.value'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Value', size=256, required=True)
    
    
    def compute_domain_args(self, args):
        """
            Domaine des gammes
        """
        args2 = []
        for arg in args:
            if isinstance(arg, str) or (isinstance(arg, list) and arg[0] in ('!', '|', '&')):
                args2.append(arg)
                continue
            
            if arg[0] == 'domain_result_control':
                arg[0] = 'id'
                ids = []
                if arg[-1]:
                    ids = arg[-1] and arg[-1][0] and arg[-1][0][-1] or []
                
                arg[-1] = ids
            args2.append(arg)
            
        return args2

    
    @api.model
    def search(self, args=None, offset=0, limit=None, order=None, count=None):
        """
            Fonction search de la gamme 
        """
        args = args or []
        args_modified = self.compute_domain_args(args)
        return super(quality_control_value,self).search(args=args_modified, offset=offset, limit=limit, order=order, count=count)

            
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=1000):
        """
            Fonction name_search de la gamme
        """
        args = self.compute_domain_args(args)
        recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()
    


class quality_control_product(models.Model):
    """ 
        Quality Control Product
    """
    _name = 'quality.control.product'
    _description = 'Quality Control Product'
    _rec_name = 'product_id'
    
    @api.model
    def _type_get(self):
        return [
                ('all', _('All')),
                ('reception', _('Reception')),
#                 ('delivery', _('Delivery')),
                ('intern', _('Production')),
                ('post_reception', _('Post Reception')),
                ('post_intern', _('Post production')),
                       ]
    
    
    @api.one
    def _compute_frequency_value(self):
        frequency_value = 0
        if self.control_id:
            if self.control_id.frequency_mode == 'formula':
                frequency_value = self.compute_value_formula(self.control_id.formula, args_parameters_list=[('product_id', '=', self.product_id.id)])
            else:
                frequency_value = self.control_id.frequency_manual
            
        self.frequency_value = frequency_value
    
    
    def compute_value_formula(self, formula, args_parameters_list=[]):
        """
            Fonction qui permet de calculer la valeur d'une formule et des paramètres
        """
        qty = 0
        if formula:
            try:
                exp = re.compile("""param\[['"][^'"]{0,}['"]\]{1}""")
                param_obj = self.env['parameter.dimension']
                param_list = exp.findall(formula)
                param = {}
                if param_list:
                    param_list = list(set(param_list))
                    for v in param_list:
                        v = v[7:-2]
                        args_parameter = [('name', '=', v)]
                        if args_parameters_list:
                            args_parameter.extend(args_parameters_list)
                            
                        param_ids = param_obj.search(args_parameter, limit=1)
                        if param_ids:
                            param[v] = param_ids[0].value
                        else:
                            raise except_orm(_('Error'), _('No parameter (%s) in product.')%(v))
                       
                qty = eval(formula)
            except:
                qty = 0.0
        return qty
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='cascade')
    parent_id = fields.Many2one('quality.control.product', string='Parent', required=False, ondelete='set null')
    category_id = fields.Many2one('product.category', string='Category', required=False, ondelete='cascade',
                                  domain=[('type', '!=', 'view')])
    type = fields.Selection('_type_get', string='Type', required=True)
    control_id = fields.Many2one('quality.control', string='Control', required=True, ondelete='restrict')
    partner_id = fields.Many2one('res.partner', string='Partner', required=False, ondelete='restrict')
    date_next_frequency = fields.Datetime(string='Date next frequency')
    int_next_frequency = fields.Integer(string='Integer next frequency', default=0, required=False)
    frequency_value = fields.Integer(string='Frequency Value', default=0, compute='_compute_frequency_value')
    
    
    def product_quality_control(self, type='all', partner_id=False, quantity=0, date='', quantity_label=0):
        """
            Fonction qui permet de retourner l'id du controle et le nombre de fois que le controle qualitée doit être fait pour un produit et s'il doit être fait
            :type: self: quality.control
            :param: type: Le type de control
            :type: type: selection
            :param: partner: S'il y a un partenaire
            :type: partner: id
            :param: quantity: Qté du produit
            :type: quantity: float
            :param: date: Date du controle
            :type: date: datetime
            :return: Retourne un dico avec comme clé le recordset du control et comme valeur le nb de controle à faire
            :rtype: dico
        """
        res = {}
        for control_product in self:
            if (not control_product.partner_id or (partner_id and control_product.partner_id.id == partner_id)) and control_product.control_id:
                res_nb_quality = control_product.control_id.nb_quality_control(control_product, type, quantity=quantity, date=date, quantity_label=quantity_label)
                if res_nb_quality:
                    if control_product.control_id in res:
                        if res_nb_quality['nb'] > res[control_product.control_id]['nb'] or (res_nb_quality['nb'] == res[control_product.control_id]['nb'] and res_nb_quality['frequency'] < res[control_product.control_id]['frequency']):
                            res[control_product.control_id] = res_nb_quality 
                    else:
                        if res_nb_quality['nb']:
                            res[control_product.control_id] = res_nb_quality
        
        return res
    
    
    @api.multi
    def button_view_quality_control(self):
        for control_product in self:
            if control_product.control_id:
                return {
                            'name': _('Quality control'),
                            'view_type': 'form',
                            'view_mode': 'form',
                            'res_model': 'quality.control',
                            'type': 'ir.actions.act_window',
                            'target': 'new',
                            'res_id': control_product.control_id.id,
                            'nodestroy': True,
                            }
        return True

    
    @api.multi
    def write(self, vals=None):
        res = super(quality_control_product, self).write(vals=vals)
        category_ids = []
        for quality_control in self:
            if 'control_id' in vals:
                super(quality_control_product, quality_control).write(vals={'int_next_frequency': quality_control.frequency_value - 1})
                
            if quality_control.category_id and quality_control.category_id.id not in category_ids:
                category_ids.append(quality_control.category_id.id)
                quality_control.category_id.modif_type_quality_documents(field='quality_control_ids', product_rcs=False, delete=False, quality_documents_rs=quality_control)
                
        return res
    
    
    @api.model
    def create(self, vals):
        res = super(quality_control_product, self).create(vals=vals)
        if res.category_id:
            res.category_id.modif_type_quality_documents(field='quality_control_ids', product_rcs=False, delete=False, quality_documents_rs=res)

        res.write({'int_next_frequency': res.frequency_value - 1})
        return res
    
    
    @api.multi
    def unlink(self):
        category_ids = []
        for quality_control in self:
            if quality_control.category_id and quality_control.category_id.id not in category_ids:
                category_ids.append(quality_control.category_id.id)
                quality_control.category_id.modif_type_quality_documents(field='quality_control_ids', product_rcs=False, delete=True, ids=self.ids, quality_documents_rs=quality_control)
                
        return super(quality_control_product, self).unlink()
    
    
    #===========================================================================
    # ONCHANGE
    #===========================================================================
    @api.onchange('type')
    def _onchange_type(self):
        """
            Au changement de l'UoM, changement de la catégorie
        """
        self.control_id = False
        
        
    
class parameter_dimension(models.Model):
    """ 
    Parameter Dimension 
    """
    _name = 'parameter.dimension'
    _description = 'Parameter Dimension'
    
    
    @api.one
    @api.depends('type_param_id', 'type_param_id.price_formula', 'value')
    def _compute_price_unit(self):
        price_unit = 0
        if self.type_param_id.price_formula:
            formula = self.type_param_id.price_formula
            try:
                formula = formula.replace('value', str(self.value))
                price_unit = eval(formula)
            except:
                price_unit = 0.0
        
        self.price_unit = price_unit
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(related='type_param_id.name')
    type_param_id = fields.Many2one('parameter.dimension.type', string='Name', required=True, ondelete='restrict')
    value = fields.Float(string='Value', default=0.0, required=True)
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='cascade')
    price_unit = fields.Float(string='Price unit', digits=dp.get_precision('Product price'), compute='_compute_price_unit', store=True)
    
    #===========================================================================
    # ONCHANGE
    #===========================================================================
    
    @api.onchange('type_param_id')
    def _onchange_type_param_id(self):
        """
            Au changement de l'UoM, changement de la catégorie
        """
        self.name = self.type_param_id and self.type_param_id.name or False
    
    
    
class parameter_dimension_type(models.Model):
    """ 
    Parameter Dimension Type
    """
    _name = 'parameter.dimension.type'
    _description = 'Parameter Dimension Type'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    price_formula = fields.Text(string='Price formula', help="Here is an example of the formula 14 + 6 * 3 - value. 'Value' is the only parameter that you can use and which corresponds to the value of the parameter that has this type of parameter")
    
    
    
class purchase_property_category(models.Model):
    """
    purchase property category
    """
    _name = 'purchase.property.category'
    _description = 'Purchase property category'
    name = fields.Char(required=True)
    
    _sql_constraints = [
        ('unique_name', 'UNIQUE(name)', 'The category name must be unique'),
    ]
    
    
    
class purchase_property(models.Model):
    """
    purchase property
    """
    _name = 'purchase.property'
    _description = 'Purchase property'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    category_id = fields.Many2one('purchase.property.category', string='Category', required=True, ondelete='restrict')
    sale = fields.Boolean(default=False)
    purchase = fields.Boolean(default=False)

    _sql_constraints = [
        ('unique_name_categ', 'UNIQUE(name,category_id)', 'The property name must be unique per category'),
    ]