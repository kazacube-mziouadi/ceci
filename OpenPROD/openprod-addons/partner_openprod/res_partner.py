# -*- coding: utf-8 -*-

from openerp import models, fields, api, _
from openerp.exceptions import except_orm,Warning
from openerp.addons.base_openprod import utils

import logging
_schema = logging.getLogger(__name__ + '.schema')


class res_company_title(models.Model):
    _name = 'res.company.title'
    _order = 'name'

    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string="Title", required=True, translate=True)
    shortcut = fields.Char(string="Abbreviation", required=False, translate=True)
    
    _sql_constraints = [
        ('unique_name', 'UNIQUE(name)', 'The partner title name must be unique!'),
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
            
        return super(res_company_title, self).copy(default=default)



class res_region(models.Model):
    """ 
        The region object for address
    """
    _name = 'res.region'
    _description = 'The region object for address'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string="Name", required=True)
    country_id = fields.Many2one('res.country', string='Country', required=True, ondelete='restrict')
    code = fields.Char(string='Code', size=64, required=False)



class address(models.Model):
    """ 
        Address object 
    """
    _name = 'address'
    _description = 'Address object'
    
    
    @api.multi
    @api.depends('name', 'street', 'street2', 'street3', 'zip', 'city', 'region_id', 'country_id')
    def _compute_partner_address_id(self):
        for address in self:
            if address.id:
                partner_ids = self.env['res.partner'].search([('address_id', '=', address.id), 
                                                              ('company_address', '=', False)], limit=1)
                address.partner_address_id = partner_ids and partner_ids[0] or False
            else:
                address.partner_address_id = False
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Name', required=True)
    street = fields.Char(string='Street', size=128, required=False)
    street2 = fields.Char(string='Street 2', size=128, required=False)
    street3 = fields.Char(string='Street 3', size=128, required=False)
    zip = fields.Char(string='Zip', size=24, required=False)
    city = fields.Char(string='City', size=128, required=False)
    region_id = fields.Many2one('res.region', string='Region', required=False, ondelete='restrict')
    country_id = fields.Many2one('res.country', string='Country', required=True, ondelete='restrict')
    address_note = fields.Text(string='Address note')
    partner_address_id = fields.Many2one('res.partner', string='Partner', required=False, compute='_compute_partner_address_id', 
                                         store=True)
    

    def get_fields(self, return_id=False):
        if self:
            res = {
               'address_name': self.name,
               'street': self.street,
               'street2': self.street2,
               'street3': self.street3,
               'zip': self.zip,
               'city': self.city,
               'region_id': self.region_id and self.region_id.id or False,
               'country_id': return_id and self.country_id.id or self.country_id
                   }
        else:
            res = {
               'address_name': False,
               'street': False,
               'street2': False,
               'street3': False,
               'zip': False,
               'city': False,
               'region_id': False,
               'country_id': False,
                   }
            
        return res 
    
    
    @api.multi
    def copy(self, default=None):
        """
            On empêche la duplication de l'adresse, sauf si on lui passe 'allow_address_copy'
            dans le context
        """
        context = self.env.context
        if not 'allow_address_copy' in context:
            raise Warning(_("You can't copy an address"))
        
        return super(address, self).copy(default=default)
    
    
    @api.multi
    def unlink(self):
        """ 
        On ne peut supprimer une adresse liée à un partenaire existant 
        """
        context = self.env.context
        #Si on viens de la suppression du partenaire, on ne fait pas la vérification
        if not context.get('partner_unlink'):
            partner_obj = self.env['res.partner']
            linked_partner = partner_obj.search([('address_id', '=', self.ids)], limit=1)
            if linked_partner:
                raise except_orm(_('Error'), _('You can\'t delete an address used by a partner'))
        
        return super(address, self).unlink()

    
    
