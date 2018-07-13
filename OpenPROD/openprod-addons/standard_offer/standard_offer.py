# coding:utf-8
'''
Created on 3 juin 2015

@author: sylvain
'''

from openerp import models, fields, api
from openerp.tools.translate import _


class standard_offer_line(models.Model):
    """ 
    Standard offer line 
    """
    _name = 'standard.offer.line'
    _description = 'Standard offer line'

    @api.model
    def _type_get(self):
        return [('product', _('Product')), ('category', _('Category')), ]

    @api.model
    def _discount_type_get(self):
        return [('discount', _('Discount')), ('increase', _('Increase')), ('net_price', _('Net price')), ('base_price', _('Base price')), ]

    @api.model
    def _mode_get(self):
        return [('value', _('Value')), ('percent', _('Percent')), ]

    @api.model
    def _state_get(self):
        return [('new', _('New')), ('old', _('Old')), ]

    @api.one
    @api.depends('discount_type')
    def _compute_mode(self):
        if self.discount_type in ['discount', 'increase']:
            self.mode = 'percent'
        else:
            self.mode = 'value'

    #===========================================================================
    # COLUMNS
    #===========================================================================
    offer_id = fields.Many2one('standard.offer', string='Parent offer', ondelete='cascade', select=True)
    type = fields.Selection('_type_get', string='Rule type', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='restrict')
    category_id = fields.Many2one('sale.family', string='Category', required=False, ondelete='restrict')
    quantity = fields.Integer(string='Quantity', default=0, required=False)
    uoi_id = fields.Many2one(related="product_id.sale_uoi_id", readonly=True)
    uos_id = fields.Many2one(related='product_id.uos_id', readonly=True)
    discount_type = fields.Selection('_discount_type_get', string='Discount type', required=True)
    mode = fields.Char(string='Mode', compute='_compute_mode')
    value = fields.Float(string='Value', default=0.0, required=False)
    state = fields.Selection('_state_get', string='State', default="new")
    customer_id = fields.Many2one('res.partner', related="offer_id.customer_id")
    currency_id = fields.Many2one('res.currency', related="offer_id.currency_id")

    _sql_constraints = [
        ('unique_product', 'unique(offer_id, product_id, quantity)', _("You can't have the same product and quantity twice.")),
        ('unique_category', 'unique(offer_id, category_id, quantity)', _("You can't have the same category and quantity twice.")),
    ]

    def copy_data(self, cr, uid, id, default=None, context=None):
        if context is None:
            context = {}

        if default is None:
            default = {}

        default["state"] = "old"

        return super(standard_offer_line, self).copy_data(cr, uid, id, default=default, context=context)
    
    @api.onchange('type')
    def _onchange_type(self):
        if self.type == 'product':
            self.category_id = None
        else:
            self.product_id = None


class standard_offer(models.Model):
    """ 
    Standard offer 
    """
    _name = 'standard.offer'
    _description = 'Standard offer'

    @api.one
    @api.constrains('state')
    def _check_overlap(self):
        """
            Check si il n'y a pas deux offres applicables pour le même client ayant des jours en commun
        """
        if self.type == "customer":
            previous_offer = self.search([
                ("type", "=", "customer"),
                ("customer_id", "=", self.customer_id.id),
                ("state", "=", "applicable"),
                ("currency_id", "=", self.currency_id.id),
                '|',
            ] + between_dates(self.start_date) + between_dates(self.end_date))
            if len(previous_offer) > 1:
                raise Warning(_('There is already an applicable offer for that customer on that period.'))
        elif self.type == "standard":
            previous_offer = self.search([
                ("type", "=", "standard"),
                ("category_id", "=", self.category_id.id),
                ("state", "=", "applicable"),
                ("currency_id", "=", self.currency_id.id),
                '|',
            ] + between_dates(self.start_date) + between_dates(self.end_date))
            if len(previous_offer) > 1:
                raise Warning(_('There is already an applicable standard offer for that category on that period.'))
        elif self.type == "family":
            previous_offer = self.search([
                ("type", "=", "family"),
                ("family_id", "=", self.family_id.id),
                ("state", "=", "applicable"),
                ("currency_id", "=", self.currency_id.id),
                '|',
            ] + between_dates(self.start_date) + between_dates(self.end_date))
            if len(previous_offer) > 1:
                raise Warning(_('There is already an applicable offer for that family on that period.'))

    @api.one
    @api.constrains('type', 'rule_ids')
    def _check_discount_type(self):
        """
            Restreint les prix nets aux offres "client" et les prix de base aux offres "standard"
        """
        for rule in self.rule_ids:
            if self.type in ("customer", "family") and rule.discount_type == "base_price":
                raise Warning(_('Base price only for standard offer.'))
            if self.type == "standard" and rule.discount_type != "base_price":
                raise Warning(_('Only base price is possible for standard offer'))

    @api.model
    def _type_get(self):
        return [('standard', _('Standard')), ('customer', _('Customer')), ('family', _('Family')), ]

    @api.model
    def _state_get(self):
        return [('draft', _('Draft')), ('sent', _('Sent')), ('applicable', _('Applicable')), ('obsolete', _('Obsolete')), ]

    def _get_states(self):
        return {'sent': [('readonly', True)], 'applicable': [('readonly', True)]}
    
