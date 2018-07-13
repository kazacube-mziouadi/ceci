# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
from openerp.addons.base_openprod.common import get_form_view


class note_openprod(models.Model):
    _inherit = 'note.openprod'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    supplier_performance_id = fields.Many2one('supplier.performance', string='Supplier performance', required=False, ondelete='cascade')


    
class supplier_performance_category(models.Model):
    """ 
        Supplier category for supplier performance
    """
    _name = 'supplier.performance.category'
    _description = 'Supplier category for supplier performance'
    
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Name', size=218, required=True)

    
    
class supplier_performance(models.Model):
    """ 
        Supplier performance analysis
    """
    _name = 'supplier.performance'
    _description = 'Supplier performance analysis'
    _rec_name = 'supplier_id'
    
    @api.one
    @api.depends('date_from')
    def _compute_performance_year(self):
        """
            Affiche l'année de la date de début de période
        """
        date_from = self.date_from and fields.Date.from_string(self.date_from) or False
        if date_from:
            self.year = date_from.year
        else:
            self.year = 0
            
    
    @api.one
    @api.depends('supplier_id', 'date_from', 'date_to')
    def _compute_volumetry_and_delay(self):
        """
            Calcul de la volumétrie et du délai:
            - CA réalisé sur le fournisseur sur l'année : total de tous les achats du commandeur convertit dans
                la devise de la société, avec comme date pour le taux de conversion la date du jour
                - Nombre de ligne d'achat généré
                - Nombre de produits achetés
                - Taux de service (nb lignes en retard/nb lignes total d'achat)
        """
        purchase_line_obj = self.env['purchase.order.line']
        supplier = self.supplier_id
        revenue = 0
        nb_purchase_line = 0
        service_rate = 100
        late_line = 0
        late_day_avg_qty = 0
        late_day_qty = 0
        date_from = self.date_from
        date_to = self.date_to
        product_list = self.env['product.product']
        today = fields.Date.today()
        if supplier and date_from and date_to:
            args = [('purchase_partner_id', '=', supplier.id), 
                    ('purchase_state', 'not in', ['draft', 'cancel']), 
                    ('expected_date', '>=', date_from), 
                    ('expected_date', '<=', date_to)]
            pol_amount = purchase_line_obj.search_group(fields=['total_price_currency'],
                                            groupby=[],
                                            args=args,
                                            sum=['total_price_currency'],
                                            return_dict=True,
                                            without_order=True)
            revenue = pol_amount and pol_amount[0].get('total_price_currency', 0) or 0
            #Calcul du nombre de lignes d'achat
            purchase_line_rs = purchase_line_obj.search(args)
            nb_purchase_line = purchase_line_rs and len(purchase_line_rs) or 0
            #Calcul du nombre de produits et du nombre de lignes en retard
            for purchase_line in purchase_line_rs:
                product_list |= purchase_line.product_id
                compare_date = purchase_line.confirmed_date or purchase_line.last_delivery_date or False 
                if not compare_date:
                    compare_date = today
                    
                expected_date = purchase_line.expected_date
                if compare_date and expected_date < compare_date:
                    time_delta = fields.Date.from_string(compare_date) - fields.Date.from_string(expected_date)
                    late_day_qty += time_delta.days
                    late_line += 1
        
        if late_line > 0 and nb_purchase_line > 0:
            service_rate = (1-late_line / float(nb_purchase_line)) * 100.0
            late_day_avg_qty = late_day_qty / late_line
            
        self.year_revenue = revenue
        self.purchase_line_qty = nb_purchase_line
        self.purchased_product_qty = product_list and len(product_list) or 0
        self.service_rate = service_rate
        self.late_line_qty = late_line 
        self.late_day_avg_qty = late_day_avg_qty 
        
    
    @api.one
    @api.depends()
    def _compute_quality(self):
        """
            Calcule le nombre de fiches de non conformité sur la période indiquée
        """
        supplier = self.supplier_id
        date_from = self.date_from
        date_to = self.date_to
        if supplier and date_from and date_to:
            self.non_conformity_qty = len(self.env['nonconformity.file'].search([('partner_id', '=', supplier.id), 
                                                                                 ('create_date', '>=', self.date_from), 
                                                                                 ('create_date', '<=', date_to)]).ids)
        else:
            self.non_conformity_qty = 0
            
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    #En-tête
    supplier_id = fields.Many2one('res.partner', string='Supplier', required=True, ondelete='restrict',
                                  domain=[('is_supplier', '=', True)])
    date_from = fields.Date(string='Start date of the period', required=True)
    date_to = fields.Date(string='End date of the period', required=True)
    year = fields.Integer(string='Year', required=False, compute='_compute_performance_year', store=True)
    cat_supplier_id = fields.Many2one('supplier.performance.category', string='Supplier category', required=False, ondelete='restrict')
    supplier_grade = fields.Float(string='Supplier grade', default=0.0, required=False)
    #Indicateur
    year_revenue = fields.Float(string='Supplier revenue on the year', default=0.0, required=False, compute='_compute_volumetry_and_delay', store=False)
    purchase_line_qty = fields.Integer(string='Purchase line number generated', default=0, required=False, compute='_compute_volumetry_and_delay', store=False)
    purchased_product_qty = fields.Integer(string='Purchased products number', default=0, required=False, compute='_compute_volumetry_and_delay', store=False)
    service_rate = fields.Float(string='Service rate', default=0.0, required=False, compute='_compute_volumetry_and_delay', store=False,
                                help="Service rate = ((1 - Receipt late line number) / Purchase line number generated ) * 100")
    late_line_qty = fields.Integer(string='Receipt late line number', default=0, required=False, compute='_compute_volumetry_and_delay', store=False)
    non_conformity_qty = fields.Integer(string='Non conformity number', default=0, required=False, compute='_compute_quality', store=False)
    late_day_avg_qty = fields.Float(string='Late day average number', default=0.0, required=False, compute='_compute_volumetry_and_delay', store=False,
                                help="(Sum of late days) / (Late purchase line number)")
    
    comment_ids = fields.One2many('note.openprod', 'supplier_performance_id', string='Comments')
    
    
    @api.multi
    def show_late_purchase_line(self):
        """
            Fonction qui appelle la fonction de recherche des lignes d'achat en retard
        """
        return self.show_purchase_line()
        
        
    @api.multi
    def show_purchase_line(self):
        """
            Fonction qui cherche et retourne les lignes d'achat (retard ou non) du fournisseur et de la période
            sélectionnés
        """
        purchase_line_obj = self.env['purchase.order.line']
        supplier = self.supplier_id
        date_from = self.date_from
        date_to = self.date_to
        purchase_line_ids = []
        context = self.env.context
        today = fields.Date.today()
        if supplier and date_from and date_to:
            args = [('purchase_partner_id', '=', supplier.id), 
                    ('purchase_state', 'not in', ['draft', 'cancel']), 
                    ('expected_date', '>=', date_from), 
                    ('expected_date', '<=', date_to)]
            purchase_line_rs = purchase_line_obj.search(args)
            if context.get('search_late_line'):
                for purchase_line in purchase_line_rs:
                    compare_date = purchase_line.confirmed_date or purchase_line.last_delivery_date or False 
                    if not compare_date:
                        compare_date = today
                        
                    expected_date = purchase_line.expected_date
                    if compare_date and expected_date < compare_date:
                        purchase_line_ids.append(purchase_line.id)
                        
            else:
                purchase_line_ids = purchase_line_rs.ids
        
        action_struc = {}
        action_dict = get_form_view(self, 'purchase.action_purchase_order_line')
        if action_dict and action_dict.get('id') and action_dict.get('type'):
            action = self.env[action_dict['type']].browse(action_dict['id'])
            action_struc = action.read()
            action_struc[0]['domain'] = [('id', 'in', purchase_line_ids)]
            action_struc[0]['context'] = {}
            action_struc = action_struc[0]
              
        return action_struc
        
        
    @api.multi
    def show_non_conformity_line(self):
        """
            Fonction qui cherche et retourne les fiches de non conformités du partenaire et de la période sélectionnés
        """
        supplier = self.supplier_id
        date_from = self.date_from
        date_to = self.date_to
        non_conformity_ids = []
        if supplier and date_from and date_to:
            non_conformity_ids = self.env['nonconformity.file'].search([('partner_id', '=', supplier.id), 
                                                                        ('create_date', '>=', self.date_from), 
                                                                        ('create_date', '<=', date_to)]).ids
        
        action_struc = {}
        action_dict = get_form_view(self, 'stock.act_nonconformity_file_reception_id')
        if action_dict and action_dict.get('id') and action_dict.get('type'):
            action = self.env[action_dict['type']].browse(action_dict['id'])
            action_struc = action.read()
            action_struc[0]['domain'] = [('id', 'in', non_conformity_ids)]
            action_struc[0]['context'] = {}
            action_struc = action_struc[0]
              
        return action_struc
    
