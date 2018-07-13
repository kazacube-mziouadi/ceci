# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
import time, datetime
import openerp.addons.decimal_precision as dp
from decimal import Decimal

class wo_declaration_main(models.TransientModel):
    """ 
        WorkOrder Declaration Main
    """
    _name = 'wo.declaration.main'
    _description = 'WorkOrder Declaration Main'
    _rec_name = 'wo_id'
    
    @api.model
    def default_get(self, fields_list):
        res = super(wo_declaration_main, self).default_get(fields_list=fields_list)
        wo_obj = self.env['mrp.workorder']
        #Fonction permettant de passer par défaut l'id de l'OT ouvert
        if self.env.context.get('active_model') == 'mrp.workorder':
            wo = wo_obj.browse(self.env.context.get('active_id'))
            # Calcul de la quantité restante
            quantity = wo.quantity
            if wo.mo_id.is_disassembly:
                for consumption in wo.workorder_consumption_ids:
                    if consumption.state == 'done':
                        quantity -= consumption.quantity
            else:
                for produce in wo.workorder_produce_ids:
                    if produce.state == 'done':
                        quantity -= produce.qty_ok
            
            first_resource_id = wo.first_resource_id and wo.first_resource_id.id or False
            vals = {
                'wo_id': wo.id,
                'user_id': self.env.user.id,
                'uom_id': wo.uom_id.id,
                'product_id': self.wo_id.final_product_id.id,
                'quantity': quantity,
                'first_resource_id': first_resource_id
            }
            res.update(vals)
            
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    @api.model
    def _type_get(self):
        return [
                ('consumption', _('Consumption')),
                ('produce', _('Produce')),
                ('cons_prod', _('Consumption & Produce')),
                       ]
    
    
    @api.one
    @api.depends('wo_id')
    def _compute_wo(self):
        """
            Fonction qui récupère le produit et l'UdM dans l'OT
        """
        self.product_id = self.wo_id and self.wo_id.final_product_id or False
        self.uom_id = self.wo_id and self.wo_id.uom_id or False
        
    
    wo_id = fields.Many2one('mrp.workorder', string='WorkOrder', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='cascade', default=lambda self: self.env.uid)
    uom_id = fields.Many2one('product.uom', string='UoM', required=False, ondelete='cascade', compute='_compute_wo')
    product_id = fields.Many2one('product.product', string='Product', compute='_compute_wo')
    quantity = fields.Float(string='Quantity', required=True, digits=dp.get_precision('Product quantity'))
    type = fields.Selection('_type_get', string='Type', required=True)
    date = fields.Datetime(string='Date of declaration', required=True, default=lambda self: fields.Datetime.now())
    first_resource_id = fields.Many2one('mrp.resource', string='First resource')
    is_simple_declaration = fields.Boolean(string='Simple declaration', default=False)
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('wo_id')
    def _onchange_wo_id(self):
        """
            Au changement de l'ot
        """
        self.first_resource_id = self.wo_id and self.wo_id.first_resource_id and self.wo_id.first_resource_id.id or False



