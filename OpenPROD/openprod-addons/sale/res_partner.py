# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.addons.base_openprod.common import get_form_view


class partner_stat_family(models.Model):
    _inherit = 'partner.stat.family'
    
    is_sale = fields.Boolean(string='Sale', default=False)


    
class res_partner_type(models.Model):
    """ 
    Type for partners
    """
    _name = 'res.partner.type'
    _description = 'Type for partners'
    _rec_name = 'partner_type'
    _order = 'sequence'
    
    @api.model
    def _partner_type_get(self):
        return [
                ('can_paid', _('Paid per')),
                ('can_be_charged', _('Invoiced to')),
                ('can_be_delivered', _('Delivered to'))
                       ]
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    sequence = fields.Integer(string='Sequence', default=1, required=False)
    partner_type = fields.Selection('_partner_type_get', string='Type', required=True)
    partner_type_id = fields.Many2one('res.partner', string='Partner', required=False, ondelete='restrict')
    partner_id = fields.Many2one('res.partner', string='Partner', required=False, ondelete='cascade', select=True)
    
    @api.onchange('partner_type')
    def _onchange_partner_type(self):
        """
            On vide le champ du partner si on sélectionne un autre type
        """
        self.partner_type_id = False



class res_partner(models.Model):
    _inherit = 'res.partner'

    
    @api.model
    def _sale_communication_method_get(self):
        return [
                ('fax', _('Fax')),
                ('email', _('Email')),
                       ]
    
    # START TO DELETE #
    @api.model
    def _sale_invoicing_trigger_get(self):
        return [
                ('picking', _('To the delivery')),
                ('manual', _('On demand')),
                ('postpaid', _('On the order')),
                       ]
    # END TO DELETE #
    
    @api.model
    def _sale_invoiced_on_get(self):
        return [
                ('order', _('Ordered quantities')),
                ('delivery', _('Delivered quantities')),
                       ]
        
    
    @api.one
    @api.depends('email', 'fax', 'sale_contact_ids', 'sale_communication_method', 'receipt_demand', 'delay_confirmation')
    def _compute_sale_communication_value(self):
        if self.sale_communication_method:
            self.sale_communication_value = self.env['res.partner'].calcul_value_com(self.sale_contact_ids, self, self.sale_communication_method)
        else:
            self.sale_communication_value = ''
    
    
    @api.model
    def _sale_invoice_postage_get(self):
        return [
                ('never', _('Never')),
                ('always', _('Always')),
                ('threshold', _('< Threshold')),
                       ]
        
        
    @api.one
    def _compute_type_inv_ids(self):
        partner_type_rcs = self.env['res.partner.type'].search([('partner_type_id', '=', self.id)])
        partner_rcs = self.env['res.partner']
        if partner_type_rcs:
            for partner_type in partner_type_rcs:
                partner_rcs |= partner_type.partner_id
            
        self.type_inv_ids = partner_rcs.ids
        
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    
    # Onglet vente
    can_order = fields.Boolean(string='Authorized to place an order', default=False)
    can_be_charged = fields.Boolean(string='Authorized to be charged', default=False)
    can_be_delivered = fields.Boolean(string='Authorized to be delivered', default=False)
    can_paid = fields.Boolean(string='Authorized to paid', default=False)
    type_ids = fields.One2many('res.partner.type', 'partner_id',  string='Partners types')
    type_inv_ids = fields.Many2many('res.partner', 'sale_res_partner_type_partner_rel', 'partner_id', 'partner_type_inv_id',  string='Partners types inverse', compute='_compute_type_inv_ids')
    partial_sale_delivery = fields.Boolean(string='Partial delivery allowed', default=True, help='If you don\'t have enough stock available to '
                                           'deliver all at once, do you accept partial shipments or not?')
    generate_sale_rest = fields.Boolean(string='Allowed rest', default=True)
    receipt_demand = fields.Boolean(string='Acknowledgement or receipt demand', default=False)
    delay_confirmation = fields.Boolean(string='Delay confirmation', default=False)
    sale_contact_ids = fields.Many2many('res.partner', 'sale_contact_id_partner_rel', 'partner_id', 'contact_id', string='Contacts', help='If you choose a contact, '
                                      'the communication value will refer to its coordinates')
    sale_invoicing_method_id = fields.Many2one('account.invoicing.method', string='Invoicing method', required=False, ondelete='restrict')

    #Champ conservé pour la reprise des données, à supprimer plus tard
    sale_contact_id = fields.Many2one('res.partner', string='Contact', required=False, ondelete='restrict')
    sale_communication_method = fields.Selection('_sale_communication_method_get', string='Communication method')
    sale_communication_value = fields.Char(string='Communication value', compute='_compute_sale_communication_value')
    sales_manager_id = fields.Many2one('res.users', string='Sales manager', required=False, ondelete='restrict')
    seller_id = fields.Many2one('res.users', string='Seller', required=False, ondelete='restrict')
    stat_family_id = fields.Many2one('partner.stat.family', string='Statistics family', required=False, ondelete='restrict')
    edi_code = fields.Char(string='EDI code', size=17, required=False)
    num_with_customer = fields.Char(string='Our number with the customer', size=128, required=False)
    note_header = fields.Html(string='Note on the sale order header')
    sale_payment_method_id = fields.Many2one('payment.method', string='Payment method', required=False, ondelete='restrict')
    # START TO DELETE #
    sale_invoicing_trigger = fields.Selection('_sale_invoicing_trigger_get', string='Invoicing trigger method')
    sale_invoiced_on = fields.Selection('_sale_invoiced_on_get', string='Invoiced on', help='This field indicates if the invoice on the '
                                        'basis of quantities actually delivered or on the basis of quantities ordered (can be useful in '
                                        'case of flat rate, for example)')
    # END TO DELETE #
    sale_discount_management = fields.Boolean(string='Discount management', default=False)
    sale_max_delay = fields.Integer(string='Maximum delay for application', default=0, required=False, help="In days")
    sale_discount_value = fields.Float(string='Discount value', default=0.0, required=False)
    
    #Champ transport
    sale_incoterm_id = fields.Many2one('stock.incoterms', string='Incoterm', required=False, ondelete='restrict', help='Incoterm which '
                                       'stands for \'International Commercial terms\' implies its a series of sales terms which are used '
                                       'in the commercial transaction.')
    sale_invoice_postage = fields.Selection('_sale_invoice_postage_get', string='Invoice postage type')
    sale_threshold = fields.Float(string='Threshold', default=0.0, required=False)
    sale_forwarding_agent_id = fields.Many2one('res.partner', string='Forwarding Agent', required=False, ondelete='restrict')
    sale_delivery_delay = fields.Integer(string='Delivery delay', default=0, required=False, help="Carrier delay (in working days)")
    sale_delivery_contact_id = fields.Many2one('res.partner', string='Contact', required=False, ondelete='restrict')
    note_delivery_order = fields.Html(string='Note on delivery order')
    
    _sql_constraints = [
        ('check_sale_partner_qualified', 
         """CHECK((is_customer=true AND (state='qualified' AND ((can_be_charged = true AND sale_invoicing_method_id IS NOT NULL) OR (can_be_charged=false)) AND ((can_be_delivered = true AND property_account_position_id IS NOT NULL) OR (can_be_delivered=false)) AND ((can_paid = true AND property_payment_term_id IS NOT NULL AND sale_payment_method_id IS NOT NULL) OR (can_paid=false))) OR (state!='qualified')) OR (is_customer=false))""",
          """Some required fields are not filled, please check the form view of the partner:
                 - if the partner is delivered, you must fill the incoterm and the fiscal position,
                 - if the partner is invoiced, you must fill the invoicing method,
                 - and if the partner can pay, you must fill the payment term and the payment method.
          """)
    ]
    
