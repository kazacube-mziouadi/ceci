# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
import string
import datetime
from datetime import timedelta
from openerp.addons.base_openprod.common import get_form_view
from openerp.addons.base_openprod.common import roundingUp, rounding
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
import re
from decimal import Decimal
from operator import itemgetter


def count_letter():
    res = {i: str(i) for i in range(10)}
    res.update({string.ascii_lowercase.index(x) + 11: x for x in string.ascii_lowercase})
    return res
    
_COUNT_LETTER = count_letter()
_LEVEL_NUMBER = 50


class mrp_routing_line(models.Model):
    """
    Routing line
    """
    _name = 'mrp.routing.line'
    _description = 'Routing line'
    _order = 'sequence asc'
    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('active', _('Active')),
                ('obsolete', _('Obsolete')),
                       ]

    
    @api.multi
    def name_get(self):
        """
            Name get de la mrp_operation_consumed [seq_routing_line] name_routing_line
        """
        result = []
        for event in self:
            if event.name and event.sequence:
                name = '[%s] %s'%(event.sequence, event.name)
            else:
                name = event.name
                
            result.append((event.id, name))
            
        return result
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    @api.one
    @api.depends('rl_resource_category_ids', 'rl_resource_category_ids.category_id', 'rl_resource_category_ids.rl_resource_ids',
                 'rl_resource_category_ids.rl_resource_ids.resource_id')
    def _compute_resource(self):
        """
            Calcul la première ressource et sa catégorie
        """
        rl_category = self.env['mrp.rl.resource.category'].search([('routing_line_id', '=', self.id)], order='sequence asc', limit=1)
        self.first_category_id = rl_category and rl_category.category_id and rl_category.category_id.id or False
        rl_resource_val = False
        if rl_category:
            rl_resource = self.env['mrp.rl.resource'].search([('rl_category_id', '=', rl_category.id)], order='sequence asc', limit=1)
            rl_resource_val = rl_resource and rl_resource.resource_id and rl_resource.resource_id.id or False
             
        self.first_resource_id = rl_resource_val


    @api.one
    def _compute_time(self):
        """
            Temps de la gamme
        """
        preparation_time = 0.0
        list_masked_preparation_time = []
        production_time = 0.0
        list_masked_production_time = []
        cleaning_time = 0.0
        list_masked_cleaning_time = []
        
        dico = self._function_time(preparation_time, list_masked_preparation_time, production_time, list_masked_production_time, 
                                    cleaning_time, list_masked_cleaning_time)
        
        preparation_time = dico['preparation_time']
        list_masked_preparation_time = dico['list_masked_preparation_time']
        production_time = dico['production_time']
        list_masked_production_time = dico['list_masked_production_time']
        cleaning_time = dico['cleaning_time']
        list_masked_cleaning_time = dico['list_masked_cleaning_time']
        
        self.preparation_time = preparation_time
        self.production_time = production_time
        self.cleaning_time = cleaning_time
        nb_product_parallel = self.nb_product_parallel or 1.0
        price_qty = self.routing_id and self.routing_id.price_qty or 1.0
        self.total_time = round((preparation_time + (production_time * price_qty / nb_product_parallel + cleaning_time)), 4)
        self.total_time_produce = (production_time * price_qty / nb_product_parallel)
        self.total_time_unit = self.total_time / price_qty
        
        
    @api.one
    def _compute_max_sequence_category(self):
        """
            Séquence max
        """
        line_ids = self.env['mrp.rl.resource.category'].search([('routing_line_id', '=', self.id)], order='sequence desc', limit=1)
        self.max_sequence_category = line_ids and line_ids.sequence + 10 or 10
    
    
    @api.one
    @api.depends('routing_id', 'routing_id.state')
    def _compute_routing_state(self):
        """
            Calcul de l'etat de la gamme
        """
        self.routing_state = self.routing_id and self.routing_id.state or ''
        self.price_qty = self.routing_id and self.routing_id.price_qty or ''
        
    
    #Entête
    routing_id = fields.Many2one('mrp.routing', string='Routing', required=False, ondelete='Cascade')
    name = fields.Char(required=True)
    sequence = fields.Integer(string='Sequence', default=0, required=True)
    product_id = fields.Many2one('product.product', string='Product', default= lambda self: self.env.ref('mrp.int_product_PCE') , required=True, ondelete='restrict')
    nb_product_parallel = fields.Float(string='Number of products in parallel', default=1.0, required=False, digits=dp.get_precision('Product quantity'))
    efficiency = fields.Float(string='Efficiency', default=1.0, digits=dp.get_precision('Product quantity'), required=False)
    waiting_time_next_ope = fields.Float(string='Waiting time for the next operation', default=1.0, required=False, digits=dp.get_precision('Product quantity'))
    percentage_overlap_next_ope = fields.Float(string='% of overlap with the next operation', default=0.0, required=False)
    option_id = fields.Many2one('mrp.option', string='Option', required=False, ondelete='restrict')
    total_cost = fields.Float(string='Total cost', digits=dp.get_precision('Product price'))
    unit_cost = fields.Float(string='Unit cost', digits=dp.get_precision('Price technical'))
    first_category_id = fields.Many2one('mrp.resource.category', string='First category resource', compute='_compute_resource')
    first_resource_id = fields.Many2one('mrp.resource', string='First resource', compute='_compute_resource', store=True)
    preparation_time = fields.Float(string='Preparation time', compute='_compute_time', digits=dp.get_precision('Time'))
    production_time = fields.Float(string='Production time', compute='_compute_time', digits=dp.get_precision('Time'))
    cleaning_time = fields.Float(string='Cleaning time', compute='_compute_time', digits=dp.get_precision('Time'))
    total_time = fields.Float(string='Total time', compute='_compute_time', digits=dp.get_precision('Time'))
    total_time_produce = fields.Float(string='Total time produce', compute='_compute_time', digits=dp.get_precision('Time'), help='mrp_routing_line.total_time_produce.help')
    total_time_unit = fields.Float(string='Total time unit', compute='_compute_time', digits=dp.get_precision('Time'))
    is_forecast_time = fields.Boolean(string='Forecast time', default=False)
    is_line_category = fields.Boolean(string='Line category', default=False)
    routing_state = fields.Selection('_state_get', string='State', compute='_compute_routing_state', store=True)
    price_qty = fields.Float("Price Qty", digits=dp.get_precision('Price technical'), compute='_compute_routing_state', store=True)
    #Catégorie de ressource
    is_supplier_delay_subc = fields.Boolean(string='Supplier delay for subcontracting', default=False)
    rl_resource_category_ids = fields.One2many('mrp.rl.resource.category', 'routing_line_id', string='Resource category', copy=True)
    max_sequence_category = fields.Integer(string='Max sequence', default=10, compute='_compute_max_sequence_category')

    #Produit consommé
    consumed_component_ids = fields.Many2many('mrp.bom', 'mrp_routing_line_mrp_bom_rel', 'routing_line_id', 'bom_id', string='Components')
    
    #Service consommé
    consumed_service_ids = fields.One2many('mrp.rl.consumed.service', 'routing_line_id',  string='Consumed service', copy=True)
    
    #Outillage utilisé
    tool_ids = fields.One2many('mrp.rl.tools', 'routing_line_id',  string='Tools', copy=True)
    
    #Réclamation
    complaint_ids = fields.Many2many('mrp.rl.complaint', 'mrp_rl_complaint_mrp_routing_line_rel', 'routing_line_id', 'complaint_id', string='Complaint')
    
    #Document
    document_ids = fields.Many2many('document.openprod', 'mrp_rl_document_openprod_rel', 'mrp_rl_id', 'document_id', 
                                         string='Documents', copy=False)
    
    #Consigne
    consign_ids = fields.One2many('mrp.rl.consign', 'routing_line_id',  string='Consigns', copy=True)
    
    #Quality Control
    quality_control_ids = fields.One2many('quality.control.product', 'routing_line_id',  string='Quality Control')
    
    #History cost
    rl_cost_history_ids = fields.One2many('mrp.rl.cost.history', 'rl_id',  string='Cost history')
    base_coeff = fields.Float(string='Coefficient', default=1.0, required=False)
    price_total_coeff = fields.Float(string='Total price with coefficient', default=1.0, required=False, digits=dp.get_precision('Price technical'))
    unit_cost_coeff = fields.Float(string='Unit cost with coefficient', digits=dp.get_precision('Price technical'))
    #===========================================================================
    # Onchange
    #===========================================================================
    
    @api.onchange('rl_resource_category_ids')
    def _onchange_rl_resource_category_ids(self):
        """
            Calcul séquence
        """
        seq_list = [line.sequence for line in self.rl_resource_category_ids]
        if seq_list:
            max_sequence_category = max(seq_list)
            self.is_line_category = True
        else:
            max_sequence_category = 0
            self.is_line_category = False

        self.max_sequence_category = max_sequence_category + 10
    
    
    @api.onchange('consumed_component_ids')
    def _onchange_consumed_component_ids(self):
        """
            Calcul séquence
        """
        list_component_consum = []
        if self.routing_id:
            for line in self.routing_id.routing_line_ids:
                if line.consumed_component_ids:
                    list_component_consum.extend([x.id for x in line.consumed_component_ids])
            
            self.routing_id.consumed_component_ids = [(6, 0, list_component_consum)]
    
    
    #===========================================================================
    # Fonction
    #===========================================================================
    def _function_time(self, preparation_time, list_masked_preparation_time, production_time, list_masked_production_time, cleaning_time, list_masked_cleaning_time):
        """
            Calcul du temps dans les lignes de gammes
        """
        rl_resource_obj = self.env['mrp.rl.resource']
        for rl_resource_category in self.rl_resource_category_ids:
            #Récupération de la première ressource
            rl_resource = rl_resource_obj.search([('rl_category_id', '=', rl_resource_category.id)], order='sequence asc', limit=1)
            
            #Calcul du temps de préparation
            if rl_resource.preparation_time:
                preparation_time += rl_resource.preparation_time * (1 - (rl_resource.preparation_masked_time/100))
                preparation_masked_time = (rl_resource.preparation_time * (rl_resource.preparation_masked_time/100))
                list_masked_preparation_time.append(preparation_masked_time)
            else:
                preparation_time += rl_resource_category.preparation_time * (1 - (rl_resource_category.preparation_masked_time/100))
                preparation_masked_time = (rl_resource_category.preparation_time * (rl_resource_category.preparation_masked_time/100))
                list_masked_preparation_time.append(preparation_masked_time)
                
            #Calcul du temps de production
            if rl_resource.production_time:
                production_time += rl_resource.production_time * (1 - (rl_resource.production_masked_time/100))
                production_masked_time = (rl_resource.production_time * (rl_resource.production_masked_time/100))
                list_masked_production_time.append(production_masked_time)
            else:
                production_time += rl_resource_category.production_time * (1 - (rl_resource_category.production_masked_time/100))
                production_masked_time = (rl_resource_category.production_time * (rl_resource_category.production_masked_time/100))
                list_masked_production_time.append(production_masked_time)
            
            #Calcul du temps de nettoyage
            if rl_resource.cleaning_time:
                cleaning_time += rl_resource.cleaning_time * (1 - (rl_resource.cleaning_masked_time/100))
                cleaning_masked_time = (rl_resource.cleaning_time * (rl_resource.cleaning_masked_time/100))
                list_masked_cleaning_time.append(cleaning_masked_time)
            else:
                cleaning_time += rl_resource_category.cleaning_time * (1 - (rl_resource_category.cleaning_masked_time/100))
                cleaning_masked_time = (rl_resource_category.cleaning_time * (rl_resource_category.cleaning_masked_time/100))
                list_masked_cleaning_time.append(cleaning_masked_time)
        
        dico = {
            'preparation_time': preparation_time,
            'list_masked_preparation_time': list_masked_preparation_time,
            'production_time': production_time,
            'list_masked_production_time': list_masked_production_time,
            'cleaning_time': cleaning_time,
            'list_masked_cleaning_time': list_masked_cleaning_time,
        }
        
        return dico
    
    
    @api.one
    @api.constrains('option_id', 'product_id', 'rl_resource_category_ids', 'rl_resource_category_ids.rl_resource_ids')
    def _check_function_time_masked(self):
        """ 
            Contrainte temps masqués
        """ 
         
        preparation_time = 0.0
        list_masked_preparation_time = []
        production_time = 0.0
        list_masked_production_time = []
        cleaning_time = 0.0
        list_masked_cleaning_time = []
         
        dico = self._function_time(preparation_time, list_masked_preparation_time, production_time, list_masked_production_time, 
                                    cleaning_time, list_masked_cleaning_time)
         
        preparation_time = dico['preparation_time']
        list_masked_preparation_time = dico['list_masked_preparation_time']
        production_time = dico['production_time']
        list_masked_production_time = dico['list_masked_production_time']
        cleaning_time = dico['cleaning_time']
        list_masked_cleaning_time = dico['list_masked_cleaning_time']
        
        #Contrainte : les temps masquées de chaque catégorie de ressource ne peut être supérieur à la Somme des temps de préparation d'une opération
        if list_masked_preparation_time:
            for masked_preparation_time in list_masked_preparation_time:
                if masked_preparation_time > preparation_time:
                    raise except_orm(_('Error'), _('Time masked in each resource category can not be superior to the sum preparing an operation times'))
         
        #Contrainte : les temps masquées de chaque catégorie de ressource ne peut être supérieur à la Somme des temps de production d'une opération
        if list_masked_production_time:
            for masked_production_time in list_masked_production_time:
                if masked_production_time > production_time:
                    raise except_orm(_('Error'), _('Time masked in each resource category can not be superior to the sum production an operation times'))

        #Contrainte : les temps masquées de chaque catégorie de ressource ne peut être supérieur à la Somme des temps de nettoyage d'une opération
        if list_masked_cleaning_time:
            for masked_cleaning_time in list_masked_cleaning_time:
                if masked_cleaning_time > cleaning_time:
                    raise except_orm(_('Error'), _('Time masked in each resource category can not be superior to the sum cleaning an operation times'))
    
    
    @api.model
    def create(self, vals=None):
        """
            Changement du state du WO par rapport à la déclaration de production
        """
        res = super(mrp_routing_line, self).create(vals=vals)
        if not res.rl_resource_category_ids:
            raise except_orm(_('Error'), _('It takes at least one resource category'))
        
        return res
    
    @api.multi
    def write(self, vals=None):
        """
            Redéfinition pour les opérations consommées
        """
        res = super(mrp_routing_line, self).write(vals=vals)
        if 'consumed_component_ids' in vals:
            routing_rcs = self.env['mrp.routing']
            for line in self:
                routing_rcs |= line.routing_id
            
            for routing in routing_rcs:
                list_component_consum = []
                for line in routing.routing_line_ids:
                    if line.consumed_component_ids:
                        list_component_consum.extend([x.id for x in line.consumed_component_ids])
                
                routing.consumed_component_ids = [(6, 0, list_component_consum)]
            
        return res
    
    
    def additional_function_domain(self, arg):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de mrp_routing_line
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
        return super(mrp_routing_line,self).search(args=args_modified, offset=offset, limit=limit, order=order, count=count) 
    
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=1000):
        """
            Fonction name_search
        """
        args.append(('name', 'ilike', name))
        args = self.compute_domain_args_resource(args)
        recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()
    
    
    #===========================================================================
    # Boutons
    #===========================================================================
    @api.multi
    def button_line_complete(self):
        for line in self:
            action = self.env.ref('mrp.act_mrp_routing_line_complete_button')
            if action:
                action = action.read()[0]
                if action.get('views'):
                    for index,item in enumerate(action['views']):
                        if item[-1] == 'form':
                            del action['views'][index]
                            action['views'].insert(0, item)
                action['res_id'] = line.id
                action['view_mode'] = 'form' 
                action['context'] = {'button_save': False}
            return action
    
    
    @api.multi
    def button_save_true(self):
        return {'type':'ir.actions.act_window_view_reload'}
    
    
    def get_vals_rl_cost_history(self, price, price_coeff, coeff):
        """
            Fonction qui permet de rajouter dans la creation d'un enregistrement dans l'historique de coût des infos (mrp_ftpr_gergonne) pour les lignes de gamme
        """
        return {}
    
    
    def compute_price_ftpr_gergonne(self, unit_cost, unit_cost_coeff):
        return unit_cost, unit_cost_coeff
    
    
    

class mrp_routing(models.Model):
    """ 
    Routing 
    """
    _name = 'mrp.routing'
    _description = 'Routing'
    _order = 'sequence asc'
    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('active', _('Active')),
                ('obsolete', _('Obsolete')),
                       ]
    
    @api.one
    def _compute_max_sequence(self):
        """
            Séquence max
        """
        line_ids = self.env['mrp.routing.line'].search([('routing_id', '=', self.id)], order='sequence desc', limit=1)
        self.max_sequence = line_ids and line_ids[0].sequence + 10 or 10
        
    @api.one
    @api.depends('bom_ids', 'bom_ids.component_total_price', 'bom_ids.state', 'price_last_date')
    def _compute_bom_first_price(self):
        """
            Prix de la première nomenclature
        """
        price = 0.0
        bom_first = False
        bom_first_uom = False
        for bom in self.bom_ids:
            if bom.state == 'active':
                bom_valid = True
                if (bom.start_date and bom.start_date > self.price_last_date) or (bom.stop_date and bom.stop_date < self.price_last_date):
                    bom_valid = False
                
                if bom_valid:
                    price = bom.price_unit
                    bom_first = bom
                    bom_first_uom = bom.uom_id
                    break
        
        self.bom_first_uom_id = bom_first_uom
        self.bom_first_id = bom_first
        self.bom_first_price = price
    
    @api.one
    def _compute_efficiency_global(self):
        """
            Calcul du pourcentage moyen de l'efficience dans les lignes
        """
        efficiency = 0.0
        for routing_line in self.routing_line_ids:
            if efficiency:
                efficiency = (routing_line.efficiency) * efficiency
            else:
                efficiency = routing_line.efficiency

        self.efficiency_global = efficiency or 1.0
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    #Entête
    name = fields.Char(required=True)
    reference = fields.Char(string='Reference', size=256, required=False)
    is_model = fields.Boolean(string='Model', default=False)
    start_date = fields.Date(string='Date Start')
    stop_date = fields.Date(string='Date Stop')
    template_id = fields.Many2one('mrp.routing', string='Model', required=False, ondelete='set null')
    price_qty = fields.Float("Price Qty", digits=dp.get_precision('Price technical'))
    state = fields.Selection('_state_get', string='State', default='draft')
    max_sequence = fields.Integer(string='Max sequence', compute='_compute_max_sequence')
    option_id = fields.Many2one('mrp.option', string='Option', required=False, ondelete='restrict')
    sequence = fields.Integer(string='Sequence', default=0, required=False)
    
    #Operations
    routing_line_ids = fields.One2many('mrp.routing.line', 'routing_id',  string='Routing lines', copy=True)
    
    #Nomenclature
    bom_ids = fields.Many2many('mrp.bom', 'mrp_bom_mrp_routing_rel', 'routing_id', 'bom_id', string='BoMs')
    consumed_component_ids = fields.Many2many('mrp.bom', 'mrp_routing_mrp_bom_rel', 'routing_id', 'bom_id', string='Components')
    
    #Modèle
    template_ids = fields.One2many('mrp.routing', 'template_id',  string='Model')
    
    #Opération consommée
    operation_consumed_ids = fields.One2many('mrp.operation.consumed', 'routing_id',  string='Operations consumed', copy=True)
    
    #Cout
    total_price = fields.Float(string='Total price', digits=dp.get_precision('Price technical'), default=0.0, required=False)
    price_unit = fields.Float(string='Price unit', default=0.0, digits=dp.get_precision('Price technical'), required=False)
    bom_first_price = fields.Float(string='BoM first price', digits=dp.get_precision('Price technical'), default=0.0, required=False, compute='_compute_bom_first_price', store=True)
    bom_first_id = fields.Many2one('mrp.bom', string='Bom first', required=False, ondelete='restrict', compute='_compute_bom_first_price', store=True)
    bom_first_uom_id = fields.Many2one('product.uom', string='Bom first UoM', required=False, ondelete='restrict', compute='_compute_bom_first_price', store=True)
    price_last_date = fields.Date(string='Price compute last date')
    company_id = fields.Many2one('res.company', string='Company', required=False, ondelete='restrict', default=lambda self: self.env.user.company_id)
    efficiency_global = fields.Float(string='Global efficiency', default=0.0, digits=dp.get_precision('Product quantity'), compute='_compute_efficiency_global', required=False)
    note_mo = fields.Text(string='Note on manufacturing')
    #History cost
    routing_cost_history_ids = fields.One2many('mrp.routing.cost.history', 'routing_id',  string='Cost history')
    price_unit_coeff = fields.Float(string='Unit price with coefficient', default=0.0, readonly=True, digits=dp.get_precision('Price technical'))
    
    is_disassembly = fields.Boolean(string='Disassembly', default=False)
    
    #===========================================================================
    # Boutons
    #===========================================================================
    
    @api.multi
    def wkf_draft(self):
        self.write({'state': 'draft'})
    
    
    @api.multi
    def wkf_active(self):
        self.write({'state': 'active'})
        if not self.env.context.get('no_compute_price', False):
            self.action_compute_price()
    
    
    @api.multi
    def wkf_obsolete(self):
        self.write({'state': 'obsolete'})
    
    # TODO thomas - changer nom de méthode franglais
    @api.multi
    def boutton_generate_op_cons(self):
        """
            pour chaque routing:
                recuperer les lignes de routing
                si il existe des lignes:
                    trier la liste des lignes par séquence
                    toutes les lignes de la séquence la + basse sont consommées par toutes les lignes de séquence supérieure
                    ex: les lignes de seq 10 sont toutes consommées par les lignes de seq 20. Si 3 lignes en seq 10 et 3 lignes en seq 20, alors 9 lignes consommées
                    seule la/les lignes(s) de séquence la + haute ne sont pas consommées
                sinon:
                    on fait rien
                    
        """
        op_cons_obj = self.env['mrp.operation.consumed']
        for routing in self:
            routing.boutton_delete_op_cons()
            lines = routing.routing_line_ids
            if lines:
                lines_r = lines.read(['sequence'])
                lines_r.sort(key=lambda x: x['sequence'])
    
                dico = {}
                for elt in lines_r:
                    if not dico.get(elt['sequence'], False):
                        dico[elt['sequence']] = [elt['id']]
                    else:
                        dico[elt['sequence']].append(elt['id'])
    
                sequences = dico.keys()
                sequences.sort()
                for i,j in enumerate(sequences):
                    for elt in dico[j]:
                        try:
                            for elt2 in dico[sequences[i+1]]:
                                vals = {
                                    'routing_id': routing.id,
                                    'operation_id': elt2,
                                    'operation_consumed_id': elt,
                                }
                                op_cons_obj.create(vals)
                        except:
                            pass
                        
        return True
    
    
    @api.multi
    def boutton_delete_op_cons(self):
        """
           Suppression operation consumed
                    
        """
        cons_ids = self.env['mrp.operation.consumed'].search([('routing_id', 'in', self.ids)])
        if cons_ids:
            cons_ids.unlink()
            
        return True
   
   
    @api.multi
    def action_compute_price(self):
        """ 
            Calcul du prix unitaire et total de la BoM, des sous produits et des composants en fonction de: BoM, Sub product, Component
        """
        for routing in self:
            routing.function_compute_price(button=True, serie_eco=routing.price_qty)
            
        return True  
    
    
    def compute_price_ftpr_gergonne(self, price_unit, price_unit_coef, total_price):
        return price_unit, price_unit_coef, total_price
    
    
    def function_compute_price(self, button=False, serie_eco=1, option_ids=[]):
        """ 
            Fonction qui permet de calculer prix unitaire et total de la gamme, de ses lignes de gammes
        """
        rl_resource_obj = self.env['mrp.rl.resource']
        price_preparation_time = 0.0
        price_production_time = 0.0
        price_cleaning_time = 0.0
        price_qty = serie_eco or 1
        total_subcontracting = 0.0
        total_preparation_time = 0.0
        total_production_time = 0.0
        total_cleaning_time = 0.0
        #coef pour mrp_ftpr_gergonne
        total_subcontracting_coef = 0.0
        price_preparation_time_coef = 0.0
        price_production_time_coef = 0.0
        price_cleaning_time_coef = 0.0
        waiting_time_next_ope = 0
        for routing_line in self.routing_line_ids:
            price_preparation_time_line = 0.0
            price_production_time_line = 0.0
            price_cleaning_time_line = 0.0
            price_preparation_time_line_coef = 0.0
            price_production_time_line_coef = 0.0
            price_cleaning_time_line_coef = 0.0
            st = False
            nb_product_parallel = routing_line.nb_product_parallel or 1.0
            #boucle sur les catégories de ressource
            for rl_resource_category in routing_line.rl_resource_category_ids:
                #Récupération de la première ressource
                rl_resource = rl_resource_obj.search([('rl_category_id', '=', rl_resource_category.id)], order='sequence asc', limit=1)
                
                #Coût de la première ressource si vide on prend le coût de la catégorie
                if rl_resource.resource_id:
                    if rl_resource.resource_id.type == 'subcontracting':
                        st = True 
                        break
                        
                if rl_resource.resource_id and rl_resource.resource_id.hourly_rate:
                    hourly_rate = rl_resource.resource_id.hourly_rate
                else:
                    hourly_rate = rl_resource_category.category_id and rl_resource_category.category_id.hourly_rate
                
                #Calcul du coût de préparation
                if rl_resource.preparation_time:
                    preparation_time = rl_resource.preparation_time
                    price_preparation_time_line += preparation_time * hourly_rate
                    price_preparation_time_line_coef += preparation_time * hourly_rate * (routing_line.base_coeff or 1)
                else:
                    preparation_time = rl_resource_category.preparation_time
                    price_preparation_time_line += preparation_time * hourly_rate
                    price_preparation_time_line_coef += preparation_time * hourly_rate * (routing_line.base_coeff or 1)
                
                #Calcul du coût de production
                if rl_resource.production_time:
                    production_time = rl_resource.production_time * (price_qty / nb_product_parallel)
                    price_production_time_line += production_time * hourly_rate
                    price_production_time_line_coef += production_time * hourly_rate * (routing_line.base_coeff or 1)
                else:
                    production_time = rl_resource_category.production_time * (price_qty / nb_product_parallel)
                    price_production_time_line += production_time * hourly_rate
                    price_production_time_line_coef += production_time * hourly_rate * (routing_line.base_coeff or 1)
                    
                #Calcul du coût de nettoyage
                if rl_resource.cleaning_time:
                    cleaning_time = rl_resource.cleaning_time
                    price_cleaning_time_line += cleaning_time * hourly_rate
                    price_cleaning_time_line_coef += cleaning_time * hourly_rate * (routing_line.base_coeff or 1)
                else:
                    cleaning_time = rl_resource_category.cleaning_time
                    price_cleaning_time_line += cleaning_time * hourly_rate
                    price_cleaning_time_line_coef += cleaning_time * hourly_rate * (routing_line.base_coeff or 1)
                
                if not routing_line.option_id or option_ids and routing_line.option_id.id in option_ids:
                    total_preparation_time += preparation_time
                    total_production_time += production_time
                    total_cleaning_time += cleaning_time
            
            # Si ressource de ST
            if st:
                total_line = 0 
                total_line_coef = 0 
            else:
                total_line = price_preparation_time_line + price_production_time_line + price_cleaning_time_line
                total_line_coef = price_preparation_time_line_coef + price_production_time_line_coef + price_cleaning_time_line_coef
                
            #Calcul du coût de sous-traitance
            total_line_subcontracting = 0
            total_subcontracting_line_coef = 0.0
            for service in routing_line.consumed_service_ids:
                if service.type == 'fixed':
                    total_line_subcontracting += service.price_total
                    total_subcontracting_line_coef += total_subcontracting_line_coef * (routing_line.base_coeff or 1)
                else:
                    total_line_subcontracting += service.price_total * (price_qty / nb_product_parallel)
                    total_subcontracting_line_coef += service.price_total * (price_qty / nb_product_parallel) * (routing_line.base_coeff or 1)
            
            #Ecriture dans la ligne de gamme
            total = total_line + total_line_subcontracting
            total = total / price_qty
            unit_cost = total
            total_coef = total_line_coef + total_subcontracting_line_coef
            total_coef = total_coef / price_qty
            unit_cost_coeff = total_coef
            unit_cost, unit_cost_coeff = routing_line.compute_price_ftpr_gergonne(unit_cost, unit_cost_coeff)
            if button:
                routing_line.write({'total_cost': total, 'unit_cost': unit_cost, 'price_total_coeff': total_coef, 'unit_cost_coeff': unit_cost_coeff}) 
                #Creation de ligne dans le historique de coût
                list_currency_prod_ids = self.env['technical.data.config.settings'].get_param('list_currency_prod_ids')
                routing_currency_rcs = self.company_id.currency_id
                if list_currency_prod_ids:
                    for list_currency_prod in self.env['list.currency.production'].search([('id', 'in', list_currency_prod_ids)], order='sequence asc'):
                        price_list_currency_prod = routing_currency_rcs.compute(total, list_currency_prod.currency_id, round=False)
                        if total != total_coef:
                            total_coef_list_currency_prod = routing_currency_rcs.compute(total_coef, list_currency_prod.currency_id, round=False)
                        else:
                            total_coef_list_currency_prod = price_list_currency_prod
                            
                        vals_mrlch = {
                                        'currency_id': list_currency_prod.currency_id.id,
                                        'price_qty': self.price_qty,
                                        'price': price_list_currency_prod,
                                        'rl_id': routing_line.id,
                                        'user_id': self.env.user.id,}
                        
                        vals_mrlch_other = routing_line.get_vals_rl_cost_history(price_list_currency_prod, total_coef_list_currency_prod, routing_line.base_coeff)
                        vals_mrlch.update(vals_mrlch_other)
                        self.env['mrp.rl.cost.history'].create(vals_mrlch)
                else:
                    vals_mrlch = {
                                    'currency_id': routing_currency_rcs.id,
                                    'price_qty': self.price_qty,
                                    'price': total,
                                    'rl_id': routing_line.id,
                                    'user_id': self.env.user.id,}
                    vals_mrlch_other = routing_line.get_vals_rl_cost_history(total, total_coef, routing_line.base_coeff)
                    vals_mrlch.update(vals_mrlch_other)
                    self.env['mrp.rl.cost.history'].create(vals_mrlch)
            
            if not routing_line.option_id or option_ids and routing_line.option_id.id in option_ids:
                #Addition des valeurs pour chaque lignes
                waiting_time_next_ope += routing_line.waiting_time_next_ope
                total_subcontracting += total_line_subcontracting
                total_subcontracting_coef += total_subcontracting_line_coef
                if not st:
                    price_preparation_time += price_preparation_time_line
                    price_preparation_time_coef += price_preparation_time_line_coef
                    price_production_time += price_production_time_line
                    price_production_time_coef += price_production_time_line_coef
                    price_cleaning_time += price_cleaning_time_line
                    price_cleaning_time_coef += price_cleaning_time_line_coef
        
        total_price = price_preparation_time + price_production_time + price_cleaning_time + total_subcontracting
        total_price_coef = price_preparation_time_coef + price_production_time_coef + price_cleaning_time_coef + total_subcontracting_coef
        total_time = total_preparation_time + total_production_time + total_cleaning_time
        price_unit = total_price / price_qty
        price_unit_coef = total_price_coef / price_qty
        price_unit, price_unit_coef, total_price = self.compute_price_ftpr_gergonne(price_unit, price_unit_coef, total_price)
        if button:
            self.write({'total_price': total_price, 'price_unit': price_unit, 'price_unit_coeff': price_unit_coef, 'price_last_date': fields.Datetime.now()})
            #Creation de ligne dans le historique de coût
            list_currency_prod_ids = self.env['technical.data.config.settings'].get_param('list_currency_prod_ids')
            routing_currency_rcs = self.company_id.currency_id
            if list_currency_prod_ids:
                for list_currency_prod in self.env['list.currency.production'].search([('id', 'in', list_currency_prod_ids)], order='sequence asc'):
                    price_list_currency_prod = routing_currency_rcs.compute(price_unit, list_currency_prod.currency_id, round=False)
                    if price_unit != price_unit_coef:
                        price_unit_coef_list_currency_prod = routing_currency_rcs.compute(price_unit_coef, list_currency_prod.currency_id, round=False)
                    else:
                        price_unit_coef_list_currency_prod = price_list_currency_prod
                        
                    vals_mrch = {
                                    'currency_id': list_currency_prod.currency_id.id,
                                    'price_qty': self.price_qty,
                                    'price': price_list_currency_prod,
                                    'routing_id': self.id,
                                    'user_id': self.env.user.id,}
                
                    vals_mrch_other = self.get_vals_routing_cost_history(price_list_currency_prod, price_unit_coef_list_currency_prod)
                    vals_mrch.update(vals_mrch_other)
                    self.env['mrp.routing.cost.history'].create(vals_mrch)
            else:
                vals_mrch = {
                                'currency_id': routing_currency_rcs.id,
                                'price_qty': self.price_qty,
                                'price': price_unit,
                                'routing_id': self.id,
                                'user_id': self.env.user.id,}
                
                vals_mrch_other = self.get_vals_routing_cost_history(price_unit, price_unit_coef)
                vals_mrch.update(vals_mrch_other)
                self.env['mrp.routing.cost.history'].create(vals_mrch)
            return True
        else:
            return price_unit, total_price, total_time, waiting_time_next_ope
    
    
    def get_vals_routing_cost_history(self, price, price_coeff):
        """
            Fonction qui permet de rajouter dans la creation d'un enregistrement dans l'historique de coût des infos (mrp_ftpr_gergonne) pour les gammes
        """
        return {}
    
    
    #===========================================================================
    # Onchange
    #===========================================================================
    
    @api.onchange('routing_line_ids')
    def _onchange_routing_line_ids(self):
        """
            Calcul séquence
        """
        seq_list = []
        list_component_consum = []
        for line in self.routing_line_ids:
            seq_list.append(line.sequence)
            if line.consumed_component_ids:
                list_component_consum.extend([x.id for x in line.consumed_component_ids])
                
        if seq_list:
            max_sequence = max(seq_list)        
        else:
            max_sequence = 0
        
        self.max_sequence = max_sequence + 10
        self.consumed_component_ids = [(6, 0, list_component_consum)]
    
    #===========================================================================
    # Fonctions
    #===========================================================================
    def _routing_find(self, options=None):
        """
            Fonction qui permet de retourner la gamme à partir des propriétés
        """
        routing_rcs = False
        flag = False
        if options:
            for option in options:
                # Si encore aucune bom n a ete choisie
                if not flag:
                    for routing in self:
                        # Prend la BoM qui a la propriete recherche
                        if routing.option_id and  routing.option_id == option:
                            routing_rcs = routing
                            flag = True
                            break
                            
                else:
                    break
                
        if not routing_rcs:
            for routing in self:
                if routing.state == 'active' and not routing.option_id:
                    routing_rcs = routing
                    break
        
        return routing_rcs

    
    @api.multi
    def write(self, vals=None):
        """
            Redéfinition pour les opérations consommées
        """
        gernerate_op_cons = False
        if vals and 'routing_line_ids' in vals:
            for routing_line_ids in vals['routing_line_ids']:
                if routing_line_ids[0] == 2 or routing_line_ids[0] == 0:
                    gernerate_op_cons = True
                    break
                
        res = super(mrp_routing, self).write(vals=vals)
        if not self.operation_consumed_ids or gernerate_op_cons:
            self.boutton_generate_op_cons()
        
        return res
    
    
    def additional_function_domain(self, arg):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de mrp_routing_line
        """
        arg0, arg1, arg_1 = False, False, False
        if arg[0] == 'routing_product':
            arg0 = 'id'
            arg1 = arg[1]
            routing_ids = []
            bom_rcs = self.env['mrp.bom'].search([('bom_id', '=', False),('product_id', '=', arg[-1])])
            if bom_rcs:
                routing_rcs = self.search([('bom_ids', '=', bom_rcs.ids)])
                if routing_rcs:
                    routing_ids = routing_rcs.ids

            arg_1 = routing_ids
        
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
        return super(mrp_routing,self).search(args=args_modified, offset=offset, limit=limit, order=order, count=count) 
    
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=1000):
        """
            Fonction name_search
        """
        args.append(('name', 'ilike', name))
        args = self.compute_domain_args_resource(args)
        recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()
    
   
    #===========================================================================
    # Contraintes
    #===========================================================================
    @api.one
    @api.constrains('operation_consumed_ids')
    def _check_operation_consumed(self):
        # Contrainte de récursion dans les operations consommees
        ope_cons_obj = self.env['mrp.operation.consumed']
        # Fonction qui regarde si val et key sont dans les clef du dictionnaire
        def rec(key, val, dic):
            res = False
            for val1 in val:
                if key in dic and val1 in dic: 
                    res = key in dic[val1] or rec(key, dic[val1], dic)
                    
            return res

        result = False
        dic = {}
        no_ope_consum_rcs = self.env['mrp.routing.line']
        # Boucle sur les opérations consommées
        for ope in self.operation_consumed_ids:
            args = [
                    ('routing_id', '=', self.id),
                    ('operation_id', '=', ope.operation_id.id)
                    ]
            # On remplit le dictionnaire avec comme clé l'opération et comme valeur les opérations consomées
            ope_consu_ids = ope_cons_obj.search(args)
            consu_ids = []
            if ope_consu_ids:
                consu_ids = []
                for ope_consu in ope_consu_ids:
                    if ope_consu.operation_consumed_id:
                        if ope_consu.operation_consumed_id.id not in consu_ids:
                            consu_ids.append(ope_consu.operation_consumed_id.id)
                        else:
                            raise except_orm(_('Error'), _('There are many times the same consumption'))
                        
            dic[ope.operation_id.id] = consu_ids
            #Boucle pour connaitre le nb d'opérations non consommées car il ne faut qu'une opération finale
            args = [
                    ('routing_id', '=', self.id),
                    ('operation_consumed_id', '=', ope.operation_id.id)
                    ]
            # On cherche à savoir si l'opération est consommée ou non
            ope_consu_rcs = ope_cons_obj.search(args)
            if not ope_consu_rcs:
                no_ope_consum_rcs |= ope.operation_id
            
        # On teste s'il y a plusieurs opération non consommées car si oui erreur
        if no_ope_consum_rcs and len(no_ope_consum_rcs) > 1:
            name_ope = ''
            for ope_consu in no_ope_consum_rcs:
                if not name_ope:
                    name_ope = '%s'%(ope_consu.name)
                else:
                    name_ope = '%s, %s'%(name_ope, ope_consu.name)
                    
            raise except_orm(_('Error'), _('It may be that an operation is not consumed (a final operation) (%s)')%(name_ope))
        
        
        # On boucle sur l'ensemble des valeur du dict
        for key,val in dic.items(): 
            if rec(key, val, dic):
                result = True
                break
            
        if result:
            raise except_orm(_('Error'), _('Recursion in operation consumed'))
    
    
    @api.one
    @api.constrains('operation_consumed_ids','routing_line_ids')
    def _check_operation_consumed_routing_line(self):
        ope_cons_obj = self.env['mrp.operation.consumed']
        rl_obj = self.env['mrp.routing.line']
        # Contrainte dans les operations consommees la dernière opération doit être unique
        last_rl = rl_obj.search([('routing_id', '=', self.id)], order='sequence desc', limit=1)
        if last_rl:
            rl_ids = rl_obj.search([('routing_id', '=', self.id),('sequence', '=', last_rl.sequence)])
            count = 0
            for rl in rl_ids:
                consum_id = ope_cons_obj.search([('operation_id', '=', rl.id)])
                if consum_id:
                    count += 1
                    if count > 1:
                        raise except_orm(_('Error'), _('The last operation must be unique'))
       
       
    @api.multi
    def copy(self, default=None):
        """
            Copie d'OT
        """
        
        if not default:
            default = {}
            
        default['state'] = 'draft'
        return super(mrp_routing, self).copy(default=default)    
    
    
    
class mrp_rl_resource_category(models.Model):
    """ 
        Resource category in routing line 
    """
    _name = 'mrp.rl.resource.category'
    _description = 'Resource category in routing line'
    _rec_name = 'category_id'
    _order = 'sequence asc'
    
    @api.model
    #Première catégorie de ressource temps masqué à 0.0% et le reste des ressources 100.0%
    def default_get(self, fields_list):
        res = super(mrp_rl_resource_category, self).default_get(fields_list=fields_list)
        is_line_category = self._context.get('is_line_category', False)
        if not is_line_category:
            res['preparation_masked_time'] = 0.0
            res['production_masked_time'] = 0.0 
            res['cleaning_masked_time'] = 0.0
            res['color_kanban'] = 2
        else:
            res['color_kanban'] = 5
        return res
    
    
    @api.one
    def _compute_max_sequence_resource(self):
        line_ids = self.env['mrp.rl.resource'].search([('rl_category_id', '=', self.id)], order='sequence desc', limit=1)
        self.max_sequence_resource = line_ids and line_ids.sequence + 10 or 10


    @api.one
    @api.depends('rl_resource_ids', 'resource_ids', 'rl_resource_ids.resource_id')
    def _compute_concat_resource(self):
        """
            Champ qui concatène les ressources pour la vue simplifié des opérations
        """
        concat_resource = ''
        for rl_resource in self.rl_resource_ids:
            if not concat_resource:
                concat_resource = rl_resource.resource_id.name
            else:
                concat_resource = ' %s, %s'%(concat_resource,rl_resource.resource_id.name)
                
        self.concat_resource = concat_resource
    
    
    @api.one   
    def _compute_resource_ids(self):
        """
            Toutes les resources
        """
        self.resource_ids = [x.resource_id.id for x in self.rl_resource_ids if x.resource_id]
    
    
    @api.model
    def _type_get(self):
        return [
                ('time', _('Time')),
                ('cadence', _('Cadence')),
                ('formula', _('Formula')),
                       ]
    
    
    @api.one
    @api.depends('cadence', 'type', 'production_time_seizure', 'formula')
    def _compute_time(self):
        product_id = self.routing_line_id and self.routing_line_id.routing_id and self.routing_line_id.routing_id.bom_first_id and self.routing_line_id.routing_id.bom_first_id.product_id and self.routing_line_id.routing_id.bom_first_id.product_id.id or 0
        self.production_time = self.compute_time_production(self.type, time=self.production_time_seizure, cadence=self.cadence, 
                                                            formula=self.formula, args_parameters_list=[('product_id', '=', product_id)])
        
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    routing_line_id = fields.Many2one('mrp.routing.line', string='Routing line', required=False, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=0, required=True)
    category_id = fields.Many2one('mrp.resource.category', string='Category', required=True, ondelete='restrict')
    nb_resource = fields.Float(string='Nb resources', default=1.0, digits=dp.get_precision('Product quantity'), required=True)
    preparation_time = fields.Float(string='Preparation time', default=0.0, digits=dp.get_precision('Time'), required=True)
    production_time_seizure = fields.Float(string='Production time', default=0.0, digits=dp.get_precision('Time'), required=True)
    cleaning_time = fields.Float(string='Cleaning time', default=0.0, digits=dp.get_precision('Time'), required=True)
    preparation_masked_time = fields.Float(string='% Preparation masked time', default=100.0, digits=dp.get_precision('Product quantity'), required=True)
    production_masked_time = fields.Float(string='% Production masked time', default=100.0, digits=dp.get_precision('Product quantity'), required=True)
    cleaning_masked_time = fields.Float(string='% Cleaning masked time', default=100.0, digits=dp.get_precision('Product quantity'), required=True)
    rl_resource_ids = fields.One2many('mrp.rl.resource', 'rl_category_id',  string='Resources', copy=True)
    max_sequence_resource = fields.Integer(string='Max sequence', default=10, compute='_compute_max_sequence_resource', store=False)
    concat_resource = fields.Char(string='string', size=256, compute='_compute_concat_resource', store=True)
    resource_ids = fields.One2many('mrp.resource', compute='_compute_resource_ids')
    color_kanban = fields.Integer(string='Color Kanban', default=5, required=False)
    type = fields.Selection('_type_get', string='Production time type', default='time', required=True)
    production_time = fields.Float(string='Production time', digits=dp.get_precision('Time'), compute='_compute_time', store=True)
    cadence = fields.Float(string='Cadence (/h)', digits=dp.get_precision('Product quantity'), default=0.0, required=False)
    formula = fields.Text(string='Production time formula', help="""If the type is formula you can put in the formula of defined parameters\nHere is the unit time\nThe default parameter values are taken from the product file (Use the formula param[ 'parameter name'])\nexample:\n    220 * 12/11\n    param['width1'] / param['length1'] + 5""")

    
    #===========================================================================
    # Onchange
    #===========================================================================
    
    @api.onchange('rl_resource_ids', 'resource_ids')
    def _onchange_rl_resource_ids(self):
        """
            Calcul séquence
        """
        seq_list = []
        list_resource = []
        concat_resource = ''
        for line in self.rl_resource_ids:
            seq_list.append(line.sequence)
            if line.resource_id:
                list_resource.append(line.resource_id.id)
                if not concat_resource:
                    concat_resource = line.resource_id.name
                else:
                    concat_resource = ' %s, %s'%(concat_resource, line.resource_id.name)
                    
        if seq_list:
            max_sequence_resource = max(seq_list)        
        else:
            max_sequence_resource = 0
            
        self.max_sequence_resource = max_sequence_resource + 10
        self.resource_ids = list_resource
        self.concat_resource = concat_resource
    
    
    @api.onchange('type', 'production_time_seizure', 'cadence')
    def _onchange_compute_cadence_production_time(self):
        if self.type == 'time':
            self.cadence = self.production_time_seizure != 0 and 1 / self.production_time_seizure or 0.0 
        elif self.type == 'cadence':
            self.production_time_seizure = self.cadence != 0 and 1 / self.cadence or 0.0 
        
    
    #===========================================================================
    # Fonction
    #===========================================================================
    
    def compute_time_production(self, type, time=0.0, cadence=0.0, formula=0.0, args_parameters_list=[]):
        """
            Fonction qui permet de calculer de temps de production en fonction du type et des paramètres si c'est de type formule
        """
        production_time = 0.0
        if type == 'time':
            production_time = time
        elif type == 'cadence':
            production_time = cadence != 0.0 and 1 / cadence or 0.0 
        elif type == 'formula':
            production_time = self.compute_time_production_formula(formula, args_parameters_list=args_parameters_list)
        elif type == 'abc':
            production_time = self.compute_time_production_abc()
            
        return production_time
    
    
    def compute_time_production_abc(self):
        """
            Fonction utilisée dans Gergonne
        """
        return 0.0

    
    def compute_time_production_formula(self, formula, args_parameters_list=[]):
        """
            Fonction qui permet de calculer de temps de production en fonction de la formule et des paramètres
        """
        qty = 0
        if formula:
            try:
                exp = re.compile("""param\[['"][^'"]{0,}['"]\]{1}""")
                param_obj = self.env['parameter.dimension']
                param_list = exp.findall(formula)
                param = {}
                if param_list:
                    param_list = list(set(param_list))
                    for v in param_list:
                        v = v[7:-2]
                        args_parameter = [('name', '=', v)]
                        if args_parameters_list:
                            args_parameter.extend(args_parameters_list)
                            
                        param_ids = param_obj.search(args_parameter, limit=1)
                        if param_ids:
                            param[v] = param_ids[0].value
                        else:
                            raise except_orm(_('Error'), _('No parameter (%s) in product.')%(v))
                       
                qty = eval(formula)
            except:
                qty = 0.0
        return qty
    
    
    
class mrp_rl_resource(models.Model):
    """ 
    Resource in routing line 
    """
    _name = 'mrp.rl.resource'
    _description = 'Resource in routing line'
    _rec_name = 'resource_id'
    _order = 'sequence asc'
    
    @api.model
    # Récupérer la catégorie de ressource dans mrp_rl_catégory pour faire le domain sur les ressources
    def default_get(self, fields_list):
        res = super(mrp_rl_resource, self).default_get(fields_list=fields_list)
        if self.rl_category_id:
            res['category_id'] = self.rl_category_id.category_id
            
        return res
    
    @api.model
    def _type_get(self):
        return [
                ('time', _('Time')),
                ('cadence', _('Cadence')),
                ('formula', _('Formula')),
                       ]
    
    
    @api.one
    @api.depends('cadence', 'type', 'production_time_seizure', 'formula')
    def _compute_time(self):
        product_id = self.rl_category_id and self.rl_category_id.routing_line_id and self.rl_category_id.routing_line_id.routing_id and self.rl_category_id.routing_line_id.routing_id.bom_first_id and self.rl_category_id.routing_line_id.routing_id.bom_first_id.product_id and self.rl_category_id.routing_line_id.routing_id.bom_first_id.product_id.id or 0
        if product_id:
            self.production_time = self.rl_category_id.compute_time_production(self.type, time=self.production_time_seizure, cadence=self.cadence, 
                                                            formula=self.formula, args_parameters_list=[('product_id', '=', product_id)])
        else:
            prod_family_id = self.rl_category_id and self.rl_category_id.routing_line_id and self.rl_category_id.routing_line_id.routing_id and self.rl_category_id.routing_line_id.routing_id.bom_first_id and self.rl_category_id.routing_line_id.routing_id.bom_first_id.prod_family_id and self.rl_category_id.routing_line_id.routing_id.bom_first_id.prod_family_id.id or 0
            self.production_time = self.rl_category_id.compute_time_production(self.type, time=self.production_time_seizure, cadence=self.cadence, 
                                                            formula=self.formula, args_parameters_list=[('prod_family_id', '=', prod_family_id)])
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    rl_category_id = fields.Many2one('mrp.rl.resource.category', string='Category', required=False, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=0, required=True)
    category_id = fields.Many2one('mrp.resource.category', string='Resource Category', related='rl_category_id.category_id', readonly=True)
    resource_id = fields.Many2one('mrp.resource', string='Resource', required=True, ondelete='restrict')
    preparation_time = fields.Float(string='Preparation time', default=0.0, digits=dp.get_precision('Time'), required=False)
    production_time_seizure = fields.Float(string='Production time', default=0.0, digits=dp.get_precision('Time'), required=False)
    cleaning_time = fields.Float(string='Cleaning time', default=0.0, digits=dp.get_precision('Time'), required=False)
    preparation_masked_time = fields.Float(string='% Preparation masked time', default=0.0, digits=dp.get_precision('Product quantity'), required=False)
    production_masked_time = fields.Float(string='% Production masked time', default=0.0, digits=dp.get_precision('Product quantity'), required=False)
    cleaning_masked_time = fields.Float(string='% Cleaning masked time', default=0.0, digits=dp.get_precision('Product quantity'), required=False)
    type = fields.Selection('_type_get', string='Production time type', default='time', required=True)
    production_time = fields.Float(string='Production time', digits=dp.get_precision('Time'), compute='_compute_time')
    cadence = fields.Float(string='Cadence (/h)', digits=dp.get_precision('Product quantity'), default=0.0, required=False)
    formula = fields.Text(string='Production time formula', help="""If the type is formula you can put in the formula of defined parameters\nHere is the unit time\nThe default parameter values are taken from the product file (Use the formula param[ 'parameter name'])\nexample:\n    220 * 12/11\n    param['width1'] / param['length1'] + 5""")
    
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('type', 'production_time_seizure', 'cadence')
    def _onchange_compute_cadence_production_time(self):
        if self.type == 'time':
            self.cadence = self.production_time_seizure != 0 and 1 / self.production_time_seizure or 0.0 
        elif self.type == 'cadence':
            self.production_time_seizure = self.cadence != 0 and 1 / self.cadence or 0.0 
    
    
    
class mrp_rl_consumed_service(models.Model):
    """ 
        Consumed service 
    """
    _name = 'mrp.rl.consumed.service'
    _description = 'Consumed service'
    _rec_name = 'product_id'
    
    
    @api.model
    def _type_get(self):
        return [
            ('fixed', _('Fixed')),
            ('variable', _('Variable')),
               ]


    @api.one
    def _compute_price_total(self):
        price = 0.0
        bon_obj = self.env['mrp.bom']
        currency_price_return = self.routing_line_id and self.routing_line_id.routing_id and self.routing_line_id.routing_id.company_id and self.routing_line_id.routing_id.company_id.currency_id or False
        if self.product_id:
            if self.product_id.supply_method == 'buy':
                eoq = self.routing_line_id and self.routing_line_id.routing_id and self.routing_line_id.routing_id.price_qty or 1.0
                qty_calcul = self.quantity * eoq
                price_unit_product = bon_obj.compute_price_component_buy(self.product_id, qty_calcul, self.uom_id, currency_price_return)
            else:
                price_unit_product = bon_obj.compute_price_component_produce(self.product_id, self.quantity)
            
            price = price_unit_product * self.quantity
            
        self.price_total = price
       
    
    #===========================================================================
    # COLUMNS
    #=========================================================================== 
    routing_line_id = fields.Many2one('mrp.routing.line', string='Routing line', required=False, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='restrict')
    quantity = fields.Float(string='Quantity', digits=dp.get_precision('Product quantity'), default=1.0, required=True)
    uom_id = fields.Many2one('product.uom', string='UOM', required=True, ondelete='restrict')
    uom_category_id = fields.Many2one('product.uom.category', related='product_id.uom_id.category_id', string="UOM category", readonly=True)
    type = fields.Selection('_type_get', string='Type', required=True, default='variable')
    price_total = fields.Float(string='Price total', compute='_compute_price_total', digits=dp.get_precision('Price technical'))
    
    #===========================================================================
    # Onchange
    #===========================================================================
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
            Au changement du produit, changement de la catégorie de l'uom
        """
        self.uom_id = self.product_id and self.product_id.uom_id or False
        self.uom_category_id = self.product_id and self.product_id.uom_id and self.product_id.uom_id.category_id or False



class mrp_rl_tools(models.Model):
    """ 
        Tools 
    """
    _name = 'mrp.rl.tools'
    _description = 'Tools'
    _rec_name = 'product_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    routing_line_id = fields.Many2one('mrp.routing.line', string='Routing line', required=False, ondelete='Cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='restrict')
    quantity = fields.Float(string='Quantity', digits=dp.get_precision('Product quantity'), default=1.0, required=True)
    uom_id = fields.Many2one('product.uom', string='UOM', required=True, ondelete='restrict')
    uom_category_id = fields.Many2one('product.uom.category', related='product_id.uom_id.category_id', string="UOM category", 
                                      readonly=True)

    #===========================================================================
    # Onchange
    #===========================================================================
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
            Au changement du produit, changement de la catégorie de l'uom
        """
        self.uom_id = self.product_id and self.product_id.uom_id or False
        self.uom_category_id = self.product_id and self.product_id.uom_id and self.product_id.uom_id.category_id or False



class mrp_rl_complaint(models.Model):
    """ 
        Complaint 
    """
    _name = 'mrp.rl.complaint'
    _description = 'Complaint'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    @api.model
    def _type_get(self):
        return [
                ('intern', _('Intern')),
                ('customer', _('Customer')),
                       ]
    
    name = fields.Char(required=True,string=u"N°", size=256)
    date = fields.Date(string='Date')
    type = fields.Selection('_type_get', string='Type',required=True,default='intern')
    customer_id = fields.Many2one('res.partner', string='Customer', required=False, ondelete='restrict')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='restrict')
    motif = fields.Char(string='Motif', size=256, required=False)
    cause = fields.Text(string='Cause')
    action = fields.Text(string='Action')
    area_id = fields.Many2one('mrp.area', string='Area', required=False, ondelete='restrict', help='mrp_rl_complaint.area_id.help')
    routing_line_ids = fields.Many2many('mrp.routing.line', 'mrp_rl_complaint_mrp_routing_line_rel', 'complaint_id', 'routing_line_id', string='Routing line')
    
    
    @api.multi
    def generate_nonconformity_manual(self):
        """
            Generer fiche de non-conformité manuelle
        """
        nonconformity_obj = self.env['nonconformity.file']
        for complaint in self:
            vals = {'partner_id': complaint.customer_id.id,
                    'complaint_id': complaint.id,
                    'origin_type': 'complaint',
                    'product_id': complaint.product_id.id,
                    'qty': 0.0,
                    'type': 'product',
                    'create_date': fields.Date.today()}
            nonconformity_rcs = nonconformity_obj.create(vals)  
#             nonconformity_rcs = nonconformity_obj.generate_manual(vals)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Nonconformity File',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'nonconformity.file',
                'res_id': nonconformity_rcs.id,
                'target': 'current',
            }
          
        return True  
    
    
    @api.multi
    def unlink(self):
        """
            On empêche la suppression de la réclamation si elle est utilisée dans une gamme
        """
        routing_line_obj = self.env['mrp.routing.line']
        for complaint in self:
            complaint_rel_rs = routing_line_obj.search([('complaint_ids', 'in', complaint.id)], limit=1)
            if complaint_rel_rs:
                raise except_orm(_('Error'), _('The complaint n° %s is used in a routing line. Please delete the complaint reference in '
                                               'the routing line before delete it')%(complaint.name))
        
        return super(mrp_rl_complaint, self).unlink()
    
    

class mrp_rl_consign(models.Model):
    """ 
        Consign
    """
    _name = 'mrp.rl.consign'
    _description = 'Consign'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    @api.model
    def _type_get(self):
        return [
                ('consign', _('Consign')),
                ('control', _('Control')),
                       ]
    
    routing_line_id = fields.Many2one('mrp.routing.line', string='Routing line', required=False, ondelete='cascade')
    name = fields.Char(required=True, string=u"N°")
    frequency = fields.Char(string='Frequency', size=256, required=False)
    type = fields.Selection('_type_get', string='Type', default='consign')
    desciptive = fields.Char(string='Desciptive', size=256, required=True)
    means = fields.Char(string='Means', size=32, required=False)



class mrp_operation_consumed(models.Model):
    """ 
        Operations consumed 
    """
    _name = 'mrp.operation.consumed'
    _description = 'Operations consumed'
    _rec_name = 'routing_id'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    routing_id = fields.Many2one('mrp.routing', string='Routing', required=False, ondelete='cascade')
    operation_id = fields.Many2one('mrp.routing.line', string='Operation', required=False, ondelete='cascade',help="Define the operation")
    operation_consumed_id = fields.Many2one('mrp.routing.line', string='Operation consumed', required=False, ondelete='cascade', help="Define the operation consumed")

    
    
class mrp_bom(models.Model):
    """ 
        description 
    """
    _name = 'mrp.bom'
    _description = 'Bill of Material'
    _order = 'sequence asc, id asc'
    
    @api.multi
    def name_get(self):
        """
            Name get de la nomenclature [name_bom] name_product
        """
        result = []
        for event in self:
            if event.product_id:
                name = '[%s] %s'%(event.name, event.product_id.name)
            elif event.prod_family_id:
                name = '[%s] %s'%(event.name, event.prod_family_id.name)
            else:
                name = event.name
                
            result.append((event.id, name))
            
        return result
    
    
    def compute_domain_args(self, args):
        """
            Domaine des nomenclatures
        """
        args2 = []
        for arg in args:
            if isinstance(arg, str) or (isinstance(arg, list) and arg[0] in ('!', '|', '&')):
                args2.append(arg)
                continue
            
            # Permet de filtrer les bom component avec la bom de la routing
            if arg[0] == 'bom_id_in_routing':
                if 'value_parent' in self.env.context and 'name_ftpr' in self.env.context['value_parent']:
                    arg[0] = 'id'
                else:
                    arg[0] = 'bom_id'
                    
                list_arg = []
                for val_arg in arg[-1]:
                    if val_arg[0] == 6:
                        list_arg.extend(val_arg[-1])
                    elif val_arg[0] == 1 or val_arg[0] == 4:
                        list_arg.append(val_arg[1])
                
                arg[-1] = list_arg 
            elif arg[0] == 'bom_id_in_routing1':
                arg[0] = 'bom_id'
                if arg[-1]:
                    routing_rcs = self.env['mrp.routing'].browse(arg[-1])
                    bom_ids = routing_rcs.bom_ids and routing_rcs.bom_ids.ids or []
                else:
                    bom_ids = []

                arg[-1] = bom_ids
            elif arg[0] == 'bom_id_already_use':
                arg[0] = 'id'
                list_arg = []
                for val_arg in arg[-1]:
                    if val_arg[0] == 6:
                        list_arg.extend(val_arg[-1])
                    elif val_arg[0] == 1 or val_arg[0] == 4:
                        list_arg.append(val_arg[1])
                
                arg[-1] = list_arg 
            elif arg[0] == 'bom_id_already_use1':
                arg[0] = 'id'
                if arg[-1]:
                    routing_rcs = self.env['mrp.routing'].browse(arg[-1])
                    bom_ids = routing_rcs.consumed_component_ids and routing_rcs.consumed_component_ids.ids or []
                else:
                    bom_ids = []
                    
                arg[-1] = bom_ids
                
            elif arg[0] == 'bom_id_in_available':
                arg[0] = 'id'
                arg[-1] = arg[-1] and arg[-1][0] and arg[-1][0][-1]
                
#             # Faire un raccourcis vers l'ensemble des nomenclature qui on ce produit en tant que composant
#             elif arg[0] == 'my_component':
#                 bom_ids = []
#                 bom_lines = self.search([('product_id','in',self.env.context['active_ids']),('bom_id','!=',False)])
#                 if bom_lines:
#                     bom_ids = self.search([('bom_lines','in',bom_lines)])
#                 arg[0] = 'id'
#                 arg[-1] = bom_ids
            args2.append(arg)
        
        return args2

    
    @api.model
    def search(self,args=None, offset=0, limit=None, order=None, count=None):
        """
            Fonction search de la nomenclature 
        """
        args = args or []
        args_modified = self.compute_domain_args(args)
        return super(mrp_bom,self).search(args=args_modified, offset=offset, limit=limit, order=order, count=count)

            
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=1000):
        """
            Fonction name_search de la nomenclature
        """
        recs = False
        args = self.compute_domain_args(args)
        if name:
            product_ids = self.env['product.product'].search(['|',('code', operator, name), ('name', operator, name)], limit=limit)
            list_product_ids = [x.id for x in product_ids]
            recs = self.search([('product_id', 'in', list_product_ids), ('bom_id', '=', False)] + args, limit=limit)
            
        if not recs:
            recs = self.search([('name', operator, name)] + args, limit=limit)
            
        return recs.name_get()
    
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False,lazy=True):
        domain = self.compute_domain_args(domain)
        return super(mrp_bom, self).read_group(domain=domain, fields=fields, groupby=groupby, offset=offset, limit=limit, orderby=orderby,lazy=lazy)
    


    @api.model
    def _type_get(self):
        return [
                ('normal', _('Normal')),
                ('kit', _('Kit')),
                ('family', _('Family')),
                       ]
        
        
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('active', _('Active')),
                ('obsolete', _('Obsolete')),
                       ]
    
    @api.model
    def _type_component_get(self):
        return [
                ('fixed', _('Fixed')),
                ('variable', _('Variable')),
                ('formula', _('Formula')),
                       ]
        
    @api.one
    def _compute_price_total_component(self):
        """
            Prix total du composant
        """
        if self.bom_id:
            self.price_total_component = self.price_unit * self.qty_component_compute
        else:
            self.price_total_component = 0.0
    
    
    @api.one
    def _qty_component_compute(self):
        """
            Quantité composant
        """
        # Pour le calcul de la qté dans les lignes de composants
#         serie_eco = self.env['mrp.manufacturingorder'].qty_min_multiple(self.bom_id.price_qty, 
#                                      self.bom_id.product_id.production_min_qty, 
#                                      self.bom_id.product_id.production_multiple_qty,
#                                      self.bom_id.efficiency,
#                                      self.bom_id.round)
        serie_eco = self.bom_id.price_qty
        prod_family_id = self.bom_id.prod_family_id and self.bom_id.prod_family_id.id  or False
        product_id = self.bom_id.product_id and self.bom_id.product_id.id or False
        qty, efficient_unit_qty = self.function_qty_component_compute(self.bom_id.type, serie_eco, prod_family_id=prod_family_id, product_id=product_id)
        self.qty_component_compute = qty
        
    
    def function_qty_component_compute(self, type, serie_eco, prod_family_id=False, product_id=False):
        """
            Quantité composant
        """
        if type == 'family':
            qty, efficient_unit_qty = self.compute_qty_component(self.quantity, self.round, self.efficiency, self.bom_id.quantity, qty_wo=serie_eco, 
                                                                 type_component=self.type_component, 
                                                                 formula=self.formula_component, args_parameters_list=[('prod_family_id', '=', prod_family_id)])
        else:
            qty, efficient_unit_qty = self.compute_qty_component(self.quantity, self.round, self.efficiency, self.bom_id.quantity, qty_wo=serie_eco, 
                                                                 type_component=self.type_component, 
                                                                 formula=self.formula_component, args_parameters_list=[('product_id', '=', product_id)])
        
        return qty, efficient_unit_qty
    
    
    
    
    def compute_child_complete_ids(self):
        """
            Fonction qui calcule les composants liées à la nomenclature de tête
        """
        component_ids = []
        for component in self.bom_ids:
            component_ids.append(component)
            options = component.option_id and [component.option_id.id] or False
            bom_component = self._bom_find(component.product_id.id, component.uom_id.id, options=options)
            if bom_component:
                component_ids.extend(bom_component.compute_child_complete_ids())
                
        return component_ids
    
    
    def compute_child_structure_ids(self):
        """
            Fonction qui calcule la structure
        """
        bom_head_ids = []
        parent_bom = self if self.bom_ids else self._bom_find(self.product_id.id, self.uom_id.id, options=self.option_id.id, no_active=True)
        if parent_bom:
            for component in parent_bom.bom_ids:
                bom_head_ids.append(component)
        return bom_head_ids
    
    
    @api.one         
    def _compute_child_complete_ids(self):
        """
            Toutes les composants liées à la nomenclature de tête
        """
        self.child_complete_ids = [x.id for x in self.compute_child_complete_ids()]
    
    
    @api.one         
    def _compute_child_structure_ids(self):
        """
            Fonction qui calcule la structure
        """
        self.child_structure_ids = [x.id for x in self.compute_child_structure_ids()]
    
    @api.one
    def _compute_qty_with_factor(self):
        self.qty_with_factor = "{} (x{})".format(self.quantity, self.qty_component_compute / self.quantity)
    
    
    @api.one         
    def _compute_parameter_product_text(self):
        parameter_product_text = _('Product parameters from the head of BOM that can be used:')
        if self.bom_id and self.bom_id.prod_family_id and self.bom_id.type == 'family':
            parameter_product_rcs = self.env['parameter.dimension'].search([('prod_family_id', '=', self.bom_id.prod_family_id.id)])
            for parameter_product in parameter_product_rcs:
                parameter_product_text = '%s\n    %s'%(parameter_product_text, parameter_product.name)
        
        elif self.bom_id and self.bom_id.product_id:
            parameter_product_rcs = self.env['parameter.dimension'].search([('product_id', '=', self.bom_id.product_id.id)])
            for parameter_product in parameter_product_rcs:
                parameter_product_text = '%s\n    %s'%(parameter_product_text, parameter_product.name)
            
        self.parameter_product_text = parameter_product_text
        
        
    @api.one
    @api.depends('routing_ids', 'routing_ids.price_unit', 'routing_ids.state', 'routing_ids.stop_date', 'routing_ids.start_date', 'price_last_date')
    def _compute_routing_first_price(self):
        """
            Prix de la première gamme
        """
        price = 0.0
        routing_first = False
        for routing in self.env['mrp.routing'].search([('id', 'in', self.routing_ids.ids), ('state', '=', 'active')], order='sequence asc'):
            routing_valid = True
            if (routing.start_date and routing.start_date > self.price_last_date) or (routing.stop_date and routing.stop_date < self.price_last_date):
                routing_valid = False
            
            if routing_valid:
                price = routing.price_unit
                routing_first = routing
                break

        self.routing_first_id = routing_first
        self.routing_first_price = price
        self.routing_first_efficiency = routing_first and routing_first.efficiency_global or 1
        
        
    @api.one
    @api.depends('efficiency', 'routing_first_efficiency')
    def _compute_total_efficiency(self):
        self.total_efficiency = self.efficiency * self.routing_first_efficiency
    
    
    @api.one
    @api.depends('price_unit', 'routing_first_price', 'product_id.price_qty', 'prod_family_id.price_qty', 
                 'product_id.uom_id.category_id', 'prod_family_id.uom_id.category_id', 'bom_id')
    def _value_product_family_compute(self):
        """
            Prix de revient
        """
        uom_category_id = False
        price_qty = 1
        if self.type == 'family':
            uom_category_id = self.prod_family_id.uom_id.category_id.id
            if not self.bom_id:
                price_qty = self.prod_family_id.price_qty
        else:
            uom_category_id = self.product_id.uom_id.category_id.id
            if not self.bom_id:
                price_qty = self.product_id.price_qty
            
            
        self.uom_category_id = uom_category_id
        self.price_qty = price_qty
        self.production_cost_price = self.price_unit + self.routing_first_price
    
    
    @api.one
    @api.depends('price_total_component', 'base_coeff')
    def _compute_price_total_coeff(self):
        if self.bom_id:
            self.price_total_coeff = self.price_total_component * self.base_coeff
        else:
            self.price_total_coeff = 0.0
 
 
    @api.one
    @api.depends('version_historical_ids')
    def _compute_version(self):
        current_date = fields.Date.today()
        i = 0
        while i < len(self.version_historical_ids) and self.version_historical_ids[i].start_date <= current_date:
            self.version = self.version_historical_ids[i].version
            i += 1
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    #Entête
    name = fields.Char(required=True,string='Reference', default='/')
    prod_family_id = fields.Many2one('production.family', string='Production family', required=False, ondelete='restrict')
    product_id = fields.Many2one('product.product', string='Product', select=True, required=False, ondelete='restrict')
    quantity = fields.Float(string='Quantity', digits=dp.get_precision('Product quantity'), default=1.0, required=True)
    uom_id = fields.Many2one('product.uom', string='UOM', required=True, ondelete='restrict')
    uom_category_id = fields.Many2one('product.uom.category', compute='_value_product_family_compute', string="UOM category", readonly=True, store=True)
    is_model = fields.Boolean(string='Model', default=False)
    start_date = fields.Date(string='Date Start', select=True)
    stop_date = fields.Date(string='Date Stop', select=True)
    template_id = fields.Many2one('mrp.bom', string='Model', required=False, ondelete='set null')
    type = fields.Selection('_type_get', string='Type', default='normal')
    price_qty = fields.Float(compute='_value_product_family_compute', string="Economic series", digits=dp.get_precision('Price technical'), store=True, 
                             readonly=True, help="Used to calculate the price of raw materials")
    production_cost_price = fields.Float(compute='_value_product_family_compute', digits=dp.get_precision('Price technical'), store=True, 
                                         readonly=True)
    bom_id = fields.Many2one('mrp.bom', string='Bom', required=False, select=True, ondelete='cascade')
    state = fields.Selection('_state_get', string='State', select=True, default='draft')
    
    #Composant
    sequence = fields.Integer(string='Sequence', default=0, required=False)
    bom_ids = fields.One2many('mrp.bom', 'bom_id',  string='Component', copy=True)
    price_unit = fields.Float(string='Price unit', default=0.0, digits=dp.get_precision('Price technical'), required=False)
    price_total_component = fields.Float(string='Price total', digits=dp.get_precision('Price technical'), compute='_compute_price_total_component')
    is_valid_priceunit = fields.Boolean(string='Valid price unit', default=False)
    type_component = fields.Selection('_type_component_get', string='Type component', required=True, default='variable')
    formula_component = fields.Text(string='Formula Qty')
    qty_component_compute = fields.Float(string='Qty compute', digits=dp.get_precision('Product quantity'), compute='_qty_component_compute')
    
    #Révision
    revison_ids = fields.One2many('mrp.bom.revision', 'bom_id',  string='Revisions', copy=True)
    version_historical_ids = fields.One2many('product.version.historical', string='Version historical', related='product_id.version_historical_ids', readonly=True)
    version = fields.Char(string='Version', related='product_id.version_product', readonly=True)
    
    #Information
    company_id = fields.Many2one('res.company', string='Company', required=False, ondelete='restrict', default=lambda self: self.env.user.company_id)
    round = fields.Float(string='Round', default=0, digits=dp.get_precision('Technical Product Round'), required=True)
    efficiency = fields.Float(string='Efficiency', default=1, digits=dp.get_precision('Product Efficiency'), required=True)
    active = fields.Boolean(string='Active', default=True)
    note_mo = fields.Text(string='Note on manufacturing')
    option_id = fields.Many2one('mrp.option', string='Option', required=False, select=True, ondelete='restrict')
    
    #Déclinaison
    template_ids = fields.One2many('mrp.bom', 'template_id',  string='Declension')
    
    #Gamme
    routing_ids = fields.Many2many('mrp.routing', 'mrp_bom_mrp_routing_rel', 'bom_id', 'routing_id', string='Routings')
    
    #Sous produits
    subproduct_ids = fields.One2many('mrp.subproduct', 'bom_id',  string='Sub product', copy=True)
    
    #Cout
    component_total_price = fields.Float(string='Components total price', default=0.0, required=False, digits=dp.get_precision('Price technical'))
    routing_first_price = fields.Float(string='Routing first price', default=0.0, required=False, compute='_compute_routing_first_price', store=True, digits=dp.get_precision('Price technical'))
    routing_first_efficiency = fields.Float(string='Routing first efficiency', default=0.0, required=False, compute='_compute_routing_first_price', store=True)
    routing_first_id = fields.Many2one('mrp.routing', string='Routing first', required=False, compute='_compute_routing_first_price', store=True)
    price_last_date = fields.Date(string='Price compute last date')
    is_subtract_price_subproduct = fields.Boolean(string='Subtract the price sub product to the final product', default=False)
    total_efficiency = fields.Float(string='Total efficiency', default=0.0, required=False, compute='_compute_total_efficiency', store=True, help='Efficiency BoM * efficiency Routing')
    base_coeff = fields.Float(string='Coefficient', default=1.0, required=False)
    component_price_unit_coeff = fields.Float(string='Unit price with coefficient', compute='_compute_price_total_coeff', store=True, digits=dp.get_precision('Price technical'))
    price_unit_no_coeff = fields.Float(string='Unit price without coefficient', default=0.0, readonly=True, digits=dp.get_precision('Price technical'))
    price_unit_coeff = fields.Float(string='Unit price with coefficient', default=0.0, readonly=True, digits=dp.get_precision('Price technical'))
    #Autres
    child_complete_ids = fields.One2many('mrp.bom', compute='_compute_child_complete_ids')
    child_structure_ids = fields.One2many('mrp.bom', compute='_compute_child_structure_ids')
    qty_with_factor = fields.Char("Quantity", compute="_compute_qty_with_factor")
    parameter_product_text = fields.Text(compute='_compute_parameter_product_text')
    property_ids = fields.Many2many('purchase.property', string='Properties')
    mark = fields.Text(string='Mark')
    component_cost_history_ids = fields.One2many('mrp.component.cost.history', 'component_id',  string='Cost history')
    bom_cost_history_ids = fields.One2many('mrp.bom.cost.history', 'bom_id',  string='Cost history')

         
    #===========================================================================
    # Contraintes
    #===========================================================================
    @api.one
    @api.constrains('active', 'state', 'start_date', 'stop_date', 'option_id', 'product_id', 'prod_family_id')
    def _check_function_bom_double(self):
        """ Check BoM double
         @return: Boolean (if recursion : return false)
        """
        if self.active and self.state == 'active' and self.product_id and not self.bom_id:
            option = self.option_id and self.option_id.id or False
            bom = False
            if self.start_date and self.stop_date:
                bom = bool(self.search(['&', '&', '&', '&', '&', '&',('product_id', '=', self.product_id.id), 
                                                                ('active', '=', True),
                                                                ('state', '=', 'active'),
                                                                ('bom_id', '=', False),
                                                                ('id', '!=', self.id),
                                                                ('option_id', '=', option),
                                                                '|', '&', ('start_date', '>=', self.start_date), 
                                                                ('start_date', '<=', self.stop_date),
                                                                '|', '&', ('stop_date', '>=', self.start_date), 
                                                                ('stop_date', '<=', self.stop_date),
                                                                '|', '&', ('start_date', '=', False), 
                                                                ('stop_date', '=', False),
                                                                '|', '&', ('start_date', '=', False), 
                                                                ('stop_date', '>=', self.start_date),
                                                                '&', ('start_date', '<=', self.stop_date), 
                                                                ('stop_date', '=', False)], limit=1))
                
                if self.start_date > self.stop_date:
                    raise except_orm(_('Error'), _('Start date > Stop Date'))
                
            elif self.start_date:
                bom = bool(self.search(['&', '&', '&', '&', '&', '&',('product_id', '=', self.product_id.id), 
                                                                ('active', '=', True),
                                                                ('state', '=', 'active'),
                                                                ('bom_id', '=', False),
                                                                ('id', '!=', self.id),
                                                                ('option_id', '=', option),
                                                                '|',  '|',('start_date', '>=', self.start_date), 
                                                                ('stop_date', '>=', self.start_date),
                                                                ('stop_date', '=', False)], limit=1))
            elif self.stop_date:
                bom = bool(self.search(['&', '&', '&', '&', '&', '&',('product_id', '=', self.product_id.id), 
                                                                ('active', '=', True),
                                                                ('state', '=', 'active'),
                                                                ('bom_id', '=', False),
                                                                ('id', '!=', self.id),
                                                                ('option_id', '=', option), 
                                                                '|', '|',('start_date', '<=', self.stop_date), 
                                                                ('stop_date', '<=', self.stop_date),
                                                                '&', ('start_date', '=', False), 
                                                                ('stop_date', '=', False),], limit=1))
            else:
                bom = bool(self.search([('product_id', '=', self.product_id.id), 
                                                                ('active', '=', True),
                                                                ('state', '=', 'active'),
                                                                ('bom_id', '=', False),
                                                                ('id', '!=', self.id),
                                                                ('option_id', '=', option)], limit=1))
            if bom:
                raise except_orm(_('Error'), _('You can not have two active bom (with or without the same option) on the same product with date overlaps'))
            
        if self.active and self.state == 'active' and self.prod_family_id and not self.bom_id:
            option = self.option_id and self.option_id.id or False
            bom = False
            if self.start_date and self.stop_date:
                bom = bool(self.search(['&', '&', '&', '&', '&', '&',('prod_family_id', '=', self.prod_family_id.id), 
                                                                ('active', '=', True),
                                                                ('state', '=', 'active'),
                                                                ('bom_id', '=', False),
                                                                ('id', '!=', self.id),
                                                                ('option_id', '=', option),
                                                                '|', '&', ('start_date', '>=', self.start_date), 
                                                                ('start_date', '<=', self.stop_date),
                                                                '|', '&', ('stop_date', '>=', self.start_date), 
                                                                ('stop_date', '<=', self.stop_date),
                                                                '|', '&', ('start_date', '=', False), 
                                                                ('stop_date', '=', False),
                                                                '|', '&', ('start_date', '=', False), 
                                                                ('stop_date', '>=', self.start_date),
                                                                '&', ('start_date', '<=', self.stop_date), 
                                                                ('stop_date', '=', False)], limit=1))
                
                if self.start_date > self.stop_date:
                    raise except_orm(_('Error'), _('Start date > Stop Date'))
                
            elif self.start_date:
                bom = bool(self.search(['&', '&', '&', '&', '&', '&',('prod_family_id', '=', self.prod_family_id.id), 
                                                                ('active', '=', True),
                                                                ('state', '=', 'active'),
                                                                ('bom_id', '=', False),
                                                                ('id', '!=', self.id),
                                                                ('option_id', '=', option),
                                                                '|',  '|',('start_date', '>=', self.start_date), 
                                                                ('stop_date', '>=', self.start_date),
                                                                ('stop_date', '=', False)], limit=1))
            elif self.stop_date:
                bom = bool(self.search(['&', '&', '&', '&', '&', '&',('prod_family_id', '=', self.prod_family_id.id), 
                                                                ('active', '=', True),
                                                                ('state', '=', 'active'),
                                                                ('bom_id', '=', False),
                                                                ('id', '!=', self.id),
                                                                ('option_id', '=', option), 
                                                                '|', '|',('start_date', '<=', self.stop_date), 
                                                                ('stop_date', '<=', self.stop_date),
                                                                '&', ('start_date', '=', False), 
                                                                ('stop_date', '=', False),], limit=1))
            else:
                bom = bool(self.search([('prod_family_id', '=', self.prod_family_id.id), 
                                                                ('active', '=', True),
                                                                ('state', '=', 'active'),
                                                                ('bom_id', '=', False),
                                                                ('id', '!=', self.id),
                                                                ('option_id', '=', option)], limit=1))
            if bom:
                raise except_orm(_('Error'), _('You can not have two active bom (with or without the same option) on the same product with date overlaps'))
            
            
    def check_rec(self, product_ids=None):
        """
            Fonction qui permet de savoir si l'on a fait une récursion sur les nomenclatures
        """
        if product_ids:
            product_ids.append(self.product_id.id)
        else:
            product_ids = [self.product_id.id]
        
        for component in self.bom_ids:
            if component.product_id.id in product_ids:
                raise except_orm(_('Error'), _('You cannot create recursive BoM'))
            
            options = component.option_id and [component.option_id.id] or False
            bom_component = self._bom_find(component.product_id.id, component.uom_id.id, options=options)
            if bom_component:
                bom_component.check_rec(product_ids[:])
                
        return True
            
    
    @api.one
    @api.constrains('bom_id', 'bom_ids', 'product_id', 'state')
    def _check_recursion(self):
        """ Check BoM recursion
         @return: Boolean (if recursion : return false)
        """
        self.check_rec()

    
    #===========================================================================
    # Onchange
    #===========================================================================
    
    @api.onchange('product_id', 'prod_family_id', 'type')
    def _onchange_product_id(self):
        """
            Au changement du produit, changement de la catégorie de l'uom et de la référence
        """
        if self.type == 'family':
            self.uom_id = self.prod_family_id and self.prod_family_id.uom_id or False
            self.name = self.prod_family_id and self.prod_family_id.name or '/'
            self.product_id = False
        else:
            self.uom_id = self.product_id and self.product_id.uom_id or False
            self.name = self.product_id and self.product_id.code or '/'
            self.prod_family_id = False
    
    
    @api.onchange('uom_id')
    def _onchange_uom_id(self):
        """
            Au changement du produit, changement de la catégorie de l'uom et de la référence
        """
        if self.uom_id:
            self.round = self.uom_id.rounding
            self.uom_category_id = self.uom_id.category_id
        else:
            self.round = 0.0
            self.uom_category_id = False

    
    #===========================================================================
    # Boutons
    #===========================================================================
    
    @api.multi
    def wkf_draft(self):
        self.write({'state': 'draft'})
        if not self.bom_id and self.bom_ids:
            self.bom_ids.write({'state':'draft'})
    
    
    @api.multi
    def wkf_active(self):
        self.write({'state': 'active'})  
        if not self.bom_id and self.bom_ids:
            self.bom_ids.write({'state':'active'})
        
        if not self.env.context.get('no_compute_price', False):
            self.action_compute_price()
    
    
    @api.multi
    def wkf_obsolete(self):
        self.write({'state': 'obsolete'})  
        if not self.bom_id and self.bom_ids:
            self.bom_ids.write({'state':'obsolete'})
    
    
    def action_compute_all_prices(self):
        """ 
            Calcul du prix unitaire et total de toutes les BoM, des sous produits et des composants en fonction de: BoM, Sub product, Component
        """
        self.env['product.product'].cron_calc_bom_level()

        for routing in self.env['mrp.routing'].search([]):
            routing.action_compute_price()

        bom_query = """
            SELECT bom.id, p.id 
            FROM mrp_bom bom
              JOIN product_product p ON bom.product_id = p.id
            WHERE bom_id is null
            ORDER BY p.bom_level ASC
                """
        self.env.cr.execute(bom_query)
        res = self.env.cr.fetchall()
        if res:
            for x in res:
                self.browse(x[0]).action_compute_price()
            
        return True
    
    
    @api.multi
    def action_compute_price(self):
        """ 
            Calcul du prix unitaire et total de la BoM, des sous produits et des composants en fonction de: BoM, Sub product, Component
        """
        for bom in self:
            bom.routing_ids.action_compute_price()
            bom.function_compute_price(button=True, type=bom.type, product=bom.product_id, serie_eco=bom.price_qty, prod_family=bom.prod_family_id)
            
        return True  
    
    
    def function_return_product_component(self):
        """
            Fonction qui retourne le produit du composant
        """
        return self.product_id
    
    
    def function_compute_price(self, button=False, type='normal', product=False, serie_eco=1, prod_family=False):
        """ 
            Fonction qui permet de calculer prix unitaire et total de la BoM ou du produit final, des sous produits et des composants en fonction de: BoM, Sub product, Component
            Attention la serie_eco doit être passé dans l'UoM de la nomenclature
            Le prix unitaire est retourné dans l'UoM de la nomenclature
        """
        price_unit_variable_bom = 0.0
        price_unit_fixed_bom = 0.0
        price_unit_fixed_bom_coeff = 0.0
        price_unit_variable_bom_coeff = 0.0
        efficiency = 1
        bom = self
        product_id = product and product.id or False
        prod_family_id = prod_family and prod_family.id or False
        # Calcul des composants
        currency_price_return = bom.company_id and bom.company_id.currency_id or False
        for component in bom.bom_ids:
            price_unit_fixed_bom, price_unit_variable_bom, price_unit_fixed_bom_coeff, price_unit_variable_bom_coeff = component.function_compute_price_component(price_unit_fixed_bom, price_unit_variable_bom, price_unit_fixed_bom_coeff, price_unit_variable_bom_coeff, efficiency, 
                                                                                                       serie_eco, prod_family_id, product_id, 
                                                                                                       button, bom, currency_price_return)
        
        price_unit_variable_subproduct = 0.0
        price_unit_fixed_subproduct = 0.0
        # Calcul des sous produits
        for subproduct in bom.subproduct_ids:
            #Si l'on ne modifie pas le prix du sous produit
            if subproduct.is_valid_priceunit:
                #Calcul prix total du sous produit
                if subproduct.type == 'fixed':
                    price_unit_fixed_subproduct += subproduct.price_unit * subproduct.quantity * efficiency
                else:
                    price_unit_variable_subproduct += subproduct.price_unit * subproduct.quantity * efficiency
                    
            #Si on modifie le prix du sous produit
            else:
                #Calcul du prix unitaire du produit
                subproduct_efficiency = subproduct.efficiency
                if subproduct.product_id.supply_method =='buy':
                    if subproduct.type == 'fixed':
                        qty_calcul = subproduct.quantity
                    else:
                        qty_calcul = bom.quantity and subproduct.quantity * serie_eco / bom.quantity or subproduct.quantity * serie_eco
                    
                    qty_calcul = qty_calcul * subproduct_efficiency   
                    price_unit_subproduct = bom.compute_price_component_buy(subproduct.product_id, qty_calcul, subproduct.uom_id, currency_price_return)
                else:
                    price_unit_subproduct = bom.compute_price_component_produce(subproduct.product_id, subproduct.quantity)
                
                if button:
                    subproduct.write({'price_unit':price_unit_subproduct})
                    
                #Calcul prix total du sous produit
                if subproduct.type == 'fixed':
                    price_unit_fixed_subproduct += price_unit_subproduct * subproduct_efficiency * subproduct.quantity * efficiency
                else:
                    price_unit_variable_subproduct += price_unit_subproduct * subproduct_efficiency * subproduct.quantity * efficiency
        
        qty_bom = bom.quantity or 1.0
        if bom.is_subtract_price_subproduct:
            price_total_bom = price_unit_fixed_bom + (price_unit_variable_bom * serie_eco / qty_bom) - (price_unit_variable_subproduct * serie_eco / qty_bom) - price_unit_fixed_subproduct
            price_unit_bom = price_total_bom / serie_eco
            price_total_bom_coeff = price_unit_fixed_bom_coeff + (price_unit_variable_bom_coeff * serie_eco / qty_bom) - (price_unit_variable_subproduct * serie_eco / qty_bom) - price_unit_fixed_subproduct
            price_unit_bom_coeff = price_total_bom_coeff / serie_eco
        else:
            price_total_bom = price_unit_fixed_bom + (price_unit_variable_bom * serie_eco / qty_bom)
            price_unit_bom = price_total_bom / serie_eco
            price_total_bom_coeff = price_unit_fixed_bom_coeff + (price_unit_variable_bom_coeff * serie_eco / qty_bom)
            price_unit_bom_coeff = price_total_bom_coeff / serie_eco
        
        if button:
            bom.write({'price_unit': price_unit_bom, 'component_total_price': price_total_bom, 'price_last_date': fields.Datetime.now(), 'price_unit_coeff': price_unit_bom_coeff})
            #Creation de ligne dans le historique de coût
            list_currency_prod_ids = self.env['technical.data.config.settings'].get_param('list_currency_prod_ids')
            bom_currency_rcs = bom.company_id.currency_id
            if list_currency_prod_ids:
                for list_currency_prod in self.env['list.currency.production'].search([('id', 'in', list_currency_prod_ids)], order='sequence asc'):
                    price_list_currency_prod = bom_currency_rcs.compute(price_unit_bom, list_currency_prod.currency_id, round=False)
                    if price_unit_bom_coeff != price_unit_bom:
                        price_list_currency_prod_coeff = bom_currency_rcs.compute(price_unit_bom_coeff, list_currency_prod.currency_id, round=False)
                    else:
                        price_list_currency_prod_coeff = price_list_currency_prod
                    
                    routing_first_price_list_currency_prod = bom_currency_rcs.compute(bom.routing_first_price, list_currency_prod.currency_id, round=False)
                    if bom.routing_first_id.price_unit_coeff != bom.routing_first_price:
                        routing_first_price_list_currency_prod_coeff = bom_currency_rcs.compute(bom.routing_first_id.price_unit_coeff, list_currency_prod.currency_id, round=False)
                    else:
                        routing_first_price_list_currency_prod_coeff = routing_first_price_list_currency_prod
                        
                    vals_mbch = {
                                    'currency_id': list_currency_prod.currency_id.id,
                                    'price_qty': bom.price_qty,
                                    'price': price_list_currency_prod,
                                    'bom_id': bom.id,
                                    'user_id': self.env.user.id,
                                    'routing_first_price': routing_first_price_list_currency_prod,
                                    'production_cost_price': price_list_currency_prod + routing_first_price_list_currency_prod}
                    
                    base_coeff = vals_mbch['production_cost_price'] and (price_list_currency_prod_coeff+routing_first_price_list_currency_prod_coeff) / vals_mbch['production_cost_price'] or 0
                    vals_mbch_other = bom.get_vals_bom_cost_history(price_list_currency_prod, price_list_currency_prod_coeff, 
                                                                    routing_first_price_list_currency_prod, routing_first_price_list_currency_prod_coeff, base_coeff)
                    vals_mbch.update(vals_mbch_other)
                    self.env['mrp.bom.cost.history'].create(vals_mbch)
            else:
                vals_mbch = {
                                'currency_id': bom_currency_rcs.id,
                                'price_qty': bom.price_qty,
                                'price': price_unit_bom,
                                'bom_id': bom.id,
                                'user_id': self.env.user.id,
                                'routing_first_price': bom.routing_first_price,
                                'production_cost_price': price_unit_bom + bom.routing_first_price}
                
                base_coeff = vals_mbch['production_cost_price'] and (price_unit_bom_coeff+bom.routing_first_id.price_unit_coeff) / vals_mbch['production_cost_price'] or 0
                vals_mbch_other = bom.get_vals_bom_cost_history(price_unit_bom, price_unit_bom_coeff, bom.routing_first_price, bom.routing_first_id.price_unit_coeff, base_coeff)
                vals_mbch.update(vals_mbch_other)
                self.env['mrp.bom.cost.history'].create(vals_mbch)
                
            return True  
        else:
            return price_unit_bom, price_total_bom
    
    
    def get_vals_bom_cost_history(self, price_bom, price_coeff, routing_first_price, routing_first_price_coeff, base_coeff):
        """
            Fonction qui permet de rajouter dans la creation d'un enregistrement dans l'historique de coût des infos (mrp_ftpr_gergonne) pour les nomenclatures
        """
        return {}
    
    
    def function_compute_price_component(self, price_unit_fixed_bom, price_unit_variable_bom, price_unit_fixed_bom_coeff, price_unit_variable_bom_coeff, efficiency, 
                                         serie_eco, prod_family_id, product_id, button, bom, currency_price_return):
        """
            Fonction qui permet de calculer le prix d'un composant
        """
        component = self
        product_component = component.function_return_product_component()
        #Si l'on ne modifie pas le prix du composant
        if component.is_valid_priceunit:
            #Calcul prix unitaire de la bom
            if component.type_component == 'fixed':
                price_unit_fixed_bom += component.price_unit * component.quantity * efficiency
            elif component.type_component == 'formula':
                qty_component_compute, efficient_unit_qty = component.function_qty_component_compute(type, serie_eco, prod_family_id=prod_family_id, product_id=product_id)
                price_unit_fixed_bom += component.price_unit * qty_component_compute * efficiency
            else:
                price_unit_variable_bom += component.price_unit * component.quantity * efficiency
                
        #Si on modifie le prix du composant
        else:
            #Calcul du prix unitaire du produit
            efficiency_component = component.efficiency and 1 / component.efficiency or 1
            if product_component.supply_method == 'buy':
                if component.type_component == 'fixed':
                    qty_calcul = component.quantity
                elif component.type_component == 'formula':
                    qty_component_compute, efficient_unit_qty = component.function_qty_component_compute(type, serie_eco, prod_family_id=prod_family_id, product_id=product_id)
                    qty_calcul = qty_component_compute or 0
                else:
                    qty_calcul = bom.quantity and component.quantity * serie_eco / bom.quantity or component.quantity * serie_eco
                
                qty_calcul = qty_calcul * efficiency_component
                price_unit_component = bom.compute_price_component_buy(product_component, qty_calcul, component.uom_id, currency_price_return)
            else:
                qty_component_compute, efficient_unit_qty = component.function_qty_component_compute(type, serie_eco, prod_family_id=prod_family_id, product_id=product_id)
                price_unit_component = bom.compute_price_component_produce(product_component, qty_component_compute)
            
            
            #Calcul prix unitaire de la bom
            if component.type_component in ('fixed', 'formula'):
                qty_component_compute, efficient_unit_qty = component.function_qty_component_compute(type, serie_eco, prod_family_id=prod_family_id, product_id=product_id)
                price_temp = price_unit_component * efficiency_component * qty_component_compute * efficiency
                price_unit_fixed_bom += price_temp
                component_price_unit_coeff = price_temp * component.base_coeff
                price_unit_fixed_bom_coeff += component_price_unit_coeff
            else:
                price_temp = price_unit_component * efficiency_component * component.quantity * efficiency
                price_unit_variable_bom += price_temp
                component_price_unit_coeff = price_temp * component.base_coeff
                price_unit_variable_bom_coeff += component_price_unit_coeff
                price_temp = bom.quantity and price_temp / bom.quantity or price_temp
                component_price_unit_coeff = bom.quantity and component_price_unit_coeff / bom.quantity or component_price_unit_coeff
            
            if button:
                #Creation de ligne dans le historique de coût
                component.write({'price_unit': price_unit_component, 'price_unit_no_coeff': price_temp, 'component_price_unit_coeff': component_price_unit_coeff})
                list_currency_prod_ids = self.env['technical.data.config.settings'].get_param('list_currency_prod_ids')
                bom_currency_rcs = bom.company_id.currency_id
                if list_currency_prod_ids:
                    for list_currency_prod in self.env['list.currency.production'].search([('id', 'in', list_currency_prod_ids)], order='sequence asc'):
                        price_list_currency_prod = bom_currency_rcs.compute(price_temp, list_currency_prod.currency_id, round=False)
                        if component_price_unit_coeff != price_list_currency_prod:
                            price_list_currency_prod_coef = bom_currency_rcs.compute(component_price_unit_coeff, list_currency_prod.currency_id, round=False)
                        else:
                            price_list_currency_prod_coef = price_list_currency_prod
                            
                        vals_mcch = {
                                        'currency_id': list_currency_prod.currency_id.id,
                                        'price_qty': bom.price_qty,
                                        'price': price_list_currency_prod,
                                        'component_id': component.id,
                                        'user_id': self.env.user.id,}
                        vals_mcch_other = component.get_vals_component_cost_history(price_list_currency_prod, price_list_currency_prod_coef, component.base_coeff)
                        vals_mcch.update(vals_mcch_other)
                        self.env['mrp.component.cost.history'].create(vals_mcch)
                else:
                    vals_mcch = {
                                    'currency_id': bom_currency_rcs.id,
                                    'price_qty': bom.price_qty,
                                    'price': price_temp,
                                    'component_id': component.id,
                                    'user_id': self.env.user.id,}
                    vals_mcch_other = component.get_vals_component_cost_history(price_temp, component_price_unit_coeff, component.base_coeff)
                    vals_mcch.update(vals_mcch_other)
                    self.env['mrp.component.cost.history'].create(vals_mcch)
    
        return price_unit_fixed_bom, price_unit_variable_bom, price_unit_fixed_bom_coeff, price_unit_variable_bom_coeff
    
    
    def get_vals_component_cost_history(self, price, price_coeff, coeff):
        """
            Fonction qui permet de rajouter dans la creation d'un enregistrement dans l'historique de coût des infos (mrp_ftpr_gergonne) pour les composants
        """
        return {}
    
    
    @api.multi
    def action_return_formula_component(self):
        data_pool = self.env['ir.model.data']
        action_model, action_id = data_pool.get_object_reference('mrp', 'act_mrp_component_formula')
        if action_model:
            action_pool = self.env[action_model]
            action = action_pool.browse(action_id).read()[0]
            action['res_id'] = self.id
            action['target'] = 'new'
            res = action
            return res
    
    @api.multi
    def action_return_true(self):
        return True
    
    @api.multi
    def button_return_list_component_product(self):
        for bom in self:
            product_ids = [line.product_id.id for line in bom.bom_ids if line.product_id]
            return {
                    'name': _('Component product'),
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'product.product',
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'domain': [('id', 'in', product_ids)],
                } 
    
    
    #===========================================================================
    # Foncions
    #===========================================================================
                    
                    
    def _bom_find(self, product_id, product_uom, options=None, no_active=False, date=False):
        """ Finds BoM for particular product and product uom.
        :param product_id: Selected product.
        :type product_id: int
        :param product_uom: Unit of measure of a product.
        :type product_uom: recordset
        :param options: List of related options.
        :type options: List of int.
        :param date: date si non date du jour.
        :type date: date.
        :return: False or BoM id.
        """
        if not date:
            date = fields.Date.today()
        
        args1 = ['&', '&', '&', '&', ('state', '=', 'active'), 
                               ('product_id', '=', product_id), 
                               ('bom_id', '=', False), 
                               ('type', '!=', 'family'), 
                               '|', '&', ('stop_date', '>=', date), 
                               ('start_date', '<=', date),
                               '|', '&', ('start_date', '=', False), 
                               ('stop_date', '=', False),
                               '|', '&', ('start_date', '=', False), 
                               ('stop_date', '>=', date),
                               '&', ('start_date', '<=', date), 
                               ('stop_date', '=', False)]

        boms = self.search(args1)
        if no_active and not boms:
            args1 = ['&', '&', '&',  ('product_id', '=', product_id), 
                               ('bom_id', '=', False), 
                               ('type', '!=', 'family'), 
                               '|', '&', ('stop_date', '>=', date), 
                               ('start_date', '<=', date),
                               '|', '&', ('start_date', '=', False), 
                               ('stop_date', '=', False),
                               '|', '&', ('start_date', '=', False), 
                               ('stop_date', '>=', date),
                               '&', ('start_date', '<=', date), 
                               ('stop_date', '=', False)]
            boms = self.search(args1)
            
        if not boms:
            prod_family_id = self.env['product.product'].browse(product_id).read(['prod_family_id'], load='_classic_write')
            if prod_family_id and prod_family_id[0] and prod_family_id[0]['prod_family_id']:
                args1 = ['&', '&', '&', '&', ('state', '=', 'active'), 
                                   ('prod_family_id', '=', prod_family_id[0]['prod_family_id']), 
                                   ('bom_id', '=', False), 
                                   ('type', '=', 'family'), 
                                   '|', '&', ('stop_date', '>=', date), 
                                   ('start_date', '<=', date),
                                   '|', '&', ('start_date', '=', False), 
                                   ('stop_date', '=', False),
                                   '|', '&', ('start_date', '=', False), 
                                   ('stop_date', '>=', date),
                                   '&', ('start_date', '<=', date), 
                                   ('stop_date', '=', False)]
                boms = self.search(args1)
            
        ids = boms.ids
        result = False
        flag = False
        if options:
            for option in options:
                # Si encore aucune bom n a ete choisie
                if not flag:
                    for bom in boms:
                        # Prend la BoM qui a la propriete recherche
                        if bom.option_id and  bom.option_id == option:
                            result = bom
                            flag = True
                            break
                            
                    # Si aucune BoM ne correspond renvoie la premiere venue
                    if not result:
                        bom_without_prop = self.search([('id', 'in', ids), ('option_id', '=', False)], limit=1)
                        result = bom_without_prop and bom_without_prop[0] or False
                else:
                    break
                
        # Si aucune propriete ne correspond renvoie la BoM sans propriete
        else:
            bom_without_prop = self.search([('id', 'in', ids), ('option_id', '=', False)], limit=1)
            result = bom_without_prop and bom_without_prop[0] or False
        
        return result
    
    
    def compute_price_component_buy(self, product, quantity, uom, currency_price_return, supplier=False, sinfo_brw=False):
        """ Compute price Component buy
            retun price unit in uom product
            :param: product: product component.
            :type: product: recordset: product.product
            :param: quantity: quantity of product.
            :type: quantity: float
            :param: quantity: quantity of product.
            :type: quantity: float
            :param: uom: recordset de l'unité de gestion
            :type: uom: recordset
            :param: currency_price_return: recordset de la devise dans laquelle on souhaite retouner le prix
            :type: currency_price_return: recordset
            :return: Prix unitaire
        """
        if product.cost_method == 'supplier_pl':
            if not supplier or not sinfo_brw:
                for sinfo in product.sinfo_ids:
                    supplier = sinfo.partner_id
                    sinfo_brw = sinfo
                    break
            
            priceliste_unit_uoi = product.get_price_purchase(supplier, False, currency_price_return=currency_price_return, qty_uom=quantity, uom=uom, 
                                                             force_price=True, state_dev=True, type='pricelist')
            if priceliste_unit_uoi and priceliste_unit_uoi.sinfo_id:
                price = priceliste_unit_uoi.price * (1 + (priceliste_unit_uoi.sinfo_id.customs_duties/100)) * (1 + (priceliste_unit_uoi.sinfo_id.other_expenses/100))
                devise_price = priceliste_unit_uoi.sinfo_id.currency_id
                price_unit_uoi = product._calcul_price_rate_devise(devise_price, price, currency_price_return)
            elif priceliste_unit_uoi:
                price_unit_uoi = priceliste_unit_uoi.price
            else:
                price_unit_uoi = 0
            
            purchase_factor = self.env['technical.data.config.settings'].get_param('purchase_factor') or 1
            price_unit_uoi = price_unit_uoi * purchase_factor
            if sinfo_brw and price_unit_uoi:
                qtys = product.get_qtys_unit(price_unit_uoi, 
                             uom_id=uom, 
                             sec_uom_id=sinfo_brw.uop_id, 
                             uoi_id=sinfo_brw.uoi_id, 
                             by_field='uoi', 
                             dual_unit=product.dual_unit, 
                             dual_unit_type=product.dual_unit_type, 
                             factor=sinfo_brw.factor, 
                             divisor=sinfo_brw.divisor,
                             with_raise=True,
                             with_round=False)
                price_unit = 'uom_qty' in qtys and qtys['uom_qty'] or price_unit_uoi
            else:
                price_unit = price_unit_uoi
        else:
            if product.uom_id.id != uom.id:
                uom_product = product.uom_id
                factor = product.uom_id.factor or 1
                divisor = uom.factor or 1
                price_unit_uom = product.purchase_cost_price
                price_dico = product.get_qtys_unit(price_unit_uom, 
                                 uom_id=uom_product, 
                                 sec_uom_id=uom, 
                                 uoi_id=uom, 
                                 by_field='uom', 
                                 dual_unit=product.dual_unit, 
                                 dual_unit_type=product.dual_unit_type, 
                                 factor=factor, 
                                 divisor=divisor,
                                 with_raise=True,
                                 with_round=False)
            
                price_unit = 'uoi_qty' in price_dico and price_dico['uoi_qty'] or product.purchase_cost_price
            else:
                price_unit = product.purchase_cost_price
                
        return price_unit
    
    
    def compute_price_component_produce(self, product, quantity):
        """ Compute price Component produce
            retun price unit in uom product
        :param product: product component.
        :type product: recordset: product.product
        :param quantity: quantity of product.
        :type quantity: float
        :return: Prix unitaire
        """
#         price_unit = product.compute_production_cost_price(quantity=quantity) or 0.0
        price_unit = product.production_cost_price
        return price_unit
    
    
    def compute_qty_component(self, qty_component, round_component, eff_component, qty_bom, qty_wo, type_component, formula='', args_parameters_list=[]):
        """
            Fonction qui permet de calculer la quantité d'un composant
            :return: la qté (float) et l'efficacité unitaire
        """
        
        if not qty_bom:
            qty_bom = 1
            
        if not qty_wo:
            qty_wo = 1

        qty_produce = qty_wo / qty_bom
        
        if not eff_component:
            eff_component = 1
        
        if not qty_component:
            qty_component = 1
        
        qty = 0
        efficient_unit_qty = 0
        # Calcul de la quantité par rapport à l'efficacité
        quantity_consum = qty_component * (1/eff_component)
        # Si la consommation du composant est variable
        if type_component == 'variable':
            qty = (quantity_consum * qty_produce)
            efficient_unit_qty = qty / qty_wo or qty_component
        # Si la consommation du composant est formule
        elif type_component == 'formula':
            qty = self.compute_qty_formula(formula, qty_component, eff_component, qty_bom, qty_wo, args_parameters_list)
        # Si la consommation du composant est fixe
        else:
            qty = quantity_consum
        
        if round_component:
            qty = roundingUp(qty, round_component)

        return qty, efficient_unit_qty
    
    
    def compute_qty_formula(self, formula, qty_component, eff_component, qty_bom, qty_wo, args_parameters_list=[]):
        qty = 0
        if formula:
            try:
                exp = re.compile("""param\[['"][^'"]{0,}['"]\]{1}""")
                param_obj = self.env['parameter.dimension']
                param_list = exp.findall(formula)
                param = {}
                if param_list:
                    param_list = list(set(param_list))
                    for v in param_list:
                        v = v[7:-2]
                        args_parameter = [('name', '=', v)]
                        if args_parameters_list:
                            args_parameter.extend(args_parameters_list)
                            
                        param_ids = param_obj.search(args_parameter, limit=1)
                        if param_ids:
                            param[v] = param_ids[0].value
                        else:
                            raise except_orm(_('Error'), _('No parameter (%s) in product.')%(v))
                       
                qty = eval(formula)
            except:
                qty = 0.0
        return qty
    
    
    def find_bom_head(self, product):
        """
            Fonction qui permet de retourner toutes les nomenclatures qui a le produit comme composant
            :return: la liste d'id
        """
        request = """select 
                        bom_id 
                     from
                        mrp_bom
                     where
                        product_id = %d
                        and bom_id is not null """%(product.id)
        self.env.cr.execute(request)
        res = self.env.cr.fetchall()  
        if res:
            res_ids = [x[0] for x in res]
        else:
            res_ids = []

        return res_ids
    
    
    def compute_bom_routing_for_product(self, product, uom=False, options=None, with_raise=True):
        """
            Fonction qui permet de retourner la nomenclature et la gamme d'un produit
        """
        routing = False
        mo_obj = self.env['mrp.manufacturingorder']
        res_onchange_product= mo_obj.onchange_product_id(product,  options)
        if not uom:
            uom = res_onchange_product['uom'] or product.uom_id

        bom = res_onchange_product['bom'] or self._bom_find(product.id, uom.id, date=fields.Date.today(), options=options)
        if bom and bom.routing_ids:
            routing = res_onchange_product['routing'] or bom and bom.routing_ids and bom.routing_ids[0] or False

        if (not bom or not routing) and with_raise:
            raise except_orm(_('Error'), _('Please check the product, a routing and BoM.'))
        
        return bom, routing
    
    
    def compute_price_product_produce(self, serie_eco, bom, routing, option_ids=[]):
        """
            Fonction qui calcule le prix d'un produit fabriqué
        """
        price_unit_routing, price_total_routing, total_time_routing, waiting_time_next_ope_routing = routing.function_compute_price(button=False, serie_eco=serie_eco, option_ids=option_ids)
        price_unit_bom, price_total_bom = bom.function_compute_price(button=False, type=bom.type, product=bom.product_id, serie_eco=serie_eco, prod_family=bom.prod_family_id)
        
        return price_unit_bom, price_total_bom, price_unit_routing, price_total_routing
    
    
    @api.multi
    def copy(self, default=None):
        """
            Copie d'OT
        """
        
        if not default:
            default = {}
            
        default['state'] = 'draft'
        return super(mrp_bom, self).copy(default=default)

    
class mrp_option(models.Model):
    """ 
    TODO 
    """
    _name = 'mrp.option'
    _description = 'TODO'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    group_id = fields.Many2one('mrp.option.group', string='Option Group', required=True, ondelete='restrict')
    description = fields.Text(string='Description')
    price_unit = fields.Float(string='Price unit', default=0.0, digits=dp.get_precision('Product price'))
    
    @api.multi
    def unlink(self):
        """
            On empêche la suppression de l'option si elle est utilisée dans une vente
        """
        sale_line_option_obj = self.env['sale.order.line.option']
        for option in self:
            option_rel_rs = sale_line_option_obj.search([('option_id', 'in', option.id)], limit=1)
            if option_rel_rs:
                raise except_orm(_('Error'), _('The option %s is used in a sale line. Please delete the option reference in '
                                               'the sale line before delete it')%(option.name))
        
        return super(mrp_option, self).unlink()
    


class mrp_option_group(models.Model):
    """ 
    TODO 
    """
    _name = 'mrp.option.group'
    _description = 'TODO'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    description = fields.Text(string='Description')



class mrp_bom_revision(models.Model):
    """ 
    Bill of Material Revision 
    """
    _name = 'mrp.bom.revision'
    _description = 'Bill of Material Revision'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    desciption = fields.Text(string='Description')
    date = fields.Date(string='Modification Date', default=lambda self: fields.date.today()) 
    indice = fields.Char(string='Revision', size=16, required=False)
    last_indice = fields.Char(string='Last indice', size=64, required=False)
    author_id = fields.Many2one('res.users', string='Author', required=False, ondelete='restrict', default=lambda self: self.env.uid)
    bom_id = fields.Many2one('mrp.bom', string='BoM', required=False, ondelete='cascade')
   
        

class mrp_subproduct(models.Model):
    """ 
    Sub product 
    """
    _name = 'mrp.subproduct'
    _description = 'Sub product'
    _rec_name = 'product_id'
    _order = 'sequence asc, id asc'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    @api.model
    def _type_get(self):
        return [
                ('fixed', _('Fixed')),
                ('variable', _('Variable')),
                       ]
    
    @api.one
    def _compute_price_total(self):
        self.price_total = self.price_unit and self.quantity and self.price_unit * self.quantity * self.efficiency or 0.0
    
    
    sequence = fields.Integer(string='Sequence', default=0, required=False)
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='restrict')
    quantity = fields.Float(string='Quantity', default=1.0, required=True, digits=dp.get_precision('Product quantity'))
    uom_id = fields.Many2one('product.uom', string='UOM', required=True, ondelete='restrict')
    uom_category_id = fields.Many2one('product.uom.category', related='product_id.uom_id.category_id', string="UOM category", readonly=True)
    type = fields.Selection('_type_get', string='Quantity Type', required=True, default='variable', help="Define how the quantity of byproducts will be set on the production orders using this BoM.\
                 'Fixed' depicts a situation where the quantity of created byproduct is always equal to the quantity set on the BoM, regardless of how many are created in the production order.\
                  By opposition, 'Variable' means that the quantity will be computed as\
                    '(quantity of byproduct set on the BoM / quantity of manufactured product set on the BoM * quantity of manufactured product in the production order.)'")
    bom_id = fields.Many2one('mrp.bom', string='Bom', required=False, ondelete='cascade')
    round = fields.Float(string='Round', default=0, digits=dp.get_precision('Technical Product Round'), required=True)
    efficiency = fields.Float(string='Efficiency', default=1, digits=dp.get_precision('Product Efficiency'), required=True)
    option_id = fields.Many2one('mrp.option', string='Option', required=False, ondelete='restrict')
    price_unit = fields.Float(string='Price unit', default=0.0, digits=dp.get_precision('Price technical'), required=False)
    price_total = fields.Float(string='Price total', compute='_compute_price_total', store=False, digits=dp.get_precision('Price technical'))
    is_valid_priceunit = fields.Boolean(string='Valid price unit', default=False)
    
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
            Au changement du produit, changement de la catégorie de l'uom et de la référence
        """
        self.uom_id = self.product_id and self.product_id.uom_id or False
        self.uom_category_id = self.product_id and self.product_id.uom_id and self.product_id.uom_id.category_id or False



class mrp_bom_modif_component(models.Model):
    """ 
    Remplacement de composants dans toutes les nomenclatures 
    """
    _name = 'mrp.bom.modif.component'
    _description = 'Remplacement de composants dans toutes les nomenclatures'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('validate', _('Validate')),
                       ]
        
    name = fields.Char(required=True)
    reason = fields.Char(required=True, size=256, string="Reason")
    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='restrict', default=lambda self: self.env.uid)
    product_id = fields.Many2one('product.product', string='Replacing component', required=True, ondelete='restrict')
    new_product_id = fields.Many2one('product.product', string='New component', required=True, ondelete='restrict')
    component_ids = fields.One2many('mrp.bom.modif.component.line', 'modif_component_id',  string='Components', copy=True)
    uom_id = fields.Many2one('product.uom', string='UoM', required=False, ondelete='restrict')
    state = fields.Selection('_state_get', string='State', default='draft')
    
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
            Au changement du produit, changement des lignes de composants
        """
        l = []
        for component in self.component_ids:
            l.append((2, component.id))
            
        if self.product_id:
            bom_obj = self.env['mrp.bom']
            component_ids = bom_obj.search([('bom_id', '!=', False), ('product_id', '=', self.product_id.id), ('state', '!=', 'obsolete')])
            if component_ids:
                for component in component_ids:
                    l.append({'component_id': component.id})
                    
            self.uom_id = self.product_id.uom_id and self.product_id.uom_id or False
        else:
            self.new_product_id = False
            self.uom_id = False
            
        self.component_ids = l


    #===========================================================================
    # Boutons
    #===========================================================================
    @api.multi
    def wkf_validate(self):
        #Boutton permettant de remplacer le composant dans toutes les nomenclatures 
        if not self.component_ids: 
            raise except_orm(_('Error'), _('There is not bom.'))
        
        if not self.new_product_id: 
            raise except_orm(_('Error'), _('There is not new product.'))
        
        for x in self.component_ids:
            x.component_id.write({'product_id': self.new_product_id.id, 'product_efficiency': 0.0, 'name': self.new_product_id.code})
            
        self.write({'state':'validate'})
        return True



class mrp_bom_modif_component_line(models.Model):
    """ 
    Remplacement de composants dans toutes les nomenclatures 
    """
    _name = 'mrp.bom.modif.component.line'
    _description = 'Remplacement de composants dans toutes les nomenclatures'
    _rec_name = "component_id"
    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('active', _('Active')),
                ('obsolete', _('Obsolete')),
                       ]
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    component_id = fields.Many2one('mrp.bom', string='Component', required=True, ondelete='cascade')
    bom_id = fields.Many2one('mrp.bom', string='BoM', related='component_id.bom_id', required=False, readonly=True)
    modif_component_id = fields.Many2one('mrp.bom.modif.component', string='Parent', required=False, ondelete='cascade')
    state_bom = fields.Selection('_state_get', related='component_id.bom_id.state', string='State', readonly=True)
    uom_id = fields.Many2one('product.uom', string='UOM', related='component_id.uom_id', required=False, readonly=True)
    quantity = fields.Float(string='Quantity', digits=dp.get_precision('Product quantity'), related='component_id.quantity', required=False, 
                            readonly=True)
    
    #===========================================================================
    # Onchange
    #===========================================================================
    
    @api.onchange('component_id')
    def _onchange_component_id(self):
        """
            Au changement du produit, changement des lignes de composants
        """
        self.bom_id = self.component_id and self.component_id.bom_id
        self.state_bom = self.component_id and self.component_id.state or ''
        self.uom_id = self.component_id and self.component_id.uom_id
        self.quantity = self.component_id and self.component_id.quantity or 0.0



class mrp_area(models.Model):
    """ 
    Atelier 
    """
    _name = 'mrp.area'
    _description = 'Atelier'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    description = fields.Text(string='Description')
    company_id = fields.Many2one('res.company', string='Company', required=False, ondelete='restrict', default=lambda self: self.env.user.company_id)
    active = fields.Boolean(string='Active', default=True)


class mrp_resource(models.Model):
    """ 
    Resource 
    """
    _inherit = 'mrp.resource'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    area_id = fields.Many2one('mrp.area', string='Area', required=False, ondelete='restrict')
    limit_loading = fields.Float(string='Limit loading', default=1.0, required=False)
    
    def additional_function_domain(self, arg):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de mrp_resource
        """
        arg0, arg1, arg_1 = super(mrp_resource, self).additional_function_domain(arg)
        if arg[0] == 'double_resource':
            arg0 = 'id'
            arg1 = arg[1]
            arg_1 = [x[1] for x in arg[-1] if x[0] != 2]
        
        if arg[0] == 'change_resource':
            arg0 = 'id'
            arg1 = arg[1]
            rl_res_cat = self.env['mrp.rl.resource.category'].browse(arg[-1])
            resources_ids = [x.resource_id.id for x in rl_res_cat.rl_resource_ids if x.resource_id]
            if not resources_ids:
                resources_rcs = self.env['mrp.resource'].search([('category_resource_ids','=',rl_res_cat.category_id.id)])
                if resources_rcs:
                    resources_ids = resources_rcs.ids
            arg_1 = resources_ids
        elif arg[0] == 'find_resource_for_wo':
            arg0 = 'id'
            arg1 = 'in'
            wo_read = self.env['mrp.workorder'].browse(arg[-1]).read(['routing_line_id'], load='_classic_write')
            rl_resource_categ_ids = self.env['mrp.rl.resource.category'].search([('routing_line_id', '=', wo_read[0]['routing_line_id'])])
            resource_ids = []
            for rl_resource_categ in rl_resource_categ_ids:
                if rl_resource_categ.rl_resource_ids:
                    for x in rl_resource_categ.rl_resource_ids:
                        resource_ids.append(x.resource_id.id)
                else:
                    for x in rl_resource_categ.category_id.resource_ids:
                        resource_ids.append(x.id)
            
            arg_1 = list(set(resource_ids))
                    
        return arg0, arg1, arg_1
    
    

class mrp_workorder(models.Model):
    """ 
        Workorder 
    """
    _name = 'mrp.workorder'
    _description = 'Workorder'
    _order = 'mo_id desc, sequence asc'

    @api.multi
    def name_get(self):
        """
            Name get des wo [sequence]name
        """
        result = []
        for event in self:
            if event.mo_id:
                name = '%s[%s]'%(event.mo_id.name, event.sequence)
            else:
                name = '%s[%s]'%(event.name, event.sequence)
            
            result.append((event.id, name))

        return result
    
    
    @api.multi
    def copy(self, default=None):
        """
            Copie d'OT
        """
        if not self._context.get('ok_copy', False):
            raise except_orm(_('Error'), _('Impossible to copy WO.'))
            
        return super(mrp_workorder, self).copy(default=default)
    
    
    @api.multi
    def unlink(self):
        for wo in self:
            if wo.state not in ('draft', 'cancel'):
                raise except_orm(_('Error'), _('Impossible to delete a work order if its state is not draft or cancel (%s[%d]).')%(wo.mo_id.name, wo.sequence))
                
            # Suppression des mouvements avant le WO pour passer dans le unlink de stock.move (ne passe pas dedans avec ondelete cascade)
            move_rs = wo.rm_done_ids + wo.fp_done_ids + wo.fp_draft_ids + wo.rm_draft_ids
            if move_rs:
                move_rs.unlink()
            
            if wo.next_wo_ids and wo.prev_wo_ids:
                next_wo_ids = []
                for next_wo in wo.next_wo_ids:
                    next_wo_ids.append((4, next_wo.id))
                    
                wo.prev_wo_ids.write({'next_wo_ids': next_wo_ids})
            
            
        return super(mrp_workorder, self).unlink()
    
    
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
    
    
    @api.one
    @api.depends('wo_resource_ids', 'wo_resource_ids.total_time_theo', 'wo_resource_ids.total_time_real', 'is_subcontracting', 
                 'is_supplier_delay_subc', 'routing_line_id', 'planned_start_date', 'wo_resource_ids.nb_product_parallel', 'planned_end_date')
    def _compute_times(self):
        """
            Fonction qui calcule:
                - Le temps de réel
                - Le temps théorique
                - L'écart de temps
        """
        total_time_theo = 0.0
        total_time_real = 0.0
        
        if self.is_supplier_delay_subc and self.is_subcontracting:
            total_time_theo = self.first_resource_id and self.first_resource_id.calendar_id and self.first_resource_id.calendar_id.get_compute_hours_interval(self.planned_start_date, self.planned_end_date) or 0.0
            for wo_resource in self.wo_resource_ids.read(['total_time_real']):
                total_time_real += wo_resource['total_time_real']
        else:
            for wo_resource in self.wo_resource_ids:
                total_time_theo += wo_resource.total_time_theo
                total_time_real += wo_resource.total_time_real
        
        self.total_time_theo = total_time_theo
        self.total_time_real = total_time_real
        self.difference = total_time_theo and ((total_time_real - total_time_theo) * 100 / total_time_theo)
    
    
    @api.one
    @api.depends('wo_resource_ids', 'wo_resource_ids.resource_id', 'wo_resource_ids.resource_id.type', 'wo_resource_ids.sequence')
    def _compute_first_resource(self):
        """
            Fonction qui récupère la première ressource et sa première catégorie
        """
        wo_resource_id = self.env['mrp.wo.resource'].search([('wo_id', '=', self.id)], order='sequence asc', limit=1)
        self.first_resource_id = wo_resource_id and wo_resource_id.resource_id and wo_resource_id.resource_id.id or False
        self.categ_first_resource_id = wo_resource_id and wo_resource_id.resource_category_id and wo_resource_id.resource_category_id.id or False
        self.first_wo_resource_id = wo_resource_id and wo_resource_id.id or False
        if wo_resource_id and wo_resource_id.resource_id:
            resource_vals = wo_resource_id.resource_id.read(['area_id', 'type'], load='_classic_write')
            self.area_first_resource_id = resource_vals[0]['area_id']
            self.is_subcontracting = resource_vals[0]['type'] == 'subcontracting' or False
        else:
            self.is_subcontracting = False
            self.area_first_resource_id = False


    @api.one
    @api.depends('workorder_produce_ids')
    def _compute_real_date_end(self):
        """
            Au mise done de l'OT on vient mettre la date de fin de la dernière déclaration
        """
        produce_end_id = self.env['mrp.wo.produce'].search([('wo_id', '=', self.id)], order='date desc', limit=1)
        self.real_end_date = produce_end_id and produce_end_id.read(['date'])[0]['date'] or ''
    
    
    @api.one
    @api.depends('resource_timetracking_ids', 'workorder_produce_ids')
    def _compute_real_date_start(self):
        """
            A déclaration de temps on vient mettre la date de début de l'ot
        """
        timetracking_start_id = self.env['resource.timetracking'].search([('wo_id', '=', self.id)], order='start_date asc', limit=1)
        if timetracking_start_id:
            self.real_start_date = timetracking_start_id.start_date
        else:
            produce_start_id = self.env['mrp.wo.produce'].search([('wo_id', '=', self.id)], order='date asc', limit=1)
            self.real_start_date = produce_start_id and produce_start_id.date or ''
    
    
    @api.one
    def _compute_availability_rm(self):
        """
            Date de disponibilitée des matières premières
        """
        move_obj = self.env['stock.move']
        product_obj = self.env['product.product']
        # 1. Récupération des délais
        d_delays = {}
        for move in move_obj.search([('wo_incoming_id', '=', self.id), 
                                     ('state', 'not in', ('done', 'cancel')), 
                                     '|', ('not_covered_qty', '>', 0), ('state', '=', 'draft')]).read(['supply_method', 'product_id'], load='_classic_write'):
            if move['supply_method'] == 'buy' and move['product_id'] not in d_delays:
                d_delays[move['product_id']] = product_obj.browse(move['product_id']).get_default_supply_delay()
                
        l_delays = d_delays.values()
        self.availability_delay_rm = l_delays and max(l_delays) or 0
        
        # 2. Date maximum
        in_date = move_obj.search([('wo_incoming_id', '=', self.id), ('state', '=', 'waiting'), 
                                   ('covered_by_stock_percent', '<', 100), ('supply_method', '=', 'buy')], order='in_date desc', limit=1).read(['in_date'])
        self.availability_date_rm = in_date and in_date[0]['in_date'] or False
    
    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('waiting', _('Waiting')),
                ('plan', _('Plan')),
                ('ready', _('Ready')),
                ('progress', _('In progress')),
                ('pause', _('Pause')),
                ('done', _('Done')),
                ('cancel', _('Cancel')),
                       ]
        
        
    @api.one
    @api.depends('mo_id', 'mo_id.product_id', 'mo_id.quantity', 'mo_id.uom_id')
    def _compute_mo_id(self):
        """
            Fonction qui récupère UDG, le produit final et la quantité de la production
        """ 
        if self.mo_id:
            mo_vals = self.mo_id.read(['product_id', 'uom_id'], load='_classic_write')
            self.final_product_id = mo_vals[0]['product_id']
            self.uom_id = mo_vals[0]['uom_id']
        else:
            self.final_product_id = False
            self.uom_id = False
    
#     
#     @api.one
#     def _compute_cost(self):
#         self.theo_mp_cost = 0.0
#         self.theo_produce_cost = 0.0
#         self.theo_subcontracting_cost = 0.0
#         self.theo_total_cost = 0.0
#         self.real_mp_cost = 0.0
#         self.real_produce_cost = 0.0
#         self.real_subcontracting_cost = 0.0
#         self.real_total_cost = 0.0
        
        
    @api.one
    def _compute_availability(self): 
        """
            Fonction qui permet de calculer la disponibilité de l'ot
        """ 
        self.availability = self.compute_availability()
    
    
    def _search_availability(self, operator, value):
        """
            Fonction search de la disponibilité de l'ot
        """ 
        wo_rcs = self.search([('state', 'not in', ('done','cancel'))])
        wo_ids = []
        for wo in wo_rcs:
            availability = wo.compute_availability()
            if value == 100 and availability >= 100:
                wo_ids.append(wo.id)
            elif value == 0.1 and availability < 100 and availability > 0:
                wo_ids.append(wo.id)
            else:
                pass
            
        return [('id', 'in', wo_ids)]
            
            
    @api.one
    def _compute_advancement(self):  
        """
            Fonction qui calcule l'avancement
            Qty produite/qty a fabriqué*100 si terminé on est a 100 % 
        """ 
        self.advancement = self._function_compute_advancement() 
    
    
    def _function_compute_advancement(self, with_state=True):  
        """
            Fonction qui calcule l'avancement
            Qty produite/qty a fabriqué*100 si terminé on est a 100 % 
        """ 
        advancement = 0.0
        qty_final = self.quantity or 1.0
        qty_produce = 0.0
        if self.state == 'done' and with_state:
            advancement = 100
        else:
            for wo_produce in self.workorder_produce_ids:
                if wo_produce.state == 'done' and wo_produce.uom_id and wo_produce.qty_ok:
                    qty_produce += self.env['product.uom']._compute_qty_obj(wo_produce.uom_id, wo_produce.qty_ok, self.uom_id, with_raise=False)
            
            advancement = (qty_produce / qty_final) * 100

        return advancement 
        
        
    @api.one
    @api.depends('planned_start_date')
    def _compute_planned_start_date(self):
        """
        Fonction qui calcule la semaine, le mois et l'année de la date de début plannifié
        """
        wo_vals = self.read(['planned_start_date']) 
        if wo_vals[0]['planned_start_date']:
            date = '%s'%(wo_vals[0]['planned_start_date'][0:10])
            date = datetime.datetime.strptime(date, '%Y-%m-%d')
            isocal = date.isocalendar()
            
            # Sur 2 caractères
            if len(str(isocal[1])) == 1:
                self.week_number = '0%s'%(str(isocal[1]))
            else:
                self.week_number = str(isocal[1])
            
            # Sur 2 caractères
            if len(str(date.month)) == 1:
                self.month = '0%s'%(str(date.month))
            else:
                self.month = str(date.month)
                
            self.year = str(isocal[0])
        else:
            self.week_number = '00'
            self.month = '00'
            self.year = '0'
        
        
    @api.one
    @api.depends('rm_draft_ids', 'rm_draft_ids.color_priority_need')
    def _compute_color_priotity_need_move(self):
        """
            Fonction qui permet de connaitre la couleur de l'OT en fonction des matières premières non done et cancel
        """ 
        color_priority_need_read = self.env['stock.move'].search_read([('id', 'in', self.rm_draft_ids.ids)], ['color_priority_need'], limit=1, order='color_priority_need desc')
        color_priority_need = color_priority_need_read and color_priority_need_read[0]['color_priority_need'] or 0
        self.color_priority_need_move = color_priority_need
    
    
    @api.one
    @api.depends('name', 'mo_level')
    def _compute_label(self):
        self.label = '%s%s%s%s%s'%((self.mo_level) * 4 * '-', self.final_product_id.read(['name'])[0]['name'], '[',self.sequence ,']')
    
    
    def _search_color_line(self, operator, value):
        """
            Fonction search de la couleur de l'OT en fonction des matières premières non done et cancel
        """ 

        request = """select x.wo_id from
        (select max(color_priority_need) as color, wo_incoming_id as wo_id from stock_move where wo_incoming_id is not null and state not in ('done', 'cancel') group by wo_incoming_id)  x
        where x.color = %d"""%(value)
        self.env.cr.execute(request)
        res_ids = self.env.cr.fetchall()          
        return [('id', 'in', res_ids)]


    @api.model        
    def _state_timetracking_get(self):
        return [
                ('waiting', _('Waiting')),
                ('setting', _('Setting')),
                ('production', _('Production')),
                ('cleaning', _('Cleaning')),
                ('stop', _('Stop'))
                       ]
            
            
    @api.one
    def _compute_is_subc_no_regul(self):
        """
            Fonction qui permet de savoir s'ils restent des matiéres premières envoyées et non utilisées dans les ots terminés de st
        """ 
        is_subc_no_regul = False
        if self.is_subcontracting:
            product_dics = self.env['subcontracting.regul.wiz'].compute_qty_regul_st(self)
            for product_dic in product_dics:
                if product_dics[product_dic]['remaining_qty'] > 0:
                    is_subc_no_regul = True
                    break
            
        self.is_subc_no_regul = is_subc_no_regul
        
        
    def _search_is_subc_no_regul(self, operator, value):
        """
            Fonction search qui permet de retourner tous les ots où ils restent des matiéres premières envoyées et non utilisées dans les ots terminés de st
        """ 
        res_ids = []
        srw_obj = self.env['subcontracting.regul.wiz']
        now = datetime.datetime.now()
        date = fields.Date.to_string(now - timedelta(days=60))
        wo_rcs = self.search([('is_subcontracting', '=', True), ('real_end_date', '>=', date)])
        for wo in wo_rcs:
            product_dics = srw_obj.compute_qty_regul_st(wo)
            for product_dic in product_dics:
                if product_dics[product_dic]['remaining_qty'] > 0:
                    res_ids.append(wo.id)
                    break
                  
        return [('id', 'in', res_ids)]   
    
    
    @api.one
    @api.depends('planned_end_date')
    def _compute_search_date(self):
        """
            Fonction qui calcule les champs utilisés dans la recherche
        """
        is_week = False
        is_next_week = False
        is_month = False
        
        wo_vals = self.read(['planned_start_date'])
        if wo_vals[0]['planned_start_date']:
            date = '%s'%(wo_vals[0]['planned_start_date'][0:10])
            date = datetime.datetime.strptime(date, '%Y-%m-%d')
            isocal = date.isocalendar()
            now = datetime.datetime.now()
            now_iso = now.isocalendar()
            week_num = now_iso[1]
            year_num = now_iso[0]
            if isocal[1] == week_num and year_num == isocal[0]:
                is_week = True
                
            if isocal[1] == 52 and (year_num + 1) == isocal[0] and (week_num + 1) == isocal[1]:
                is_next_week = True
                
            if now.month == date.month and year_num == isocal[0]:
                self.is_month = True

        else:
            self.week_number = '00'
            self.month = '00'
            self.year = '0'
        
        self.is_week = is_week
        self.is_next_week = is_next_week
        self.is_month = is_month
    
    
    def _search_is_week(self, operator, value):
        """
            Fonction search qui permet de retrouver tous les OTs qui sont de cette semaine
        """
        request = """
        SELECT 
            x.id 
        FROM
            (SELECT     
            to_char(planned_start_date, 'WW') as week_date,
            to_char(planned_start_date, 'YYYY') as year_date,
            to_char((current_date), 'WW') as week_now,
            to_char((current_date), 'YYYY') as year_now,
            id
             FROM 
             mrp_workorder 
             WHERE
             planned_start_date is not null)  x
        
        where 
            x.week_now = x.week_date and
            x.year_now = x.year_date"""
        self.env.cr.execute(request)
        res_ids = self.env.cr.fetchall()          
        return [('id', 'in', res_ids)]
    
    
    def _search_is_next_week(self, operator, value):
        """
            Fonction search qui permet de retrouver tous les OTs qui sont de la semaine d'après semaine
        """
        request = """
        SELECT 
            x.id 
        FROM
            (SELECT     
            to_char(planned_start_date, 'WW') as week_date,
            to_char(planned_start_date, 'YYYY') as year_date,
            to_char((current_date + interval '1 week'), 'WW') as week_now,
            to_char((current_date + interval '1 week'), 'YYYY') as year_now,
            id
             FROM 
             mrp_workorder 
             WHERE
             planned_start_date is not null)  x
        
        where 
            x.week_now = x.week_date and
            x.year_now = x.year_date"""
        self.env.cr.execute(request)
        res_ids = self.env.cr.fetchall()          
        return [('id', 'in', res_ids)]
    
    
    def _search_is_month(self, operator, value):
        """
            Fonction search qui permet de retrouver tous les OTs qui sont dans le mois
        """
        request = """
        SELECT 
            x.id 
        FROM
            (SELECT     
            to_char(planned_start_date, 'MM') as week_date,
            to_char(planned_start_date, 'YYYY') as year_date,
            to_char((current_date), 'MM') as week_now,
            to_char((current_date), 'YYYY') as year_now,
            id
             FROM 
             mrp_workorder 
             WHERE
             planned_start_date is not null)  x
        
        where 
            x.week_now = x.week_date and
            x.year_now = x.year_date"""
        self.env.cr.execute(request)
        res_ids = self.env.cr.fetchall()          
        return [('id', 'in', res_ids)]
    
    
    @api.one
    def _compute_is_purchase_already(self):
        """
            Fonction qui permet de savoir s'ils restent des matiéres premières envoyées et non utilisées dans les ots terminés de st
        """ 
        is_purchase_already = False
        if self.is_subcontracting and self.wo_subc_pol_rm_ids:
            is_purchase_already = True
            
        self.is_purchase_already = is_purchase_already
    
    
    @api.one
    @api.depends()
    def _compute_produce_total_qty(self):
        produce_total_qty = 0
        uom_obj = self.env['product.uom']
        for wo_produce in self.workorder_produce_ids:
            if wo_produce.state == 'done':
                produce_total_qty += uom_obj._compute_qty_obj(wo_produce.uom_id, wo_produce.qty_ok, self.uom_id)
                produce_total_qty += uom_obj._compute_qty_obj(wo_produce.uom_id, wo_produce.qty_hs, self.uom_id)
                
        self.produce_total_qty = produce_total_qty
        
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    # Entête
    name = fields.Char(required=True, size=256)
    label = fields.Char(string='Label', compute='_compute_label', size=512)
    mo_id = fields.Many2one('mrp.manufacturingorder', string='MO', required=True, ondelete='cascade', select=True)
    sale_line_id = fields.Many2one('sale.order.line', string='Sale line', readonly=True)
    customer_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    requested_date = fields.Date(string='Requested Date', readonly=True)
    final_product_id = fields.Many2one('product.product', string='Final Product', compute='_compute_mo_id', store=True)
    quantity = fields.Float(string='Quantity', default=1.0)
    uom_id = fields.Many2one('product.uom', string='UoM', compute='_compute_mo_id', store=True)
    availability = fields.Float(string='Availability', compute='_compute_availability', search='_search_availability')
    advancement = fields.Float(string='Advancement', compute='_compute_advancement')
    state = fields.Selection('_state_get', default='draft', string='State')
    sequence = fields.Integer(string='Sequence', default=0, required=False)
    level = fields.Integer(default=0, required=False)
    mo_level = fields.Integer(default=0, required=False)
    sorting_level = fields.Char(default='00000000000000000000000000000000000000000000000000', required=False, size=64)
    
    # Component
    rm_draft_ids = fields.One2many('stock.move', 'wo_incoming_id',  string='Draft Raw Material', domain=[('state','not in',('done','cancel')), ('not_usable', '=', False)], copy=False)
    rm_done_ids = fields.One2many('stock.move', 'wo_incoming_id',  string='Done Raw Material', domain=[('state','in',('done','cancel')), ('not_usable', '=', False)], copy=False)
    fp_draft_ids = fields.One2many('stock.move', 'wo_outgoing_id',  string='Draft Final Product', domain=[('state','not in',('done','cancel')), ('not_usable', '=', False)], copy=False)
    fp_done_ids = fields.One2many('stock.move', 'wo_outgoing_id',  string='Done Final Product', domain=[('state','in',('done','cancel')), ('not_usable', '=', False)], copy=False)
    
    # Resource
    first_wo_resource_id = fields.Many2one('mrp.wo.resource', string='First wo resource', compute='_compute_first_resource', store=True)
    first_resource_id = fields.Many2one('mrp.resource', string='First resource', compute='_compute_first_resource', store=True)
    categ_first_resource_id = fields.Many2one('mrp.resource.category', string='Category of first resource', compute='_compute_first_resource', store=True)
    area_first_resource_id = fields.Many2one('mrp.area', string='Area', compute='_compute_first_resource', store=True)
    is_subcontracting = fields.Boolean(string='Is Subcontracting', compute='_compute_first_resource', store=True)
    total_time_real = fields.Float(string='Total Time Real', digits=dp.get_precision('Time'), compute='_compute_times', store=True)
    total_time_theo = fields.Float(string='Total Time Theo', digits=dp.get_precision('Time'), compute='_compute_times', store=True)
    difference = fields.Float(string='Difference %', digits=dp.get_precision('Product quantity'), compute='_compute_times', store=True)
    wo_resource_ids = fields.One2many('mrp.wo.resource', 'wo_id',  string='Resources', copy=True)
    is_supplier_delay_subc = fields.Boolean(string='Supplier delay for subcontracting', default=False, readonly=False)
    additional_resource_ids = fields.One2many('mrp.wo.additional.resource', 'wo_id', string="Addtionnal resources")
    allow_operator_add = fields.Boolean(string='Allow to add operators', default=False)
    modif_time_int = fields.Integer(string='Modif time int', default=0, required=False)
    
    # Approvisionnement
    procurement_ids = fields.One2many('procurement.order', 'origin_wo_id',  string='string')
    consumed_service_ids = fields.One2many('mrp.wo.consumed.service', 'wo_id',  string='Consumed service', copy=False)
    
    # Planification
    min_date = fields.Datetime(string='Min Date')
    max_date = fields.Datetime(string='Max date')
    planned_start_date = fields.Datetime(string='Planned Start Date')
    planned_end_date = fields.Datetime(string='Planned End Date')
    real_start_date = fields.Datetime(string='Real Start Date', compute='_compute_real_date_start', store=True)
    real_end_date = fields.Datetime(string='Real End Date', compute='_compute_real_date_end', store=True)
    waiting_time_next_ope = fields.Float(string='Waiting time for the next operation', default=1.0, required=False , digits=dp.get_precision('Product quantity'))
    percentage_overlap_next_ope = fields.Float(string='% of overlap with the next operation', default=0.0, required=False)
    is_forecast = fields.Boolean(string='Forecast', default=False)
    company_id = fields.Many2one('res.company', string='Company', required=False, ondelete='restrict', default=lambda self: self.env.user.company_id)
    routing_line_id = fields.Many2one('mrp.routing.line', string='Routing line', required=False, ondelete='restrict')
    index = fields.Float(string='Index', default=0.0, required=False, digits=dp.get_precision('Product quantity'))
    compute_availability_material = fields.Boolean(string='Availability compute only material', default=False)
    availability_date_rm = fields.Datetime(string=_('Availability Date Raw Material'), compute='_compute_availability_rm')
    availability_delay_rm = fields.Integer(string=_('Availability delay Raw Material'), compute='_compute_availability_rm')
    availability_simulation = fields.Datetime(string=_('Availability simulation'))
    is_at_earlier = fields.Boolean(string='Is at earlier', default=False)
    
    # Déclaration
    workorder_produce_ids = fields.One2many('mrp.wo.produce', 'wo_id',  string='Workorder Produce', copy=False)
    note_tracability = fields.Text(string='Note tracability')
    close_wo_prev = fields.Boolean(string='Close Workorder previous', default=False)
    availability_force = fields.Boolean(string='To ignore availability', default=False)
    declare_tablet_product = fields.Boolean(string='Declare the tablet production', default=False)
    workorder_consumption_ids = fields.One2many('mrp.wo.consumption', 'wo_id',  string='Workorder Consumption', copy=False)
    produce_more = fields.Boolean(string='Produce more', default=False)
    corrected_time = fields.Boolean(string='Time Correction', default=False)
    correct_time = fields.Boolean(string='Time Ok', default=False)
    resource_timetracking_ids = fields.One2many('resource.timetracking', 'wo_id',  string='Resource Time Tracking')
    label_consumed_ids = fields.One2many('mrp.label.consumption', 'wo_id',  string='Labels Consumed')
    label_production_ids = fields.One2many('mrp.label.production', 'wo_id',  string='Labels production')
    
    # Outillages et qualités
    tool_ids = fields.One2many('mrp.wo.tools', 'wo_id',  string='Tools', copy=True)
    consign_ids = fields.One2many('mrp.wo.consign', 'wo_id',  string='Consign', copy=True)
    rl_document_ids = fields.Many2many('document.openprod', 'wo_document_openprod_rel', 'wo_id', 'document_id',  string='Routing line documents', copy=True)

    # Coût
    theo_rm_cost = fields.Float(string='Material first cost', default=0.0)#, compute='_compute_cost')
    theo_produce_cost = fields.Float(string='Produce cost', default=0.0, digits=dp.get_precision('Product price'))#, compute='_compute_cost')
    theo_subcontracting_cost = fields.Float(string='Subcontracting cost', default=0.0, digits=dp.get_precision('Product price'))#, compute='_compute_cost')
    theo_total_cost = fields.Float(string='Total cost', default=0.0, digits=dp.get_precision('Product price'))#, compute='_compute_cost')
    real_rm_cost = fields.Float(string='Material first cost', default=0.0, digits=dp.get_precision('Product price'))#, compute='_compute_cost')
    real_produce_cost = fields.Float(string='Produce cost', default=0.0, digits=dp.get_precision('Product price'))#, compute='_compute_cost')
    real_subcontracting_cost = fields.Float(string='Subcontracting cost', default=0.0, digits=dp.get_precision('Product price'))#, compute='_compute_cost')
    real_total_cost = fields.Float(string='Total cost', default=0.0, digits=dp.get_precision('Product price'))#, compute='_compute_cost')

    # Notes et divers
    next_wo_ids = fields.Many2many('mrp.workorder', 'mrp_wo_rel', 'prev_wo_ids', 'next_wo_ids', string='Next Workorder')
    prev_wo_ids = fields.Many2many('mrp.workorder', 'mrp_wo_rel', 'next_wo_ids', 'prev_wo_ids', string='Previous Workorder')
    note_planned = fields.Text(string='Note planned')
    note_manufacturing = fields.Text(string='Note manufacturing')
    color_priority_need_move = fields.Integer(compute='_compute_color_priotity_need_move', store=False, search='_search_color_line')
    split_id = fields.Many2one('mrp.workorder', string='Workorder Split', required=False, ondelete='set null')
    
    # Date
    month = fields.Selection('_month_get', string='Month', compute='_compute_planned_start_date', store=True)
    week_number = fields.Char(string='Week number', size=2, compute='_compute_planned_start_date', store=True) 
    year = fields.Char(string='Year', size=4, compute='_compute_planned_start_date', store=True)
    
    # Timetracking
    state_timetracking = fields.Selection('_state_timetracking_get', default='stop',  string='Timetracking state', readonly=1)

    # Subcontracting
    wo_subc_pol_rm_ids = fields.One2many('purchase.order.line', 'wo_rm_subcontracting_id',  string='Subcontracting Purchase Line RM', copy=False)
    wo_subc_pol_fp_ids = fields.One2many('purchase.order.line', 'wo_fp_subcontracting_id',  string='Subcontracting Purchase Line FP', copy=False)
    wo_subc_move_rm_ids = fields.One2many('stock.move', 'wo_rm_subcontracting_id', domain=[('state', '!=', 'cancel'), '|', ('type_subcontracting', '!=', 'indirect'), '&', ('type_subcontracting', '=', 'indirect'), ('type', '=', 'out')],  string='Subcontracting Move RM', copy=False)
    wo_subc_move_fp_ids = fields.One2many('stock.move', 'wo_fp_subcontracting_id',  string='Subcontracting Move FP', copy=False)
    subc_move_counterpart_ids = fields.One2many('stock.move', 'counterpart_wo_id',  string='Counterpart move', copy=False)
    is_warning_subc = fields.Boolean(string='Warning Subcontracting', default=False)
    warning_subc = fields.Text(string='Warning Subcontracting')
    is_subc_no_regul = fields.Boolean(string='Subc. regul is not ok', compute='_compute_is_subc_no_regul', search='_search_is_subc_no_regul', help='On 60 last days' )
    is_purchase_already = fields.Boolean(string='Purchases were made', compute='_compute_is_purchase_already')
    
    #Search
    is_week = fields.Boolean(string='Is week', compute='_compute_search_date', search='_search_is_week')
    is_next_week = fields.Boolean(string='Is next week', compute='_compute_search_date', search='_search_is_next_week')
    is_month = fields.Boolean(string='Is month', compute='_compute_search_date', search='_search_is_month')
    
    #Lien vers l'étiquette de réparation SAV si l'on doit garder la même étiquette
    label_mo_repair_id = fields.Many2one('stock.label', string='Label MO repaire', required=False, ondelete='restrict')
    produce_total_qty = fields.Float(string='Produce total qty', compute='_compute_produce_total_qty', digits=dp.get_precision('Product quantity'), help="The sum of the quantities manufactured (ok + quarantine, no HS)")
    group_wo_id = fields.Many2one('mrp.group.wo', string='Group', required=False, ondelete='set null')
    
    
    #===========================================================================
    # Boutons
    #===========================================================================
    @api.multi
    def wkf_draft(self, no_recursion_fct=False):
        self.function_stop_timetracking(no_recursion_fct)
        for wo in self:
            wo.state = 'draft'
            wo.state_mo()
            move_rcs = wo.rm_done_ids + wo.fp_done_ids + wo.fp_draft_ids + wo.rm_draft_ids
            move_not_draft_rcs = self.env['stock.move']
            for move in move_rcs:
                if move.state != 'draft':
                    move_not_draft_rcs += move
            
            if move_not_draft_rcs:
                move_not_draft_rcs.wkf_cancel()
                move_not_draft_rcs.wkf_draft_with_aggregate()
    
    
    @api.multi
    def wkf_waiting(self, automatic_purchase=True, is_procur_level_manufact=True, is_procur_level_purchase=True, modif_state=True, no_recursion_fct=False):
        self.function_stop_timetracking(no_recursion_fct)
        move_obj = self.env['stock.move']
        for wo in self:
            if modif_state:
                wo.write({'state': 'waiting'})   
                
            move_rcs = wo.rm_draft_ids + wo.fp_draft_ids
            move_purchase_draft_rcs = []
            move_produce_draft_rcs = []
            for move in move_rcs.read(['state', 'supply_method']):
                if move['state'] == 'draft':
                    if move['supply_method'] == 'produce':
                        move_produce_draft_rcs.append(move['id'])
                    else:
                        move_purchase_draft_rcs.append(move['id'])
            
            if move_produce_draft_rcs and is_procur_level_manufact:
                move_obj.browse(move_produce_draft_rcs).wkf_waiting(automatic_purchase=automatic_purchase)
            
            if move_purchase_draft_rcs and is_procur_level_purchase:
                move_obj.browse(move_purchase_draft_rcs).wkf_waiting(automatic_purchase=automatic_purchase)
            
            if modif_state:
                wo.state_mo()
            
            if wo.is_subcontracting and not move_obj.search([('state', '=', 'waiting'), ('counterpart_wo_id', '=', self.id)], limit=1):
                self.compute_subcontracting_counterpart_move()
        
        self.button_compute_theo_costs()
    
    
    @api.multi
    def wkf_plan(self, no_recursion_fct=False):
        self.function_stop_timetracking(no_recursion_fct)
        for wo in self:
            if not wo.planned_start_date or not wo.planned_end_date:
                raise except_orm(_('Error'), _('We must first plannifier WO.'))
            
            if wo.fp_draft_ids:
                wo.fp_draft_ids.write({'is_confirmed': True})
            
            if wo.is_forecast:
                raise except_orm(_('Error'), _('MO/WO PROVISIONAL can not exceed the waiting state.'))
                
            wo.state = 'plan'
            wo.state_mo()
            
    
    @api.multi
    def wkf_ready(self, no_recursion_fct=False):
        self.function_stop_timetracking(no_recursion_fct)
        for wo in self:
            wo.state = 'ready'
            if wo.is_forecast:
                raise except_orm(_('Error'), _('MO/WO PROVISIONAL can not exceed the waiting state.'))
            
            wo.state_mo()
    
    
    @api.multi
    def wkf_progress(self, no_recursion_fct=False):
        self.function_stop_timetracking(no_recursion_fct)
        for wo in self:
            wo.state = 'progress'
            wo.state_mo()
        
        
    @api.multi
    def wkf_pause(self, no_recursion_fct=False):
        
        self.function_stop_timetracking(no_recursion_fct)
        for wo in self:
            wo.state = 'pause'
            if wo.is_forecast:
                raise except_orm(_('Error'), _('MO/WO PROVISIONAL can not exceed the waiting state.'))
            
            wo.state_mo()
            
        
    @api.multi
    def wkf_done(self, no_recursion_fct=False):
        self.function_stop_timetracking(no_recursion_fct)
        loading_obj = self.env['calendar.loading']
        wo = False
        for wo in self:
            wo.state = 'done'
            if wo.is_forecast:
                raise except_orm(_('Error'), _('MO/WO PROVISIONAL can not exceed the waiting state.'))
            
            wo.state_mo()
            # Annulation des mouvements des MP et PF en attente
            rm_draft_ids = wo.rm_draft_ids
            if wo.rm_draft_ids and wo.rm_done_ids:
                rm_draft_ids = wo.rm_draft_ids - wo.rm_done_ids
            
            fp_draft_ids = wo.fp_draft_ids
            if wo.fp_draft_ids and wo.fp_done_ids:
                fp_draft_ids = wo.fp_draft_ids - wo.fp_done_ids
                
            move_rs = fp_draft_ids + rm_draft_ids
            if move_rs:
                move_rs.wkf_cancel()
                
            # Suppression des lignes de charges 
            loading_delete_rcs = loading_obj.search([('wo_id', '=', wo.id)])
            if loading_delete_rcs:
                loading_delete_rcs.unlink()

            # terminer les ressources additionelles:
            for resource_id in wo.additional_resource_ids:
                if not resource_id.end_date:
                    resource_id.write({'end_date': fields.Datetime.now()})
            
            wo_time_rcs = wo.group_wo_id and wo.group_wo_id.wo_ids or wo
            done_time_rcs = self.env['resource.timetracking'].search([('wo_id', 'in', wo_time_rcs.ids), ('end_date', '=', False)])
            date_time = fields.Datetime.now()
            if done_time_rcs:
                for done_time in done_time_rcs:
                    time_activity = (datetime.datetime.strptime(date_time, DEFAULT_SERVER_DATETIME_FORMAT) - datetime.datetime.strptime(done_time.start_date, DEFAULT_SERVER_DATETIME_FORMAT)) / 3600
                    time_spent = done_time.is_first_resource and done_time.wo_id.group_wo_id and done_time.wo_id.group_wo_id.time_total_theo and time_activity.total_seconds() * done_time.wo_id.total_time_theo / done_time.wo_id.group_wo_id.time_total_theo or time_activity.total_seconds()
                    done_time.write({'end_date': date_time, 'time': time_activity.total_seconds(), 'time_spent': time_spent})
            
            if wo.close_wo_prev:
                wo.close_wo_previous()
            
                
        #Calcul du prix de l'ot
        self.button_compute_real_costs()
        self.button_compute_theo_costs()

        # Cancel mouvement de contrepartie (sous traitance)
        if wo and wo.is_subcontracting:
            wo.cancel_subcontracting_counterpart_move()
        
        #Calcul du prix de l'OF si dernier OT terminé
        mo_ids = [x.mo_id.id for x in self]
        if mo_ids:
            mo_ids = list(set(mo_ids))
            for mo_id in mo_ids:
                last_workorder_rcs = self.search([('mo_id', '=', mo_id), ('state', '=', 'done'), ('id', 'in', self.ids)], order='sequence desc', limit=1)
                if last_workorder_rcs:
                    last_workorder_rcs.mo_id.button_compute_real_costs()
                    last_workorder_rcs.mo_id.button_compute_theo_costs()
                    
    
    @api.multi
    def wkf_cancel(self, no_recursion_fct=False):
        self.function_stop_timetracking(no_recursion_fct)
        loading_obj = self.env['calendar.loading']
        for wo in self:
            wo.write({'state': 'cancel', 'planned_end_date': False, 'planned_start_date': False})
            wo.state_mo()
            # Annulation des déclarations
            if wo.workorder_consumption_ids:
                wo.workorder_consumption_ids.wkf_cancel()
            
            if wo.workorder_produce_ids:
                wo.workorder_produce_ids.wkf_cancel()
            
            # Annulation des mouvements
            move_rs = wo.rm_done_ids + wo.fp_done_ids + wo.fp_draft_ids + wo.rm_draft_ids
            if move_rs:
                move_rs.wkf_cancel()
                
            # Suppression des lignes de charges 
            loading_delete_rcs = loading_obj.search([('wo_id', '=', wo.id)])
            if loading_delete_rcs:
                loading_delete_rcs.unlink()
                
            # Cancel mouvement de contrepartie (sous traitance)
            if wo.is_subcontracting:
                wo.cancel_subcontracting_counterpart_move()
    
    
    @api.multi
    def button_reopen(self):
        """
            Bouton Re ouverture
        """ 
        for wo in self:
            move_cancel_rm = self.env['stock.move'].search([('state', '=', 'cancel'), ('wo_incoming_id', '=', wo.id), ('not_usable', '=', False)])
            if move_cancel_rm:
                wo.aggregate_move(move_cancel_rm, type='rm', waiting_state=True)
            move_cancel_fp = self.env['stock.move'].search([('state', '=', 'cancel'), ('wo_outgoing_id', '=', wo.id), ('not_usable', '=', False)])
            if move_cancel_fp:
                wo.aggregate_move(move_cancel_fp, type='fp', waiting_state=True)
                
            wo.wkf_progress()
            
        return True
            
            
    @api.multi
    def button_split(self):
        """
            Bouton qui split les OTs
        """ 
        for wo in self:
            def get_next_ids(wo_rcs, first=True):
                # Retourne la liste des ids de tous les moves apres celui passé en paramètres
                # a condition qu'il ne soit ni cancel ni done et qu'il n'appartienne pas a un OF
                res = []
                if not first:
                    res.append(wo_rcs.id)
    
                next_wo_ids = wo_rcs.next_wo_ids
                
                if next_wo_ids and len(next_wo_ids) < 2:
                    res.extend(get_next_ids(next_wo_ids, first=False))
                return res
            
            vals = []
            # Création du wizard
            split_wo_obj = self.env['mrp.wo.split']
            next_wo_ids = get_next_ids(wo)
            if next_wo_ids:
                vals = [[0, 0, {'wo_id': wo_id}] for wo_id in next_wo_ids]

            new_rcs = split_wo_obj.create({'wo_id': wo.id, 'line_ids': vals})
            return {
                    'name': _('Split WO'),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'mrp.wo.split',
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'res_id': new_rcs.id,
                    'nodestroy': True,
                    }
    
    
    @api.multi
    def button_availability_simulation_compute(self):
        for wo in self:
            l_dates = self.availability_simulation_compute()
            wo.write({'availability_simulation': l_dates and max(l_dates) or False})
            
        return self.availability_simulation
    
    
    def availability_simulation_compute(self):
        """
            Fonction qui permet des calculer la date de disponibilité de la simulation
        """
        d_dates = {}
        for move in self.env['stock.move'].search([('wo_incoming_id', '=', self.id), 
                                                   ('state', 'not in', ('done', 'cancel')), 
                                                   ('supply_method', '=', 'buy'), ('in_date', '=', False)]):
            product = move.product_id
            if product.id not in d_dates:
                virtual_stock, available_stock = product.get_available_stock(return_real_stock=True)
                move_qty = move.get_product_uom_qty()
                # Stock virtuel < besoin => delai fournisseur
                if virtual_stock < move_qty:
                    d_dates[product.id] = product.get_default_supply_delay(return_date=True, hours=True)[1]
                # Stock réel et stock virtuel >= besoin => AJD
                elif available_stock >= move_qty:
                    d_dates[product.id] = fields.Datetime.now()
                # Stock réel < besoin et stock virtuel >= besoin => Calcul date besoin
                else:
                    d_dates[product.id] = product.get_date_last_stock_min(self.env.user.company_id.warehouse_id.stock_location_id, move_qty, inverse=True)
        
        l_dates = d_dates.values()
        return l_dates
    
    
    @api.multi
    def button_waiting_timetracking(self):
        """
            Bouton qui déclanche les temps de production selon les différentes étapes (waiting)
        """ 
        timetracking_obj = self.env['resource.timetracking']
        for wo in self:
            if wo.state in ('plan', 'ready', 'pause'):
                wo.wkf_progress()
            
            wo_rcs = wo.group_wo_id and wo.group_wo_id.wo_ids or wo
            timetracking_obj.create_wo_timetracking(wo_rcs, activity='waiting', stop=False)
            wo_rcs.write({'state_timetracking': 'waiting'})
        return True
    
    
    @api.multi
    def button_setting_timetracking(self):
        """
            Bouton qui déclanche les temps de production selon les différentes étapes (setting)
        """ 
        timetracking_obj = self.env['resource.timetracking']
        for wo in self:
            if wo.state in ('plan', 'ready', 'pause'):
                wo.wkf_progress()
            
            wo_rcs = wo.group_wo_id and wo.group_wo_id.wo_ids or wo
            timetracking_obj.create_wo_timetracking(wo_rcs, activity='setting', stop=False)
            wo_rcs.write({'state_timetracking': 'setting'})
            
        return True
    
    
    @api.multi
    def button_production_timetracking(self):
        """
            Bouton qui déclanche les temps de production selon les différentes étapes (production)
        """ 
        timetracking_obj = self.env['resource.timetracking']
        for wo in self:
            if wo.state in ('plan', 'ready', 'pause'):
                wo.wkf_progress()
            
            wo_rcs = wo.group_wo_id and wo.group_wo_id.wo_ids or wo
            timetracking_obj.create_wo_timetracking(wo_rcs, activity='production', stop=False)
            wo_rcs.write({'state_timetracking': 'production'})
            
        return True
    
    
    @api.multi
    def button_cleaning_timetracking(self):
        """
            Bouton qui déclanche les temps de production selon les différentes étapes (cleaning)
        """ 
        timetracking_obj = self.env['resource.timetracking']
        for wo in self:
            if wo.state in ('plan', 'ready', 'pause'):
                wo.wkf_progress()
            
            wo_rcs = wo.group_wo_id and wo.group_wo_id.wo_ids or wo
            timetracking_obj.create_wo_timetracking(wo_rcs, activity='cleaning', stop=False)
            wo_rcs.write({'state_timetracking': 'cleaning'})
            
        return True
    
    
    @api.multi
    def button_stop_timetracking(self):
        """
            Bouton qui stop les temps de production
        """ 
        self.function_stop_timetracking()
        return True
    
    
    def function_stop_timetracking(self, no_recursion_fct=False):
        """
            Bouton qui stop les temps de production
        """ 
        timetracking_obj = self.env['resource.timetracking']
        if not no_recursion_fct:
            for wo in self:
                list_wo_rcs = wo.group_wo_id and wo.group_wo_id.wo_ids or wo
                for wo_rcs in list_wo_rcs:
                    if wo_rcs.state in ('ready', 'progress'):
                        wo_rcs.wkf_pause(no_recursion_fct=True)
                        
                timetracking_obj.create_wo_timetracking(list_wo_rcs, activity='', stop=True)
                list_wo_rcs.write({'state_timetracking': 'stop'})
        
        return True
    
    
    #===========================================================================
    # CALCUL DES COUTS THEORIQUES
    #===========================================================================    
    @api.multi
    def button_clear_theo_costs(self):
        self.write({'theo_rm_cost': 0.0,
                    'theo_produce_cost': 0.0,
                    'theo_subcontracting_cost': 0.0,
                    'theo_total_cost': 0.0,})
    
    
    def compute_mo_theo_price(self, move, mo_rss):
        """
            :param mo_rs: Liste de tous les OF à calculer
            :type mo_rs: recordset mrp.manufacturingorder            
        """
        qtys = 0.0
        prices = 0.0
        for mo_rs in mo_rss:
            qtys += mo_rs.quantity
            prices += mo_rs.theo_total_cost
        
        return qtys and ((prices / qtys) * move.get_product_uom_qty()) or 0.0 
        
        
    def get_theo_rm_cost(self):
        """
            Calcul de coût des MP:
            Prix de la (Prix unitaire théorique OF du produit OU prix nomenclature) * quantité du mouvement
        """
        res = 0.0
        bom_obj = self.env['mrp.bom']
        uom_obj = self.env['product.uom']
        if self.mo_id.bom_id:
            for move in self.env['stock.move'].search([('wo_incoming_id', '=', self.id), ('state', '!=', 'cancel')]):
                bom_price = False
                procurement_rs = move.get_procurement()
                if procurement_rs:
                    mo_rs = [proc.mo_id for proc in procurement_rs if proc.mo_id and proc.mo_id.state != 'cancel']
                    if mo_rs:
                        res += self.compute_mo_theo_price(move, mo_rs)
                    else:
                        bom_price = True
                        
                else:
                    bom_price = True
                
                if bom_price:
                    if move.component_id:
                        bom_rcs = move.component_id
                    else:
                        bom_rcs = bom_obj.search([('bom_id', '=', self.mo_id.bom_id.id), ('product_id', '=', move.product_id.id)], limit=1)
                        
                    if bom_rcs:
                        currency_price_return = self.mo_id.company_id and self.mo_id.company_id.currency_id or False
                        price_unit_fixed_bom, price_unit_variable_bom, price_unit_fixed_bom_coeff, price_unit_variable_bom_coeff = bom_rcs.function_compute_price_component(0, 0, 0, 0, 1, move.uom_qty, False, 
                                                                                                                 self.mo_id.bom_id.product_id.id, False, 
                                                                                                                 bom_rcs.bom_id, currency_price_return)
                        
                        qty_bom = bom_rcs.quantity and uom_obj._compute_qty_obj(bom_rcs.uom_id, bom_rcs.quantity, move.uom_id, with_raise=False, with_round=False) or 1
                        qty = move.uom_qty / qty_bom
                        res += (price_unit_fixed_bom_coeff + price_unit_variable_bom_coeff * qty)
                    else:
                        res += 0.0
        return res
    
    
    def get_theo_produce_cost(self):
        res = 0.0
        for resource_line in self.wo_resource_ids:
            res += resource_line.total_time_theo_with_masked * (resource_line.resource_id.hourly_rate or resource_line.resource_category_id.hourly_rate) * (self.routing_line_id and self.routing_line_id.base_coeff or 1.0)
             
        return res
    
    
    def get_theo_subcontracting_cost(self):
        res = 0.0
        if self.is_subcontracting:
            for service in self.consumed_service_ids:
                if service.type == 'variable':
                    res += service.price_total * self.quantity
                else:
                    res += service.price_total
            
        return res
    
    
    def get_theo_costs(self):
        res = {}
        res['theo_rm_cost'] = self.get_theo_rm_cost()
        res['theo_produce_cost'] = self.get_theo_produce_cost()
        res['theo_subcontracting_cost'] = self.get_theo_subcontracting_cost()
        res['theo_total_cost'] = res['theo_rm_cost'] + res['theo_produce_cost'] + res['theo_subcontracting_cost']
        return res
        
        
    @api.multi    
    def button_compute_theo_costs(self):
        costs = 0.0
        for wo in self:
            costs = wo.get_theo_costs()
            wo.write({'theo_rm_cost': costs['theo_rm_cost'], 
                      'theo_produce_cost': costs['theo_produce_cost'], 
                      'theo_subcontracting_cost': costs['theo_subcontracting_cost'], 
                      'theo_total_cost': costs['theo_total_cost'],})
    
        return costs
    
        
    #===========================================================================
    # CALCUL DES COUTS REELS
    #===========================================================================
    @api.multi
    def button_clear_real_costs(self):
        self.write({'real_rm_cost': 0.0,
                    'real_produce_cost': 0.0,
                    'real_subcontracting_cost': 0.0,
                    'real_total_cost': 0.0,})
        
        
    def compute_pol_price(self, move, pol_rs):
        """
            :param pol_rs: Liste de toutes les lignes d'achat à calculer
            :type pol_rs: recordset purchase.order.line            
        """
        qtys = 0
        prices = 0
        for x in pol_rs:
            qtys += x.uom_qty
            prices += x.total_price_currency
            
        return qtys and ((move.get_product_uom_qty() * prices) / qtys) or 0.0
    
    
    def compute_mo_real_price(self, move, mo_rs):
        """
            :param mo_rs: Liste de tous les OF à calculer
            :type mo_rs: recordset mrp.manufacturingorder            
        """
        mo_unit_prices = [0.0]
        for x in mo_rs:
            qtys = 0
            last_mo_rs = x.workorder_ids[-1] 
            for fp_move in last_mo_rs.fp_done_ids:
                if fp_move.state == 'done' and move.product_id.id == fp_move.product_id.id:
                    qtys += fp_move.get_product_uom_qty()
            
            if qtys:
                mo_unit_prices.append(x.real_total_cost / qtys)
            
        return move.get_product_uom_qty() * sum(mo_unit_prices)
        
    
    def get_last_mo_price(self, move):
        mo_obj = self.env['mrp.manufacturingorder']
        mo_rs = mo_obj.search([('product_id', '=', move.product_id.id), ('state', '=', 'done')], limit=1, order='id desc')
        if mo_rs:
            res = self.compute_mo_real_price(move, mo_rs)
        else:
            res = move.product_id.production_cost_price
        
        return res
    
        
    def get_real_rm_cost(self):    
        """
        Si procurement: 
            Acheté: Prix de l'achat en devise société ramené à la quantité du mouvement
            Fabriqué: Prix de l'OF du procurement. Si pas d'OF: Prix du dernier OF. Si pas d'OF: 0
        Si pas de procurement: 
            Acheté: Prix du dernier achats. Si pas d'achat: Prix valorisé fiche produit
            Fabriqué: Prix du dernier OF. Si pas d'OF: 0
        """
        res = 0.0
        pol_obj = self.env['purchase.order.line']
        bom_obj = self.env['mrp.bom']
        for move in self.rm_done_ids:
            currency_price_return = move.company_id and move.company_id.currency_id or False
            if move.state == 'done':
                procurement_rs = move.get_procurement()
                if procurement_rs:
                    # Acheté
                    if move.supply_method == 'buy':
                        pol_rs = [proc.pol_id for proc in procurement_rs if proc.pol_id]
                        res_price = False
                        if not pol_rs:                        
                            pol_rs = pol_obj.search([('product_id', '=', move.product_id.id), 
                                                     ('purchase_state', 'not in', ('draft', 'cancel'))], limit=1, order='id desc')
                        
                        if pol_rs:
                            res_price = self.compute_pol_price(move, pol_rs)
                        else:
                            #Si pas d'achat 
                            #on prend le prix valorisation si différent de 0
                            if  move.product_id.enhanced_price:
                                res_price = move.product_id.enhanced_price * move.get_product_uom_qty()
                            else:
                                price_unit = bom_obj.compute_price_component_buy(move.product_id, move.get_product_uom_qty(), move.product_id.uom_id, currency_price_return)
                                res_price = price_unit * move.get_product_uom_qty()
                                
                        res += res_price
                    else:
                        mo_rs = [proc.mo_id for proc in procurement_rs if proc.mo_id]
                        if mo_rs:
                            res += self.compute_mo_real_price(move, mo_rs)
                        else:
                            res += self.get_last_mo_price(move)
                              
                # Si pas de procurement
                else:
                    # Acheté
                    if move.supply_method == 'buy':
                        pol = pol_obj.search([('product_id', '=', move.product_id.id), 
                                              ('purchase_state', 'not in', ('draft', 'cancel'))], limit=1, order='id desc')
                        if pol:
                            res += pol.uom_qty and ((move.get_product_uom_qty() * pol.total_price_currency) / (pol.uom_qty)) or 0.0
                        else:
                            #Si pas d'achat 
                            #on prend le prix valorisation si différent de 0
                            if  move.product_id.enhanced_price:
                                res_price = move.product_id.enhanced_price * move.get_product_uom_qty()
                            else:
                                price_unit = bom_obj.compute_price_component_buy(move.product_id, move.get_product_uom_qty(), move.product_id.uom_id, currency_price_return)
                                res_price = price_unit * move.get_product_uom_qty()
                            
                            res += res_price
                            
                    # Fabriqué
                    else:
                        res += self.get_last_mo_price(move)
                            
        return res
    
    
    def get_real_produce_cost(self):
        res = 0.0
        resource_obj = self.env['mrp.resource']
        vals = self.env['resource.timetracking'].search_group(fields=['resource_id', 'time'], 
                                                              groupby=['resource_id'], 
                                                              args=[('wo_id', '=', self.id), ('state', 'in', ('validated', 'draft'))],
                                                              sum='time',
                                                              return_dict=True)
        for val in vals:
            res += val['time'] * resource_obj.browse(val['resource_id']).read(['hourly_rate'])[0]['hourly_rate']
             
        return res
    
    
    def get_real_subcontracting_cost(self):
        res = 0.0
        if self.is_subcontracting:
            for pol in self.wo_subc_pol_fp_ids:
                res += pol.total_price_currency
            
        return res
    
    
    def get_real_costs(self):
        res = {}
        res['real_rm_cost'] = self.get_real_rm_cost()
        res['real_produce_cost'] = self.get_real_produce_cost()
        res['real_subcontracting_cost'] = self.get_real_subcontracting_cost()
        res['real_total_cost'] = res['real_rm_cost'] + res['real_produce_cost'] + res['real_subcontracting_cost'] 
        return res
        
        
    @api.multi    
    def button_compute_real_costs(self):
        costs = 0.0
        for wo in self:
            costs = wo.get_real_costs()
            wo.write({'real_rm_cost': costs['real_rm_cost'], 
                      'real_produce_cost': costs['real_produce_cost'], 
                      'real_subcontracting_cost': costs['real_subcontracting_cost'], 
                      'real_total_cost': costs['real_total_cost'],})
        
        return costs
    
    
    @api.multi
    def validate_procurement_rm(self):
        """
            Bouton pour générer l'achat ou la production de la matière première
        """ 
        for wo in self:
            for procurement in wo.procurement_ids:
                if procurement.state == 'draft':
                    procurement.do_default_procurement()
        
        return True
    
    
    @api.multi
    def button_regul_rmst(self):
        """
            Bouton pour générer le wizard de régulation de quantité de soustraitance pour les matières premières
        """ 
        for wo in self:
            wiz_rcs = self.env['subcontracting.regul.wiz'].create_wiz(wo)
            if not wiz_rcs:
                raise except_orm(_('Error'), _('No product.'))
            
            return {'name': _('Regulation'),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'subcontracting.regul.wiz',
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'res_id': wiz_rcs.id,
                    'nodestroy': True}
        
        return True
            
    
    def cancel_subcontracting_counterpart_move(self):
        """
            Recalcul mouvement de contrepartie (sous traitance). Annulation si qty <= 0
        """
        move_counterpart_rcs = self.env['stock.move'].search([('counterpart_wo_id', '=', self.id)])
        if move_counterpart_rcs:
            move_counterpart_rcs.wkf_cancel()
                    
        return True
    
    
    @api.multi
    def compute_subcontracting_counterpart_move(self):
        """
            Recalcul mouvement de contrepartie (sous traitance). Annulation si qty <= 0
        """
        pol_obj = self.env['purchase.order.line']
        move_obj = self.env['stock.move']
        new_qty = 0.0
        if self.state not in ('draft', 'done', 'cancel') and self.consumed_service_ids and self.is_subcontracting:
            service_rs = self.consumed_service_ids[0]
            service_product_rs = service_rs.product_id
            new_qty = self.quantity
            pol_qtys = pol_obj.search_group(fields=['wo_qty'],
                                            groupby=['product_id'],
                                            args=[('purchase_state', 'not in', ('draft', 'cancel')),
                                                  ('wo_fp_subcontracting_id', '=', self.id),
                                                  ('product_id', '=', service_product_rs.id),
                                                  ('purchase_type', '!=', 'open')],
                                            sum='wo_qty',
                                            return_dict=True)
            for pol_qty in pol_qtys:
                new_qty -= pol_qty['wo_qty']
         
        if new_qty <= 0.0:
            self.cancel_subcontracting_counterpart_move()
        else:
            move_rcs = move_obj.search([('state', '=', 'waiting'), ('counterpart_wo_id', '=', self.id)]) or self.create_subcontracting_counterpart_move()
            for move_rc in move_rcs:
                if move_rc.state != 'draft':
                    move_rc.wkf_cancel()
                    new_move_created, new_move_rcs = move_rc.wkf_draft()
                    if new_move_created:
                        move_rc = new_move_rcs
                 
                move_rc.write({'uom_qty': new_qty, 
                               'sec_uom_qty': move_rc.uom_qty and (new_qty * move_rc.sec_uom_qty / move_rc.uom_qty) or 0.0,
                               'uoi_qty': move_rc.uom_qty and (new_qty * move_rc.uoi_qty / move_rc.uom_qty) or 0.0})
                move_rc.wkf_waiting()
                
        return True
    
    
    def create_subcontracting_counterpart_move(self):
        """
            Création d'un mouvement de contrepartie 
            (Comme le mouvement de sous traitance est externe, sans ce mouvement, le stock virtuel ne serait pas mis à jour)
        """
        move_obj = self.env['stock.move']
        location_obj = self.env['stock.location']
        counterpart_move_rcs = self.env['stock.move']
        for move in self.fp_draft_ids:
            if not move.product_id.is_int and move.state == 'waiting':
                # Sous traitance interne (dans le même entrepôt): un seul mouvement de contrepartie de production à l'entrepôt
                if move.location_dest_id.warehouse_id.id == self.company_id.warehouse_id.id:
                    counterpart_move_rcs |= move_obj.create_move(move.product_id, move.location_id.id, move.warehouse_id.input_location_id.id, qty=move.uom_qty, uom=move.uom_id, date=move.date, other_data={'counterpart_wo_id': self.id})
                # Sous traitance externe (entrepôt de sous-traitance): deux mouvements de contrepartie: de production à l'entrepôt
                #     - De sous-traitance à transit
                #     - De transit à l'entrepôt de la société
                else:
                    transit_location_rc = location_obj.get_transfer_location(with_raise=True)
                    counterpart_move_rcs |= move_obj.create_move(move.product_id, move.location_dest_id.id, transit_location_rc.id, qty=move.uom_qty, uom=move.uom_id, date=move.date, other_data={'counterpart_wo_id': self.id})
                    counterpart_move_rcs |= move_obj.create_move(move.product_id, transit_location_rc.id, self.company_id.warehouse_id.input_location_id.id, qty=move.uom_qty, uom=move.uom_id, date=move.date, other_data={'counterpart_wo_id': self.id})
                    
                if counterpart_move_rcs:
                    counterpart_move_rcs.wkf_waiting()
                    
        return counterpart_move_rcs
    
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('mo_id')
    def _onchange_mo_id(self):
        """
            Calcul séquence
        """
        quantity = 1.0
        if self.mo_id:
            quantity = self.mo_id.quantity
            
        self.quantity= quantity


    @api.onchange('label_production_ids', 'declare_tablet_product')
    def _onchange_label_production_ids(self):
        """
            On interdit la déclaration de prod a la tablette si étiquette créée en avance
        """
        if self.label_production_ids:
            self.declare_tablet_product = False
            
            
    @api.onchange('total_time_theo')
    def _onchange_total_time_theo(self):       
        if self.state in ('draft', 'waiting', 'plan', 'ready'):
            self.modif_time_int += 1
        
        
    #===========================================================================
    # Fonctions
    #===========================================================================
    @api.multi
    def print_wo(self):
        """
            Fonction associée au bouton du wo, permet d'imprimer
            des wo
        """
        return True
      
      
    def do_print_wo(self, print_plan=False):
        """ 
            Fonction permettant d'imprimer le wo ainsi que les plans liés à la ligne de gamme
        """
        return True
    
    
    def state_mo(self):
        """ 
            Modification de l'état de l'ordre de fabriquation
            L'état est le même que les OTs, on prend l'état le plus avancé des OTs sauf pour les terminés et annulés, il faut que tous les OTs soient terminés ou annulés
            :return: True
        """
        if self.mo_id:
            workorder_ids = self.search([('mo_id', '=', self.mo_id.id)], order='sequence asc')
            wo_state = [x.state for x in workorder_ids]
            if wo_state:
                wo_state = list(set(wo_state))
                if len(wo_state) == 1:
                    self.mo_id.write({'state': wo_state[0]})
                else:
                    if 'cancel' in wo_state:
                        wo_state.remove('cancel')
                    
                    if len(wo_state) == 1:
                        self.mo_id.write({'state': wo_state[0]})
                    elif 'draft' in wo_state:
                        self.mo_id.write({'state': 'draft'})
                    elif 'waiting' in wo_state:
                        self.mo_id.write({'state': 'waiting'})
                    elif 'plan' in wo_state:
                        self.mo_id.write({'state': 'plan'})
                    elif 'ready' in wo_state or 'progress' in wo_state or 'pause' in wo_state or 'done' in wo_state:
                        if 'progress' in wo_state or 'pause' in wo_state or 'done' in wo_state:
                            self.mo_id.write({'state': 'progress'})
                        else:
                            self.mo_id.write({'state': 'ready'})
                    else: 
                        pass
                    
        return True
    
    
    def close_wo_previous(self):
        """
            On cloture les OTs précédents et on annule les consommations non terminées
        """
        for prev_wo in self.prev_wo_ids:
            if prev_wo.state not in ('done', 'cancel'):
                prev_wo.close_wo_previous()
                prev_wo.wkf_done()
        
        return True

#     
#     def close_wo(self):
#         """ 
#             Fonction qui termine l'OT, il annule les mouvements restant à consommé et à produire
#         """
#         if self.rm_draft_ids:
#             self.rm_draft_ids.wkf_cancel():
#         
#         if self.fp_draft_ids:
#             self.fp_draft_ids.wkf_cancel():
#         
#         self.state = 'done'
#         return True
    
    def recusion_availability_splited(self, wo_splited_rcs, prev_wo_ids, list_wo_use, list_wo_splited=None):   
        """ 
            Fonction recursive qui permet de retrouver tous les OTs splités précédent afin de calculer la quantité total faite des mes OTs précédents 
            :param wo_splited_rcs: Liste des OTs qui sont splités à partir d'un OT
            :type wo_splited_rcs: recordset mrp.workorder
            :param prev_wo_ids: Liste des OTs précédent de l'OT
            :type prev_wo_ids: list integer
            :param list_wo_splited: Liste de tous les OTs précédent (ex: OT2 est un split de OT1 et OT3 est un split de OT2 et OT4 est un split de OT1 donc on a OT1 OT2 OT3 OT4)
            :type list_wo_splited: recordset mrp.workorder
        """
        if not list_wo_splited:
            list_wo_splited = self.env['mrp.workorder']
        
        for wo_splited in wo_splited_rcs:
            # On vérifie que l'ot splité fait partie de la liste des ots précédents
            if wo_splited.id in prev_wo_ids and  wo_splited.id not in list_wo_use:
                if wo_splited.state not in ('cancel'):
                    if wo_splited not in list_wo_splited:
                        # On ajoute l'ot splité à la liste
                        list_wo_splited += wo_splited
                    # On recherche si cette OT à des ots splités
                    new_wo_splited_rcs = self.search([('split_id', '=', wo_splited.id)])
                    # Si oui on relance la fonction
                    if new_wo_splited_rcs:
                        list_wo_splited = self.recusion_availability_splited(new_wo_splited_rcs, prev_wo_ids, list_wo_use, list_wo_splited)
        
        return  list_wo_splited
     
        
    @api.multi
    def compute_level(self, write=True):
        """ 
            Calcul du niveau de l'OT dans l'OF
            :param write: Mise à jour ou non de la base de données
            :type write: boolean
            :return: Dictionnaire {wo_rs: level}
        """
        computed_mo = []
        for wo in self:
            if wo.mo_id not in computed_mo:
                computed_mo.append(wo.mo_id) 
                wo.mo_id.compute_wo_level()
        
        return True
    
    
    @api.multi
    def compute_sorting_level(self, write=True, res=None):
        """ 
            Calcul du niveau de tri pour les vues arboréscentes
            :param write: Mise à jour ou non de la base de données
            :type write: boolean
            :param res: Paramètre utile à la récursion, laisser par défaut
            :type res: dict
            :return: Dictionnaire {wo_rs: level}
        """
        if not res:
            res = {}
            
        proc_obj = self.env['procurement.order']
        self.sorted(key=lambda x: (x.mo_level, x.level))
        count_letter_max = max(_COUNT_LETTER.keys())
        for wo in self:
            if wo not in res:
                # Recherche du parent
                proc = proc_obj.search([('mo_id', '=', wo.mo_id.id), ('state', '!=', 'cancel')], limit=1)
                if proc and proc.move_id.wo_incoming_id:
                    parent_wo = proc.move_id.wo_incoming_id
                    # Calcul du parent si pas encore fait
                    if parent_wo not in res:
                        res = parent_wo.compute_sorting_level(write=False, res=res)
                    
                    res[wo] = list(res[parent_wo])
                else:
                    res[wo] = list('0' * _LEVEL_NUMBER)
                    
                res[wo][wo.mo_level] = _COUNT_LETTER[count_letter_max - wo.level - 1]
                # Si deux OF au même niveau
                i = 2
                res_copy = res.copy()
                del res_copy[wo]
                while res[wo] in res_copy.values():
                    res[wo][wo.mo_level] = _COUNT_LETTER[count_letter_max - wo.level - i]
                    i += 1
                    
        if write:
            for wo, value in res.iteritems():
                wo.write({'sorting_level': ''.join(value)}) 
        
        return res
        
        
    def compute_availability(self, is_availability_force=False):
        """ 
            Fonction qui calcule la disponibilité
            Si dispo forcé coché disponible à 100%
            Si non uniquement sur matière : C'est la dispo min des matières premières non annulées
            Si non C'est la dispo min entre la dispo des matières premières et le min des avancements des OTs précédents non annulés et l'on fait un prorata si des ots ont été splités
            :param self: L' OT  mrp.workorder
            :type self: recordset
            :return: Float la disponibilité
        """
        list_availability = []
        availability = 0.0
        wo_rcs = self
        if wo_rcs.state not in ('done', 'cancel'):
            # Disponibilité forcée
            if wo_rcs.availability_force and is_availability_force:
                availability = 100
            
            else:
                # Partie avancement OT précédent
                # Si le champ "calculer seulement la dispo des MP" n'est pas coché: intégration de la dispo des OT précédents
                if not wo_rcs.compute_availability_material and wo_rcs.prev_wo_ids:
                    prev_wo_ids = wo_rcs.prev_wo_ids.ids
                    list_wo_use = []
                    # On boucle sur chacun des OTs précédents
                    for prev_wo in wo_rcs.prev_wo_ids:
                        list_wo_splited = self.env['mrp.workorder']
                        if prev_wo.state not in ('cancel'):
                            # On teste l'OT afin de savoir si on a déjà pris sa valeur
                            if prev_wo.id not in list_wo_use:
                                # On teste l'OT afin de savoir si c'est un splite et si oui on regarde si l'ot d'origine fait partie de la liste, si oui cette ot sera prise en compte lors du passage de l'ot d'origine
                                if not prev_wo.split_id or prev_wo.split_id.id not in prev_wo_ids:
                                    wo_splited_rcs = self.search([('split_id', '=', prev_wo.id)])
                                    if prev_wo not in list_wo_splited:
                                        list_wo_splited += prev_wo
                                        
                                    if wo_splited_rcs:
                                        # Appel de la fonction de recursion
                                        list_wo_splited = self.recusion_availability_splited(wo_splited_rcs, prev_wo_ids, list_wo_use, list_wo_splited)
                                        
                                    # On calcul l'avance de l'ot en tenant compte de tous les splits
                                    total_qty = 0
                                    total_qty_advancement = 0
                                    for wo_splited in list_wo_splited:
                                        total_qty += wo_splited.quantity
                                        total_qty_advancement += wo_splited.advancement * wo_splited.quantity / 100
                                    
                                    if total_qty:    
                                        list_availability.append(total_qty_advancement * 100 / total_qty)
                                
                                list_wo_use.extend(list_wo_splited.ids)
                
                # Partie dispo matière première
                move_done_and_no_cancel = True
                for rm in wo_rcs.rm_draft_ids:
                    if rm.state not in ('cancel', 'done'):
                        list_availability.append(rm.covered_by_stock_percent)
                    elif rm.state == 'cancel':
                        move_done_and_no_cancel = False
                    
                if list_availability:
                    availability = min(list_availability)
                elif not list_availability and (not wo_rcs.rm_draft_ids or move_done_and_no_cancel) and not wo_rcs.prev_wo_ids:
                    availability = 100.0
        
        return availability
        
        
    def prepare_wo_resource(self, rl_resource_categ, mo, rl_resource_rcs=False, resource_rcs=False, other_data=None):
        """ 
            Préparation des valeurs pour la création d'un enregistrement de l'objet mrp.wo.resource
            :param rl_resource_categ: La categorie de ressource de la ligne de gamme mrp.rl.resource.category
            :type rl_resource_categ: recordset
            :param mo: L'ordre de fabrication mrp.manufacturingorder
            :type mo: recordset
            :param rl_resource_rcs: La ressource de la ligne de gamme mrp.rl.resource
            :type rl_resource_rcs: recordset
            :param resource_rcs: La ressource mrp.resource
            :type resource_rcs: recordset
            :param other_data: dico pour remplir de nouveau champ pour la creation d'une resource de l'OT
            :type other_data: dico des valeurs de l'OT (ex: {'name':'toto',})
            :return: dico de valeurs
        """
        if not rl_resource_rcs and not resource_rcs:
            rl_resource_rcs = self.env['mrp.rl.resource'].search([('rl_category_id','=',rl_resource_categ.id)], order='sequence asc', limit=1)
            
        # Si pas de resource, on prend la première ressource de la categorie
        if rl_resource_rcs:
            production_time = rl_resource_categ.compute_time_production(rl_resource_rcs.type, time=rl_resource_rcs.production_time_seizure, cadence=rl_resource_rcs.cadence, 
                                                            formula=rl_resource_rcs.formula, args_parameters_list=[('mo_id', '=', mo.id)])
            if not production_time:
                production_time = rl_resource_categ.compute_time_production(rl_resource_categ.type, time=rl_resource_categ.production_time_seizure, cadence=rl_resource_categ.cadence, 
                                                            formula=rl_resource_categ.formula, args_parameters_list=[('mo_id', '=', mo.id)])
            
            nb_resource = rl_resource_categ.nb_resource or 1
            vals = {
                        'sequence': rl_resource_categ.sequence,
                        'resource_category_id': rl_resource_categ.category_id.id,
                        'rl_resource_category_id': rl_resource_categ.id,
                        'resource_id': rl_resource_rcs.resource_id.id,
                        'nb_resource': nb_resource,
                        'preparation_time': rl_resource_rcs.preparation_time or rl_resource_categ.preparation_time,
                        'production_time': production_time,
                        'cleaning_time': rl_resource_rcs.cleaning_time or rl_resource_categ.cleaning_time,
                        'preparation_masked_time': rl_resource_rcs.preparation_masked_time or rl_resource_categ.preparation_masked_time,
                        'production_masked_time': rl_resource_rcs.production_masked_time or rl_resource_categ.production_masked_time,
                        'cleaning_masked_time': rl_resource_rcs.cleaning_masked_time or rl_resource_categ.cleaning_masked_time,
                        
                    } 
            if other_data:
                vals.update(other_data)
        else:
            if not resource_rcs:
                resource_rcs = rl_resource_categ.category_id.resource_ids and rl_resource_categ.category_id.resource_ids[0] or False
            
            if resource_rcs:
                production_time = rl_resource_categ.compute_time_production(rl_resource_categ.type, time=rl_resource_categ.production_time_seizure, cadence=rl_resource_categ.cadence, 
                                                            formula=rl_resource_categ.formula, args_parameters_list=[('mo_id', '=', mo.id)])
                nb_resource = rl_resource_categ.nb_resource or 1
                vals = {
                            'sequence': rl_resource_categ.sequence,
                            'resource_category_id': rl_resource_categ.category_id.id,
                            'rl_resource_category_id': rl_resource_categ.id,
                            'resource_id': resource_rcs.id,
                            'nb_resource': nb_resource,
                            'preparation_time': rl_resource_categ.preparation_time,
                            'production_time': production_time,
                            'cleaning_time': rl_resource_categ.cleaning_time,
                            'preparation_masked_time': rl_resource_categ.preparation_masked_time,
                            'production_masked_time': rl_resource_categ.production_masked_time,
                            'cleaning_masked_time': rl_resource_categ.cleaning_masked_time,
                            'nb_product_parallel': rl_resource_categ.routing_line_id.nb_product_parallel,
                        } 
                if other_data:
                    vals.update(other_data)
            else:
                vals = {}
                
        return vals
     
    
    def prepare_wo(self, rl, mo, resource_list_vals=None, consum_serv_list_vals=None, tool_list_vals=None, consign_list_vals=None, other_data=None, sequence=False):
        """ 
            Préparation des valeurs pour la création d'un enregistrement de l'objet mrp.wo
            :param rl: les lignes de gammes mrp.routing.line
            :type rl: recordset
            :param mo: L'ordre de fabrication mrp.manufactoringorder
            :type mo: recordset
            :param resource_list_vals: dico pour le champs resource_ids mrp.wo.resource
            :type resource_list_vals: list de dico (ex: [(0,0,{}),(0,0,{})])
            :param consum_serv_list_vals: dico pour le champs consumed_service_ids mrp.wo.consumed.service
            :type consum_serv_list_vals: list de dico (ex: [(0,0,{}),(0,0,{})])
            :param tool_list_vals: dico pour le champs tool_ids mrp.wo.tools
            :type tool_list_vals: list de dico (ex: [(0,0,{}),(0,0,{})])
            :param consign_list_vals: dico pour le champs consign_ids mrp.wo.consign
            :type consign_list_vals: list de dico (ex: [(0,0,{}),(0,0,{})])
            :param other_data: dico pour remplir de nouveau champ pour la creation d'un OT
            :type other_data: dico des valeurs de l'OT (ex: {'name':'toto',})
            :return: dico de valeurs
        """
        if not sequence:
            sequence = rl.sequence
            
        vals = {
                    'name': '%s'%(rl.name),
                    'sequence': sequence,
                    'mo_id': mo.id,
                    'quantity': mo.quantity,
                    'routing_line_id': rl.id,
                    'waiting_time_next_ope': rl.waiting_time_next_ope,
                    'percentage_overlap_next_ope': rl.percentage_overlap_next_ope,
                    'sale_line_id': mo.sale_line_id.id,
                    'is_forecast': mo.is_forecast,
                    'note_manufacturing': mo.note_manufacturing,
                    'note_planned': mo.note_planned,
                    'state': 'draft',
                    'is_supplier_delay_subc': rl.is_supplier_delay_subc
                }
                    
        if resource_list_vals:
            vals['wo_resource_ids'] = resource_list_vals
            
        if consum_serv_list_vals:
            vals['consumed_service_ids'] = consum_serv_list_vals
        
        if tool_list_vals:
            vals['tool_ids'] = tool_list_vals
        
        if consign_list_vals:
            vals['consign_ids'] = consign_list_vals
                
        if other_data:
            vals.update(other_data)
            
        return vals
    
    
    def construct_next_wo(self, list_wo, mo):
        """
         Reconstruit les liens entre les WO en se basant sur les routing lines de la gamme
         :param list_wo_ids: list d'OT (recordset) 
         :type list_wo_ids: list d'ids
         :param mo: L'ordre de fabrication mrp.manufactoringorder
         :type mo: recordset
         
        """
        ope_consum_obj = self.env['mrp.operation.consumed']
        if list_wo:
            for wo in list_wo:
                # Si la routing line contient des opérations consommées 
                if wo.routing_line_id.routing_id.operation_consumed_ids:
                    # Récupération des next ids de la ligne de gamme
                    ope_consum_rcs = ope_consum_obj.search([('routing_id', '=', wo.routing_line_id.routing_id.id), ('operation_consumed_id', '=', wo.routing_line_id.id)])
                    rl_rcs = self.env['mrp.routing.line']
                    for x in ope_consum_rcs:
                        rl_rcs += x.operation_id
                    
                    if rl_rcs:
                        next_wo_rcs = self.search([('routing_line_id', 'in', rl_rcs.ids), ('mo_id', '=', mo.id)])
                        if next_wo_rcs:
                            # Récupération de l'équivalent en simulation WO
                            wo.write({'next_wo_ids': [(6, 0, next_wo_rcs.ids)]})
                        else:
                            next_wo_rcs = self.recursive_construct_next_wo(wo.routing_line_id.routing_id.id, mo.id, rl_rcs, ope_consum_obj)
                            if next_wo_rcs:
                                wo.write({'next_wo_ids': [(6, 0, next_wo_rcs.ids)]})
                            
                            
                            
        return True
    
    
    def recursive_construct_next_wo(self, routing_id, mo_id, rl_rcs, ope_consum_obj):
        """
            Fonction récursive qui permet de faire le lien entre les WO en se basant sur les routing lines de la gamme avec des lignes de gammes optionnelles
            :param routing_id: Id de la gamme
            :type routing_id: id
            :param mo_id: Id manufacturing order
            :type mo_id: id
            :param rl_rcs: Liste des lignes de gammes suivante
            :type rl_rcs: recordset mrp.routing.line
            :param ope_consum_obj: self.env['mrp.operation.consumed']
            :type ope_consum_obj: self.env['mrp.operation.consumed']
        """
        next_wo_rcs = False
        ope_consum_rcs = ope_consum_obj.search([('routing_id', '=', routing_id), ('operation_consumed_id', 'in', rl_rcs.ids)])
        rl_int_rcs = self.env['mrp.routing.line']
        for x in ope_consum_rcs:
            rl_int_rcs += x.operation_id
        
        if rl_int_rcs:
            next_wo_rcs = self.search([('routing_line_id', 'in', rl_int_rcs.ids), ('mo_id', '=', mo_id)])
            if not next_wo_rcs:
                next_wo_rcs = self.recursive_construct_next_wo(routing_id, mo_id, rl_int_rcs, ope_consum_obj)
        
        return next_wo_rcs
    

    def create_rm(self, consumed_component_list, wo, quantity_ot, quantity_bom, location_in, location_out, 
                  list_bom_consommed, move_obj, bom_obj, variant_values=None, is_consume_directly_storage=False, is_disassembly=False):
        """ 
            Préparation des valeurs pour la création d'un enregistrement de l'objet mrp.wo
            :param consumed_component_list: composants consommés
            :type consumed_component_list: liste de recordset
            :param wo: L'ordre de travail mrp.workorder
            :type wo: recordset
            :param quantity_ot: quantité de l'ordre de travail
            :type quantity_ot: float
            :param quantity_bom: quantité de la nomenclature
            :type quantity_bom: float
            :param location_in: emplacement interne
            :type location_in: recordset
            :param location_out: emplacement de sortie
            :type location_out: recordset
            :param list_bom_consommed: liste des composants à consommer
            :type list_bom_consommed: list de recordset
            :param move_obj: self.env sur les stock.move
            :type move_obj: self.env sur les stock.move
            :param bom_obj: self.env sur les mrp.bom
            :type bom_obj: self.env sur les mrp.bom
            :return: dico de valeurs
        """
        move_rm_rcs = self.env['stock.move']
        move_obj = self.env['stock.move']
        uom_obj = self.env['product.uom']
        for consum_comp in consumed_component_list:
            qty, efficient_unit_qty = consum_comp.compute_qty_component(consum_comp.quantity, consum_comp.round, consum_comp.efficiency,
                                                                        quantity_bom, quantity_ot, consum_comp.type_component, 
                                                                        formula=consum_comp.formula_component, args_parameters_list=[('mo_id', '=', wo.mo_id.id)])
            
            parameters = [(0, 0, {'type_component': consum_comp.type_component,
                                 'formula_component': consum_comp.formula_component,
                                 'qty_bom': quantity_bom,
                                 'qty_component': consum_comp.quantity,
                                 'round_component': consum_comp.round,
                                 'eff_component': consum_comp.efficiency,
                                 'property_ids': [(6, 0, consum_comp.property_ids.ids)]})]
            
            product_id = self._get_product(consum_comp, variant_values, product=consum_comp.product_id)
            efficient_unit_qty = uom_obj._compute_qty_obj(consum_comp.uom_id, efficient_unit_qty, consum_comp.product_id.uom_id)
            #Si on utilise les nomenclatures est fantome (nomenclature de type kit), que le produit est produit et que sa nomenclature est de type fantome
            bom_kit = False
            bom_kit, move_rm_rcs = self.recursive_create_rm_kit(product_id, consum_comp, qty, bom_obj, uom_obj, move_obj, variant_values, is_consume_directly_storage, location_in, move_rm_rcs, wo, bom_kit, location_out)
            
            #Si la nomenclature n'est pas fantome
            if not bom_kit:
                if is_consume_directly_storage:
                    self.env.cr.execute(""" SELECT 
                                product_storage_location.location_id 
                            FROM
                                stock_warehouse,
                                res_company,
                                product_storage_location                     
                            where 
                                product_storage_location.product_id = %s and
                                product_storage_location.warehouse_id = stock_warehouse.id and
                                res_company.warehouse_id = stock_warehouse.id and
                                res_company.id = %s
                            limit 1"""%(product_id.id, wo.company_id.id))
                    val_location_id = self.env.cr.fetchall() 
                    location_in_temp_id = val_location_id and val_location_id[0][0] or False
                    location_in_temp_id = location_in_temp_id or location_in.id
                else:
                    location_in_temp_id = location_in.id
                
                if is_disassembly:
                    move_rm_rcs += move_obj.create_move(product_id, location_out, location_in, 
                                               qty=qty, uom=consum_comp.uom_id, 
                                               other_data={'efficient_unit_qty': efficient_unit_qty, 
                                                           'wo_outgoing_id': wo.id,
                                                           'origin': wo.name,
                                                           'type_qty': consum_comp.type_component,
                                                           'parameter_ids': parameters,
                                                           'is_forecast': wo.is_forecast,
                                                           'component_id': consum_comp.id}, in_product_uom=True)
                else:
                    move_rm_rcs += move_obj.create_move(product_id, location_in_temp_id, location_out.id, 
                                               qty=qty, uom=consum_comp.uom_id, 
                                               other_data={'efficient_unit_qty': efficient_unit_qty, 
                                                           'wo_incoming_id': wo.id,
                                                           'origin': wo.name,
                                                           'type_qty': consum_comp.type_component,
                                                           'parameter_ids': parameters,
                                                           'is_forecast': wo.is_forecast,
                                                           'component_id': consum_comp.id}, in_product_uom=True)
            
            if consum_comp in list_bom_consommed:
                list_bom_consommed -= consum_comp

        if move_rm_rcs:
            move_rm_rcs.create_move_history()
            
        return list_bom_consommed
    
    
    def recursive_create_rm_kit(self, product_id, consum_comp, qty, bom_obj, uom_obj, move_obj, variant_values, is_consume_directly_storage, location_in, move_rm_rcs, wo, bom_kit, location_out):
        #Si on utilise les nomenclatures est fantome (nomenclature de type kit), que le produit est produit et que sa nomenclature est de type fantome
        if wo.mo_id.is_use_kit and product_id.supply_method == 'produce':
            bom_product = bom_obj._bom_find(product_id.id, consum_comp.product_id.uom_id.id, date=fields.Date.today(), options=wo.mo_id.option_ids)
            if bom_product and bom_product.type == 'kit':
                bom_kit = True
                kit_quantity_bom = uom_obj._compute_qty_obj(bom_product.uom_id, bom_product.quantity, consum_comp.product_id.uom_id)
                for kit_components in bom_product.bom_ids:
                    kit_product_id = self._get_product(kit_components, variant_values, product=kit_components.product_id)
                    kit_qty, kit_efficient_unit_qty = kit_components.compute_qty_component(kit_components.quantity, kit_components.round, kit_components.efficiency,
                                                                                           kit_quantity_bom, qty, kit_components.type_component, 
                                                                                           formula=kit_components.formula_component, args_parameters_list=[('mo_id', '=', wo.mo_id.id)])
                    
                    kit_product_recursive = False
                    if kit_product_id.supply_method == 'produce':
                        kit_bom_product = bom_obj._bom_find(kit_product_id.id, kit_components.product_id.uom_id.id, date=fields.Date.today(), options=wo.mo_id.option_ids)
                        if kit_bom_product and kit_bom_product.type == 'kit':   
                            bom_kit, move_rm_rcs = self.recursive_create_rm_kit(kit_product_id, kit_components, kit_qty, bom_obj, uom_obj, move_obj, variant_values, is_consume_directly_storage, location_in, move_rm_rcs, wo, bom_kit, location_out)
                            kit_product_recursive = True
                    
                    if not kit_product_recursive:
                        kit_efficient_unit_qty = uom_obj._compute_qty_obj(kit_components.uom_id, kit_efficient_unit_qty, kit_components.product_id.uom_id)
                        kit_parameters = [(0, 0, {'type_component': consum_comp.type_component,
                                                  'formula_component': kit_components.formula_component,
                                                  'qty_bom': kit_quantity_bom,
                                                  'qty_component': kit_components.quantity,
                                                  'round_component': kit_components.round,
                                                  'eff_component': kit_components.efficiency,
                                                  'property_ids': [(6, 0, kit_components.property_ids.ids)]})]
                        
                        if is_consume_directly_storage:
                            self.env.cr.execute(""" SELECT 
                                        product_storage_location.location_id 
                                    FROM
                                        stock_warehouse,
                                        res_company,
                                        product_storage_location                     
                                    where 
                                        product_storage_location.product_id = %s and
                                        product_storage_location.warehouse_id = stock_warehouse.id and
                                        res_company.warehouse_id = stock_warehouse.id and
                                        res_company.id = %s
                                    limit 1"""%(kit_product_id.id, wo.company_id.id))
                            val_location_id = self.env.cr.fetchall() 
                            location_in_temp_id = val_location_id and val_location_id[0][0] or False
                            location_in_temp_id = location_in_temp_id or location_in.id
                        else:
                            location_in_temp_id = location_in.id
                            
                        move_rm_rcs += move_obj.create_move(kit_product_id, location_in_temp_id, location_out.id, 
                                           qty=kit_qty, uom=kit_components.uom_id, 
                                           other_data={'efficient_unit_qty': kit_efficient_unit_qty, 
                                                       'wo_incoming_id': wo.id,
                                                       'origin': wo.name,
                                                       'type_qty': kit_components.type_component,
                                                       'parameter_ids': kit_parameters,
                                                       'is_forecast': wo.is_forecast,
                                                       'component_id': kit_components.id}, in_product_uom=True)
        return bom_kit, move_rm_rcs
    
    
    
    def _get_product(self, bom_id, variant_value_ids, product=False):
        """
            Point d'entrée pour les variantes
            :param bom_id: la nomenclature mrp.bom
            :type bom_id: recordset
            :param variant_value_ids: liste des paramètres à utiliser pour déterminer la variante
            :type variant_value_ids: recordset
            :return: un product.product
        """
        if product:
            return product
        
        return bom_id.product_id
    
    
    def _get_rl_ids(self, routing_id, options):
        result = []
        for rl in self.env['mrp.routing.line'].search([('routing_id', '=', routing_id.id)], order='sequence asc'):
            if (not rl.option_id) or (rl.option_id in options):
                result.append(rl)
                
        return result


    def _get_list_bom_consommed(self, bom_id, options):
        return self.env['mrp.bom'].search([('bom_id', '=', bom_id.id),
                                           '|',
                                            ('option_id', 'in', options.ids),
                                            ('option_id', '=', None)],
                                            order='sequence asc')
    
    
    def create_wo(self, product, mo, quantity=1.0, uom=False, bom=False, routing=False, options=None, other_data=None, other_data_last_move=None, variant_values=None):
        """ 
            Génération des OTs à partir d'une nomenclature et d'une gamme, de la quantité et son unité
            :param product: Le produit product.product
            :type product: recordset
            :param mo: L'ordre de fabrication mrp.manufactoringorder
            :type mo: recordset
            :param quantity: Quantité de la fabrication.
            :type quantity: float.
            :param uom: Unité de mesure product.uom.
            :type uom: recordset
            :param bom: La nomenclature mrp.bom
            :type bom: recordset
            :param routing: La gamme mrp.routing
            :type routing: recordset
            :param options: Liste de propriétés
            :type options: list of recordset
            :param other_data: dico pour remplir de nouveau champ pour la creation d'un OT
            :type other_data: dico des valeurs de l'OT (ex: {'name':'toto',})
            :param other_data_last_move: dico pour remplir de nouveau champ pour la creation du dernier mouvement du produit final dans le dernier OT
            :type other_data_last_move: dico des valeurs pour la création du dernier mouvement du produit final dans le dernier OT (ex: {'name':'toto',})
            :return: list_wo_ids Une liste des IDs créés
        """
        if not other_data:
            other_data = {}
            
        bom_obj = self.env['mrp.bom']
        uom_obj = self.env['product.uom']
        wo_resource_obj = self.env['mrp.wo.resource']
        location_obj = self.env['stock.location']
        product_obj = self.env['product.product']
        move_obj = self.env['stock.move']
        list_wo_ids = []
        list_wo = []
        last_wo_id = False
        first_wo_id = False
        self.env.cr.execute(""" SELECT 
                                    is_consume_directly_storage,
                                    is_produce_directly_storage
                                FROM
                                    stock_warehouse,
                                    res_company                               
                                where 
                                    res_company.warehouse_id = stock_warehouse.id and
                                    res_company.id = %s
                                limit 1"""%(mo.company_id.id,))
        val_stock_warehouse = self.env.cr.fetchall() 
        is_consume_directly_storage = val_stock_warehouse and val_stock_warehouse[0][0] or False
        is_produce_directly_storage = val_stock_warehouse and val_stock_warehouse[0][1] or False
        if product:
            # Récupération de la nomenclature et de la gamme
            if not bom:
                bom = bom_obj._bom_find(product.id, uom.id, options=options)
                if bom:
                    for rout in bom.routing_ids:
                        if rout.state == 'active':
                            routing = rout
                            break
                        
            else:
                if not routing:
                    for rout in bom.routing_ids:
                        if rout.state == 'active':
                            routing = rout
                            break
                        
            if product._columns.has_key('is_model') and product.is_model and variant_values:
                product = self._get_product(bom, variant_values, product=product)
            
            if bom and routing:
                # Modification de la quantité dans l'uom de la bom
                quantity_ot = quantity
                quantity_bom = bom.quantity or 1.0
                if uom and uom.id != bom.uom_id.id:
                    quantity_ot = uom_obj._compute_qty_obj(uom, quantity, bom.uom_id, with_raise=False)
                    
                # On range les lignes de gammes par séquence
                rl_rcs = self._get_rl_ids(routing, options)
                # Rechercher le produit int
                product_int_rcs = product_obj.search([('is_int', '=', True)], limit=1)
                if rl_rcs:
                    # Identifier la dernière ligne de gamme
                    last_rl_id = rl_rcs[-1].id
                    # Identifier la première ligne de gamme
                    first_rl_id = rl_rcs[0].id
                    # Lister tous les composants à consommer s'ils ne sont pas tous déclarés dans les lignes de gammes ils seront affectés au premier OT
                    list_bom_consommed = self._get_list_bom_consommed(bom, options)
                    # Dictionnaire qui lie l'id de la routing line à l'id du WO
                    routing_line_wc_line_ids = {}
                    # Création des mouvement des matières premières et du produit final
                    move_fp_rcs = self.env['stock.move']
                    location_out = location_obj.search([('usage', '=', 'production')], limit=1)
                    # Gestion des niveaux par rapport à la séquence
                    rl_sequences = [(r.sequence, r.id) for r in rl_rcs]
                    rl_level = {x[-1]: rl_sequences.index(x) for x in rl_sequences}
                    # Boucler par les lignes de gammes
                    for rl in rl_rcs:
                        # Boucler sur les catégories de ressources
                        resource_list_vals = []
                        for rl_resource_categ in rl.rl_resource_category_ids:
                            rl_resource_categ_vals = self.prepare_wo_resource(rl_resource_categ, mo)
                            if rl_resource_categ_vals:
                                resource_list_vals.append([0, 0, rl_resource_categ_vals])
                        
                        # Boucler sur les services consommés
                        consum_serv_list_vals = []
                        for consum_serv in rl.consumed_service_ids.read(['quantity', 'product_id', 'uom_id', 'type'], load='_classic_write'):
                            # Si la consommation du service est fixe ou variable
                            #if consum_serv.type == 'variable':
                            #    qy_service = consum_serv.quantity * quantity_ot / quantity_bom
                            #else:
                            #    qy_service = consum_serv.quantity
                            consum_serv_vals = {
                                        'product_id': consum_serv['product_id'],
                                        'quantity': consum_serv['quantity'],
                                        'uom_id': consum_serv['uom_id'],
                                        'type': consum_serv['type']
                                    }
                            if consum_serv_vals:
                                consum_serv_list_vals.append([0, 0, consum_serv_vals])
                        
                        # Boucler sur les outils
                        tool_list_vals = []
                        for tool in rl.tool_ids.read(['quantity', 'product_id', 'uom_id'], load='_classic_write'):
                            tool_vals = {
                                        'product_id': tool['product_id'],
                                        'quantity': tool['quantity'] * quantity_ot / quantity_bom,
                                        'uom_id': tool['uom_id']
                                    }
                            if tool_vals:
                                tool_list_vals.append([0, 0, tool_vals])
                        
                        # Boucler sur les consignes
                        consign_list_vals = []
                        for consign in rl.consign_ids.read(['name', 'frequency', 'type', 'desciptive', 'means'], load='_classic_write'):
                            consign_vals = {
                                        'name': consign['name'],
                                        'frequency': consign['frequency'],
                                        'type': consign['type'],
                                        'desciptive': consign['desciptive'],
                                        'means': consign['means']
                                    }
                            consign_list_vals.append((0, 0, consign_vals))

                        # Création du WO
                        other_data['level'] = rl_level.get(rl.id, 0)
                        other_data['mo_level'] = mo.level
                        wo_vals = self.prepare_wo(rl, mo, resource_list_vals=resource_list_vals, consum_serv_list_vals=consum_serv_list_vals, tool_list_vals=tool_list_vals, 
                                                  consign_list_vals=consign_list_vals, other_data=other_data)
                        wo = self.create(wo_vals)
                        routing_line_wc_line_ids[rl.id] = wo.id
                        list_wo_ids.append(wo.id)
                        list_wo.append(wo)
                        
                        # Emplacement pour les mouvements
                        # On récupère l'emplacement de la première ressource
                        wo_resource_rcs = wo_resource_obj.search([('wo_id', '=', wo.id)], order='sequence asc', limit=1)
                        if wo_resource_rcs:
                            location_in = wo_resource_rcs.resource_id.location_id
                            if wo_resource_rcs.resource_id.type == 'subcontracting':
                                is_consume_directly_storage = False
                                is_produce_directly_storage = False
                            
                        else:
                            location_in = location_obj.search([('usage', '=', 'internal')], limit=1)
                        
                        if not location_in:
                            raise except_orm(_('Error'), _('There is not location internal.'))
                        
                        if not location_out:
                            raise except_orm(_('Error'), _('There is not location production.'))

                        # Création des mouvement des matières premières
                        consumed_component_list = [x for x in rl.consumed_component_ids if x.bom_id and x.bom_id.id == bom.id and x in list_bom_consommed]
                        list_bom_consommed = self.create_rm(consumed_component_list, wo, quantity_ot, quantity_bom, location_in, location_out, 
                                                                         list_bom_consommed, move_obj, bom_obj, variant_values, 
                                                                         is_consume_directly_storage=is_consume_directly_storage, is_disassembly=mo.is_disassembly)
                        
                        if rl.id == first_rl_id:
                            first_wo_id = wo.id
                        
                        if rl.id != last_rl_id:
                            # Création du mouvement du produit final
                            if rl.product_id:
                                final_product_rs = rl.product_id
                            else:
                                final_product_rs = product_int_rcs
                                
                            if final_product_rs:
                                efficient_unit_qty = 1.0
                                move_fp_rcs += move_obj.create_move(final_product_rs, location_out.id, location_in.id, qty=quantity, 
                                                                   uom=final_product_rs.uom_id, other_data={'wo_outgoing_id': wo.id, 
                                                                                                           'efficient_unit_qty': efficient_unit_qty,
                                                                                                           'origin': wo.name_get()[0][1],
                                                                                                           'is_forecast': wo.is_forecast,
                                                                                                           'is_control_declaration_recep': False})
                        else:
                            # Création du mouvement du produit final
                            quantity_product_final = quantity_ot
                            other_move_data = {'efficient_unit_qty':1.0, 
                                               'origin': wo.name_get()[0][1],
                                               'is_forecast': wo.is_forecast}
                            if other_data_last_move:
                                other_move_data.update(other_data_last_move)
                                
                            if is_produce_directly_storage:
                                self.env.cr.execute(""" SELECT 
                                            product_storage_location.location_id 
                                        FROM
                                            stock_warehouse,
                                            res_company,
                                            product_storage_location                     
                                        where 
                                            product_storage_location.product_id = %s and
                                            product_storage_location.warehouse_id = stock_warehouse.id and
                                            res_company.warehouse_id = stock_warehouse.id and
                                            res_company.id = %s
                                        limit 1"""%(self._get_product(bom, variant_values, product=product).id, mo.company_id.id))
                                val_location_id = self.env.cr.fetchall() 
                                location_in_temp_id = val_location_id and val_location_id[0][0] or False
                                location_in_temp_id = location_in_temp_id or location_in.id
                            else:
                                location_in_temp_id = location_in.id
                            
                            if mo.is_disassembly:
                                other_move_data['wo_incoming_id'] = first_wo_id
                                move_fp_rcs += move_obj.create_move(self._get_product(bom, variant_values, product=product), location_in_temp_id, location_out.id, 
                                                           qty=quantity_product_final, uom=bom.uom_id, 
                                                           other_data=other_move_data, in_product_uom=True)
                            else:
                                other_move_data['wo_outgoing_id'] = wo.id
                                other_move_data['is_control_declaration_recep'] = False
                                move_fp_rcs += move_obj.create_move(self._get_product(bom, variant_values, product=product), location_out.id, location_in_temp_id, 
                                                               qty=quantity_product_final, uom=bom.uom_id, 
                                                               other_data=other_move_data, in_product_uom=True)
                                
                            # Création du mouvement des sous produits s'il y en a
                            for subproduct in bom.subproduct_ids:
                                # Si de type variable
                                if subproduct.type == 'variable':
                                    quantity_subproduct = (subproduct.quantity * quantity_ot / quantity_bom)
                                else:
                                    efficient_subproduct_unit_qty = 0
                                    quantity_subproduct = subproduct.quantity
                                    
                                # Calcul de la quantité par rapport à l'efficacité
                                efficiency = subproduct.efficiency or 1.0
                                quantity_subproduct = quantity_subproduct * efficiency
                                if subproduct.round:
                                    quantity_subproduct = rounding(quantity_subproduct, subproduct.round)
                                    
                                if subproduct.type == 'variable':
                                    efficient_subproduct_unit_qty = quantity_ot and quantity_subproduct/quantity_ot or quantity_subproduct
                                
                                if is_produce_directly_storage:
                                    self.env.cr.execute(""" SELECT 
                                                product_storage_location.location_id 
                                            FROM
                                                stock_warehouse,
                                                res_company,
                                                product_storage_location                     
                                            where 
                                                product_storage_location.product_id = %s and
                                                product_storage_location.warehouse_id = stock_warehouse.id and
                                                res_company.warehouse_id = stock_warehouse.id and
                                                res_company.id = %s
                                            limit 1"""%(subproduct.product_id.id, mo.company_id.id))
                                    val_location_id = self.env.cr.fetchall() 
                                    location_in_temp_id = val_location_id and val_location_id[0][0] or False
                                    location_in_temp_id = location_in_temp_id or location_in.id
                                else:
                                    location_in_temp_id = location_in.id
                                
#                                 move_fp_rcs += move_obj.create_move(self._get_product(subproduct.bom_id, variant_values), location_out.id, location_in.id,
                                move_fp_rcs += move_obj.create_move(subproduct.product_id, location_out.id, location_in_temp_id, 
                                                           qty=quantity_subproduct, uom=subproduct.uom_id, 
                                                           other_data={'efficient_unit_qty':efficient_subproduct_unit_qty, 
                                                                       'wo_outgoing_id':wo.id,
                                                                       'origin': wo.name_get()[0][1],
                                                                       'type_qty': subproduct.type,
                                                                       'is_forecast': wo.is_forecast,
                                                                       'is_control_declaration_recep': False,
                                                                       'trigger_supply': 'without_stock'}, in_product_uom=True)
                            
                            last_wo_id = wo.id
                        
                    # Matières premières restante non affectées dans les lignes de gammes que l'on affecte à la première gamme
                    if list_bom_consommed:
                        if (first_wo_id and not mo.is_disassembly) or (last_wo_id and mo.is_disassembly):
                            if mo.is_disassembly:
                                wo_first = self.browse(last_wo_id)
                            else:
                                wo_first = self.browse(first_wo_id)
                            
                            # On récupère l'emplacement de la première ressource
                            wo_resource_rcs = wo_resource_obj.search([('wo_id', '=', wo_first.id)], order='sequence asc', limit=1)
                            if wo_resource_rcs:
                                location_in = wo_resource_rcs.resource_id.location_id
                            else:
                                location_in = location_obj.search([('usage', '=', 'internal')], limit=1)
                                
                            if not location_in:
                                raise except_orm(_('Error'), _('There is not location internal.'))
                            
                            if mo.is_disassembly:
                                list_none = self.create_rm(list_bom_consommed[:], wo_first, quantity_ot, quantity_bom, location_in, location_out, 
                                                                             list_bom_consommed, move_obj, bom_obj, variant_values, 
                                                                             is_consume_directly_storage=is_consume_directly_storage, is_disassembly=True)
                            else:
                                list_none = self.create_rm(list_bom_consommed[:], wo_first, quantity_ot, quantity_bom, location_in, location_out, 
                                                                             list_bom_consommed, move_obj, bom_obj, variant_values, 
                                                                             is_consume_directly_storage=is_consume_directly_storage)
                        
                    
                    
                    
                    
                    # Création des relations prev/next des WO par rapport aux opérations consomées
                    self.construct_next_wo(list_wo, mo)
                    wo.vals_platics_industry()
                    
        return list_wo_ids, last_wo_id, first_wo_id
    
    
    def vals_platics_industry(self):
        return True
    
                        
    def create_mo_and_wo(self, product, name_mo=False, qty_mo=0.0, uom_mo=False, other_wo_data=None, other_mo_data=None, other_data_last_move=None, with_raise=False, no_under_mo=True, options=[], variant_values=[], parameters=[]):
        """ 
            Génération de l'OF et des OTs à partir d'un produit, d'un nom d'OF, d'une quantité et son unité
            :param product: Le produit product.product
            :type product: recordset
            :param name_mo: Le name de l'ordre de fabrication
            :type name_mo: char 256
            :param qty_mo: Quantité de la fabrication
            :type qty_mo: float
            :param uom_mo: Unité de mesure product.uom
            :type uom_mo: recordset
            :return: list_wo_ids Une liste des IDs créés et l'id du dernier OTs
        """    
        mo_obj = self.env['mrp.manufacturingorder']
        list_wo_ids = []
        last_wo_id = False
        first_wo_id = False
        if not uom_mo:
            uom_mo = product.uom_id
        
        mo, qty_mo = mo_obj.create_mo(product, name=name_mo, quantity=qty_mo, uom=uom_mo, bom=False, routing=False, other_data=other_mo_data, with_raise=with_raise, options=options, variant_values=variant_values, parameters=parameters)
        
        if mo:
            list_wo_ids, last_wo_id, first_wo_id = self.create_wo(mo.product_id, mo, quantity=qty_mo, uom=mo.uom_id, bom=mo.bom_id, routing=mo.routing_id, options=mo.option_ids, other_data=other_wo_data, other_data_last_move=other_data_last_move, variant_values=variant_values)

        return mo, list_wo_ids, last_wo_id, first_wo_id
    
    
    def aggregate_move(self, move_ids=None, type='rm', waiting_state=False):
        """ 
            Fonction qui permet d'annuler toutes les consommations ou les productions d'un OT
        """    
        uom_obj = self.env['product.uom']
        move_obj = self.env['stock.move']
        product_move_qty = {}
        
        # Dictionnaire des UoM des MP non consommées pour avoir l'UoM et le move de reference
        product_uom = {}
        product_move = {}
        move_to_del_ids = self.env['stock.move']
        # Savoir si on agrége les mouvements de consommations ou de productions
        without_duplicate = False
        if type == 'rm':
            if waiting_state:
                without_duplicate = True
                
            for move in self.rm_draft_ids:
                if not move_ids or move not in move_ids: 
                    product_uom[move.product_id] = move.uom_id
                    product_move[move.product_id] = move
            
            if not move_ids:
                move_ids = move_obj.search([('wo_incoming_id', '=', self.id), ('state', 'in', ['done', 'cancel']), ('not_usable', '=', False)])
                
        elif type == 'fp':
            for move in self.fp_draft_ids:
                if not move_ids or move not in move_ids:  
                    product_uom[move.product_id] = move.uom_id
                    product_move[move.product_id] = move
            
            if not move_ids:
                move_ids = move_obj.search([('wo_outgoing_id', '=', self.id), ('state', 'in', ['done', 'cancel'])])
        
        quality = False
        for move in move_ids:
            product = move.product_id
            if move.control_declaration_id or move.post_control_declaration_id:
                quality = True
                
            # Recuperation de l'UoM de reference pour ce produit
            if product in product_uom:
                ref_uom = product_uom[product]
            else:
                ref_uom = False
                
            # Conversion de quantité si deux UoM différent pour le même produit (cas ou il y a plusieurs fois le meme produit)
            if ref_uom and ref_uom.id != move.uom_id.id and ref_uom.category_id.id == move.uom_id.category_id.id:    
                qty = uom_obj._compute_qty_obj(move.uom_id, move.uom_qty, ref_uom)
            else:
                qty = move.uom_qty
                
            # Création d'un dictionnaire {product_id: [move_id, qty], ...}
            if product in product_move_qty:
                product_move_qty[product][-1] += qty
                move_to_del_ids += move
            else:
                product_move_qty[product] = [move, qty]
        
        # Mise à jour de tous les mouvements
        for product, move_qty in product_move_qty.items():
            vals = {}
            if product in product_uom:
                vals['uom_id'] = product_uom[product].id
            
            # Si le produit a déjà un mouvement non consommé: on écrit dessus, sinon: on modifie le mouvement    
            if product in product_move:
                move_to_del_ids += move_qty[0]
                vals['uom_qty'] = product_move[product].uom_qty + move_qty[-1]
                vals['sec_uom_qty'] = product_move[product].uom_qty and product_move[product].sec_uom_qty + (move_qty[-1] * product_move[product].sec_uom_qty / product_move[product].uom_qty) or product_move[product].uom_qty + move_qty[-1]
                vals['uoi_qty'] = product_move[product].uom_qty and  product_move[product].uoi_qty + (move_qty[-1] * product_move[product].uoi_qty / product_move[product].uom_qty) or product_move[product].uom_qty + move_qty[-1]
                product_move[product].write(vals)
            else:
                new_move_created, new_move = move_qty[0].with_context({'without_duplicate': without_duplicate}).reopen()
                if new_move_created:
                    move_qty[0] = new_move
                    
                if waiting_state:
                    move_qty[0].wkf_waiting()
                
                vals['uom_qty'] = move_qty[-1]
                vals['sec_uom_qty'] = move_qty[0].uom_qty and move_qty[-1] * move_qty[0].sec_uom_qty / move_qty[0].uom_qty or move_qty[0].uom_qty + move_qty[-1]
                vals['uoi_qty'] = move_qty[0].uom_qty and move_qty[-1] * move_qty[0].uoi_qty / move_qty[0].uom_qty or move_qty[0].uom_qty + move_qty[-1]
                vals['wo_consumption_id'] = False
                vals['wo_produce_id'] = False
                move_qty[0].write(vals)
                move_qty[0].move_label_ids.unlink()
                product_move[product] = move_qty[0]
        
        if move_to_del_ids and not quality:
            move_to_del_ids.write({'procurement_id': False})
            move_to_del_ids.wkf_cancel()
            move_to_del_ids.unlink()
            
        return True
    
    
    def modif_move_or_scrap(self, move_rcs, move_qty, qty, move_sec_qty=0.0, sec_qty=0.0, is_variable_double_unit=False):
        """ 
            Modification d'un mouvement par rapport à une quantité: si move_qty > qty création d'un reliquat avec la différence, 
                et dans tous les cas modification de la quantité dans les mouvements par la qty
            :param move_rcs: Mouvement stock.move.
            :type move_rcs: recordset
            :param move_qty: Quantité dans le mouvement.
            :type move_qty: Float.
            :param move_sec_qty: Quantité dans le mouvement en seconde unité.
            :type move_sec_qty: Float.
            :param qty: Nouvelle quantité pour la modification.
            :type qty: Float.
            :param sec_qty: Nouvelle quantité pour la modification en seconde unité.
            :type sec_qty: Float.
            :param is_variable_double_unit: Flag indique si double unité variable
            :type is_variable_double_unit: boolean
            :return: si création d'un reliquat renvoie d'un recordset si non False.
        """
        new_move = False
        uom_obj= self.env['product.uom']
        if move_qty != qty: 
            if not is_variable_double_unit:
                sec_uom_qty_factor = move_rcs.sec_uom_qty / (move_rcs.uom_qty or 1.0)
                uoi_qty_factor = move_rcs.uoi_qty / (move_rcs.uom_qty or 1.0)
            # Si la quantité est inférieur à la quantité du mouvement on fait un reliquat du reste
            if move_qty > qty:
                sec_uom_qty_factor = move_rcs.sec_uom_qty / (move_qty or 1.0)
                uoi_qty_factor = move_rcs.uoi_qty / (move_qty or 1.0)
                diff =  move_qty - qty
                copy_vals = {'uom_qty': diff,
                             'move_label_ids': [],
                             'history_id': move_rcs.history_id.id}
                if is_variable_double_unit:
                    sec_diff = sec_qty
                    copy_vals['sec_uom_qty'] = sec_diff
                    copy_vals['uoi_qty'] = uom_obj._compute_qty_obj(move_rcs.sec_uom_id, sec_diff, move_rcs.uoi_id)
                else:
                    copy_vals['sec_uom_qty'] = diff * sec_uom_qty_factor
                    copy_vals['uoi_qty'] = diff * uoi_qty_factor
                    
                new_move = move_rcs.copy(copy_vals)
#                 new_move.wkf_waiting()
            
            # Si la quantité a été changée on la change dans le mouvement
            write_vals = {'uom_qty': qty}
            if is_variable_double_unit:
                write_vals['sec_uom_qty'] = sec_qty
                write_vals['uoi_qty'] = uom_obj._compute_qty_obj(move_rcs.sec_uom_id, sec_qty, move_rcs.uoi_id)
            else:
                write_vals['sec_uom_qty'] = qty * sec_uom_qty_factor
                write_vals['uoi_qty'] = qty * uoi_qty_factor
                
            move_rcs.write(write_vals)
            
        elif is_variable_double_unit and move_sec_qty != sec_qty:
            move_rcs.write({'sec_uom_qty': sec_qty,
                            'uoi_qty' : uom_obj._compute_qty_obj(move_rcs.sec_uom_id, sec_qty, move_rcs.uoi_id)})
            
            
        return new_move
    
    
    def change_qty(self, factor, spread):
        """ 
            Changement quantité OT
            :param self: mrp.workorder
            :type self: recordset
            :param factor: Facteur de changement de quantité.
            :type factor: Float.
            :param spread: Propagation.
            :type spread: Boolean.
            :return: si création d'un reliquat renvoie d'un recordset si non False.
        """
        # Si l'état est brouillon ou en attente: on change juste la quantité
        def get_next_wo_ids(self):
            # Retourne la liste des ids de tous les moves apres celui passé en paramètres
            res = self
            next_wo_rcs = self.search([('prev_wo_ids', 'in', res.ids)])
            if next_wo_rcs:
                res |= get_next_wo_ids(next_wo_rcs)
                
            return res
        
        if spread:
            wo_rcs = get_next_wo_ids(self)
        else:
            wo_rcs = self
            
        prod_digits = 2
        mo_rs = self.env['mrp.manufacturingorder']
        move_obj = self.env['stock.move']
        parameter_obj = self.env['stock.move.parameter']
        product_obj = self.env['product.product']
        bom_obj = self.env['mrp.bom']
        for wo in wo_rcs:
            mo_rs |= wo.mo_id
            if wo.state in ('draft', 'waiting', 'ready', 'plan'):
                wo_new_qty = wo.quantity * factor
                for move in wo.rm_draft_ids.read(['type_qty', 'efficient_unit_qty', 'sec_uom_qty', 'uom_qty', 'uoi_qty', 'wo_incoming_id', 'product_id', 'procurement_id', 'parameter_ids'], load='_classic_write'):
                    if move['type_qty'] == 'formula' and move['parameter_ids']:
                        rm_done_ids = move_obj.search([('state', '=', 'done'), 
                                                       ('wo_incoming_id', '=', move['wo_incoming_id']), 
                                                       ('product_id', '=', move['product_id']), 
                                                       ('procurement_id', '=', move['procurement_id'])])
                        if rm_done_ids:
                            product_read = product_obj.browse(move['product_id']).read(['name'], load='_classic_write')
                            raise except_orm(_('Error'), _('The product %s is type formula, must remove the declarations consumption.')%(product_read['name']))
                        
                        parameter_rcs = parameter_obj.browse(move['parameter_ids'][0]).read(['qty_component', 'round_component', 'eff_component', 'qty_bom', 'type_component', 'formula_component'])[0]
                        move_qty_uom_total, efficient_new_uom_qty = bom_obj.compute_qty_component(parameter_rcs['qty_component'], parameter_rcs['round_component'], parameter_rcs['eff_component'], 
                                                                                                  parameter_rcs['qty_bom'], wo_new_qty, parameter_rcs['type_component'], 
                                                                                                  formula= parameter_rcs['formula_component'], args_parameters_list=[('mo_id', '=', wo.mo_id.id)])
                        coeff_new_qty = move_qty_uom_total and move['uom_qty'] / move_qty_uom_total or move['uom_qty']
                        move_qty_sec_uom_total = move['sec_uom_qty'] / coeff_new_qty
                        move_qty_uoi_total = move['uoi_qty'] / coeff_new_qty
                    
                        move_qty_uom = round(move_qty_uom_total, prod_digits)
                        move_qty_sec_uom = round(move_qty_sec_uom_total, prod_digits)
                        move_qty_uoi = round(move_qty_uoi_total, prod_digits)
                        
                        move_brw = move_obj.browse(move['id'])
                        state_move = move_brw.state
                        move_brw.wkf_cancel()
                        if state_move != 'cancel':
                            dummy, new_move_brw = move_brw.wkf_draft()
                            if dummy:
                                move_brw = new_move_brw

                        move_brw.write({'uom_qty': move_qty_uom,
                                        'sec_uom_qty': move_qty_sec_uom,
                                        'uoi_qty': move_qty_uoi})
                        
                        if state_move not in ('draft', 'cancel'):
                            move_brw.wkf_waiting()
                            
                    elif move['type_qty'] == 'variable':
                        if move['efficient_unit_qty'] and move['uom_qty']:
                            move_qty_uom_total = move['efficient_unit_qty'] * factor * wo.quantity
                            move_qty_sec_uom_total = move['efficient_unit_qty'] * factor * wo.quantity * move['sec_uom_qty'] / move['uom_qty']
                            move_qty_uoi_total = move['efficient_unit_qty'] * factor * wo.quantity * move['uoi_qty'] / move['uom_qty']
                            move_qty_uom_total_done = 0
                            move_qty_sec_uom_total_done = 0
                            move_qty_uoi_total_done = 0
                            rm_done_ids = move_obj.search([('state', '=', 'done'), 
                                                           ('wo_incoming_id', '=', move['wo_incoming_id']), 
                                                           ('product_id', '=', move['product_id']), 
                                                           ('procurement_id', '=', move['procurement_id'])])
                            for rm_done in rm_done_ids.read(['uom_qty', 'sec_uom_qty', 'uoi_qty']):
                                move_qty_uom_total_done += rm_done['uom_qty']
                                move_qty_sec_uom_total_done += rm_done['sec_uom_qty']
                                move_qty_uoi_total_done += rm_done['uoi_qty']
                            
                            move_qty_uom = round(move_qty_uom_total - move_qty_uom_total_done, prod_digits)
                            move_qty_sec_uom = round(move_qty_sec_uom_total - move_qty_sec_uom_total_done, prod_digits)
                            move_qty_uoi = round(move_qty_uoi_total - move_qty_uoi_total_done, prod_digits)
                            
                            if move['parameter_ids']:
                                parameter_rcs = parameter_obj.browse(move['parameter_ids'][0]).read(['round_component'])[0]
                                if parameter_rcs['round_component']:
                                    move_qty_uom = roundingUp(move_qty_uom, parameter_rcs['round_component'])
                                    move_qty_sec_uom = roundingUp(move_qty_sec_uom, parameter_rcs['round_component'])
                                    move_qty_uoi = roundingUp(move_qty_uoi, parameter_rcs['round_component'])
                                
                        else:
                            move_qty_uom = round(move['uom_qty'] * factor, prod_digits)
                            move_qty_sec_uom = round(move['sec_uom_qty'] * factor, prod_digits)
                            move_qty_uoi = round(move['uoi_qty'] * factor, prod_digits)
                            if move['parameter_ids']:
                                parameter_rcs = parameter_obj.browse(move['parameter_ids'][0]).read(['round_component'])[0]
                                if parameter_rcs['round_component']:
                                    move_qty_uom = roundingUp(move_qty_uom, parameter_rcs['round_component'])
                                    move_qty_sec_uom = roundingUp(move_qty_sec_uom, parameter_rcs['round_component'])
                                    move_qty_uoi = roundingUp(move_qty_uoi, parameter_rcs['round_component'])
                            
                        move_brw = move_obj.browse(move['id'])
                        state_move = move_brw.state
                        move_brw.wkf_cancel()
                        if state_move != 'cancel':
                            dummy, new_move_brw = move_brw.wkf_draft()
                            if dummy:
                                move_brw = new_move_brw

                        move_brw.write({'uom_qty': move_qty_uom,
                                        'sec_uom_qty': move_qty_sec_uom,
                                        'uoi_qty': move_qty_uoi})
                        
                        if state_move not in ('draft', 'cancel'):
                            move_brw.wkf_waiting()
                     
                for move in wo.fp_draft_ids.read(['type_qty', 'efficient_unit_qty', 'sec_uom_qty', 'uom_qty', 'uoi_qty', 'wo_outgoing_id', 'product_id', 'procurement_id', 'parameter_ids'], load='_classic_write'):
                    if move['type_qty'] == 'formula' and move['parameter_ids']:
                        fp_done_ids= move_obj.search([('state', '=', 'done'), 
                                                          ('wo_outgoing_id', '=', move['wo_outgoing_id']), 
                                                          ('product_id', '=', move['product_id']), 
                                                          ('procurement_id', '=', move['procurement_id'])])
                        
                        if fp_done_ids:
                            product_read = product_obj.browse(move['product']).read(['name'], load='_classic_write')
                            raise except_orm(_('Error'), _('The product %s is type formula, must remove the declarations produce.')%(product_read['name']))
                        
                        parameter_rcs = parameter_obj.browse(move['parameter_ids'][0]).read(['qty_component', 'round_component', 'eff_component', 'qty_bom', 'type_component', 'formula_component'])[0]
                        move_qty_uom_total, efficient_new_uom_qty = bom_obj.compute_qty_component(parameter_rcs['qty_component'], parameter_rcs['round_component'], parameter_rcs['eff_component'], 
                                                                                                  parameter_rcs['qty_bom'], wo_new_qty, parameter_rcs['type_component'], 
                                                                                                  formula= parameter_rcs['formula_component'], args_parameters_list=[('mo_id', '=', wo.mo_id.id)])
                        coeff_new_qty = move_qty_uom_total and move['uom_qty'] / move_qty_uom_total or move['uom_qty']
                        move_qty_sec_uom_total = move['sec_uom_qty'] / coeff_new_qty
                        move_qty_uoi_total = move['uoi_qty'] / coeff_new_qty
                    
                        move_qty_uom = round(move_qty_uom_total, prod_digits)
                        move_qty_sec_uom = round(move_qty_sec_uom_total, prod_digits)
                        move_qty_uoi = round(move_qty_uoi_total, prod_digits)
                        
                        move_brw = move_obj.browse(move['id'])
                        state_move = move_brw.state
                        move_brw.wkf_cancel()
                        if state_move != 'cancel':
                            dummy, new_move_brw = move_brw.wkf_draft()
                            if dummy:
                                move_brw = new_move_brw

                        move_brw.write({'uom_qty': move_qty_uom,
                                                          'sec_uom_qty': move_qty_sec_uom,
                                                          'uoi_qty': move_qty_uoi})
                        
                        if state_move not in ('draft', 'cancel'):
                            move_brw.wkf_waiting()
                        
                    elif move['type_qty'] == 'variable':
                        if move['efficient_unit_qty'] and move['uom_qty']:
                            move_qty_uom_total = move['efficient_unit_qty'] * factor * wo.quantity
                            move_qty_sec_uom_total = move['efficient_unit_qty'] * factor * wo.quantity * move['sec_uom_qty'] / move['uom_qty']
                            move_qty_uoi_total = move['efficient_unit_qty'] * factor * wo.quantity * move['uoi_qty'] / move['uom_qty']
                            move_qty_uom_total_done = 0
                            move_qty_sec_uom_total_done = 0
                            move_qty_uoi_total_done = 0
                            fp_done_ids= move_obj.search([('state', '=', 'done'), 
                                                          ('wo_outgoing_id', '=', move['wo_outgoing_id']), 
                                                          ('product_id', '=', move['product_id']), 
                                                          ('procurement_id', '=', move['procurement_id'])])
                            for fp_done in fp_done_ids.read(['uom_qty', 'sec_uom_qty', 'uoi_qty']):
                                move_qty_uom_total_done += fp_done['uom_qty']
                                move_qty_sec_uom_total_done += fp_done['sec_uom_qty']
                                move_qty_uoi_total_done += fp_done['uoi_qty']
                            
                            move_qty_uom = round(move_qty_uom_total - move_qty_uom_total_done, prod_digits)
                            move_qty_sec_uom = round(move_qty_sec_uom_total - move_qty_sec_uom_total_done, prod_digits)
                            move_qty_uoi = round(move_qty_uoi_total - move_qty_uoi_total_done, prod_digits)
                        else:
                            move_qty_uom = round(move['uom_qty'] * factor, prod_digits)
                            move_qty_sec_uom = round(move['sec_uom_qty'] * factor, prod_digits)
                            move_qty_uoi = round(move['uoi_qty'] * factor, prod_digits)
                        
                        move_brw = move_obj.browse(move['id'])
                        state_move = move_brw.state
                        move_brw.wkf_cancel()
                        if state_move != 'cancel':
                            dummy, new_move_brw = move_brw.wkf_draft()
                            if dummy:
                                move_brw = new_move_brw
                            
                        move_brw.write({'uom_qty': move_qty_uom,
                                        'sec_uom_qty': move_qty_sec_uom,
                                        'uoi_qty': move_qty_uoi})
                        
                        if state_move not in ('draft', 'cancel'):
                            move_brw.wkf_waiting()
                        
                wo.write({'quantity': round(wo.quantity * factor, prod_digits)})
                if wo.state != 'draft':
                    if wo.is_at_earlier:
                        date = wo.planned_start_date or fields.Datetime.now()
                        wo.action_plannification_wo_at_earlier(date, automatic_purchase=False, is_procur_level_manufact=False, is_procur_level_purchase=False, no_modif_prio_date=False)
                    else:
                        date = wo.planned_end_date or fields.Datetime.now()
                        wo.action_plannification_wo_at_the_latest(date, automatic_purchase=False, is_procur_level_manufact=False, is_procur_level_purchase=False, no_modif_prio_date=False)
                
                if wo.state == 'ready':
                    wo.wkf_waiting()
                    wo.wkf_ready()
                
                if wo.is_subcontracting:
                    self.compute_subcontracting_counterpart_move()
                    
            # Sinon: impossible
            else:
                raise except_orm(_('Error'), _('WO %s cannot be changed quantity: it is in state %s.')%(wo.name, wo.state))
        
        if spread:
            for mo in mo_rs:
                mo.write({'quantity': round(mo.quantity * factor, prod_digits)})
            
        return True
    
    
    def split_wo(self, wo_rs_to_split, coeff, data_other=None):
        """ 
            Diviser l'OT
            :param ids_to_split: Liste des OTs à modifier.
            :type ids_to_split: list d'ids
            :param coeff: Coefficient de division.
            :type coeff: Float.
            :return: True.
        """
        mo_obj = self.env['mrp.manufacturingorder']
        move_obj = self.env['stock.move']
        prev_wo_rcs = False
        mo_wo_to_split = {}
        mo_wo_to_splited = {}
        wo_wo_splited_ids = {}
        dic_wo_splited = []
        mo_wo_splited = {}
        mo_rcs = mo_obj.search([('workorder_ids', 'in', wo_rs_to_split.ids)])
        for mo in mo_rcs:
            wo_rcs = self.search([('mo_id', '=', mo.id)], order='sequence asc')
            # Si tous les OT sont splités on split l'OF
            if not wo_rcs - wo_rs_to_split:
                mo_wo_to_split[mo] = wo_rcs
        
        for wo in wo_rs_to_split:
            # Calcule de la quantité
            new_qty = wo.quantity/coeff
            rest_qty = wo.quantity - new_qty
            # Préparation de la copie de l'ot
            default={
             'quantity': rest_qty,
             'rm_draft_ids': [],
             'rm_done_ids': [],
             'fp_draft_ids': [],
             'fp_done_ids': [],
             'prev_wo_ids': [],
             'next_wo_ids': [],
             'split_id': wo.id,
                     }
            if not self.env.context.get('no_label'):
                default['name'] = '%s SPLITED'%(wo.name)
                
            if data_other:
                default.update(data_other)
                
            if self.env.context.get('no_label_splited'):
                default['name'] = '%s'%(wo.name)
            
                
            # Copie de l'ot
            new_wo_rcs = wo.with_context({'ok_copy': True}).copy(default)
            if data_other:
                new_wo_rcs.write(data_other)
            
            if new_wo_rcs.mo_id and new_wo_rcs.mo_id in mo_wo_to_splited and new_wo_rcs.mo_id in mo_wo_to_split:
                mo_wo_to_splited[new_wo_rcs.mo_id] += new_wo_rcs
            elif new_wo_rcs.mo_id and new_wo_rcs.mo_id not in mo_wo_to_splited and new_wo_rcs.mo_id in mo_wo_to_split:
                mo_wo_to_splited[new_wo_rcs.mo_id] = new_wo_rcs
                
            wo_wo_splited_ids[wo.id] = new_wo_rcs
            dic_wo_splited.append(new_wo_rcs.id)
            # Split les services consommés
            for service in wo.consumed_service_ids:
                #if service.type == 'fixed':
                #    service.copy({'wo_id':new_wo_rcs.id})
                #else:
                #    coeff_qty_service_copy = wo.quantity and service.quantity / wo.quantity or service.quantity
                #    service.copy({'wo_id': new_wo_rcs.id, 'quantity': coeff_qty_service_copy*rest_qty})
                #    service.write({'quantity': coeff_qty_service_copy*new_qty})
                service.copy({'wo_id': new_wo_rcs.id})
                
            # Incoming moves
            for rm_draft in wo.rm_draft_ids:
                rm_done_rcs = move_obj.search([('product_id', '=', rm_draft.product_id.id), ('state', '=', 'done'), ('wo_incoming_id', '=', wo.id)])
                qty_done = 0
                for rm_done in rm_done_rcs:
                    qty_done += rm_done.uom_qty

                qty_remaining = (new_qty * rm_draft.efficient_unit_qty) - qty_done
                coeff_rm_draft = qty_remaining and rm_draft.uom_qty / qty_remaining or 1.0
                rm_draft.split_light(coeff_rm_draft, wo_rest_qty=rest_qty, wo_new_qty=new_qty, component_done_qty=qty_done, new_wo_incoming_rcs=new_wo_rcs, wo_rcs=wo)
                
            # Outgoing moves
            for fp_draft in wo.fp_draft_ids:
                fp_done_rcs = move_obj.search([('product_id', '=', fp_draft.product_id.id),('state', '=', 'done'), ('wo_outgoing_id', '=', wo.id)])
                qty_done = 0
                for fp_done in fp_done_rcs:
                    qty_done += fp_done.uom_qty

                qty_remaining = (new_qty * fp_draft.efficient_unit_qty) - qty_done
                coeff_fp_draft = qty_remaining and fp_draft.uom_qty / qty_remaining or 1.0
                fp_draft.split_light(coeff_fp_draft, wo_rest_qty=rest_qty, wo_new_qty=new_qty, component_done_qty=qty_done, new_wo_outgoing_rcs=new_wo_rcs, wo_rcs=wo)
            
            # Si l'ope n'est pas la premiere splitée, son previous n'est plus le meme
            if prev_wo_rcs:
                new_wo_rcs.write({'prev_wo_ids': [(6, 0, [prev_wo_rcs.id])]})
            
            wo.write({'quantity': new_qty})
            prev_wo_rcs = new_wo_rcs
            
            if wo.state != 'draft':
                prev_temp_ids = self.search([('sequence', '<', wo.sequence), ('mo_id', '=', wo.mo_id.id)], limit=1)
                if wo.is_at_earlier and (not wo.prev_wo_ids or prev_temp_ids):
                    wo.action_plannification_wo_at_earlier(wo.planned_start_date, automatic_purchase=False, is_procur_level_manufact=False, 
                                                           is_procur_level_purchase=False, no_modif_prio_date=False)
                    if new_wo_rcs.state == 'draft':
                        new_wo_rcs.wkf_waiting(automatic_purchase=False, is_procur_level_manufact=True, is_procur_level_purchase=True, modif_state=True)
                            
                    new_wo_rcs.action_plannification_wo_at_earlier(new_wo_rcs.planned_start_date, automatic_purchase=False, is_procur_level_manufact=True, 
                                                                   is_procur_level_purchase=True, no_modif_prio_date=False)
                else:
                    wo.action_plannification_wo_at_the_latest(wo.planned_end_date, automatic_purchase=False, is_procur_level_manufact=False, 
                                                              is_procur_level_purchase=False, no_modif_prio_date=False)
                    
                    if new_wo_rcs.state == 'draft':
                        new_wo_rcs.wkf_waiting(automatic_purchase=False, is_procur_level_manufact=True, is_procur_level_purchase=True, modif_state=True)
                        
                    new_wo_rcs.action_plannification_wo_at_the_latest(new_wo_rcs.planned_end_date, automatic_purchase=True, is_procur_level_manufact=True, 
                                                                      is_procur_level_purchase=True, no_modif_prio_date=False)
            
        
        # Gestion des suivants et précédents
        for wo_id, wo_splited in wo_wo_splited_ids.items():
            vals = {}
            prec_ids = []
            for prev_wo in self.browse(wo_id).prev_wo_ids:
                if prev_wo.id in wo_wo_splited_ids:
                    prec_ids.append(wo_wo_splited_ids[prev_wo.id].id)
                else:
                    prec_ids.append(prev_wo.id)
                    
            if prec_ids:
                vals['prev_wo_ids'] = [(6, 0, prec_ids)]
            
            next_ids = []
            for next_wo in self.browse(wo_id).next_wo_ids:
                if next_wo.id in wo_wo_splited_ids:
                    next_ids.append(wo_wo_splited_ids[next_wo.id].id)
                else:
                    next_ids.append(next_wo.id)
                    
            if next_ids:
                vals['next_wo_ids'] = [(6, 0, next_ids)]
            
            if vals:
                wo_splited.write(vals)
        
        # Split des OF si tous ses OT ont été splités
        for mo_rcs, wo_rcs in mo_wo_to_splited.items():
            data_other_mo = data_other.copy()
            if 'name' in data_other_mo:
                del data_other_mo['name']
                
            new_mo_rcs = mo_rcs.split_light(coeff, data_other=data_other_mo)
            wo_rcs.write({'mo_id': new_mo_rcs.id})
            if wo_rcs:
                wo_rcs[0].state_mo()
            
            mo_wo_splited[new_mo_rcs] = wo_rcs
            if mo_rcs in mo_wo_to_split and mo_wo_to_split[mo_rcs]:
                mo_wo_to_split[mo_rcs][0].state_mo()
            
            if self.env.context.get('return_wo_splited') and wo_rcs and len(wo_rcs.ids) > 1 and new_mo_rcs.planned_start_date:
                self.plannification_mo_at_earlier(new_mo_rcs.planned_start_date, 
                                                  new_mo_rcs, 
                                                  is_sublevel=True, 
                                                  is_procur_level_manufact=True,
                                                  is_product_sublevel_manufact=True,
                                                  is_procur_level_purchase=True,
                                                  automatic_purchase=True,
                                                  is_procur_sublevel_purchase=True,
                                                  first_mo_id=False,
                                                  is_delay_rm=False,
                                                  change_resources=False, 
                                                  no_modif_prio_date=False)
        
        
        if self.env.context.get('return_mo_wo_splited'):
            return mo_wo_splited
        
        elif self.env.context.get('return_wo_splited'):
            return dic_wo_splited
        
        return True
    
    
    def action_plannification_wo_at_earlier(self, start_date, automatic_purchase=True, is_procur_level_manufact=True, is_procur_level_purchase=True, 
                                            is_delay_rm=False, no_modif_prio_date=False, change_resources=False):
        """ 
            Fonction qui calcule, à partir de la date de départ, la charge et les dates planifiées de départ et fin + création ligne de charge d'un OT
            :param is_delay_rm: Si l'on choisie le délai des matières premières
            :type is_delay_rm: boolean
            :return: Date de fin.
        """
        procurement_obj = self.env['procurement.order']
        loading_obj = self.env['calendar.loading']
        mo_obj = self.env['mrp.manufacturingorder']
        #Changement de resource
        if change_resources:
            self.change_resource_plannif(start_date, is_delay_rm=is_delay_rm, is_procur_level_manufact=is_procur_level_manufact, no_plannif=True)
            
        end_date_progress = start_date
        start_date_progress = start_date
        start_date_first = start_date
        end_date_final = start_date
        # Suppressions des lignes de charges
        loading_delete_rcs = loading_obj.search([('wo_id', '=', self.id)])
        if loading_delete_rcs:
            loading_delete_rcs.unlink()
        
        # Si l'ot est de sous-traitance et délai du fournisseur du service soit coché
        if self.is_subcontracting and self.is_supplier_delay_subc:
            # On utilise la fonction get_dates pour récupérer la date de fin et calculer les lignes dans la table de calendar.loading
            days_supplier = 1
            stop_days_supplier = False
            for consumed_service in self.consumed_service_ids:
                for sinfo in consumed_service.product_id.sinfo_ids:
                    days_supplier = sinfo.delivery_delay or 1
                    stop_days_supplier = True
                    break
                
                if stop_days_supplier:
                    break
                
            res_get_date = self.first_resource_id and self.first_resource_id.calendar_id.get_date(end_date_progress, days_supplier, hours=True) or ''
            if res_get_date and res_get_date > end_date_final:
                end_date_final = res_get_date
                
        # Si on calcule le temps par les temps de ressources
        else:
            no_resource = True
            for wo_resource in self.env['mrp.wo.resource'].search([('wo_id', '=', self.id)], order='sequence asc'):
                no_resource = False
                if not wo_resource.resource_id:
                    raise except_orm(_('Error'), _('There are not resource in WO'))
                
                if is_delay_rm:
                    res_availability_simulation_compute = self.availability_simulation_compute()
                    if res_availability_simulation_compute:
                        res_availability_simulation_compute = max(res_availability_simulation_compute)
                        end_date_progress = max(res_availability_simulation_compute, end_date_progress)
                        start_date_first = max(res_availability_simulation_compute, start_date_first)
                
                # S'il n'y a pas de temps
                if not wo_resource.total_time_theo and not wo_resource.total_time_theo_with_masked:
                    pass
                # Si le temps total masqué est à 0%
                elif wo_resource.total_time_theo and wo_resource.total_time_theo == wo_resource.total_time_theo_with_masked:
                    # On utilise la fonction get_dates pour récupérer la date de fin et calculer les lignes dans la table de calendar.loading
                    res_get_dates = wo_resource.resource_id.calendar_id.get_dates(end_date_progress, 
                                                                                  wo_resource.total_time_theo_with_masked, 
                                                                                  dico_create_load={'wo_id': self.id, 
                                                                                                    'resource_id': wo_resource.resource_id.id, 
                                                                                                    'area_id': wo_resource.resource_id.area_id.id, 
                                                                                                    'mo_id': self.mo_id.id, 
                                                                                                    'is_at_earlier': True, 
                                                                                                    'is_forecast': self.is_forecast})
                    if not res_get_dates['end_date']:
                        raise except_orm(_('Error'), _('There are not enough lines in the calendar to schedule the work order'))
                    
                    # On récupère la date de fin qui sera la date de début si une ressource est en partie masqué et la date de début pour toute les ressources à 100% masqué
                    start_date_progress = res_get_dates['start_date']
                    end_date_progress = res_get_dates['end_date']
                    if not start_date_first:
                        start_date_first = start_date_progress
                        
                    if res_get_dates['end_date'] > end_date_final:
                        end_date_final = res_get_dates['end_date']
                        
                # Si le temps total masqué est à 100%
                elif not wo_resource.total_time_theo and wo_resource.total_time_theo_with_masked:
                    # On utilise la fonction get_dates pour récupérer la date de fin et calculer les lignes dans la table de calendar.loading
                    res_get_dates = wo_resource.resource_id.calendar_id.get_dates(start_date_progress, 
                                                                                  wo_resource.total_time_theo_with_masked, 
                                                                                  dico_create_load={'wo_id': self.id, 
                                                                                                    'resource_id': wo_resource.resource_id.id, 
                                                                                                    'area_id': wo_resource.resource_id.area_id.id, 
                                                                                                    'mo_id': self.mo_id.id, 
                                                                                                    'is_at_earlier': True, 
                                                                                                    'is_forecast': self.is_forecast})
                # Si non
                else:
                    total_time_theo_masked = wo_resource.total_time_theo_with_masked - wo_resource.total_time_theo
                    # On utilise la fonction get_dates_inverse pour calculer la date de départ de la resource qui est masquée en partie et calculer les lignes dans la table de calendar.loading
                    wo_resource.resource_id.calendar_id.get_dates_inverse(end_date_progress, 
                                                                          total_time_theo_masked, 
                                                                          dico_create_load={'wo_id': self.id, 
                                                                                            'resource_id': wo_resource.resource_id.id, 
                                                                                            'area_id': wo_resource.resource_id.area_id.id, 
                                                                                            'mo_id': self.mo_id.id, 
                                                                                            'is_at_earlier': True, 
                                                                                            'is_forecast': self.is_forecast})
                    # On utilise la fonction get_dates pour récupérer la date de fin et calculer les lignes dans la table de calendar.loading
                    res_get_dates = wo_resource.resource_id.calendar_id.get_dates(end_date_progress, 
                                                                                  wo_resource.total_time_theo, 
                                                                                  dico_create_load={'wo_id': self.id, 
                                                                                                    'resource_id': wo_resource.resource_id.id, 
                                                                                                    'area_id': wo_resource.resource_id.area_id.id, 
                                                                                                    'mo_id': self.mo_id.id, 
                                                                                                    'is_at_earlier': True, 
                                                                                                    'is_forecast': self.is_forecast})
                    if not res_get_dates['end_date']:
                        raise except_orm(_('Error'), _('There are not enough lines in the calendar to schedule the work order'))
                    
                    if res_get_dates['end_date'] > end_date_final:
                        end_date_final = res_get_dates['end_date']
                        end_date_progress = res_get_dates['end_date']            
        
            if no_resource:
                raise except_orm(_('Error'), _('There are not resource in WO'))
        
        # On écrit les dates dans l'OT
        self.write({'planned_start_date': start_date_first, 'planned_end_date': end_date_final, 'is_at_earlier': True})
        # J'écris la date de départ plannifiée dans les mouvements des matières premières ni cancel ni done
        if self.rm_draft_ids:
            modif_move_rm = {'date_expected': start_date_first, 'date': start_date_first}
            if not no_modif_prio_date:
                modif_move_rm['priority_date'] = start_date_first
                
            self.rm_draft_ids.write(modif_move_rm)
        
        # J'écris la date de fin plannifiée dans les mouvements des produits finit qui ne sont ni cancel ni done
        if self.fp_draft_ids:
            modif_move_fp = {'date_expected': end_date_final, 'date': end_date_final}
            if not no_modif_prio_date:
                modif_move_fp['priority_date'] = end_date_final
                
            self.fp_draft_ids.write(modif_move_fp)

        for procurement in procurement_obj.search([('origin_wo_id', '=', self.id)]).read(['supply_method', 'mo_id'], load='_classic_write'):
            if procurement['supply_method'] == 'produce' and procurement['mo_id']:
                procurement_obj.browse(procurement['id']).write({'needed_date': start_date_first})
                mo_obj.browse(procurement['mo_id']).write({'max_end_date': start_date_first})
                
        return end_date_final
    
    
    def recursion_plannification_wo_at_earlier(self, start_date, res=None, automatic_purchase=True, is_procur_level_manufact=True, is_procur_level_purchase=True, 
                                               change_resources=False, is_delay_rm=False, no_modif_prio_date=False):
        """ 
            Fonction récursive qui permet de calculer les dates au plus tôt des OTs
            :param self: Le Recordset du dernier OT
            :type self: Un Recordset
            :param start_date: La date de départ du première OT
            :type start_date: Date
            :param res: Dico qui permet d'optimiser la recursion
            :type res: Dict
            :return: Date de fin.
        """
        if not res:
            res={}
            
        # Si l'ot n'est pas dans ces états on ne plannifie pas l'ot et l'on récupère la date de fin plannifiée
#         if self.state not in ('draft', 'waiting'):
        if self.state in ('cancel'):
            date_temp = self.planned_end_date
            if self.waiting_time_next_ope and self.first_resource_id:
                date_temp = self.first_resource_id.calendar_id.get_date(date_temp, self.waiting_time_next_ope, hours=True)
            
            res[self] = date_temp
        else:
            # Test Si l'oT à des précédents
            is_prev_wo = False
            if self.prev_wo_ids:
                prev_wo_ids = self.env['mrp.workorder']
                for prev_wo in self.prev_wo_ids:
                    if prev_wo.state not in ('cancel', 'done'):
                        prev_wo_ids += prev_wo
                        
                if prev_wo_ids:
                    is_prev_wo = True
            
            # Si l'oT à des précédents
            if is_prev_wo:
                # Pour chaque précédent on relance la fonction récursive de plannification si res ne contient pas l'ot et la date
                for prev in prev_wo_ids:
                    if prev not in res and prev.state not in ('cancel', 'done'):
                        res.update(prev.recursion_plannification_wo_at_earlier(start_date, res=res, automatic_purchase=automatic_purchase, is_procur_level_manufact=is_procur_level_manufact, 
                                                                               is_procur_level_purchase=is_procur_level_purchase, change_resources=change_resources, is_delay_rm=is_delay_rm, 
                                                                               no_modif_prio_date=no_modif_prio_date))
                    
                # Je récupère la date max des prècédents OT si vide je prends la date du jour
                dates = [res[x] for x in self.prev_wo_ids]
                date = dates and max(dates) or fields.Datetime.now() 
                # Je prends la date max entre la date des précédents OTs et la date de dispo des mes matières premières
                date = max([date, self.availability_date_rm])
                compute_date = date
            # Si pas OTs précédents
            else:
                compute_date = start_date
                
            # Je lance la plannification de l'OT
            date_temp = self.action_plannification_wo_at_earlier(compute_date, automatic_purchase=automatic_purchase, is_procur_level_manufact=is_procur_level_manufact, 
                                                                 is_procur_level_purchase=is_procur_level_purchase, is_delay_rm=is_delay_rm, 
                                                                 no_modif_prio_date=no_modif_prio_date, change_resources=change_resources)
            # Si l'OT un temps d'attente après la fin de l'OT
            if self.waiting_time_next_ope and self.first_resource_id:
                date_temp = self.first_resource_id.calendar_id.get_date(date_temp, self.waiting_time_next_ope, hours=True)
                
            # On ajoute à res l'ot et la date_start
            res[self] = date_temp
        
        return res
    
    
    def _get_resource_rcs(self, rl_resource_categ, start_date, quantity):
        #TODO Sylvain: à commenter
        calendar = self.env.user.find_user_calendar()
        prod_time = (rl_resource_categ.production_time * quantity + rl_resource_categ.preparation_time + rl_resource_categ.cleaning_time)
        config_obj = self.env['ir.config_parameter']
        coeff = float(config_obj.get_param('planning_period_coeff')) or 1
        date_start = calendar.get_dates_inverse(start_date, (prod_time * coeff))
        date_start = date_start and date_start['start_date'] or False
        if not date_start:
            raise except_orm(_('Error'), _('There are not enough lines in the calendar to schedule the work order'))
        date_end = calendar.get_dates(start_date, prod_time + prod_time * coeff)
        date_end = date_end and date_end['end_date'] or False
        if not date_end:
            raise except_orm(_('Error'), _('There are not enough lines in the calendar to schedule the work order'))
        resources = []
        if len(rl_resource_categ.rl_resource_ids):
            resource_ids = [x.resource_id for x in rl_resource_categ.rl_resource_ids]
        else:
            resource_ids = rl_resource_categ.category_id.resource_ids
        for resource_id in resource_ids:
            load = self.get_load(resource_id, date_start, date_end)
            resources.append((resource_id, load))
            
        def cmp_resources(resource1, resource2):
            resource1_overbooked = resource1[1] >= resource1[0].limit_loading
            resource2_overbooked = resource2[1] >= resource2[0].limit_loading
            if resource1_overbooked and not resource2_overbooked:
                return 1
            if resource2_overbooked and not resource1_overbooked:
                return -1
            return cmp(resource2[0].limit_loading - resource2[1], resource1[0].limit_loading - resource1[1])
        
        resources.sort(cmp=cmp_resources)
        if len(resources):
            return resources[0][0]
     
    def get_load(self, resource_id, date_start, date_end):
        #TODO Sylvain: à commenter
        date_start = date_start[:10]
        date_end = date_end[:10]
        self.env.cr.execute('''select sum(loading) as load 
        from calendar_loading co
        right outer join calendar_line ci on co.calendar_line_id = ci.id
        where co.start_date::date between %s and %s
        and resource_id=%s
        group by ci.id''', 
                            (date_start, date_end, resource_id.id))
        loading = self.env.cr.dictfetchall()
        if len(loading):
            return sum([x['load'] for x in loading])/len(loading)
        else:
            return 0
    
    
    def change_resource_plannif(self, date, is_delay_rm=False, is_procur_level_manufact=False, no_plannif=True):
        """ 
            Fonction de changer de ressource dans l'OT, si l'on coche le champ équilibrage de charge
            :param is_delay_rm: Si l'on choisie le délai des matières premières
            :type is_procur_level_manufact: boolean
            :param is_procur_level_manufact: Permet de savoir si on créer le niveau des ots
            :type is_procur_level_manufact: boolean
            :param no_plannif: Variable qui permet de ne pas faire une boucle infinie entre le changement de ressource et la plannification
            :type no_plannif: boolean
            :return: True
        
        """
        if self.wo_resource_ids:
            resource_id = self._get_resource_rcs(self.wo_resource_ids[0].rl_resource_category_id, date, self.quantity)
            if resource_id and self.first_resource_id != resource_id:
                self.change_resource(self.wo_resource_ids[0], resource_id, self.wo_resource_ids[0].rl_resource_category_id, is_delay_rm=is_delay_rm, 
                                     is_procur_level_manufact=is_procur_level_manufact, no_plannif=no_plannif)
            
        return True
    
    
    def action_plannification_wo_at_the_latest(self, end_date, automatic_purchase=True, is_procur_level_manufact=True, is_procur_level_purchase=True, 
                                               no_modif_prio_date=False, change_resources=False):
        """ 
            Fonction qui calcule, à partir de la date de fin, la charge et les dates planifiées de départ et fin + création ligne de charge
            Met a jour et renvoie la date
            :param end_date: Date de fin
            :type end_date: datetime
            :param automatic_purchase: Permet de savoir si on gère les achats dans les mouvement
            :type automatic_purchase: boolean
            :param is_procur_level_manufact: Permet de savoir si on créer le niveau des ots
            :type is_procur_level_manufact: boolean
            :param is_procur_level_purchase: Permet de savoir si on créer le niveau des achats
            :type is_procur_level_purchase: boolean
            :return: Date de fin.
        """
        procurement_obj = self.env['procurement.order']
        loading_obj = self.env['calendar.loading']
        mo_obj = self.env['mrp.manufacturingorder']
        # Changement de resource
        if change_resources:
            self.change_resource_plannif(end_date, is_delay_rm=False, is_procur_level_manufact=is_procur_level_manufact, no_plannif=True)
        
        # Date de départ en cours car on utilise get_dates_inverse
        end_date_progress = end_date
        # Date de fin en cours car on utilise get_dates_inverse
        start_date_progress = end_date
        # Date de départ finale
        start_date_final = end_date
        # Date de fin
        end_date_first = end_date
        # Suppressions des lignes de charges
        loading_delete_rcs = loading_obj.search([('wo_id', '=', self.id)])
        if loading_delete_rcs:
            loading_delete_rcs.unlink()
        
        # Si l'ot est de sous-traitance et que le délai du fournisseur du service soit coché
        if self.is_subcontracting and self.is_supplier_delay_subc:
            # On utilise la fonction get_dates pour récupérer la date de fin et calculer les lignes dans la table de calendar.loading
            days_supplier = 1
            for consumed_service in self.consumed_service_ids:
                sinfo_rs = consumed_service.product_id.sinfo_ids
                if sinfo_rs:
                    days_supplier = sinfo_rs[0].read(['delivery_delay'])[0]['delivery_delay'] or 1
                    break
                
            res_get_date = self.first_resource_id and self.first_resource_id.calendar_id.get_date_inverse(end_date_progress, days_supplier, hours=True) or ''
            if res_get_date and res_get_date < start_date_final:
                start_date_final = res_get_date
                
        # Si on calcule le temps par les temps de ressources
        else:
            no_resource = True
            for wo_resource in self.env['mrp.wo.resource'].search([('wo_id', '=', self.id)], order='sequence asc'):
                no_resource = False
                if not wo_resource.resource_id:
                    raise except_orm(_('Error'), _('There are not resource in WO'))
    
                # S'il n'y a pas de temps
                if not wo_resource.total_time_theo and not wo_resource.total_time_theo_with_masked:
                    pass
                # Si le temps total masqué est à 0%
                elif wo_resource.total_time_theo and wo_resource.total_time_theo == wo_resource.total_time_theo_with_masked:
                    # On utilise la fonction get_dates pour récupérer la date de fin et calculer les lignes dans la table de calendar.loading
                    res_get_dates = wo_resource.resource_id.calendar_id.get_dates_inverse(end_date_progress, 
                                                                                          wo_resource.total_time_theo_with_masked, 
                                                                                          dico_create_load={'wo_id': self.id, 
                                                                                                            'resource_id': wo_resource.resource_id.id, 
                                                                                                            'area_id': wo_resource.resource_id.area_id.id, 
                                                                                                            'mo_id': self.mo_id.id, 
                                                                                                            'is_at_earlier': False, 
                                                                                                            'is_forecast': self.is_forecast})
                    if not res_get_dates['start_date']:
                        raise except_orm(_('Error'), _('There are not enough lines in the calendar to schedule the work order'))
                    
                    # On récupère la date de début qui sera la date de fin si une ressource est en partie masqué et la date de fin pour toute les ressources à 100% masqué
                    start_date_progress = res_get_dates['end_date']
                    end_date_progress = res_get_dates['start_date']
                    if not end_date_first:
                        end_date_first = res_get_dates['end_date']
                        
                    if res_get_dates['start_date'] < start_date_final:
                        start_date_final = res_get_dates['start_date']
                        
                # Si le temps total masqué est à 100%
                elif not wo_resource.total_time_theo and wo_resource.total_time_theo_with_masked:
                    # On utilise la fonction get_dates pour récupérer la date de fin et calculer les lignes dans la table de calendar.loading
                    wo_resource.resource_id.calendar_id.get_dates_inverse(start_date_progress, 
                                                                          wo_resource.total_time_theo_with_masked, 
                                                                          dico_create_load={'wo_id': self.id, 
                                                                                            'resource_id': wo_resource.resource_id.id, 
                                                                                            'area_id': wo_resource.resource_id.area_id.id, 
                                                                                            'mo_id': self.mo_id.id, 
                                                                                            'is_at_earlier': False, 
                                                                                            'is_forecast': self.is_forecast})
                # Sinon
                else:
                    total_time_theo_masked = wo_resource.total_time_theo_with_masked - wo_resource.total_time_theo
                    # On utilise la fonction get_dates_inverse pour calculer la date de départ de la resource qui est masquée en partie et calculer les lignes dans la table de calendar.loading
                    wo_resource.resource_id.calendar_id.get_dates_inverse(end_date_progress, 
                                                                          total_time_theo_masked, 
                                                                          dico_create_load={'wo_id': self.id, 
                                                                                            'resource_id': wo_resource.resource_id.id, 
                                                                                            'area_id': wo_resource.resource_id.area_id.id, 
                                                                                            'mo_id': self.mo_id.id, 
                                                                                            'is_at_earlier': False, 
                                                                                            'is_forecast': self.is_forecast})
                    # On utilise la fonction get_dates pour récupérer la date de fin et calculer les lignes dans la table de calendar.loading
                    res_get_dates = wo_resource.resource_id.calendar_id.get_dates_inverse(end_date_progress, 
                                                                                          wo_resource.total_time_theo, 
                                                                                          dico_create_load={'wo_id': self.id, 
                                                                                                            'resource_id': wo_resource.resource_id.id, 
                                                                                                            'area_id': wo_resource.resource_id.area_id.id, 
                                                                                                            'mo_id': self.mo_id.id, 
                                                                                                            'is_at_earlier':False, 
                                                                                                            'is_forecast': self.is_forecast})
                    if not res_get_dates['end_date']:
                        raise except_orm(_('Error'), _('There are not enough lines in the calendar to schedule the work order'))
                    
                    if res_get_dates['start_date'] < start_date_final:
                        start_date_final = res_get_dates['start_date']
                        end_date_progress = res_get_dates['start_date']       
        
            if no_resource:
                raise except_orm(_('Error'), _('There are not resource in WO'))
        
        # Écriture des dates dans l'OT
        self.write({'planned_start_date': start_date_final, 'planned_end_date': end_date_first})
        # Écriture de la date de départ plannifiée dans les mouvements des matières premières ni cancel ni done
        if self.rm_draft_ids:
            modif_move_rm = {'date_expected': start_date_final, 'date': start_date_final}
            if not no_modif_prio_date:
                modif_move_rm['priority_date'] = start_date_final
                
            self.rm_draft_ids.write(modif_move_rm)
        
        # Écriture de la date de fin plannifiée dans les mouvements des produits finit qui ne sont ni cancel ni done
        if self.fp_draft_ids:
            modif_move_fp = {'date_expected': end_date_first, 'date': end_date_first}
            if not no_modif_prio_date:
                modif_move_fp['priority_date'] = end_date_first
                
            self.fp_draft_ids.write(modif_move_fp)

        # Passage de l'OT à waiting si ce n'est pas déjà le cas et donc les mouvements
        if self.state == 'draft':
            self.wkf_waiting(automatic_purchase=automatic_purchase, is_procur_level_manufact=is_procur_level_manufact, is_procur_level_purchase=is_procur_level_purchase, modif_state=True)
        elif self.state in ('waiting', 'plan'):
            self.wkf_waiting(automatic_purchase=automatic_purchase, is_procur_level_manufact=is_procur_level_manufact, is_procur_level_purchase=is_procur_level_purchase, modif_state=False)
            
        for procurement in procurement_obj.search([('origin_wo_id', '=', self.id)]).read(['supply_method', 'mo_id'], load='_classic_write'):
            if procurement['supply_method'] == 'produce' and procurement['mo_id']:
                procurement_obj.browse(procurement['id']).write({'needed_date': start_date_final})
                mo_obj.browse(procurement['mo_id']).write({'max_end_date': start_date_final})
        
        if self.is_subcontracting:
            warning_subc = ''
            name_action = _('Warning Change Date WO %s')%(self.name_get()[0][1])
            action_obj = self.env['calendar.event']
            # Partie achat de ST MP
            warning_purchase_rm = self.env['purchase.order']
            for pol_rm in self.wo_subc_pol_rm_ids:
                if pol_rm.purchase_state != 'draft':
                    warning_subc += _('Warning Purchase Order Line RM (Order: %s, Product: %s, Id: %d)\n')%(pol_rm.purchase_order_id.name, pol_rm.product_id.name, pol_rm.id)
                    if pol_rm.purchase_order_id not in warning_purchase_rm:
                        warning_purchase_rm += pol_rm.purchase_order_id
                else:
                    if pol_rm.purchase_state != 'cancel':
                        pol_rm.write({'expected_date': start_date_final})
            
            if warning_purchase_rm:
                description_warn_st = _('Warning Purchase Order RM (new date %s)')%(start_date_final)
                for warning_purchase in warning_purchase_rm:
                    action_obj.create({ 'name': name_action,
                                        'requested_by_user_id': self.env.user.id,
                                        'affected_user_id': warning_purchase.purchaser_id.id,
                                        'purchase_id': warning_purchase.id,
                                        'date': fields.Date.today(),
                                        'description': description_warn_st,
                                       })
            
            # Partie mouvement de ST MP   
            warning_picking_rm = self.env['stock.picking']
            for move_rm in self.wo_subc_move_rm_ids:
                if move_rm.state not in  ('draft', 'waiting') or (move_rm.state == 'waiting' and move_rm.purchase_line_id and move_rm.purchase_line_id.purchase_state not in ('draft', 'cancel')):
                    warning_subc += _('Warning Move RM (Product: %s, Id: %d)\n')%(move_rm.product_id.name, move_rm.id)
                    if move_rm.picking_id not in warning_picking_rm:
                        warning_picking_rm += move_rm.picking_id
                else:
                    if move_rm.state != 'cancel':
                        modif_move_rm_sub = {'date_expected': start_date_final, 'date': start_date_final }
                        if not no_modif_prio_date:
                            modif_move_rm_sub['priority_date'] = start_date_final
                            
                        move_rm.write(modif_move_rm_sub)
            
            if warning_picking_rm:
                description_warn_st = _('Warning Picking RM (new date %s)')%(start_date_final)
                for warning_picking in warning_picking_rm:
                    action_obj.create({ 'name': name_action,
                                        'requested_by_user_id': self.env.user.id,
                                        'affected_user_id': self.env.user.id,
                                        'picking_id': warning_picking.id,
                                        'date': fields.Date.today(),
                                        'description': description_warn_st,
                                       })
                    
            # Partie achat de ST FP
            warning_purchase_fp = self.env['purchase.order']
            for pol_fp in self.wo_subc_pol_fp_ids:
                if pol_fp.purchase_state != 'draft':
                    warning_subc += _('Warning Purchase Order Line PF (Order: %s, Product: %s, Id: %d)\n')%(pol_fp.purchase_order_id.name, pol_fp.product_id.name, pol_fp.id)
                    if pol_fp.purchase_order_id not in warning_purchase_fp:
                        warning_purchase_fp += pol_fp.purchase_order_id
                else:
                    if pol_fp.purchase_state != 'cancel':
                        pol_fp.write({'expected_date': end_date})
            
            if warning_purchase_fp:
                description_warn_st = _('Warning Purchase Order FP (new date %s)')%(end_date)
                for warning_purchase in warning_purchase_fp:
                    action_obj.create({ 'name': name_action,
                                        'requested_by_user_id': self.env.user.id,
                                        'affected_user_id': warning_purchase.purchaser_id.id,
                                        'purchase_id': warning_purchase.id,
                                        'date': fields.Date.today(),
                                        'description': description_warn_st,
                                       })
                    
            # Partie mouvement de ST FP    
            warning_picking_fp = self.env['stock.picking'] 
            for move_fp in self.wo_subc_move_fp_ids:
                if move_fp.state not in  ('draft', 'waiting') or (move_fp.state == 'waiting' and move_fp.purchase_line_id and move_fp.purchase_line_id.purchase_state not in ('draft', 'cancel')):
                    warning_subc += _('Warning Move PF (Product: %s, Id: %d)\n')%(move_fp.product_id.name, move_fp.id)
                    if move_fp.picking_id not in warning_picking_fp:
                        warning_picking_fp += move_fp.picking_id
                else:
                    if move_fp.state != 'cancel':
                        if move_rm.state != 'cancel':
                            modif_move_fp_sub = {'date_expected': start_date_final, 'date': start_date_final}
                            if not no_modif_prio_date:
                                modif_move_fp_sub['priority_date'] = start_date_final
                            
                        move_fp.write(modif_move_fp_sub)
            
            if warning_picking_fp:
                description_warn_st = _('Warning Picking FP (new date %s)')%(end_date)
                for warning_picking in warning_picking_fp:
                    action_obj.create({ 'name': name_action,
                                        'requested_by_user_id': self.env.user.id,
                                        'affected_user_id': self.env.user.id,
                                        'picking_id': warning_picking.id,
                                        'date': fields.Date.today(),
                                        'description': description_warn_st,
                                       })
            
            if warning_subc:
                self.write({'warning_subc': warning_subc, 'is_warning_subc': True})
            else:
                self.write({'warning_subc': '', 'is_warning_subc': False})
            
        return start_date_final
    
    
    def recursion_plannification_wo_at_the_latest(self, end_date, res=None, automatic_purchase=True, is_procur_level_manufact=True, is_procur_level_purchase=True, 
                                                  change_resources=False, no_modif_prio_date=False, is_product_sublevel_manufact=True):
        """ 
            Fonction récursive qui permet de calculer les dates au plus tard des OTs
            :param self: Le Recordset du dernier OT
            :type self: Un Recordset
            :param end_date: La date de fin du dernier OT
            :type start_date: Date
            :param res: Dico qui permet d'optimiser la recursion
            :type res: Dict
            :return: Date de fin.
        """
        if not res:
            res={}
        
        # Si l'ot n'est pas dans ces états on ne plannifie pas l'ot et l'on récupère la date de départ plannifiée
#         if self.state not in ('draft', 'waiting'):
        if self.state in ('cancel'):
            res[self] = self.planned_start_date
        # Si non
        else:
            # Variable qui permet de savoir si tous les OTs suivant sont plannifiés
            all_compute = True
            date_temp = []
            # On teste si l'OT à des suivants à fin de savoir si tous les OTs suivants sont déjà plannifiés
            for next_wo in self.next_wo_ids:
                # On teste si l'OT est plannifié si on prend sa date que l'on met dans une liste 
                if next_wo in res:
                    date_temp.append(res[next_wo])
                # Si non, on ne plannifie pas l'ot et on continue de plannifier tous les anciens avant de le calculer
                else:
                    all_compute = False
            
            # Si tous les OTs suivant sont plannifiés
            if all_compute:
                # On recupère la date de départ des OTs suivant afin de calculer l'OT contenu dans le self
                # S'il a des OTs suivants
                if date_temp:
                    # On prend la plus petite date de départ des OTs suivants
                    date_temp = min(date_temp)
                    if self.first_resource_id and date_temp:
                        # Et on soustrait à cette date le temps d'attente de l'OT contenu dans le self afin d'avoir la date de fin de fin
                        date_temp = self.first_resource_id.calendar_id.get_date_inverse(date_temp, self.waiting_time_next_ope, hours=True)
                # Si non on prend la date de fin
                else:
                    date_temp = end_date
                
                # On calcule la date et on ajoute à res l'ot et la date_end
                res[self] = self.action_plannification_wo_at_the_latest(date_temp, automatic_purchase=automatic_purchase, is_procur_level_manufact=is_procur_level_manufact, 
                                                                        is_procur_level_purchase=is_procur_level_purchase, no_modif_prio_date=no_modif_prio_date, change_resources=change_resources)
            
            # Si l'OT a des OTs précédents on relance la fonction récursive de plannification
            if self.prev_wo_ids:
                for prev in self.prev_wo_ids:
                    if prev not in res and prev.state not in ('cancel', 'done'):
                        res.update(prev.recursion_plannification_wo_at_the_latest(end_date, res=res, automatic_purchase=automatic_purchase, 
                                                                                  is_procur_level_manufact=is_procur_level_manufact, is_procur_level_purchase=is_procur_level_purchase, 
                                                                                  change_resources=change_resources, no_modif_prio_date=no_modif_prio_date, is_product_sublevel_manufact=is_product_sublevel_manufact))
        
        return res
    
    
    
    def additional_function_domain(self, arg):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de mrp_workorder
        """
        arg0, arg1, arg_1 = False, False, False
        # Permet de retrouver des wo à partir d'une ressource
        if arg[0] == 'find_wo_with_resource':
            arg0 = 'id'
            arg1 = 'in'
            wo_resources_rcs = self.env['mrp.wo.resource'].search([('resource_id','=',arg[-1])])
            arg_1 = [x.wo_id.id for x in wo_resources_rcs if x.wo_id and x.wo_id.state not in ('draft', 'cancel')]
        
        return arg0, arg1, arg_1
    
    
    def compute_domain_args_wo(self, args):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de mrp_workorder
        """
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
    def search(self, args=None, offset=0, limit=None, order=None, count=None):
        """
            Fonction search de l'OT 
        """
        args = args or []
        args_modified = self.compute_domain_args_wo(args)
        return super(mrp_workorder,self).search(args=args_modified, offset=offset, limit=limit, order=order, count=count)
    
            
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=1000):
        """
            Fonction name_search de l'OT
        """
        recs = False
        context = self.env.context
        if 'domain_scan_id' in context and context['domain_scan_id'] and name:
            recs = self.search([('id', '=', name)], limit=limit)
        else:
            args_modified = self.compute_domain_args_wo(args)
            if name:
                mo_ids = self.env['mrp.manufacturingorder'].search([('name', operator, name)], limit=limit)
                if mo_ids:
                    wo_ids = self.search(['|', '|', ('sequence', operator, name), ('name', operator, name), ('mo_id', 'in', mo_ids.ids)], limit=limit)
                else:
                    wo_ids = self.search(['|',('sequence', operator, name), ('name', operator, name)], limit=limit)
                
                list_wo_ids = [x.id for x in wo_ids]
                recs = self.search([('id', 'in', list_wo_ids)] + args_modified, limit=limit)
                
            if not recs:
                recs = self.search([('name', operator, name)] + args_modified, limit=limit)
            
        return recs.name_get()
    
    
    def plannification_mo_at_the_latest(self, date, mo, is_sublevel=False, is_procur_level_manufact=False,
                                              is_product_sublevel_manufact=False, is_procur_level_purchase=False, automatic_purchase=False,
                                              is_procur_sublevel_purchase=False, first_pass=False, change_resources=False, no_modif_prio_date=False):
        """
            Première méthode appellée pour la planification des OT au plus tard
            :param self: Le Recordset du dernier OT
            :type self: Un Recordset
            :param date: La date OT
            :type date: Date
            :param automatic_purchase: Permet de savoir si on gère les achats dans les mouvement
            :type automatic_purchase: boolean
            :param is_procur_level_manufact: Permet de savoir si on créer le niveau des ots
            :type is_procur_level_manufact: boolean
            :param is_procur_level_purchase: Permet de savoir si on créer le niveau des achats
            :type is_procur_level_purchase: boolean
            :param is_product_sublevel_manufact: Permet de savoir si on créer les sous niveaux des ots
            :type is_product_sublevel_manufact: boolean
            :param is_procur_sublevel_purchase: Permet de savoir si on créer les sous niveaux des achats
            :type is_procur_sublevel_purchase: boolean
            :return True
        """
        procurement_obj = self.env['procurement.order']
        workorder_rcs = self.search([('mo_id', '=', mo.id), ('state', 'not in', ('cancel', 'done'))], order='sequence desc', limit=1)
        if is_sublevel:
            is_procur_level_manufact = True
            is_product_sublevel_manufact = True
            is_procur_level_purchase = True
            automatic_purchase = True
            is_procur_sublevel_purchase = True
        else:    
            if is_product_sublevel_manufact:
                is_procur_level_manufact = True
            
            if is_procur_sublevel_purchase:
                is_procur_level_purchase = True
            
        if workorder_rcs:
            if not first_pass:
                # On soustrait à la date le temps d'attente de l'OT contenu dans le dernier OT afin d'avoir la date de fin de l'OT
                date = workorder_rcs[0].first_resource_id and workorder_rcs[0].first_resource_id.calendar_id.get_date_inverse(date, workorder_rcs[0].waiting_time_next_ope, hours=True) or date
            else:
                mo.validate_move_fp_intervention()
                
            first_pass = False
            # Déclanche la planification de tous les OT de l'OF en partant du dernier
            workorder_rcs[0].recursion_plannification_wo_at_the_latest(date, res=None, automatic_purchase=automatic_purchase, 
                                                                   is_procur_level_manufact=is_procur_level_manufact, is_procur_level_purchase=is_procur_level_purchase, 
                                                                   change_resources=change_resources, no_modif_prio_date=no_modif_prio_date, is_product_sublevel_manufact=is_product_sublevel_manufact)
            
            if not is_procur_sublevel_purchase and not is_sublevel and is_product_sublevel_manufact:
                automatic_purchase = False
                is_procur_level_purchase = False
                        
            date = mo.planned_start_date or fields.Datetime.now()
            if is_product_sublevel_manufact:
                for wo in mo.workorder_ids:
                    for procurement in procurement_obj.search([('origin_wo_id', '=', wo.id)]):
                        if procurement.supply_method == 'produce' and procurement.mo_id:
                            if not is_product_sublevel_manufact:
                                is_procur_level_manufact_inter = False
                            else:
                                is_procur_level_manufact_inter = True
                            
                            if not is_procur_sublevel_purchase:
                                is_procur_level_purchase_inter = False
                            else:
                                is_procur_level_purchase_inter = True   
                                 
                            # Calcul des autres OF générés par le procurement
                            self.plannification_mo_at_the_latest(date, procurement.mo_id, is_sublevel=is_sublevel, 
                                                                 is_procur_level_manufact=is_procur_level_manufact_inter,
                                                                 is_product_sublevel_manufact=is_product_sublevel_manufact, is_procur_level_purchase=is_procur_level_purchase_inter, 
                                                                 automatic_purchase=automatic_purchase, is_procur_sublevel_purchase=is_procur_sublevel_purchase, first_pass=first_pass, 
                                                                 change_resources=change_resources, no_modif_prio_date=no_modif_prio_date)
            
        return True
    
    
    def plannification_mo_at_earlier(self, date, mo, is_sublevel=False, is_procur_level_manufact=False,
                                           is_product_sublevel_manufact=False, is_procur_level_purchase=False, automatic_purchase=False,
                                           is_procur_sublevel_purchase=False, first_mo_id=False, is_delay_rm=False, change_resources=False, no_modif_prio_date=False):
        """
            Si premier OF (OF principal): lancement de sa plannification au plus tôt
            Sinon (OF de sous niveau): lancement de sa plannification au plus tard par rapport a la date de début de l'OF suivant
            Si sous niveau: planification des sous niveaux
        """
        procurement_obj = self.env['procurement.order']
        workorder_rcs = self.search([('mo_id', '=', mo.id), ('state', 'not in', ('cancel', 'done'))])
        if is_sublevel:
            is_procur_level_manufact = True
            is_product_sublevel_manufact = True
            is_procur_level_purchase = True
            automatic_purchase = True
            is_procur_sublevel_purchase = True
        else:
            if is_product_sublevel_manufact:
                is_procur_level_manufact = True
            
            if is_procur_sublevel_purchase:
                is_procur_level_purchase = True
        
        if not first_mo_id:
            first_mo_id = mo.id
        
        if workorder_rcs:
            for workorder in workorder_rcs:
                if workorder.state == 'draft':
                    workorder.wkf_waiting(automatic_purchase=automatic_purchase, is_procur_level_manufact=is_procur_level_manufact, is_procur_level_purchase=is_procur_level_purchase, modif_state=True)
                elif workorder.state in ('waiting', 'plan'):
                    workorder.wkf_waiting(automatic_purchase=automatic_purchase, is_procur_level_manufact=is_procur_level_manufact, is_procur_level_purchase=is_procur_level_purchase, modif_state=False)
            
            if is_sublevel or is_product_sublevel_manufact:
                # Si pas de demande de génération d'achat: automatic_purchase=False
                if not is_procur_sublevel_purchase and not is_sublevel:
                    automatic_purchase = False
                    is_procur_level_purchase = False
                    
                date_return = [date]
                for wo in mo.workorder_ids:
                    for procurement in procurement_obj.search([('origin_wo_id', '=', wo.id), 
                                                               ('supply_method', '=', 'produce'), 
                                                               ('mo_id', '!=', False)]):
                        if not is_product_sublevel_manufact:
                            is_procur_level_manufact_inter = False
                        else:
                            is_procur_level_manufact_inter = True
                        
                        if not is_procur_sublevel_purchase:
                            is_procur_level_purchase_inter = False
                        else:
                            is_procur_level_purchase_inter = True   
                        
                        date_return.append(self.plannification_mo_at_earlier(date, procurement.mo_id, is_sublevel=is_sublevel, 
                                                          is_procur_level_manufact=is_procur_level_manufact_inter,
                                                          is_product_sublevel_manufact=is_product_sublevel_manufact, is_procur_level_purchase=is_procur_level_purchase_inter, 
                                                          automatic_purchase=automatic_purchase, is_procur_sublevel_purchase=is_procur_sublevel_purchase, first_mo_id=first_mo_id, 
                                                          is_delay_rm=is_delay_rm, change_resources=change_resources, no_modif_prio_date=no_modif_prio_date))
                date = max(date_return)
            
            last_workorder_rcs = self.search([('mo_id', '=', mo.id), ('state', 'not in', ('cancel', 'done'))], order='sequence desc', limit=1)
            res = last_workorder_rcs.recursion_plannification_wo_at_earlier(date, res=None, automatic_purchase=automatic_purchase, 
                                                                           is_procur_level_manufact=is_procur_level_manufact, is_procur_level_purchase=is_procur_level_purchase,
                                                                           change_resources=change_resources, is_delay_rm=is_delay_rm, no_modif_prio_date=no_modif_prio_date)
            
            date = max(res.values())
            
        return date
    
    @api.multi
    def plannification_wo_done(self, automatic_purchase=True):
        """
            Permet de terminer la plannification
        """
        if not self.planned_start_date or not self.planned_end_date:
            raise except_orm(_('Error'), _('We must first plannifier self.'))
        
        self.wkf_waiting(automatic_purchase=automatic_purchase, is_procur_level_manufact=True, is_procur_level_purchase=True)
        self.wkf_plan()
        if automatic_purchase:
            self.validate_procurement_rm()

        return self.state
    
    
    def create_wo_without_bom(self, rl, mo, sequence, other_data_arg=None):
        """
            Fonction qui permet de créer un OT sans bom
            :param mo: Recordset de l'of
            :type mo: Recordset
            :param rl: Recordset de la gamme
            :type rl: Recordset
            :param sequence: sequence
            :type sequence: int
            :return MO_RCS
            
        """
        # Boucler sur les catégories de ressources
        other_data = {}
        resource_list_vals = []
        for rl_resource_categ in rl.rl_resource_category_ids:
            rl_resource_categ_vals = self.prepare_wo_resource(rl_resource_categ, mo)
            if rl_resource_categ_vals:
                resource_list_vals.append([0, 0, rl_resource_categ_vals])
        
        # Boucler sur les services consommés
        consum_serv_list_vals = []
        for consum_serv in rl.consumed_service_ids.read(['quantity', 'product_id', 'uom_id', 'type'], load='_classic_write'):
            qy_service = consum_serv['quantity']     
            consum_serv_vals = {
                        'product_id': consum_serv['product_id'],
                        'quantity': qy_service,
                        'uom_id': consum_serv['uom_id'],
                        'type': consum_serv['type']
                    }
            if consum_serv_vals:
                consum_serv_list_vals.append([0, 0, consum_serv_vals])
        
        # Boucler sur les outils
        tool_list_vals = []
        for tool in rl.tool_ids.read(['quantity', 'product_id', 'uom_id'], load='_classic_write'):
            tool_vals = {
                        'product_id': tool['product_id'],
                        'quantity': tool['quantity'] * mo.quantity,
                        'uom_id': tool['uom_id']
                    }
            if tool_vals:
                tool_list_vals.append([0, 0, tool_vals])
        
        # Boucler sur les consignes
        consign_list_vals = []
        for consign in rl.consign_ids.read(['name', 'frequency', 'type', 'desciptive', 'means'], load='_classic_write'):
            consign_vals = {
                        'name': consign['name'],
                        'frequency': consign['frequency'],
                        'type': consign['type'],
                        'desciptive': consign['desciptive'],
                        'means': consign['means']
                    }
            consign_list_vals.append([0, 0, consign_vals])

        wo_vals = self.prepare_wo(rl, mo, resource_list_vals=resource_list_vals, consum_serv_list_vals=consum_serv_list_vals, tool_list_vals=tool_list_vals, 
                                  consign_list_vals=consign_list_vals, other_data=other_data, sequence=sequence)
        
        if other_data_arg:
            wo_vals.update(other_data_arg)
            
        return self.create(wo_vals)
    

    def create_mo_light(self, product, quantity, uom, routing_id, bom_id=False, other_data=None):
        """
            Fonction qui permet de créer un OF light avec bom_id optionnelle
            :param product: Recordset du produit
            :type product: Recordset
            :param uom: Recordset de l'uom
            :type uom: Recordset
            :param routing_id: ID de la gamme
            :type routing_id: integer
            :param quantity: Quantité
            :type quantity: float
            :param bom_id: ID de la nomenclature optionnelle
            :type bom_id: integer
            :return MO_RCS
            
        """
        prod_family_id = product.prod_family_id and product.prod_family_id.id or False
        parameter_list = []
        name = self.env['ir.sequence'].get('mrp.manufacturingorder')
        internal_plan_ids = [(4, plan_control.pdf_file.id) for plan_control in product.plan_control_ids if plan_control.type == 'pdf_production']
        for param in product.parameter_ids:
            cont = False
            for line in parameter_list:
                if line[2]['name'] == param.name:
                    cont = True
                    break
                
            if cont:
                continue
            
            parameter_list.append((0, 0, {'name': param.name, 'type_param_id': param.type_param_id.id, 'value': param.value, }))
        
        needed_quantity = quantity
        if bom_id:
            is_without_bom = False
        else:
            is_without_bom = True
            
        vals = {
            'name': name,
            'product_id': product.id,
            'quantity': quantity,
            'needed_quantity': needed_quantity,
            'uom_id': uom.id,
            'bom_id': bom_id,
            'routing_id': routing_id,
            'option_ids':[],
            'variant_value_ids':[],
            'parameter_ids': parameter_list,
            'internal_plan_ids': internal_plan_ids,
            'prod_family_id': prod_family_id,
            'is_without_bom': is_without_bom,
        }
        if other_data:
            vals.update(other_data)

        return self.env['mrp.manufacturingorder'].create(vals)

    
    
    def add_operation_wo(self, routing_line_ids, solution1, solution2, solution3, solution4, arg_rl_sequences=[], no_wo=None, other_data_arg=None):
        """
            Fonction utilisé dans l'ajout d'opération dans un ot et dans la création d'OF de réparation
            :param self: Le Recordset OT si ot si non remplire l'argument no_wo
            :type self: Un Recordset
            :param routing_line_ids: Les de Recordset des lignes de gammes
            :type routing_line_ids: list ids
            :param solution1: Si solution 1 choisie
            :type solution1: boolean
            :param solution2: Si solution 2 choisie
            :type solution2: boolean
            :param solution3: Si solution 3 choisie
            :type solution3: boolean
            :param solution4: Si solution 4 choisie
            :type solution4: boolean
            :param arg_rl_sequences: Liste de tuple [(sequence de la ligne de gamme, id de la ligne de gamme)]. Argument pour la réparation
            :type arg_rl_sequences: List
            :param no_wo: Dico de valeur pour créer un OF {'quantity':.., 'uom':.., 'product':.., 'routing_id':..} et bom_id en option .Argument pour la réparation
            :type no_wo: Dico
            :return MO_RCS
        """
        move_obj = self.env['stock.move']
        uom_obj = self.env['product.uom']
        routing_line_obj = self.env['mrp.routing.line']
        wo = self
        # Test si on a sélectionné au moins une solution
        if sum([solution1, solution2, solution3, solution4]) != 1:
            raise except_orm(_('Error'), _('Select only one solution.'))
        
        if not routing_line_ids:
            raise except_orm(_('Error'), _('Select routing lines.'))
        
        other_data = {}
        if not no_wo:
            #Partie ajout d'opération
            quantity_ot = wo.quantity
            mo = wo.mo_id
            quantity_bom = mo.bom_id and mo.bom_id.quantity or 1.0
            uom = wo.uom_id
            if wo.mo_id.bom_id and uom and uom.id != wo.mo_id.bom_id.uom_id.id:
                quantity_ot = uom_obj._compute_qty_obj(uom, wo.quantity, wo.mo_id.bom_id.uom_id, with_raise=False)
        
        else:
            #Partie of de répation
            quantity_ot = 'quantity' in no_wo and no_wo['quantity'] or 1
            quantity_bom = quantity_ot
            uom = 'uom' in no_wo and no_wo['uom'] or False
            product = 'product' in no_wo and no_wo['product'] or False
            routing_id = 'routing_id' in no_wo and no_wo['routing_id'] or False
            bom_id = 'bom_id' in no_wo and no_wo['bom_id'] or False
            mo = self.create_mo_light(product, quantity_ot, uom, routing_id, bom_id=bom_id, other_data=other_data_arg)
            wo = False
        
        i = 1
        if routing_line_ids and mo:
            wo_last_rcs = self.search([('mo_id', '=', mo.id)], order='sequence desc', limit=1)
            rl_rcs = routing_line_obj.search([('id', 'in', routing_line_ids)], order='sequence asc')
            # Dictionnaire qui lie l'id de la routing line à l'id du WO
            routing_line_wc_line_ids = {}
            # Gestion des niveaux par rapport à la séquence
            if not arg_rl_sequences:
                rl_sequences = [(r.sequence, r.id) for r in rl_rcs]
            else:
                rl_sequences = arg_rl_sequences
                
            rl_level = {x[-1]: rl_sequences.index(x) for x in rl_sequences}
            sequence_list = []
            sequence_dict = {}
            # Boucler par les lignes de gammes
            for rl in rl_rcs:
                # Boucler sur les catégories de ressources
                resource_list_vals = []
                for rl_resource_categ in rl.rl_resource_category_ids:
                    rl_resource_categ_vals = self.prepare_wo_resource(rl_resource_categ, mo)
                    if rl_resource_categ_vals:
                        resource_list_vals.append([0, 0, rl_resource_categ_vals])
                
                # Boucler sur les services consommés
                consum_serv_list_vals = []
                for consum_serv in rl.consumed_service_ids.read(['quantity', 'product_id', 'uom_id', 'type'], load='_classic_write'):
                    qy_service = consum_serv['quantity']     
                    consum_serv_vals = {
                                'product_id': consum_serv['product_id'],
                                'quantity': qy_service,
                                'uom_id': consum_serv['uom_id'],
                                'type': consum_serv['type']
                            }
                    if consum_serv_vals:
                        consum_serv_list_vals.append([0, 0, consum_serv_vals])
                
                # Boucler sur les outils
                tool_list_vals = []
                for tool in rl.tool_ids.read(['quantity', 'product_id', 'uom_id'], load='_classic_write'):
                    tool_vals = {
                                'product_id': tool['product_id'],
                                'quantity': tool['quantity'] * quantity_ot / quantity_bom,
                                'uom_id': tool['uom_id']
                            }
                    if tool_vals:
                        tool_list_vals.append([0, 0, tool_vals])
                
                # Boucler sur les consignes
                consign_list_vals = []
                for consign in rl.consign_ids.read(['name', 'frequency', 'type', 'desciptive', 'means'], load='_classic_write'):
                    consign_vals = {
                                'name': consign['name'],
                                'frequency': consign['frequency'],
                                'type': consign['type'],
                                'desciptive': consign['desciptive'],
                                'means': consign['means']
                            }
                    consign_list_vals.append([0, 0, consign_vals])

                # Création du WO
                other_data['level'] = rl_level.get(rl.id, 0)
                other_data['mo_level'] = mo.level
                if wo:
                    #Partie ajout d'opération
                    sequence = wo.sequence + i
                    i += 1
                else:
                    #Partie of de répation
                    sequence = rl.sequence
                    for x in arg_rl_sequences:
                        if x[-1] == rl.id:
                            sequence = x[0]
                            break
                
                wo_vals = self.prepare_wo(rl, mo, resource_list_vals=resource_list_vals, consum_serv_list_vals=consum_serv_list_vals, tool_list_vals=tool_list_vals, 
                                          consign_list_vals=consign_list_vals, other_data=other_data, sequence=sequence)
                new_wo = self.create(wo_vals)
                routing_line_wc_line_ids[rl.id] = new_wo.id
                if rl.sequence not in sequence_list:
                    sequence_list.append(rl.sequence)
                
                if rl.sequence not in sequence_dict:
                    sequence_dict[rl.sequence] = self.env['mrp.workorder']

                sequence_dict[rl.sequence] += new_wo
                if (solution1 or solution3) and wo:
                    inter_move_ids = move_obj.search_group(fields=['product_id', 'uom_qty'], 
                                       groupby=['product_id'], 
                                       args=[('wo_outgoing_id', '=', wo.id), ('state', '!=', 'cancel')],
                                       sum='uom_qty',
                                       return_dict=True)
                    
                    for inter_move in inter_move_ids:
                        move_inter = move_obj.search([('product_id', '=', inter_move['product_id']), ('wo_outgoing_id', '=', wo.id)], limit=1)
                        if move_inter.product_id.is_int:
                            move_inter.copy({'uom_qty': inter_move['uom_qty'],
                                             'sec_uom_qty': inter_move['uom_qty'],
                                             'uoi_qty': inter_move['uom_qty'],
                                             'wo_outgoing_id': new_wo.id,
                                             'move_label_ids': []})
                elif wo:
                    inter_move_ids = move_obj.search_group(fields=['product_id', 'uom_qty'], 
                                       groupby=['product_id'], 
                                       args=[('wo_outgoing_id', '=', wo.id), ('state', '!=', 'cancel'), ('product_id', '=', mo.product_id.id)],
                                       sum='uom_qty',
                                       return_dict=True)
                    
                    for inter_move in inter_move_ids:
                        move_inter = move_obj.search([('product_id', '=', inter_move['product_id']), ('wo_outgoing_id', '=', wo.id)], limit=1)
                        move_inter.copy({'uom_qty': inter_move['uom_qty'],
                                         'sec_uom_qty': inter_move['uom_qty'],
                                         'uoi_qty': inter_move['uom_qty'],
                                         'wo_incoming_id': new_wo.id,
                                         'wo_outgoing_id': False,
                                         'location_id': move_inter.location_dest_id.id,
                                         'location_dest_id': move_inter.location_id.id,
                                         'move_label_ids': []})
                        
                        move_inter.copy({'uom_qty': inter_move['uom_qty'],
                                         'sec_uom_qty': inter_move['uom_qty'],
                                         'uoi_qty': inter_move['uom_qty'],
                                         'wo_outgoing_id': new_wo.id,
                                         'move_label_ids': []})
                        break
            
            if sequence_list:
                sequence_list.sort()
                first = True
                wo_ids_prec = []
                last_sequence = sequence_list[-1]
                first_sequence = sequence_list[0]
                for sequence in sequence_list:
                    wo_ids_prec_inter = []
                    for value_sequence in sequence_dict[sequence]:
                        if first and wo:
                            value_sequence.write({'prev_wo_ids': [(4, wo.id)]})
                        else:
                            value_sequence.write({'prev_wo_ids': [(6, 0, wo_ids_prec)]})
                        wo_ids_prec_inter.extend(value_sequence.ids)
                    
                    first = False
                    wo_ids_prec = list(wo_ids_prec_inter)
                    
                if solution1 and wo:
                    wo_last_ids = sequence_dict[last_sequence].ids
                    next_wo_rcs = wo.next_wo_ids - sequence_dict[last_sequence] - sequence_dict[first_sequence]
                    next_wo_rcs.write({'prev_wo_ids': [(6, 0, wo_last_ids)]})
                elif solution3 and wo:
                    next_wo_inter_rcs = wo.next_wo_ids
                    wo_last_ids = sequence_dict[last_sequence].ids
                    wo_last_rcs.write({'prev_wo_ids': [(6, 0, wo_last_ids)]}) 
                    wo_first_ids = sequence_dict[first_sequence].ids + next_wo_inter_rcs.ids
                    wo.write({'next_wo_ids': [(6, 0, wo_first_ids)]})
            
            if wo:
                wo.compute_sorting_level()
            
        return mo
    

    def change_resource(self, wo_resource, resource, rl_resource_category, add_resource_rl=False, is_delay_rm=False, no_modif_prio_date=True, is_procur_level_manufact=True, no_plannif=False):
        """ 
            Préparation des valeurs pour la création d'un enregistrement de l'objet mrp.wo.resource
            :param self: L'order de travail mrp.wo
            :type self: recordset
            :param wo_resource: La ressource du workorder mrp.wo.resource
            :type wo_resource: recordset
            :param resource: La ressource mrp.resource
            :type resource: recordset
            :param rl_resource_category: La categorie de ressource de la ligne de gamme mrp.rl.resource.category
            :type rl_resource_category: recordset
            :param add_resource_rl: Un boolean si l'on veut rajouter la ressource dans la categorie de ressource de la ligne de gamme 
            :type add_resource_rl: boolean
            :return: True
        """
        wo = self
        if wo and wo_resource and resource and rl_resource_category:
            if wo.is_subcontracting and (wo.wo_subc_pol_rm_ids or wo.wo_subc_pol_fp_ids or wo.wo_subc_move_rm_ids or wo.wo_subc_move_fp_ids):
                raise except_orm(_('Error'), _('We can not change the resource because it is already purchases of subcontracting that were created'))
            
            rl_resource_obj = self.env['mrp.rl.resource']
            wo_resource_obj = self.env['mrp.wo.resource']
            rl_resource_rcs = False
            if rl_resource_category:
                rl_resource_rcs = rl_resource_obj.search([('resource_id', '=', resource.id), 
                                                          ('rl_category_id', '=', rl_resource_category.id)], order='sequence asc', limit=1)
            
            timetracking = self.env['resource.timetracking'].search([('wo_id', '=', wo.id), ('resource_id', '=', wo_resource.resource_id.id)], limit=1)
            if timetracking:
                raise except_orm(_('Error'), _('You can not change resource because there is the declared time on this resource'))
            
            # S'il y a une resource de ligne de gamme
            if rl_resource_rcs:
                self.write_resource(rl_resource_rcs, wo.mo_id, rl_resource_category, False, wo_resource)
            # S'il n'y a pas de resource de ligne de gamme
            else:
                self.write_resource(False, wo.mo_id, rl_resource_category, resource, wo_resource)
                # Si ajout de ressource est à vrai on ajoute la ressource dans la categorie de ressource de la ligne de gamme 
                if add_resource_rl:
                    # On récupère la séquence de la dernière resource dans la categorie de ressource de la ligne de gamme
                    last_rl_resource_rcs = rl_resource_obj.search([('rl_category_id', '=', rl_resource_category.id)], order='sequence desc', limit=1)
                    if last_rl_resource_rcs:
                        seq = last_rl_resource_rcs.sequence + 10
                    else:
                        seq = 10
                        
                    # Création de la resource dans la categorie de ressource de la ligne de gamme
                    rl_resource_obj.create({'sequence': seq, 'resource_id': resource.id, 'rl_category_id': rl_resource_category.id})
                    
            # Teste si première ressource du WO pour modifier les emplacements des mouvements
            first_wo_resource_rcs = wo_resource_obj.search([('wo_id', '=', wo.id)], order='sequence asc', limit=1)
            if first_wo_resource_rcs and first_wo_resource_rcs.id == wo_resource.id:
                move_obj = self.env['stock.move']
                modif_location = False
                if wo_resource.resource_id.location_id:
                    if wo.fp_draft_ids:
                        if wo.fp_draft_ids[0].location_dest_id.id != wo_resource.resource_id.location_id.id:
                            modif_location = True
                            
                    elif wo.fp_done_ids:
                        if wo.fp_done_ids[0].location_dest_id.id != wo_resource.resource_id.location_id.id:
                            modif_location = True
                            
                    else:
                        pass
                    
                    # Modification des emplacements dans Matières premières et produit final
                    if modif_location:
                        warehouse_rc = wo.company_id.warehouse_id
                        is_produce_directly_storage = warehouse_rc.is_produce_directly_storage
                        is_consume_directly_storage = warehouse_rc.is_consume_directly_storage
                        # Si les mouvements sont waiting et que l'entrepot n'est pas le même entre les ressources on repasse les mouvements à cancel draft et waiting
                        in_move_rcs = move_obj.search([('wo_incoming_id', '=', wo.id), ('not_usable', '=', False), ('state', 'in', ('draft', 'cancel'))])
                        if in_move_rcs:
                            # Si les emplacements de stockage sont activés pour les MP et que la nouvelle ressource n'est pas une ST
                            if is_consume_directly_storage and wo_resource.resource_id.type != 'subcontracting':
                                for move_rc in in_move_rcs:
                                    move_rc.write({'location_id': move_rc.product_id.get_storage_location(warehouse_rc.id).id or wo_resource.resource_id.location_id.id})
                                    
                            else:
                                in_move_rcs.write({'location_id': wo_resource.resource_id.location_id.id})
                        
                        in_move_waiting_rcs = move_obj.search([('wo_incoming_id', '=', wo.id), ('not_usable', '=', False), ('state', '=', 'waiting')])
                        if in_move_waiting_rcs:
                            # Si les emplacements de stockage sont activés pour les MP et que la nouvelle ressource n'est pas une ST
                            if is_consume_directly_storage and wo_resource.resource_id.type != 'subcontracting':
                                for in_move_waiting_rc in in_move_waiting_rcs:
                                    if in_move_waiting_rc.location_id != (in_move_waiting_rc.product_id.get_storage_location(warehouse_rc.id).id or wo_resource.resource_id.location_id.id):
                                        in_move_waiting_rc.wkf_cancel()
                                        new_move_created, new_in_move_waiting_rc = in_move_waiting_rc.wkf_draft()
                                        if new_move_created:
                                            in_move_waiting_rc = new_in_move_waiting_rc
                                            
                                        new_in_move_waiting_rc.write({'location_id': in_move_waiting_rc.product_id.get_storage_location(warehouse_rc.id).id or wo_resource.resource_id.location_id.id})
                                        new_in_move_waiting_rc.wkf_waiting()
                                    else:
                                        new_in_move_waiting_rc.write({'location_id': in_move_waiting_rc.product_id.get_storage_location(warehouse_rc.id).id or wo_resource.resource_id.location_id.id})
                                    
                            else:
                                if in_move_waiting_rcs[0].location_id != wo_resource.resource_id.location_id:
                                    in_move_waiting_rcs.wkf_cancel()
                                    new_move_created, new_in_move_waiting_rcs = in_move_waiting_rcs.wkf_draft()
                                    if new_move_created:
                                        in_move_waiting_rcs = new_in_move_waiting_rcs
                                        
                                    in_move_waiting_rcs.write({'location_id': wo_resource.resource_id.location_id.id})
                                    in_move_waiting_rcs.wkf_waiting()
                                else:
                                    in_move_waiting_rcs.write({'location_id': wo_resource.resource_id.location_id.id})
                        
                        out_move_rcs = move_obj.search([('wo_outgoing_id', '=', wo.id), ('state', 'in', ('draft', 'cancel'))])
                        if out_move_rcs:
                            # Si les emplacements de stockage sont activés pour les PF et que la nouvelle ressource n'est pas une ST
                            if is_produce_directly_storage and wo_resource.resource_id.type != 'subcontracting':
                                for move_rc in out_move_rcs:
                                    move_rc.write({'location_dest_id': move_rc.product_id.get_storage_location(warehouse_rc.id).id or wo_resource.resource_id.location_id.id})
                            else:
                                out_move_rcs.write({'location_dest_id': wo_resource.resource_id.location_id.id})
                            
                        out_move_waiting_rcs = move_obj.search([('wo_outgoing_id', '=', wo.id), ('state', '=', 'waiting')])
                        if out_move_waiting_rcs:
                            # Si les emplacements de stockage sont activés pour les PF et que la nouvelle ressource n'est pas une ST
                            if is_produce_directly_storage and wo_resource.resource_id.type != 'subcontracting':
                                for out_move_waiting_rc in out_move_waiting_rcs:
                                    if out_move_waiting_rc.warehouse_id != wo_resource.resource_id.location_id:
                                        out_move_waiting_rc.wkf_cancel()
                                        new_move_created, new_out_move_waiting_rc = out_move_waiting_rc.wkf_draft()
                                        if new_move_created:
                                            out_move_waiting_rc = new_out_move_waiting_rc
                                        
                                        out_move_waiting_rc.write({'location_dest_id': out_move_waiting_rc.product_id.get_storage_location(warehouse_rc.id).id or wo_resource.resource_id.location_id.id})
                                        out_move_waiting_rc.wkf_waiting()
                                    else:
                                        out_move_waiting_rc.write({'location_dest_id': wo_resource.resource_id.location_id.id})
                                        
                            else:
                                if out_move_waiting_rcs[0].warehouse_id != wo_resource.resource_id.location_id:
                                    out_move_waiting_rcs.wkf_cancel()
                                    new_move_created, new_out_move_waiting_rcs = out_move_waiting_rcs.wkf_draft()
                                    if new_move_created:
                                        out_move_waiting_rcs = new_out_move_waiting_rcs
                                    
                                    out_move_waiting_rcs.write({'location_dest_id': wo_resource.resource_id.location_id.id})
                                    out_move_waiting_rcs.wkf_waiting()
                                else:
                                    out_move_waiting_rcs.write({'location_dest_id': wo_resource.resource_id.location_id.id})
            
                self.compute_subcontracting_counterpart_move()
                    
            wo.vals_platics_industry()
            # no_plannif est une variable qui permet de ne pas faire une boucle infinie entre le changement de ressource et la plannification
            if wo.state in ('draft', 'waiting', 'plan', 'ready') and not no_plannif:
                if wo.is_at_earlier:
                    planned_start_date = wo.planned_start_date or fields.Datetime.now()
                    wo.action_plannification_wo_at_earlier(planned_start_date, automatic_purchase=False, is_procur_level_manufact=False, 
                                                           is_procur_level_purchase=False, is_delay_rm=is_delay_rm, no_modif_prio_date=no_modif_prio_date)
                else:
                    planned_end_date = wo.planned_end_date or fields.Datetime.now()
                    wo.action_plannification_wo_at_the_latest(planned_end_date, automatic_purchase=False, is_procur_level_manufact=False, 
                                                              is_procur_level_purchase=False, no_modif_prio_date=no_modif_prio_date, change_resources=False)

        else:
            raise except_orm('Error', 'Problem')
        
        return True
    
    
    def return_product_qty_wo_rm_fp(self, wo_new_qty=1.0):
        """ 
            Fonction qui permet d'avoir les matières et les produits finaux d'un OT avec une nouvelle quantitée. Utile si l'on veut produire plus
            Elle retourne un dictionnaire contenant comme clé l'id du produit et comme valeurs une quantité et l'uom
            :param self: L'order de travail mrp.wo
            :type self: recordset
        """
        move_obj = self.env['stock.move']
        parameter_obj = self.env['stock.move.parameter']
        bom_obj = self.env['mrp.bom']
        wo = self
        prod_digits = 2
        factor = wo_new_qty / wo.quantity
        dict_product_rm = {}
        dict_product_fp = {}
        for move in move_obj.search([('wo_incoming_id', '=', wo.id), ('not_usable', '=', False)]).read(['type_qty', 'efficient_unit_qty', 'uom_qty', 'product_id', 'procurement_id', 'parameter_ids', 'uom_id'], load='_classic_write'):
            if move['product_id'] not in dict_product_rm:
                if move['type_qty'] == 'formula' and move['parameter_ids']:
                    parameter_rcs = parameter_obj.browse(move['parameter_ids'][0])
                    move_qty_uom_total, efficient_new_uom_qty = bom_obj.compute_qty_component(parameter_rcs.qty_component, parameter_rcs.round_component, parameter_rcs.eff_component, 
                                                                                              parameter_rcs.qty_bom, wo_new_qty, parameter_rcs.type_component, 
                                                                                              formula= parameter_rcs.formula_component, args_parameters_list=[('mo_id', '=', wo.mo_id.id)])
                    move_qty_uom = round(move_qty_uom_total, prod_digits)
                    dict_product_rm[move['product_id']] = {'qty': move_qty_uom,
                                                           'uom_id': move['uom_id'],
                                                           'move_id': move['id']}
                elif move['type_qty'] == 'variable':
                    if move['efficient_unit_qty'] and move['uom_qty']:
                        move_qty_uom_total = move['efficient_unit_qty'] * factor * wo.quantity
                        move_qty_uom = round(move_qty_uom_total, prod_digits)
                    else:
                        rm_product_ids = move_obj.search([('wo_incoming_id', '=', wo.id), 
                                                          ('product_id', '=', move['product_id']), 
                                                          ('procurement_id', '=', move['procurement_id'], 
                                                           ('not_usable', '=', False))])
                        
                        move_qty_uom = 0
                        for rm_product in rm_product_ids.read(['uom_qty']):
                            move_qty_uom += rm_product['uom_qty']
                    
                    dict_product_rm[move['product_id']] = {'qty': move_qty_uom,
                                                           'uom_id': move['uom_id'],
                                                           'move_id': move['id']}
                else:
                    rm_product_ids = move_obj.search([('wo_incoming_id', '=', wo.id), 
                                                      ('product_id', '=', move['product_id']), 
                                                      ('procurement_id', '=', move['procurement_id']), 
                                                      ('not_usable', '=', False)])
                    move_qty_uom = 0
                    for rm_product in rm_product_ids.read(['uom_qty']):
                        move_qty_uom += rm_product['uom_qty']
                    
                    dict_product_rm[move['product_id']] = {'qty': move_qty_uom,
                                                           'uom_id': move['uom_id'],
                                                           'move_id': move['id']}
                 
        for move in move_obj.search([('wo_outgoing_id', '=', wo.id)]).read(['type_qty', 'efficient_unit_qty', 'uom_qty', 'product_id', 'procurement_id', 'parameter_ids', 'uom_id'], load='_classic_write'):
            if move['product_id'] not in dict_product_fp:
                if move['type_qty'] == 'formula' and move['parameter_ids']:
                    parameter_rcs = parameter_obj.browse(move['parameter_ids'][0])
                    move_qty_uom_total, efficient_new_uom_qty = bom_obj.compute_qty_component(parameter_rcs.qty_component, parameter_rcs.round_component, parameter_rcs.eff_component, 
                                                                                              parameter_rcs.qty_bom, wo_new_qty, parameter_rcs.type_component, 
                                                                                              formula= parameter_rcs.formula_component, args_parameters_list=[('mo_id', '=', wo.mo_id.id)])
                    move_qty_uom = round(move_qty_uom_total, prod_digits)
                    dict_product_fp[move['product_id']] = {'qty': move_qty_uom,
                                                           'uom_id': move['uom_id'],
                                                           'move_id': move['id']}
                    
                elif move['type_qty'] == 'variable':
                    if move['efficient_unit_qty'] and move['uom_qty']:
                        move_qty_uom_total = move['efficient_unit_qty'] * factor * wo.quantity
                        move_qty_uom = round(move_qty_uom_total, prod_digits)
                    else:
                        fp_product_ids = move_obj.search([('wo_outgoing_id', '=', wo.id), 
                                                          ('product_id', '=', move['product_id']), 
                                                          ('procurement_id', '=', move['procurement_id'])])
                        
                        move_qty_uom = 0
                        for fp_product in fp_product_ids.read(['uom_qty']):
                            move_qty_uom += fp_product['uom_qty']
                    
                    dict_product_fp[move['product_id']] = {'qty': move_qty_uom,
                                                           'uom_id': move['uom_id'],
                                                           'move_id': move['id']}
                else:
                    fp_product_ids = move_obj.search([('wo_outgoing_id', '=', wo.id), 
                                                      ('product_id', '=', move['product_id']), 
                                                      ('procurement_id', '=', move['procurement_id'])])
                    move_qty_uom = 0
                    for fp_product in fp_product_ids.read(['uom_qty']):
                        move_qty_uom += fp_product['uom_qty']
                    
                    dict_product_fp[move['product_id']] = {'qty': move_qty_uom,
                                                           'uom_id': move['uom_id'],
                                                           'move_id': move['id']}
        
        return dict_product_rm, dict_product_fp
    
    
    
    def write_resource(self, rl_resource_rcs, mo, rl_resource_categ_rcs, resource_rcs, wo_resource_rcs):
        vals = self.prepare_wo_resource(rl_resource_categ_rcs, mo, rl_resource_rcs=rl_resource_rcs, 
                                        resource_rcs=resource_rcs, other_data=None)
        if vals:
            wo_resource_rcs.write(vals)
            
        return vals
    
    
    def do_label_consumption(self, label_rcs, wo_qty_decla=1):
        """
            Fonction qui permet de consommer un seul produit dans un OT à partir d'étiquettes
        """
        if label_rcs:
            move_obj = self.env['stock.move']
            uom_obj = self.env['product.uom']
            move_label_obj = self.env['stock.move.label']
            label = label_rcs[0]
            product = label.product_id
            if product:
                # Recherche d'un mouvement à consommer du produit dans l'OT, s'il n'y en a pas il sera créé
                move_rcs = move_obj.search([('wo_incoming_id', '=', self.id), 
                                            ('state', 'not in', ('cancel', 'done')), 
                                            ('product_id', '=', product.id)], limit=1)
                create_new_move = True
                if move_rcs:
                    # On regarde si le mouvement n'a pas déjà des étiquettes affectées si c'est le cas on split le mouvement pour n'utiliser qu'un mouvement sans étiquette, par
                    # contre si la somme des étiquettes est équivalente à la quantité du mouvement alors on crée un nouveau mouvement
                    if move_rcs.move_label_ids:
                        total_qty_inter = 0.0
                        total_sec_qty_inter = 0.0
                        total_uoi_qty_inter = 0.0
                        sec_qty_factor = move_rcs.sec_uom_qty / (move_rcs.uom_qty or 1.0)
                        uoi_qty_factor = move_rcs.uoi_qty / (move_rcs.uom_qty or 1.0)
                        for move_label in move_rcs.move_label_ids:
                            if (move_label.uom_id or move_label.label_id.uom_id) != move_rcs.uom_id:
                                label_uom_id = move_label.uom_id or move_label.label_id.uom_id
                                qty = uom_obj._compute_qty_obj(label_uom_id, move_label.uom_qty, move_rcs.uom_id)
                            else:
                                qty = label.uom_qty
                            
                            total_qty_inter += qty
                            total_sec_qty_inter += qty * sec_qty_factor
                            total_uoi_qty_inter += qty * uoi_qty_factor
                        
                        if total_qty_inter >= move_rcs.uom_qty:
                            create_new_move = True
                        else:
                            create_new_move = False
                            move_draft = False
                            if move_rcs.state == 'draft':
                                move_draft = True
                                
                            move_dic = move_rcs.split_light(move_rcs.uom_qty/total_qty_inter)
                            move_rcs = move_dic['new_move_rcs']
                            if not move_draft:
                                move_rcs.wkf_waiting()
                            
                    else:
                        create_new_move = False  
                
                # Création du nouveau mouvement
                if create_new_move:
                    location_obj = self.env['stock.location']
                    location_dest_rcs = location_obj.search([('usage', '=', 'production')], limit=1)
                    location_id = self.first_resource_id and self.first_resource_id.location_id and self.first_resource_id.location_id.id or False
                    if not location_id:
                        location_id = location_obj.search([('usage', '=', 'intern')], limit=1).id
                        
                    move_rcs = move_obj.create_move(product, location_id, location_dest_rcs.id, 
                                                    qty=1, uom=product.uom_id, other_data={'wo_incoming_id': self.id, 
                                                                                           'efficient_unit_qty':1, 
                                                                                           'is_forecast': self.is_forecast,}, in_product_uom=True)
                
                move_draft = False
                if move_rcs.state == 'draft':
                    move_rcs.wkf_waiting()
                    move_draft = True
                
                # facteur de conversion des quantités
                sec_qty_factor = move_rcs.sec_uom_qty / (move_rcs.uom_qty or 1.0)
                uoi_qty_factor = move_rcs.uoi_qty / (move_rcs.uom_qty or 1.0)
                
                # On regarde si l'on doit convertir les quantité
                if move_rcs.uom_id and move_rcs.product_id and move_rcs.product_id.uom_id \
                   and move_rcs.uom_id.id != move_rcs.product_id.uom_id.id \
                   and move_rcs.uom_id.category_id.id == move_rcs.product_id.uom_id.category_id.id:
                    need_convert = True
                else: 
                    need_convert = False
                
                # On calcule la somme des étiquettes
                total_qty = 0.0
                total_sec_qty = 0.0
                total_uoi_qty = 0.0
                for label in label_rcs:
                    if need_convert:
                        qty = uom_obj._compute_qty_obj(label.uom_id, label.uom_qty, move_rcs.uom_id)
                    else:
                        qty = label.uom_qty
                    
                    total_qty += qty
                    total_sec_qty += qty * sec_qty_factor
                    total_uoi_qty += qty * uoi_qty_factor
                
                # On compare la quantité des étiquette et celle du mouvement
                # Si elle est supérieur ou égale on écrit la quantité dans le mouvement
                if move_rcs.uom_qty <= total_qty:
                    move_rcs.write({'uom_qty': total_qty,
                                    'sec_uom_qty': total_sec_qty,
                                    'uoi_qty': total_uoi_qty})
                # Si non split le mouvement afin que l'on ne consomme pas moins que ce qui est prévue
                else:
                    move_dic = move_rcs.split_light(move_rcs.uom_qty/total_qty)
                    move_rcs = move_dic['move_rcs']
                    if not move_draft:
                        move_dic['new_move_rcs'].wkf_waiting()
                
                # Génération des move_label entre les étiquettes et le mouvement
                move_same_label_ids = move_label_obj.search([('move_id.state', 'not in', ['done', 'cancel']), 
                                                             ('move_id.picking_id', '!=', False), 
                                                             ('label_id', 'in', label_rcs.ids)], limit=1)
                if move_same_label_ids:
                    raise except_orm(_('Error'), _('UC label %s is already assign.')%(move_same_label_ids[0].label_id.name))
                        
                move_label_obj.create_move_label(label_rcs, move_rs=move_rcs)
                # Déclaration de la consommation
                vals = {
                    'wo_id': self.id,
                    'user_id': self.env.user.id,
                    'uom_id': self.uom_id.id,
                    'product_id': self.final_product_id.id,
                    'quantity': wo_qty_decla,
                    'type': 'consumption',
                    'date': fields.Datetime.now(),
                }
                wdm_rcs = self.env['wo.declaration.main'].create(vals)
                wdc_rcs = wdm_rcs.create_declaration_consumption_move(move_rcs)
                wdc_rcs.action_validate_comsuption(no_return_view=True)
                    
                    
                
        return True
    
    
    @api.model
    def create(self, vals):
        """
            A la création de l'OT, on récupère les documents de la ligne de gamme
            Si on a un OF lié on récupère le client, la date demandée et la ligne de vente de l'OF
            Sinon, s'il y a une ligne de vente, on rempli le client et la
            date demandée à partir de cette ligne de vente 
        """
        if vals:
            if vals.get('mo_id'):
                mo = self.env['mrp.manufacturingorder'].browse(vals['mo_id'])
                if mo:
                    vals['sale_line_id'] = mo.sale_line_id and mo.sale_line_id.id or False
                    vals['customer_id'] = mo.customer_id and mo.customer_id.id or False
                    vals['requested_date'] = mo.requested_date
                    
            elif vals.get('sale_line_id'):
                sale_line_rs = self.env['sale.order.line'].browse(vals['sale_line_id'])
                if sale_line_rs:
                    partner_rs = sale_line_rs.sale_order_id and sale_line_rs.sale_order_id.partner_id or False
                    vals['customer_id'] = partner_rs and partner_rs.id or False
                    vals['requested_date'] = sale_line_rs and (sale_line_rs.departure_date or sale_line_rs.requested_date) or False
            
        documents = []
        wo = super(mrp_workorder, self).create(vals)
        if wo.routing_line_id and wo.routing_line_id.document_ids:
            documents = [(4, document_line.id) for document_line in wo.routing_line_id.document_ids]
            
        wo.write({'rl_document_ids': documents})
        return wo
    
    
    @api.multi
    def write(self, vals=None):
        """
        """
        res = super(mrp_workorder, self).write(vals=vals)
        if 'modif_time_int' in vals:
            if self.is_at_earlier:
                planned_start_date = self.planned_start_date or fields.Datetime.now()
                self.action_plannification_wo_at_earlier(planned_start_date, automatic_purchase=False, is_procur_level_manufact=False, 
                                                       is_procur_level_purchase=False, change_resources=False)
            else:
                planned_end_date = self.planned_end_date or fields.Datetime.now()
                self.action_plannification_wo_at_the_latest(planned_end_date, automatic_purchase=False, is_procur_level_manufact=False, 
                                                          is_procur_level_purchase=False, change_resources=False)
        
        return res
    
    
    
class mrp_wo_produce(models.Model):
    """ 
        Workorder Produce
    """
    _name = 'mrp.wo.produce'
    _description = 'Workorder produce'    
    _rec_name = 'wo_id'
    
    @api.model
    def _state_get(self):
        return [
                ('done', _('Done')),
                ('cancel', _('Cancel')),
                       ]
    
    
    @api.one
    @api.depends('wo_id')
    def _compute_wo(self):
        self.st_wo = self.wo_id.is_subcontracting
    
    
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
    
    
    @api.one
    @api.depends('date')
    def _compute_date(self):
        """
            Fonction qui calcule la semaine, le mois et l'année de la date
        """
        if self.date:
            date = '%s'%(self.date[0:10])
            date = datetime.datetime.strptime(date, '%Y-%m-%d')
            isocal = date.isocalendar()
            # Sur 2 caractères
            if len(str(isocal[1])) == 1:
                self.week_number = '0%s'%(str(isocal[1]))
            else:
                self.week_number = str(isocal[1])
            
            # Sur 2 caractères
            if len(str(date.month)) == 1:
                self.month = '0%s'%(str(date.month))
            else:
                self.month = str(date.month)
                
            self.year = str(isocal[0])
        else:
            self.week_number = '00'
            self.month = '00'
            self.year = '0'
        
        
    @api.one
    @api.depends('wo_id')
    def _compute_wo_id(self):
        is_final = False
        last_wo_rcs = self.env['mrp.workorder'].search([('mo_id', '=', self.wo_id.mo_id.id)], order='sequence desc', limit=1)
        if self.wo_id == last_wo_rcs:
            is_final = True
        
        self.is_final = is_final
    
    
    @api.one
    def _compute_search_date(self):
        """
            Fonction qui calcule les champs utilisés dans la recherche
        """
        self.is_week = False
        self.is_month = False  
        self.is_yesturday = False 
        self.is_today = False 
        
    
    def _search_is_week(self, operator, value):
        """
            Fonction search qui permet de retrouver tous les OFs qui sont de cette semaine
        """
        request = """
        SELECT 
            x.id 
        FROM
            (SELECT     
                to_char(min(date), 'WW') as week_date,
                to_char(min(date), 'YYYY') as year_date,
                to_char((current_date), 'WW') as week_now,
                to_char((current_date), 'YYYY') as year_now,
                id
             FROM 
                 mrp_wo_produce 
             WHERE
                 is_final = true and
                 state = 'done' and
                 date is not null
             group by id)  x
        
        where 
            x.week_now = x.week_date and
            x.year_now = x.year_date"""
        self.env.cr.execute(request)
        res_ids = self.env.cr.fetchall()          
        return [('id', 'in', res_ids)]
    
    
    def _search_is_yesturday(self, operator, value):
        """
            Fonction search qui permet de retrouver tous les OFs qui sont d'hier
        """
        request = """
        select 
            id
        from
            mrp_wo_produce
        where
            is_final = true and
            state = 'done' and
            date =(current_date - interval '1 days')::date"""
        self.env.cr.execute(request)
        res_ids = self.env.cr.fetchall()          
        return [('id', 'in', res_ids)]
    
    
    def _search_is_today(self, operator, value):
        """
            Fonction search qui permet de retrouver tous les OFs qui sont d'aujourdhui
        """
        request = """
        select 
            id
        from
            mrp_wo_produce
        where
            is_final = true and
            state = 'done' and
            date =(current_date)::date"""
        self.env.cr.execute(request)
        res_ids = self.env.cr.fetchall()          
        return [('id', 'in', res_ids)]
    
    
    def _search_is_month(self, operator, value):
        """
            Fonction search qui permet de retrouver tous les OFs qui sont dans le mois
        """
        request = """
        SELECT 
            x.id 
        FROM
            (SELECT     
                to_char(min(date), 'MM') as week_date,
                to_char(min(date), 'YYYY') as year_date,
                to_char((current_date), 'MM') as week_now,
                to_char((current_date), 'YYYY') as year_now,
                id
             FROM 
                 mrp_wo_produce 
             WHERE
                 is_final = true and
                 state = 'done' and
                 date is not null
             group by id)  x
        
        where 
            x.week_now = x.week_date and
            x.year_now = x.year_date"""
        self.env.cr.execute(request)
        res_ids = self.env.cr.fetchall()          
        return [('id', 'in', res_ids)]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wo_id = fields.Many2one('mrp.workorder', string='Workorder', required=False, ondelete='cascade', select=True)
    product_id = fields.Many2one('product.product', string='Product', ondelete='restrict')
    is_final = fields.Boolean(string='Is final', compute='_compute_wo_id', store=True)
    date = fields.Datetime(string='Date')
    qty_ok = fields.Float(string='Qty Ok', default=0.0, required=False, digits=dp.get_precision('Product quantity'))
    qty_hs = fields.Float(string='Qty Hs', default=0.0, required=False, digits=dp.get_precision('Product quantity'))
    qty_quarantine = fields.Float(string='Qty Quarantine', default=0.0, required=False, digits=dp.get_precision('Product quantity'))
    user_id = fields.Many2one('res.users', string='Users', default=lambda self: self.env.user.id, required=False, ondelete='restrict')
    state = fields.Selection('_state_get', default='done', string='State')
    note = fields.Text(string='Note')
    uom_id = fields.Many2one('product.uom', string='UoM', required=False, ondelete='restrict')
    move_ids = fields.One2many('stock.move', 'wo_produce_id',  string='Moves')
    user_cancel_id = fields.Many2one('res.users', string='Users Cancel', default=False, required=False, ondelete='restrict')
    date_cancel = fields.Datetime(string='Date Cancel')
    st_move_id = fields.Many2one('stock.move', string='ST move', required=False, ondelete='restrict')
    st_pol_id = fields.Many2one('purchase.order.line', string='ST POL', required=False, ondelete='restrict')
    st_wo = fields.Boolean(string='st wo', compute='_compute_wo')
    month = fields.Selection('_month_get', string='Month', compute='_compute_date', store=True)
    week_number = fields.Char(string='Week number', size=2, compute='_compute_date', store=True) 
    year = fields.Char(string='Year', size=4, compute='_compute_date', store=True)
    first_resource_id = fields.Many2one('mrp.resource', string='First resource')
    #Search
    is_week = fields.Boolean(string='Is week', compute='_compute_search_date', search='_search_is_week')
    is_yesturday = fields.Boolean(string='Is yesturday', compute='_compute_search_date', search='_search_is_yesturday')
    is_month = fields.Boolean(string='Is month', compute='_compute_search_date', search='_search_is_month')
    is_today = fields.Boolean(string='Is today', compute='_compute_search_date', search='_search_is_today')


    #===========================================================================
    # bouton
    #===========================================================================
    @api.multi
    def wkf_cancel(self):
        for wiz in self:
            if wiz.state != 'cancel':
                for move in wiz.move_ids:
                    if move.post_control_declaration_id:
                        move.post_control_declaration_id.wkf_cancel()
                        
                    if move.product_id == wiz.wo_id.final_product_id:
                        move.write({'partner_price': 0.0, 'currency_id': False})
                
                wiz.wo_id.aggregate_move(wiz.move_ids, type='fp', waiting_state=True)
                wiz.write({
                    'date_cancel': fields.Datetime.now(), 
                    'user_cancel_id': self.env.user.id, 
                    'state': 'cancel'
                })
                wiz.move_ids.write({'wo_produce_id': False})
            
        return True
        
        
    #===========================================================================
    # Fonction
    #===========================================================================
    def get_corresponding_consumption(self):
        i = 0
        for wo_produce_rc in self.search([('wo_id', '=', self.wo_id.id), ('state', '=', 'done')], order='date asc'):
            if wo_produce_rc.id == self.id:
                index = i
                break
            
            i += 1
        
        return self.env['mrp.wo.consumption'].search([('wo_id', '=', self.wo_id.id), ('state', '=', 'done')], order='date asc', offset=index, limit=1)
        

    @api.model
    def create(self, vals=None):
        """
            Changement du state du WO par rapport à la déclaration de production
        """
        res = super(mrp_wo_produce, self).create(vals=vals)
        if res.wo_id and res.wo_id._function_compute_advancement(with_state=False) >= 100 and res.wo_id.state != 'done' and (res.move_ids or res.st_move_id):
            res.wo_id.wkf_done()
        
        return res
    
    
    
class mrp_wo_consumption(models.Model):
    """ 
        Workorder Consumption
    """
    _name = 'mrp.wo.consumption'
    _description = 'Workorder Consumption'    
    _rec_name = 'wo_id'
    
    @api.model
    def _state_get(self):
        return [
                ('done', _('Done')),
                ('cancel', _('Cancel')),
                       ]
    
    
    @api.one
    @api.depends('wo_id')
    def _compute_wo(self):
        self.st_wo = self.wo_id.is_subcontracting
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wo_id = fields.Many2one('mrp.workorder', string='Workorder', required=False, ondelete='cascade')
    date = fields.Datetime(string='Date')
    quantity = fields.Float(string='Qty', default=0.0, required=False, digits=dp.get_precision('Product quantity'))
    user_id = fields.Many2one('res.users', string='Users', default=lambda self: self.env.user.id, required=False, ondelete='restrict')
    state = fields.Selection('_state_get', default='done', string='State')
    note = fields.Text(string='Note')
    uom_id = fields.Many2one('product.uom', string='UoM', required=False, ondelete='restrict')
    move_ids = fields.One2many('stock.move', 'wo_consumption_id',  string='Moves')
    user_cancel_id = fields.Many2one('res.users', string='Users Cancel', default=False, required=False, ondelete='restrict')
    date_cancel = fields.Datetime(string='Date Cancel')
    st_move_id = fields.Many2one('stock.move', string='ST move', required=False, ondelete='restrict')
    st_pol_id = fields.Many2one('purchase.order.line', string='ST POL', required=False, ondelete='restrict')
    st_wo = fields.Boolean(string='st wo', compute='_compute_wo')
    first_resource_id = fields.Many2one('mrp.resource', string='First resource')
    
    #===========================================================================
    # bouton
    #===========================================================================
    @api.multi
    def wkf_cancel(self):
        for wiz in self:
            if wiz.state != 'cancel':
                wiz.wo_id.aggregate_move(wiz.move_ids, type='rm', waiting_state=True)
                wiz.write({'date_cancel': fields.Datetime.now(), 'user_cancel_id': self.env.user.id, 'state': 'cancel'})
                if wiz.wo_id.state == 'done':
                    wiz.wo_id.button_reopen()
            
        return True
    
    
    
class mrp_wo_tools(models.Model):
    """ 
        Work order Tools 
    """
    _name = 'mrp.wo.tools'
    _description = 'Tools'
    _rec_name = 'product_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wo_id = fields.Many2one('mrp.workorder', string='Workorder', required=False, ondelete='Cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='restrict')
    stock_label_id = fields.Many2one('stock.label', string='Label', ondelete='restrict')
    quantity = fields.Float(string='Quantity', digits=dp.get_precision('Product quantity'), default=1.0, required=True)
    uom_id = fields.Many2one('product.uom', string='UOM', required=True, ondelete='restrict')
    uom_category_id = fields.Many2one('product.uom.category', related='product_id.uom_id.category_id', string="UOM category", 
                                      readonly=True)

    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
            Au changement du produit, changement de la catégorie de l'uom
        """
        self.uom_id = self.product_id and self.product_id.uom_id or False
        self.uom_category_id = self.product_id and self.product_id.uom_id and self.product_id.uom_id.category_id or False

    

class mrp_wo_consign(models.Model):
    """ 
    Consign
    """
    _name = 'mrp.wo.consign'
    _description = 'Consign'
    
    @api.model
    def _type_get(self):
        return [
                ('consign', _('Consign')),
                ('control', _('Control')),
                       ]
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wo_id = fields.Many2one('mrp.workorder', string='Workorder', required=False, ondelete='Cascade')
    name = fields.Char(required=True, string=u"N°")
    frequency = fields.Char(string='Frequency', size=256, required=False)
    type = fields.Selection('_type_get', string='Type', default='consign')
    desciptive = fields.Char(string='Desciptive', size=256, required=True)
    means = fields.Char(string='Means', size=32, required=False)


    
class mrp_wo_resource(models.Model):
    """ 
        Workorder Resource
    """
    _name = 'mrp.wo.resource'
    _description = 'Workorder Resource'
    _rec_name = 'wo_id'
    
    
    @api.one
    @api.depends('preparation_time', 'preparation_masked_time', 'production_time', 'production_masked_time', 'wo_id', 'wo_id.quantity', 'nb_resource', 'cleaning_time', 
                 'cleaning_masked_time', 'nb_product_parallel', 'wo_id.is_supplier_delay_subc', 'wo_id.is_subcontracting')
    def _compute_time(self):
        """
            Fonction qui calcule les temps
        """
        nb_product_parallel = self.nb_product_parallel or 1.0
        production_time = self.production_time / nb_product_parallel
        total_production_time = production_time * (1 - (self.production_masked_time/100)) * self.wo_id.quantity / (self.nb_resource or 1.0)
        if self.wo_id.is_supplier_delay_subc and self.wo_id.is_subcontracting:
            self.total_preparation_time = 0.0
            self.total_production_time = 0.0
            self.total_cleaning_time = 0.0
            self.total_time_theo = 0.0
            self.total_time_theo_with_masked = 0.0
        else:
            self.total_preparation_time = self.preparation_time * (1 - (self.preparation_masked_time/100))
            self.total_production_time = total_production_time
            self.total_cleaning_time = self.cleaning_time * (1 - (self.cleaning_masked_time/100))
            self.total_time_theo = self.total_preparation_time + self.total_production_time + self.total_cleaning_time
            self.total_time_theo_with_masked = self.preparation_time + (production_time * self.wo_id.quantity / (self.nb_resource or 1.0)) + self.cleaning_time
    
    
    def _get_compute_time(self, qty_wo=0):
        """
            Fonction qui calcule les temps d'un wo_resource
        """
        nb_product_parallel = self.nb_product_parallel or 1.0
        production_time = self.production_time / nb_product_parallel
        total_production_time = production_time * (1 - (self.production_masked_time/100)) * qty_wo / (self.nb_resource or 1.0)
        if self.wo_id.is_supplier_delay_subc and self.wo_id.is_subcontracting:
            res = {
                    'total_preparation_time': 0.0,
                    'total_production_time': 0.0,
                    'total_cleaning_time': 0.0,
                    'total_time_theo': 0.0,
                    'total_time_theo_with_masked': 0.0}
        else:
            res = {
                    'total_preparation_time': self.preparation_time * (1 - (self.preparation_masked_time/100)),
                    'total_production_time': total_production_time,
                    'total_cleaning_time': self.cleaning_time * (1 - (self.cleaning_masked_time/100)),
                    'total_time_theo': self.total_preparation_time + self.total_production_time + self.total_cleaning_time,
                    'total_time_theo_with_masked': self.preparation_time + (production_time * qty_wo / (self.nb_resource or 1.0)) + self.cleaning_time}
        
        return res
    
    
    @api.one
    @api.depends('total_time_theo', 'total_time_theo')
    def _compute_difference(self):
        """
            Fonction qui calcule la différence de temps
        """
        self.difference = self.total_time_theo and (self.total_time_real - self.total_time_theo)*100/(self.total_time_theo)
    
    
    @api.one
    @api.depends('wo_id', 'wo_id.resource_timetracking_ids', 'wo_id.resource_timetracking_ids.wo_id',
                'wo_id.resource_timetracking_ids.resource_id', 'wo_id.resource_timetracking_ids.activity', 'sequence',
                'wo_id.resource_timetracking_ids.end_date', 'wo_id.resource_timetracking_ids.time', 'resource_id', 'resource_id.type')
    def _compute_total_time_real(self):
        """
            Fonction qui calcule le temps réel
        """
        time = 0
        timetracking_rcs = self.env['resource.timetracking'].search([('wo_id', '=', self.wo_id.id), 
                                                                     ('resource_id', '=', self.resource_id.id), 
                                                                     ('activity', '!=', 'waiting')])
        for timetracking in timetracking_rcs:
            time += timetracking.time
        
        
        if self.resource_id and self.wo_id and isinstance(self.wo_id.id, int):
            self.env.cr.execute("""
                                    select 
                                        mrp_wo_resource.id
                                    
                                    From 
                                        mrp_wo_resource,
                                        mrp_resource
                                    Where
                                        mrp_resource.id = mrp_wo_resource.resource_id AND
                                        mrp_resource.type = %s AND
                                        mrp_wo_resource.wo_id = %s
                                    
                                    Order by mrp_wo_resource.sequence asc
                                    Limit 1""", (self.resource_id.type, self.wo_id.id))
            
            res_ids = self.env.cr.fetchall() 
            if res_ids and res_ids[0] and res_ids[0][0] == self.id:
                resource_rcs = self.env['mrp.resource']
                for wo_resource in self.wo_id.wo_resource_ids:
                    resource_rcs |= wo_resource.resource_id
                    
                self.env.cr.execute("""
                                        select 
                                            sum(resource_timetracking.time)
                                        From 
                                            mrp_resource,
                                            resource_timetracking
                                        Where
                                            mrp_resource.type = %s AND
                                            resource_timetracking.wo_id = %s AND
                                            resource_timetracking.resource_id = mrp_resource.id AND
                                            resource_timetracking.activity != 'waiting' AND
                                            mrp_resource.id not in %s""", (self.resource_id.type, self.wo_id.id, tuple(resource_rcs.ids)))
                
                times = self.env.cr.fetchall() 
                if times and times[0] and times[0][0]:
                    time += times[0][0]

        self.total_time_real = time
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wo_id = fields.Many2one('mrp.workorder', string='Workorder', required=False, ondelete='cascade', select=True)
    resource_category_id = fields.Many2one('mrp.resource.category', string='Category', required=True, ondelete='restrict')
    sequence = fields.Integer(string='Sequence', default=0, required=True)
    resource_id = fields.Many2one('mrp.resource', string='Resource', required=True, ondelete='restrict')
    rl_resource_category_id = fields.Many2one('mrp.rl.resource.category', string='RL Resource Category', required=False, ondelete='set null')
    nb_resource = fields.Float(string='Nb resource', default=1.0, digits=dp.get_precision('Product quantity'))
    preparation_time = fields.Float(string='Preparation time unit', default=0.0, digits=dp.get_precision('Time'), required=False)
    production_time = fields.Float(string='Production time unit', default=0.0, digits=dp.get_precision('Time'), required=False)
    cleaning_time = fields.Float(string='Cleaning time unit', default=0.0, digits=dp.get_precision('Time'), required=False)
    preparation_masked_time = fields.Float(string='% Preparation masked time', default=0.0, digits=dp.get_precision('Product quantity'), required=False)
    production_masked_time = fields.Float(string='% Production masked time', default=0.0, digits=dp.get_precision('Product quantity'), required=False)
    cleaning_masked_time = fields.Float(string='% Cleaning masked time', default=0.0, digits=dp.get_precision('Product quantity'), required=False)
    total_time_real = fields.Float(string='Total Time Real', digits=dp.get_precision('Time'), compute='_compute_total_time_real', store=True)
    total_time_theo = fields.Float(string='Total Time Theo', digits=dp.get_precision('Time'), compute='_compute_time', store=True)
    total_time_theo_with_masked = fields.Float(string='Total Time Theo With Masked', digits=dp.get_precision('Time'), compute='_compute_time', store=True)
    difference = fields.Float(string='Difference %', digits=dp.get_precision('Product quantity'), compute='_compute_difference')
    total_preparation_time = fields.Float(string='Total Preparation Time', digits=dp.get_precision('Time'), compute='_compute_time', store=True)
    total_production_time = fields.Float(string='Total Production Time', digits=dp.get_precision('Time'), compute='_compute_time', store=True)
    total_cleaning_time = fields.Float(string='Total Cleaning Time', digits=dp.get_precision('Time'), compute='_compute_time', store=True)
    nb_product_parallel = fields.Float(string='Number of products in parallel', default=1.0, required=False, digits=dp.get_precision('Product quantity'))


class mrp_wo_additional_resource(models.Model):
    _name = 'mrp.wo.additional.resource'
    
    wo_id = fields.Many2one('mrp.workorder', string='Workorder', required=True, ondelete='cascade')
    resource_id = fields.Many2one('mrp.resource', string='Resource', required=True, ondelete='cascade')
    start_date = fields.Datetime(string='Start date', default=fields.Datetime.now)
    end_date = fields.Datetime(string='End date')
    
    @api.model
    def create(self, vals):
        wo_id = self.env['mrp.workorder'].browse(vals['wo_id'])
        if vals['resource_id'] in (x.resource_id.id
                                   for x in wo_id.additional_resource_ids
                                   if not x.end_date):
            raise ValidationError(_('A resource cannot be started multiple times'))
        return super(mrp_wo_additional_resource, self).create(vals)


class mrp_wo_consumed_service(models.Model):
    """ 
    Consumed service 
    """
    _name = 'mrp.wo.consumed.service'
    _description = 'Consumed service'
    _rec_name = 'product_id'
    
    @api.model
    def _type_get(self):
        return [
                ('fixed', _('Fixed')),
                ('variable', _('Variable')),
                       ]

    @api.one
    @api.depends('quantity', 'quantity', 'product_id')
    def _compute_price_total(self):
        price = 0.0
        bon_obj = self.env['mrp.bom']
        currency_price_return = self.wo_id and self.wo_id.company_id and self.wo_id.company_id.currency_id or False
        if self.product_id:
            qty_calcul = self.quantity
            price_unit_product = bon_obj.compute_price_component_buy(self.product_id, qty_calcul, self.uom_id, currency_price_return)
            price = price_unit_product * self.quantity
            
        self.price_total = price
       
    
    #===========================================================================
    # COLUMNS
    #=========================================================================== 
    wo_id = fields.Many2one('mrp.workorder', string='Workorder', required=False, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='restrict')
    quantity = fields.Float(string='Quantity', digits=dp.get_precision('Product quantity'), default=1.0, required=True)
    uom_id = fields.Many2one('product.uom', string='UOM', required=True, ondelete='restrict')
    uom_category_id = fields.Many2one('product.uom.category', related='product_id.uom_id.category_id', string="UOM category", 
                                      readonly=True)
    type = fields.Selection('_type_get', string='Type', required=True, default='variable')
    price_total = fields.Float(string='Price total', compute='_compute_price_total', digits=dp.get_precision('Price technical'))
    # Champ utilisé pour la soustraitance, lors de la création des réceptions des produits finaux par la validation de la ligne d'achat du service
    is_fp = fields.Boolean(string='FP', default=True)
    
    #===========================================================================
    # Onchange
    #===========================================================================
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
            Au changement du produit, changement de la catégorie de l'uom
        """
        self.uom_id = self.product_id and self.product_id.uom_id or False
        self.uom_category_id = self.product_id and self.product_id.uom_id and self.product_id.uom_id.category_id or False



class mrp_manufacturingorder(models.Model):
    """ 
        Manufacturing order 
    """
    _name = 'mrp.manufacturingorder'
    _description = 'Manufacturing order'
    
    
    @api.multi
    def copy(self, default=None):
        """
            Copie d'MO
        """
        if not self._context.get('ok_copy', False):
            raise except_orm(_('Error'), _('Impossible to copy MO.'))
        
        return super(mrp_manufacturingorder, self).copy(default=default)
    
    
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
    
    
    @api.one
    @api.depends('sale_line_id', 'sale_line_id.requested_date', 'sale_line_id.sale_order_id', 'sale_line_id.sale_order_id.partner_id')
    def _compute_sale_line(self):
        """
            Fonction qui récupère la date de demandé et le client dans la ligne de vente
        """
        self.requested_date = self.sale_line_id and (self.sale_line_id.departure_date or self.sale_line_id.requested_date) or ''
        self.customer_id = self.sale_line_id and self.sale_line_id.sale_order_id and self.sale_line_id.sale_order_id.partner_id or False

    
    @api.one
    @api.depends('product_id', 'product_id.uom_id')
    def _compute_product_id(self):
        """
            Fonction qui récupère la unite de gestion du produit
        """
        self.uom_id = self.product_id and self.product_id.uom_id or False

    
    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('waiting', _('Waiting')),
                ('plan', _('Plan')),
                ('ready', _('Ready')),
                ('progress', _('In progress')),
                ('pause', _('Pause')),
                ('done', _('Done')),
                ('cancel', _('Cancel')),
                       ]
    
    
    @api.one
    @api.depends('workorder_ids', 'workorder_ids.planned_start_date', 'workorder_ids.planned_end_date')
    def _compute_planned_date(self):
        """
            Fonction qui calcule la semaine, le mois et l'année de la date de début plannifié
        """
        planned_start_date = False
        planned_end_date = False
        is_week = False
        is_next_week = False
        is_month = False
        
        first_workorder_rcs = self.env['mrp.workorder']
        last_workorder_rcs = self.env['mrp.workorder']
        for wo in self.workorder_ids:
            if not wo.prev_wo_ids:
                first_workorder_rcs += wo
            
            if not wo.next_wo_ids:
                last_workorder_rcs += wo
        
        if first_workorder_rcs:
            first_date = [x.planned_start_date for x in first_workorder_rcs if x.planned_start_date]
            planned_start_date = first_date and min(first_date) or False
        
        if last_workorder_rcs:
            last_dates = [x.planned_end_date for x in last_workorder_rcs if x.planned_end_date]
            planned_end_date = last_dates and max(last_dates) or False
        
        if planned_start_date:
            date = '%s'%(planned_start_date[0:10])
            date = datetime.datetime.strptime(date, '%Y-%m-%d')
            isocal = date.isocalendar()
            now = datetime.datetime.now()
            now_iso = now.isocalendar()
            week_num = now_iso[1]
            year_num =now_iso[0]
            if isocal[1] == week_num and year_num == isocal[0]:
                is_week = True
                
            if isocal[1] == 52 and (year_num + 1) == isocal[0] and (week_num + 1) == isocal[1]:
                is_next_week = True
                
            if now.month == date.month and year_num == isocal[0]:
                self.is_month = True
            
            # Sur 2 caractères
            if len(str(isocal[1])) == 1:
                self.week_number = '0%s'%(str(isocal[1]))
            else:
                self.week_number = str(isocal[1])
            
            # Sur 2 caractères
            if len(str(date.month)) == 1:
                self.month = '0%s'%(str(date.month))
            else:
                self.month = str(date.month)
                
            self.year = str(isocal[0])
        else:
            self.week_number = '00'
            self.month = '00'
            self.year = '0'
        
        self.planned_start_date = planned_start_date
        self.planned_end_date = planned_end_date
        self.is_week = is_week
        self.is_next_week = is_next_week
        self.is_month = is_month
    
    
    @api.one
    def _compute_color_priotity_need_move(self):
        """
            Fonction qui permet de récuperer la couleur du mouvement du produit final du dernier OT
        """
        if self.workorder_ids and self.product_id:
            last_wo_id = False
            for wo in self.workorder_ids:
                if not wo.next_wo_ids:
                    last_wo_id = wo.id
                    break
                
            color_priority_need_read = self.env['stock.move'].search_read([('wo_outgoing_id', '=', last_wo_id), ('state', 'not in', ('done', 'cancel')), ('product_id', '=', self.product_id.id)], ['color_priority_need'], limit=1, order='color_priority_need desc')
            color_priority_need = color_priority_need_read and color_priority_need_read[0]['color_priority_need'] or 0
        else:
            color_priority_need = 0
        
        self.color_priority_need_move = color_priority_need
    
    
    def _search_color_line(self, operator, value):
        """
            Fonction search qui permet de retrouver tous les OFs qui ont cette couleur
        """
        request = """
        SELECT 
            x.mo_id 
        FROM
            (SELECT 
                 max(color_priority_need) as color, 
                 (select mo_id from mrp_workorder where id = wo_outgoing_id) as mo_id
             FROM 
                 stock_move 
             WHERE
                 wo_outgoing_id is not null and 
                 state not in ('done', 'cancel') and
                 product_id = (SELECT 
                                    product_id 
                               FROM 
                                    mrp_manufacturingorder 
                               WHERE
                                    id = (SELECT 
                                              mo_id 
                                          FROM 
                                              mrp_workorder 
                                          WHERE 
                                              id = wo_outgoing_id))
             GROUP BY 
                 mo_id)  x
        WHERE 
            x.color = %d"""%(value)
        self.env.cr.execute(request)
        res_ids = self.env.cr.fetchall()          
        return [('id', 'in', res_ids)]
    
    
    def _search_is_week(self, operator, value):
        """
            Fonction search qui permet de retrouver tous les OFs qui sont de cette semaine
        """
        request = """
        SELECT 
            x.mo_id 
        FROM
            (SELECT     
            to_char(min(planned_start_date), 'WW') as week_date,
            to_char(min(planned_start_date), 'YYYY') as year_date,
            to_char((current_date), 'WW') as week_now,
            to_char((current_date), 'YYYY') as year_now,
            mo_id
             FROM 
             mrp_workorder 
             WHERE
             mo_id is not null
             and planned_start_date is not null
             GROUP BY 
             mo_id)  x
        
        where 
            x.week_now = x.week_date and
            x.year_now = x.year_date"""
        self.env.cr.execute(request)
        res_ids = self.env.cr.fetchall()          
        return [('id', 'in', res_ids)]
    
    
    def _search_is_next_week(self, operator, value):
        """
            Fonction search qui permet de retrouver tous les OFs qui sont de la semaine d'après semaine
        """
        request = """
        SELECT 
            x.mo_id 
        FROM
            (SELECT     
            to_char(min(planned_start_date), 'WW') as week_date,
            to_char(min(planned_start_date), 'YYYY') as year_date,
            to_char((current_date + interval '1 week'), 'WW') as week_now,
            to_char((current_date + interval '1 week'), 'YYYY') as year_now,
            mo_id
             FROM 
             mrp_workorder 
             WHERE
             mo_id is not null
             and planned_start_date is not null
             GROUP BY 
             mo_id)  x
        
        where 
            x.week_now = x.week_date and
            x.year_now = x.year_date"""
        self.env.cr.execute(request)
        res_ids = self.env.cr.fetchall()          
        return [('id', 'in', res_ids)]
    
    
    def _search_is_month(self, operator, value):
        """
            Fonction search qui permet de retrouver tous les OFs qui sont dans le mois
        """
        request = """
        SELECT 
            x.mo_id 
        FROM
            (SELECT     
            to_char(min(planned_start_date), 'MM') as week_date,
            to_char(min(planned_start_date), 'YYYY') as year_date,
            to_char((current_date), 'MM') as week_now,
            to_char((current_date), 'YYYY') as year_now,
            mo_id
             FROM 
             mrp_workorder 
             WHERE
             mo_id is not null
             and planned_start_date is not null
             GROUP BY 
             mo_id)  x
        
        where 
            x.week_now = x.week_date and
            x.year_now = x.year_date"""
        self.env.cr.execute(request)
        res_ids = self.env.cr.fetchall()          
        return [('id', 'in', res_ids)]
    
    
    @api.one
    @api.depends()
    def _compute_costs(self):
        wo_read = self.wo_ids.read(['theo_total_cost', 'real_total_cost'])
        self.wo_theo_cost = sum([x['theo_total_cost'] for x in wo_read] or [])
        self.wo_real_cost = sum([x['real_total_cost'] for x in wo_read] or [])
    
    
    @api.one
    @api.depends()
    def _compute_produce_total_qty(self):
        produce_total_qty = 0
        uom_obj = self.env['product.uom']
        last_wo = self.env['mrp.workorder'].search([('mo_id', '=', self.id)], order='sequence desc', limit=1)
        if last_wo:
            for wo_produce in last_wo.workorder_produce_ids:
                if wo_produce.state == 'done':
                    produce_total_qty += uom_obj._compute_qty_obj(wo_produce.uom_id, wo_produce.qty_ok, self.uom_id)
                    produce_total_qty += uom_obj._compute_qty_obj(wo_produce.uom_id, wo_produce.qty_hs, self.uom_id)
                
        self.produce_total_qty = produce_total_qty
    
    
    def _search_planned_end_date(self, operator, value):
        request = """
            SELECT 
                m.id
            FROM
                mrp_manufacturingorder as m,
                (SELECT     
                    mo_id,
                    max(planned_end_date) as max_date
                 FROM 
                     mrp_workorder
                 GROUP BY 
                     mo_id) as x
            WHERE 
                m.id = x.mo_id and
                x.max_date %s '%s'
                
        """%(operator, value)
        self.env.cr.execute(request)
        res_ids = self.env.cr.fetchall()          
        return [('id', 'in', [x[0] for x in res_ids])]
    
    
    @api.one
    @api.depends('routing_id', 'bom_id', 'is_disassembly')
    def _compute_disassembly(self):
        self.is_disassembly = self.routing_id and self.routing_id.is_disassembly or False
        if self.is_disassembly and self.bom_id:
            self.final_manuf_component_ids = self.bom_id.bom_ids.ids
        else:
            self.final_manuf_component_ids = []
        
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    #Entête
    name = fields.Char(required=True, size=256, default=lambda self: self.env['ir.sequence'].get('mrp.manufacturingorder'))
    product_id = fields.Many2one('product.product', string='Final Product', required=True, ondelete='restrict')
    prod_family_id = fields.Many2one('production.family', string='Production family', required=False, ondelete='restrict')
    quantity = fields.Float(string='Quantity', default=1.0, required=True, digits=dp.get_precision('Product quantity'))
    needed_quantity = fields.Float(string='Needed quantity', default=1.0, required=True, digits=dp.get_precision('Product quantity'))
    uom_id = fields.Many2one('product.uom', string='UoM', compute='_compute_product_id')
    bom_id = fields.Many2one('mrp.bom', string='BoM', required=False, ondelete='restrict')
    routing_id = fields.Many2one('mrp.routing', string='Routing', required=True, ondelete='restrict')
    sale_line_id = fields.Many2one('sale.order.line', string='Sale line', required=False, ondelete='set null', readonly=True)
    customer_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    requested_date = fields.Date(string='Requested Date', readonly=True)
    is_forecast = fields.Boolean(string='Forecast', default=False)
    min_start_date = fields.Datetime(string='Min Start Date')
    max_end_date = fields.Datetime(string='Max End Date')
    planned_start_date = fields.Datetime(string='Planned Start Date', compute='_compute_planned_date')
    planned_end_date = fields.Datetime(string='Planned End Date', compute='_compute_planned_date', search='_search_planned_end_date')
    state = fields.Selection('_state_get', default='draft', string='State')
    company_id = fields.Many2one('res.company', string='Company', required=False, ondelete='restrict', default=lambda self: self.env.user.company_id)
    color_priority_need_move = fields.Integer(compute='_compute_color_priotity_need_move', store=False, search='_search_color_line')
    level = fields.Integer(default=0, required=False)
    is_week = fields.Boolean(string='Is week', compute='_compute_planned_date', search='_search_is_week')
    is_next_week = fields.Boolean(string='Is next week', compute='_compute_planned_date', search='_search_is_next_week')
    is_month = fields.Boolean(string='Is month', compute='_compute_planned_date', search='_search_is_month')
    is_without_bom = fields.Boolean(string='Without BoM', default=False)
    is_use_kit = fields.Boolean(string='use kit', default=False)
    
    #OT
    workorder_ids = fields.One2many('mrp.workorder', 'mo_id',  string='Work Orders')

    #Comment
    note_planned = fields.Text(string='Note Planned')
    note_manufacturing = fields.Text(string='Note Manufacturing')
    note_origin = fields.Text(string='Note')    
    
    #Date
    month = fields.Selection('_month_get', string='Month', compute='_compute_planned_date', store=True)
    week_number = fields.Char(string='Week number', size=2, compute='_compute_planned_date', store=True) 
    year = fields.Char(string='Year', size=4, compute='_compute_planned_date', store=True)
    
    # Procurement
    procurement_deleted = fields.Boolean(string='Procurement order deleted', default=False)
    
    # Options
    option_ids = fields.Many2many('mrp.option',  string='Options')
    
    # Couts
    wo_real_cost = fields.Float(string='Real cost', compute='_compute_costs', digits=dp.get_precision('Product price'))
    wo_theo_cost = fields.Float(string='Theorical cost', compute='_compute_costs', digits=dp.get_precision('Product price'))
    
    # Attente délai
    need_delay_validation = fields.Boolean(default=False, copy=False)
    waiting_delay = fields.Boolean(default=False, copy=False)
    
    #Parameter Dimension
    parameter_ids = fields.One2many('parameter.dimension', 'mo_id',  string='Parameters', copy=True)
    
    #Documents
    internal_plan_ids = fields.Many2many('document.openprod', 'mo_document_openprod_rel', 'mo_id', 'document_id',  string='Internal documents', copy=True)
    
    # Coût
    theo_rm_cost = fields.Float(string='Material first cost', default=0.0, digits=dp.get_precision('Product price'))
    theo_produce_cost = fields.Float(string='Produce cost', default=0.0, digits=dp.get_precision('Product price'))
    theo_subcontracting_cost = fields.Float(string='Subcontracting cost', default=0.0, digits=dp.get_precision('Product price'))
    theo_total_cost = fields.Float(string='Total cost', default=0.0, digits=dp.get_precision('Product price'))
    real_rm_cost = fields.Float(string='Material first cost', default=0.0, digits=dp.get_precision('Product price'))
    real_produce_cost = fields.Float(string='Produce cost', default=0.0, digits=dp.get_precision('Product price'))
    real_subcontracting_cost = fields.Float(string='Subcontracting cost', default=0.0, digits=dp.get_precision('Product price'))
    real_total_cost = fields.Float(string='Total cost', default=0.0, digits=dp.get_precision('Product price'))
    produce_total_qty = fields.Float(string='Produce total qty', compute='_compute_produce_total_qty', digits=dp.get_precision('Product quantity'), help="The sum of the quantities manufactured (ok + quarantine, no HS)")
    
    # disassembly
    is_disassembly = fields.Boolean(string='Disassembly', compute='_compute_disassembly', store=True)
    final_manuf_component_ids = fields.Many2many('mrp.bom', 'mrp_manuf_mrp_bom_compoennt_rel', 'mo_id', 'bom_id', compute='_compute_disassembly', string='Final manuf components', store=True)


    #===========================================================================
    # Boutons
    #===========================================================================
    @api.multi    
    def button_compute_theo_costs(self):
        for mo in self:
            theo_rm_cost = 0
            theo_produce_cost = 0
            theo_subcontracting_cost = 0
            theo_total_cost = 0
            for wo in mo.workorder_ids:
                costs = wo.button_compute_theo_costs()
                theo_rm_cost += costs['theo_rm_cost']
                theo_produce_cost += costs['theo_produce_cost']
                theo_subcontracting_cost += costs['theo_subcontracting_cost']
                theo_total_cost += costs['theo_total_cost']
            
            mo.write({'theo_rm_cost': theo_rm_cost, 
                      'theo_produce_cost': theo_produce_cost, 
                      'theo_subcontracting_cost': theo_subcontracting_cost, 
                      'theo_total_cost': theo_total_cost,})
            
            move_produce_rcs, theo_price, real_price, currency_id = mo.compute_price_move_fp_button()
            if move_produce_rcs:
                move_produce_rcs.write({'theo_price': theo_price, 'currency_id': currency_id})
    
    
    @api.multi
    def button_clear_theo_costs(self):
        self.write({'theo_rm_cost': 0.0,
                    'theo_produce_cost': 0.0,
                    'theo_subcontracting_cost': 0.0,
                    'theo_total_cost': 0.0,})
        
    
    @api.multi    
    def button_compute_real_costs(self):
        for mo in self:
            real_rm_cost = 0
            real_produce_cost = 0
            real_subcontracting_cost = 0
            real_total_cost = 0
            for wo in mo.workorder_ids:
                costs = wo.button_compute_real_costs()
                real_rm_cost += costs['real_rm_cost']
                real_produce_cost += costs['real_produce_cost']
                real_subcontracting_cost += costs['real_subcontracting_cost']
                real_total_cost += costs['real_total_cost']
            
            
            mo.write({'real_rm_cost': real_rm_cost, 
                      'real_produce_cost': real_produce_cost, 
                      'real_subcontracting_cost': real_subcontracting_cost, 
                      'real_total_cost': real_total_cost,})
            
            move_produce_rcs, theo_price, real_price, currency_id = mo.compute_price_move_fp_button()
            if move_produce_rcs:
                move_produce_rcs.write({'partner_price': real_price, 'theo_price': theo_price, 'currency_id': currency_id})
    
    
    def compute_price_move_fp_button(self, forced_move_rcs=False):
        """
            Fonction qui permet de retourner les mouvements à modifier le prix theo, prix réel et la devise en donnant juste le MO
            forced_move_rcs sert que pour les ots de soustraitance
        """
        move_obj = self.env['stock.move']  
        mo = self
        if forced_move_rcs:
            move_rcs = forced_move_rcs
        else:
            wo_ids = mo.workorder_ids.ids
            move_rcs = move_obj.search([('product_id', '=', mo.product_id.id), '|', ('wo_fp_subcontracting_id', 'in', wo_ids), ('wo_outgoing_id', 'in', wo_ids)], limit=1)
            
        move_produce_rcs = False
        theo_price = 0
        real_price = 0
        currency_id = False
        if move_rcs:
            if move_rcs.wo_outgoing_id:
                subcontracting = move_rcs.wo_outgoing_id.is_subcontracting
            else:
                subcontracting = move_rcs.wo_fp_subcontracting_id.is_subcontracting
            
            if not subcontracting:
                move_rcs = move_obj.search([('product_id', '=', mo.product_id.id), ('wo_outgoing_id', 'in', wo_ids)], limit=1)
                if move_rcs:
                    last_wo = move_rcs.wo_outgoing_id
                    qty_ok = 0
                    qty_hs = 0
                    qty_quarantine = 0
                    move_produce_rcs = self.env['stock.move']
                    for wo_produce in last_wo.workorder_produce_ids:
                        if wo_produce.state == 'done':
                            qty_ok += wo_produce.qty_ok
                            qty_hs += wo_produce.qty_hs
                            qty_quarantine += wo_produce.qty_quarantine
                            move_produce_rcs += wo_produce.move_ids
                    
                    if move_produce_rcs:    
                        theo_price, real_price, currency_id = last_wo.mo_id.compute_price_move_fp(last_wo, qty_ok, qty_hs, qty_quarantine)
            else:
                if forced_move_rcs:
                    move_rcs = forced_move_rcs
                else:
                    move_rcs = move_obj.search([('product_id', '=', mo.product_id.id), ('wo_fp_subcontracting_id', 'in', wo_ids)], limit=1)
                    
                if move_rcs:
                    last_wo = move_rcs.wo_fp_subcontracting_id
                    # Pas de gestion de déchets en soustraitance
                    qty_ok = last_wo.quantity
                    qty_hs = 0
                    qty_quarantine = 0
                    if forced_move_rcs:
                        move_produce_rcs = forced_move_rcs
                    else:
                        move_produce_rcs = move_obj.search([('product_id', '=', mo.product_id.id), ('wo_fp_subcontracting_id', '=', last_wo.id)])
                    
                    if move_produce_rcs:
                        theo_price, real_price, currency_id = last_wo.mo_id.compute_price_move_fp(last_wo, qty_ok, qty_hs, qty_quarantine)
            
        return move_produce_rcs, theo_price, real_price, currency_id
    
    
    @api.multi
    def button_clear_real_costs(self):
        self.write({'real_rm_cost': 0.0,
                    'real_produce_cost': 0.0,
                    'real_subcontracting_cost': 0.0,
                    'real_total_cost': 0.0,})
    
    
    @api.multi
    def action_generating_wo(self):
        for mo in self:
            if mo.workorder_ids:
                raise except_orm(_('Error'), _('There are already WO lines'))
            variant_values = mo.variant_value_ids if mo._columns.has_key('variant_value_ids') else None
            res = self.env['mrp.workorder'].create_wo(mo.product_id, mo, quantity=mo.quantity, uom=mo.uom_id, bom=mo.bom_id, routing=mo.routing_id, options=mo.option_ids, variant_values=variant_values)

        return res
    
    
    @api.multi
    def button_split(self):
        for mo in self:
            vals = []
            # Création du wizard
            split_mo_obj = self.env['mrp.mo.split']
            workorder_ids = self.env['mrp.workorder'].search([('mo_id', '=', mo.id)], order='sequence asc')
            vals = [[0, 0, {'wo_id': wo.id}] for wo in workorder_ids]

            new_rcs = split_mo_obj.create({'mo_id': mo.id, 'line_ids': vals})
            return {
                    'name': _('Split MO'),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'mrp.mo.split',
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'res_id': new_rcs.id,
                    'nodestroy': True,
                    }
    
    
    @api.multi
    def conf_delay_button(self):
        for mo in self.read(['planned_end_date']):
            procurement_rs = self.env['procurement.order'].search([('mo_id', '=', mo['id'])])
            for proc in procurement_rs:
                action = self.env.ref('stock.act_confirm_date_wizard')
                if action:
                    action = action.read()[0]
                    action['context'] = {'default_mo_id': mo['id'], 
                                         'default_date': mo['planned_end_date'],
                                         'default_procurement_id': proc.id}

            return action
        
        
    @api.multi
    def open_source_procurement(self):
        """
            Fonction permettant d'afficher le procurement déclencheur
        """
        return self.env['procurement.order']._open_source_procurement([('mo_id', '=', self[0].id)])
    
    
    @api.multi
    def wkf_draft(self):
        for mo in self:
            mo.workorder_ids.wkf_draft()
            if not mo.workorder_ids:
                mo.write({'state': 'draft'})
    
    @api.multi
    def wkf_waiting(self, automatic_purchase=True, is_procur_level_manufact=True, is_procur_level_purchase=True):
        for mo in self:
            mo.workorder_ids.wkf_waiting(automatic_purchase=automatic_purchase, is_procur_level_manufact=is_procur_level_manufact, is_procur_level_purchase=is_procur_level_purchase)
    
    
    @api.multi
    def wkf_ready(self):
        for mo in self:
            mo.workorder_ids.wkf_ready()
    
    
    @api.multi
    def wkf_progress(self):
        for mo in self:
            mo.workorder_ids.wkf_progress()
        
        
    @api.multi
    def wkf_pause(self):
        for mo in self:
            mo.workorder_ids.wkf_pause()
            
        
    @api.multi
    def wkf_done(self):
        for mo in self:
            mo.workorder_ids.wkf_done()
    
    
    @api.multi
    def wkf_cancel(self):
        for mo in self:
            mo.workorder_ids.wkf_cancel()
            if not mo.workorder_ids:
                mo.write({'state': 'cancel'})
    
    
    def del_mo_and_son_mo(self, without_head=False):
        for mo in self:
            recursion_son_mo_wo = mo.recursion_son_mo_wo()
            mo_ids = recursion_son_mo_wo['mo_rcs'] or []
            if mo_ids:
                mo_ids += mo
            else:
                mo_ids = mo
            
            mo_ids.wkf_cancel()
            if without_head and mo in mo_ids:
                mo_ids -= mo
                mo.workorder_ids.unlink()
                
            for to_del_mo in mo_ids:
                if to_del_mo:
                    try:
                        to_del_mo.state
                        delete = True
                    except:
                        delete = False
                    
                    if delete:
                        to_del_mo.unlink()
        
        return True
    
    
    @api.multi
    def button_del_mo_and_son_mo(self):
        """
            Bouton qui supprime l'OF sélectionné et tous ses fils
        """
        return self.del_mo_and_son_mo()
    
    
    @api.multi
    def button_validate_forecast(self):
        """
            Bouton qui décoche la case prévisionnel sélectionnée de l'OF et tous ses fils
        """
        for mo in self:
            recursion_son_mo_wo = mo.recursion_son_mo_wo()
            mo_rcs = recursion_son_mo_wo['mo_rcs'] or self.env['mrp.manufacturingorder']
            wo_rcs = recursion_son_mo_wo['wo_rcs'] or self.env['mrp.workorder']
            mo_rcs += mo
            if mo.workorder_ids:
                wo_rcs += mo.workorder_ids
            
            mo_rcs.write({'is_forecast': False})
            if wo_rcs:
                wo_rcs.write({'is_forecast': False})
                loading_rcs = self.env['calendar.loading'].search([('wo_id', 'in', wo_rcs.ids)])
                loading_rcs.write({'is_forecast': False})
                # Partie mouvements et procurements
                move_rcs = self.env['stock.move'].search(['|', ('wo_incoming_id', 'in', wo_rcs.ids), ('wo_outgoing_id', 'in', wo_rcs.ids), ('not_usable', '=', False)])
                if move_rcs:
                    move_rcs.write({'is_forecast': False})
                    procurement_rcs = self.env['procurement.order'].search([('move_id', 'in', move_rcs.ids)])
                    procurement_rcs.write({'is_forecast': False})
        
        return True
    
    
    #===========================================================================
    # OnChange
    #===========================================================================
    @api.onchange('product_id', 'option_ids')
    def _onchange_product_id(self):
        """
            Au changement du produit, changement l'uom
        """
        res_onchange = self.onchange_product_id(self.product_id,  self.option_ids)
        self.uom_id = res_onchange['uom'] and res_onchange['uom'].id or False
        self.bom_id = res_onchange['bom'] and res_onchange['bom'].id or False
        self.routing_id = res_onchange['routing'] and res_onchange['routing'].id or False
        self.prod_family_id = res_onchange['prod_family'] and res_onchange['prod_family'].id or False
        self.parameter_ids.unlink()
        self.parameter_ids = res_onchange['parameter_ids']
        self.internal_plan_ids = res_onchange['internal_plan_ids']
    
    
    @api.onchange('needed_quantity', 'bom_id')
    def _onchange_quantity(self):
        """
            Vérification des minimum et multiples
        """
        res = {'warning': {}}
        res_onchange = self.onchange_quantity(self.product_id, self.needed_quantity, self.bom_id)
        self.quantity = res_onchange['quantity']
        return res
            
    
    @api.onchange('routing_id', 'bom_id')
    def _onchange_bom_routing_id(self):
        """
            Au changement de la nomenclature ou de la gamme, changement de la note pour production
        """
        res_onchange = self.onchange_bom_routing_id(self.bom_id, self.routing_id)
        self.note_manufacturing = res_onchange['note']
    
    
    #===========================================================================
    # Fonctions
    #===========================================================================     
    
    def compute_price_move_fp(self, wo, qty_ok, qty_hs, qty_quarantine):
        """
            Fonction qui permet de calculer le prix theo et réel et la devise en donnant l'ot, la qté ok, qté hs, qté quanrantaine
        """
        qty_total = qty_ok + qty_hs + qty_quarantine
        qty_ok_quaran = qty_ok + qty_quarantine
        ratio = 1
        if wo.quantity != qty_total and qty_total != 0:
            ratio = wo.quantity / qty_total
            
        real_price = wo.mo_id.real_total_cost / (ratio or 1) / (qty_ok_quaran or 1)
        type_valuation_production = self.env['stock.config.settings'].get_param('type_valuation_production') or False
        if type_valuation_production == 'theoretical_mo':
            theo_price = wo.mo_id.theo_total_cost / (ratio or 1) / (qty_ok_quaran or 1)
        elif type_valuation_production == 'theoretical_td':
            theo_price = wo.final_product_id.production_cost_price
            theo_price = self.env['product.uom']._compute_qty_obj(wo.final_product_id.uom_id, theo_price, wo.uom_id)
        elif type_valuation_production == 'seizure_theoretical':
            theo_price = wo.final_product_id.price_theo_manual
            theo_price = self.env['product.uom']._compute_qty_obj(wo.final_product_id.uom_id, theo_price, wo.uom_id)
        else:
            theo_price = 0 
        
        if wo.final_product_id.type_valuation_production == 'manual':
            real_price = wo.final_product_id.price_theo_manual
            theo_price = wo.final_product_id.price_theo_manual
        elif wo.final_product_id.type_valuation_production == 'pourcent_sale':
            price_temp = 0
            if wo.final_product_id.free_sale:
                price_temp = wo.final_product_id.sale_price
                price_temp = self.env['product.uom']._compute_qty_obj(wo.final_product_id.uos_id, price_temp, wo.uom_id)
            else:
                cinfo_rc = self.env['product.customerinfo'].search([('product_id','=', wo.final_product_id.id), ('state', '!=', 'obsolete')], order='sequence', limit=1)
                price_temp = wo.final_product_id.get_price_sale(cinfo_rc.partner_id, False, currency_price_return=wo.final_product_id.company_id.currency_id.id, 
                                                                    qty_uom = 1.0, date=fields.Date.today(), type='price', with_uoi=wo.uom_id)
            
            price_temp = price_temp * wo.final_product_id.pourcent_sale_price / 100
            real_price = price_temp
            theo_price = price_temp
        
        return theo_price, real_price, wo.final_product_id.company_id.currency_id.id
    
        
    def recursion_son_mo_wo(self, res=None):
        """
            Fonction récursive qui perme de retrouvé les OFs et OTs fils d'un OF
        """
        if not res:
            res = {'mo_rcs': self.env['mrp.manufacturingorder'], 'wo_rcs': self.env['mrp.workorder']}
        
        procurement_obj = self.env['procurement.order']
        wo_ids = self.workorder_ids.ids
        if wo_ids:
            procurement_rcs = procurement_obj.search([('origin_wo_id', '=', wo_ids), ('mo_id', '!=', False)])
            for procurement in procurement_rcs:
                res['mo_rcs'] += procurement.mo_id
                res['wo_rcs'] += procurement.mo_id.workorder_ids
                res = procurement.mo_id.recursion_son_mo_wo(res=res)

        return res
    
    
    def onchange_bom_routing_id(self, bom, routing):
        note = ''
        res={}
        if bom:
            note = bom.note_mo or ''
            if routing and routing.note_mo:
                note = '%s \n %s'%(note,routing.note_mo)
        
        res['note'] = note
        return res
    
    
    def onchange_product_id(self, product,  option_ids):
        res = {'uom': False, 'bom': False, 'routing': False, 'parameter_ids': [], 'internal_plan_ids': [], 'prod_family': False}
        if product:
            res['prod_family'] = product.prod_family_id
            res['uom'] = product.uom_id
            if res['uom']:
                res['bom'] = self.env['mrp.bom']._bom_find(product.id, res['uom'].id, date=fields.Date.today(), options=option_ids)
                if res['bom']:
                    if res['bom'].routing_ids:
                        routing_rcs = self.env['mrp.routing'].search([('id', 'in', res['bom'].routing_ids.ids)], order='sequence asc')
                        routing_list_rcs = routing_rcs._routing_find(options=option_ids)
                    else:
                        routing_list_rcs = False
                        
                    res['routing'] = routing_list_rcs or False
                    parameter_list = []
                    for param in product.parameter_ids:
                        parameter_list.append((0, 0, {'name': param.name, 'type_param_id': param.type_param_id.id, 'value': param.value}))
        
                    res['parameter_ids'] = parameter_list
            
            #On récupère les plans internes du produit
            if product.plan_control_ids:
                res['internal_plan_ids']  = [(4, plan_control.pdf_file.id) for plan_control in product.plan_control_ids if plan_control.type == 'pdf_production']
        
        return res
    
    
    def onchange_quantity(self, product, needed_quantity, bom):
        res = {'quantity': 0.0}
        if product:
            if bom:
                efficiency = bom.total_efficiency
                efficiency_round = bom.round
            else:
                efficiency = 0.0
                efficiency_round = 0.0
            
            res['quantity'] = self.qty_min_multiple(needed_quantity, 
                                                  product.production_min_qty, 
                                                  product.production_multiple_qty, 
                                                  efficiency, 
                                                  efficiency_round)
        else:
            res['quantity'] = needed_quantity
        
        return res
    
    
    @api.multi
    def compute_level(self, write=True):
        """ 
            Calcul du niveau de l'OF
            :param write: Mise à jour ou non de la base de données
            :type write: boolean
            :return: True
        """
        res = {}
        proc_obj = self.env['procurement.order']
        for mo in self:
            proc = proc_obj.search([('mo_id', '=', mo.id), ('state', '!=', 'cancel')], limit=1)
            if proc and proc.move_id.wo_incoming_id:
                parent_mo = proc.move_id.wo_incoming_id.mo_id
                if parent_mo.id not in res.keys():
                    res[mo] = parent_mo.level + 1
                else:
                    parent_mo.compute_level(write=False)
            else:
                res[mo] = 0
        
        if write:
            for mo, value in res.iteritems():
                mo.write({'level': value})
                mo.workorder_ids.write({'mo_level': value})
            
        return True
    
    
    @api.multi
    def compute_wo_level(self, write=True):
        """ 
            Calcul du niveau de l'OT dans l'OF
            :param write: Mise à jour ou non de la base de données
            :type write: boolean
            :return: Dictionnaire {wo_rs: level}
        """
        rl_level = {}
        for mo in self:
            sequences = [(wo.sequence, wo) for wo in mo.workorder_ids]
            rl_level = {x[-1]: sequences.index(x) for x in sequences}
        
        if write:
            for wo, value in rl_level.iteritems():
                wo.write({'level': value})
                
        return rl_level
    
    
    def qty_min_multiple(self, qty, qty_min=0.0, qty_multiple=1.0, efficiency=0.0, efficiency_round=0.0):
        """ 
            Retourne une quantité par rapport à une quantité minimum et un multiple
            :param qty: Quantité de base
            :type qty: float
            :param qty_min: Quantité minimum
            :type qty_min: float
            :param qty_multiple: Quantité multiple
            :type qty_multiple: float
            :param efficiency: Efficacité
            :type efficiency: float
            :param efficiency_round: Arrondie éfficacité
            :type efficiency_round: float
            :return: qty en float
        """
        # Efficacité
        if efficiency:
            qty = qty * (1.0 / efficiency)
        
        if efficiency_round:
            qty = roundingUp(qty, float(efficiency_round))
        
        # Minimum
        if qty_min > qty:
            qty = qty_min
        
        # Multiple
        if qty_multiple and Decimal(str(qty)) % Decimal(str(qty_multiple)):
            qty = roundingUp(qty, float(qty_multiple))
            
        return qty

    def vals_distribution_analytique(self, res_onchange_product):
        """
            Point d'entrée si le produit à de la distribution analytique
        """
        return False
    
    
    def create_mo(self, product, name=False, quantity=1.0, uom=False, bom=False, routing=False, other_data=None, with_raise=False, options=[], variant_values=[], parameters=[]):
        """ 
           Génération d'un ordre de fabrication à partir d'un produit
           :param product: Le produit product.product
           :type product: recordset
           :param name: Nom de la fabrication
           :type name: char 256
           :param quantity: Quantité de la fabrication.options
           :type quantity: float.
           :param uom: Unité de mesure product.uom.
           :type uom: recordset
           :param bom: La nomenclature mrp.bom
           :type bom: recordset
           :param routing: La gamme mrp.routing
           :type routing: recordset
           :param other_data: dico pour remplir de nouveau champ pour la creation d'une resource de l'OT
           :type other_data: dico des valeurs de l'OT (ex: {'name':'toto',})
           :return: id de l'ordre de fabrication créé
        """
        bom_obj = self.env['mrp.bom']
        mo_rs = False
        if product:
            res_onchange_product= self.onchange_product_id(product, options)
            if not uom:
                uom = res_onchange_product['uom'] or product.uom_id
                
            prod_family_id = res_onchange_product['prod_family'] and res_onchange_product['prod_family'].id or False
            if not bom:
                bom = res_onchange_product['bom'] or bom_obj._bom_find(product.id, uom.id, date=fields.Date.today(), options=options)
                
            if not routing and bom and bom.routing_ids:
                routing = res_onchange_product['routing'] or bom and bom.routing_ids and bom.routing_ids[0] or False
            
            if bom and routing:
                if not name:
                    name = self.env['ir.sequence'].get('mrp.manufacturingorder')
                
                needed_quantity = quantity
                if quantity:
                    res_onchange_quantity = self.onchange_quantity(product, needed_quantity, bom)
                    quantity = res_onchange_quantity['quantity']
                    
                parameter_list = parameters
                for param in product.parameter_ids:
                    cont = False
                    for line in parameter_list:
                        if line[2]['name'] == param.name:
                            cont = True
                            break
                        
                    if cont:
                        continue
                    
                    parameter_list.append((0, 0, {'name': param.name, 'type_param_id': param.type_param_id.id, 'value': param.value, }))

                vals = {
                    'name': name,
                    'product_id': product.id,
                    'quantity': quantity,
                    'needed_quantity': needed_quantity,
                    'uom_id': uom.id,
                    'bom_id': bom.id,
                    'routing_id': routing.id,
                    'option_ids': [(6, 0, [p.id for p in options])],
                    'variant_value_ids':[(6, 0, [v.id for v in variant_values])],
                    'parameter_ids': parameter_list,
                    'internal_plan_ids': res_onchange_product.get('internal_plan_ids', []),
                    'prod_family_id': prod_family_id,
                }
                if other_data:
                    vals.update(other_data)
                
                distrib_vals = self.vals_distribution_analytique(res_onchange_product)
                if distrib_vals:
                    vals.update(distrib_vals)
                
                mo_rs = self.create(vals)
                
            elif with_raise:
                if not bom:
                    raise except_orm(_('Error'), _('Product %s have not BoM')%(product.name_get()[0][1]))
                
                if not routing:
                    raise except_orm(_('Error'), _('Product %s have not routing')%(product.name_get()[0][1]))
                
        return mo_rs, quantity
    
    
    def split_light(self, coeff, data_other=None):
        """ 
           Diviser l'ordre de fabrication simple
           :param coeff: Le coefficient diviseur
           :type coeff: Float
           :return: recordset de l'ordre de fabrication créé
        """
        new_qty = self.quantity/coeff
        rest_qty = self.quantity - new_qty 
        
        default = {
          'quantity': rest_qty,
          'workorder_ids': [],
          'name':self.env['ir.sequence'].get('mrp.manufacturingorder')
        }
        if data_other:
            default.update(data_other)
            
        new_rcs = self.with_context({'ok_copy':True}).copy(default)
        self.write({'quantity': new_qty})
        return new_rcs
    
    
    def split(self, ids_to_split, coeff, data_other=None):
        """ 
            Diviser l'OF et des OTs
            :param ids_to_split: Liste des OF à modifier.
            :type ids_to_split: list d'ids
            :param coeff: Coefficient de division.
            :type coeff: Float.
            :return: True.
        """
        wo_obj = self.env['mrp.workorder']
        ctx = self.env.context.copy()
        for mo_id in ids_to_split:
            mo_wo_splited = wo_obj.with_context(ctx).split_wo(wo_obj.search([('mo_id', '=', mo_id)], order='sequence asc'), coeff, data_other=data_other)
            if self.env.context.get('return_mo_wo_splited'):
                return mo_wo_splited
               
        return True
    
    
    def validate_move_fp_intervention(self):
        """
            Fonction utilisé dans la GMAO qui permet lors de la plannification au plus tard de valider les mouvements finaux du premier OT qui sont les matières 
            démontées pour ne pas lancer la production ou l'achat des produits à remonter dans le dernier OT.
        """
        return True
    
    
    @api.multi
    def unlink(self):
        for mo in self:
            mo.workorder_ids.unlink()
        
        return super(mrp_manufacturingorder, self).unlink()
    
    
    def plannification_mo_done(self, is_sublevel=False, automatic_purchase=False):
        """ 
            Termine la plannification l'OF ou des OFs
        """
        procurement_obj = self.env['procurement.order']
        for wo in self.workorder_ids:
            if not wo.planned_start_date or not wo.planned_end_date:
                raise except_orm(_('Error'), _('We must first plannifier WOs.'))
                
            wo.wkf_waiting(automatic_purchase=automatic_purchase, is_procur_level_manufact=True, is_procur_level_purchase=True)
            if automatic_purchase:
                wo.validate_procurement_rm()
            
            if is_sublevel:    
                for procurement in procurement_obj.search([('origin_wo_id', '=', wo.id)]):
                    if procurement.supply_method == 'produce' and procurement.mo_id:
                        procurement.mo_id.plannification_mo_done(is_sublevel=is_sublevel, automatic_purchase=automatic_purchase)
            
            wo.wkf_plan()
            
        return True
    
    
    @api.model
    def create(self, vals):
        """
            A la création d'un OF, si il y a une ligne de vente, on rempli le client et la
            date demandée à partir de cette ligne de vente 
        """
        if vals and vals.get('sale_line_id'):
            sale_line_rs = self.env['sale.order.line'].browse(vals['sale_line_id'])
            if sale_line_rs:
                partner_rs = sale_line_rs.sale_order_id and sale_line_rs.sale_order_id.partner_id or False
                vals['customer_id'] = partner_rs and partner_rs.id or False
                vals['requested_date'] = sale_line_rs and (sale_line_rs.departure_date or sale_line_rs.requested_date) or False
            
        return super(mrp_manufacturingorder, self).create(vals)
    
    
#     def recursion_plannification_mo_at_earlier(self, res=None):
#         """
#             Fonction de récursion qui permet plannifie les OFs du premier niveau en dessous
#         """
#         procurement_obj = self.env['procurement.order']
#         if not res:
#             res = self.env['mrp.manufacturingorder']
#         
#         if self.workorder_ids:
#             procurement_rcs = procurement_obj.search([('origin_wo_id', 'in', self.workorder_ids.ids)])
#             if procurement_rcs:
#                 for procurement in procurement_rcs:
#                     if procurement.supply_method == 'produce' and procurement.mo_id:
#                         res += procurement.mo_id.recursion_plannification_mo_at_earlier(res=res)
# 
#             res += self
#             
#         return res



class resource_timetracking(models.Model):
    _inherit = 'resource.timetracking'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wo_id = fields.Many2one('mrp.workorder', string='WO', required=False, ondelete='restrict', select=True)
    group_wo_id = fields.Many2one('mrp.group.wo', string='Group wo', required=False, ondelete='restrict')
    
    
    #===========================================================================
    # Fonctions
    #===========================================================================
    def create_wo_timetracking(self, wo_rcs, activity='', stop=False):
        """ 
            Creation d'une ligne de timetracking pour un WO
            :param wo_rcs: Les OTs
            :type wo_rcs: Recordeset: mrp.workorder
            :param activity: L'activité
            :type activity: String.
            :param stop: Si ce n'est que pour terminer un timetracking
            :type stop: Boolean.
            :return: Recordset de toutes les lignes créées.
        """
        timetracking_rcs = False
        done_time_rcs = self.search([('wo_id', 'in', wo_rcs.ids), ('end_date', '=', False)])
        date_time_str = fields.Datetime.context_timestamp(self, datetime.datetime.now()).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        date_time = fields.Datetime.now()
        if done_time_rcs:
            for done_time in done_time_rcs:
                time_activity = (datetime.datetime.strptime(date_time, DEFAULT_SERVER_DATETIME_FORMAT) - datetime.datetime.strptime(done_time.start_date, DEFAULT_SERVER_DATETIME_FORMAT)) / 3600
                time_spent = done_time.is_first_resource and done_time.wo_id.group_wo_id and done_time.wo_id.group_wo_id.time_total_theo and time_activity.total_seconds() * done_time.wo_id.total_time_theo / done_time.wo_id.group_wo_id.time_total_theo or time_activity.total_seconds()
                done_time.write({'end_date': date_time, 'time': time_activity.total_seconds(), 'time_spent': time_spent})
        
        if not stop and activity:
            for wo in wo_rcs:
                for wo_resource in wo.wo_resource_ids:
                    vals = {
                        'name': '%s - %s - %s'%(wo_resource.resource_id.name, wo.name, date_time_str),
                        'resource_id': wo_resource.resource_id.id,
                        'start_date': date_time,
                        'activity': activity,
                        'wo_id': wo.id,
                        'user_id': self.env.user.id,
                        'is_first_resource': wo.first_resource_id == wo_resource.resource_id,
                        'group_wo_id': wo.group_wo_id and wo.group_wo_id.id or False,
                        
                    }
                    if timetracking_rcs:
                        timetracking_rcs += self.create(vals)
                    else:
                        timetracking_rcs = self.create(vals)
                for additional_wo_resource in wo.additional_resource_ids:
                    if not additional_wo_resource.end_date:
                        is_first_resource = wo.first_resource_id.type == 'human'
                        vals = {
                            'name': '%s - %s - %s'%(additional_wo_resource.resource_id.name, wo.name, date_time),
                            'resource_id': additional_wo_resource.resource_id.id,
                            'start_date': date_time,
                            'activity': activity,
                            'wo_id': wo.id,
                            'user_id': self.env.user.id,
                            'is_first_resource': is_first_resource,
                            'group_wo_id': wo.group_wo_id and wo.group_wo_id.id or False,
                        }
                        timetracking_rcs += self.create(vals)
                        
        return timetracking_rcs
    
    
    def _timesheet_fields_list(self):
        res = super(resource_timetracking, self)._timesheet_fields_list()
        res.append('wo_id')
        return res
            
            
    
class mrp_label_consumption(models.Model):
    """ 
    Relation OT/étiquette lors de la déclaration de production 
    """
    _name = 'mrp.label.consumption'
    _description = 'Relation OT/etiquette lors de la declaration de production '
    
    
    @api.one
    def _compute_is_declared(self):
        """
            Fonction qui permet de savoir si l'étiquette a déjà été utilisée pour la déclaration 
        """
        is_declared = False
        if self.label_id.product_id:
            # Récupération des mouvements done dans l'OT du produit de l'étiquette
            move_rcs = self.env['stock.move'].search([('state', '=', 'done'), ('product_id', '=', self.label_id.product_id.id), ('wo_incoming_id', '=', self.wo_id.id)])
            # Récupération des mouvements de l'étiquette
            move_in_stock_move_label_ids = []
            stock_move_label_rcs = self.env['stock.move.label'].search([('label_id', '=', self.label_id.id)])
            for stock_move_label in stock_move_label_rcs:
                if stock_move_label.move_id:
                    move_in_stock_move_label_ids.append(stock_move_label.move_id.id)
            
            # Test si un des mouvements de l'étiquette fait partie des mouvements de terminés de l'OT
            if move_rcs and move_in_stock_move_label_ids:
                for move in move_rcs:
                    if move.id in move_in_stock_move_label_ids:
                        is_declared = True
                        break
                    
        self.is_declared = is_declared
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wo_id = fields.Many2one('mrp.workorder', string='Workorder', required=True, ondelete='cascade')
    label_id = fields.Many2one('stock.label', string='Label', required=True, ondelete='cascade')
    quantity = fields.Float(string='Quantity', default=0.0, required=True)
    product_id = fields.Many2one('product.product', string='Product', related='label_id.product_id', ondelete='cascade', readonly=True)
    quantity_label = fields.Float(string='Quantity Label', related='label_id.uom_qty', readonly=True)
    is_declared = fields.Boolean(string='Is Declared', default=False, compute='_compute_is_declared') 
    use_consumption = fields.Boolean(string='Used for consumption', default=False)
    uom_id = fields.Many2one('product.uom', string='UoM', related='label_id.uom_id')
    
    _sql_constraints = [
        ('unique_label', 'unique(label_id, wo_id)', 'Error: This label is already in use for this work order'),
    ]
    
    @api.constrains('quantity', 'quantity_label', 'label_id')
    def _check_qty_label(self):
        """ 
            Contrainte sur la qty de l'étiquète
        """ 
        #Contrainte : les temps masquées de chaque catégorie de ressource ne peut être supérieur à la Somme des temps de préparation d'une opération
        if self.quantity and self.quantity_label and self.label_id and self.quantity > self.quantity_label:
            raise except_orm(_('Error'), _('The amount can not be higher than that of the label %s (%f)') %(self.label_id.name, self.quantity_label))
    

    @api.onchange('label_id')
    def _onchange_label_id(self):
        self.quantity_label = self.label_id.uom_qty
        self.quantity = self.label_id.uom_qty



class mrp_label_production(models.Model):
    """ 
    Relation OT/étiquette lors de la déclaration de production 
    """
    _name = 'mrp.label.production'
    _description = 'Relation OT/etiquette lors de la declaration de production '
    
    
    @api.one
    def _compute_is_declared(self):
        """
            Fonction qui permet de savoir si l'étiquette a déjà été utilisée pour la déclaration 
        """
        is_declared = False
        if self.label_id.product_id:
            # Récupération des mouvements done dans l'OT du produit de l'étiquette
            move_rcs = self.env['stock.move'].search([('state', '=', 'done'), ('product_id', '=', self.label_id.product_id.id), ('wo_outgoing_id', '=', self.wo_id.id)])
            # Récupération des mouvements de l'étiquette
            move_in_stock_move_label_ids = []
            stock_move_label_rcs = self.env['stock.move.label'].search([('label_id', '=', self.label_id.id)])
            for stock_move_label in stock_move_label_rcs:
                if stock_move_label.move_id:
                    move_in_stock_move_label_ids.append(stock_move_label.move_id.id)
            
            # Test si un des mouvements de l'étiquette fait partie des mouvements de terminés de l'OT
            if move_rcs and move_in_stock_move_label_ids:
                for move in move_rcs:
                    if move.id in move_in_stock_move_label_ids:
                        is_declared = True
                        break
                    
        self.is_declared = is_declared
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wo_id = fields.Many2one('mrp.workorder', string='Workorder', required=True, ondelete='cascade')
    label_id = fields.Many2one('stock.label', string='Label', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', related='label_id.product_id', ondelete='cascade', readonly=True)
    quantity_label = fields.Float(string='Quantity Label', related='label_id.uom_qty', readonly=True)
    is_declared = fields.Boolean(string='Is Declared', default=False, compute='_compute_is_declared') 
    uom_id = fields.Many2one('product.uom', string='UoM', related='label_id.uom_id')
    
    _sql_constraints = [
        ('unique_label', 'unique(label_id, wo_id)', 'Error: This label is already in use for this work order'),
    ]
    

    @api.onchange('label_id')
    def _onchange_label_id(self):
        self.quantity_label = self.label_id.printed_qty



class mrp_rl_cost_history(models.Model):
    """ 
    Mrp routing line cost history 
    """
    _name = 'mrp.rl.cost.history'
    _description = 'Mrp routing line cost history'
    _order = 'date DESC'
    _rec_name = 'rl_id'

    #===========================================================================
    # COLUMNS
    #===========================================================================
    date = fields.Datetime(string='Date', default=lambda self: fields.Datetime.now())
    currency_id = fields.Many2one('res.currency', string='Currency', required=False, ondelete='cascade')
    price_qty = fields.Float("Price Qty", digits=dp.get_precision('Price technical'))
    price = fields.Float(string='Price total', default=0.0, required=False, digits=dp.get_precision('Price technical'))
    rl_id = fields.Many2one('mrp.routing.line', string='RL', required=False, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='Users', required=False, ondelete='set null')



class mrp_routing_cost_history(models.Model):
    """ 
    Mrp routing cost history 
    """
    _name = 'mrp.routing.cost.history'
    _description = 'Mrp routing cost history'
    _order = 'date DESC'
    _rec_name = 'routing_id'

    #===========================================================================
    # COLUMNS
    #===========================================================================
    date = fields.Datetime(string='Date', default=lambda self: fields.Datetime.now())
    currency_id = fields.Many2one('res.currency', string='Currency', required=False, ondelete='cascade')
    price_qty = fields.Float("Price Qty", digits=dp.get_precision('Price technical'))
    price = fields.Float(string='Price unit', default=0.0, required=False, digits=dp.get_precision('Price technical'))
    routing_id = fields.Many2one('mrp.routing', string='Routing', required=False, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='Users', required=False, ondelete='set null')
    


class mrp_component_cost_history(models.Model):
    """ 
    Mrp component cost history 
    """
    _name = 'mrp.component.cost.history'
    _description = 'Mrp component cost history'
    _order = 'date DESC'
    _rec_name = 'component_id'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    date = fields.Datetime(string='Date', default=lambda self: fields.Datetime.now())
    currency_id = fields.Many2one('res.currency', string='Currency', required=False, ondelete='cascade')
    price_qty = fields.Float("Price Qty", digits=dp.get_precision('Price technical'))
    price = fields.Float(string='Price total', default=0.0, required=False, digits=dp.get_precision('Price technical'))
    component_id = fields.Many2one('mrp.bom', string='Component', required=False, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='Users', required=False, ondelete='set null')
    


class mrp_bom_cost_history(models.Model):
    """ 
    Mrp bom cost history 
    """
    _name = 'mrp.bom.cost.history'
    _description = 'Mrp bom cost history'
    _order = 'date DESC'
    _rec_name = 'bom_id'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    date = fields.Datetime(string='Date', default=lambda self: fields.Datetime.now())
    currency_id = fields.Many2one('res.currency', string='Currency', required=False, ondelete='cascade')
    bom_id = fields.Many2one('mrp.bom', string='BoM', required=False, ondelete='cascade')
    price_qty = fields.Float("Price Qty", digits=dp.get_precision('Price technical'))
    price = fields.Float(string='Price unit', default=0.0, required=False, digits=dp.get_precision('Price technical'))
    routing_first_price = fields.Float(string='Routing first price', default=0.0, required=False, digits=dp.get_precision('Price technical'))
    production_cost_price = fields.Float("Cost price", digits=dp.get_precision('Price technical'))
    user_id = fields.Many2one('res.users', string='Users', required=False, ondelete='set null')
    


class mrp_group_wo(models.Model):
    _name = 'mrp.group.wo'
    _description = """Group work order object"""
    
    
    @api.one
    @api.depends('wo_ids', 'wo_ids.categ_first_resource_id')
    def _compute_categ_resource_id(self):
        self.categ_resource_id = self.wo_ids and self.wo_ids[0].categ_first_resource_id and self.wo_ids[0].categ_first_resource_id.id or False
    
    
    @api.one
    @api.depends('wo_ids', 'wo_ids.first_wo_resource_id', 'wo_ids.first_wo_resource_id.total_production_time', 'wo_ids.first_wo_resource_id.total_preparation_time')
    def _compute_duration_theo(self):
        first = True
        duration_theo = 0
        time_total_theo = 0
        for wo in self.wo_ids:
            if first:
                duration_theo += wo.first_wo_resource_id.total_preparation_time
                first = False
            
            duration_theo += wo.first_wo_resource_id.total_production_time
            time_total_theo += wo.total_time_theo
        
        self.duration_theo = duration_theo
        self.time_total_theo = time_total_theo
    
    
    @api.one
    @api.depends('planned_start_date', 'duration', 'resource_id')
    def _compute_planned_end_date(self):
        planned_end_date = None
        if self.resource_id and self.planned_start_date and self.duration:
            planned_end_date = self.resource_id.calendar_id.get_dates(self.planned_start_date, self.duration)
        
        self.planned_end_date = planned_end_date and planned_end_date['end_date'] or None
        
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Name', size=128, required=True, help='mrp_group_wo.name.help', default=lambda self: self.env['ir.sequence'].get('group_wo'))
    wo_ids = fields.One2many('mrp.workorder', 'group_wo_id',  string='WOs')
    resource_id = fields.Many2one('mrp.resource', string='Resource', required=True, ondelete='restrict', help='mrp_group_wo.resource_id.help')
    categ_resource_id = fields.Many2one('mrp.resource.category', string='Category', compute='_compute_categ_resource_id', store=True, help='mrp_group_wo.categ_resource_id.help')
    planned_start_date = fields.Datetime(string='Planned start date', required=True, help='mrp_group_wo.planned_start_date.help')
    planned_end_date = fields.Datetime(string='Planned end date', compute='_compute_planned_end_date', store=True, help='mrp_group_wo.planned_end_date.help')
    duration_theo = fields.Float(string='Duration theo', compute='_compute_duration_theo', store=True, help='mrp_group_wo.duration_theo.help')
    duration = fields.Float(string='Duration', default=0.0, required=True, help='mrp_group_wo.duration.help')
    time_total_theo = fields.Float(string='Duration', compute='_compute_duration_theo', store=True, help='mrp_group_wo.time_total_theo.help')
    
    
    #===========================================================================
    # Functions
    #===========================================================================
    @api.model
    def create(self, vals=None):
        """
        """
        res = super(mrp_group_wo, self).create(vals=vals)
        res.add_change_resource(res.resource_id.id, res.wo_ids)
        res.wo_ids.write({'planned_start_date': res.planned_start_date, 'planned_end_date': res.planned_end_date})
        return res
    
    
    @api.multi
    def write(self, vals=None):
        """
            Redéfinition pour les opérations consommées
        """
        res = super(mrp_group_wo, self).write(vals=vals)
        if 'resource_id' in vals:
            for group in self:
                group.add_change_resource(group.resource_id, group.wo_ids)
        if 'planned_start_date' in vals or 'resource_id' in vals or 'duration_theo' in vals or 'duration' in vals:
            for group in self:
                group.wo_ids.write({'planned_start_date': group.planned_start_date, 'planned_end_date': group.planned_end_date})
        
        return res
    
     
    def delete_wo_from_group(self, wo_ids):
        """
            Suppresion d'OT du group
        """
        groups = {}
        for wo in self.env['mrp.workorder'].browse(wo_ids):
            if wo.group_wo_id:
                if wo.group_wo_id in groups:
                    groups[wo.group_wo_id].append(wo.id)
                else:
                    groups[wo.group_wo_id] = [wo.id]
                 
        for group_wo, wo_list in groups.iteritems():
            group_wo.write({'wo_ids': [(3, x) for x in wo_list]})
 
        return True
     
    
    @api.multi
    def add_wo_to_group(self, wo_ids):
        """
            Fonction ajout d'OTs dans le groupement
        """
        self.add_change_resource(self.resource_id.id, self.env['mrp.workorder'].browse(wo_ids))
        return True
     
     
    def add_change_resource(self, resource_id, wo_rcs):
        """
            Fonction ajout de ressource dans les OTs et changement de ressource
        """
        first = True
        rm_ids = []
        categ_resource_id = self.categ_resource_id.id
        wo_exist_ids = self.wo_ids.ids
        no_constraint = self.no_constraint()
        for wo in wo_rcs:
            if not first:
                if set([x.product_id.id for x in wo.rm_draft_ids if x.product_id]) != set(rm_ids) and not no_constraint:
                    raise except_orm(_('Error'), _("Incompatible raw materials."))
                
                if categ_resource_id != (wo.categ_first_resource_id and wo.categ_first_resource_id.id or False) and not no_constraint:
                    raise except_orm(_('Error'), _("Incompatible category resource."))
            else:
                rm_ids = [x.product_id.id for x in wo.rm_draft_ids if x.product_id]
                first = False
            
            if wo.first_resource_id != self.resource_id:
                wo.change_resource(wo.first_wo_resource_id, self.resource_id, wo.first_wo_resource_id.rl_resource_category_id, add_resource_rl=True, no_plannif=True)
            
            if wo.id not in wo_exist_ids:
                self.write({'wo_ids': [(4, wo.id)]})
                self._compute_categ_resource_id()
                categ_resource_id = self.categ_resource_id.id
                wo_exist_ids.append(wo.id)
            
            
        return True
    
    
    def no_constraint(self):
        return False
    
    
    @api.multi
    def action_validation(self):
        return {
                    'name': _('Group WO'),
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'mrp.group.wo',
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'res_id': self.id,
                    }
        
    
    def do_label_consumption_grouped(self, label_rcs, wo_qty_decla=1):
        if label_rcs:
            move_obj = self.env['stock.move']
            uom_obj = self.env['product.uom']
            move_label_obj = self.env['stock.move.label']
            label = label_rcs[0]
            product = label.product_id
            if product and self.wo_ids:
                # Recherche des mouvements à consommer du produit dans les OTs, s'il n'y en a pas il sera créé dans le premier OTs
                move_rcs_temporate = move_obj.search([('wo_incoming_id', '=', self.wo_ids.ids), 
                                            ('state', 'not in', ('cancel', 'done')), 
                                            ('product_id', '=', product.id)], order='wo_incoming_id asc')
                
                move_rcs = self.env['stock.move']
                create_new_move = True
                if move_rcs_temporate:
                    # On regarde si le mouvement n'a pas déjà des étiquettes affectées si c'est le cas on split le mouvement pour n'utiliser qu'un mouvement sans étiquette, par
                    # contre si la somme des étiquettes est équivalente à la quantité du mouvement alors on crée un nouveau mouvement
                    for move in move_rcs_temporate:
                        if move.move_label_ids:
                            total_qty_inter = 0.0
                            total_sec_qty_inter = 0.0
                            total_uoi_qty_inter = 0.0
                            sec_qty_factor = move.sec_uom_qty / (move.uom_qty or 1.0)
                            uoi_qty_factor = move.uoi_qty / (move.uom_qty or 1.0)
                            for move_label in move.move_label_ids:
                                if (move_label.uom_id or move_label.label_id.uom_id) != move.uom_id:
                                    label_uom_id = move_label.uom_id or move_label.label_id.uom_id
                                    qty = uom_obj._compute_qty_obj(label_uom_id, move_label.uom_qty, move.uom_id)
                                else:
                                    qty = label.uom_qty
                                
                                total_qty_inter += qty
                                total_sec_qty_inter += qty * sec_qty_factor
                                total_uoi_qty_inter += qty * uoi_qty_factor
                            
                            if total_qty_inter < move.uom_qty:
                                create_new_move = False
                                move_draft = False
                                if move.state == 'draft':
                                    move_draft = True
                                    
                                move_dic = move.split_light(move.uom_qty/total_qty_inter)
                                move_rcs_int = move_dic['new_move_rcs']
                                move_rcs += move_rcs_int
                                if not move_draft:
                                    move_rcs_int.wkf_waiting()
                                
                        else:
                            move_rcs += move
                            create_new_move = False  
                
                # Si pas de mouvement on fait appelà la consommation d'un OT
                if create_new_move:
                    self.wo_ids[0].do_label_consumption(label_rcs, wo_qty_decla or 1.0)
                    return True
                
                move_data = []
                for move in move_rcs:
                    # Conversion de la quantité du move en UoM du produit
                    if move.uom_id and move.product_id and move.product_id.uom_id \
                       and move.uom_id.id != move.product_id.uom_id.id \
                       and move.uom_id.category_id.id == move.product_id.uom_id.category_id.id:
                        qty = uom_obj._compute_qty_obj(product.uom_id, move.uom_qty, move.uom_id)
                    else: 
                        qty = move.uom_qty
                        
                    # facteur de conversion des quantités
                    sec_qty_factor = move.sec_uom_qty / (move.uom_qty or 1.0)
                    uoi_qty_factor = move.uoi_qty / (move.uom_qty or 1.0)
                    
                    move_data.append({'move': move, 
                                      'qty': qty, 
                                      'wo_id': move.wo_incoming_id.id, 
                                      'sec_qty_factor': sec_qty_factor, 
                                      'uoi_qty_factor': uoi_qty_factor})   
                
                label_data = []
                for label in label_rcs:
                    label_data.append({'label': label, 
                                       'qty': label.uom_qty})
                
                if move_data and label_rcs:    
                    # 3. Trie des listes
                    label_data = sorted(label_data, key=itemgetter('qty'), reverse=True)
                    move_data = sorted(move_data, key=itemgetter('wo_id', 'qty'), reverse=True)
                    # 4. Consommation
                    move_to_cancel_rcs = self.env['stock.move']
                    no_label = False
                    for move_dict in move_data:
                        last_move = move_dict['move'] == move_data[-1]['move']
                        affect_label_move_rcs = self.env['stock.label']
                        dict_label_qty = {}
                        move_to_done = False
                        if not no_label:
                            for label_dict in label_data:
                                last_label = label_dict['label'] == label_data[-1]['label']
                                if label_dict['qty']:
                                    # Si "qte etiquette" >= "qte move"
                                    if label_dict['qty'] >= move_dict['qty']:
                                        # Si c'est le dernier mouvement: consommation de toutes les étiquettes restantes
                                        if last_move:
                                            affect_label_move_rcs += label_dict['label']
                                            break
                                        # Sinon affectiation de l'étiquette en partie
                                        else:
                                            label_dict['qty'] -= move_dict['qty']
                                            dict_label_qty[label_dict['label']] = (move_dict['qty'], move_dict['qty'])
                                            break
                                        
                                    # Si "qte etiquette" < "qte move": split du move, affectation de l'etiquette au nouveau move et done du nouveau move
                                    else:
                                        affect_label_move_rcs += label_dict['label']
                                        move_dict['qty'] -= label_dict['qty']
                                        label_dict['qty'] = 0.0
                    
                            # Si c'est la dernière étiquette: cancel du mouvement
                            if last_label and not label_dict['qty']:
                                no_label = True
                            
                            move_to_done = move_dict['move']
                        
                        else:
                            move_to_cancel_rcs |= move_dict['move']
                            
                        if affect_label_move_rcs:
                            move_same_label_ids = move_label_obj.search([('move_id.state', 'not in', ['done', 'cancel']), 
                                                                         ('move_id.picking_id', '!=', False), 
                                                                         ('label_id', 'in', affect_label_move_rcs.ids)], limit=1)
                            if move_same_label_ids:
                                raise except_orm(_('Error'), _('UC label %s is already assign.')%(move_same_label_ids[0].label_id.name))
                                    
                            move_label_obj.create_move_label(affect_label_move_rcs, move_rs=move_dict['move'])
                        
                        if dict_label_qty:
                            move_label_obj.create_move_label(dict_label_qty.keys()[0], move_rs=move_dict['move'], dict_label_qty=dict_label_qty)
                        
                        if move_to_done:
                            sec_qty_factor = move_to_done.sec_uom_qty / (move_to_done.uom_qty or 1.0)
                            uoi_qty_factor = move_to_done.uoi_qty / (move_to_done.uom_qty or 1.0)
                            if move_to_done.uom_id and move_to_done.product_id and move_to_done.product_id.uom_id \
                               and move_to_done.uom_id.id != move_to_done.product_id.uom_id.id \
                               and move_to_done.uom_id.category_id.id == move_to_done.product_id.uom_id.category_id.id:
                                need_convert = True
                            else: 
                                need_convert = False
                                
                            # On calcule la somme des étiquettes
                            total_qty = 0.0
                            total_sec_qty = 0.0
                            total_uoi_qty = 0.0
                            for label in move_to_done.move_label_ids:
                                if need_convert:
                                    qty = uom_obj._compute_qty_obj(label.uom_id, label.uom_qty, move_to_done.uom_id)
                                else:
                                    qty = label.uom_qty
                                
                                total_qty += qty
                                total_sec_qty += qty * sec_qty_factor
                                total_uoi_qty += qty * uoi_qty_factor
                            
                            # On compare la quantité des étiquette et celle du mouvement
                            # Si elle est supérieur ou égale on écrit la quantité dans le mouvement
                            if move_to_done.uom_qty <= total_qty:
                                move_to_done.write({'uom_qty': total_qty,
                                                    'sec_uom_qty': total_sec_qty,
                                                    'uoi_qty': total_uoi_qty})
                            # Si non split le mouvement afin que l'on ne consomme pas moins que ce qui est prévue
                            else:
                                move_dic = move_to_done.split_light(move_to_done.uom_qty/total_qty)
                                move_to_done = move_dic['move_rcs']
                                move_dic['new_move_rcs'].wkf_cancel()
                            
                            # Déclaration de la consommation
                            first_resource_id = move_to_done.wo_incoming_id.first_resource_id and move_to_done.wo_incoming_id.first_resource_id.id or False
                            vals = {
                                'wo_id': move_to_done.wo_incoming_id.id,
                                'user_id': self.env.user.id,
                                'uom_id': move_to_done.wo_incoming_id.uom_id.id,
                                'product_id': move_to_done.wo_incoming_id.final_product_id.id,
                                'quantity': wo_qty_decla,
                                'type': 'consumption',
                                'date': fields.Datetime.now(),
                                'first_resource_id': first_resource_id
                            }
                            wdm_rcs = self.env['wo.declaration.main'].create(vals)
                            wdc_rcs = wdm_rcs.create_declaration_consumption_move(move_to_done)
                            wdc_rcs.action_validate_comsuption(no_return_view=True)

                    if move_to_cancel_rcs:
                        move_to_cancel_rcs.wkf_cancel()
                
        return True
    
    
    