#     @api.onchange('type')
#     def _onchange_type(self):
#         """
#             Au changement du produit, changement de la catégorie de l'uom
#         """
#         quantity = self.wo_id.quantity
#         if self.type == 'consumption':
#             for consumption in self.wo_id.workorder_consumption_ids:
#                 if consumption.state == 'done':
#                     quantity -= consumption.quantity
#                     
#         else:
#             for produce in self.wo_id.workorder_produce_ids:
#                 if produce.state == 'done':
#                     quantity -= produce.qty_ok
#         
#         self.quantity = quantity

    
    #===========================================================================
    # Bouton
    #===========================================================================
    @api.multi
    def action_validate(self):
        """
            Lancement du wizard de conso ou de production en fonction du choix
        """
        res = False
        for wiz in self:
            if wiz.wo_id.state in ('draft', 'waiting', 'cancel'):
                raise except_orm('Error', 'it is not possible to make declaration if the state is draft or waiting or cancel')
            
            qty_max = wiz.wo_id.quantity
            for produce in wiz.wo_id.workorder_produce_ids:
                if produce.state == 'done':
                    qty_max -= produce.qty_ok
            
            if Decimal(str(wiz.quantity)) > Decimal(str(qty_max)) and not wiz.wo_id.produce_more:
                raise except_orm('Error', 'You can not declare more than %f.'%(qty_max))
            
            if qty_max < 0:
                qty_max = 0

            if wiz.type == 'produce':
                action_name = 'act_wo_declaration_produce_form'
                conso_or_prod_rcs = self.create_declaration_produce()
            else:
                action_name = 'act_wo_declaration_consumption_form'
                conso_or_prod_rcs = self.create_declaration_consumption()

            # Retour de la vue
            data_pool = self.env['ir.model.data']
            action_model, action_id = data_pool.get_object_reference('mrp', action_name)
            # Puis on va passer l'id à la vue pour pouvoir l'afficher dans la vue form
            if action_model:
                action_pool = self.env[action_model]
                if wiz.type == 'produce':
                    action = action_pool.with_context(first_product=conso_or_prod_rcs.product_id.id).browse(action_id).read()[0]
                    action['context'] = "{'first_product':%s}" % (conso_or_prod_rcs.product_id.id,)
                else:
                    action = action_pool.browse(action_id).read()[0]
                action['res_id'] = conso_or_prod_rcs.id
                res = action
                
            return res
                
                
    def create_declaration_consumption(self):
        """ 
            Fonction qui crée la déclaration de consommation
            return le recordset
        """
        consum_obj = self.env['wo.declaration.consumption']
        val_consum = {
            'declaration_id': self.id,
            'wo_id': self.wo_id.id,
            'quantity': self.quantity,
            'date': self.date,
            'first_resource_id': self.first_resource_id and self.first_resource_id.id or False,
            'is_labels': False,
        }
        
        if self.type == 'cons_prod':
            val_consum['is_produce'] = True
        else:
            val_consum['is_produce'] = False
        
        list_consumption_line = []
        for rm in self.wo_id.rm_draft_ids:
            track_label = rm.product_id.track_label and not self.wo_id.is_subcontracting or False
            track_out_lot = rm.product_id.track_out_lot and not self.wo_id.is_subcontracting or False
            if rm.type_qty == 'variable':
                quantity_draft = rm.efficient_unit_qty * self.quantity
            else:
                quantity_draft = rm.uom_qty
            
            is_variable_double_unit = False
            if track_label and rm.product_id.dual_unit and rm.product_id.dual_unit_type == 'variable':
                is_variable_double_unit = True
            
            if track_label:
                val_consum['is_labels'] = True
            
            vals_line = {
                'quantity': quantity_draft,
                'product_id': rm.product_id.id,
                'move_id': rm.id,
                'is_variable_double_unit': rm.is_variable_double_unit,
                'track_label': track_label,
                'track_out_lot': track_out_lot,
                'is_variable_double_unit': is_variable_double_unit,
            }
            if self.is_simple_declaration and rm.product_id and not rm.product_id.track_label and not rm.product_id.track_out_lot:
                vals_line['is_invisible'] = True
            else:
                vals_line['is_invisible'] =  False
                
            list_consumption_line.append((0, 0, vals_line))
        
        if list_consumption_line:
            val_consum['line_ids'] = list_consumption_line
        
        consum_rcs = consum_obj.create(val_consum)
        # Partie déclaration 
        # Etiquettes déjà déclaré dans les mouvements
        label_consumption_obj = self.env['assign.label.wo.consumption']
        label_consumption_line_obj = self.env['assign.label.wo.consumption.line']
        uom_obj = self.env['product.uom']
        dico_consupline_qty_label = {}
        for consumption_line in consum_rcs.line_ids:
            if consumption_line.track_label:
                if consumption_line.move_id and consumption_line.move_id.move_label_ids:
                    if consumption_line.label_consumption_ids:
                        label_consumption_rcs = consumption_line.label_consumption_ids
                    else:
                        label_consumption_rcs = label_consumption_obj.create({'consumption_line_id': consumption_line.id})
                    
                    qty_total_label = 0
                    sec_qty_total_label = 0
                    sec_uom_id = consumption_line.sec_uom_id and consumption_line.sec_uom_id.id or False
                    for move_label in consumption_line.move_id.move_label_ids:
                        label = move_label.label_id
                        if label:
                            qty_init = uom_obj._compute_qty_obj(label.uom_id, label.uom_qty, consumption_line.uom_id, with_raise=False, with_round=False)
                            qty = uom_obj._compute_qty_obj(move_label.uom_id, move_label.uom_qty, consumption_line.uom_id, with_raise=False, with_round=False)
                            sec_qty_init = uom_obj._compute_qty_obj(label.sec_uom_id, label.sec_uom_qty, consumption_line.sec_uom_id, with_raise=False, with_round=False)
                            sec_qty = uom_obj._compute_qty_obj(move_label.sec_uom_id, move_label.sec_uom_qty, consumption_line.sec_uom_id, with_raise=False, with_round=False)
                            if label.template_id.is_theorical_comuption:
                                if consumption_line.quantity >= (qty_total_label + qty):
                                    qty_total_label += qty
                                else:
                                    qty = consumption_line.quantity - qty_total_label
                                    qty_total_label += qty
                                
                                if consumption_line.sec_uom_qty >= (sec_qty_total_label + sec_qty):
                                    sec_qty_total_label += sec_qty
                                else:
                                    sec_qty = consumption_line.sec_uom_qty - sec_qty_total_label
                                    sec_qty_total_label += qty
                                
                            vals = {
                               'consumption_line_id': consumption_line.id,
                               'label_consumption_id': label_consumption_rcs.id,
                               'label_id': label.id,
                               'quantity_init_inv': qty_init,
                               'is_variable_double_unit': label.is_variable_double_unit,
                               'quantity': qty,
                               'sec_uom_qty': sec_qty,
                               'sec_uom_id': sec_uom_id,
                               'sec_quantity_init': sec_qty_init,
                                }
                            label_consumption_line_obj.create(vals)
                    
                    dico_consupline_qty_label[consumption_line] = {'uom_qty': qty_total_label, 'sec_uom_qty': sec_qty_total_label}
        
        # Etiquettes consommées non utilisées de l'OT (onglet déclaration)
        for label_consumed in self.wo_id.label_consumed_ids:
            consumption_line_rcs = False
            for consumption_line in consum_rcs.line_ids:
                if consumption_line.product_id == label_consumed.product_id:
                    consumption_line_rcs = consumption_line
                    break
                    
            if label_consumed.quantity and not label_consumed.is_declared and consumption_line_rcs and label_consumed.use_consumption:
                if consumption_line_rcs.label_consumption_ids:
                    label_consumption_rcs = consumption_line_rcs.label_consumption_ids
                else:
                    label_consumption_rcs = label_consumption_obj.create({'consumption_line_id': consumption_line_rcs.id})
                
                label_consumption_line_obj.create_consumption_line(label_consumed.label_id, consumption_line_rcs, label_consumption_rcs, 
                                                                   qty_default=label_consumed.quantity, dico_consupline_qty_label=dico_consupline_qty_label) 

        return consum_rcs
    
    @api.multi
    def get_product_produce(self):
        # point d'entrée pour module cedre
        return self.product_id
    
    @api.multi
    def get_quantity_for_product(self, product):
        # point d'entrée pour module cedre
        return self.quantity
    
    @api.multi
    def get_uom_for_product(self, product):
        try:
            return next(x for x in self.wo_id.fp_draft_ids if x.product_id.is_int or x.product_id == product).uom_id
        except StopIteration:
            return product.uom_id
    
    @api.multi
    def get_other_data(self, product_id):
        return {}
    
    
    def create_declaration_consumption_move(self, move_rcs):
        """ 
            Fonction qui crée la déclaration de consommation
            return le recordset
        """
        consum_obj = self.env['wo.declaration.consumption']
        val_consum = {
            'declaration_id': self.id,
            'wo_id': self.wo_id.id,
            'quantity': self.quantity,
            'date': self.date
        }
        
        if self.type == 'cons_prod':
            val_consum['is_produce'] = True
        else:
            val_consum['is_produce'] = False
        
        list_consumption_line = []
        for rm in move_rcs:
            track_label = rm.product_id.track_label and not self.wo_id.is_subcontracting or False
            track_out_lot = rm.product_id.track_out_lot and not self.wo_id.is_subcontracting or False
            quantity_draft = rm.uom_qty
            
            is_variable_double_unit = False
            if track_label and rm.product_id.dual_unit and rm.product_id.dual_unit_type == 'variable':
                is_variable_double_unit = True
            
            vals_line = {
                'quantity': quantity_draft,
                'product_id': rm.product_id.id,
                'move_id': rm.id,
                'is_variable_double_unit': rm.is_variable_double_unit,
                'track_label': track_label,
                'track_out_lot': track_out_lot,
                'is_variable_double_unit': is_variable_double_unit,
            }
            list_consumption_line.append((0, 0, vals_line))
        
        if list_consumption_line:
            val_consum['line_ids'] = list_consumption_line
        
        consum_rcs = consum_obj.create(val_consum)
        # Partie déclaration 
        # Etiquettes déjà déclaré dans les mouvements
        label_consumption_obj = self.env['assign.label.wo.consumption']
        label_consumption_line_obj = self.env['assign.label.wo.consumption.line']
        uom_obj = self.env['product.uom']
        dico_consupline_qty_label = {}
        for consumption_line in consum_rcs.line_ids:
            if consumption_line.track_label:
                if consumption_line.move_id and consumption_line.move_id.move_label_ids:
                    if consumption_line.label_consumption_ids:
                        label_consumption_rcs = consumption_line.label_consumption_ids
                    else:
                        label_consumption_rcs = label_consumption_obj.create({'consumption_line_id': consumption_line.id})
                    
                    qty_total_label = 0
                    sec_qty_total_label = 0
                    sec_uom_id = consumption_line.sec_uom_id and consumption_line.sec_uom_id.id or False
                    for move_label in consumption_line.move_id.move_label_ids:
                        label = move_label.label_id
                        if label:
                            qty_init = uom_obj._compute_qty_obj(label.uom_id, label.uom_qty, consumption_line.uom_id, with_raise=False, with_round=False)
                            qty = uom_obj._compute_qty_obj(move_label.uom_id, move_label.uom_qty, consumption_line.uom_id, with_raise=False, with_round=False)
                            sec_qty_init = uom_obj._compute_qty_obj(label.sec_uom_id, label.sec_uom_qty, consumption_line.sec_uom_id, with_raise=False, with_round=False)
                            sec_qty = uom_obj._compute_qty_obj(move_label.sec_uom_id, move_label.sec_uom_qty, consumption_line.sec_uom_id, with_raise=False, with_round=False)
                            if label.template_id.is_theorical_comuption:
                                if consumption_line.quantity >= (qty_total_label + qty):
                                    qty_total_label += qty
                                else:
                                    qty = consumption_line.quantity - qty_total_label
                                    qty_total_label += qty
                                
                                if consumption_line.sec_uom_qty >= (sec_qty_total_label + sec_qty):
                                    sec_qty_total_label += sec_qty
                                else:
                                    sec_qty = consumption_line.sec_uom_qty - sec_qty_total_label
                                    sec_qty_total_label += qty
                                
                            vals = {
                               'consumption_line_id': consumption_line.id,
                               'label_consumption_id': label_consumption_rcs.id,
                               'label_id': label.id,
                               'quantity_init_inv': qty_init,
                               'is_variable_double_unit': label.is_variable_double_unit,
                               'quantity': qty,
                               'sec_uom_qty': sec_qty,
                               'sec_uom_id': sec_uom_id,
                               'sec_quantity_init': sec_qty_init,
                                }
                            label_consumption_line_obj.create(vals)
                    
                    dico_consupline_qty_label[consumption_line] = {'uom_qty': qty_total_label, 'sec_uom_qty': sec_qty_total_label}

        return consum_rcs
    
    
    
    
    def create_declaration_produce(self, consumption_id=None):
        """ 
            Fonction qui crée la déclaration de production
            return le recordset
        """
        produce_obj = self.env['wo.declaration.produce']
        qcp_obj = self.env['quality.control.product']
        label_mo_repair_id = self.wo_id.label_mo_repair_id and self.wo_id.label_mo_repair_id.id or False
        product_id = self.get_product_produce()
        qty = self.get_quantity_for_product(product_id)
        val_produce = {
            'declaration_id': self.id,
            'wo_id': self.wo_id.id,
            'quantity': qty,
            'qty_hs': 0.0,
            'qty_ok' : qty,
            'uom_id': self.get_uom_for_product(product_id).id,
            'label_template_id': product_id.label_template_id.id,
            'is_variable_double_unit': product_id.dual_unit and product_id.dual_unit_type == 'variable' or False,
            'label_mo_repair_id': label_mo_repair_id,
            'date': self.date,
            'first_resource_id': self.first_resource_id and self.first_resource_id.id or False,
        }
        val_produce.update(self.get_other_data(product_id))
        if consumption_id:
            val_produce['consumption_id'] = consumption_id
            
        move_id = False
        move_rcs = False
        # Si c'est le dernier OT de l'OF, déclaration du produit final
        last_wo = False
        if not self.wo_id.next_wo_ids:
            last_wo = True
        else:
            last_wo = True
            for next_wo in self.wo_id.next_wo_ids:
                if next_wo.mo_id.id == self.wo_id.mo_id.id:
                    last_wo = False
                    break
                 
        
        track_label = product_id.track_label and self.wo_id and not self.wo_id.is_subcontracting or False
        new_auto_lot = product_id.track_label and self.wo_id and not self.wo_id.is_subcontracting or False
        val_produce['product_id'] = product_id.id
        val_produce['is_expiry_date'] = False
        if product_id.is_expiry_date and product_id.expiry_type == 'manual':
            val_produce['is_expiry_date'] = True
            
        val_produce['track_label'] = track_label
        val_produce['new_auto_lot'] = new_auto_lot
        for fp in self.wo_id.fp_draft_ids:
            if fp.product_id.id == product_id.id:
                move_id = fp.id
                move_rcs = fp
                break
        # Si ce n'est pas le dernier OT, déclaration du produit intermédiaire
        if not last_wo and not move_id:
            for fp in self.wo_id.fp_draft_ids:
                product = fp.product_id.read(['is_int'])[0]
                if product['is_int']:
                    val_produce['product_id'] = product['id']
                    val_produce['track_label'] = False
                    val_produce['is_expiry_date'] = False
                    val_produce['is_variable_double_unit'] = False
                    move_id = fp.id
                    move_rcs = fp
                    break
        
        if move_id:
            val_produce['move_id'] = move_id
        elif self.wo_id.produce_more:
            pass
        else:
            raise except_orm('Error', 'There is not move.')
        
        val_produce['is_control_declaration'] = False
        if last_wo:
            dict_control = qcp_obj.search([('type', 'in', ('intern', 'all')), ('product_id', '=', product_id.id)], limit=1)
            if not dict_control:
                dict_control = qcp_obj.search([('type', 'in', ('intern', 'all')), ('routing_line_id', '=', self.wo_id.routing_line_id.id)], limit=1)
                if dict_control:
                    val_produce['quality_rl'] = True
        
        else:
            dict_control = qcp_obj.search([('type', 'in', ('intern', 'all')), ('routing_line_id', '=', self.wo_id.routing_line_id.id)], limit=1)
            if dict_control:
                val_produce['quality_rl'] = True
        
        if dict_control:
            val_produce['is_control_declaration'] = True
            if move_rcs and move_rcs.control_declaration_id:
                val_produce['control_declaration_id'] = move_rcs.control_declaration_id.id
                val_produce['qty_hs'] = move_rcs.control_declaration_id.qty_hs
                val_produce['qty_ok'] = move_rcs.control_declaration_id.qty_ok
                val_produce['qty_quarantine'] = move_rcs.control_declaration_id.qty_quarantine
                
        produce_rcs = produce_obj.create(val_produce)
        
        label_produce_obj = self.env['assign.label.wo.produce']
        for label_production in produce_rcs.wo_id.label_production_ids:
            if not label_production.is_declared and label_production.product_id == self.product_id:
                label_produce_vals = {'consumption_line_id': produce_rcs.id,
                                      'label_id': label_production.label_id.id,
                                      'uom_id': label_production.label_id.uom_id.id,
                                      'quantity': label_production.quantity_label}
                if label_production.label_id.is_before_create:
                    label_produce_vals['is_no_modif_qty'] = True
                    if label_production.label_id.is_before_create:
                        label_produce_vals['quantity'] = label_production.label_id.printed_qty
                    
                label_produce_obj.create(label_produce_vals)
               
        if move_rcs and move_rcs.track_label_product and move_rcs.move_label_ids:
            if self.should_create_consumption_lines():
                for move_label in move_rcs.move_label_ids:
                    label_produce_vals = {'consumption_line_id': produce_rcs.id,
                                          'label_id': move_label.label_id.id,
                                          'uom_id': move_label.label_id.uom_id.id,
                                          'quantity': move_label.uom_qty}
                    label_produce_obj.create(label_produce_vals)
                
        return produce_rcs
    
    @api.model
    def should_create_consumption_lines(self):
        return True
    
    @api.model
    def create_and_produce(self, wo_id):
        main_id = self.create({
                     'wo_id': wo_id,
                     'type':'produce',
                     'user_id':self.env.uid,
                     })
        quantity = main_id.wo_id.quantity
        if main_id.type == 'consumption':
            for consumption in main_id.wo_id.workorder_consumption_ids:
                if consumption.state == 'done':
                    quantity -= consumption.quantity
                     
        else:
            for produce in main_id.wo_id.workorder_produce_ids:
                if produce.state == 'done':
                    quantity -= produce.qty_ok
         
        main_id.quantity = quantity
        res = main_id.action_validate()
        return res['res_id']
    
    
   
