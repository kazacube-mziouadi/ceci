# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from dateutil.relativedelta import relativedelta

MONTH_FIELDS = {
    1: 'month1',
    2: 'month2',
    3: 'month3',
    4: 'month4',
    5: 'month5',
    6: 'month6',
    7: 'month7',
    8: 'month8',
    9: 'month9',
    10: 'month10',
    11: 'month11',
    12: 'month12',
}


class budget_treasury_summary(models.Model):
    """ 
        Budget treasury summary
    """
    _name = 'budget.treasury.summary'
    _description = 'Budget treasury summary'
    
    @api.model
    def _type_get(self):
        return [
                ('balance_sheet', _('Balance sheet')),
                ('budget_balance', _('Budget balance sheet')),
                       ]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char('Name', required=True, size=24)
    sequence = fields.Integer(string='Sequence', default=0, required=True)
    type = fields.Selection('_type_get', string='Type')
    month1 = fields.Float(string='Month 1', default=0.0, required=False)
    month2 = fields.Float(string='Month 2', default=0.0, required=False)
    month3 = fields.Float(string='Month 3', default=0.0, required=False)
    month4 = fields.Float(string='Month 4', default=0.0, required=False)
    month5 = fields.Float(string='Month 5', default=0.0, required=False)
    month6 = fields.Float(string='Month 6', default=0.0, required=False)
    month7 = fields.Float(string='Month 7', default=0.0, required=False)
    month8 = fields.Float(string='Month 8', default=0.0, required=False)
    month9 = fields.Float(string='Month 9', default=0.0, required=False)
    month10 = fields.Float(string='Month 10', default=0.0, required=False)
    month11 = fields.Float(string='Month 11', default=0.0, required=False)
    month12 = fields.Float(string='Month 12', default=0.0, required=False)
    treasury_id = fields.Many2one('treasury', string='Treasury', required=False, ondelete='cascade')
    
    _sql_constraints = [
        ('unique_type', 'unique(type, treasury_id)', 'Error: You can\'t have two lines with the same type.'),
    ]
    
    def compute_budget_treasury_summary(self, treasury):
        """
            Fonction permettant de calculer la synthèse de la trésorerie
            :param treasury_id: L'id de la trésorerie à assigner à la ligne
            :type treasury_id: integer
            :return: True
            :rtype: boolean
        """
        total_revenue = {
                    'month1': 0,
                    'month2': 0,
                    'month3': 0,
                    'month4': 0,
                    'month5': 0,
                    'month6': 0,
                    'month7': 0,
                    'month8': 0,
                    'month9': 0,
                    'month10': 0,
                    'month11': 0,
                    'month12': 0,
                    }
        total_expenses = {
                    'month1': 0,
                    'month2': 0,
                    'month3': 0,
                    'month4': 0,
                    'month5': 0,
                    'month6': 0,
                    'month7': 0,
                    'month8': 0,
                    'month9': 0,
                    'month10': 0,
                    'month11': 0,
                    'month12': 0,
                    }
        total_balance = {
                    'month1': 0,
                    'month2': 0,
                    'month3': 0,
                    'month4': 0,
                    'month5': 0,
                    'month6': 0,
                    'month7': 0,
                    'month8': 0,
                    'month9': 0,
                    'month10': 0,
                    'month11': 0,
                    'month12': 0,
                    }
        total_budget_balance = {
                    'month1': 0,
                    'month2': 0,
                    'month3': 0,
                    'month4': 0,
                    'month5': 0,
                    'month6': 0,
                    'month7': 0,
                    'month8': 0,
                    'month9': 0,
                    'month10': 0,
                    'month11': 0,
                    'month12': 0,
                    }
        #On récupère les montants des recettes, dépenses et bilans des paiements
        for payment_line in treasury.payment_list_ids:
            if payment_line.type == 'revenue':
                for v in MONTH_FIELDS.values():
                    total_revenue[v] += payment_line[v]
                    total_balance[v] += payment_line[v]
            elif payment_line.type == 'expense':
                for v in MONTH_FIELDS.values():
                    total_expenses[v] += payment_line[v]
                    total_balance[v] -= payment_line[v]
        
        #On récupère les montants des recettes, dépenses et bilans des ventes et achats
        for so_po_line in treasury.sale_purchase_list_ids:
            if so_po_line.type == 'revenue':
                for v in MONTH_FIELDS.values():
                    total_revenue[v] += so_po_line[v]
                    total_balance[v] += so_po_line[v]
            elif so_po_line.type == 'expense':
                for v in MONTH_FIELDS.values():
                    total_expenses[v] += so_po_line[v]
                    total_balance[v] -= so_po_line[v]
        
        #On récupère les montants des saisies manuelles de budget
        for manual_line in treasury.manual_budget_list_ids:
            if manual_line.type == 'budget_revenue':
                for v in MONTH_FIELDS.values():
                    total_budget_balance[v] += manual_line[v]
            elif manual_line.type == 'budget_expense':
                for v in MONTH_FIELDS.values():
                    total_budget_balance[v] -= manual_line[v]
        
        #On récupère les montants des recettes et dépenses des saisies manuelles
        for manual_line in treasury.manual_treasury_list_ids:
            if manual_line.type == 'revenue':
                for v in MONTH_FIELDS.values():
                    total_revenue[v] += manual_line[v]
                    total_balance[v] += manual_line[v]
            elif manual_line.type == 'expense':
                for v in MONTH_FIELDS.values():
                    total_expenses[v] += manual_line[v]
                    total_balance[v] -= manual_line[v]
        
        #On recherche les éventuelles lignes déjà existantes liées à la trésorerie 
        old_lines_ids = self.search([('treasury_id', '=', treasury.id)])
        if old_lines_ids:
            for line in old_lines_ids:
                if line.type == 'balance_sheet':
                    line.write(total_balance)
                elif line.type == 'budget_balance':
                    line.write(total_budget_balance)
        else:
            #S'il n'en existe pas, on crée les 2 lignes correspondantes
            #Ligne de bilan
            vals = {'name': _('Balance sheet'), 'sequence': 3, 'type': 'balance_sheet',
                     'treasury_id': treasury.id}
            vals.update(total_balance)
            self.create(vals)
            #Ligne de bilan budget
            vals = {'name': _('Budget balance sheet'), 'sequence': 4, 'type': 'budget_balance',
                     'treasury_id': treasury.id}
            vals.update(total_budget_balance)
            self.create(vals)
            
        return True
    
    
    
