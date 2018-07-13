# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
import openerp.addons.decimal_precision as dp
from openerp.addons.base_openprod.common import get_form_view
from datetime import datetime
from dateutil.relativedelta import relativedelta

class tender_answer(models.Model):
    """ 
        Answers for calls for tender
    """
    _name = 'tender.answer'
    _description = 'Answers for calls for tender'
    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('updated', _('Updated')),
                       ]
    
    
    @api.one
    @api.depends('anomaly')
    def _compute_anomaly(self):
        """
            Si l'une des valeurs du référencement fournisseur auquel la ligne fait référence est différente
            de la valeur dans la ligne, 
        """
        anomaly = False
        search_args = [('product_id', '=', self.product_id.id),
                       ('partner_id', '=', self.supplier_id.id), 
                       ('state', '=', 'active')]
        if self.property_ids:
            search_args.append(('property_ids', 'in', self.property_ids.ids))
        else:
            search_args.append(('property_ids', '=', False))
            
        supplier_info_rs = self.env['product.supplierinfo'].search(search_args, limit=1)
        if supplier_info_rs:
            supplier_key = '%s/%s/%s/%s/%s/%s/%s/%s'%(supplier_info_rs.currency_id.id, 
                                                      supplier_info_rs.uop_id.id,
                                                      supplier_info_rs.uoi_id.id,
                                                      supplier_info_rs.multiple_qty,
                                                      supplier_info_rs.min_qty,
                                                      supplier_info_rs.delivery_delay,
                                                      supplier_info_rs.factor,
                                                      supplier_info_rs.divisor)
            key_verif = '%s/%s/%s/%s/%s/%s/%s/%s'%(self.currency_id.id, 
                                                   self.uop_id.id,
                                                   self.uoi_id.id,
                                                   self.multiple_qty,
                                                   self.min_qty,
                                                   self.delivery_delay,
                                                   self.factor,
                                                   self.divisor)
            if supplier_key != key_verif:
                anomaly = True
            
        self.anomaly = anomaly
    
    
    def _search_anomaly(self, operator, value):
        """
            Fonction search de la détection d'anomalie
        """ 
        query = """
            SELECT 
                id 
            FROM 
                tender_answer answer 
            WHERE 
                CONCAT(answer.currency_id, answer.uop_id, answer.uoi_id, answer.multiple_qty, answer.min_qty, answer.delivery_delay, answer.factor, answer.divisor) != (
                    SELECT 
                        CONCAT(suppinfo.currency_id, suppinfo.uop_id, suppinfo.uoi_id, suppinfo.multiple_qty, suppinfo.min_qty, suppinfo.delivery_delay, suppinfo.factor, suppinfo.divisor) 
                    FROM 
                        product_supplierinfo suppinfo 
                    WHERE 
                        suppinfo.product_id=answer.product_id 
                    AND 
                        suppinfo.partner_id=answer.supplier_id 
                    AND 
                        suppinfo.state='active')

        """
        self.env.cr.execute(query)
        res_ids = self.env.cr.fetchall()
        return [('id', 'in', res_ids)]
    
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    date_from = fields.Date(string='Date from', required=True, default=lambda self: fields.Date.today())
    date_to = fields.Date(string='Date to')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='restrict')
    supplier_id = fields.Many2one('res.partner', string='Supplier', required=True, ondelete='restrict')
    quantity = fields.Float(string='Quantity', required=True)
    price = fields.Float(string='Price', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, ondelete='restrict')
    comment = fields.Text(string='Comment')
    tender_id = fields.Many2one('call.tender', string='Call for tender', required=False, ondelete='cascade')
    state = fields.Selection('_state_get', string='State', required=True, default='draft')
    uop_id = fields.Many2one('product.uom', string='UoP', required=True, ondelete='restrict', help='Unit of Purchase')
    uop_category_id = fields.Many2one('product.uom.category', string='UoP category', required=False, ondelete='restrict')
    uoi_id = fields.Many2one('product.uom', string='UoI', required=True, ondelete='restrict', help='Unit of Invoice')
    multiple_qty = fields.Float(string='Multiple qty', digits=dp.get_precision('Product quantity'), help="Expressed in purchase quantity",
                                default=1.0, required=True)
    min_qty = fields.Float(string='Min qty', digits=dp.get_precision('Product quantity'), help="Expressed in purchase quantity",
                           default=1.0, required=True)
    delivery_delay = fields.Integer(string='Delivery delay', default=0, required=True, help="Expressed in working day")
    factor = fields.Float(string='Factor', default=1.0, required=True)
    divisor = fields.Float(string='Divisor', default=1.0, required=True)
    dual_unit = fields.Boolean(string='Dual unit', related='product_id.dual_unit')
    dual_unit_type = fields.Selection(string='Dual unit type', selection=[('fixed', 'Fix'), ('variable', 'Variable')], related='product_id.dual_unit_type')
    property_ids = fields.Many2many('purchase.property', string='Properties', domain=[('purchase', '=', True)])
    anomaly = fields.Boolean(string='Anomaly', compute='_compute_anomaly', store=False, search='_search_anomaly',
                          help="If True, this field indicate that the value of one "
                          "of the referencing fields (multiple qty, min qty, ...) is not the same in the supplier referencing of "
                          "the supplier, the product and the properties of the line")

    
    
    @api.multi
    def update_key_referencing(self):
        """
            Permet de rechercher toutes les lignes de l'appel d'offre ayant la même clé et de
            les mettre à jour 
        """
        list_line = self
        property_ids_list = sorted(self.property_ids.ids)
        search_list_line = self.search([('tender_id', '=', self.tender_id.id),
                                      ('product_id', '=', self.product_id.id),
                                      ('supplier_id', '=', self.supplier_id.id)])
        for line in search_list_line:
            line_property_ids = sorted(line.property_ids.ids)
            if line_property_ids == property_ids_list:
                list_line |= line
            
        list_line.referencing_management()
        return True
    
    
    @api.multi
    def referencing_management(self):
        """
            Gestion de la mise à jour des référentiels
        """
        #Création des clés
        line_keys = self.create_keys()
        #Recherche des référencements + vérification contraintes
        update_vals, create_vals = self.search_supplier_referencing(line_keys)
        #Mise à jour et création référentiel 
        self.update_and_create_referencing(update_vals, create_vals)
        self.write({'state': 'updated'})
        return True
    
    
    @api.multi
    def create_keys(self):
        """
            Regroupement des lignes de réponses par clé: [product_id, supplier_id, [property_ids]]
        """
        line_keys = {}
        for line in self:
            if line.state == 'draft':
                key = (line.product_id.id, line.supplier_id.id, tuple(line.property_ids.ids))
                if not key in line_keys:
                    line_keys[key] = line
                else:
                    line_keys[key] += line
                
        return line_keys
    
    
    @api.multi
    def search_supplier_referencing(self, line_keys):
        """
            Recherche du référencement correspondant à chaque clé:
                - Référencement existant : vérifie que les valeurs de référencement (qté multiple, min...) 
                    sont identiques au référencement
                - Référencement inexistant : récupération des valeurs pour la création des référencements
                :type self: tender.answer
                :param line_keys: Clé du référencement et listes de recordset
                :type line_keys: dict {(product_id, supplier_id, (property_ids)): [line_rs]}
                :return: Dictionnaire détaillant les enregistrements à mettre à jour + liste de valeurs 
                    pour créer les référencements
                :rtype: dict, list
        """
        update_vals = {}
        verif_vals = {}
        create_vals = {}
        supplierinfo_obj = self.env['product.supplierinfo']
        for key, list_line in line_keys.items():
            supplier_info_rs = False
            args = [('product_id', '=', key[0]),
                    ('partner_id', '=', key[1]), 
                    ('state', '=', 'active')]
            if key[-1]:
                args.append(('property_ids', 'in', list(key[-1])))
            else:
                args.append(('property_ids', '=', False))
                
            #Recherche du référencement fournisseur
            supplier_info_list = supplierinfo_obj.search(args)
            for supplier in supplier_info_list:
                if sorted(key[-1]) == sorted(supplier.property_ids.ids):
                    supplier_info_rs = supplier
                    
            for line in list_line:
                #On vérifie que toutes les lignes de la clé ont les mêmes valeurs
                if not verif_vals.get(key):
                    verif_vals[key] = '%s/%s/%s/%s/%s/%s/%s/%s'%(line.currency_id.id, 
                                                                 line.uop_id.id,
                                                                 line.uoi_id.id,
                                                                 line.multiple_qty,
                                                                 line.min_qty,
                                                                 line.delivery_delay,
                                                                 line.factor,
                                                                 line.divisor)
                else:
                    key_verif = '%s/%s/%s/%s/%s/%s/%s/%s'%(line.currency_id.id, 
                                                                 line.uop_id.id,
                                                                 line.uoi_id.id,
                                                                 line.multiple_qty,
                                                                 line.min_qty,
                                                                 line.delivery_delay,
                                                                 line.factor,
                                                                 line.divisor)
                    if verif_vals[key] != key_verif:
                        raise except_orm(_('Error'), _('For a same supplier, product and properties, referencing values '
                                                       '(multiple qty, qty min....) must be the same.'))
                        
                if supplier_info_rs:
                    if not supplier_info_rs in update_vals:
                        update_vals[supplier_info_rs] = {}
                        update_vals[supplier_info_rs]['pricelist_ids'] = []
                    
                    update_vals[supplier_info_rs]['pricelist_ids'].append({'date_start': line.date_from,
                                                                           'date_stop': line.date_to,
                                                                           'min_qty': line.quantity,
                                                                           'price': line.price})
                    #Si les lignes n'ont pas les mêmes valeurs que le référencement fournisseur, on le mettra à jour
                    supplier_key = '%s/%s/%s/%s/%s/%s/%s/%s'%(supplier_info_rs.currency_id.id, 
                                                              supplier_info_rs.uop_id.id,
                                                              supplier_info_rs.uoi_id.id,
                                                              supplier_info_rs.multiple_qty,
                                                              supplier_info_rs.min_qty,
                                                              supplier_info_rs.delivery_delay,
                                                              supplier_info_rs.factor,
                                                              supplier_info_rs.divisor)
                    if supplier_key != verif_vals[key]:
                        update_vals[supplier_info_rs]['supplier_values'] = {'currency_id': line.currency_id.id,
                                                 'uop_id': line.uop_id.id,
                                                 'uoi_id': line.uoi_id.id,
                                                 'multiple_qty': line.multiple_qty,
                                                 'min_qty': line.min_qty,
                                                 'delivery_delay': line.delivery_delay,
                                                 'factor': line.factor,
                                                 'divisor': line.divisor,
                                                 'uop_category_id': line.uop_category_id.id}
                    
                else:
                    #Implémentation du dictionnaire de création
                    create_line_vals = {'date_start': line.date_from,
                                        'date_stop': line.date_to or False,
                                        'min_qty': line.quantity,
                                        'price': line.price}
                    if not create_vals.get(key):
                        create_vals[key] = {
                                       'product': line.product_id,
                                       'partner_id': line.supplier_id.id,
                                       'state': 'active',
                                       'currency_id': line.currency_id.id,
                                       'company_id': self.env.user.company_id and self.env.user.company_id.id or False,
                                       'property_ids': [(4, x) for x in line.property_ids.ids],
                                       'uop_id': line.uop_id.id,
                                       'uoi_id': line.uoi_id.id,
                                       'uop_category_id': line.uop_category_id.id,
                                       'multiple_qty': line.multiple_qty,
                                       'min_qty': line.min_qty,
                                       'delivery_delay': line.delivery_delay,
                                       'factor': line.factor,
                                       'divisor': line.divisor,
                                       'pricelist_ids': [(0, 0, create_line_vals)]
                                       }
                    else:
                        if create_vals[key].get('pricelist_ids'):
                            create_vals[key]['pricelist_ids'].append((0, 0, create_line_vals))
                
        return update_vals, create_vals
    
    @api.multi
    def update_and_create_referencing(self, update_vals, create_vals):
        """
            Permet de mettre à jour ou de créer un référencement fournisseur
            :type self: tender.answer
            :param update_vals: Dictionnaire contenant les détails des référencements à mettre à jour
            :type update_vals: dict {supplier_info_rs: [{'date_from':...,'date_to':...}]}
            :param create_vals: Dictionnaire contenant les détails des référencements à créer
            :type create_vals: dict {(product_id, supplier_id, (property_ids)): {'product': ..., 'state': ...}}
            :return: True
            :rtype: boolean
        """
        supplier_pricelist_obj = self.env['pricelist.supplierinfo']
        #Mise à jour des lignes de prix
        for supplier_ref, update_list in update_vals.items():
            supplier_ref_id = supplier_ref.id
            str_min_date = False
            #On récupère la date de début minimum des lignes à laquelle on retire 1 jour
            if update_list.get('pricelist_ids'):
                date_list = [x['date_start'] for x in update_list['pricelist_ids'] if x.get('date_start')]
                if date_list:
                    str_min_date = min(date_list)
                    
                if not str_min_date:
                    str_min_date = fields.Date.today()
                    
                min_date = fields.Date.from_string(str_min_date)
                line_stop_date = fields.Date.to_string(min_date - relativedelta(days=1))
                #On met à jour la date de fin des lignes de prix existantes
                for price_line in supplier_ref.pricelist_ids:
                    if (price_line.date_stop and price_line.date_stop >= str_min_date) or (not price_line.date_stop):
                        price_line.write({'date_stop': line_stop_date})
                        #Si date de début supérieur à date de fin, on vide la date de début
                        if (price_line.date_start and price_line.date_start >= str_min_date):
                            price_line.write({'date_start': False})
                
                #Création des nouvelles lignes de prix
                for update_line in update_list['pricelist_ids']:
                    if isinstance(update_line, dict):
                        update_line.update({'sinfo_id': supplier_ref_id})
                        supplier_pricelist_obj.create(update_line)
            
            #Mise à jour des informations fournisseur
            if update_list.get('supplier_values'):
                supplier_ref.write(update_list['supplier_values'])
        
        #Création des référencements fournisseurs
        for key in create_vals:
            if create_vals[key].get('product'):
                product = create_vals[key]['product']
                del create_vals[key]['product']
                product.write({'sinfo_ids': [(0, 0, create_vals[key])]})
            
        return True
        
        
    @api.onchange('supplier_id')
    def _onchange_supplier_id(self):
        """
            On récupère la devise du fournisseur sélectionné
        """
        res = {}
        supplier = self.supplier_id
        if supplier:
            self.currency_id = supplier.currency_id and supplier.currency_id.id or False
        else:
            self.currency_id = False
        
        return res
    
    
    @api.onchange('uop_id')
    def _onchange_uop_id(self):
        self.uop_category_id = self.uop_id and self.uop_id.category_id or False 
        self.uoi_id = self.uop_id
    
    