# Même contrainte que ci-dessus indenté pour lisibilité.
#     _sql_constraints = [
#         ('check_sale_partner_qualified', 
#          """CHECK((
#                 is_customer=true AND (
#                     state='qualified' AND (
#                         (
#                             can_be_charged = true AND 
#                             sale_invoicing_method_id IS NOT NULL
#                         ) OR (can_be_charged=false)
#                     )
#                     AND (
#                         (
#                             can_be_delivered = true AND 
#                             property_account_position_id IS NOT NULL
#                         ) OR (can_be_delivered=false)
#                     )
#                     AND (
#                         (
#                             can_paid = true AND
#                             property_payment_term_id IS NOT NULL AND 
#                             sale_payment_method_id IS NOT NULL
#                         ) OR (can_paid=false)
#                     )
#                 ) OR (state!='qualified')
#             ) OR (is_customer=false))""",
#           """Some required fields are not filled, please check the form view of the partner:
#                  - if the partner is delivered, you must fill the incoterm and the fiscal position,
#                  - if the partner is invoiced, you must fill the invoicing method,
#                  - and if the partner can pay, you must fill the payment term and the payment method.
#           """)
#     ]
    
    
    @api.onchange('partial_sale_delivery')
    def _onchange_partial_sale_delivery(self):
        """
            Si 'Livraison incomplète' est décochée, on décoche 'Générer un reliquat'
        """
        if not self.partial_sale_delivery:
            self.generate_sale_rest = False
    