class treasury_summary(models.Model):
    """ 
        Treasury summary
    """
    _name = 'treasury.summary'
    _description = 'Treasury summary'
    
    @api.model
    def _type_get(self):
        return [
                ('revenue', _('Revenue')),
                ('expense', _('Expense')),
                ('balance_sheet', _('Balance sheet')),
                ('accumulation_balance', _('Accumulation balance sheet')),
                       ]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char('Name', required=True, size=24)
    sequence = fields.Integer(string='Sequence', default=0, required=True)
    type = fields.Selection('_type_get', string='Type')
    month1 = fields.Float(string='Month 1', default=0.0, required=False)
    month2 = fields.Float(string='Month 2', default=0.0, required=False)
    month3 = fields.Float(string='Month 3', default=0.0, required=False)
    month4 = fields.Float(string='Month 4', default=0.0, required=False)
    month5 = fields.Float(string='Month 5', default=0.0, required=False)
    month6 = fields.Float(string='Month 6', default=0.0, required=False)
    month7 = fields.Float(string='Month 7', default=0.0, required=False)
    month8 = fields.Float(string='Month 8', default=0.0, required=False)
    month9 = fields.Float(string='Month 9', default=0.0, required=False)
    month10 = fields.Float(string='Month 10', default=0.0, required=False)
    month11 = fields.Float(string='Month 11', default=0.0, required=False)
    month12 = fields.Float(string='Month 12', default=0.0, required=False)
    treasury_id = fields.Many2one('treasury', string='Treasury', required=False, ondelete='cascade')
    
    _sql_constraints = [
        ('unique_type', 'unique(type, treasury_id)', 'Error: You can\'t have two lines with the same type.'),
    ]
    
    def compute_treasury_summary(self, treasury):
        """
            Fonction permettant de calculer la synthèse de la trésorerie
            :param treasury_id: L'id de la trésorerie à assigner à la ligne
            :type treasury_id: integer
            :return: True
            :rtype: boolean
        """
        #On récupère le solde initial
        initial_balance = treasury.initial_balance
        #On crée une liste de mois afin de les récupérer dans l'ordre
        month_list = ['month1','month2','month3','month4','month5','month6','month7','month8',
                      'month9','month10','month11', 'month12']
        total_revenue = {
                    'month1': 0,
                    'month2': 0,
                    'month3': 0,
                    'month4': 0,
                    'month5': 0,
                    'month6': 0,
                    'month7': 0,
                    'month8': 0,
                    'month9': 0,
                    'month10': 0,
                    'month11': 0,
                    'month12': 0,
                    }
        total_expenses = {
                    'month1': 0,
                    'month2': 0,
                    'month3': 0,
                    'month4': 0,
                    'month5': 0,
                    'month6': 0,
                    'month7': 0,
                    'month8': 0,
                    'month9': 0,
                    'month10': 0,
                    'month11': 0,
                    'month12': 0,
                    }
        total_balance = {
                    'month1': 0,
                    'month2': 0,
                    'month3': 0,
                    'month4': 0,
                    'month5': 0,
                    'month6': 0,
                    'month7': 0,
                    'month8': 0,
                    'month9': 0,
                    'month10': 0,
                    'month11': 0,
                    'month12': 0,
                    }
        total_accumul_balance = {
                    'month1': 0,
                    'month2': 0,
                    'month3': 0,
                    'month4': 0,
                    'month5': 0,
                    'month6': 0,
                    'month7': 0,
                    'month8': 0,
                    'month9': 0,
                    'month10': 0,
                    'month11': 0,
                    'month12': 0,
                    }
        #On récupère les montants des recettes, dépenses et bilans des paiements
        for payment_line in treasury.payment_list_ids:
            if payment_line.type == 'revenue':
                for v in MONTH_FIELDS.values():
                    total_revenue[v] += payment_line[v]
                    total_balance[v] += payment_line[v]
            elif payment_line.type == 'expense':
                for v in MONTH_FIELDS.values():
                    total_expenses[v] += payment_line[v]
                    total_balance[v] -= payment_line[v]
        
        #On récupère les montants des recettes, dépenses et bilans des ventes et achats
        for so_po_line in treasury.sale_purchase_list_ids:
            if so_po_line.type == 'revenue':
                for v in MONTH_FIELDS.values():
                    total_revenue[v] += so_po_line[v]
                    total_balance[v] += so_po_line[v]
            elif so_po_line.type == 'expense':
                for v in MONTH_FIELDS.values():
                    total_expenses[v] += so_po_line[v]
                    total_balance[v] -= so_po_line[v]
        
        #On récupère les montants des recettes, dépenses et bilans des saisies manuelles
        for manual_line in treasury.manual_treasury_list_ids:
            if manual_line.type == 'revenue':
                for v in MONTH_FIELDS.values():
                    total_revenue[v] += manual_line[v]
                    total_balance[v] += manual_line[v]
            elif manual_line.type == 'expense':
                for v in MONTH_FIELDS.values():
                    total_expenses[v] += manual_line[v]
                    total_balance[v] -= manual_line[v]
        
        #On fait le cumul de la balance à partir du solde initial saisi
        for acc_month in month_list:
            initial_balance += total_balance[acc_month]
            total_accumul_balance[acc_month] = initial_balance
        
        #On recherche les éventuelles lignes déjà existantes liées à la trésorerie 
        old_lines_ids = self.search([('treasury_id', '=', treasury.id)])
        if old_lines_ids:
            for line in old_lines_ids:
                if line.type == 'revenue':
                    line.write(total_revenue)
                elif line.type == 'expense':
                    line.write(total_expenses)
                elif line.type == 'balance_sheet':
                    line.write(total_balance)
                elif line.type == 'accumulation_balance':
                    line.write(total_accumul_balance)
        else:
            #S'il n'en existe pas, on crée les 4 lignes correspondantes
            #Ligne de recette
            vals = {'name': _('Revenue'), 'sequence': 1, 'type': 'revenue',
                     'treasury_id': treasury.id}
            vals.update(total_revenue)
            self.create(vals)
            #Ligne de dépense
            vals = {'name': _('Expenses'), 'sequence': 2, 'type': 'expense',
                     'treasury_id': treasury.id}
            vals.update(total_expenses)
            self.create(vals)
            #Ligne de bilan
            vals = {'name': _('Balance sheet'), 'sequence': 3, 'type': 'balance_sheet',
                     'treasury_id': treasury.id}
            vals.update(total_balance)
            self.create(vals)
            #Ligne de bilan cumulé
            vals = {'name': _('Accumulation balance'), 'sequence': 4, 'type': 'accumulation_balance',
                     'treasury_id': treasury.id}
            vals.update(total_accumul_balance)
            self.create(vals)
            
        return True
    
    
    
