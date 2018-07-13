# -*- coding: utf-8 -*-
from openerp.tools.translate import _
from openerp import models, fields, api
from openerp.exceptions import except_orm, ValidationError
from dateutil.relativedelta import relativedelta
from openerp.addons.base_openprod.common import get_form_view


class master_production_period(models.Model):
    """ 
        Period for master production schedule  
    """
    _name = 'master.production.period'
    _description = 'Period for master production schedule'
    _order = 'sequence'
    
    @api.model
    def _period_type_get(self):
        return [
                ('week', _('Week')),
                ('month', _('Month')),
                ('trimester', _('Trimester')),
                       ]
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Name', required=False)
    sequence = fields.Integer(string='Sequence', default=0, required=False)
    start_date = fields.Date(string='Start date', required=False)
    end_date = fields.Date(string='End date', required=False)
    period_type = fields.Selection('_period_type_get', string='Period type')
    is_initial = fields.Boolean(string='Is initial', default=False)
    production_schedule_id = fields.Many2one('master.production.schedule', string='Master production schedule', 
                                             required=False, ondelete='cascade')
    mid_period = fields.Date(string='Mid-date of the period')

    def create_period_line(self, period_type='month', nb=12, production_schedule_id=False, start_date=None):
        """
            Fonction qui crée les lignes de période en fonction du type et du nombre de la période
            :type self: master.production.period
            :param period_type: Type de la période: 'month', 'week' ou 'trimester'
            :type period_type: char
            :param nb: Nombre de périodes
            :type nb: integer
            :param production_schedule_id: Id du PDP auquel on souhaite lier les périodes créées
            :type production_schedule_id: integer
            :param start_date: Date de début à partir de laquelle on commence à créer les périodes
            :type start_date: Date
            :return: True
            :rtype: Boolean 
        """
        if not start_date:
            start_date = fields.Date.today()
        
        x = 1
        sequence = 10
        delta = False
        real_start_date = fields.Date.from_string(start_date)
        #On récupère le delta en fonction du type de période
        if period_type == 'week':
            delta = relativedelta(weeks=1, days=-1)
            mid_delta = relativedelta(days=3)
        elif period_type == 'month':
            delta = relativedelta(months=1, days=-1)
            mid_delta = relativedelta(days=15)
        elif period_type == 'trimester':
            delta = relativedelta(months=3, days=-1)
            mid_delta = relativedelta(days=45)
        
        if delta:
            mid_period = real_start_date + mid_delta
            #On crée une période initiale qui commence et fini à la date de début - 1 jour
            first_date = real_start_date - relativedelta(days=1)
            first_vals = {'name': _('Initial'),
                          'sequence': sequence,
                          'start_date': fields.Date.to_string(first_date),
                          'end_date': fields.Date.to_string(first_date),
                          'mid_period': fields.Date.to_string(mid_period),
                          'period_type': period_type,
                          'is_initial': True,
                          'production_schedule_id': production_schedule_id}
            self.create(first_vals)
            #On crée toutes les périodes qui suivent
            while x <= nb:
                sequence += 10
                day = real_start_date.day
                if day < 10:
                    day = '0%s'%(day)
                else:
                    day = str(day)
                    
                month = real_start_date.month
                if month < 10:
                    month = '0%s'%(month)
                else:
                    month = str(month)
                    
                year = real_start_date.year
                name = '%s/%s/%s'%(day, month, year)
                end_date = real_start_date + delta
                mid_period = real_start_date + mid_delta
                vals = {'name': name,
                        'sequence': sequence,
                        'start_date': fields.Date.to_string(real_start_date),
                        'end_date': fields.Date.to_string(end_date),
                        'mid_period': fields.Date.to_string(mid_period),
                        'period_type': period_type,
                        'production_schedule_id': production_schedule_id}
                x+= 1
                real_start_date = end_date + relativedelta(days=1)
                self.create(vals)
            
        return True
    
    