class supplier_call_tender(models.Model):
    """ 
        Supplier list for calls tender
    """
    _name = 'supplier.call.tender'
    _description = 'Supplier list for calls tender'
    _rec_name = 'supplier_id'
    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('sent', _('Sent')),
                ('received', _('Received')),
                       ]
        
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    supplier_id = fields.Many2one('res.partner', string='Supplier', required=True, ondelete='restrict')
    comment = fields.Char(string='Comment', size=160)
    state = fields.Selection('_state_get', string='State', default='draft', required=True)
    tender_id = fields.Many2one('call.tender', string='Call for tender', required=False, ondelete='cascade')
    
    _sql_constraints = [
        ('unique_supplier_id', 'UNIQUE(supplier_id,tender_id)', "You can't have two suppliers lines with the same supplier!"),
    ]
    
    
    @api.multi
    def action_send_mail(self):
        return self.env['mail.message'].action_send_mail(self.supplier_id, 'supplier.call.tender', '',self.id)
    
    
    @api.multi
    def action_print_call(self):
        """
            Action d'impression de la cotation 
        """
        jasper_obj = self.env['jasper.document']
        for supplier_call in self:
            data = {'ids': supplier_call.ids,
                    'model': 'supplier.call.tender'}
            report_rcs = jasper_obj.search([('report_unit' ,'=', 'purchase_call_tender')], limit=1)
            report = report_rcs and report_rcs[0] or False
            if report and report.report_id:
                return {
                    'type': 'ir.actions.report.xml',
                    'report_name': report.report_id.report_name,
                    'datas': data,
                }
            else: 
                raise except_orm(_('Error'), _("There is no report declared for call for tender. You need a report with the report unit 'purchase_call_tender'"))
            
            return True