class manual_treasury(models.Model):
    """ 
        Manual expenses and revenue for treasury
    """
    _name = 'manual.treasury'
    _description = 'Manual expenses and revenue for treasury'
    _order = 'sequence asc'
    
    @api.model
    def _type_get(self):
        return [
                ('revenue', _('Revenue')),
                ('expense', _('Expense')),
                       ]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char('Name', required=True, size=24)
    sequence = fields.Integer(string='Sequence', default=0, required=True)
    type = fields.Selection('_type_get', string='Type', required=True)
    month1 = fields.Float(string='Month 1', default=0.0, required=False)
    month2 = fields.Float(string='Month 2', default=0.0, required=False)
    month3 = fields.Float(string='Month 3', default=0.0, required=False)
    month4 = fields.Float(string='Month 4', default=0.0, required=False)
    month5 = fields.Float(string='Month 5', default=0.0, required=False)
    month6 = fields.Float(string='Month 6', default=0.0, required=False)
    month7 = fields.Float(string='Month 7', default=0.0, required=False)
    month8 = fields.Float(string='Month 8', default=0.0, required=False)
    month9 = fields.Float(string='Month 9', default=0.0, required=False)
    month10 = fields.Float(string='Month 10', default=0.0, required=False)
    month11 = fields.Float(string='Month 11', default=0.0, required=False)
    month12 = fields.Float(string='Month 12', default=0.0, required=False)
    treasury_id = fields.Many2one('treasury', string='Treasury', required=False, ondelete='cascade')
    
    _sql_constraints = [
        ('unique_type', 'unique(type, treasury_id)', 'Error: You can\'t have two lines with the same type.'),
    ]
    
    
    