class master_production_schedule_line(models.Model):
    """ 
        Master production schedule line 
    """
    _name = 'master.production.schedule.line'
    _description = 'Master production schedule line'
    _rec_name = 'product_id'
    _order = 'product_id, period_sequence asc'
    
    @api.model
    def _period_type_get(self):
        return [
                ('week', _('Week')),
                ('month', _('Month')),
                ('trimester', _('Trimester')),
                       ]
    
    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('validate', _('Validate')),
                ('obsolete', _('Obsolete')),
                       ]
    
    
    @api.model
    def _month_get(self):
        return [
                ('00', _('Without month')), 
                ('01', _('January')), 
                ('02', _('February')), 
                ('03', _('March')), 
                ('04', _('April')), 
                ('05', _('May')), 
                ('06', _('June')), 
                ('07', _('July')), 
                ('08', _('August')), 
                ('09', _('September')), 
                ('10', _('October')), 
                ('11', _('November')), 
                ('12', _('December'))
           ]
        
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    period_sequence = fields.Integer(string='Period sequence', default=1, required=False)
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='restrict')
    produce_ok = fields.Boolean(string='Can be produced', default=False, related='product_id.produce_ok')
    sale_ok = fields.Boolean(string='Can be sold', default=False, related='product_id.sale_ok')
    uom_id = fields.Many2one('product.uom', string='Management unit', required=False, ondelete='restrict')
    category_id = fields.Many2one('product.category', string='Product category', required=False, ondelete='restrict', 
                                  domain=[('type', '!=', 'view')])
    period_type = fields.Selection('_period_type_get', string='Period type')
    start_date = fields.Date(string='Start date', required=False)
    mid_period = fields.Date(string='Mid-date', required=False)
    end_date = fields.Date(string='End date', required=False)
    year = fields.Char(string='Year', size=4, required=False)
    month = fields.Selection('_month_get', string='Month')
    week = fields.Char(string='Week', size=2, required=False)
    qty_firm_order = fields.Float(string='Firm consum.', default=0.0, required=False)
    firm_qty_order_amount = fields.Float(string='Amount firm consumption', default=0.0, required=False, help="In company currency")
    qty_forecast_order = fields.Float(string='Forecast consum.', default=0.0, required=False)
    forecast_qty_order_amount = fields.Float(string='Amount forecast consumption', default=0.0, required=False, help="In company currency")
    qty_firm_procurement = fields.Float(string='Firm proc.', default=0.0, required=False)
    firm_procurement_amount = fields.Float(string='Amount firm procurement', default=0.0, required=False, help="In company currency")
    qty_forecast_procurement = fields.Float(string='Forecast proc.', default=0.0, required=False)
    forecast_procurement_amount = fields.Float(string='Amount forecast procurement', default=0.0, required=False, help="In company currency")
    available_stock_firm = fields.Float(string='Firm stock', default=0.0, required=False)
    available_stock_firm_forecast = fields.Float(string='Firm + forecast stock ', default=0.0, required=False)
    state = fields.Selection('_state_get', string='State')
    customer_id = fields.Many2one('res.partner', string='Customer', required=False, ondelete='restrict')
    period_id = fields.Many2one('master.production.period', string='Period', required=False, ondelete='restrict')
    master_production_id = fields.Many2one('master.production.schedule', string='Program', 
                                           required=False, ondelete='cascade')
    

    def create_program_line(self, product=False, period=None, is_initial=False, program_id=False, init_vals=None, customer_id=False, stock=0, stock_prev=0):
        """
            Fonction qui crée les lignes de programme correspondant à la première 
            :type self: master.production.schedule.line
            :param product: recordset du produit
            :type product: recordset : product.product
            :param period: recordset de la période
            :type period: recordset: master.production.period
            :param is_initial: True s'il s'agit de la période initiale
            :type is_initial: Boolean
            :param program_id: Id du programme auquel la ligne va être liée
            :type program_id: Integer
            :param init_vals: Valeurs génériques de la ligne (produit, état ...)
            :type init_vals: Dict
            :param stock: Valeur du stock ferme dispo de la ligne précédente
            :type stock: Float
            :param stock_prev: Valeur du stock dispo (ferme + prévisionnel) de la ligne précédente
            :type stock_prev: Float
            :return: True
            :rtype: Boolean
        """
        if not init_vals:
            init_vals = {}
        
        if period and product:
            #On récupère le mois, l'année et la semaine à partir de la date de début de la période
            period_start = fields.Date.from_string(period.start_date)
            isocal = period_start.isocalendar()
            week = str(isocal[1])
            year = period_start.year
            if len(str(period_start.month)) == 1:
                month = '0%s'%(str(period_start.month))
            else:
                month = str(period_start.month)
                
            vals2 = {'period_id': period.id,
                     'period_type': period.period_type,
                     'period_sequence': period.sequence,
                     'start_date': period.start_date,
                     'mid_period': period.mid_period,
                     'end_date': period.end_date,
                     'year': year,
                     'month': month,
                     'week': week}
            vals2.update(init_vals)
            production_cost = product.production_cost_price
            #Calul des quantités et montants des commandes fermes (moves sortants prévisionnels)
            qty_firm_order = self.compute_procurement_qty(prev=False, initial=is_initial, product_id=product.id, start_date=period.start_date, 
                                                          end_date=period.end_date, customer_id=customer_id, type='out')
            firm_qty_order_amount = qty_firm_order * production_cost
            #Calul des quantités et montants des commandes prévisionnelles (moves sortants prévisionnels + commandes prévisionnelles)
            qty_forecast_order1, forecast_qty_order_amount1 = self.compute_order_amount_and_qty(prev=True, initial=is_initial, product_id=product.id, 
                                                               start_date=period.start_date, end_date=period.end_date, customer_id=customer_id)
            qty_forecast_order2 = self.compute_procurement_qty(prev=True, initial=is_initial, product_id=product.id, start_date=period.start_date, 
                                                               end_date=period.end_date, customer_id=customer_id, type='out')
            forecast_qty_order_amount2 = qty_forecast_order2 * production_cost
            qty_forecast_order = qty_forecast_order1 + qty_forecast_order2
            forecast_qty_order_amount = forecast_qty_order_amount1 + forecast_qty_order_amount2
            #Calul des quantités et montants des approvisionnements fermes (on calcule le montant à partir du prix de revient du produit)
            qty_firm_procurement = self.compute_procurement_qty(prev=False, initial=is_initial, product_id=product.id, start_date=period.start_date, 
                                                                end_date=period.end_date, customer_id=customer_id, type='in')
            firm_procurement_amount = qty_firm_procurement * production_cost
            #Calul des quantités et montants des approvisionnements prévisionnels
            qty_forecast_procurement = self.compute_procurement_qty(prev=True, initial=is_initial, product_id=product.id, start_date=period.start_date, 
                                                                    end_date=period.end_date, customer_id=customer_id, type='in')
            forecast_procurement_amount = qty_forecast_procurement * production_cost
            #Calul du stock dispo ferme
            #Si il s'agit de la ligne initiale, on récupère le stock actuel
            if is_initial:
                stock = product.get_stock_level()
                stock_prev = product.get_stock_level()
            
            avail_firm_stock = stock - qty_firm_order + qty_firm_procurement
            #Calul du stock dispo prévisionnel
            avail_previ_stock = stock_prev - qty_firm_order - qty_forecast_order + qty_firm_procurement + qty_forecast_procurement
            #On récupère toutes les informations de quantité et de montant
            vals3 = {'qty_firm_order': qty_firm_order,
                    'firm_qty_order_amount': firm_qty_order_amount,
                    'qty_forecast_order': qty_forecast_order,
                    'forecast_qty_order_amount': forecast_qty_order_amount,
                    'qty_firm_procurement': qty_firm_procurement,
                    'firm_procurement_amount': firm_procurement_amount,
                    'qty_forecast_procurement': qty_forecast_procurement,
                    'forecast_procurement_amount': forecast_procurement_amount,
                    'available_stock_firm': avail_firm_stock,
                    'available_stock_firm_forecast': avail_previ_stock}
            #Création de la ligne
            vals2.update(vals3)
            self.create(vals2)
        
        return avail_firm_stock, avail_previ_stock
    
    
    def compute_order_amount_and_qty(self, prev=False, initial=False, product_id=False, start_date=None, end_date=None, customer_id=False):
        """
            Fonction qui permet de calculer les quantités et les montants des commandes prévisionnelles ou fermes
            Pour ça, on récupère les quantité des lignes de vente du produit sur la période
            :type self: master.production.schedule.line
            :param prev: True si on recherche les commandes prévisionnelles
            :type prev: Boolean
            :param initial: True s'il s'agit de la ligne correspondant à la période initiale
            :type initial: Boolean
            :param product_id: Id du produit pour lequel on recherche les lignes de vente
            :type product_id: Integer
            :param start_date: Date de début permettant de rechercher les lignes de vente
            :type start_date: Date
            :param end_date: Date de fin permettant de rechercher les lignes de vente
            :type end_date: Date
            :param customer_id: Id du client pour lequel on recherche les lignes de vente
            :type customer_id: Integer
            :return: La quantité et le montant total des lignes de vente trouvées
            :rtype: Float
        """
        qty = 0
        amount = 0
        if product_id and end_date:
            sale_line_obj = self.env['sale.order.line']
            #Si on a une date de départ confirmée on base notre search dessus, sinon on prend la date de départ de la ligne de vente
            args = [('product_id', '=', product_id), ('sale_state', '!=', 'cancel'), '|', '&', ('confirmed_departure_date', '!=', False), ('confirmed_departure_date', '<=', end_date), 
                    '&', ('confirmed_departure_date', '=', False), ('departure_date', '<=', end_date)]
            if prev:
                args.append(('sale_type', '=', 'forecast'))
            else:
                args.append(('sale_type', 'not in', ('open', 'forecast')))
            
            if initial:
                args.extend(['|', ('remaining_qty', '>', 0), '&', ('remaining_qty', '=', 0), ('delivered_qty', '=', 0)])
            else:
                args.extend([ '|', '&', ('confirmed_departure_date', '!=', False), ('confirmed_departure_date', '>=', start_date), 
                            '&', ('confirmed_departure_date', '=', False),('departure_date', '>=', start_date)])
            
            if customer_id:
                args.append(('sale_partner_id', '=', customer_id))
                
            sol_qtys = sale_line_obj.search_group(fields=['uom_qty', 'total_price_currency'],
                                            groupby=[],
                                            args=args,
                                            sum=['uom_qty', 'total_price_currency'],
                                            return_dict=True,
                                            without_order=True)
            if sol_qtys:
                qty = sol_qtys[0].get('uom_qty', 0)
                if not qty:
                    qty = 0 
                    
                amount = sol_qtys[0].get('total_price_currency', 0)
                if not amount:
                    amount = 0 
                
        return qty, amount
    
    
    def compute_procurement_qty(self, prev=False, initial=False, product_id=False, start_date=None, end_date=None, customer_id=False, type=False):
        """
            Fonction qui permet de calculer les quantités et les montants des approvisionnements fermes ou prévisionnels
            Pour ça, on recherche les mouvements en attente du produit et on somme les quantités des mouvements
            :type self: master.production.schedule.line
            :param initial: True s'il s'agit de la ligne correspondant à la période initiale
            :type initial: Boolean
            :param product_id: Id du produit pour lequel on recherche les moves
            :type product_id: Integer
            :param start_date: Date de début permettant de rechercher les moves
            :type start_date: Date
            :param end_date: Date de fin permettant de rechercher les moves
            :type end_date: Date
            :param customer_id: Id du client pour lequel on recherche les moves
            :type customer_id: Integer
            :param type: 'in' ou 'out'
            :type type: Char
            :return: La quantité de produit de tous les moves trouvés
            :rtype: Float
        """
        qty = 0
        if product_id and end_date:
            move_obj = self.env['stock.move']
            args = [('product_id', '=', product_id), ('date', '<=', end_date)]
            if prev:
                args.extend([('is_forecast', '=', True), ('state', '!=', 'cancel')])
            else:
                args.extend([('is_forecast', '=', False), ('state', '=', 'waiting')])
            
            if not initial:
                args.append(('date', '>=', start_date))
            
            if customer_id:
                args.extend([('wo_outgoing_id', '!=', False), ('wo_outgoing_id.customer_id', '=', customer_id)])
            
            if type:
                args.append(('type', '=', type))
                
            move_qtys = move_obj.search_group(fields=['uom_qty'],
                                            groupby=[],
                                            args=args,
                                            sum=['uom_qty'],
                                            return_dict=True,
                                            without_order=True)
            if move_qtys:
                qty = move_qtys[0].get('uom_qty', 0)
                if not qty:
                    qty = 0 
                
        return qty
    
    
    def change_line_state(self, state=False):
        """
            Fonction qui permet de modifier l'état des lignes
        """
        if state:
            self.write({'state': state})
            
        return True
    
    