#     
#     @api.onchange('sale_invoicing_trigger')
#     def _onchange_sale_invoicing_trigger(self):
#         """
#             Si on passe le mode de déclenchement à la commande, on sélectionne la facturation sur 
#             quantités commandées
#             Si on passe le mode de déclenchement à la livraison, on sélectionne la facturation sur 
#             quantités livrées
#         """
#         if self.sale_invoicing_trigger in ['manual','postpaid']:
#             self.sale_invoiced_on = 'order'
#         elif self.sale_invoicing_trigger == 'picking' and self.property_payment_term_id.payment_type != 'after_invoicing':
#             self.sale_invoiced_on = 'delivery'
#     
#     
#     @api.onchange('sale_invoiced_on', 'property_payment_term_id')
#     def _onchange_sale_invoiced_on(self):
#         """
#             On modifie la méthode de déclenchement de facturation en fonction du type de paiement
#             et du type de facturation (qtés livrées ou commandées)
#         """
#         if self.sale_invoiced_on == 'delivery':
#             self.sale_invoicing_trigger = 'picking'
#         elif self.sale_invoiced_on == 'order' and self.property_payment_term_id.payment_type != 'after_invoicing' and self.sale_invoicing_trigger != 'manual':
#             self.sale_invoicing_trigger = 'postpaid'
    
    
#     @api.one
#     @api.constrains('sale_invoicing_trigger', 'sale_invoiced_on', 'property_payment_term_id', 'property_payment_term_id.payment_type')
#     def _check_sale_invoiced_on(self):
#         """
#             Verifie:
#             - que le déclenchement de la facturation soit cohérent avec le type de facturation
#             - que la facturation ne se fait pas sur les quantités livrées si la facturation est manuelle
#         """
#         if self.sale_invoiced_on == 'delivery' and self.sale_invoicing_trigger != 'picking':
#             raise Warning(_('Error ! You cannot have an invoice in the delivered quantities if the invoice trigger is not on the picking'))
#         
#         if self.sale_invoiced_on == 'order':
#             if self.property_payment_term_id.payment_type in ['before_validation', 'before_delivery'] and self.sale_invoicing_trigger not in ['postpaid', 'manual']:
#                 raise Warning(_('Error ! You cannot have an invoice in the ordered quantities if the invoice trigger is not in the order or manual'))
            
    
    @api.one
    @api.constrains('partial_sale_delivery', 'generate_sale_rest')
    def _check_partial_sale_delivery(self):
        """
            Verifie que le booléen de génération de reliquat soit bien décoché si celui
            de livraison incomplète l'es aussi 
        """
        if self.is_company and not self.partial_sale_delivery and self.generate_sale_rest:
            raise Warning(_('Error ! You cannot generate rest if you don\'t accept partial delivery (in the sale tab)'))
            
        return True
    
    
    @api.one
    @api.constrains('can_order', 'can_be_charged', 'can_be_delivered', 'can_paid')
    def _check_sale_partner_type(self):
        """
            Dans le cas d'un contact, si celui-ci est lié à une société, la société doit avoir
            la même configuration que lui (c'est-à-dire qu'elle doit être autorisée à commander
            si le contact est autorisé à commander, autorisée à payer si le contact l'est etc...).
            Si le contact n'est pas lié à une société, les 4 booléens doivent être cochés ou aucun
            ne doit l'être
            
            Dans le cas d'une société, si elle est autorisée à commander, on doit avoir au moins
            un livreur, un facturé et un payeur.
        """
        #Cas d'un contact
        if not self.is_company:
            parent_company = self.parent_id
            #Contact avec société parente
            if parent_company:
                if self.can_be_charged and not parent_company.can_be_charged:
                    raise Warning(_('Error ! If the contact can be charged, the parent company'
                                    ' must be charged too'))
                if self.can_be_delivered and not parent_company.can_be_delivered:
                    raise Warning(_('Error ! If the contact can be delivered, the parent company'
                                    ' must be delivered too'))
                if self.can_order and not parent_company.can_order:
                    raise Warning(_('Error ! If the contact can order, the parent company'
                                    ' must order too'))
                if self.can_paid and not parent_company.can_paid:
                    raise Warning(_('Error ! If the contact can pay, the parent company'
                                    ' must pay too'))
            
            else:
                #Contact sans société parente
                bool_count = 0
                if self.can_be_charged:
                    bool_count += 1
                    
                if self.can_be_delivered:
                    bool_count += 1
                    
                if self.can_order:
                    bool_count += 1
                    
                if self.can_paid:
                    bool_count += 1
                
                if bool_count != 4 and bool_count != 0:
                    raise Warning(_('Error ! If the contact haven\'t a parent company, it must'
                                    ' order, pay, be charged and be delivered, or none of them.'))
        
        else:
            #Cas d'une société qui peut commander
            if self.can_order and self.is_customer:
                delivered = False
                charged = False
                paid = False
                if self.can_be_delivered:
                    delivered = True
                
                if self.can_be_charged:
                    charged = True
                
                if self.can_paid:
                    paid = True
                
                for partner in self.type_ids:
                    if partner.partner_type == 'can_be_delivered':
                        delivered = True
                    elif partner.partner_type == 'can_be_charged':
                        charged = True
                    elif partner.partner_type == 'can_paid':
                        paid = True
                
                if not delivered or not charged or not paid:
                    raise Warning(_('Error ! If the partner can order, it must be or have a payer, '
                                    'a charged and a delivered.'))
                
        return True
    
    
    def get_partner_address(self, infos={}, return_id=False):
        """
            Fonction qui ramène toutes les adresses et les clients
            pour la livraison, la facturation, la commande et le paiement
            On passe un dictionnaire dans lequel on entre les informations souhaitées. Exemple:
            Si on ne souhaite que l'adresse de livraison, on entrera uniquement 'delivery' dans le dictionnaire
            :type self: res.partner
            :param infos: Dictionnaire contenant les informations souhaitées
            :type infos: dict
            :param return_id: True si on veut des ids, False pour des recordset
            :type return_id: boolean
            :return: Le dictionnaire contenant les informations demandées
            :rtype: dict
        """
        res = super(res_partner, self).get_partner_address(infos=infos, return_id=return_id)
        #La fonction est en deux parties : le cas d'un partenaire client et le cas d'un contact
        # 1 - Partner client
        #On vérifie avant tout que le partner soit bien un client, sinon on renvoie un dictionnaire vide
        partner = self
        if partner:
            principal_address = return_id and partner.address_id.id or partner.address_id 
            principal_customer = return_id and partner.id or partner
            res['order_address'] = principal_address
            if partner.is_company and partner.is_customer:
                #On commence par récupérer l'adresse principale du partner pour
                #la passer en tant qu'adresse de la commande
                #On regarde ensuite si le partner peut être livré. Si c'est le cas, 
                #on renvoie son adresse principale et l'id du partner
                if infos.get('delivery'):
                    if partner.can_be_delivered:
                        res['delivery_address'] = principal_address
                        res['delivery_partner'] = principal_customer
                    #Sinon, on recherche et récupère le partner ou contact livré, ainsi que
                    #son adresse principale.
                    else:
                        for line in partner.type_ids:
                            if line.partner_type == 'can_be_delivered':
                                res['delivery_partner'] = return_id and line.partner_type_id.id or line.partner_type_id
                                res['delivery_address'] = return_id and line.partner_type_id.address_id.id or line.partner_type_id.address_id
                                break
                
                #On regarde ensuite si le partner peut être facturé. Si c'est le cas, 
                #on renvoie son adresse principale et l'id du partner
                if infos.get('invoiced'):
                    if partner.can_be_charged:
                        res['invoiced_address'] = principal_address
                        res['invoiced_partner'] = principal_customer
                    #Sinon, on recherche et récupère le partner ou contact facturé, ainsi que
                    #son adresse principale.
                    else:
                        for line in partner.type_ids:
                            if line.partner_type == 'can_be_charged':
                                res['invoiced_partner'] = return_id and line.partner_type_id.id or line.partner_type_id
                                res['invoiced_address'] = return_id and line.partner_type_id.address_id.id or line.partner_type_id.address_id
                                break
                        
                #On regarde enfin si le partner peut être payeur. Si c'est le cas, 
                #on renvoie id. Sinon, on recherche et récupère le partner ou contact payeur
                if infos.get('paid'):
                    if partner.can_paid:
                        res['pay_partner'] = principal_customer
                    else:
                        for line in partner.type_ids:
                            if line.partner_type == 'can_paid':
                                res['pay_partner'] = return_id and line.partner_type_id.id or line.partner_type_id
                                break
            
            # 2 - Contact
            elif not partner.is_company:
                #Si le contact n'est pas lié à un partenaire, on récupère son adresse et son id pour tous les champs
                if not partner.parent_id and partner.can_be_charged and partner.can_be_delivered and partner.can_paid \
                and partner.can_order:
                    if infos.get('delivery'):
                        res['delivery_address'] = principal_address
                        res['delivery_partner'] = principal_customer
                    
                    if infos.get('invoiced'):
                        res['invoiced_address'] = principal_address
                        res['invoiced_partner'] = principal_customer
                    
                    if infos.get('paid'):
                        res['pay_partner'] = principal_customer
                    
                    res['pay_partner'] = principal_customer
                    
                elif partner.parent_id:
                    related_partner = partner.parent_id
                    if infos.get('invoiced'):
                        if partner.can_be_charged:
                            res['invoiced_address'] = principal_address
                            res['invoiced_partner'] = principal_customer
                        elif related_partner.can_be_charged:
                            res['invoiced_address'] = return_id and related_partner.address_id.id or related_partner.address_id 
                            res['invoiced_partner'] = return_id and related_partner.id or related_partner
                        else:
                            for line in related_partner.type_ids:
                                if line.partner_type == 'can_be_charged':
                                    res['invoiced_partner'] = return_id and line.partner_type_id.id or line.partner_type_id
                                    res['invoiced_address'] = return_id and line.partner_type_id.address_id.id or line.partner_type_id.address_id
                                    break
                    
                    if infos.get('delivery'):
                        if partner.can_be_delivered:
                            res['delivery_address'] = principal_address
                            res['delivery_partner'] = principal_customer
                        elif related_partner.can_be_delivered:
                            res['delivery_address'] = related_partner.address_id and related_partner.address_id.id or False 
                            res['delivery_partner'] = related_partner.id
                        else:
                            for line in related_partner.type_ids:
                                if line.partner_type == 'can_be_delivered':
                                    res['delivery_partner'] = return_id and line.partner_type_id.id or line.partner_type_id
                                    res['delivery_address'] = return_id and line.partner_type_id.address_id.id or line.partner_type_id.address_id
                                    break
                    
                    if infos.get('paid'):
                        if partner.can_paid:
                            res['pay_partner'] = principal_customer
                        elif related_partner.can_paid:
                            res['pay_partner'] = related_partner.id
                        else:
                            for line in related_partner.type_ids:
                                if line.partner_type == 'can_paid':
                                    res['pay_partner'] = return_id and line.partner_type_id.id or line.partner_type_id
                                    break
                        
        return res
    
    
    @api.multi
    def show_partner_sale(self):
        """
            Fonction qui cherche et retourne les ventes du partenaire
        """
        action_struc = {}
        action_dict = get_form_view(self, 'sale.action_see_all_sale_order')
        if action_dict and action_dict.get('id') and action_dict.get('type'):
            action = self.env[action_dict['type']].browse(action_dict['id'])
            action_struc = action.read()
            action_struc[0]['context'] = {'partner_id': self.id}
            action_struc = action_struc[0]
              
        return action_struc
    
        
    def get_sale_transport_fields(self, return_id=False):
        if self:
            res = {
               'sale_incoterm_id': return_id and self.sale_incoterm_id.id or self.sale_incoterm_id,
               'sale_invoice_postage': self.sale_invoice_postage,
               'sale_threshold': self.sale_threshold,
               'sale_forwarding_agent_id': return_id and self.sale_forwarding_agent_id.id or self.sale_forwarding_agent_id,
               'transport_delay': self.sale_delivery_delay,
                   }
        else:
            res = {
               'sale_incoterm_id': False,
               'sale_invoice_postage': False,
               'sale_threshold': False,
               'sale_forwarding_agent_id': False,
               'transport_delay': False,
                   }
            
        return res
    
    
    def compute_domain_args(self, args):
        #Fonction appelée par le search afin de n'afficher que les contacts inscrits dans la liste de contact
        args2 = []
        partner_type_obj = self.env['res.partner.type']
        partner_obj = self.env['res.partner']
        for arg in args:
            match = False
            if isinstance(arg, str) or (isinstance(arg, list) and arg[0] in ('!', '|', '&')):
                args2.append(arg)
                continue
             
            if arg[0] == 'contact_in_partner_sale':
                arg[0] = 'id'
                arg[-1] = [x[1] for x in arg[-1] if x[0] != 2]
            elif arg[0] == 'partner_contact_sale_order':
                arg[0] = 'id'
                arg[1] = 'in'
                partner_id = arg[-1]
                arg[-1] = []
                for contact in self.browse(partner_id).contact_ids:
                    arg[-1].append(contact.id)
            elif arg[0] == 'invoiced_customer_in_order_list':
                arg[0] = 'id'
                arg[1] = 'in'
                partner_rs = partner_obj.browse(arg[-1]) 
                if not partner_rs.is_company and partner_rs.parent_id:
                    partner_rs = partner_rs.parent_id
                    
                arg[-1] = [x.partner_type_id.id for x in partner_type_obj.search([('partner_type', '=', 'can_be_charged'), 
                                                                                         ('partner_id', '=', partner_rs.id)]) if x.partner_type_id]
            elif arg[0] in ('cust_can_order', 'cust_can_be_charged'):
                if isinstance(arg[-1], list) and arg[-1][0]:
                    arg = ('id', '=', arg[-1][1])
                else:
                    match = True
                    args2.append((arg[0][5:], '=', True))
                    args2.append('|')
                    args2.append(('is_company', '=', False))
                    args2.append(('is_customer', '=', True))
            
            #On affiche les partenaires qui ont le partenaire passé dans le domaine dans leur liste de facturé
            elif arg[0] == 'order_customer_in_invoiced_list':
                arg[0] = 'id'
                arg[1] = 'in'
                partner_rs = partner_obj.browse(arg[-1]) 
                if not partner_rs.is_company and partner_rs.parent_id:
                    partner_rs = partner_rs.parent_id
                    
                arg[-1] = [x.partner_id.id for x in partner_type_obj.search([('partner_type', '=', 'can_be_charged'), 
                                                                                         ('partner_type_id', '=', partner_rs.id)]) if x.partner_id]
            #On affiche les partenaires livrables qui sont dans la liste du partenaire passé dans le domaine
            elif arg[0] == 'delivered_customer_in_order_list':
                arg[0] = 'id'
                arg[1] = 'in'
                partner_rs = partner_obj.browse(arg[-1]) 
                if not partner_rs.is_company and partner_rs.parent_id:
                    partner_rs = partner_rs.parent_id
                    
                arg[-1] = [x.partner_type_id.id for x in partner_type_obj.search([('partner_type', '=', 'can_be_delivered'), 
                                                                                         ('partner_id', '=', partner_rs.id)]) if x.partner_type_id]
            #On affiche les partenaires payeurs qui sont dans la liste du partenaire passé dans le domaine
            elif arg[0] == 'paid_customer_in_order_list':
                arg[0] = 'id'
                arg[1] = 'in'
                partner_rs = partner_obj.browse(arg[-1]) 
                if not partner_rs.is_company and partner_rs.parent_id:
                    partner_rs = partner_rs.parent_id
                    
                arg[-1] = [x.partner_type_id.id for x in partner_type_obj.search([('partner_type', '=', 'can_paid'), 
                                                                                         ('partner_id', '=', partner_rs.id)]) if x.partner_type_id]
                    
            if not match:
                args2.append(arg)
              
        return args2
  
      
    @api.model
    def search(self,args=None, offset=0, limit=None, order=None, count=None):
        #Modification du search afin de n'afficher que les contacts inscrits dans la liste de contact
        args = args or []
        args_modified = self.compute_domain_args(args)
        return super(res_partner,self).search(args=args_modified, offset=offset, limit=limit, order=order, count=count)
     
     
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False,lazy=True):
        domain = self.compute_domain_args(domain)
        return super(res_partner, self).read_group(domain=domain, fields=fields, groupby=groupby, offset=offset, limit=limit, orderby=orderby,lazy=lazy)

    
    def modif_value_partner_type(self, modif_field):
        """"
            Mise à jour des champs dans les partenaires, selon les informations rentrées dans res.partner.type
            :param modif_field: Liste pour savoir quoi modifier: can_be_delivered, can_be_charged, can_paid, type_ids
            :type modif_field: char           
        """
        res = super(res_partner, self).modif_value_partner_type(modif_field=modif_field)  
        if modif_field == 'can_paid' and self.can_paid:
            request = """Select
                            partner_type_val.partner_id
                        From
                            (Select
                        
                                partner_id,
                                id
                            From
                                res_partner_type
                            Where
                                partner_type_id =  %s and
                                partner_type = 'can_paid') partner_type_val,
                            res_partner
                        Where
                            (res_partner.can_paid is null or res_partner.can_paid = false) and
                            partner_type_val.partner_id = res_partner.id and
                            partner_type_val.id = (Select id 
                                                   From res_partner_type 
                                                   Where partner_type = 'can_paid' and 
                                                         partner_id = partner_type_val.partner_id 
                                                   order by sequence asc limit 1) """%(self.id)
            self.env.cr.execute(request)
            res_sql = self.env.cr.fetchall()  
            if res_sql:
                partner_ids = [x[0] for x in res_sql]
                paid_vals = {}
                for x in self.paid_fields_partner():
                    if type(self[x]) is not int and type(self[x]) is not str and type(self[x]) is not float and type(self[x]) is not bool and type(self[x]) is not unicode and self[x] != None: 
                        if isinstance((self._fields[x]), fields.Many2many) or isinstance((self._fields[x]), fields.One2many):
                            paid_vals[x] = []
                            for i in self[x].ids:
                                paid_vals[x].append((4, i))
                        else:
                            paid_vals[x] = self[x].id
                    else:
                        paid_vals[x] = self[x]
                
                self.browse(partner_ids).write(paid_vals)
        
        elif modif_field == 'can_be_delivered' and self.can_be_delivered:
            request = """Select
                            partner_type_val.partner_id
                        From
                            (Select
                        
                                partner_id,
                                id
                            From
                                res_partner_type
                            Where
                                partner_type_id =  %s and
                                partner_type = 'can_be_delivered') partner_type_val,
                            res_partner
                        Where
                            (res_partner.can_be_delivered is null or res_partner.can_be_delivered = false) and
                            partner_type_val.partner_id = res_partner.id and
                            partner_type_val.id = (Select id 
                                                   From res_partner_type 
                                                   Where partner_type = 'can_be_delivered' and 
                                                         partner_id = partner_type_val.partner_id 
                                                   order by sequence asc limit 1) """%(self.id)
            self.env.cr.execute(request)
            res_sql = self.env.cr.fetchall()  
            if res_sql:
                partner_ids = [x[0] for x in res_sql]
                delivered_vals = {}
                for x in self.delivered_fields_partner():
                    if type(self[x]) is not int and type(self[x]) is not str and type(self[x]) is not float and type(self[x]) is not bool and type(self[x]) is not unicode and self[x] != None: 
                        if isinstance((self._fields[x]), fields.Many2many) or isinstance((self._fields[x]), fields.One2many):
                            delivered_vals[x] = []
                            for i in self[x].ids:
                                delivered_vals[x].append((4, i))
                        else:
                            delivered_vals[x] = self[x].id
                    else:
                        delivered_vals[x] = self[x]
                            
                self.browse(partner_ids).write(delivered_vals)

        elif modif_field == 'can_be_charged' and self.can_be_charged:
            request = """Select
                            partner_type_val.partner_id
                        From
                            (Select
                        
                                partner_id,
                                id
                            From
                                res_partner_type
                            Where
                                partner_type_id =  %s and
                                partner_type = 'can_be_charged') partner_type_val,
                            res_partner
                        Where
                            (res_partner.can_be_charged is null or res_partner.can_be_charged = false) and
                            partner_type_val.partner_id = res_partner.id and
                            partner_type_val.id = (Select id 
                                                   From res_partner_type 
                                                   Where partner_type = 'can_be_charged' and 
                                                         partner_id = partner_type_val.partner_id 
                                                   order by sequence asc limit 1) """%(self.id)
            self.env.cr.execute(request)
            res_sql = self.env.cr.fetchall()  
            if res_sql:
                partner_ids = [x[0] for x in res_sql]
                invoiced_vals = {}
                for x in self.invoiced_fields_partner():
                    if type(self[x]) is not int and type(self[x]) is not str and type(self[x]) is not float and type(self[x]) is not bool and type(self[x]) is not unicode and self[x] != None: 
                        if isinstance((self._fields[x]), fields.Many2many) or isinstance((self._fields[x]), fields.One2many):
                            invoiced_vals[x] = []
                            for i in self[x].ids:
                                invoiced_vals[x].append((4, i))
                        else:
                            invoiced_vals[x] = self[x].id
                    else:
                        invoiced_vals[x] = self[x]
                    
                self.browse(partner_ids).write(invoiced_vals)

        elif modif_field == 'type_ids':
            partner_type_obj = self.env['res.partner.type']
            if not self.can_paid:
                partner_type_rcs = partner_type_obj.search([('partner_type', '=', 'can_paid'), ('partner_id', '=', self.id)], order='sequence asc', limit=1)
                if partner_type_rcs:
                    paid_vals = {}
                    for x in self.paid_fields_partner():
                        if type(partner_type_rcs.partner_type_id[x]) is not int and type(partner_type_rcs.partner_type_id[x]) is not str and type(partner_type_rcs.partner_type_id[x]) is not float and type(partner_type_rcs.partner_type_id[x]) is not bool and type(partner_type_rcs.partner_type_id[x]) is not unicode and partner_type_rcs.partner_type_id[x] != None:
                            if isinstance((self._fields[x]), fields.Many2many) or isinstance((self._fields[x]), fields.One2many):
                                paid_vals[x] = []
                                for i in partner_type_rcs.partner_type_id[x].ids:
                                    paid_vals[x].append((4, i))
                            else:
                                paid_vals[x] = partner_type_rcs.partner_type_id[x].id
                        else:
                            paid_vals[x] = partner_type_rcs.partner_type_id[x]
                            
                    self.write(paid_vals)
            
            if not self.can_be_delivered:
                partner_type_rcs = partner_type_obj.search([('partner_type', '=', 'can_be_delivered'), ('partner_id', '=', self.id)], order='sequence asc', limit=1)
                if partner_type_rcs:
                    delivered_vals = {}
                    for x in self.delivered_fields_partner():
                        if type(partner_type_rcs.partner_type_id[x]) is not int and type(partner_type_rcs.partner_type_id[x]) is not str and type(partner_type_rcs.partner_type_id[x]) is not float and type(partner_type_rcs.partner_type_id[x]) is not bool and type(partner_type_rcs.partner_type_id[x]) is not unicode and partner_type_rcs.partner_type_id[x] != None: 
                            if isinstance((self._fields[x]), fields.Many2many) or isinstance((self._fields[x]), fields.One2many):
                                delivered_vals[x] = []
                                for i in partner_type_rcs.partner_type_id[x].ids:
                                    delivered_vals[x].append((4, i))
                            else:
                                delivered_vals[x] = partner_type_rcs.partner_type_id[x].id
                        else:
                            delivered_vals[x] = partner_type_rcs.partner_type_id[x]
                    
                    self.write(delivered_vals)
            
            if not self.can_be_charged:
                partner_type_rcs = partner_type_obj.search([('partner_type', '=', 'can_be_charged'), ('partner_id', '=', self.id)], order='sequence asc', limit=1)
                if partner_type_rcs:
                    invoiced_vals = {}
                    for x in self.invoiced_fields_partner():
                        if type(partner_type_rcs.partner_type_id[x]) is not int and type(partner_type_rcs.partner_type_id[x]) is not str and type(partner_type_rcs.partner_type_id[x]) is not float and type(partner_type_rcs.partner_type_id[x]) is not bool and type(partner_type_rcs.partner_type_id[x]) is not unicode and partner_type_rcs.partner_type_id[x] != None:
                            if isinstance((self._fields[x]), fields.Many2many) or isinstance((self._fields[x]), fields.One2many):
                                invoiced_vals[x] = []
                                for i in partner_type_rcs.partner_type_id[x].ids:
                                    invoiced_vals[x].append((4, i))
                            else:
                                invoiced_vals[x] = partner_type_rcs.partner_type_id[x].id
                        else:
                            invoiced_vals[x] = partner_type_rcs.partner_type_id[x]
                    
                    self.write(invoiced_vals)
        
        return res