class manual_budget_treasury(models.Model):
    """ 
        Manual expenses and revenue for budget
    """
    _name = 'manual.budget.treasury'
    _description = 'Manual expenses and revenue for budget'
    _order = 'sequence asc'
    
    @api.model
    def _type_get(self):
        return [
                ('budget_revenue', _('Budget Revenue')),
                ('budget_expense', _('Budget Expense')),
                       ]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char('Name', required=True, size=24)
    sequence = fields.Integer(string='Sequence', default=0, required=True)
    type = fields.Selection('_type_get', string='Type', required=True)
    month1 = fields.Float(string='Month 1', default=0.0, required=False)
    month2 = fields.Float(string='Month 2', default=0.0, required=False)
    month3 = fields.Float(string='Month 3', default=0.0, required=False)
    month4 = fields.Float(string='Month 4', default=0.0, required=False)
    month5 = fields.Float(string='Month 5', default=0.0, required=False)
    month6 = fields.Float(string='Month 6', default=0.0, required=False)
    month7 = fields.Float(string='Month 7', default=0.0, required=False)
    month8 = fields.Float(string='Month 8', default=0.0, required=False)
    month9 = fields.Float(string='Month 9', default=0.0, required=False)
    month10 = fields.Float(string='Month 10', default=0.0, required=False)
    month11 = fields.Float(string='Month 11', default=0.0, required=False)
    month12 = fields.Float(string='Month 12', default=0.0, required=False)
    treasury_id = fields.Many2one('treasury', string='Treasury', required=False, ondelete='cascade')
    
    _sql_constraints = [
        ('unique_type', 'unique(type, treasury_id)', 'Error: You can\'t have two lines with the same type.'),
    ]
    
    
    
