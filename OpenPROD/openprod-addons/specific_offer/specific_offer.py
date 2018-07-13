# coding: utf-8

from openerp import fields, models, api
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp.addons.base_openprod.common import roundingUp
from openerp.addons.base_openprod.common import get_form_view
from openerp.exceptions import Warning

class specific_offer_qty(models.Model):
    """ 
        List of price and quantity for specific offer
    """
    _name = 'specific.offer.qty'
    _rec_name = 'specific_offer_id'
    _description = 'List of price and quantity for specific offer'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    quantity = fields.Float(string='Quantity', default=0.0, required=False)
    price = fields.Float(string='Price', default=0.0, required=False)
    specific_offer_id = fields.Many2one('specific.offer', string='Specific offer', required=False, ondelete='restrict')
    
    
    
class specific_offer(models.Model):
    """ 
    specific offer 
    """
    _name = 'specific.offer'
    _description = 'specific offer'
    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('simulated', _('Simulated')),
                ('sent', _('Sent')),
                ('validated', _('Validated')),
                ('cancelled', _('Cancelled')),
                       ]
    
    @api.one
    def _compute_mail(self):
        self.mail_ids = self.env['mail.mail'].search([('model', '=', 'specific.offer'), ('res_id', '=', self.id)]).ids
        
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    sequence = fields.Char(required=True, default='/', copy=False)
    name = fields.Char(required=True)
    state = fields.Selection('_state_get', string='State', default="draft", copy=False)
    partner_id = fields.Many2one('res.partner', required=False, string='Partner', domain=[('is_customer', '=', True), ('can_order', '=', True)])
    model_id = fields.Many2one('product.product', string='Model', required=False, ondelete='cascade', domain=[('supply_method', '=', 'produce')])
    quantity = fields.Float(string='Quantity', digits=dp.get_precision('Product quantity'), default=1.0, required=True)
    responsible_id = fields.Many2one('res.users', string='Responsible', required=False, ondelete='restrict', default=lambda self:self.env.user)
    description = fields.Text()
    option_ids = fields.One2many('specific.offer.option', 'specific_offer_id',  string='Options')
    total_price = fields.Float(string='Total price', default=0.0, digits=dp.get_precision('Account'), required=False)
    unit_price = fields.Float(string='Unit price', default=0.0, digits=dp.get_precision('Account'), required=False)
    proposition_date = fields.Datetime(string='Proposition date')
    simulation_line_ids = fields.One2many('simulation.line', 'specific_offer_id',  string='Lines')
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='restrict')
    date_from = fields.Date(string='Date from')
    date_to = fields.Date(string='Date to')
    mail_ids = fields.One2many('mail.mail', string='Mails', compute='_compute_mail', readonly=True)
    qty_ids = fields.One2many('specific.offer.qty', 'specific_offer_id',  string='Price list')
    crm_id = fields.Many2one('crm', string='CRM', required=False, ondelete='restrict')
    start_date_simulation = fields.Date(string='From', default=lambda self: fields.Date.today())
    end_date_simulation = fields.Date(string='To')
    price_rm = fields.Float()
    price_labour = fields.Float()
    
    @api.model
    def create(self, vals):
        """
            Sequence creation Ex: SIM12145
        """
        if 'sequence' not in vals or vals.get('sequence') == '/':
            vals['sequence'] = self.env['ir.sequence'].get('specific.offer')

        return super(specific_offer, self).create(vals=vals)
    
    @api.multi
    def simulate(self):
        bom_obj = self.env['mrp.bom']
        option_ids = self.env['mrp.option'].browse([x.option_id.id for x in self.option_ids])
        bom_id = bom_obj._bom_find(self.model_id.id, self.model_id.uom_id, option_ids)
        if not (bom_id and bom_id.routing_ids[0]):
            raise Warning(_('BoM and routing not found'))
        for line in self.simulation_line_ids:
            line.unlink()
        vals = self.get_all_lines(option_ids)
        total_price = sum([x['total_price'] for x in vals])
        unit_price = total_price / self.quantity
        vals = {
                    'simulation_line_ids':[(0, 0, x) for x in vals],
                    'total_price':total_price,
                    'unit_price':unit_price,
                    'end_date_simulation':vals[0]['availability_date'],
                    'price_rm': sum([x['total_price'] for x in vals if x['supply_method'] == 'buy']),
                    'price_labour': sum([x['total_price'] for x in vals if x['supply_method'] == 'produce']),
                    }
        if self.state == 'draft':
            vals['state'] = 'simulated'
        self.write(vals)
        self.compute_critical_path()
    
    def get_all_lines(self, option_ids):
        return self.get_lines(self.model_id, [], option_ids, 1, self.quantity, self.start_date_simulation)
    
    def get_lines(self, product_id, value_ids, option_ids, level, qty, start_date):
        bom_obj = self.env['mrp.bom']
        wo_obj = self.env['mrp.workorder']
        if product_id:
            bom_id = bom_obj._bom_find(product_id.id, product_id.uom_id, option_ids)
            if bom_id:
                routing = bom_id.routing_ids[0]
                option_id = bom_id.option_id.id
                product_id = wo_obj._get_product(bom_id, value_ids, product_id)
            else:
                routing = None
                option_id = None
                product_id = wo_obj._get_product(None, value_ids, product_id)
            
            if product_id.supply_method == 'produce' and routing:
                pricetime = routing.function_compute_price(serie_eco=qty, option_ids=option_ids.ids)
                unit_price = pricetime[0]
                delay = pricetime[2] / self.env['calendar'].get_avg_hours()
            elif product_id.supply_method == 'buy':
                delay = product_id.get_default_supply_delay_purchase()
                unit_price = bom_obj.compute_price_component_buy(product_id, qty, product_id.uom_id, self.env.user.company_id.currency_id)
            else:
                unit_price = 0
                delay = 0
            
            
            vals = [{
                     'name': product_id.name,
                     'bom_id':bom_id.id if bom_id else None,
                     'product_id':product_id.id,
                     'level':level,
                     'supply_method':product_id.supply_method,
                     'quantity': qty,
                     'stock_qty': product_id.virtual_stock,
                     'option_id':option_id,
                     'routing_id': routing.id if routing else None,
                     'unit_price': unit_price,
                     'total_price': unit_price * qty,
                     'delay': delay,
                     'supplier_id': product_id.sinfo_ids and product_id.sinfo_ids[0].partner_id.id,
                     }]
            max_delay = 0
            new_start_date = start_date
            if bom_id:
                for bom in wo_obj._get_list_bom_consommed(bom_id, option_ids):
                    bom_qty = self.get_bom_qty(bom, qty)
                    child_vals = self.get_lines(bom.product_id, value_ids, option_ids, level + 1, bom_qty, start_date)
                    new_start_date = max(new_start_date, child_vals[0]['availability_date'])
                    vals += child_vals
                    max_delay = max(max_delay, child_vals[0]['cumulative_delay'])
            availability_date = product_id.simulate_availability(qty, None, self.option_ids, new_start_date)
            vals[0]['availability_date'] = availability_date

            vals[0]['cumulative_delay'] = delay + max_delay
            return vals
        else:
            return []
    
    def get_bom_qty(self, bom, qty):
        if bom.type_component == 'formula':
            return roundingUp(bom.compute_qty_formula(bom.formula_component, bom.quantity, bom.efficiency, qty*bom.quantity, qty, [('specific_offer_id', '=', self.id)]), bom.round)
        elif bom.type_component == 'variable':
            return roundingUp(bom.quantity * qty / (bom.efficiency if bom.efficiency else 1), bom.round)
        else:
            return roundingUp(bom.quantity / (bom.efficiency if bom.efficiency else 1), bom.round)
        
    
    @api.multi
    def create_update_cust_ref(self):
        """
            Fonction qui permet de créer ou de mettre à jour le référencement client 
            de ce produit pour le partenaire sélectionné
        """
        cust_obj = self.env['product.customerinfo']
        for offer in self:
            if offer.partner_id and offer.product_id:
                #On recherche le référencement client actif liés au produit et au partenaire et qui n'a pas 
                #de propriétés
                custinfo = cust_obj.search([('partner_id', '=', offer.partner_id.id), 
                                 ('product_id', '=', offer.product_id.id),
                                 ('state', '=', 'active'), ('property_ids', '=', False)], limit=1)
                #On va effacer l'éventuelle liste de prix du référencement trouvé et on va créer la nouvelle
                if custinfo:
                    custinfo.write({'pricelist_ids': [(5, 0)]})
                    vals_price_line = []
                    vals_date = {'date_start': offer.date_from, 'date_stop': offer.date_to}
                    for qty_line in offer.qty_ids:
                        price_line = {}
                        price_line.update(vals_date)
                        price_line.update({'min_qty': qty_line.quantity, 
                                           'price': qty_line.price})
                        vals_price_line.append([0, 0, price_line])
                        
                    custinfo.write({'pricelist_ids': vals_price_line})
                else:
                    raise Warning(_('There is no customer referencing for this product and this customer'))
                            
            return True
        
        
    @api.multi
    def create_specific_product(self):
        """
            Fonction qui permet de créer un produit à partir de l'offre spécifique
        """
        cust_obj = self.env['product.customerinfo']
        for offer in self:
            if not offer.product_id and offer.model_id:
                model = offer.model_id
                #On copie le produit depuis le modèle en lui donnant le nom
                #de l'offre
                partner = offer.partner_id
                default = {'name': offer.name}
                if partner:
                    default['free_sale'] = False
                    
                context2 = {'copy_by_button': True}
                context2.update(self.env.context)
                new_product = model.with_context(context2).copy(default)
                if new_product:
                    offer.write({'product_id': new_product.id})
                    #On copie les documents imprimés, les règles de stock et les plans de
                    #contrôle pour le nouveau produit
                    default2 = {'product_id': new_product.id}
                    model.plan_control_ids.copy(default2)
                    model.orderpoint_ids.copy(default2)
                    model.quality_control_ids.copy(default2)
                    #Si l'offre a un partenaire, on crée le référencement associé en prenant en compte les
                    #lignes de prix
                    if partner:
                        vals_price_line = []
                        vals_date = {'date_start': offer.date_from, 'date_stop': offer.date_to}
                        for qty_line in offer.qty_ids:
                            price_line = {}
                            price_line.update(vals_date)
                            price_line.update({'min_qty': qty_line.quantity, 
                                               'price': qty_line.price})
                            vals_price_line.append([0, 0, price_line])
                        
                        vals = {'partner_id': partner.id,
                                'currency_id': partner.currency_id.id,
                                'product_id': new_product.id,
                                'uos_id': new_product.uom_id.id,
                                'uoi_id': new_product.uom_id.id,
                                'pricelist_ids': vals_price_line,
                                'company_id': new_product.company_id.id}
                        cust_obj.create(vals)
                        
                    
            return True
        
    
    def add_product_line_values(self, offer):
        """
            Fonction servant à ajouter des valeurs éventuelles à la ligne de vente
        """
        values = {}
        return values
        
        
    @api.multi
    def action_send_mail(self):
        return self.env['mail.message'].action_send_mail(self.partner_id, 'specific.offer', '',self.id)
    
    
    @api.multi
    def create_new_sale(self):
        """
            Fonction qui permet de vérifier si le produit est actif et a un référencement client
            qui correspond au client de l'offre et qui envoie le wizard de création d evente
        """
        customerinfo_obj = self.env['product.customerinfo']
        for offer in self:
            product_rs = offer.product_id
            partner_rs = offer.partner_id
            if product_rs and partner_rs:
                #On recherche un référencement client correspondant au produit et au client de l'offre
                customer_ref = customerinfo_obj.search([('partner_id', '=', partner_rs.id), 
                                                        ('product_id', '=', product_rs.id), 
                                                        ('state', '=', 'active')], limit=1)
                if not product_rs.state in ['lifeserie', 'endlife'] or not customer_ref:
                    raise Warning(_('To create a sale, your product must be in life or end of life, and he must have '
                                  'an active customer referencing with the customer of the offer'))
                else:
                    action_dict = get_form_view(self, 'specific_offer.action_create_sale_from_offer')
                    if action_dict and action_dict.get('id') and action_dict.get('type'):
                        action = self.env[action_dict['type']].browse(action_dict['id'])
                        action_struc = action.read()[0]
                        return action_struc
            else:
                return {'type': 'ir.actions.act_window_close'}
    
    @api.one
    def compute_critical_path(self):
        self.simulation_line_ids.write({'critical_path':False})
        crit = self.simulation_line_ids[0]
        pos = 1
        cont = True
        while cont and len(self.simulation_line_ids) > pos + 1:
            crit.critical_path = True
            new_crit = self.simulation_line_ids[pos+1]
            next_pos = -1
            # trouve la bonne ligne
            for i, line in enumerate(self.simulation_line_ids[pos+1:]):
                if line.level == crit.level:
                    break
                elif line.level == crit.level + 1 and line.availability_date > new_crit.availability_date:
                    new_crit = line
                    next_pos = i
                else:
                    continue
            # marque la ligne trouvée précédemment comme critique
            for i, line in enumerate(self.simulation_line_ids[pos+1:]):
                if line.level == crit.level:
                    break
                elif line.level == crit.level + 1 and line.availability_date == new_crit.availability_date:
                    line.critical_path = True
                else:
                    continue
            if next_pos == -1:
                cont = False
            crit = new_crit
            pos = pos + next_pos + 1
    
    
    