#     @api.one
#     @api.depends('currency_manual_id', 'type')
#     def _compute_currency(self):
#         if type == 'standard':
#             currency_id = self.env.user.company_id.currency_id.id
#         else:
#             currency_id = self.currency_manual_id and self.currency_manual_id.id or self.env.user.company_id.currency_id.id
#         
#         self.currency_id = currency_id
        
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True, default='/', states=_get_states, copy=False)
    start_date = fields.Date(string='Start date', states=_get_states, select=True)
    end_date = fields.Date(string='End date', states=_get_states, select=True)
    type = fields.Selection('_type_get', string='Tariff type', states=_get_states, required=True)
    comment = fields.Text(string='Comment', states=_get_states)
    state = fields.Selection('_state_get', string='Tariff state', default="draft", states=_get_states, copy=False)
    customer_id = fields.Many2one('res.partner', string='Customer', required=False, ondelete='restrict', states=_get_states)
    category_id = fields.Many2one('sale.family', string='Category', required=False, ondelete='restrict', states=_get_states)
    family_id = fields.Many2one('partner.stat.family', string='Family', required=False, ondelete='restrict', states=_get_states, domain=[("is_sale", '=', True)], context={'default_is_sale': True})
    rule_ids = fields.One2many('standard.offer.line', 'offer_id', string='Standard offer rules', states=_get_states, copy=True)
    sending_date = fields.Date(string='Sent on', states=_get_states, copy=False)
    sending_uid = fields.Many2one('res.users', string='User', required=False, ondelete='restrict', states=_get_states, copy=False)
    application_date = fields.Date(string='Applicated on', states=_get_states, copy=False)
    application_uid = fields.Many2one('res.users', string='User', required=False, ondelete='restrict', states=_get_states, copy=False)
    obsolescence_date = fields.Date(string='Obsoleted on', states=_get_states, copy=False)
    obsolescence_uid = fields.Many2one('res.users', string='User', required=False, ondelete='restrict', states=_get_states, copy=False)
    mail_ids = fields.One2many('mail.mail', 'res_id', string='Mails', states=_get_states, domain=[("model", "=", "standard.offer")], readonly=True)
    print_line_ids = fields.One2many('standard.offer.print.line', 'offer_id', string='Print Lines')
#     currency_id = fields.Many2one('res.currency', string='Currency', required=True)
#     currency_manual_id = fields.Many2one('res.currency', string='Currency', required=False, ondelete='restrict', default=lambda self: self.env.user.company_id.currency_id)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, ondelete='restrict', default=lambda self: self.env.user.company_id.currency_id)
    
    
    @api.model
    def create(self, vals):
        """
            Name creation Ex: OS12145
        """
        if 'name' not in vals or vals.get('name') == '/':
            vals['name'] = self.env['ir.sequence'].get('standard_offer.offer')

        return super(standard_offer, self).create(vals=vals)

    @api.multi
    def to_draft(self):
        self.write({
            "state": "draft",
            "sending_date": None,
            "sending_uid": None,
            "application_date": None,
            "application_uid": None,
            "obsolescence_date": None,
            "obsolescence_uid": None
        })

    @api.multi
    def to_sent(self):
        self.write({"state": "sent", "sending_date": fields.Date.today(), "sending_uid": self.env.user.id})

    @api.multi
    def to_applicable(self):
        self.write({"state": "applicable", "application_date": fields.Date.today(), "application_uid": self.env.user.id})

    @api.multi
    def to_obsolete(self):
        self.write({"state": "obsolete", "obsolescence_date": fields.Date.today(), "obsolescence_uid": self.env.user.id})

    @api.one
    def delete_print_lines(self):
        self.print_line_ids.unlink()

    @api.one
    def import_all_print_lines(self):
        """
            Crée des lignes dans l'onglet impression pour chaque règle de type produit
        """
        product_ids = []
        standard_offer_print_line_obj = self.env["standard.offer.print.line"]
        for rule in self.rule_ids:
            if rule.type == "product" and rule.state == "new":
                product_ids.append(rule.product_id)
        for product_id in set(product_ids):
            standard_offer_print_line_obj.create_print_lines(product_id, self)
        pass

    @api.multi
    def action_send_mail(self):
        return self.env['mail.message'].with_context(default_offer_id=self.id).action_send_mail(self.customer_id, 'standard.offer', '',
                                                                                                self.id)


