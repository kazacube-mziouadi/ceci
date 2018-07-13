# -*- coding: utf-8 -*-
from datetime import date

from openerp import models, fields, api
from openerp.addons.base_openprod.common import get_form_view
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT


class note_openprod(models.Model):
    _inherit = 'note.openprod'
    # ===========================================================================
    # COLUMNS
    # ===========================================================================
    customer_performance_id = fields.Many2one(
        'customer_performance.analysis', string='Customer performance',
        required=False, ondelete='cascade'
    )


class customer_performance_category(models.Model):
    """
        Customer category for customer performance analysis
    """
    _name = 'customer_performance.category'
    _description = 'category of customer'

    # ===========================================================================
    # COLUMNS
    # ===========================================================================
    name = fields.Char(size=255, required=True)


class customer_performance_analysis(models.Model):
    """
    Customer performance analysis
    """
    _name = 'customer_performance.analysis'
    _description = (
        'Auto generated customer\'s performance analysis'
        ' for his orders requested in a given time lapse'
    )
    _rec_name = 'customer_id'

    @api.one
    @api.depends('date_from')
    def _compute_performance_year(self):
        """
            Affiche l'année de la date de début de période
        """
        if not self.date_from:
            return
        self.year = fields.Date.from_string(self.date_from).year

    @api.one
    @api.depends('customer_id', 'date_from', 'date_to')
    def _compute_volumetry_and_delay(self):
        product_list = self.env['product.product']
        sale_order_line_obj = self.env['sale.order.line']
        late_line_count = 0
        late_day_total = 0
        service_rate = 100
        late_day_avg = 0
        late_line_count_for_service_rate = 0

        if not(self.customer_id and self.date_from and self.date_to):
            return

        sol_total_price = sale_order_line_obj.search_group(
            fields=['total_price_currency'],
            args=self._get_sale_order_line_default_query_args(),
            groupby=list(),
            sum=['total_price_currency'],
            return_dict=True,
            without_order=True
        )
        expense = sol_total_price and sol_total_price[0].get('total_price_currency', 0) or 0
        sale_order_line_rs = self._get_sale_order_line_rs()
        sale_order_line_count = len(sale_order_line_rs)

        for sale_order_line in sale_order_line_rs:
            product_list |= sale_order_line.product_id
            delivery = Delievery(sale_order_line)
            if delivery.is_late:
                late_line_count += 1
                if delivery.is_done:
                    late_line_count_for_service_rate += 1
                    late_day_total += delivery.nb_days_lateness

        if late_line_count_for_service_rate > 0 and sale_order_line_count > 0:
            service_rate = (1 - late_line_count_for_service_rate / float(sale_order_line_count)) * 100.0
            late_day_avg = late_day_total / late_line_count_for_service_rate

        self.year_expense = expense
        self.sale_order_line_quantity = sale_order_line_count
        self.sold_product_quantity = product_list and len(product_list) or 0
        self.service_rate = service_rate
        self.late_order_line_quantity = late_line_count
        self.late_day_avg_quantity = late_day_avg

    @api.one
    @api.depends('date_from', 'date_to', 'customer_id')
    def _compute_quality(self):
        """
            Calcule le nombre de fiches de non conformité sur la période indiquée
        """
        if not (self.customer_id and self.date_from and self.date_to):
            return
        non_conformity_file_obj = self.env['nonconformity.file']

        self.non_conformity_quantity = int(non_conformity_file_obj.search_count(
            [('partner_id', '=', self.customer_id.id),
             ('create_date', '>=', self.date_from),
             ('create_date', '<=', self.date_to)])
        )

    @api.one
    @api.depends('customer_id')
    def _compute_invoices(self):
        if not self.customer_id:
            return

        self.customer_exceed_invoice_outstanding = self.customer_id.exceed_invoice_outstanding
        self.customer_invoice_outstanding = self.customer_id.invoice_outstanding

    # ===========================================================================
    # COLUMNS
    # ===========================================================================
    # En-tête
    customer_id = fields.Many2one(
        'res.partner', string='Customer', required=True, ondelete='restrict'
    )
    customer_category_id = fields.Many2one(
        'customer_performance.category',
        string='Customer category', required=False, ondelete='restrict'
    )
    customer_grade = fields.Float(
        string='Customer grade', default=0.0, required=False
    )
    customer_invoice_outstanding = fields.Float(
        string='Invoice outstanding', required=False,
        store=False, compute='_compute_invoices'
    )
    customer_exceed_invoice_outstanding = fields.Float(
        string='Exceed invoice outstanding', required=False,
        store=False, compute='_compute_invoices'
    )
    comment_ids = fields.One2many(
        'note.openprod', 'customer_performance_id', string='Comments'
    )
    date_from = fields.Date(
        string='Starting date', required=True
    )
    date_to = fields.Date(
        string='Ending date', required=True
    )
    late_order_line_quantity = fields.Integer(
        string='Number of late delivery', default=0,
        required=False, compute='_compute_volumetry_and_delay', store=False
    )
    late_day_avg_quantity = fields.Float(
        string='Average lateness in days', default=0.0,
        required=False, compute='_compute_volumetry_and_delay', store=False,
        help="(sum of late days) / (Number of late delieveries)"
    )
    non_conformity_quantity = fields.Integer(
        string='Non conformity number', default=0,
        required=False, compute='_compute_quality', store=False
    )
    sale_order_line_quantity = fields.Integer(
        string='Number of order', default=0,
        required=False, compute='_compute_volumetry_and_delay', store=False
    )
    service_rate = fields.Float(
        string='Service rate', default=0.0, required=False,
        compute='_compute_volumetry_and_delay', store=False,
        help=("Service rate = ((1 - number of late delieveries) "
              "/ number of delieveries ) * 100")
    )
    sold_product_quantity = fields.Integer(
        string='Product types sold', default=0, required=False,
        compute='_compute_volumetry_and_delay', store=False
    )
    year = fields.Integer(
        string='Year', required=False,
        compute='_compute_performance_year', store=True
    )
    # Indicateur
    year_expense = fields.Float(
        string='Customer expense', default=0.0,
        required=False, compute='_compute_volumetry_and_delay', store=False
    )

    @api.multi
    def show_sale_order_lines(self):
        """
            Fonction retourne les lignes d'achat (retard ou non selon le context) du fournisseur et de la période
            sélectionnés
        """
        sale_order_line_rs = self._get_sale_order_line_rs()
        sale_order_line_ids = list()
        action_struc = dict()

        if not sale_order_line_rs:
            return action_struc

        if self.env.context.get('only_late_line'):
            sale_order_line_ids = self._get_late_sale_order_line_ids(sale_order_line_rs=sale_order_line_rs)
        else:
            sale_order_line_ids = sale_order_line_rs.ids

        action_dict = get_form_view(self, 'sale.action_sale_order_line')
        if action_dict and 'id' and 'type' in action_dict:
            action = self.env[action_dict['type']].browse(action_dict['id'])
            action_struc = action.read()
            action_struc[0]['domain'] = [('id', 'in', sale_order_line_ids)]
            action_struc[0]['context'] = {}
            action_struc = action_struc[0]
        return action_struc

    @api.multi
    def show_non_conformity_lines(self):
        """
            Fonction qui cherche et retourne les fiches de non conformités du partenaire et de la période sélectionnés
        """
        action_struc = dict()
        nonconformity_file_obj = self.env['nonconformity.file']

        if not (self.customer_id and self.date_from and self.date_to):
            return action_struc

        non_conformity_ids = nonconformity_file_obj.search([
            ('partner_id', '=', self.customer_id.id),
            ('create_date', '>=', self.date_from),
            ('create_date', '<=', self.date_to)
        ]).ids

        action_dict = get_form_view(self, 'stock.act_nonconformity_file_reception_id')

        if 'id' and 'type' in action_dict:
            action = self.env[action_dict['type']].browse(action_dict['id'])
            action_struc = action.read()
            action_struc[0]['domain'] = [('id', 'in', non_conformity_ids)]
            action_struc[0]['context'] = {}
            action_struc = action_struc[0]

        return action_struc

    def _get_sale_order_line_default_query_args(self):
        return [
            ('sale_partner_id', '=', self.customer_id.id),
            ('sale_state', 'not in', ['draft', 'cancel']),
            ('requested_date', '>=', self.date_from),
            ('requested_date', '<=', self.date_to)
        ]

    def _get_sale_order_line_rs(self):
        sale_order_line_obj = self.env['sale.order.line']
        if not (self.date_from and self.date_to and self.customer_id):
            return sale_order_line_obj

        return sale_order_line_obj.search(args=self._get_sale_order_line_default_query_args())

    def _get_late_sale_order_line_ids(self, sale_order_line_rs=None):
        if not sale_order_line_rs:
            sale_order_line_rs = self._get_sale_order_line_rs()
        sale_order_line_ids = list()
        for sale_order_line in sale_order_line_rs:
            delievery = Delievery(sale_order_line)
            if delievery.is_late:
                sale_order_line_ids.append(sale_order_line.id)
        return sale_order_line_ids


class Delievery(object):
    """
        Utility object to get lateness for a sale order line,
        By default a delievery is not late
    """

    is_late = False
    nb_days_lateness = 0
    is_done = False

    def __init__(self, sale_order_line_id):
        self.line_id = sale_order_line_id
        self._compute_lateness()

    def _compute_lateness(self):
        self.is_done = self._get_is_done()
        self.is_late = self._get_is_late()
        self.nb_days_lateness = self._get_nb_days_lateness()

    def _get_is_late(self):
        if not self.line_id.confirmed_departure_date:
            return False

        if not self.is_done:
            return self.line_id.confirmed_departure_date < date.today().strftime(DEFAULT_SERVER_DATE_FORMAT)

        return self.line_id.confirmed_departure_date < self.line_id.last_delivery_date

    def _get_is_done(self):
        waiting_move_ids = self.line_id.stock_move_ids.filtered(
            lambda r: r.state == 'waiting'
        )
        return len(waiting_move_ids) == 0

    def _get_nb_days_lateness(self):
        if not (self.is_late and self.is_done):
            return 0
        string_to_date = fields.Date.from_string
        time_delta = string_to_date(self.line_id.confirmed_departure_date) -\
            string_to_date(self.line_id.last_delivery_date)
        return time_delta.days