class wo_declaration_consumption(models.TransientModel):
    """ 
        WorkOrder Declaration Consumption
    """
    _name = 'wo.declaration.consumption'
    _description = 'WorkOrder Declaration Consumption'
    _rec_name = 'wo_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    declaration_id = fields.Many2one('wo.declaration.main', string='Main', required=False, ondelete='cascade')
    wo_id = fields.Many2one('mrp.workorder', string='WorkOrder', required=True, ondelete='cascade')
    line_ids = fields.One2many('wo.declaration.consumption.line', 'declaration_consumption_id',  string='Lines', domain=[('is_invisible', '!=', True)])
    is_produce = fields.Boolean(string='Produce', default=False)
    quantity = fields.Float(string='Quantity', default=0.0, required=False, digits=dp.get_precision('Product quantity'))
    date = fields.Datetime(string='Date of declaration')
    first_resource_id = fields.Many2one('mrp.resource', string='First resource')
    labels_names = fields.Text(string='Label names')
    is_labels = fields.Boolean(string='Labels', default=False)
    #===========================================================================
    # Bouton
    #===========================================================================
    @api.multi
    def action_validate(self):
        """
            Validation du wizard de consommation
        """
        for wiz in self:
            # Si consommation et production
            if wiz.is_produce:
                produce_rcs = wiz.declaration_id.create_declaration_produce(consumption_id=wiz.id)
                # Retour de la vue
                action_model, action_id = self.env['ir.model.data'].get_object_reference('mrp', 'act_wo_declaration_produce_form')
                #Puis on va passer l'id à la vue pour pouvoir l'afficher dans la vue form
                if action_model:
                    action = self.env[action_model].browse(action_id).read()[0]
                    action['res_id'] = produce_rcs.id
                    res = action
                    return res
            # Si que consommation
            else:
                res = wiz.action_validate_comsuption(no_return_view=True, vals_wo_comsumption_data=False)
                
        return res
    
    
    def action_validate_comsuption(self, no_return_view=False, vals_wo_comsumption_data=False):
        """ 
            Validation de la consommation
        """
        date_stpr = datetime.datetime.strptime(self.date, '%Y-%m-%d %H:%M:%S')
        date_diff = (date_stpr - datetime.timedelta(0, 1)).strftime("%Y-%m-%d %H:%M:%S")
        consum_line_obj = self.env['wo.declaration.consumption.line']
        wo_consumption_obj = self.env['mrp.wo.consumption']
        uom_obj = self.env['product.uom']
        move_lot_obj = self.env['stock.move.lot']
        wiz = self
        ctx = self.env.context.copy()
        ctx.update(force_done=wiz.wo_id.availability_force)
        if wiz.wo_id.state in ('draft', 'waiting', 'cancel'):
            raise except_orm(_('Error'), _('It is not possible to make declaration if the state is draft or waiting or cancel'))
        
        # On recherche toutes les lignes qui ne sont pas des labels
        line_rcs = consum_line_obj.search([('declaration_consumption_id', '=', wiz.id)])
        if line_rcs:
            move_ids = self.env['stock.move']
            new_move_ids = self.env['stock.move']
            # On boucle sur les lignes
            for line in line_rcs:
                move_ids += line.move_id
                move_qty = line.move_id.uom_qty
                move_sec_qty = line.move_id.sec_uom_qty
                label_qty = 0.0
                dict_label_qty = {}
                label_ids = self.env['stock.label']
                # Calcule du pourcentage de production
                # TODO THOMAS: normal que ce calcul soit dans la boucle alors qu'il ne dépend que du WO?
                availability = wiz.wo_id.compute_availability(is_availability_force=True)
                if availability < 100:
                    if line.quantity > line.product_id.available_stock and not wiz.wo_id.is_subcontracting:
                        raise except_orm('Error', 'The %s product is not available (in covered by stock %f).'%(line.product_id.name, line.product_id.available_stock))
                    elif line.quantity > line.move_id.covered_by_stock_qty and wiz.wo_id.is_subcontracting:
                        raise except_orm('Error', 'The %s product is not available (in covered by stock %f).'%(line.product_id.name, line.move_id.covered_by_stock_qty))
                
                # Si la ligne est un produit qui doit être suivi par les étiquettes
                if line.track_label:
                    line.move_id.move_label_ids.unlink()
                    if line._compute_sum_label_qtys()[0] == 0:
                        raise except_orm('Error', 'you should declare labels for the product %s'%(line.product_id.name))
                    
                    # On récupère toutes les affectations d'étiquettes faites précédement 
                    for label_consumption in line.label_consumption_ids:
                        for label_consumption_line in label_consumption.line_ids:
                            # Teste si la quantité est supérieur à l'étiquette   
                            if label_consumption_line.quantity_init < label_consumption_line.quantity:
                                raise except_orm('Error', 'The quantity can not exceed that of the label (%s %f)'%(label_consumption_line.label_id.name, label_consumption_line.quantity_init))
                            
                            # Gestion du reste de l'etiquette si l'on n'utilise pas tout
                            if label_consumption_line.label_id in dict_label_qty:
                                raise except_orm('Error', 'Label already used %s'%(label_consumption_line.label_id.name))
                            else:
                                dict_label_qty[label_consumption_line.label_id] = (label_consumption_line.quantity, label_consumption_line.sec_uom_qty)
                                label_ids |= label_consumption_line.label_id
                                
                            label_qty += uom_obj._compute_qty_obj(label_consumption_line.label_id.uom_id, label_consumption_line.quantity, line.move_id.uom_id, with_raise=False, with_round=False)

                    # On lie les étiquettes aux mouvements
                    if dict_label_qty:
                        line.move_id.with_context({'wkf_reserved_from_consumtion': True, 'label_move_done_date': date_diff}).assign_label(label_ids, dict_label_qty=dict_label_qty, with_write=True)
                        
                else:
                    # Si la quantité n'est pas égale à la quantité du mouvement on fait un reliquat du reste
                    new_move = wiz.wo_id.modif_move_or_scrap(line.move_id, move_qty, line.quantity, move_sec_qty, line.sec_uom_qty, line.is_variable_double_unit)
                    if new_move:
                        new_move_ids += new_move
                
                if line.track_out_lot and line.lot_id and line.move_id:
                    line.move_id.move_lot_ids.unlink()
                    move_lot_obj.create({
                        'move_id': line.move_id.id,
                        'lot_id': line.lot_id.id
                    })
                    
            # On prépare la création d'une ligne dans le tableau des OTs de consommations
            vals_wo_comsumption = {
                'wo_id': wiz.wo_id.id,
                'date': self.date,
                'quantity': wiz.quantity,
                'uom_id': wiz.declaration_id.uom_id.id,
                'first_resource_id': self.first_resource_id and self.first_resource_id.id or False,
            } 
            if vals_wo_comsumption_data:
                vals_wo_comsumption.update(vals_wo_comsumption_data)
                
            wo_consumption = wo_consumption_obj.create(vals_wo_comsumption)
            # On lie les mouvements à la déclaration
            move_ids.write({'wo_consumption_id': wo_consumption.id, 'done_date': self.date})
            # On valides les mouvements
            move_ids.with_context(ctx).wkf_done()