class sale_purchase_treasury(models.Model):
    """ 
        Sales and purchases in progress for the treasury
    """
    _name = 'sale.purchase.treasury'
    _description = 'Sales and purchases in progress for the treasury'
    
    @api.model
    def _type_get(self):
        return [
                ('revenue', _('Revenue')),
                ('expense', _('Expense')),
                ('balance_sheet', _('Balance sheet')),
                       ]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char('Name', required=True, size=24)
    sequence = fields.Integer(string='Sequence', default=0, required=True)
    type = fields.Selection('_type_get', string='Type')
    month1 = fields.Float(string='Month 1', default=0.0, required=False)
    month2 = fields.Float(string='Month 2', default=0.0, required=False)
    month3 = fields.Float(string='Month 3', default=0.0, required=False)
    month4 = fields.Float(string='Month 4', default=0.0, required=False)
    month5 = fields.Float(string='Month 5', default=0.0, required=False)
    month6 = fields.Float(string='Month 6', default=0.0, required=False)
    month7 = fields.Float(string='Month 7', default=0.0, required=False)
    month8 = fields.Float(string='Month 8', default=0.0, required=False)
    month9 = fields.Float(string='Month 9', default=0.0, required=False)
    month10 = fields.Float(string='Month 10', default=0.0, required=False)
    month11 = fields.Float(string='Month 11', default=0.0, required=False)
    month12 = fields.Float(string='Month 12', default=0.0, required=False)
    treasury_id = fields.Many2one('treasury', string='Treasury', required=False, ondelete='cascade')
    
    _sql_constraints = [
        ('unique_type', 'unique(type, treasury_id)', 'Error: You can\'t have two lines with the same type.'),
    ]
    
    def compute_revenue(self, start_date, end_date, match_month):
        """
            Fonction permettant de calculer le montant des revenus des ventes en cours.
            Pour ça, on prend le montant total des ventes en cours entre les deux dates et
            on retire le montant payé de ces ventes
            :param start_date: La date de début de recherche (en général, le premier jour de l'année)
            :type start_date: Date
            :param end_date: La date de fin de recherche (en général, le dernier jour de l'année)
            :type end_date: Date
            :return: Le montant des revenus pour chaque mois, et le montant du solde pour chaque mois
            :rtype: dict
        """
        revenue = {
                    'month1': 0,
                    'month2': 0,
                    'month3': 0,
                    'month4': 0,
                    'month5': 0,
                    'month6': 0,
                    'month7': 0,
                    'month8': 0,
                    'month9': 0,
                    'month10': 0,
                    'month11': 0,
                    'month12': 0,
                    }
        expenses = {
                    'month1': 0,
                    'month2': 0,
                    'month3': 0,
                    'month4': 0,
                    'month5': 0,
                    'month6': 0,
                    'month7': 0,
                    'month8': 0,
                    'month9': 0,
                    'month10': 0,
                    'month11': 0,
                    'month12': 0,
                    }
        balance = {
                    'month1': 0,
                    'month2': 0,
                    'month3': 0,
                    'month4': 0,
                    'month5': 0,
                    'month6': 0,
                    'month7': 0,
                    'month8': 0,
                    'month9': 0,
                    'month10': 0,
                    'month11': 0,
                    'month12': 0,
                    }
        invoice_list = []
        start_date = fields.Date.from_string(start_date)
        #On recherche toutes les ventes en cours de l'année
        sale_rcs = self.env['sale.order'].search([('requested_date', '>=', start_date), 
                                                  ('requested_date', '<=', end_date), 
                                                  ('state', '=', 'progress')])
        #On parcourt les lignes de vente afin d'incrémenter le montant de la recette
        for sale in sale_rcs:
            #Pour la date, on récupère la date demandée de la vente à laquelle on applique le délai
            #en jours des conditions de paiement de la vente.
            date = sale.requested_date
            payment_term = sale.payment_term_id
            amount = sale.total_amount
            pterm_list = payment_term.compute(value=amount, date_ref=date)
            if pterm_list and amount > 0:
                new_date = max(line[0] for line in pterm_list)[0]
            else:
                new_date = date
            
            #On vérifie que la date est toujours dans l'année
            if new_date <= end_date:
                month = fields.Date.from_string(new_date).month
                for line in sale.order_line_ids:
                    revenue[match_month[month]] += line.total_price
                    balance[match_month[month]] += line.total_price
                    #On recherche les lignes de facture affectées à cette ligne de vente 
                    invoice_line_rcs = self.env['account.invoice.line'].search([('sale_order_line_id', '=', line.id)])
                    #On récupère le montant payé de la facture (une seule fois par facture) et 
                    #on le soustrait au montant des ventes en cours
                    for invoice_line in invoice_line_rcs:
                        invoice_rcs = invoice_line.invoice_id
                        if not invoice_rcs in invoice_list:
                            if invoice_rcs.type == 'out_refund':
                                refund_amount = invoice_rcs.residual
                                expenses[match_month[month]] += refund_amount
                                balance[match_month[month]] -= refund_amount
                            elif invoice_rcs.state != 'draft':
                                invoice_paid_amount = invoice_rcs.amount_total - invoice_rcs.residual
                                revenue[match_month[month]] -= invoice_paid_amount
                                balance[match_month[month]] -= invoice_paid_amount
                                
                                invoice_list.append(invoice_rcs)
                
                #On ajoute également les taxes (non visibles sur les lignes)
                revenue[match_month[month]] += sale.taxes
                balance[match_month[month]] += sale.taxes
                    
        return revenue, expenses, balance
    
    
    def compute_expense(self, start_date, end_date, revenue, expenses, balance, match_month):
        """
            Fonction permettant de calculer le montant des dpenses des achats en cours.
            Pour ça, on prend le montant total des achats en cours entre les deux dates et
            on retire le montant payé de ces achats
            :param start_date: La date de début de recherche (en général, le premier jour de l'année)
            :type start_date: Date
            :param end_date: La date de fin de recherche (en général, le dernier jour de l'année)
            :type end_date: Date
            :param revenue: Un dictionnaire contenant la valeur des revenues pour chaque mois
            :type revenue: dict
            :param expenses: Un dictionnaire contenant la valeur des dépenses pour chaque mois
            :type expenses: dict
            :param balance: Un dictionnaire contenant la valeur du solde pour chaque mois
            :type balance: dict
            :return: Le montant des dépenses pour chaque mois
            :rtype: dict
        """
        invoice_list = []
        start_date = fields.Date.from_string(start_date)
        #On recherche tous les achats en cours de l'année
        purchase_rcs = self.env['purchase.order'].search([('state', '=', 'progress'),
                                                          ('purchase_type', '!=', 'open'),
                                                          ('expected_date', '>=', start_date), 
                                                          ('expected_date', '<=', end_date)])
        #On parcourt les lignes d'achat afin d'incrémenter le montant des dépenses
        for purchase in purchase_rcs:
            refund_amount = 0
            invoice_paid_amount = 0
            #Pour la date, on récupère la date demandée de l'achat à laquelle on applique le délai
            #en jours des conditions de paiement de l'achat.
            date = purchase.expected_date
            payment_term = purchase.payment_term_id
            amount = purchase.total_amount
            pterm_list = payment_term.compute(value=amount, date_ref=date)
            if pterm_list and amount > 0:
                new_date = max(line[0] for line in pterm_list)[0]
            else:
                new_date = date
                
            #On vérifie que la date est toujours dans l'année
            if new_date <= end_date:
                month = fields.Date.from_string(new_date).month
                for line in purchase.purchase_order_line_ids:
                    expenses[match_month[month]] += line.total_price
                    balance[match_month[month]] -= line.total_price
                    #On recherche les lignes de facture affectées à cette ligne d'achat
                    invoice_line_rcs = self.env['account.invoice.line'].search([('purchase_order_line_id', '=', line.id)])
                    #On récupère le montant payé de la facture (une seule fois par facture) et 
                    #on le soustrait au montant des achats en cours
                    for invoice_line in invoice_line_rcs:
                        invoice_rcs = invoice_line.invoice_id
                        if not invoice_rcs in invoice_list:
                            if invoice_rcs.type == 'in_refund':
                                refund_amount = invoice_rcs.residual
                                revenue[match_month[month]] += refund_amount
                                balance[match_month[month]] += refund_amount
                            elif invoice_rcs.state != 'draft':
                                invoice_paid_amount = invoice_rcs.amount_total - invoice_rcs.residual
                                expenses[match_month[month]] -= invoice_paid_amount
                                balance[match_month[month]] += invoice_paid_amount
                                
                                invoice_list.append(invoice_rcs)
                
                #On ajoute également les taxes (non visibles sur les lignes)
                expenses[match_month[month]] += purchase.taxes
                balance[match_month[month]] -= purchase.taxes
            
        return revenue, expenses, balance
    
        
    def compute_sale_purchase(self, treasury_id, date_from):
        """
            Fonction permettant de calculer et de créer les lignes de ventes et achats en cours et
            du bilan des ventes et achats
            :param treasury_id: L'id de la trésorerie à assigner à la ligne
            :type treasury_id: integer
            :param date_from: Date de début pour la recherche des achats et ventes
            :type date_from: string
            :return: True
            :rtype: boolean
        """
        start_date_form = fields.Date.from_string(date_from) 
        start_month = start_date_form.month
        start_date = '%s-%s-01'%(start_date_form.year, start_month)
        end_date_form = start_date_form + relativedelta(months=12)
        end_date = fields.Date.to_string(end_date_form)
        match_month = {}
        x = 1
        #On crée un dictionnaire nous permettant de faire correspondre les numéro de mois
        while x <= 12:
            match_month[start_month] = 'month%s'%(x)
            start_month = (start_date_form + relativedelta(months=x)).month
            x += 1
            
        revenue, expenses, balance = self.compute_revenue(start_date, end_date, match_month)
        revenue, expenses, balance = self.compute_expense(start_date, end_date, revenue, expenses, balance, match_month)
        #On recherche les éventuelles lignes déjà existantes liées à la trésorerie 
        old_lines_ids = self.search([('treasury_id', '=', treasury_id)])
        if old_lines_ids:
            for line in old_lines_ids:
                if line.type == 'revenue':
                    line.write(revenue)
                elif line.type == 'expense':
                    line.write(expenses)
                elif line.type == 'balance_sheet':
                    line.write(balance)
        else:
            #S'il n'en existe pas, on crée les 3 lignes correspondantes
            #Ligne de recette
            vals = {'name': _('Revenue'), 'sequence': 1, 'type': 'revenue',
                     'treasury_id': treasury_id}
            vals.update(revenue)
            self.create(vals)
            #Ligne de dépense
            vals = {'name': _('Expenses'), 'sequence': 2, 'type': 'expense',
                     'treasury_id': treasury_id}
            vals.update(expenses)
            self.create(vals)
            #Ligne de bilan
            vals = {'name': _('Balance sheet'), 'sequence': 3, 'type': 'balance_sheet',
                     'treasury_id': treasury_id}
            vals.update(balance)
            self.create(vals)
            
        return True
    
    
    
