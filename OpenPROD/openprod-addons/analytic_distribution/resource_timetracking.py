# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from compute_amount import compute_amount
from openerp.exceptions import ValidationError


class resource_timetracking(models.Model):
    _inherit = 'resource.timetracking'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    analytic_distribution_id = fields.Many2one('product.analytic.distribution', string='Analytic distribution', required=False, ondelete='restrict')
    analytic_line_ids = fields.One2many('account.analytic.line', 'timetracking_id',  string='Analytic lines')
    
    def _timesheet_fields_list(self):
        res = super(resource_timetracking, self)._timesheet_fields_list()
        res.append('analytic_distribution_id')
        return res
    
    
    def compute_analytic_line_time(self, distrib_line, analytic_distribution_rcs, total_amount_time=0):
        """
            Fonction permettant de calculer le montant de la ligne de distribution analytique en 
            fonction du montant de la ligne
        """
        total = 0
        if distrib_line.type == 'garbage':
            total_amount = sum([compute_amount(l.type, l.value, total_amount_time) 
                                for l in analytic_distribution_rcs.distribution_ids if l.type != 'garbage'])
            total = total_amount_time - total_amount
        else:
            total = compute_amount(distrib_line.type, distrib_line.value, total_amount_time)
        
        return total
    
    
    @api.multi
    def create_analytic_lines(self, analytic_distribution_rcs=False, product_rcs=False):
        """
            Fonction qui crée des lignes analytiques en fonction d'une distribution, et qui les
            lie aux lignes de temps
            :type self: resource.timetracking
            :param analytic_distribution_rcs: La distribution analytique à appliquer
            :type analytic_distribution_rcs: recordset: product.analytic.distribution
            :param product_rcs: Le produit utilisé pour le compte général
            :type product_rcs: recordset: product.product
            :return: True
            :rtype: boolean
        """
        if analytic_distribution_rcs and product_rcs:
            analytic_distribution_id = analytic_distribution_rcs.id
            analytic_line_obj = self.env['account.analytic.line']
            #On recherche le journal analytique lié aux lignes de temps
            timetracking_journal_ids = self.env['account.journal'].search([('is_timetracking_journal', '=', True)], limit=1).ids
            if not timetracking_journal_ids:
                raise ValidationError(_("There is no journal for timetracking, you must check the field 'Timetracking journal' in a journal"))
            
            if not product_rcs.property_account_expense_id:
                raise ValidationError(_("The selected product must have an expense account"))
            
            #Valeurs globales des lignes analytiques
            global_line_vals = {}
            for distribution_line in analytic_distribution_rcs.distribution_ids:
                global_line_vals[distribution_line]= {'account_id': distribution_line.account_id and distribution_line.account_id.id or False,
                                                      'user_id': self.env.uid,
                                                      'general_account_id': product_rcs.property_account_expense_id.id,
                                                      'journal_id': timetracking_journal_ids[0],
                                                      'product_id': product_rcs.id,
                                                      }
            
            for time_line in self:
                analytic_line_rcs = self.env['account.analytic.line']
                time_line_name = time_line.name
                #On récupère le coût horaire de la ressource pour calculer le total de la ligne de temps
                hourly_rate = time_line.resource_id and time_line.resource_id.hourly_rate or 0
                total_time_line_amount = time_line.time * hourly_rate
                #On crée une ligne pour chaque ligne de la distribution analytique
                for distrib_line in global_line_vals:
                    line_amount = self.compute_analytic_line_time(distrib_line, analytic_distribution_rcs, total_time_line_amount)
                    vals = {'name': time_line_name,
                            'amount': line_amount,
                            'timetracking_id': time_line.id,
                            'price_unit': hourly_rate}
                    vals.update(global_line_vals[distrib_line])
                    analytic_line_rcs += analytic_line_obj.create(vals)
                
                time_line.write({'analytic_distribution_id': analytic_distribution_id})
                
        return True
    
    
    @api.multi
    def delete_analytic_lines(self):
        """
            Fonction qui supprime toutes les lignes analytiques liées aux lignes de temps
        """
        for timetracking in self:
            timetracking.analytic_line_ids.unlink()
                    
        return True
    