class master_production_schedule(models.Model):
    """ 
        Master production schedule (=PDP) 
    """
    _name = 'master.production.schedule'
    _description = 'Master production schedule management'
    
    @api.model
    def _period_type_get(self):
        return [
                ('week', _('Week')),
                ('month', _('Month')),
                ('trimester', _('Trimester')),
                       ]
    
    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('validate', _('Validate')),
                ('obsolete', _('Obsolete')),
                       ]
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    #En-tête
    state = fields.Selection('_state_get', string='State', default='draft')
    name = fields.Char(string='Name', required=True)
    start_date = fields.Date(string='Start date', required=True)
    customer_id = fields.Many2one('res.partner', string='Customer', required=False, ondelete='restrict', 
                                  domain=['|','&', ('is_company', '=', True), ('is_customer', '=', True),
                                          '&', ('is_company', '=', False), ('can_order', '=', True)])
    openprod_create_date = fields.Date(string='Create date', default=lambda self: fields.Date.today())
    #Onglet lignes
    line_ids = fields.One2many('master.production.schedule.line', 'master_production_id',  string='Lines')
    #Onglet période
    period_type = fields.Selection('_period_type_get', string='Period type')
    period_nb = fields.Integer(string='Period number', default=0, required=False)
    period_ids = fields.One2many('master.production.period', 'production_schedule_id',  string='Period lines')
    #Onglet configuration
    product_ids = fields.Many2many('product.product', 'product_master_production_rel', 'master_production_id', 'product_id', 
                                   string='Products', domain=[('state', 'in', ('lifeserie', 'endlife'))])


    @api.multi
    def generate_schedule_period_line(self):
        """
            Fonction associée au bouton qui permet de créer des périodes pour le PDP
        """
        period_obj = self.env['master.production.period']
        for schedule_prod in self:
            if schedule_prod.start_date and schedule_prod.period_type:
                #On commence par supprimer toutes les lignes
                schedule_prod.write({'period_ids': [(5, 0)]}) 
                #On appelle la fonction de création des lignes
                period_obj.create_period_line(period_type=schedule_prod.period_type, nb=schedule_prod.period_nb, 
                                              production_schedule_id=schedule_prod.id, start_date=schedule_prod.start_date)
              
        return True
    
    
    @api.multi
    def delete_all_periods(self):
        """
            Fonction associée au bouton qui permet de supprimer toutes les lignes de périodes
        """
        for schedule_prod in self:
            schedule_prod.write({'period_ids': [(5, 0)]}) 
              
        return True
    
    
    @api.multi
    def import_program_lines(self):
        """
            Fonction associée au bouton qui permet d'appeler la fonction d'import des lignes de programme
        """
        for program in self:
            program._import_program_lines(master_production_id=False, period_id=False, product_id=False, delete_all_lines=True)
                    
        return True
    
    
    def _import_program_lines(self, master_production_id=False, period_id=False, product_id=False, delete_all_lines=False):
        """
            Fonction qui permet d'importer les lignes de programme
        """
        line_obj = self.env['master.production.schedule.line']
        if not master_production_id:
            program = self
        else:
            program = self.browse(master_production_id)
        
        if program:
            if program.product_ids and program.period_ids:
                period_ids = False
                new_line = False
                period_rs = False
                production_line_obj = self.env['master.production.schedule.line']
                if delete_all_lines:
                    program.write({'line_ids': [(5, 0)]})
                    
                #Si on a l'id d'une période, on ne supprime et ne recalcule que les périodes supérieures
                #à la période envoyée
                if not period_id:
                    period_ids = program.period_ids
                else:
                    period_obj = self.env['master.production.period']
                    period_rs = period_obj.browse(period_id)
                    if period_rs:
                        period_ids = period_obj.search([('production_schedule_id', '=', program.id),
                                                        ('sequence', '>=', period_rs.sequence)], order="sequence asc")
                
                #Si on a l'id d'un produit, on ne supprime et ne recalcule que les lignes de ce produit
                if not product_id:
                    product_ids = program.product_ids
                else:
                    product_ids = self.env['product.product'].browse(product_id)
                    
                if period_ids and product_ids:
                    #On recherche et supprime les ids des lignes à recalculer
                    if period_id and product_id:
                        delete_lines_rs = production_line_obj.search([('product_id', '=', product_id),
                                                                       ('period_id', 'in', period_ids.ids),
                                                                       ('master_production_id', '=', program.id)])
                        delete_lines = [(2, line.id) for line in delete_lines_rs]
                        program.write({'line_ids': delete_lines})
                        new_line = True
                            
                    #On initialise le dictionnaire de création avec les données génériques
                    customer_id = program.customer_id and program.customer_id.id or False
                    vals = {'state': program.state,
                            'customer_id': customer_id,
                            'master_production_id': program.id} 
                    #On parcourt tous les produits et on récupère les données génériques du produit
                    for product in product_ids:
                        vals2 = {'product_id': product.id,
                                 'uom_id': product.uom_id and product.uom_id.id or False,
                                 'category_id': product.categ_id and product.categ_id.id or False}
                        vals.update(vals2)
                        #On parcourt ensuite chaque période et on appelle la fonction correspondante
                        stock = 0
                        stock_prev = 0
                        #Si on a passer des périodes spécifiques, on récupère la quantité de stock de la dernière ligne
                        if new_line and period_rs:
                            last_line_rs = production_line_obj.search([('product_id', '=', product_id),
                                                                       ('period_sequence', '<', period_rs.sequence),
                                                                       ('master_production_id', '=', program.id)], order="period_sequence desc", limit=1)
                            stock = last_line_rs.available_stock_firm
                            stock_prev = last_line_rs.available_stock_firm_forecast
                            
                        for period in period_ids:
                            stock, stock_prev = line_obj.create_program_line(product=product, period=period, is_initial= period.is_initial, 
                                                         program_id=program, init_vals=vals, customer_id=customer_id, stock=stock, stock_prev=stock_prev)
                    
        return True
    
    
    @api.multi
    def show_program_lines(self):
        """
            Fonction associée au bouton qui renvoie vers la vue tree des lignes de programme
        """
        action_struc = {}
        action_dict = get_form_view(self, 'master_production_schedule.master_production_schedule_line_see_tree')
        if action_dict and action_dict.get('id') and action_dict.get('type'):
            action = self.env[action_dict['type']].browse(action_dict['id'])
            action_struc = action.read()
            action_struc[0]['domain'] = [('master_production_id', '=', self.id)]
            action_struc = action_struc[0]
              
        return action_struc
    
    
    @api.multi
    def delete_all_lines(self):
        """
            Fonction associée au bouton qui permet de supprimer toutes les lignes de programme du PDP
        """
        for schedule_prod in self:
            schedule_prod.write({'line_ids': [(5, 0)]}) 
              
        return True
    
    
    @api.multi
    def program_validate(self):
        """
            Fonction associée au bouton qui permet de passer le programme à l'état 'Validé'
        """
        for schedule_prod in self:
            schedule_prod.write({'state': 'validate'})
            schedule_prod.line_ids.change_line_state('validate')
              
        return True
    
    
    @api.multi
    def program_obsolete(self):
        """
            Fonction associée au bouton qui permet de passer le programme à l'état 'Obsolete'
        """
        for schedule_prod in self:
            schedule_prod.write({'state': 'obsolete'}) 
            schedule_prod.line_ids.change_line_state('obsolete')
            
        return True
    
    
    @api.multi
    def program_draft(self):
        """
            Fonction associée au bouton qui permet de passer le programme à l'état 'Brouillon'
        """
        for schedule_prod in self:
            schedule_prod.write({'state': 'draft'}) 
            schedule_prod.line_ids.change_line_state('draft')
              
        return True
    
    
    @api.multi
    def compute_all(self):
        """
            Fonction associée au bouton qui permet de recalculer les stocks des lignes
        """
        self.delete_all_lines()
        for schedule_prod in self:
            schedule_prod._import_program_lines(master_production_id=False, 
                                                period_id=False, 
                                                product_id=False,
                                                delete_all_lines=False)
              
        return True
    