class simulation_line(models.Model):
    """ 
    Simulation line 
    """
    _name = 'simulation.line'
    _description = 'Simulation line'
    
    def _supply_method_get(self):
        return [
            ('buy', _('Buy')),
            ('produce', _('Produce')),
               ]
    
    @api.depends('level')
    def _compute_name(self):
        for rec in self:
            rec.name = '----' * (rec.level - 1) + rec.product_id.name
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(compute='_compute_name', string='Name')
    specific_offer_id = fields.Many2one('specific.offer', string='Specific offer', required=True, ondelete='cascade')
    bom_id = fields.Many2one('mrp.bom', string='BoM', required=False, ondelete='cascade')
    product_id = fields.Many2one('product.product')
    level = fields.Integer(string='Level', default=1, required=True)
    supply_method = fields.Selection('_supply_method_get', string='Supply method', required=True, default='buy')
    quantity = fields.Float(string='Quantity', digits=dp.get_precision('Product quantity'), default=1.0, required=True)
    option_id = fields.Many2one('mrp.option', string='Options', delete='cascade')
    routing_id = fields.Many2one('mrp.routing', string='Routing', required=False, ondelete='cascade')
    delay = fields.Integer(string='Delay')
    cumulative_delay = fields.Integer('Cumulative delay')
    unit_price = fields.Float(string='Unit price', default=0.0, digits=dp.get_precision('Account'), required=False)
    total_price = fields.Float(string='Total price', default=0.0, digits=dp.get_precision('Account'), required=False)
    stock_qty = fields.Float(string='Stock Qty', default=0.0, required=False)
    availability_date = fields.Date(string='Availability date')
    supplier_id = fields.Many2one('res.partner', string='Supplier', required=False, domain="[('is_supplier', '=', True)]", ondelete='restrict')
    critical_path = fields.Boolean(string='Critical Path', default=False)
    
    @api.onchange('supplier_id')
    def _onchange_supplier_id(self):
        bom_obj = self.env['mrp.bom']
        if self.supplier_id and self.supply_method == 'buy':
            currency = self.env.user.company_id.currency_id
            sinfo_brw = self.env['product.supplierinfo'].search([('product_id', '=', self.product_id.id), ('partner_id', '=', self.supplier_id.id)])
            self.delay = sinfo_brw and sinfo_brw.delivery_delay or self.supplier_id.sale_delivery_delay
            self.unit_price = bom_obj.compute_price_component_buy(self.product_id, self.quantity, self.product_id.uom_id, currency, self.supplier_id, sinfo_brw)
            self.total_price = self.unit_price * self.quantity
        else:
            self.delay = self.product_id.get_default_supply_delay_purchase()
            self.unit_price = self.routing_id.function_compute_price(serie_eco=self.quantity, option_ids=self.specific_offer_id.option_ids.ids)
        flag = False
        start_date = self.specific_offer_id.start_date_simulation
        for line in self.specific_offer_id.simulation_line_ids:
            if not flag:
                if line == self:
                    flag = True
            elif line.level > self.level:
                start_date = max(line.availability_date, start_date)
            else:
                break
        self.availability_date = self.product_id.simulate_availability(self.quantity, self.supplier_id, self.specific_offer_id.option_ids, start_date)
    
    def update_parents(self):
        lines = self.specific_offer_id.simulation_line_ids.sorted(None, reverse=True)
        for line in lines:
            line.cumulative_delay = line.delay
            line.availability_date = line.product_id.simulate_availability(line.quantity, line.supplier_id, self.specific_offer_id.option_ids, line.specific_offer_id.start_date_simulation)
        for i, line in enumerate(lines):
            for parent in lines[i:]:
                if parent.level + 1 == line.level:
                    break
            else:
                return
            if parent.cumulative_delay < line.cumulative_delay + parent.delay:
                parent.cumulative_delay = line.cumulative_delay + parent.delay
                new_date = max(line.availability_date, line.specific_offer_id.start_date_simulation)
                parent.availability_date = parent.product_id.simulate_availability(parent.quantity, parent.supplier_id, self.specific_offer_id.option_ids, new_date)


