# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.addons.base_openprod.common import get_form_view

class partner_stat_family(models.Model):
    _inherit = 'partner.stat.family'
    
    is_purchase = fields.Boolean(string='Purchase', default=False)



class res_partner_purchase_type(models.Model):
    """ 
        Purchase type for partners
    """
    _name = 'res.partner.purchase.type'
    _description = 'Purchase type for partners'
    _rec_name = 'partner_type'
    _order = 'sequence'
    
    @api.model
    def _partner_type_get(self):
        return [
                ('paid_to', _('Paid to')),
                ('invoiced_by', _('Invoiced by')),
                ('delivered_by', _('Delivered by')),
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
    # START TO DELETE #
    @api.model
    def _purchase_invoicing_trigger_get(self):
        return [
                ('picking', _('To the delivery')),
                ('manual', _('On demand')),
                ('postpaid', _('On the order')),
                       ]
    
    @api.model
    def _purchase_invoiced_on_get(self):
        return [
                ('order', _('Ordered quantities')),
                ('delivery', _('Delivered quantities')),
                       ]
    # END TO DELETE #
    @api.model
    def _purchase_communication_method_get(self):
        return [
                ('fax', _('Fax')),
                ('email', _('Email')),
                       ]
    
    @api.model
    def _purchase_invoice_postage_get(self):
        return [
                ('never', _('Never')),
                ('always', _('Always')),
                ('threshold', _('< Threshold')),
                       ]
    
    @api.one
    @api.depends('email', 'fax', 'purchase_contact_ids', 'purchase_communication_method')
    def _compute_purchase_communication_value(self):
        self.purchase_communication_value = self.env['res.partner'].calcul_value_com(self.purchase_contact_ids, self, 
                                                                                 self.purchase_communication_method)
    
    @api.one
    def _compute_purchase_type_inv_ids(self):
        partner_type_rcs = self.env['res.partner.purchase.type'].search([('partner_type_id', '=', self.id)])
        partner_rcs = self.env['res.partner']
        if partner_type_rcs:
            for partner_type in partner_type_rcs:
                partner_rcs |= partner_type.partner_id
            
        self.purchase_type_inv_ids = partner_rcs.ids
        
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    # Onglet achat
    is_seller = fields.Boolean(string='Is seller', default=False)
    invoiced_by = fields.Boolean(string='Invoiced by', default=False)
    delivered_by = fields.Boolean(string='Delivered by', default=False)
    paid_to = fields.Boolean(string='Paid to', default=False)
    purchase_type_ids = fields.One2many('res.partner.purchase.type', 'partner_id',  string='Partners types')
    purchase_type_inv_ids = fields.Many2many('res.partner', 'purchase_res_partner_type_partner_rel', 'partner_id', 'partner_type_inv_id',  string='Partners types inverse', compute='_compute_purchase_type_inv_ids')
    partial_purchase_delivery = fields.Boolean(string='Partial receipt', default=False)
    generate_purchase_rest = fields.Boolean(string='Generate rest', default=False)
    purchase_receipt_demand = fields.Boolean(string='Request RD', default=False)
    supplier_reminder = fields.Boolean(string='Supplier reminder', default=False)
    reminder_delay = fields.Integer(string='Reminder delay', default=0, required=False, help="In days")
    purchase_contact_ids = fields.Many2many('res.partner', 'purchase_contact_id_partner_rel', 'partner_id', 'contact_id', string='Contacts')
    #Champ conservé pour la reprise des données, à supprimer plus tard
    purchase_contact_id = fields.Many2one('res.partner', string='Contact', required=False, ondelete='restrict')
    purchase_communication_method = fields.Selection('_purchase_communication_method_get', string='Communication method')
    purchaser_id = fields.Many2one('res.users', string='Purchaser', required=False, ondelete='restrict')
    purchase_stat_family_id = fields.Many2one('partner.stat.family', string='Statistics family', required=False, ondelete='restrict')
    gei_code = fields.Char(string='GEI code', size=16, required=False)
    num_with_supplier = fields.Char(string='Our number with the supplier', size=128, required=False)
    note_purchase_header = fields.Html(string='Note on the purchase order header')
    purchase_payment_method_id = fields.Many2one('payment.method', string='Payment method', required=False, ondelete='restrict')
    # START TO DELETE #
    purchase_invoicing_trigger = fields.Selection('_purchase_invoicing_trigger_get', string='Invoicing trigger method')
    purchase_invoiced_on = fields.Selection('_purchase_invoiced_on_get', string='Invoiced on')
    # END TO DELETE #
    purchase_discount_management = fields.Boolean(string='Discount management', default=False)
    purchase_max_delay = fields.Integer(string='Maximum delay for application', default=0, required=False, help="In days")
    purchase_discount_value = fields.Float(string='Discount value', default=0.0, required=False)
    supplier_account_position_id = fields.Many2one('account.fiscal.position', string='Fiscal position', required=False, 
                                                   ondelete='restrict', help="The fiscal position will determine taxes"
                                                   " and accounts used for the partner.")
    purchase_communication_value = fields.Char(string='Communication value', compute='_compute_purchase_communication_value', help='Select '
                                               'the mode of communication. It will be proposed by default when sending the order to the '
                                               'supplier or used to boost the supplier who did not confirm the order within 48 hours')
    #Champ transport
    purchase_incoterm_id = fields.Many2one('stock.incoterms', string='Incoterm', required=False, ondelete='restrict', help='Incoterm which '
                                       'stands for \'International Commercial terms\' implies its a series of sales terms which are used '
                                       'in the commercial transaction.')
    purchase_invoice_postage = fields.Selection('_purchase_invoice_postage_get', string='Invoice postage type')
    purchase_threshold = fields.Float(string='Threshold', default=0.0, required=False)
    purchase_forwarding_agent_id = fields.Many2one('res.partner', string='Forwarding Agent', required=False, ondelete='restrict')
    purchase_delivery_delay = fields.Integer(string='Delivery delay', default=0, required=False)
    note_receipt_order = fields.Html(string='Note on receipt order')
    purchase_invoicing_method_id = fields.Many2one('account.invoicing.method', string='Invoicing method', required=False, ondelete='restrict')

    _sql_constraints = [(
        'check_purchase_partner_qualified', 
         """CHECK((is_supplier=true AND (state='qualified' AND ((invoiced_by=true AND purchase_invoicing_method_id IS NOT NULL) OR (invoiced_by=false)) AND ((delivered_by=true AND supplier_account_position_id IS NOT NULL) OR (delivered_by=false)) AND ((paid_to=true AND property_supplier_payment_term_id IS NOT NULL AND purchase_invoicing_method_id IS NOT NULL AND purchase_payment_method_id IS NOT NULL) OR (paid_to=false))) OR (state!='qualified')) OR (is_supplier=false))""",
          """Some required fields are not filled, please check the form view of the partner:
                 - if the partner is a delivery, you must fill the incoterm and the fiscal position,
                 - if the partner can invoice, you must fill the invoicing method,
                 - if the partner can be payed, you must fill the payment term and the payment method.
          """
    )]
    
    @api.one
    @api.constrains('is_seller', 'invoiced_by', 'paid_to', 'delivered_by')    
    def _check_purchase_partner_type(self):
        """
            Si le partenaire est un fournisseur qui est une société et qu'il est autorisé à vendre,
            on doit avoir au moins un factureur, un livreur et un payé à.
        """
        if self.is_company and self.is_supplier:
            if self.is_seller:
                invoiced_by = False
                delivered_by = False
                paid_to = False
                if self.invoiced_by:
                    invoiced_by = True
                
                if self.paid_to:
                    paid_to = True

                if self.delivered_by:
                    delivered_by = True
                
                for partner in self.purchase_type_ids:
                    if partner.partner_type == 'invoiced_by':
                        invoiced_by = True
                    elif partner.partner_type == 'paid_to':
                        paid_to = True
                    elif partner.partner_type == 'delivered_by':
                        delivered_by = True
                
                if not invoiced_by or not paid_to or not delivered_by:
                    raise Warning(_('Error ! If the partner can sell, it must be or have a "paid to" partner, '
                                    'and an "invoiced by" partner.'))
                
        return True
    
    
    @api.onchange('partial_purchase_delivery')
    def _onchange_partial_purchase_delivery(self):
        """
            Si 'Livraison incomplète' est décochée, on décoche 'Générer un reliquat'
        """
        if not self.partial_purchase_delivery:
            self.generate_purchase_rest = False
            
    
#     @api.onchange('purchase_invoiced_on', 'property_supplier_payment_term_id')
#     def _onchange_purchase_invoiced_on(self):
#         """
#             Si on passe la facturation sur les quantités livrées, on sélectionne le mode de déclenchement à la livraison
#         """
#         if self.purchase_invoiced_on == 'delivery':
#             self.purchase_invoicing_trigger = 'picking'
#         elif self.purchase_invoiced_on == 'order' and self.property_supplier_payment_term_id.payment_type != 'after_invoicing' and self.purchase_invoicing_trigger != 'manual':
#             self.purchase_invoicing_trigger = 'postpaid'
#     
#     
#     @api.onchange('purchase_invoicing_trigger')
#     def _onchange_purchase_invoicing_trigger(self):
#         """
#             Si on passe le mode de déclenchement en manuel ou à la commande, on sélectionne la facturation sur 
#             quantités livrées
#         """
#         if self.purchase_invoicing_trigger in ['manual','postpaid']:
#             self.purchase_invoiced_on = 'order'
#         elif self.purchase_invoicing_trigger == 'picking' and self.property_supplier_payment_term_id.payment_type != 'after_invoicing':
#             self.purchase_invoiced_on = 'delivery'
    
    
#     @api.one
#     @api.constrains('property_supplier_payment_term_id', 'purchase_invoicing_trigger', 'purchase_invoiced_on')    
#     def _check_purchase_invoiced_on(self):
#         """
#             Verifie :
#               -que le mode de déclenchement soit 'A la livraison' si la facturation est sur les quantités livrées
#               -que la facturation est sur les quantités commandées si la condition de paiement est "Avant livraison"
#               -que la méthode de déclenchement est manuelle si la condition de paiement est "Paiement immédiat" ou 
#                   si elle a la case "Bloquer la commande avant validation" de cochée
#               -que la méthode de déclenchement est manuelle ou à la commande si la condition de paiement a la case
#                   "Bloquer la commande avant livraison" de cochée
#         """
#         if self.is_company:
#             if self.purchase_invoiced_on == 'delivery' and self.purchase_invoicing_trigger != 'picking':
#                 raise Warning(_('Error ! You cannot have an invoice in the delivery if the purchase trigger is not in'
#                                 ' the picking (purchase tab)'))
#             
#             elif self.purchase_invoiced_on == 'order':
#                 if self.property_supplier_payment_term_id.payment_type in ['before_validation', 'before_delivery'] and self.purchase_invoicing_trigger not in ['postpaid', 'manual']:
#                     raise Warning(_('Error ! You cannot have an invoice in the ordered quantities if the invoice trigger is not in the order or manual'))
                
    
    @api.one
    @api.constrains('partial_purchase_delivery', 'generate_purchase_rest')    
    def _check_partial_purchase_delivery(self):
        """
            Verifie que le booléen de génération de reliquat soit bien décoché si celui
            de livraison incomplète l'es aussi 
        """
        if self.is_company and not self.partial_purchase_delivery and self.generate_purchase_rest:
            raise Warning(_('Error ! You cannot generate rest if you don\'t accept partial delivery (in the purchase tab)'))
            
        return True
    
    
    def get_partner_address(self, infos={}, return_id=False):
        """
            Fonction qui ramène toutes les adresses et les fournisseurs
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
        #On vérifie avant tout que le partenaire soit bien un fournisseur
        partner = self
        if partner:
            principal_address = res.get('order_address') or (return_id and partner.address_id.id or partner.address_id)
            principal_customer = return_id and partner.id or partner
            if partner.is_company and partner.is_supplier:
                #On commence par récupérer l'adresse principale du partenaire
                #On regarde ensuite si le partenaire peut être livreur. Si c'est le cas, 
                #on renvoie son adresse principale et l'id du partner
                if infos.get('purchase_delivery'):
                    if partner.delivered_by:
                        res['purchase_delivery_address'] = principal_address
                        res['purchase_delivery_partner'] = principal_customer
                    #Sinon, on recherche et récupère le partner livreur, ainsi que
                    #son adresse principale.
                    else:
                        for line in partner.purchase_type_ids:
                            if line.partner_type == 'delivered_by':
                                res['purchase_delivery_partner'] = return_id and line.partner_type_id.id or line.partner_type_id
                                res['purchase_delivery_address'] = return_id and line.partner_type_id.address_id.id or line.partner_type_id.address_id
                                break
                
                #On regarde ensuite si le partenaire peut facturer. Si c'est le cas, 
                #on renvoie son adresse principale et l'id du partner
                if infos.get('purchase_invoiced'):
                    if partner.invoiced_by:
                        res['purchase_invoiced_address'] = principal_address
                        res['purchase_invoiced_partner'] = principal_customer
                    #Sinon, on recherche et récupère le partenaire factureur, ainsi que
                    #son adresse principale.
                    else:
                        for line in partner.purchase_type_ids:
                            if line.partner_type == 'invoiced_by':
                                res['purchase_invoiced_partner'] = return_id and line.partner_type_id.id or line.partner_type_id
                                res['purchase_invoiced_address'] = return_id and line.partner_type_id.address_id.id or line.partner_type_id.address_id
                                break
                        
                #On regarde enfin si le partenaire peut être payeé. Si c'est le cas, 
                #on renvoie son id. Sinon, on recherche et récupère le partenaire payé
                if infos.get('purchase_paid'):
                    if partner.paid_to:
                        res['purchase_pay_partner'] = principal_customer
                    else:
                        for line in partner.purchase_type_ids:
                            if line.partner_type == 'paid_to':
                                res['purchase_pay_partner'] = return_id and line.partner_type_id.id or line.partner_type_id
                                break
            
        return res
    
    
    @api.multi
    def show_partner_purchase(self):
        """
            Fonction qui cherche et retourne les achats du partenaire
        """
        action_struc = {}
        action_dict = get_form_view(self, 'purchase.action_see_all_purchase_order')
        if action_dict and action_dict.get('id') and action_dict.get('type'):
            action = self.env[action_dict['type']].browse(action_dict['id'])
            action_struc = action.read()
            action_struc[0]['context'] = {'partner_id': self.id}
            action_struc = action_struc[0]
              
        return action_struc
    
    
    def get_purchase_transport_fields(self, return_id=False):
        if self:
            res = {
               'purchase_incoterm_id': return_id and self.purchase_incoterm_id.id or self.purchase_incoterm_id,
               'purchase_invoice_postage': self.purchase_invoice_postage,
               'purchase_threshold': self.purchase_threshold,
               'purchase_forwarding_agent_id': return_id and self.purchase_forwarding_agent_id.id or self.purchase_forwarding_agent_id,
                   }
        else:
            res = {
               'purchase_incoterm_id': False,
               'purchase_invoice_postage': False,
               'purchase_threshold': False,
               'purchase_forwarding_agent_id': False,
                   }
            
        return res
    
     
    def compute_domain_args_purchase(self, args):
        """
            Fonction appelée par le search afin de n'afficher que les contacts inscrits dans la liste de contact,
            et pour récupérer uniquement les payé à et les facturé par d'un fournisseur
        """
        args2 = []
        for arg in args:
            match = False
            if isinstance(arg, str) or (isinstance(arg, list) and arg[0] in ('!', '|', '&')):
                args2.append(arg)
                continue
             
            if arg[0] == 'contact_in_partner_purchase':
                arg[0] = 'id'
                arg[-1] = [x[1] for x in arg[-1] if x[0] != 2]
            elif arg[0] == 'partner_contact_purchase_order':
                arg[0] = 'id'
                arg[1] = 'in'
                partner_id = arg[-1]
                arg[-1] = []
                for contact in self.browse(partner_id).contact_ids:
                    arg[-1].append(contact.id)
                     
            elif arg[0] == 'purchase_order_domain':
                if isinstance(arg[-1], list) and arg[-1][0]:
                    arg = ('id', '=', arg[-1][1])
                else:
                    match = True
                    args2 += [('is_supplier', '=', True)]
            
            #On affiche les partenaires payeurs qui sont dans la liste du partenaire passé dans le domaine
            elif arg[0] in ['invoiced_supplier_in_order_list', 'paid_supplier_in_order_list', 'delivered_supplier_in_order_list']:
                dict_value = {'invoiced_supplier_in_order_list': 'invoiced_by',
                              'paid_supplier_in_order_list': 'paid_to',
                              'delivered_supplier_in_order_list': 'delivered_by'}
                search_args = [('partner_type', '=', dict_value.get(arg[0], False)), ('partner_id', '=', arg[-1])]
                arg[0] = 'id'
                arg[1] = 'in'
                arg[-1] = [x.partner_type_id.id for x in self.env['res.partner.purchase.type'].search(search_args) if x.partner_type_id]
            
            elif arg[0] == 'order_supplier_in_invoiced_list':
                arg[0] = 'id'
                arg[1] = 'in'
                arg[-1] = [x.partner_id.id for x in self.env['res.partner.purchase.type'].search([('partner_type', '=', 'invoiced_by'), 
                                                                                         ('partner_type_id', '=', arg[-1])]) if x.partner_id]
             
            if not match:
                args2.append(arg)
             
        return args2
 
    @api.model
    def search(self,args=None, offset=0, limit=None, order=None, count=None):
        """
            Modification du search afin de n'afficher que les contacts inscrits dans la liste de contact
            et récupérer uniquement les 'payé à' et les 'facturé par' d'un fournisseur
        """
        args = args or []
        args_modified = self.compute_domain_args_purchase(args)
        return super(res_partner,self).search(args=args_modified, offset=offset, limit=limit, order=order, count=count)
     
     
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False,lazy=True):
        domain = self.compute_domain_args_purchase(domain)
        return super(res_partner, self).read_group(domain=domain, fields=fields, groupby=groupby, offset=offset, limit=limit, orderby=orderby,lazy=lazy)
    
    
    def modification_gergonne(self, delivered_vals):
        """
            Fonction pour gergonne, sachant que la position fiscale d'achat est un related de celle de la vente, 
            on remplit le champ position fiscale de la vente par celle dû  fournisseur qui peut livré 
        """
        return delivered_vals
    
    
    def purchase_modif_value_partner_type(self, modif_field):
        """"
            Mise à jour des champs dans les partenaires, selon les informations rentrées dans res.partner.type
            :param modif_field: Liste pour savoir quoi modifier: invoiced_by, delivered_by, paid_to, purchase_type_ids
            :type modif_field: char           
        """
        res = super(res_partner, self).purchase_modif_value_partner_type(modif_field=modif_field)  
        if modif_field == 'paid_to' and self.paid_to:
            request = """Select
                            partner_type_val.partner_id
                        From
                            (Select
                        
                                partner_id,
                                id
                            From
                                res_partner_purchase_type
                            Where
                                partner_type_id =  %s and
                                partner_type = 'paid_to') partner_type_val,
                            res_partner
                        Where
                            (res_partner.paid_to is null or res_partner.paid_to = false) and
                            partner_type_val.partner_id = res_partner.id and
                            partner_type_val.id = (Select id 
                                                   From res_partner_purchase_type 
                                                   Where partner_type = 'paid_to' and 
                                                         partner_id = partner_type_val.partner_id 
                                                   order by sequence asc limit 1) """%(self.id)
            self.env.cr.execute(request)
            res_sql = self.env.cr.fetchall()  
            if res_sql:
                partner_ids = [x[0] for x in res_sql]
                paid_vals = {}
                for x in self.purchase_paid_fields_partner():
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
        
        elif modif_field == 'delivered_by' and self.delivered_by:
            request = """Select
                            partner_type_val.partner_id
                        From
                            (Select
                        
                                partner_id,
                                id
                            From
                                res_partner_purchase_type
                            Where
                                partner_type_id =  %s and
                                partner_type = 'delivered_by') partner_type_val,
                            res_partner
                        Where
                            (res_partner.delivered_by is null or res_partner.delivered_by = false) and
                            partner_type_val.partner_id = res_partner.id and
                            partner_type_val.id = (Select id 
                                                   From res_partner_purchase_type 
                                                   Where partner_type = 'delivered_by' and 
                                                         partner_id = partner_type_val.partner_id 
                                                   order by sequence asc limit 1) """%(self.id)
            self.env.cr.execute(request)
            res_sql = self.env.cr.fetchall()  
            if res_sql:
                partner_ids = [x[0] for x in res_sql]
                delivered_vals = {}
                for x in self.purchase_delivered_fields_partner():
                    if type(self[x]) is not int and type(self[x]) is not str and type(self[x]) is not float and type(self[x]) is not bool and type(self[x]) is not unicode and self[x] != None: 
                        if isinstance((self._fields[x]), fields.Many2many) or isinstance((self._fields[x]), fields.One2many):
                            delivered_vals[x] = []
                            for i in self[x].ids:
                                delivered_vals[x].append((4, i))
                        else:
                            delivered_vals[x] = self[x].id
                    else:
                        delivered_vals[x] = self[x]
                
                delivered_vals = self.modification_gergonne(delivered_vals)
                self.browse(partner_ids).write(delivered_vals)

        elif modif_field == 'invoiced_by' and self.invoiced_by:
            request = """Select
                            partner_type_val.partner_id
                        From
                            (Select
                        
                                partner_id,
                                id
                            From
                                res_partner_purchase_type
                            Where
                                partner_type_id =  %s and
                                partner_type = 'invoiced_by') partner_type_val,
                            res_partner
                        Where
                            (res_partner.invoiced_by is null or res_partner.invoiced_by = false) and
                            partner_type_val.partner_id = res_partner.id and
                            partner_type_val.id = (Select id 
                                                   From res_partner_purchase_type 
                                                   Where partner_type = 'invoiced_by' and 
                                                         partner_id = partner_type_val.partner_id 
                                                   order by sequence asc limit 1) """%(self.id)
            self.env.cr.execute(request)
            res_sql = self.env.cr.fetchall()  
            if res_sql:
                partner_ids = [x[0] for x in res_sql]
                invoiced_vals = {}
                for x in self.purchase_invoiced_fields_partner():
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

        elif modif_field == 'purchase_type_ids':
            partner_type_obj = self.env['res.partner.purchase.type']
            if not self.paid_to:
                partner_type_rcs = partner_type_obj.search([('partner_type', '=', 'paid_to'), ('partner_id', '=', self.id)], order='sequence asc', limit=1)
                if partner_type_rcs:
                    paid_vals = {}
                    for x in self.purchase_paid_fields_partner():
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
            
            if not self.delivered_by:
                partner_type_rcs = partner_type_obj.search([('partner_type', '=', 'delivered_by'), ('partner_id', '=', self.id)], order='sequence asc', limit=1)
                if partner_type_rcs:
                    delivered_vals = {}
                    for x in self.purchase_delivered_fields_partner():
                        if type(partner_type_rcs.partner_type_id[x]) is not int and type(partner_type_rcs.partner_type_id[x]) is not str and type(partner_type_rcs.partner_type_id[x]) is not float and type(partner_type_rcs.partner_type_id[x]) is not bool and type(partner_type_rcs.partner_type_id[x]) is not unicode and partner_type_rcs.partner_type_id[x] != None: 
                            if isinstance((self._fields[x]), fields.Many2many) or isinstance((self._fields[x]), fields.One2many):
                                delivered_vals[x] = []
                                for i in partner_type_rcs.partner_type_id[x].ids:
                                    delivered_vals[x].append((4, i))
                            else:
                                delivered_vals[x] = partner_type_rcs.partner_type_id[x].id
                        else:
                            delivered_vals[x] = partner_type_rcs.partner_type_id[x]
                    
                    delivered_vals = partner_type_rcs.partner_type_id.modification_gergonne(delivered_vals)
                    self.write(delivered_vals)
            
            if not self.invoiced_by:
                partner_type_rcs = partner_type_obj.search([('partner_type', '=', 'invoiced_by'), ('partner_id', '=', self.id)], order='sequence asc', limit=1)
                if partner_type_rcs:
                    invoiced_vals = {}
                    for x in self.purchase_invoiced_fields_partner():
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