#             move_ids.write({'date_expected': self.date, 'date': self.date, 'priority_date': self.date})
            # On passe les reliquats à en attente
            if new_move_ids:
                new_move_ids.wkf_waiting()
        
        if wiz.is_produce:
            produce_rcs = wiz.declaration_id.create_declaration_produce()
            if no_return_view:
                return produce_rcs
            else:
                # Retour de la vue
                data_pool = self.env['ir.model.data']
                action_model, action_id = data_pool.get_object_reference('mrp', 'act_wo_declaration_produce_form')
                #Puis on va passer l'id à la vue pour pouvoir l'afficher dans la vue form
                if action_model:
                    action_pool = self.env[action_model]
                    action = action_pool.browse(action_id).read()[0]
                    action['res_id'] = produce_rcs.id
                    res = action
                    return res
                
        return True
    
    
    @api.multi
    def action_validate_scanne(self):
        label_consumption_obj = self.env['assign.label.wo.consumption']
        label_consumption_line_obj = self.env['assign.label.wo.consumption.line']
        for wiz in self:
            if wiz.labels_names:
                if '\n' in wiz.labels_names:
                    labels_names_list = wiz.labels_names.split('\n')
                elif ',' in wiz.labels_names:
                    labels_names_list = wiz.labels_names.split(',')
                else:
                    labels_names_list = [wiz.labels_names]
                
                label_rcs = self.env['stock.label'].search([('name', 'in', labels_names_list)])
                if label_rcs:
                    dic_product_labes = {}
                    for label in label_rcs:
                        if label.product_id not in dic_product_labes:
                            dic_product_labes[label.product_id] = self.env['stock.label']
                        
                        dic_product_labes[label.product_id] += label
                        
                    for consumption_line in wiz.line_ids:
                        if consumption_line.product_id in dic_product_labes:
                            if consumption_line.label_consumption_ids:
                                label_consumption_rcs = consumption_line.label_consumption_ids
                            else:
                                label_consumption_rcs = label_consumption_obj.create({'consumption_line_id': consumption_line.id})
                            
                            qty_total_label = 0
                            sec_qty_total_label = 0
                            sec_uom_id = consumption_line.sec_uom_id and consumption_line.sec_uom_id.id or False
                            label_existing_ids = [x.label_id.id for x in label_consumption_rcs.line_ids if x.label_id]
                            for label in dic_product_labes[consumption_line.product_id]:
                                if label and label.id not in label_existing_ids:
                                    qty_init = label.uom_qty
                                    qty = label.uom_qty
                                    sec_qty_init = label.sec_uom_qty
                                    sec_qty = label.sec_uom_qty
                                    if label.template_id.is_theorical_comuption:
                                        if consumption_line.quantity >= (qty_total_label + qty):
                                            qty_total_label += qty
                                        else:
                                            qty = consumption_line.quantity - qty_total_label
                                            qty_total_label += qty
                                        
                                        if consumption_line.sec_uom_qty >= (sec_qty_total_label + sec_qty):
                                            sec_qty_total_label += sec_qty
                                        else:
                                            sec_qty = consumption_line.sec_uom_qty - sec_qty_total_label
                                            sec_qty_total_label += qty
                                        
                                    vals = {
                                       'consumption_line_id': consumption_line.id,
                                       'label_consumption_id': label_consumption_rcs.id,
                                       'label_id': label.id,
                                       'quantity_init_inv': qty_init,
                                       'is_variable_double_unit': label.is_variable_double_unit,
                                       'quantity': qty,
                                       'sec_uom_qty': sec_qty,
                                       'sec_uom_id': sec_uom_id,
                                       'sec_quantity_init': sec_qty_init,
                                        }
                                    label_consumption_line_obj.create(vals)
                                    label_existing_ids.append(label.id)
                                    
        
        return {'type':'ir.actions.act_window_dialog_reload'}
        
        