class address(models.Model):
    _inherit = 'address'
    
    def compute_domain_args(self, args):
        #Fonction appelée par le search afin de n'afficher que les adresses du partenaire entré
        args2 = []
        for arg in args:
            if isinstance(arg, str) or (isinstance(arg, list) and arg[0] in ('!', '|', '&')):
                args2.append(arg)
                continue
            
            if isinstance(arg[-1], int):
                if arg[0] == 'partner_address_id' and self.env['res.partner'].browse(arg[-1]).company_address:
                    arg[-1] = self.env['res.partner'].browse(arg[-1]).parent_id.id
                
            args2.append(arg)
            
        return args2
    
    
    @api.model
    def search(self,args=None, offset=0, limit=None, order=None, count=None):
        #Modification du search afin de n'afficher que les adresses du contact ou du partenaire
        args = args or []
        args_modified = self.compute_domain_args(args)
        return super(address,self).search(args=args_modified, offset=offset, limit=limit, order=order, count=count)
    
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=1000):
        """
            Fonction name_search de l'adresse
        """
        args = self.compute_domain_args(args)
        recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()
    
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False,lazy=True):
        domain = self.compute_domain_args(domain)
        return super(address, self).read_group(domain=domain, fields=fields, groupby=groupby, offset=offset, limit=limit, orderby=orderby,lazy=lazy)