class contact_function(models.Model):
    """ 
    The class for the contact\'s functions 
    """
    _name = 'contact.function'
    _description = 'The class for the contact\'s functions'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string="Name", required=True, translate=True)
    
    _sql_constraints = [
        ('unique_name', 'UNIQUE(name)', 'The function name must be unique!'),
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
            
        return super(contact_function, self).copy(default=default)



class res_partner_category(models.Model):
    _inherit = 'res.partner.category'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    is_customer = fields.Boolean(string='Customer category', default=False)
    is_supplier = fields.Boolean(string='Supplier category', default=False)
    
    _sql_constraints = [
        ('unique_name', 'UNIQUE(name)', 'The partner category name must be unique!'),
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
            
        return super(res_partner_category, self).copy(default=default)



class res_partner_title(models.Model):
    _inherit = 'res.partner.title'
    
    _sql_constraints = [
        ('unique_name', 'UNIQUE(name)', 'The partner title name must be unique!'),
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
            
        return super(res_partner_title, self).copy(default=default)



class partner_stat_family(models.Model):
    """ 
    Stat family for sales and purchases in partner
    """
    _name = 'partner.stat.family'
    _description = 'Stat family'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code", required=False, size=64)



class res_partner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'workflow.base']
    
    
    STATES = [
        ('prospect', _('Prospect')),
        ('qualified', _('Qualified')),
        ('stopped', _('Stopped')),
    ]
    
    @api.model
    def state_groups(self, present_ids, domain, **kwargs):
        """
            Fonction permettant de grouper par état. On a besoin de copier
            self.STATES avant de la retourner car odoo modifie la liste
        """
        folded = {key: False for key, val in self.STATES}
        return self.STATES[:], folded
    
     
    @api.model
    def _state_get(self):
        return self.STATES
    
        
    @api.one
    def _get_image_binary_filesystem(self):
        attachment_obj = self.env['ir.attachment']
        attachment_rs = attachment_obj.search([('res_model','=',self._name),('res_id','=',self.id),('binary_field','=','image')])
        if attachment_rs:
            self.image = attachment_rs[0].datas
        else:
            self.image = False
    
    
    @api.one
    def _set_image_binary_filesystem(self):
        attachment_obj = self.env['ir.attachment']
        attachment_rs = attachment_obj.search([('res_model','=',self._name),('res_id','=',self.id),('binary_field','=','image'),('is_binary_field','=',True)])
        if self.image:
            if attachment_rs:
                attachment_rs.datas = self.image
            else:
                attachment_obj.create({'res_model': self._name, 'res_id': self.id, 'name': 'image datas' , 'is_binary_field': True, 'binary_field': 'image', 'datas': self.image, 'datas_fname':'image datas'})
        else:
            attachment_rs.unlink()
    
    
    def _default_calendar_id(self):
        today = fields.Date.today()
        res = self.env['calendar'].search([('start_date', '<=', today), ('end_date', '>=', today)], limit=1)
        if not res:
            res = self.env['calendar'].search([], limit=1)
            
        return res
    
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    # En-tête
    name = fields.Char(string='Name', size=50, required=True)
    image = fields.Binary(string='Logo', compute='_get_image_binary_filesystem', inverse='_set_image_binary_filesystem', default=False)
    is_company = fields.Boolean(string='Is company', default=True, help="Check if the contact is a company, otherwise it's a contact")
    reference = fields.Char(string='Reference', size=128, required=False, select=True)
    civility_id = fields.Many2one('res.partner.title', string='Civility', required=False, ondelete='restrict')
    title_id = fields.Many2one('res.company.title', string='Title', required=False, ondelete='restrict')
    state = fields.Selection('_state_get', string='State', select=True, default='prospect')
    calendar_id = fields.Many2one('calendar', string='Calendar', required=False, ondelete='restrict', default=_default_calendar_id,
                                   help='The calendar specify the work days, holidays... of the partner. It\'s used in most of date calculation')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, ondelete='restrict', 
                                  default=lambda self: self.env.ref('base.EUR'), readonly=False, compute=False)
    category_ids = fields.Many2many('res.partner.category',
                'openprod_res_partner_category_rel', 'openprod_partner_id', 'openprod_category_id', string='Categories')
    parent_id = fields.Many2one('res.partner', string='Partner company', required=False, ondelete='restrict')
    #pour les contacts le partenaire associé au contact
    parent_company_id = fields.Many2one('res.partner', string='Parent company', required=False, ondelete='restrict', 
                                        domain=[('is_group', '=', True)])
    is_transporter = fields.Boolean(string='Transporter', default=False)
    is_group = fields.Boolean(string='Is a holding', default=False)
    first_name = fields.Char(string='First name', size=32, required=False)
    function_id = fields.Many2one('contact.function', string='Function', required=False, ondelete='restrict')
    company_address = fields.Boolean(string='Use company address', default=False)
    color = fields.Integer(string='Color', default=0, required=False)
    
    # Adresse
    address_id = fields.Many2one('address', string='Address', required=False, ondelete='set null', copy=False)
    corporate_name = fields.Char(string='Corporate name', size=128, required=False)
    address_name = fields.Char(string='Address name', size=128, related='address_id.name', required=False,)
    attn = fields.Char(string='Attn', size=256, required=False, translate=True, help='res_partner.attn.help')
    street = fields.Char(string='Street', size=128, related='address_id.street', required=False)
    street2 = fields.Char(string='Street 2', size=128, related='address_id.street2', required=False)
    street3 = fields.Char(string='Street 3', size=128, related='address_id.street3', required=False)
    zip = fields.Char(string='Zip', size=24, related='address_id.zip', required=False)
    city = fields.Char(string='City', size=128, related='address_id.city', required=False, copy=False)
    region_id = fields.Many2one('res.region', related='address_id.region_id', string='Region', required=False, ondelete='restrict', store=True)
    country_id = fields.Many2one('res.country', string='Country', related='address_id.country_id', required=True, ondelete='restrict')
    address_note = fields.Text(string='Address note', related='address_id.address_note', readonly=True)
    phone = fields.Char(string='Phone', size=20, required=False)
    mobile = fields.Char(string='Mobile', size=20, required=False)
    email = fields.Char(string='Email', size=128, required=False)
    fax = fields.Char(string='Fax', size=16, required=False)
    
    #Contacts et notes
    internal_note = fields.Text(string='Internal notes')
    partner_doc_ids = fields.Many2many('document.openprod', 'res_partner_document_openprod_rel', 'partner_id', 'document_id', 
                                         string='Documents', copy=False)
    
    # Transport
    transp_contact_id = fields.Many2one('res.partner', string='Transporter contact', required=False, ondelete='restrict')
    transp_code = fields.Char(string='Transport code', size=128, required=False)
    
    _group_by_full = {
        'state': state_groups,
    }
    
    def _read_group_fill_results(self, cr, uid, domain, groupby,
                                 remaining_groupbys, aggregated_fields,
                                 count_field, read_group_result,
                                 read_group_order=None, context=None):
        """
        On surcharge la méthode d'odoo car elle ne permet de grouper que
        par M2O. On remplace simplement le status par un tuple contenant 
        (valeur, nom) au lieu de n'avoir que la valeur
        """
        if groupby == 'state':
            STATES_DICT = dict(self.STATES)
            for result in read_group_result:
                state = result['state']
                result['state'] = (state, STATES_DICT.get(state))

        return super(res_partner, self)._read_group_fill_results(
            cr, uid, domain, groupby, remaining_groupbys, aggregated_fields,
            count_field, read_group_result, read_group_order, context
        )
    
    
    def init(self, cr):
        cr.execute("UPDATE res_partner SET address_id= "
                            "(SELECT id FROM address WHERE partner_address_id=1) "
                        "WHERE id=1 AND address_id IS NULL")
    
    def _auto_init(self, cursor, context=None):
        """
            On ne peut pas avoir deux fois le même nom pour un partenaire qui est une société
            On rempli l'adresse, le pays et la langue des partenaires dont le champ est vide 
            On configure également la première société pour qu'elle soit fournisseur et cliente
        """
        res = super(res_partner, self)._auto_init(cursor, context=context)
        #Name unique
        try:
            cursor.execute('SELECT indexname \
                    FROM pg_indexes \
                    WHERE indexname = \'res_partner_unique_name_for_company\'')
            if not cursor.fetchone():
                cursor.execute('CREATE UNIQUE INDEX res_partner_unique_name_for_company \
                        ON res_partner (name) WHERE is_company = True')
        except Exception:
            _schema.warning('Table res_partner: unable to set a constraint: res_partner_unique_name_for_company')
        
        cursor.commit()
        #Création des adresses pour les partenaires qui n'en ont pas
        cursor.execute('SELECT id FROM res_partner WHERE address_id IS NULL')
        for partner_id in cursor.fetchall():
            query = "INSERT INTO address (name, partner_address_id, country_id) \
                    SELECT name, id, (SELECT id FROM res_country WHERE code='FR') FROM res_partner WHERE id=%s"%(partner_id)
            cursor.execute(query)
        #Association des adresses aux partenaires qui n'en ont pas
        cursor.execute('SELECT id FROM res_partner WHERE address_id IS NULL')
        for partner_id in cursor.fetchall():
            query = "UPDATE res_partner partner SET address_id=(SELECT id FROM address \
            WHERE partner_address_id=partner.id LIMIT 1) WHERE id=%s"%(partner_id)
            cursor.execute(query)
        
        #Configuration de la première société
        cursor.execute("UPDATE res_partner SET is_customer=true,is_supplier=true,state='prospect' where id=1")
        return res
    
    
    @api.one
    @api.constrains('reference', 'is_company')
    def _check_unique_ref(self):
        """
            Contrainte qui vérifie que la référence est unique par société
        """
        if self.is_company:
            if self.search([('is_company', '=', True), ('reference', '=', self.reference), ('id', '!=', self.id)], limit=1):
                raise Warning(_("Partner's reference must be unique"))
                
    
    @api.one
    @api.constrains('is_company', 'state', 'is_supplier', 'is_customer', 'is_transporter')
    def _check_function(self):
        """
            Contrainte qui vérifie que:
                - les sociétés ont bien un état
                - il y a bien la case "Est client" ou "Est fournisseur" de coché
                - si le partenaire est transporteur, alors il est également fournisseur
        """
        if self.is_company :
            if not self.state:
                raise Warning(_('State is required for companies'))
        
            if self.is_transporter and not self.is_supplier:
                raise Warning(_('If the partner is a transporter, he must be a supplier too'))
                
            if not self.is_customer and not self.is_supplier and not self.is_group:
                raise Warning(_('You can\'t have a company which is neither a supplier nor a customer'))
    
    
    @api.one
    @api.constrains('is_customer', 'is_supplier', 'category_ids')
    def _check_block_boolean(self):
        """
            Verifie que les catégories associées au partenaire appartiennent au même type (fournisseur et/ou client)
        """
        category_ids = self.category_ids
        if category_ids and self.is_company:
            #Si le partenaire est à la fois un client et un fournisseur, il peut avoir des catégories d'un type, de l'autre,
            #ou des deux
            if self.is_customer and self.is_supplier:
                for category in category_ids:
                    if not category.is_customer and not category.is_supplier:
                        raise Warning(_('Error ! You cannot choose categories which is not for customer or supplier (%s)')%(category.name))
            #Si le partenaire est seulement un client, on vérifie que toutes ses catégories ont le type client de coché
            elif self.is_customer:
                for category in category_ids:
                    if not category.is_customer:
                        raise Warning(_('Error ! You cannot choose categories which is not for customer (%s)')%(category.name))
            #Si le partenaire est seulement un fournisseur, on vérifie que toutes ses catégories ont le type fournisseur de coché
            elif self.is_supplier:
                for category in category_ids:
                    if not category.is_supplier:
                        raise Warning(_('Error ! You cannot choose categories which is not for supplier (%s)')%(category.name))
        
        return True
    
    
    @api.onchange('is_transporter')
    def _onchange_is_transporter(self):
        """
            Quand on coche "Transporteur" dans le partenaire, on coche aussi "Est fournisseur"
        """
        if self.is_transporter:
            self.is_supplier = True
                
    @api.onchange('is_company')
    def _onchange_is_company(self):
        """
            Quand on coche "Société" on déclanche une sequence sur le nom
        """
        if self.is_company and not self.reference:
            self.reference = self.env['ir.sequence'].get('res.partner') or ''
    
    
    @api.onchange('name', 'first_name', 'company_address')
    def _onchange_name(self):
        """
            Au changement du nom (ou du prénom pour le contact) du partenaire, on va le copier dans le nom de l'adresse
            Si c'est une entreprise, on copie également son nom dans le champ corporate name
        """
        if not self.company_address:
            if not self.is_company:
                self.address_name = '%s %s'%(self.name or '', self.first_name or '')
            else:
                self.corporate_name = self.name
    
    
    @api.onchange('corporate_name')
    def _onchange_corporate_name(self):
        """
            Pour les entreprises, lorsqu'on change le corporate name, on va venir changer le nom de l'adresse
        """
        if not self.company_address:
            if self.is_company:
                self.address_name = self.corporate_name
    
    
    @api.onchange('parent_id', 'company_address')
    def _onchange_address_id(self):
        """
            Au changement de la société parente ou du booléen "Utiliser l'adresse de la société", 
            on récupère l'adresse de la société ou on l'enlève en fonction du booléen
        """
        if self.company_address:
            if self.parent_id:
                self.address_id = self.parent_id.address_id
            else:
                self.address_id = False
            
        elif self.is_company and self.name:
            address_ids = self.env['address'].search([('name', 'like', '%s %s'%(self.name or '', self.first_name or ''))], limit=1)
            self.address_id = address_ids and address_ids[0] or False
        else:
            self.address_id = False
    
    
    @api.onchange('country_id')
    def _onchange_country_id(self):
        """
            Si on change de pays, on vide le champ de la région
        """
        if self.region_id and self.region_id.country_id != self.country_id:
            self.region_id = False
            
            
    def get_transport_fields(self, return_id=False):
        if self:
            res = {
               'address_name': self.name,
               'street': self.street,
               'street2': self.street2,
               'street3': self.street3,
               'zip': self.zip,
               'city': self.city,
               'region_id': self.region_id and self.region_id.id or False,
               'country_id': return_id and self.country_id.id or self.country_id
                   }
        else:
            res = {
               'address_name': False,
               'street': False,
               'street2': False,
               'street3': False,
               'zip': False,
               'city': False,
               'region_id': False,
               'country_id': False,
                   }
            
        return res 
                
    
    def get_partner_address(self, infos={}, return_id=False):
        """
            Fonction qui ramène l'adresse du partenaire
            :type self: res.partner
            :param infos: Dictionnaire contenant les informations souhaitées
            :type infos: dict
            :param return_id: True si on veut les ids des adresses
            :type return_id: boolean
            :return: Le dictionnaire contenant les informations demandées
            :rtype: dict
        """
        res = {}
        partner = self
        if partner:
            principal_address = return_id and partner.address_id.id or partner.address_id 
            res['order_address'] = principal_address
            
        return res
    

    def calcul_value_com(self, contact_list, partner, mode_com):
        """
            Fonction permettant de ramener la valeur de la communication d'un partner
            En fonction d'un contact et d'un partner
        """
        res = ''
        if mode_com:
            if contact_list:
                if mode_com == 'fax' or mode_com == 'email':
                    res = ', '.join([contact[mode_com] for contact in contact_list if contact[mode_com]])
                    
            elif partner:
                if mode_com == 'fax':
                    res = partner.fax
                elif mode_com == 'email':
                    res = partner.email
                    
        return res
    
    
    def create_partner(self, company=False, partner_type=None, other_data=None):
        """
            Création d'un partenaire
            :type self: res.partner
            :param company: True si le partenaire est une société, sinon sera un contact
            :type company: boolean
            :param partner_type: Liste des types du partenaire
            :type partner_type: list : ['customer', 'supplier', 'transporter', 'group']
            :param other_data: Dictionnaire permettant de passer d'autres champs
            :type other_data: dict
            :return: Le partenaire créée
            :rtype: recordset res.partner
        """
        vals = {}
        if not other_data:
            other_data = {}
        
        if not partner_type:
            partner_type = []
        
        without_address = False
        #On fait la liste des champs requis pour créer un partenaire
        required_fields = ['name', 'lang'] 
        #Champs obligatoires dans le cas d'une société
        if company:
            vals['is_company'] = True
            required_fields += ['calendar_id', 
                                'currency_id']

            #Cas d'un client
            if 'customer' in partner_type:
                vals['is_customer'] = True
                #Le port sur facture n'est pas toujours requis, donc s'il n'est pas passé on lui passe never par
                #défaut
                vals['sale_invoice_postage'] = other_data.get('sale_invoice_postage', 'never')
                
            # Champs obligatoires dans le cas d'un fournisseur
            if 'supplier' in partner_type:
                required_fields += ['property_supplier_payment_term_id',
                                    'purchase_payment_method_id',
                                    'supplier_account_position_id',
                                    'purchase_invoicing_method_id',
                                    'purchase_incoterm_id']
                vals['is_supplier'] = True
                #Le port sur facture n'est pas toujours requis, donc s'il n'est pas passé on lui passe never par
                #défaut
                vals['purchase_invoice_postage'] = other_data.get('purchase_invoice_postage', 'never')
        
        else:
            #Dans le cas d'un contact, si il doit utiliser l'adresse de la société parent, 
            #On vérifie qu'il y ai bien une société parente 
            if other_data.get('company_adress'):
                if other_data.get('address'):
                    del other_data['address']
                    
                without_address = True
                if not other_data.get('parent_id'):
                    raise except_orm(_('Error'), _('If the contact use the address of the company, you need a parent company'))
                
        #Vérification des champs obligatoires
        for field in required_fields:
            if not other_data.get(field):
                raise except_orm(_('Error'), _('The field %s is required to create a partner')%(field))
        
        #On crée l'adresse liée au partenaire s'il ne s'agit pas d'un contact utilisant l'adresse du parent
        if not without_address:
            if other_data.get('address'):
                vals_adress = other_data['address']
                address = self.env['address'].create(vals_adress)
                vals.update({'address_id': address.id})
                del other_data['address']
            else:
                raise except_orm(_('Error'), _('You need an adress for your partner'))
                
        #On récupère les valeurs des champs
        vals.update(other_data)
        #Création du partenaire
        vals = utils.transform_to_ids(self, vals)
        partner = self.create(vals)
        return partner
           
            
    @api.multi
    @api.depends('name')
    def name_get(self):
        """
            Pour une société, on affiche [reference] nom
            Pour un contact, on affiche [nom] prénom
        """
        result = []
        for company in self:
            if company.is_company:
                name = '[%s] %s'%(company.reference, company.name)
            else:
                name = '[%s] %s'%(company.name, company.first_name or '')
                 
            result.append((company.id, name))
        
        return result            
#     @api.multi
#     @api.depends('name')
#     def name_get(self):
#         """
#             Pour une société, on affiche [reference] nom
#             Pour un contact, on affiche [nom] prénom
#         """
#         result = []
#         for company in self:
#             if company.is_company and company.name and company.reference and company.reference not in company.name:
#                 name = '[%s] %s'%(company.reference, company.name)
#             elif not company.is_company and company.name and company.first_name:
#                 name = '[%s] %s'%(company.name, company.first_name)
#             else:    
#                 name = company.name
#                  
#             result.append((company.id, name))
#         
#         return result
    
    
    @api.multi
    def write(self, vals=None):
        """
            On ne peut enlever le lien d'un contact avec une société s'il était lié à une société
            Si pas d'adresse existante, on en crée une
        """
        if not vals:
            vals = {}
        
        address_obj = self.env['address']
        for partner in self:
            if not partner.is_company:
                if 'parent_id' in vals and not vals['parent_id'] and partner.parent_id:
                    raise Warning(_("You can't clear out the company of a contact if this contact was linked to a company"))
            
                # Champ adresse vidé
                if 'address_id' in vals and not vals['address_id']:
                    if 'country_id' in vals:
                        address_values = {
                                          'name': vals.get('name') or partner.name,
                                          'street': vals.get('street', ''),
                                          'street2': vals.get('street2', ''),
                                          'street3': vals.get('street3', ''),
                                          'zip': vals.get('zip', ''),
                                          'city': vals.get('city', ''),
                                          'region_id': vals.get('region_id', ''),
                                          'country_id': vals['country_id'],
                                          }
                        address_id = address_obj.create(address_values)
                        vals['address_id'] = address_id and address_id.id or False
                        vals['address_name'] = vals.get('name') or partner.name
                    else:
                        raise Warning(_("You must select a country for your partner"))
            
        res = super(res_partner, self).write(vals=vals)
        ctx = self.env.context.copy()
        if vals and 'modif_value_partner_type' not in ctx:
            ctx['modif_value_partner_type'] = True
            modif_field_list=[]
            
            if list(set(vals.keys()) & set(self[0].paid_fields_partner())):
                modif_field_list.append('can_paid')
            
            if list(set(vals.keys()) & set(self[0].invoiced_fields_partner())):
                modif_field_list.append('can_be_charged')
            
            if list(set(vals.keys()) & set(self[0].delivered_fields_partner())):
                modif_field_list.append('can_be_delivered')
            
            if list(set(vals.keys()) & set(['type_ids'])):
                modif_field_list.append('type_ids')
            
            if 'can_paid' in vals:
                if vals['can_paid'] and 'can_paid' not in modif_field_list:
                    modif_field_list.append('can_paid')
                elif not vals['can_paid'] and 'type_ids' not in modif_field_list:
                    modif_field_list.append('type_ids')
            
            if 'can_be_charged' in vals:
                if vals['can_be_charged'] and 'can_be_charged' not in modif_field_list:
                    modif_field_list.append('can_be_charged')
                elif not vals['can_be_charged'] and 'type_ids' not in modif_field_list:
                    modif_field_list.append('type_ids')
                    
            if 'can_be_delivered' in vals:
                if vals['can_be_delivered'] and 'can_be_delivered' not in modif_field_list:
                    modif_field_list.append('can_be_delivered')
                elif not vals['can_be_delivered'] and 'type_ids' not in modif_field_list:
                    modif_field_list.append('type_ids')

            if modif_field_list:
                for partner in self:
                    if partner.is_customer:
                        for modif_field in modif_field_list:
                            partner.with_context(ctx).modif_value_partner_type(modif_field)
        
        if vals and 'modif_value_partner_purchase_type' not in ctx:
            ctx['modif_value_partner_purchase_type'] = True
            purchase_modif_field_list=[]
            if list(set(vals.keys()) & set(self[0].purchase_paid_fields_partner())):
                purchase_modif_field_list.append('paid_to')
            
            if list(set(vals.keys()) & set(self[0].purchase_invoiced_fields_partner())):
                purchase_modif_field_list.append('invoiced_by')
            
            if list(set(vals.keys()) & set(self[0].purchase_delivered_fields_partner())):
                purchase_modif_field_list.append('delivered_by')
            
            if list(set(vals.keys()) & set(['purchase_type_ids'])):
                purchase_modif_field_list.append('purchase_type_ids')
            
            if 'paid_to' in vals:
                if vals['paid_to'] and 'paid_to' not in purchase_modif_field_list:
                    purchase_modif_field_list.append('paid_to')
                elif not vals['paid_to'] and 'purchase_type_ids' not in purchase_modif_field_list:
                    purchase_modif_field_list.append('purchase_type_ids')
            
            if 'invoiced_by' in vals:
                if vals['invoiced_by'] and 'invoiced_by' not in purchase_modif_field_list:
                    purchase_modif_field_list.append('invoiced_by')
                elif not vals['invoiced_by'] and 'purchase_type_ids' not in purchase_modif_field_list:
                    purchase_modif_field_list.append('purchase_type_ids')
                    
            if 'delivered_by' in vals:
                if vals['delivered_by'] and 'can_be_delivered' not in purchase_modif_field_list:
                    purchase_modif_field_list.append('delivered_by')
                elif not vals['delivered_by'] and 'purchase_type_ids' not in purchase_modif_field_list:
                    purchase_modif_field_list.append('purchase_type_ids')

            if purchase_modif_field_list:
                for partner in self:
                    if partner.is_supplier:
                        for modif_field in purchase_modif_field_list:
                            partner.with_context(ctx).purchase_modif_value_partner_type(modif_field)
        
        return res
    
    
    @api.multi
    def unlink(self):
        """
            A la suppression d'un partenaire, on supprime les adresses qui lui sont liées
        """
        address_ids = self.env['address'].search([('partner_address_id', 'in', self.ids)])
        ctx = self.env.context.copy()
        for partner in self:
            if partner.company_id.partner_id == partner and not ctx.get('delete_partner_company', False):
                raise except_orm(_('Error'), _('You can not delete this partner (%s) because it is linked to a company'%(partner.reference)))
            
                 
        res = super(res_partner, self).unlink()
        if address_ids:
            context2 = {'partner_unlink': True}
            context2.update(self.env.context)
            address_ids.with_context(context2).unlink()
            
        return res
    
    
    @api.one
    def copy(self, default=None):
        default = dict(default or {})
        default['name'] = _('(copy) %s') % self.name
        default['reference'] = self.env['ir.sequence'].get('res.partner') or _('(copy) %s') % self.reference
        return super(res_partner, self).copy(default)
    
    
    @api.model
    def create(self, vals):
        """
            Création de l'adresse à la création du partner
        """
        #Si on a installé le multi adresse, on passe directement dans le create
        context = self.env.context
        address_obj = self.env['address']
        if not context.get('multi_address'):
            #Si le partenaire n'a pas de langue, on prend par défaut celle de l'utilisateur
            if not vals.get('lang'):
                code_lang = self.env.user.lang
                if code_lang:
                    vals['lang'] = code_lang
                else:
                    #Si on a pas de langue, on récupère la première de la liste
                    lang = self.env['res.lang'].search([], limit=1)
                    vals['lang'] = lang.code
                    
            if not vals.get('address_id'):
                address_id = False
                #Si le partenaire n'a pas de pays, on prend par défaut celui de la société de l'utilisateur
                if not vals.get('country_id'):
                    partner = self.env.user.company_id and self.env.user.company_id.partner_id or False 
                    country = partner and partner.country_id or False
                    if country:
                        vals['country_id'] = country.id
                    else:
                        #Si on a pas de pays, on prend le premier de la liste
                        country = self.env['res.country'].search([], limit=1)
                        vals['country_id'] = country.id
                        
                        
                if 'country_id' in vals and not vals.get('company_address'):
                    address_values = {
                                      'name': vals['name'],
                                      'street': vals.get('street', ''),
                                      'street2': vals.get('street2', ''),
                                      'street3': vals.get('street3', ''),
                                      'zip': vals.get('zip', ''),
                                      'city': vals.get('city', ''),
                                      'region_id': vals.get('region_id', ''),
                                      'country_id': vals['country_id'],
                                      }
                    address_id = address_obj.create(address_values)
                    vals['address_id'] = address_id and address_id.id or False
                #S'il s'agit d'un contact et qu'on a créé le parent en même temps, on récupère l'adresse
                #du parent pour l'assigner au contact
                elif vals.get('company_address') and vals.get('parent_id') and not vals.get('address_id'):
                    parent_address = self.browse(vals['parent_id']).address_id
                    vals['address_id'] = parent_address and parent_address.id or False
                    vals['address_name'] = parent_address.name
            else:
                address_id = address_obj.browse(vals.get('address_id'))
                vals['country_id'] = address_id.country_id and address_id.country_id.id or False 
            
            res = super(res_partner, self).create(vals=vals)
            #On met à jour le champ fonction de l'adresse
            if address_id and address_id.partner_address_id != res:
                query = "UPDATE address SET partner_address_id=%s WHERE id=%s"%(res.id, address_id.id)
                self.env.cr.execute(query)
        else:
            res = super(res_partner, self).create(vals=vals)
        
        ctx = self.env.context.copy()
        if vals and 'modif_value_partner_type' not in ctx:
            ctx['modif_value_partner_type'] = True
            modif_field_list=[]
            
            if list(set(vals.keys()) & set(res.paid_fields_partner())):
                modif_field_list.append('can_paid')
            
            if list(set(vals.keys()) & set(res.invoiced_fields_partner())):
                modif_field_list.append('can_be_charged')
            
            if list(set(vals.keys()) & set(res.delivered_fields_partner())):
                modif_field_list.append('can_be_delivered')
            
            if list(set(vals.keys()) & set(['type_ids'])):
                modif_field_list.append('type_ids')
            
            if 'can_paid' in vals:
                if vals['can_paid'] and 'can_paid' not in modif_field_list:
                    modif_field_list.append('can_paid')
                elif not vals['can_paid'] and 'type_ids' not in modif_field_list:
                    modif_field_list.append('type_ids')
            
            if 'can_be_charged' in vals:
                if vals['can_be_charged'] and 'can_be_charged' not in modif_field_list:
                    modif_field_list.append('can_be_charged')
                elif not vals['can_be_charged'] and 'type_ids' not in modif_field_list:
                    modif_field_list.append('type_ids')
                    
            if 'can_be_delivered' in vals:
                if vals['can_be_delivered'] and 'can_be_delivered' not in modif_field_list:
                    modif_field_list.append('can_be_delivered')
                elif not vals['can_be_delivered'] and 'type_ids' not in modif_field_list:
                    modif_field_list.append('type_ids')

            if modif_field_list:
                for partner in res:
                    if partner.is_customer:
                        for modif_field in modif_field_list:
                            partner.with_context(ctx).modif_value_partner_type(modif_field)
        
        
        if vals and 'modif_value_partner_purchase_type' not in ctx:
            ctx['modif_value_partner_purchase_type'] = True
            purchase_modif_field_list=[]
            if list(set(vals.keys()) & set(res.purchase_paid_fields_partner())):
                purchase_modif_field_list.append('paid_to')
            
            if list(set(vals.keys()) & set(res.purchase_invoiced_fields_partner())):
                purchase_modif_field_list.append('invoiced_by')
            
            if list(set(vals.keys()) & set(res.purchase_delivered_fields_partner())):
                purchase_modif_field_list.append('delivered_by')
            
            if list(set(vals.keys()) & set(['purchase_type_ids'])):
                purchase_modif_field_list.append('purchase_type_ids')
            
            if 'paid_to' in vals:
                if vals['paid_to'] and 'paid_to' not in purchase_modif_field_list:
                    purchase_modif_field_list.append('paid_to')
                elif not vals['paid_to'] and 'purchase_type_ids' not in purchase_modif_field_list:
                    purchase_modif_field_list.append('purchase_type_ids')
            
            if 'invoiced_by' in vals:
                if vals['invoiced_by'] and 'invoiced_by' not in purchase_modif_field_list:
                    purchase_modif_field_list.append('invoiced_by')
                elif not vals['invoiced_by'] and 'purchase_type_ids' not in purchase_modif_field_list:
                    purchase_modif_field_list.append('purchase_type_ids')
                    
            if 'delivered_by' in vals:
                if vals['delivered_by'] and 'can_be_delivered' not in purchase_modif_field_list:
                    purchase_modif_field_list.append('delivered_by')
                elif not vals['delivered_by'] and 'purchase_type_ids' not in purchase_modif_field_list:
                    purchase_modif_field_list.append('purchase_type_ids')

            if purchase_modif_field_list:
                for partner in res:
                    if partner.is_supplier:
                        for modif_field in purchase_modif_field_list:
                            partner.with_context(ctx).purchase_modif_value_partner_type(modif_field)
                            
        return res
    
    
    
    def additional_function_domain(self, arg):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de mrp_resource
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


    @api.model
    def search(self,args=None, offset=0, limit=None, order=None, count=None):
        args = args or []
        args_modified = self.compute_domain_args_resource(args)
        return super(res_partner,self).search(args=args_modified, offset=offset, limit=limit, order=order, count=count) 
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=1000):
        args = args or []
        if name:
            args = ['|', ('reference', operator, name), '|',('first_name', operator, name),
                     ('name', operator, name)] + args
        
        args_modified = self.compute_domain_args_resource(args)
        recs = self.search(args_modified, limit=limit)
        return recs.name_get()
    
    
    @api.multi
    def action_stopped(self):
        custo_info_obj = self.env['product.customerinfo']
        supp_info_obj = self.env['product.supplierinfo']
        for partner in self:
            if partner.is_customer:
                custo_rcs = custo_info_obj.search([('partner_id', '=', partner.id), ('state', '!=', 'obsolete')])
                custo_rcs.write({'state': 'obsolete'})
            if partner.is_supplier:
                supplier_rcs = supp_info_obj.search([('partner_id', '=', partner.id), ('state', '!=', 'obsolete')])
                supplier_rcs.write({'state': 'obsolete'})
    
    
    def paid_fields_partner(self):
        return [
                'property_payment_term_id',
                'sale_invoicing_method_id',
                'sale_payment_method_id',
                'sale_discount_management',
                'sale_max_delay',
                'sale_discount_value',
                ]


    def invoiced_fields_partner(self):
        return [
                'lock_invoices',
                'group_invoices',
                'invoices_period',
                'invoice_copy',
                'invoicing_contact_ids',
                'communication_value',
                'accounting_communication_method',
                'invoice_send_address_id'
                ]


    def delivered_fields_partner(self):
        return [
                'partial_sale_delivery',
                'generate_sale_rest',
                'property_account_position_id',
                'sale_delivery_contact_id',
                'sale_invoice_postage',
                'sale_incoterm_id',
                'sale_threshold',
                'sale_forwarding_agent_id',
                'sale_delivery_delay',
                'note_delivery_order',
                ]
    
    
    def modif_value_partner_type(self, modif_field):
        """"
            Mise à jour des champs dans les partenaires, selon les informations rentrées dans res.partner.type
            :param modif_field: Liste pour savoir quoi modifier: can_be_delivered, can_be_charged, can_paid, type_ids
            :type modif_field: char           
        """
        return True
    
    
    def purchase_paid_fields_partner(self):
        return [
                'property_supplier_payment_term_id',
                'purchase_invoicing_method_id',
                'purchase_payment_method_id',
                'purchase_discount_management',
                'purchase_max_delay',
                'purchase_discount_value',
                ]


    def purchase_invoiced_fields_partner(self):
        return [
                ]


    def purchase_delivered_fields_partner(self):
        return [
                'partial_purchase_delivery',
                'generate_purchase_rest',
                'supplier_account_position_id',
                'purchase_invoice_postage',
                'purchase_incoterm_id',
                'purchase_threshold',
                'purchase_forwarding_agent_id',
                'purchase_delivery_delay',
                'note_receipt_order',
                ]
    
    
    def purchase_modif_value_partner_type(self, modif_field):
        """"
            Mise à jour des champs dans les partenaires, selon les informations rentrées dans res.partner.type
            :param modif_field: Liste pour savoir quoi modifier: invoiced_by, delivered_by, paid_to, purchase_type_ids
            :type modif_field: char           
        """
        return True
    
    
    @api.multi
    def send_mail_free(self):
        """
            Fonction permettant d'envoyer un mail libre
        """
        for partner in self:
            context = self.env.context.copy()
            context['default_parent_id'] = False
            return self.env['mail.message'].with_context(context).action_send_mail(False, partner._name, '', partner.id)
    
    
    