class standard_offer_print_line(models.Model):
    """ 
        Pre calculated line
    """
    _name = 'standard.offer.print.line'
    _description = 'Pre calculated line'

    #===========================================================================
    # COLUMNS
    #===========================================================================
    offer_id = fields.Many2one('standard.offer', string='Tariff', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='restrict')
    uoi_id = fields.Many2one('product.uom', string='Unit of Price', required=False, ondelete='restrict', help='Expressed in the sale unity')
    uos_id = fields.Many2one('product.uom', string='Unit of Sale', required=False, ondelete='restrict', help='Unit of Sale')
    qty_1 = fields.Float(string='Q1', required=False)
    price_1 = fields.Float(string='Price', required=False)
    qty_2 = fields.Float(string='Q2', required=False)
    price_2 = fields.Float(string='Price', required=False)
    qty_3 = fields.Float(string='Q3', required=False)
    price_3 = fields.Float(string='Price', required=False)
    qty_4 = fields.Float(string='Q4', required=False)
    price_4 = fields.Float(string='Price', required=False)

    def create_print_lines(self, product, offer):
        """
            Crée une "vue" des premiers prix dégressifs d'un produit par rapport à une offre + les offres standards applicables au jour J
        """
        for line in offer.print_line_ids:
            if product.id  == line.product_id.id:
                line.unlink()
        import sys
        min_quantity = sys.maxint

        standard_offer_line_obj = self.env["standard.offer.line"]
        product_obj = self.env["product.product"]
        net_price_rule_ids = standard_offer_line_obj.search([
            ("offer_id.id", "=", offer.id),
            ("type", "=", "product"),
            ("discount_type", "=", "net_price"),
            ("product_id", "=", product.id),
        ],
                                                                    limit=4,
                                                                    order="quantity ASC")
        quantities = [x.quantity for x in net_price_rule_ids]
        if len(net_price_rule_ids):
            min_quantity = quantities[0]

        net_price_category_rule_ids = standard_offer_line_obj.search([
            ("offer_id.id", "=", offer.id), ("type", "=", "category"), ("discount_type", "=", "net_price"),
            ("category_id", "=", product.sale_family_id.id), ("quantity", "<", min_quantity)
        ],
                                                                             limit=4,
                                                                             order="quantity ASC")
        quantities = [x.quantity for x in net_price_category_rule_ids] + quantities
        if len(quantities):
            min_quantity = quantities[0]

        category_rule_ids = standard_offer_line_obj.search([
            ("offer_id.id", "=", offer.id), ("type", "=", "category"), ("discount_type", "in", ["discount", "increase"]),
            ("category_id", "=", product.sale_family_id.id), ("quantity", "<", min_quantity)
        ],
                                                                   limit=4,
                                                                   order="quantity ASC")
        product_rule_ids = standard_offer_line_obj.search([
            ("offer_id.id", "=", offer.id), ("type", "=", "product"), ("discount_type", "in", ["discount", "increase"]),
            ("product_id", "=", product.id), ("quantity", "<", min_quantity)
        ],
                                                                  limit=4,
                                                                  order="quantity ASC")
        quantities = ([x.quantity for x in category_rule_ids] + [x.quantity for x in product_rule_ids]) + quantities

        base_price_rule_product_ids = standard_offer_line_obj.search([
            ("offer_id.type", "=", "standard"),
            ("offer_id.state", "=", "applicable"),
            ("product_id", "=", product.id),
            ("discount_type", "=", "base_price"),
            ("quantity", "<=", min_quantity),
            ("type", "=", "product"),
        ] + product_obj.between_dates(fields.Date.today()),
                                                                             limit=4,
                                                                             order="quantity ASC")
        quantities = [x.quantity for x in base_price_rule_product_ids] + quantities

        base_price_rule_category_ids = standard_offer_line_obj.search([
            ("offer_id.type", "=", "standard"),
            ("offer_id.state", "=", "applicable"),
            ("category_id", "=", product.sale_family_id.id),
            ("discount_type", "=", "base_price"),
            ("quantity", "<=", min_quantity),
            ("type", "=", "category"),
        ] + product_obj.between_dates(fields.Date.today()),
                                                                              limit=4,
                                                                              order="quantity ASC")
        quantities = [x.quantity for x in base_price_rule_category_ids] + quantities
        quantities = sorted(set(quantities))

        print_line = {"offer_id": offer.id, "product_id": product.id, "uos_id": product.uos_id.id, "uoi_id": product.sale_uoi_id.id}
        for i in range(len(quantities[:4])):
            print_line["qty_%d" % (i + 1)] = quantities[i]
            print_line["price_%d" % (i + 1)] = product.get_price_sale_for_offer(offer, quantities[i])

        self.create(print_line)


def between_dates(date):
    """
        Retourne une partie de domaine : date est compris entre deux dates qui peuvent être vides
    """
    if not date:
        return [("start_date", "=?", False)]
    a = ("start_date", "<=", date)
    b = ("end_date", ">=", date)
    an = ("start_date", "=", False)
    bn = ("end_date", "=", False)
    return ["|", "&", a, b, "|", "&", a, bn, "|", "&", b, an, "&", an, bn]