class product_call_tender(models.Model):
    """ 
        Product list for calls tender
    """
    _name = 'product.call.tender'
    _description = 'Product list for calls tender'
    _rec_name = 'product_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    sequence = fields.Integer(string='Sequence', default=10, required=False)
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='restrict')
    comment = fields.Char(string='Comment', size=160)
    tender_id = fields.Many2one('call.tender', string='Call for tender', required=False, ondelete='cascade')
    
    
    _sql_constraints = [
        ('unique_product_id', 'UNIQUE(product_id,tender_id)', "You can't have two products lines with the same product!"),
    ]
    


class call_tender(models.Model):
    """ 
        Calls for tender
    """
    _name = 'call.tender'
    _description = 'Calls for tender'
    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('progress', _('Progress')),
                ('done', _('Done')),
                       ]
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    #En-tête
    name = fields.Char(string='Name', size=32, required=True, default='/', readonly=True, copy=False)
    request_date = fields.Date(string='Request date', default=lambda self: fields.Date.today())
    answer_date = fields.Date(string='Answer date')
    state = fields.Selection('_state_get', string='State', default='draft')
    company_id = fields.Many2one('res.company', string='Company', required=False, ondelete='restrict', readonly=True, 
                                 default=lambda self:self.env.user.company_id)
    manager_id = fields.Many2one('res.users', string='Manager', required=False, ondelete='restrict')
    #Produits
    product_ids = fields.One2many('product.call.tender', 'tender_id',  string='Products')
    #Fournisseurs
    supplier_ids = fields.One2many('supplier.call.tender', 'tender_id',  string='Suppliers')
    #Réponses
    uop_id = fields.Many2one('product.uom', string='UoP', required=False, ondelete='set null', help='Unit of Purchase')
    uop_category_id = fields.Many2one('product.uom.category', string='UoP category', required=False, ondelete='set null')
    uoi_id = fields.Many2one('product.uom', string='UoI', required=False, ondelete='set null', help='Unit of Invoice')
    currency_id = fields.Many2one('res.currency', string='Currency', required=False, ondelete='set null')
    multiple_qty = fields.Float(string='Multiple qty', digits=dp.get_precision('Product quantity'), help="Expressed in purchase quantity",
                                default=1.0)
    min_qty = fields.Float(string='Min qty', digits=dp.get_precision('Product quantity'), help="Expressed in purchase quantity",
                           default=1.0)
    delivery_delay = fields.Integer(string='Delivery delay', default=0, required=False, help="Expressed in working day")
    factor = fields.Float(string='Factor', default=1.0, required=False)
    divisor = fields.Float(string='Divisor', default=1.0, required=False)
    answer_ids = fields.One2many('tender.answer', 'tender_id',  string='Answers')
    #Notes
    internal_note = fields.Text(string='Internal note')
    printed_note = fields.Html(string='Printed note')
    
    
    @api.multi
    def update_all_referencing(self):
        """
            Permet de mettre à jour tous les référentiels
        """
        self.answer_ids.referencing_management()
        return True
    
    
    @api.onchange('uop_id')
    def onchange_uop_id(self):
        self.uop_category_id = self.uop_id and self.uop_id.category_id or False 
        self.uoi_id = self.uop_id
    
    
    @api.multi
    def show_call_tender_answer(self):
        """
            Fonction qui cherche et retourne les pickings de l'achat
        """
        action_struc = {}
        action_dict = get_form_view(self, 'call_tender.act_tender_answer')
        tender_id = self.id
        if action_dict and action_dict.get('id') and action_dict.get('type'):
            action = self.env[action_dict['type']].browse(action_dict['id'])
            action_struc = action.read()
            action_struc[0]['domain'] = [('tender_id', '=', tender_id)]
            action_struc = action_struc[0]
              
        return action_struc
        
    
    @api.model
    def create(self, vals):
        """
            On écrit le nom de l'appel d'offre à partir de sa séquence en base
        """
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].get('call.tender') or '/'
        
        return super(call_tender, self).create(vals)
    
    