class wo_declaration_consumption_line(models.TransientModel):
    """ 
        WorkOrder Declaration Consumption Line
    """
    _name = 'wo.declaration.consumption.line'
    _description = 'WorkOrder Declaration Consumption Line'
    _rec_name = 'product_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    @api.one
    def _compute_move(self):
        """
            Fonction qui récupère l'UdM dans le mouvement
        """
        self.uom_id = self.move_id and self.move_id.uom_id or False
        self.sec_uom_id = self.move_id.sec_uom_id or False
    
    
    @api.one
    @api.depends('track_label', 'quantity', 'declaration_consumption_id.line_ids', 'declaration_consumption_id.line_ids.track_label', 
                  'declaration_consumption_id.line_ids.quantity')
    def _compute_qty(self):
        """
            Fonction qui la somme des étiquettes pour un produit
        """
        self.label_qty, self.sec_label_qty = self._compute_sum_label_qtys()
        
        
    declaration_consumption_id = fields.Many2one('wo.declaration.consumption', string='Consumption', required=False, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    quantity = fields.Float(string='Quantity (UoM)', required=True, digits=dp.get_precision('Product quantity'))
    uom_id = fields.Many2one('product.uom', string='UoM', required=False, ondelete='cascade', compute='_compute_move')
    sec_uom_qty = fields.Float(string='Quantity (Sec. UoM)', required=True, default=0.0, digits=dp.get_precision('Product quantity'))
    sec_uom_id = fields.Many2one('product.uom', string='Sec. UoM', required=False, ondelete='cascade', compute='_compute_move')
    move_id = fields.Many2one('stock.move', string='Move', required=False, ondelete='cascade')
    parent_id = fields.Many2one('wo.declaration.consumption.line', string='Parent', required=False, ondelete='cascade')
    track_label = fields.Boolean(string='Track Label', default=False)
    track_out_lot = fields.Boolean(default=False)
    lot_id = fields.Many2one('stock.lot', string='Lot', required=False, ondelete='cascade')
    label_qty = fields.Float(string='Label Quantity', compute='_compute_qty', digits=dp.get_precision('Product quantity'))
    sec_label_qty = fields.Float(string='Label quantity (sec. UoM)', compute='_compute_qty', digits=dp.get_precision('Product quantity'))
    label_qty_init = fields.Float(string='Quantity', digits=dp.get_precision('Product quantity') )
    label_consumption_ids = fields.One2many('assign.label.wo.consumption', 'consumption_line_id',  string='Consumption line')
    is_variable_double_unit = fields.Boolean(default=False)
    is_invisible = fields.Boolean(string='Invisible', default=False)
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
            Au changement du produit, changement de la catégorie de l'uom
        """
        self.track_label = self.product_id and self.product_id.track_label and self.declaration_consumption_id.wo_id and self.declaration_consumption_id.wo_id.is_subcontracting == False or False
        self.track_out_lot = self.product_id and self.product_id.track_out_lot and self.declaration_consumption_id.wo_id and self.declaration_consumption_id.wo_id.is_subcontracting == False or False
    
    
    #===========================================================================
    # Fonctions
    #===========================================================================
    def _compute_sum_label_qtys(self):
        label_qty = 0.0
        sec_label_qty = 0.0
        uom_obj = self.env['product.uom']
        if self.track_label:
            for label_consumption in self.label_consumption_ids:
                for label_consumption_line in label_consumption.line_ids:
                    label_qty += uom_obj._compute_qty_obj(label_consumption_line.label_id.uom_id, label_consumption_line.quantity, self.uom_id, with_raise=False, with_round=False)
                    sec_label_qty += uom_obj._compute_qty_obj(label_consumption_line.label_id.sec_uom_id, label_consumption_line.sec_uom_qty, self.sec_uom_id, with_raise=False, with_round=False)
                    
        return label_qty, sec_label_qty
    
    #===========================================================================
    # Button
    #===========================================================================
    @api.multi
    def button_modif_assign_label_wo_consumption_form(self):
        for wiz in self:
            if wiz.label_consumption_ids:
                res_id = wiz.label_consumption_ids.id
            else:
                res_id = False
                
            return {
                    'name': _('Assign label'),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'assign.label.wo.consumption',
                    'type': 'ir.actions.act_window',
                    'target': 'stack',
                    'res_id': res_id,
                    'nodestroy': True,
                    }
        
        
        return True 
    
    
    @api.multi
    def button_add_assign_label_wo_consumption_form(self):
        for wiz in self:
            return {
                    'name': _('Labels'),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'assign.add.label.wo.consumption',
                    'type': 'ir.actions.act_window',
                    'target': 'stack',
                    'nodestroy': True,
                    }
        
        
        return True 
    
    

class wo_declaration_produce(models.TransientModel):
    """ 
        WorkOrder Declaration Produce
    """
    _inherit = 'wo.declaration.produce'
    _description = 'WorkOrder Declaration Produce'
    _rec_name = 'wo_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    declaration_id = fields.Many2one('wo.declaration.main', string='Main', required=False, ondelete='cascade')
    wo_id = fields.Many2one('mrp.workorder', string='WorkOrder', required=True, ondelete='cascade')
    quantity = fields.Float(string='Quantity', default=0.0, required=False, digits=dp.get_precision('Product quantity'))  
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='cascade')
    qty_hs = fields.Float(string='Quantity HS', default=0.0, required=True, digits=dp.get_precision('Product quantity'))
    qty_ok = fields.Float(string='Quantity OK', default=0.0, required=True, digits=dp.get_precision('Product quantity'))
    qty_quarantine = fields.Float(string='Quantity Quarantine', default=0.0, required=True, digits=dp.get_precision('Product quantity'))
    sec_qty_hs = fields.Float(string='Quantity HS (Sec UoM)', default=0.0, required=True, digits=dp.get_precision('Product quantity'))
    sec_qty_ok = fields.Float(string='Quantity OK (Sec UoM)', default=0.0, required=True, digits=dp.get_precision('Product quantity'))
    sec_qty_quarantine = fields.Float(string='Quantity quarantine (Sec UoM)', default=0.0, required=True, digits=dp.get_precision('Product quantity'))
    uom_id = fields.Many2one('product.uom', string='UoM', required=False, ondelete='cascade')
    note = fields.Text(string='Note')
    nb_label = fields.Integer(string='Nb Label', default=0, required=False)
    qty_label = fields.Float(string='Qty per label', default=0.0, required=False)
    sec_qty_label = fields.Float(string='Qty Label (Sec. UoM)', default=0.0, required=False)
    track_label = fields.Boolean(string='Track Label', default=False)
    move_id = fields.Many2one('stock.move', string='Move', required=False, ondelete='cascade')
    label_template_id = fields.Many2one('stock.label.template', string='Label template', required=False, ondelete='cascade')
    asign_label_ids = fields.One2many('assign.label.wo.produce', 'consumption_line_id', string='Labels')
    is_generate = fields.Boolean(string='Generate', default=False)
    wind_up = fields.Boolean(string='WO Wind up', default=False)
    is_print_label = fields.Boolean(string='Print Label', default=True)
    consumption_id = fields.Many2one('wo.declaration.consumption', string='Consumption', required=False, ondelete='cascade')
    theorical_consumption = fields.Boolean(string='Theorical Consumption', default=False)
    control_declaration_id = fields.Many2one('quality.control.declaration', string='Declaration quality control', required=False, ondelete='cascade')
    is_control_declaration = fields.Boolean(string='Is control declaration', default=False)
    is_expiry_date = fields.Boolean(string='Expery date', default=False)
    expiry_date = fields.Date(string='Expery Date')
    quality_rl = fields.Boolean(string='Quality RL', default=False)
    is_variable_double_unit = fields.Boolean(default=False)    
    is_recalculate_frequency_control = fields.Boolean(string='Recalculate frequency control', default=False)
    label_mo_repair_id = fields.Many2one('stock.label', string='Label MO repaire', required=False, ondelete='cascade')
    new_auto_um = fields.Boolean(string='New automatic UM', default=False)
    label_um_id = fields.Many2one('stock.label', string='Label UM', required=False, ondelete='cascade')
    label_um_number = fields.Char(size=64)
    label_template_um_id = fields.Many2one('stock.label.template', string='Label UM template', required=False, ondelete='cascade', domain=[('type', '=', 'um')])
    new_auto_lot = fields.Boolean(string='New automatic lot', default=False)
    lot_id = fields.Many2one('stock.lot', string='Lot', required=False, ondelete='restrict')
    date = fields.Datetime(string='Date of declaration')
    first_resource_id = fields.Many2one('mrp.resource', string='First resource')
    is_last = fields.Boolean(string='Is last produce declaration', default=True) # pour cedre, declaration sous produit
    #===========================================================================
    # Boutons
    #===========================================================================
    
    @api.multi
    def generate_labels_subproducts(self):
        # point d'entrée module cèdre
        return True
    
    @api.multi
    def action_validate(self):
        res = False
        for wiz in self:
            # Gestion des attributs
            if wiz.is_control_declaration and (not wiz.control_declaration_id and (not wiz.move_id or wiz.move_id and not wiz.move_id.control_declaration_id)):
                raise except_orm('Error', _('Please make the quality control statement for this declaration'))
            
            if wiz.wo_id.state in ('draft', 'waiting', 'cancel'):
                raise except_orm('Error', 'it is not possible to make declaration if the state is draft or waiting or cancel')
        
            if wiz.move_id and wiz.move_id.wo_produce_id:
                raise except_orm('Error', 'The declaration was already made, if you want to print the labels must be done manually from the label')
            
            availability = self.wo_id.compute_availability(is_availability_force=True)
            if availability < 100:
                qty_availability_produce = self.wo_id.quantity and self.quantity * 100 / self.wo_id.quantity
                if qty_availability_produce > availability:
                    raise except_orm('Error', 'The availability of raw materials do not let you to produce this quantity.')
            
            if wiz.move_id.product_id.get_common_attribute_ids() and not self.env.context.get('without_attributes'):
                label_qtys = {}
                for label_line in wiz.asign_label_ids:
                    label_qtys[label_line.label_id.id] = label_line.quantity 
                    if label_line.label_name:
                        label_line.label_id.write({'name': label_line.label_name})
                                    
                res = {
                    'name': _('Create attributes'),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'create.label.attribute.wizard',
                    'type': 'ir.actions.act_window',
                    'context': {'common_product_id': wiz.move_id.product_id.id, 'default_wo_declaration_id': wiz.id, 'default_label_ids': label_qtys.keys(), 'label_qtys': label_qtys},
                    'target': 'new'
                       }
            else:
                for label_line in wiz.asign_label_ids:
                    if label_line.label_name:
                        label_line.label_id.write({'name': label_line.label_name})
                wo_produce = wiz.validate_produce(vals_wo_produce_data=False, without_availability=True)
                if not self.env.context.get('return_false'):
                    res = wo_produce
               
        return res
    
    
    @api.multi
    def action_cancel(self):
        for wiz in self:
            if wiz.control_declaration_id:
                wiz.control_declaration_id.unlink()
        
        return {'type': 'ir.actions.act_window_close'}    
    
    
    def validate_produce(self, vals_wo_produce_data=False, without_availability=False):
        """
            Validation du wizard de production
            :param without_availability: Permet de ne pas recalculer la dispo si cette méthode est appelée par une méthode calculant déjà la dispo
            :type without_availability: boolean
        """
        uom_obj = self.env['product.uom']
        label_obj = self.env['stock.label']
        move_label_obj = self.env['stock.move.label']
        wo_produce_obj = self.env['mrp.wo.produce']
        produce_more = False
        if self.is_control_declaration and (not self.control_declaration_id and (not self.move_id or self.move_id and not self.move_id.control_declaration_id)):
            raise except_orm('Error', _('Please make the quality control statement for this declaration'))
        
        qty_ok = self.qty_ok
        qty_hs = self.qty_hs
        qty_quarantine = self.qty_quarantine
        qty_total = qty_ok + qty_hs + qty_quarantine
        
        sec_qty_ok = self.sec_qty_ok
        sec_qty_hs = self.sec_qty_hs
        sec_qty_quarantine = self.sec_qty_quarantine
        sec_qty_total = sec_qty_ok + sec_qty_hs + sec_qty_quarantine
        
        if self.wo_id.state in ('draft', 'waiting', 'cancel'):
            raise except_orm('Error', 'it is not possible to make declaration if the state is draft or waiting or cancel')
        
        if self.move_id and self.move_id.wo_produce_id:
            raise except_orm('Error', 'The declaration was already made, if you want to print the labels must be done manually from the label')
        
        if self.consumption_id and self.is_last:
            self.consumption_id.action_validate_comsuption(no_return_view=True, vals_wo_comsumption_data=False)
        
        elif self.theorical_consumption:
            first_resource_id = self.wo_id.first_resource_id and self.wo_id.first_resource_id.id or False
            vals = {
                'wo_id': self.wo_id.id,
                'user_id': self.env.user.id,
                'uom_id': self.uom_id.id,
                'product_id': self.wo_id.final_product_id.id,
                'quantity': qty_total,
                'type': 'cons_prod',
                'first_resource_id': first_resource_id
            }
            wdm_rcs = self.env['wo.declaration.main'].create(vals)
            # Déclaration de la consomation
            wdc_rcs = wdm_rcs.create_declaration_consumption()
            wdc_rcs.action_validate_comsuption(no_return_view=True, vals_wo_comsumption_data=False)

        # Calcule du pourcentage de production
        if without_availability:
            availability = 100
        else:
            availability = self.wo_id.compute_availability(is_availability_force=True)
            
        if availability < 100:
            qty_availability_produce = self.wo_id.quantity and self.quantity * 100 / self.wo_id.quantity
            if qty_availability_produce > availability:
                raise except_orm('Error', 'The availability of raw materials do not let you to produce this quantity.')
        
        if not self.move_id:
            produce_more = True
            copy_move_rcs = False
            # Si c'est le dernier OT de l'OF, déclaration du produit final
            last_wo = False
            if not self.wo_id.next_wo_ids:
                last_wo = True
            else:
                last_wo = True
                for next_wo in self.wo_id.next_wo_ids:
                    if next_wo.mo_id.id == self.wo_id.mo_id.id:
                        last_wo = False
                        break
                     
            if last_wo:
                for fp in self.wo_id.fp_done_ids:
                    if fp.product_id.id == self.wo_id.final_product_id.id:
                        copy_move_rcs = fp
                        break
            
            # Si ce n'est pas le dernier OT, déclaration du produit intermédiaire
            elif self.is_last:
                for fp in self.wo_id.fp_done_ids:
                    if fp.product_id.is_int:
                        copy_move_rcs = fp
                        break
            
            if copy_move_rcs:
                copy_uom_qty = copy_move_rcs.uom_qty or 1.0
                move_vals = {'state': 'draft',
                             'uom_qty': qty_total,
                             'wo_produce_id': False,
                             'procurement_id': False,
                             'efficient_unit_qty': False,
                             'purchase_line_id': False,
                             'sale_line_id': False}
                
                if self.is_variable_double_unit:
                    move_vals['sec_uom_qty'] = sec_qty_total
                    move_vals['uoi_qty'] = uom_obj._compute_qty_obj(copy_move_rcs.sec_uom_id, sec_qty_total, copy_move_rcs.uoi_id)
                else:
                    new_qty_sec_uom = copy_move_rcs.sec_uom_qty * qty_total / copy_uom_qty
                    new_qty_uoi = copy_move_rcs.uoi_qty * qty_total / copy_uom_qty
                    move_vals['sec_uom_qty'] = new_qty_sec_uom
                    move_vals['uoi_qty'] = new_qty_uoi

                move_id = copy_move_rcs.copy(move_vals)
                move_id.wkf_waiting()
                    
            else:
                raise except_orm('Error', 'No move to the final product')
        
        else:
            move_id = self.move_id
        
        # Test si Quantity HS + Quantity OK = Quantity
        if Decimal(str(self.quantity)) != Decimal(str(qty_ok + qty_hs + qty_quarantine)):
            raise except_orm('Error', 'Quantity HS + Quantity OK + qty_quarantine != Quantity.')
        
        # Test si Quantity > 0
        if self.quantity <= 0:
            raise except_orm('Error', 'Quantity <= 0.0.')
        
        # Si produit tracé sans sous traitance
        qty_ok_label = 0.0
        qty_quarantine_label = 0.0
        dico_label_ok_ids = {}
        dico_label_quarantine_ids = {}
        if self.product_id.track_label and self.wo_id and not self.wo_id.is_subcontracting:
            # Partie UM
            if self.new_auto_um:
                name_um = self.label_um_number or self.label_template_um_id.sequence_id.next_by_id()
                label_vals = {'template_id': self.label_template_um_id.id,
                              'name': name_um,
                              }
                um_label_id = label_obj.create(label_vals).id
            else:
                um_label_id = self.label_um_id and self.label_um_id.id or False
            
            # Partie UC
            for asign_label in self.asign_label_ids:
                if asign_label.for_quarantine:
                    # Calcule de la quantité des etiquettes
                    qty_quarantine_label += uom_obj._compute_qty_obj(asign_label.uom_id, asign_label.quantity, self.uom_id, with_raise=False, with_round=False)
                    # Dico avec comme clé le recordset de l'étiquette et comme valeur sa quantité
                    dico_label_quarantine_ids[asign_label.label_id] = (asign_label.quantity, asign_label.sec_uom_qty)
                else:    
                    # Calcule de la quantité des etiquettes
                    qty_ok_label += uom_obj._compute_qty_obj(asign_label.uom_id, asign_label.quantity, self.uom_id, with_raise=False, with_round=False)
                    # Dico avec comme clé le recordset de l'étiquette et comme valeur sa quantité
                    dico_label_ok_ids[asign_label.label_id] = (asign_label.quantity, asign_label.sec_uom_qty)
                
                asign_label.label_id.write({'um_label_id': um_label_id})
            
            if qty_ok_label != qty_ok:
                raise except_orm(_('Error'), _('Sum(label quantity ok) != Quantity OK.'))
            
            if qty_quarantine_label != qty_quarantine:
                raise except_orm(_('Error'), _('Sum(label quantity quarantine) != Quantity Quarantine.'))

        move_ids = self.env['stock.move']
        new_move_ids = self.env['stock.move']
        # Si la quantité n'est pas égale à la quantité du mouvement on fait un reliquat du reste
        if self.is_variable_double_unit:
            new_move = self.wo_id.modif_move_or_scrap(move_id, move_id.uom_qty, qty_total, move_id.sec_uom_qty, sec_qty_total, self.is_variable_double_unit)
        else:
            new_move = self.wo_id.modif_move_or_scrap(move_id, move_id.uom_qty, qty_total)
        
        if new_move:
            new_move_ids += new_move
            
        # Gestion des sous produits qui sont calculés qu'avec la quantité OK
        sub_product_ids = []
        if self.is_last:
            for fp_draft in self.wo_id.fp_draft_ids:
                if fp_draft.product_id.id != self.product_id.id and not fp_draft.product_id.is_int:
                    if fp_draft.type_qty == 'variable':
                        qty_sub_product = fp_draft.uom_qty - fp_draft.initial_uom_qty
                    else:
                        qty_sub_product = self.get_quantity_subproduct(fp_draft)
                    
                    sub_product_ids.append(fp_draft.product_id.id)
                    new_move = self.wo_id.modif_move_or_scrap(fp_draft, fp_draft.uom_qty, qty_sub_product)
                    if new_move:
                        new_move_ids += new_move
                        
                    move_ids += fp_draft
        
        if produce_more:
            for fp_done in self.wo_id.fp_done_ids:
                if fp_done.product_id.id != self.product_id.id and not fp_done.product_id.is_int and fp_done.product_id.id not in sub_product_ids and fp_done.type_qty == 'variable':
                    qty_sub_product = qty_ok * fp_done.efficient_unit_qty or qty_ok
                    new_move = self.wo_id.modif_move_or_scrap(fp_done, fp_done.uom_qty, qty_sub_product)
                    if new_move:
                        new_move_ids += new_move
                        
                    move_ids += fp_done

        # On prépare la création d'une ligne dans le tableau des OTs de production
        vals_wo_produce = {
            'wo_id': self.wo_id.id,
            'date': self.date,
            'qty_ok': qty_ok,
            'qty_hs': qty_hs,
            'qty_quarantine': qty_quarantine,
            'uom_id': self.declaration_id.uom_id.id,
            'note': self.note,
            'product_id': self.product_id.id,
            'first_resource_id': self.first_resource_id and self.first_resource_id.id or False,
        } 
        if vals_wo_produce_data:
            vals_wo_produce.update(vals_wo_produce_data)
            
        if self.is_last:
            wo_produce = wo_produce_obj.create(vals_wo_produce)
        else:
            wo_produce = wo_produce_obj
        if self.is_control_declaration and self.control_declaration_id and self.control_declaration_id.line_result_ids and wo_produce:
            self.control_declaration_id.line_result_ids.write({'wo_produce_id': wo_produce.id})
            
        # On lie les mouvements à la déclaration
        move_ids += move_id
        move_ids.write({'wo_produce_id': wo_produce.id})
        # Partie sur le split des mouvements avec qty_ok, qty_hs, qty_quarantine        
        move_id, move_hs_rcs, move_quarantine_rcs = move_id.split_move_ok_hs_quarantine(qty_ok, qty_hs, qty_quarantine, sec_qty_ok=sec_qty_ok, sec_qty_hs=sec_qty_hs, sec_qty_quarantine=sec_qty_quarantine)
        write_vals = {}
        if move_hs_rcs:
            write_vals['move_hs_id'] = move_hs_rcs.id
            move_hs_rcs.wkf_waiting()
            move_ids += move_hs_rcs
            
        if move_quarantine_rcs:
            write_vals['move_quarantine_id'] = move_quarantine_rcs.id
            move_quarantine_rcs.wkf_waiting()
            move_ids += move_quarantine_rcs

        if write_vals:
            move_id.write(write_vals)
        
        if self.product_id.track_label and self.wo_id and not self.wo_id.is_subcontracting:
            lot_rcs = self.env['stock.lot']
            label_already_present_dic = {}
            for move_label in move_id.move_label_ids:
                label_already_present_dic[move_label.label_id.id] = move_label
            
            label_already_present_ids = label_already_present_dic and label_already_present_dic.keys()
            date_stpr = datetime.datetime.strptime(self.date, '%Y-%m-%d %H:%M:%S')
            date_diff = (date_stpr - datetime.timedelta(0,1)).strftime("%Y-%m-%d %H:%M:%S")
            ctx_move_label = self.env.context.copy()
            ctx_move_label['authorize_return'] = True
            for label, qtys in dico_label_ok_ids.iteritems():
                if label.id not in label_already_present_ids: 
                    if label.location_id and label.location_id != move_id.location_id:
                        if label.state in ('brouillon', 'inactive'):
                            move_temp = label.with_context(ctx_move_label).move(location=move_id.location_id)
                        else:
                            move_temp = label.with_context(ctx_move_label).move(location=move_id.location_dest_id)
                            
                        move_temp.write({'date_expected': date_diff, 
                                         'date': date_diff, 
                                         'priority_date': date_diff})
                            
                    move_label_obj.create({'move_id': move_id.id,
                                           'uom_qty': qtys[0],
                                           'sec_uom_qty': qtys[1],
                                           'label_id': label.id,
                                           'for_quarantine': False})
                else:
                    label_already_present_dic[label.id].write({'move_id': move_id.id,
                                                               'uom_qty': qtys[0],
                                                               'sec_uom_qty': qtys[1],
                                                               'for_quarantine': False})
                
                if label.lot_id and label.lot_id not in lot_rcs:
                    lot_rcs += label.lot_id
            
            if move_quarantine_rcs:
                for label, qtys in dico_label_quarantine_ids.iteritems():
                    if label.id not in label_already_present_ids: 
                        if label.location_id and label.location_id != move_quarantine_rcs.location_id:
                            if label.location_id and label.location_id != move_id.location_id:
                                if label.state in ('brouillon', 'inactive'):
                                    move_temp = label.with_context(ctx_move_label).move(location=move_id.location_id)
                                else:
                                    move_temp = label.with_context(ctx_move_label).move(location=move_id.location_dest_id)
                                
                                move_temp.write({'date_expected': date_diff, 
                                                 'date': date_diff, 
                                                 'priority_date': date_diff})
                            
                        move_label_obj.create({'move_id': move_quarantine_rcs.id,
                                               'uom_qty': qtys[0],
                                               'sec_uom_qty': qtys[1],
                                               'label_id': label.id,
                                               'for_quarantine': True})
                    else:
                        label_already_present_dic[label.id].write({'move_id': move_quarantine_rcs.id,
                                                                   'uom_qty': qtys[0],
                                                                   'sec_uom_qty': qtys[1],
                                                                   'for_quarantine': True})
                        
                if label.lot_id and label.lot_id not in lot_rcs:
                    lot_rcs += label.lot_id
                    
            if lot_rcs and self.is_expiry_date and self.expiry_date:
                lot_rcs.write({'expiry_date': self.expiry_date})
        
        if self.control_declaration_id:
            partner_id = self.wo_id and self.wo_id.customer_id and self.wo_id.customer_id.id or False
            # Passage du contrôle à l'état done suite au passage à l'état cancel (pour éviter d'avoir un contrôle done alors que le wizard de déclaration a été fermé)
            self.control_declaration_id.wkf_done()
            self.control_declaration_id.assign_move_quality(move_ok_rcs=move_id, move_hs_rcs=move_hs_rcs, move_quarantine_rcs=move_quarantine_rcs, control_declaration_rcs=self.control_declaration_id, post_control=False, partner_id=partner_id)
            
        # On valides les mouvements
        move_ids.write({'done_date': self.date})
        move_ids.wkf_done()
#         move_ids.write({'date_expected': self.date, 'date': self.date, 'priority_date': self.date})
        # On calcule le prix réel et le prix théo de l'ot
        theo_price, real_price, currency_id = self.wo_id.mo_id.compute_price_move_fp(self.wo_id, qty_ok, qty_hs, qty_quarantine)
        if move_id and move_id.product_id == self.wo_id.final_product_id:
            move_id.write({'theo_price': theo_price, 'partner_price': real_price, 'currency_id': self.wo_id.final_product_id.company_id.currency_id.id})

        if move_quarantine_rcs and move_quarantine_rcs.product_id == self.wo_id.final_product_id:
            move_quarantine_rcs.write({'theo_price': theo_price, 'partner_price': real_price, 'currency_id': self.wo_id.final_product_id.company_id.currency_id.id})
                
        # On passe les reliquats à en attente
        if new_move_ids:
            new_move_ids.wkf_waiting()
            
        # Si l'OT est  draft, waiting, plan ou ready on le passe à progress
        if self.wo_id.state in ('draft', 'waiting', 'plan', 'ready'):
            self.wo_id.wkf_progress()
            
        # Si le champ cloturé OT est coché on termine l'OT
        if self.wind_up:
            self.wo_id.wkf_done()
#         elif self.wo_id._function_compute_advancement(with_state=False) >= 100 and self.wo_id.state != 'done':
#             self.wo_id.wkf_done()
        
        if self.is_print_label and self.asign_label_ids:
            self.asign_label_ids.mapped('label_id').do_print_label()
        
        return wo_produce
    
    def get_quantity_subproduct(self, fp):
        return fp.uom_qty
    
    
    @api.multi
    def delete_label(self):
        """ 
            Suppression des étiquettes créées 
        """
        for wiz in self:
            for asign_label in wiz.asign_label_ids:
                if not asign_label.is_no_modif_qty:
                    asign_label.label_id.unlink()

                asign_label.unlink()
            
            self.write({'is_generate': False})
            data_pool = self.env['ir.model.data']
            action_model, action_id = data_pool.get_object_reference('mrp', 'act_wo_declaration_produce_form')
            #Puis on va passer l'id à la vue pour pouvoir l'afficher dans la vue form
            if action_model:
                action_pool = self.env[action_model]
                action = action_pool.browse(action_id).read()[0]
                action['res_id'] = wiz.id
                res = action
                return res
            
        return False
    
    
    @api.multi
    def generate_label(self):
        """ 
            Creation étiquette avant de les lier au mouvement sortant de production
        """
        label_obj = self.env['stock.label']
        label_produce_obj = self.env['assign.label.wo.produce']
        uom_obj = self.env['product.uom']
        for wiz in self:
            lot = self.generate_lot(wiz.product_id)
            number_of_label = wiz.nb_label
            # Bouclage pour la création des étiquettes
            label_template_id = wiz.label_template_id and wiz.label_template_id.id or wiz.product_id.label_template_id.id
            while number_of_label:
                label_vals = {'template_id': label_template_id,
                              'lot_id': lot.id,
                              'product_id': wiz.product_id.id,
                              'uom_qty': 0.0,
                              'uom_id': wiz.product_id.uom_id.id}
                if wiz.is_variable_double_unit:
                    label_vals['sec_uom_qty'] = 0.0
                    label_vals['sec_uom_id'] = wiz.product_id.sec_uom_id.id
                    label_vals['is_variable_double_unit'] = True
                    
                label_rcs = label_obj.create(label_vals)
                number_of_label -= 1
                qty = uom_obj._compute_qty_obj(wiz.uom_id, wiz.qty_label, to_uom=wiz.product_id.uom_id, with_raise=False, with_round=False)
                label_produce_vals = {'consumption_line_id': wiz.id,
                                      'label_id': label_rcs.id,
                                      'uom_id': wiz.product_id.uom_id.id,
                                      'is_variable_double_unit': wiz.is_variable_double_unit,
                                      'quantity': qty}
                if wiz.is_variable_double_unit:
                    label_produce_vals['sec_uom_qty'] = wiz.sec_qty_label
                    label_produce_vals['sec_uom_id'] = wiz.product_id.sec_uom_id.id
                   
                label_produce_obj.create(label_produce_vals)
                
            self.write({'is_generate': True})
            data_pool = self.env['ir.model.data']
            action_model, action_id = data_pool.get_object_reference('mrp', 'act_wo_declaration_produce_form')
            #Puis on va passer l'id à la vue pour pouvoir l'afficher dans la vue form
            if action_model:
                action_pool = self.env[action_model]
                action = action_pool.browse(action_id).read()[0]
                action['res_id'] = wiz.id
                res = action
                return res
            
        return False
    

    def generate_lot(self, product):
        """ 
            Creation lot pour les étiquettes des mouvements sortant de production
        """
        if self.new_auto_lot:
            lot_obj = self.env['stock.lot']
            lot = lot_obj.create({'product_id': product.id})
        else:
            lot = self.lot_id
            
        return lot
    
    
    @api.multi
    def button_control_declaration(self):
        control_declaration_obj = self.env['quality.control.declaration']
        for wiz in self:
            if wiz.control_declaration_id:
                control_declaration_rcs = wiz.control_declaration_id
            else:
                if wiz.wo_id and wiz.wo_id.name_get():
                    name_declaration = '%s %s' %(wiz.wo_id.name_get()[0][-1], wiz.wo_id.name)
                else:
                    name_declaration = ''
                
                if wiz.quality_rl:
                    quality_control_ids = wiz.wo_id.routing_line_id.quality_control_ids
                else:
                    quality_control_ids = wiz.product_id.quality_control_ids
                
                partner_id = wiz.wo_id and wiz.wo_id.customer_id and wiz.wo_id.customer_id.id or False
                control_declaration_rcs = control_declaration_obj.generate_control_declaration(quality_control_ids, 
                                                                                               wiz.quantity, 
                                                                                               type_declaration='intern', 
                                                                                               type_control='intern', 
                                                                                               date=fields.Datetime.now(), 
                                                                                               name_declaration=name_declaration, 
                                                                                               move_init_rcs=wiz.move_id, 
                                                                                               product_rcs=wiz.move_id.product_id, 
                                                                                               partner_id = partner_id,
                                                                                               wo_rcs=wiz.wo_id)
            
            if control_declaration_rcs:
                ctx2 = self.env.context.copy()
                ctx2['type_control_all'] = control_declaration_rcs.type_control
                wiz.write({'control_declaration_id': control_declaration_rcs.id})
                return {
                        'name': _('Quality Control Declaration'),
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'quality.control.declaration',
                        'type': 'ir.actions.act_window',
                        'target': 'stack',
                        'res_id': control_declaration_rcs.id,
                        'nodestroy': True,
                        'context': ctx2,
                        }
            else:
                wiz.move_id.recalculate_frequency_quality_main(post_control=False)
                wiz.write({'is_recalculate_frequency_control': True, 'is_control_declaration': False})
                wiz.move_id.write({'is_recalculate_frequency_control': True})
                msg = _('No quality control statement to make for this reception')
                return self.env['message.wizard'].create_message(msg=msg, target='stack')
                
        return {'type': 'act_window_noclose'} 
    
    
        
class assign_label_wo_consumption(models.TransientModel):
    """ 
    Assign label
    """
    _name = 'assign.label.wo.consumption'
    _description = 'Wo Assign label Consumption'
    _rec_name = 'move_id'
   
   
    @api.one
    @api.depends('consumption_line_id')
    def _compute_consumption_line(self):
        """
            Fonction qui récupère le produit et la quantité de la ligne
        """
        self.product_id = self.consumption_line_id.product_id.id
        self.product_qty = self.consumption_line_id.quantity
        self.uom_id = self.consumption_line_id.uom_id.id
        self.move_id = self.consumption_line_id.move_id.id

        
    @api.model
    def default_get(self, fields_list):
        res = super(assign_label_wo_consumption, self).default_get(fields_list=fields_list)
        consumption_line_id = self.env.context.get('active_id')
        if consumption_line_id:
            res['consumption_line_id'] = consumption_line_id
            
        return res
    

    #===========================================================================
    # COLUMNS
    #===========================================================================
    consumption_line_id = fields.Many2one('wo.declaration.consumption.line', string='Consumption Line', required=True, ondelete='cascade')
    line_ids = fields.One2many('assign.label.wo.consumption.line', 'label_consumption_id',  string='Lines')
    uom_id = fields.Many2one('product.uom', string='UoM', compute='_compute_consumption_line')
    product_id = fields.Many2one('product.product', string='Product', compute='_compute_consumption_line')
    product_qty = fields.Float(string='Quantity', compute='_compute_consumption_line')
    move_id = fields.Many2one('stock.move', string='Move', compute='_compute_consumption_line')
    is_variable_double_unit = fields.Boolean(default=False)
    
    
    #===========================================================================
    # Fonctions
    #===========================================================================
    @api.multi
    def action_validate(self):
        """ 
            Validation pour lier les etiquettes aux mouvements
        """
        return True   
    


class assign_label_wo_consumption_line(models.TransientModel):
    """ 
    Assign label Wo consumption line
    """
    _name = 'assign.label.wo.consumption.line'
    _description = 'Wo Assign label Consumption'
    _rec_name = 'label_id'    
    
    @api.one
    @api.depends('label_id')
    def _compute_label(self):
        """
            Fonction qui récupère et transforme la quantité et l'UdM de l'etiquette de ceux du mouvement
        """
        self.uom_id = self.label_consumption_id.consumption_line_id.uom_id.id
        self.sec_uom_id = self.label_consumption_id.consumption_line_id.sec_uom_id.id
        self.quantity_init = self.quantity_init_inv
        self.sec_quantity_init = self.env['product.uom']._compute_qty_obj(self.label_id.sec_uom_id, self.label_id.sec_uom_qty, self.sec_uom_id, with_raise=False, with_round=False)
    

    #===========================================================================
    # COLUMNS
    #===========================================================================
    consumption_line_id = fields.Many2one('wo.declaration.consumption.line', string='Consumption Line', ondelete='cascade')
    label_consumption_id = fields.Many2one('assign.label.wo.consumption', string='Assign label wo consumption', required=False, ondelete='cascade')
    quantity = fields.Float(string='Quantity', default=0.0, digits=dp.get_precision('Product quantity'), required=1)
    label_id = fields.Many2one('stock.label', string='Label', required=1, ondelete='cascade')
    quantity_init = fields.Float(string='Label quantity', compute='_compute_label')
    quantity_init_inv = fields.Float(string='Label quantity')
    uom_id = fields.Many2one('product.uom', string='UoM', compute='_compute_label')
    sec_quantity_init = fields.Float(string='Label quantity (Sec. UoM)', compute='_compute_label')
    sec_uom_qty = fields.Float(string='Quantity (Sec. UoM)', required=True, default=0.0, digits=dp.get_precision('Product quantity'))
    sec_uom_id = fields.Many2one('product.uom', string='Sec. UoM', required=False, ondelete='cascade', compute='_compute_label')
    is_variable_double_unit = fields.Boolean(default=False)
    
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('label_id')
    def _onchange_label_id(self):
        """
            Au changement du produit, changement de la catégorie de l'uom
        """
        qty = self.env['product.uom']._compute_qty_obj(self.label_id.uom_id, self.label_id.uom_qty, 
                                                       self.consumption_line_id.uom_id, with_raise=False, with_round=False)
        self.quantity = qty
        self.sec_uom_qty = self.label_id.sec_uom_qty
        self.quantity_init_inv = qty
    
    
    #===========================================================================
    # Fonctions
    #===========================================================================
    def create_consumption_line(self, label_ids, consumption_line_rcs, label_consumption_rcs, qty_default=False, dico_consupline_qty_label=None):
        consumption_line_ids = self
        uom_obj = self.env['product.uom']
        label_list_in_consumption_line = [x.label_id.id for x in label_consumption_rcs.line_ids if x.label_id]
        if dico_consupline_qty_label and consumption_line_rcs in dico_consupline_qty_label:
            qty_total_label = dico_consupline_qty_label[consumption_line_rcs]['uom_qty']
            sec_qty_total_label = dico_consupline_qty_label[consumption_line_rcs]['sec_uom_qty']
        for label in label_ids:
            if label.id not in label_list_in_consumption_line:
                qty = label.uom_qty
                if qty_default:
                    qty_default1 = qty_default
                else:
                    qty_default1 = qty
                
                qty_init = uom_obj._compute_qty_obj(label.uom_id, label.uom_qty, consumption_line_rcs.uom_id, with_raise=False, with_round=False)
                qty = uom_obj._compute_qty_obj(label.uom_id, qty_default1, consumption_line_rcs.uom_id, with_raise=False, with_round=False)
                sec_qty = uom_obj._compute_qty_obj(label.sec_uom_id, label.sec_uom_qty, consumption_line_rcs.sec_uom_id, with_raise=False, with_round=False)
                if dico_consupline_qty_label and consumption_line_rcs in dico_consupline_qty_label:
                    if label.template_id.is_theorical_comuption:
                        if consumption_line_rcs.quantity >= (qty_total_label + qty):
                            qty_total_label += qty
                        else:
                            qty = consumption_line_rcs.quantity - qty_total_label
                            if qty < 0:
                                qty = 0
                                
                            qty_total_label += qty
                        
                        if consumption_line_rcs.sec_uom_qty >= (sec_qty_total_label + sec_qty):
                            sec_qty_total_label += sec_qty
                        else:
                            sec_qty = consumption_line_rcs.sec_uom_qty - sec_qty_total_label
                            if sec_qty < 0:
                                sec_qty = 0
                                
                            sec_qty_total_label += qty
                
                vals = {
                   'consumption_line_id': consumption_line_rcs.id,
                   'label_consumption_id': label_consumption_rcs.id,
                   'label_id': label.id,
                   'quantity_init_inv': qty_init,
                   'quantity': qty,
                   'sec_uom_qty': sec_qty,
                   'is_variable_double_unit': label.is_variable_double_unit,
                    }
                consumption_line_ids += self.create(vals)
                label_list_in_consumption_line.append(label.id)
                
        return consumption_line_ids
    
    

class assign_label_wo_produce(models.TransientModel):
    """ 
    Assign label
    """
    _name = 'assign.label.wo.produce'
    _description = 'Wo Assign label Produce'
    _rec_name = 'label_id'

    #===========================================================================
    # COLUMNS
    #===========================================================================
    @api.one
    def _compute_label(self):
        """
            Fonction qui récupère le produit et l'UdM dans l'OT
        """
        self.uom_id = self.label_id and self.label_id.uom_id or False
        self.sec_uom_id = self.label_id and self.label_id.sec_uom_id or False
        
        
    consumption_line_id = fields.Many2one('wo.declaration.produce', string='Consumption Produce', required=False, ondelete='cascade')
    label_id = fields.Many2one('stock.label', string='Label', required=False, ondelete='cascade')
    quantity = fields.Float(string='Quantity', default=0.0, digits=dp.get_precision('Product quantity'))
    uom_id = fields.Many2one('product.uom', string='UoM', compute='_compute_label')
    sec_uom_qty = fields.Float(string='Quantity (Sec. UoM)', default=0.0, digits=dp.get_precision('Product quantity'))
    sec_uom_id = fields.Many2one('product.uom', string='Second UoM', compute='_compute_label')
    for_quarantine = fields.Boolean(string='For quarantine', default=False)
    is_variable_double_unit = fields.Boolean(default=False)
    label_mo_repair_id = fields.Many2one('stock.label', string='Label MO repaire', required=False, ondelete='cascade')
    label_name = fields.Char(required=False, help='Allows to force the label name')
    is_no_modif_qty = fields.Boolean(string='No modif qty', default=False)
    


class assign_add_label_wo_consumption(models.TransientModel):
    """ 
    Assign label
    """
    _name = 'assign.add.label.wo.consumption'
    _description = 'Wo Assign label Consumption'
    _rec_name = 'wdcl_id'
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(assign_add_label_wo_consumption, self).default_get(fields_list=fields_list)
        vals = {
            'wdcl_id': self._context.get('active_id')
        }
        
        res.update(vals)
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    label_ids = fields.Many2many('stock.label', 'assign_add_label_wo_consumption_stock_label_rel', 'assign_add_label_wo_id', 'label_id', string='Labels')
    wdcl_id = fields.Many2one('wo.declaration.consumption.line', string='WDCL', required=False, ondelete='cascade')
    
    #===========================================================================
    # Button
    #===========================================================================
    @api.multi
    def action_validate(self):
        label_consumption_obj = self.env['assign.label.wo.consumption']
        label_consumption_line_obj = self.env['assign.label.wo.consumption.line']
        for wiz in self:
            dico_consupline_qty_label = {}
            if wiz.wdcl_id.label_consumption_ids:
                label_consumption_rcs = wiz.wdcl_id.label_consumption_ids
                qty_total_label = 0
                sec_qty_total_label = 0
                for label_consumption in label_consumption_rcs:
                    for line in label_consumption.line_ids:
                        qty_total_label += line.quantity
                        sec_qty_total_label += line.sec_uom_qty
                
                dico_consupline_qty_label[wiz.wdcl_id] = {'uom_qty': qty_total_label, 'sec_uom_qty': sec_qty_total_label}
            else:
                label_consumption_rcs = label_consumption_obj.create({'consumption_line_id': wiz.wdcl_id.id, 'is_variable_double_unit': wiz.wdcl_id.is_variable_double_unit})
                dico_consupline_qty_label[wiz.wdcl_id] = {'uom_qty': 0, 'sec_uom_qty': 0}
            
            label_consumption_line_obj.create_consumption_line(wiz.label_ids, wiz.wdcl_id, label_consumption_rcs, dico_consupline_qty_label=dico_consupline_qty_label)
        
        return True
    