class mail_compose_message(models.TransientModel):
    _inherit = 'mail.compose.message'
    
    @api.multi
    def send_mail(self):
        """
            Surcharge de la fonction d'envoi du mail. On passe l'offre en "envoyé"
        """
        if self.model == 'specific.offer' and self.id_active:
            offer = self.env['specific.offer'].browse(self.id_active)
            if offer.state not in ('sent', 'validated', 'cancelled'):
                offer.write({'state': 'sent'})
                
        context2 = self.env.context.copy()
        context2['thread_model'] = 'specific.offer'
        return super(mail_compose_message, self.with_context(context2)).send_mail()
    
    
    @api.model
    def get_mail_values(self, res_ids):
        """
            Surcharge de la fonction de création du mail afin de lier le mail à l'offre spécifique
        """
        results = super(mail_compose_message, self).get_mail_values(res_ids)
        if self.env.context and self.env.context.get('model_objet', '') == 'specific.offer':
            for res_id in res_ids:
                results[res_id]['model'] = 'specific.offer'
                results[res_id]['res_id'] = res_id
            
        return results

class specific_offer_option(models.Model):
    """ 
    Specific offer option 
    """
    _name = 'specific.offer.option'
    _description = 'Specific offer option'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    specific_offer_id = fields.Many2one('specific.offer', string='Specific offer', required=True, ondelete='cascade')
    option_id = fields.Many2one('mrp.option', string='Option', required=True, ondelete='cascade')
    price_unit = fields.Float(string='Price unit', default=0.0, digits=dp.get_precision('Product price'))
    
    @api.onchange('option_id')
    def _onchange_option_id(self):
        self.price_unit = self.option_id.price_unit
    