class res_partner(models.Model):
    _inherit = 'res.partner'
 
    def compute_tender_call_domain_args(self, args):
        """
            Domaine des partenaires afin de n'afficher que ceux qui ont été sélectionnés dans l'appel d'offre
        """
        args2 = []
        for arg in args:
            if isinstance(arg, str) or (isinstance(arg, list) and arg[0] in ('!', '|', '&')):
                args2.append(arg)
                continue
             
            if arg[0] in ['tender_call_supplier', 'supplier_call_tender']:
                arg[0] = 'id'
                ids = []
                if arg[-1] and isinstance(arg[-1], list):
                    tender_supplier_obj = self.env['supplier.call.tender']
                    for tender_supplier in arg[-1]:
                        if tender_supplier[0] == 0:
                            if isinstance(tender_supplier[-1], dict) and tender_supplier[-1].get('supplier_id'):
                                ids.append(tender_supplier[-1]['supplier_id'])
                                
                        elif tender_supplier[0] == 4:
                            tender_supplier_rs = isinstance(tender_supplier[1], int) and tender_supplier_obj.browse(tender_supplier[1]) or False
                            if tender_supplier_rs:
                                ids.append(tender_supplier_rs.supplier_id.id)
                 
                arg[-1] = ids
            args2.append(arg)
             
        return args2
 
     
    @api.model
    def search(self, args=None, offset=0, limit=None, order=None, count=None):
        """
            Fonction search des partenaires
        """
        args = args or []
        args_modified = self.compute_tender_call_domain_args(args)
        return super(res_partner,self).search(args=args_modified, offset=offset, limit=limit, order=order, count=count)
    