class payment_treasury(models.Model):
    """ 
        Payments for the treasury
    """
    _name = 'payment.treasury'
    _description = 'Treasury'
    
    @api.model
    def _type_get(self):
        return [
                ('revenue', _('Revenue')),
                ('expense', _('Expense')),
                ('balance_sheet', _('Balance sheet')),
                       ]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char('Name', required=True, size=24)
    sequence = fields.Integer(string='Sequence', default=0, required=True)
    type = fields.Selection('_type_get', string='Type')
    month1 = fields.Float(string='Month 1', default=0.0, required=False)
    month2 = fields.Float(string='Month 2', default=0.0, required=False)
    month3 = fields.Float(string='Month 3', default=0.0, required=False)
    month4 = fields.Float(string='Month 4', default=0.0, required=False)
    month5 = fields.Float(string='Month 5', default=0.0, required=False)
    month6 = fields.Float(string='Month 6', default=0.0, required=False)
    month7 = fields.Float(string='Month 7', default=0.0, required=False)
    month8 = fields.Float(string='Month 8', default=0.0, required=False)
    month9 = fields.Float(string='Month 9', default=0.0, required=False)
    month10 = fields.Float(string='Month 10', default=0.0, required=False)
    month11 = fields.Float(string='Month 11', default=0.0, required=False)
    month12 = fields.Float(string='Month 12', default=0.0, required=False)
    treasury_id = fields.Many2one('treasury', string='Treasury', required=False, ondelete='cascade')
    
    _sql_constraints = [
        ('unique_type', 'unique(type, treasury_id)', 'Error: You can\'t have two lines with the same type.'),
    ]
    
    
    def compute_payments(self, treasury_id, date_from):
        """
            Fonction permettant de calculer et de créer les lignes de recette, dépense et bilan
            des paiements
            :param treasury_id: L'id de la trésorerie à assigner à la ligne
            :type treasury_id: integer
            :param date_from: Date de début pour la recherche des paiements
            :type date_from: string d'une date
            :return: True
            :rtype: boolean
        """
        revenue = {
                    'month1': 0,
                    'month2': 0,
                    'month3': 0,
                    'month4': 0,
                    'month5': 0,
                    'month6': 0,
                    'month7': 0,
                    'month8': 0,
                    'month9': 0,
                    'month10': 0,
                    'month11': 0,
                    'month12': 0,
                    }
        expenses = {
                    'month1': 0,
                    'month2': 0,
                    'month3': 0,
                    'month4': 0,
                    'month5': 0,
                    'month6': 0,
                    'month7': 0,
                    'month8': 0,
                    'month9': 0,
                    'month10': 0,
                    'month11': 0,
                    'month12': 0,
                    }
        balance = {
                    'month1': 0,
                    'month2': 0,
                    'month3': 0,
                    'month4': 0,
                    'month5': 0,
                    'month6': 0,
                    'month7': 0,
                    'month8': 0,
                    'month9': 0,
                    'month10': 0,
                    'month11': 0,
                    'month12': 0,
                    }
        match_month = {}
        x = 1
        start_date_form = fields.Date.from_string(date_from) 
        start_month = start_date_form.month
        start_date = '%s-%s-01'%(start_date_form.year, start_month)
        #On crée un dictionnaire nous permettant de faire correspondre les numéro de mois
        while x <= 12:
            match_month[start_month] = 'month%s'%(x)
            start_month = (start_date_form + relativedelta(months=x)).month
            x+= 1
            
        end_date_form = start_date_form + relativedelta(months=12)
        end_date = fields.Date.to_string(end_date_form)
        #On recherche tous les payments faits 
        payments_ids = self.env['account.voucher.line'].search([('voucher_id.date', '>=', start_date), 
                                                                ('voucher_id.date', '<=', end_date)])
        #On récupère la somme des recettes et des dépenses pour chaque mois
        for payment in payments_ids:
            month = fields.Date.from_string(payment.voucher_id.date).month
            if payment.type == 'dr':
                expenses[match_month[month]] += payment.amount
                balance[match_month[month]] -= payment.amount
            elif payment.type == 'cr':
                revenue[match_month[month]] += payment.amount
                balance[match_month[month]] += payment.amount
            
        
        #On recherche les éventuelles lignes déjà existantes liées à la trésorerie 
        old_lines_ids = self.search([('treasury_id', '=', treasury_id)])
        if old_lines_ids:
            for line in old_lines_ids:
                if line.type == 'revenue':
                    line.write(revenue)
                elif line.type == 'expense':
                    line.write(expenses)
                elif line.type == 'balance_sheet':
                    line.write(balance)
        else:
            #S'il n'en existe pas, on crée les 3 lignes correspondantes
            #Ligne de recette
            vals = {'name': _('Revenue'), 'sequence': 1, 'type': 'revenue',
                     'treasury_id': treasury_id}
            vals.update(revenue)
            self.create(vals)
            #Ligne de dépense
            vals = {'name': _('Expenses'), 'sequence': 2, 'type': 'expense',
                     'treasury_id': treasury_id}
            vals.update(expenses)
            self.create(vals)
            #Ligne de bilan
            vals = {'name': _('Balance sheet'), 'sequence': 3, 'type': 'balance_sheet',
                     'treasury_id': treasury_id}
            vals.update(balance)
            self.create(vals)
            
        return True
    
    
    