class product_product(models.Model):
    _inherit = 'product.product'

    
    def additional_function_domain(self, arg):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de product_product
        """
        arg0, arg1, arg_1 = super(product_product, self).additional_function_domain(arg)
        if arg[0] in ['product_call_product', 'product_call_tender']:
            arg0 = 'id'
            ids = []
            if arg[-1] and isinstance(arg[-1], list):
                tender_product_obj = self.env['product.call.tender']
                for tender_product in arg[-1]:
                    if tender_product[0] == 0:
                        if isinstance(tender_product[-1], dict) and tender_product[-1].get('product_id'):
                            ids.append(tender_product[-1]['product_id'])
                            
                    elif tender_product[0] == 4:
                        tender_product_rs = isinstance(tender_product[1], int) and tender_product_obj.browse(tender_product[1]) or False
                        if tender_product_rs:
                            ids.append(tender_product_rs.product_id.id)
                            
            arg_1 = ids
            arg1 = arg[1]
                
        return arg0, arg1, arg_1
    


class mail_compose_message(models.Model):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self):
        """
            On passe l'état de la ligne à "Envoyé"
        """
        if self.model == 'supplier.call.tender' and self.id_active:
            call = self.env['supplier.call.tender'].browse(self.id_active)
            call.write({'state': 'sent'})

        return super(mail_compose_message, self).send_mail()