class treasury(models.Model):
    """ 
        Object for the treasury
    """
    _name = 'treasury'
    _description = 'Treasury'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char('Name', required=True)
    year = fields.Integer(string='Year', default=0, required=True)
    manager_id = fields.Many2one('res.users', string='Manager', required=False, ondelete='restrict')
    date_from = fields.Date(string='Date from', required=True, help='The start date for treasury calculation. The system start his calcucation from the'
                            ' month of this date')
    initial_balance = fields.Float(string='Initial balance', default=0.0, required=True, help='This is the start amount for the line '
                                   '"Accumulation balance sheet" of the treasury summary')
    payment_list_ids = fields.One2many('payment.treasury', 'treasury_id',  string='Payment list', readonly=True)
    sale_purchase_list_ids = fields.One2many('sale.purchase.treasury', 'treasury_id',  string='Sales and purchases list', readonly=True, 
                                             help="To compute the revenue's amounts, we take the amount of all sales in state 'progress' and we remove "
                                             "the sum of all the amounts paid for this sales. To find this sales, we take the requested date to which we "
                                             "add the paiement delay. \n"
                                             "To compute the expense's amounts, we take the amount of all purchases in state 'progress' and we remove "
                                             "the sum of all the amounts paid for this purchases. To find this purchases, we take the requested date to "
                                             "which we add the paiement delay. ")
    manual_treasury_list_ids = fields.One2many('manual.treasury', 'treasury_id',  string='Manual list')
    manual_budget_list_ids = fields.One2many('manual.budget.treasury', 'treasury_id',  string='Budget list')
    summary_list_ids = fields.One2many('treasury.summary', 'treasury_id',  string='Summary list', readonly=True)
    budget_summary_ids = fields.One2many('budget.treasury.summary', 'treasury_id',  string='Budget summary list', readonly=True)
    
    @api.multi
    def compute_payment_list(self):
        """
            Fonction qui calcule les payments fait sur l'année sélectionnée
        """
        for treasury in self:
            if treasury.date_from:
                self.env['payment.treasury'].compute_payments(treasury.id, treasury.date_from)
                  
        return True
    
    
    @api.multi
    def compute_sale_purchase_list(self):
        """
            Fonction qui calcule le montant des ventes et achats en cours
        """
        for treasury in self:
            if treasury.date_from:
                self.env['sale.purchase.treasury'].compute_sale_purchase(treasury.id, treasury.date_from)
                  
        return True
    
    
    @api.multi
    def compute_summary(self):
        """
            Fonction qui calcule la synthèse de l'année de trésorerie
        """
        for treasury in self:
            if treasury.date_from:
                self.env['treasury.summary'].compute_treasury_summary(treasury)
                  
        return True
    
    
    @api.multi
    def compute_budget_summary(self):
        """
            Fonction qui calcule la synthèse de l'année de trésorerie
        """
        for treasury in self:
            if treasury.date_from:
                self.env['budget.treasury.summary'].compute_budget_treasury_summary(treasury)
                  
        return True
    
    
