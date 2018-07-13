# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
from decimal import Decimal

class wiz_mo_repair(models.TransientModel):
    """ 
        Wiz manufacturing order for repair
    """
    _name = 'wiz.mo.repair'
    _description = 'Wiz manufacturing order for repair'
    _rec_name = 'origin_num_serie_id'
    
    @api.one
    @api.depends('origin_num_serie_id')
    def _compute_origin_num_serie_id(self):
        """
            All origin_num_serie_id
        """
        self.product_id = self.origin_num_serie_id.product_id.id
        self.uom_id = self.origin_num_serie_id.uom_id.id
        self.qty_label = self.origin_num_serie_id.uom_qty
    
    @api.model
    def _repair_type_get(self):
        return [
                ('repair_overhead', _('Repair overhead')),
                ('repair_subset', _('Repair subset')),
                       ]
        
        
    @api.one
    @api.depends('routing_id')
    def _compute_all_operation_ids(self):
        """
            All routing_id
        """
        all_operation_ids = []
        for ope in self.routing_id.routing_line_ids:
            all_operation_ids.append((4, ope.id))
        
        self.all_operation_ids = all_operation_ids
    
    
    @api.one
    @api.depends('disassembly_rl_id', 'assembly_rl_id', 'mo_repair_ope_ids')
    def _compute_use_operation_ids(self):
        """
            All routing_id
        """
        use_operation_ids = []
        if self.disassembly_rl_id:
            use_operation_ids.append((4, self.disassembly_rl_id.id))
        
        if self.assembly_rl_id:
            use_operation_ids.append((4, self.assembly_rl_id.id))
        
        for mo_repair_ope in self.mo_repair_ope_ids:
            use_operation_ids.append((4, mo_repair_ope.rl_id.id))
            
        self.use_operation_ids = use_operation_ids
        
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    repair_date = fields.Date(string='Repair date', default=lambda self: fields.Date.today())
    return_date = fields.Date(string='Return date')
    cause = fields.Text(string='Cause')
    repair_type = fields.Selection('_repair_type_get', string='Repair type', required=True)
    origin_num_serie_id = fields.Many2one('stock.label', string='Origin serial num', required=True, ondelete='cascade')
    is_new_num_serie = fields.Boolean(string='Create a new serial num', default=False)
    wmrl_ids = fields.One2many('wiz.mo.repair.label', 'wiz_mo_repair_id', string='Labels')
    disassembly_rl_id = fields.Many2one('mrp.routing.line', string='Disassembly operation', required=False, ondelete='cascade')
    mo_repair_ope_ids = fields.One2many('wiz.mo.repair.operations', 'wiz_mo_repair_id', string='Routing lines')
    assembly_rl_id = fields.Many2one('mrp.routing.line', string='Assembly operation', required=False, ondelete='cascade')
    routing_id = fields.Many2one('mrp.routing', string='Routing', required=True, ondelete='cascade')
    quantity = fields.Float(string='Quantity', default=1.0, required=True)
    product_id = fields.Many2one('product.product', string='Product', compute='_compute_origin_num_serie_id', store=True)
    origin_product_id = fields.Many2one('product.product', string='Origin product product', ondelete='cascade')
    uom_id = fields.Many2one('product.uom', string='UoM', compute='_compute_origin_num_serie_id', store=True)
    qty_label = fields.Float(string='Label qty', compute='_compute_origin_num_serie_id', store=True)
    intervention_id = fields.Many2one('intervention', string='Intervention', required=False, ondelete='cascade')
    all_operation_ids = fields.Many2many('mrp.routing.line', 'wiz_mo_repair_all_rl_rel', 'wiz_id', 'rl_id',  string='All operations', compute='_compute_all_operation_ids')
    use_operation_ids = fields.Many2many('mrp.routing.line', 'wiz_mo_repair_use_rl_rel', 'wiz_id', 'rl_id',  string='Use operations', compute='_compute_use_operation_ids')
    
    
    #===========================================================================
    # Button
    #===========================================================================
    @api.multi
    def action_validation(self):  
        wo_obj = self.env['mrp.workorder']
        product_obj = self.env['product.product']
        location_obj = self.env['stock.location']
        move_obj = self.env['stock.move']
        wo_resource_obj = self.env['mrp.wo.resource']
        wmro_obj = self.env['wiz.mo.repair.operations']
        mlc_obj = self.env['mrp.label.consumption']
        product_int_rcs = product_obj.search([('is_int', '=', True)], limit=1)
        location_out = location_obj.search([('usage', '=', 'production')], limit=1)
        location_in = location_obj.search([('usage', '=', 'internal')], limit=1)
        list_sequence = []
        for wiz in self:
            mo_rcs = False
            intervention_id = wiz.intervention_id and wiz.intervention_id.id or False
            min_start_date = wiz.intervention_id and wiz.intervention_id.start_date_requested and '%s 06:00:00'%(wiz.intervention_id.start_date_requested) or False
            max_end_date = wiz.intervention_id and wiz.intervention_id.ended_date_requested and '%s 16:00:00'%(wiz.intervention_id.ended_date_requested) or False
            other_data_arg_mo = {'intervention_id': intervention_id,
                                 'requested_date': wiz.repair_date,
                                 'max_end_date': wiz.return_date,
                                 'note_manufacturing': wiz.cause,
                                 'min_start_date': min_start_date,
                                 'max_end_date': max_end_date,
                                 }
            other_data_arg_wo = {'intervention_id': intervention_id}
            if wiz.mo_repair_ope_ids:
                arg_rl_sequences = []
                routing_line_ids = []
                for x in self.mo_repair_ope_ids:
                    arg_rl_sequences.append((x.sequence, x.rl_id.id))
                    routing_line_ids.append(x.rl_id.id)
                    if Decimal(str(x.sequence)) % Decimal(str(10)):
                        raise except_orm(_('Error'), _('The sequence field must be a multiple of 10.'))
                    
                    list_sequence.append(x.sequence)
                   
                no_wo = {'quantity': wiz.quantity, 'uom': wiz.uom_id, 'product': wiz.product_id, 'routing_id': wiz.routing_id.id} 
                mo_rcs = wo_obj.add_operation_wo(routing_line_ids, True, False, False, False, arg_rl_sequences=arg_rl_sequences, no_wo=no_wo, other_data_arg=other_data_arg_mo)
            
            if wiz.repair_type == 'repair_subset':
                if not mo_rcs:
                    mo_rcs = wo_obj.create_mo_light(wiz.product_id, wiz.quantity, wiz.uom_id, wiz.routing_id.id, bom_id=False, other_data=other_data_arg_mo)

                first_wo_rcs = wo_obj.create_wo_without_bom(wiz.disassembly_rl_id, mo_rcs, 1, other_data_arg=other_data_arg_wo)
                if wiz.mo_repair_ope_ids:
                    last_sequence = wmro_obj.search([('wiz_mo_repair_id', '=', wiz.id)], order='sequence desc', limit=1).sequence + 10
                else:
                    last_sequence = 10
                
                last_wo_rcs = wo_obj.create_wo_without_bom(wiz.assembly_rl_id, mo_rcs, last_sequence, other_data_arg=other_data_arg_wo)
            elif mo_rcs:
                first_wo_rcs = wo_obj.search([('mo_id', '=', mo_rcs.id)], order='sequence asc', limit=1)
                last_wo_rcs = wo_obj.search([('mo_id', '=', mo_rcs.id)], order='sequence desc', limit=1)
            else:
                raise except_orm(_('Error'), _('Please choose at least one operation.'))
            
            if list_sequence:
                if  wiz.repair_type != 'repair_subset':
                    min_sequence = min(list_sequence)
                    max_sequence = max(list_sequence)
                    if list_sequence.count(min_sequence) > 1:
                        raise except_orm(_('Error'), _('It can not be two times the same minimal sequence.'))
                    
                    if list_sequence.count(max_sequence) > 1:
                        raise except_orm(_('Error'), _('It can not be two times the same maximum sequence.'))
            
            # Création matières à consommer et produits finaux
            # Pour le premier OT
            wo_resource_rcs = wo_resource_obj.search([('wo_id', '=', first_wo_rcs.id)], order='sequence asc', limit=1)
            if wo_resource_rcs:
                location_in_int = wo_resource_rcs.resource_id.location_id
            else:
                location_in_int = location_in
            
            move_product_rm = self.add_rm(first_wo_rcs, first_wo_rcs.quantity, wiz.uom_id, wiz.product_id, location_in_int.id, location_out.id, move_obj)
            move_product_rm.assign_label(wiz.origin_num_serie_id, with_scrap=False)
            mlc_obj.create({'wo_id': first_wo_rcs.id,
                            'label_id': wiz.origin_num_serie_id.id,
                            'use_consumption': True,
                            'quantity': wiz.quantity,
                            })
            
            # Pour le dernier OT
            wo_resource_rcs = wo_resource_obj.search([('wo_id', '=', last_wo_rcs.id)], order='sequence asc', limit=1)
            if wo_resource_rcs:
                location_in_int = wo_resource_rcs.resource_id.location_id
            else:
                location_in_int = location_in
                
            self.add_fp(last_wo_rcs, last_wo_rcs.quantity, wiz.uom_id, wiz.product_id, location_in_int.id, location_out.id, move_obj)
            if not wiz.is_new_num_serie:
                last_wo_rcs.write({'label_mo_repair_id': wiz.origin_num_serie_id.id})
            
            # Product int
            wo_int_rcs = wo_obj.search([('mo_id', '=', mo_rcs.id), ('id', 'not in', (first_wo_rcs.id, last_wo_rcs.id))])
            for wo_int in wo_int_rcs:
                self.add_fp(wo_int, wo_int.quantity, product_int_rcs.uom_id, product_int_rcs, location_in_int.id, location_out.id, move_obj)
            
            if wiz.repair_type == 'repair_subset':
                self.add_fp(first_wo_rcs, first_wo_rcs.quantity, product_int_rcs.uom_id, product_int_rcs, location_in_int.id, location_out.id, move_obj)
                # Liste des sous ensembles à démonter
                dico_label_ids = {}
                for wmrl in wiz.wmrl_ids:
                    label = wmrl.label_id
                    if label.product_id in dico_label_ids:
                        dico_label_ids[label.product_id]['uom_qty'] += Decimal(str(wmrl.uom_qty))
                        dico_label_ids[label.product_id]['label_rcs'] += label
                        dico_label_ids[label.product_id]['dict_label_qty'][label] = (wmrl.uom_qty, 0)
                    else:
                        dico_label_ids[label.product_id] = {'label_rcs': label,
                                                            'uom_rcs': label.uom_id,
                                                            'uom_qty': Decimal(str(wmrl.uom_qty)),
                                                            'dict_label_qty': {label:(wmrl.uom_qty, 0)}}
                    
                    mlc_obj.create({'wo_id': last_wo_rcs.id,
                                    'label_id': label.id,
                                    'use_consumption': True,
                                    'quantity': wmrl.uom_qty})
                
                for dico_label in dico_label_ids:  
                    move_fp = self.add_fp(first_wo_rcs, dico_label_ids[dico_label]['uom_qty'], dico_label_ids[dico_label]['uom_rcs'], dico_label, location_in_int.id, location_out.id, move_obj)
                    move_fp.assign_label(dico_label_ids[dico_label]['label_rcs'], dict_label_qty=dico_label_ids[dico_label]['dict_label_qty'], with_scrap=False)
                    self.add_rm(last_wo_rcs, dico_label_ids[dico_label]['uom_qty'], dico_label_ids[dico_label]['uom_rcs'], dico_label, location_in_int.id, location_out.id, move_obj)
                    
            else:
                if first_wo_rcs != last_wo_rcs:
                    self.add_fp(first_wo_rcs, first_wo_rcs.quantity, product_int_rcs.uom_id, product_int_rcs, location_in_int.id, location_out.id, move_obj)
            
            # Construction des suivants/précédents
            if first_wo_rcs != last_wo_rcs:
                new_sequence_next_rcs = wo_obj.search([('mo_id', '=', mo_rcs.id), ('sequence', '>', first_wo_rcs.sequence)], order='sequence asc', limit=1)
                if new_sequence_next_rcs:
                    new_sequence_next = new_sequence_next_rcs.read(['sequence'])[0]['sequence']
                    self.recursive_prev_next_wo(mo_rcs, first_wo_rcs, new_sequence_next, wo_obj)
            
            return {'name': _('Manufacturing order for repair'),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'mrp.manufacturingorder',
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'res_id': mo_rcs.id,
                    'nodestroy': True}
            
        return {'type': 'ir.actions.act_window_close'}


    def add_rm(self, wo, quantity, uom, product, location_id, location_dest_id, move_obj):
        efficient_unit_qty = wo.quantity and float(quantity) / wo.quantity or float(quantity)
        move = move_obj.create_move(product, 
                                    location_id, 
                                    location_dest_id, 
                                    qty=float(quantity), 
                                    uom=uom, 
                                    other_data={'wo_incoming_id':wo.id, 
                                                'efficient_unit_qty':efficient_unit_qty, 
                                                'is_forecast': wo.is_forecast,}, 
                                    in_product_uom=True)
        
        return move


    def add_fp(self, wo, quantity, uom, product, location_id, location_dest_id, move_obj):
        efficient_unit_qty = wo.quantity and float(quantity)/wo.quantity or float(quantity)
        move = move_obj.create_move(product, 
                                    location_dest_id, 
                                    location_id, 
                                    qty=float(quantity), 
                                    uom=uom, 
                                    other_data={'wo_outgoing_id':wo.id, 
                                                'efficient_unit_qty':efficient_unit_qty, 
                                                'is_forecast': wo.is_forecast,}, 
                                    in_product_uom=True)
        
        return move
    
    
    def recursive_prev_next_wo(self, mo_rcs, wo_prec_rcs, sequence_next, wo_obj):
        wo_next_rcs = wo_obj.search([('mo_id', '=', mo_rcs.id), ('sequence', '=', sequence_next)])
        wo_prec_rcs.write({'next_wo_ids': [(6, 0, wo_next_rcs.ids)]})
        new_sequence_next_rcs = wo_obj.search([('mo_id', '=', mo_rcs.id), ('sequence', '>', wo_next_rcs[0].sequence)], order='sequence asc', limit=1)
        if new_sequence_next_rcs:
            new_sequence_next = new_sequence_next_rcs.read(['sequence'])[0]['sequence']
            self.recursive_prev_next_wo(mo_rcs, wo_next_rcs, new_sequence_next, wo_obj)
            
        return True
    
    
    @api.multi
    def action_select_label(self):
        for wiz in self:
            wmrsl = self.env['wiz.mo.repair.select.label'].create({'wiz_mo_repair_id': wiz.id})
            return {'name': _('Select labels'),
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'wiz.mo.repair.select.label',
                        'type': 'ir.actions.act_window',
                        'target': 'stack',
                        'res_id': wmrsl.id,
                        'nodestroy': True,
                        }
    
    

class wiz_mo_repair_operations(models.TransientModel):
    """ 
        Wiz manufacturing order for repair operations
    """
    _name = 'wiz.mo.repair.operations'
    _description = 'Wiz manufacturing order for repair operations'
    _rec_name = 'rl_id'
    _order = 'sequence asc'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wiz_mo_repair_id = fields.Many2one('wiz.mo.repair', string='Manufacturing order for repair', required=False, ondelete='cascade')
    rl_id = fields.Many2one('mrp.routing.line', string='Operation', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=None, required=True)



class wiz_mo_repair_label(models.TransientModel):
    """ 
        Wiz manufacturing order for repair label
    """
    _name = 'wiz.mo.repair.label'
    _description = 'Wiz manufacturing order for repair label'
    _rec_name = 'label_id'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wiz_mo_repair_id = fields.Many2one('wiz.mo.repair', string='Manufacturing order for repair', required=False, ondelete='cascade')
    label_id = fields.Many2one('stock.label', string='Label', required=True, ondelete='cascade')
    uom_qty = fields.Float(string='UoM qty', default=0.0, required=True)



class wiz_mo_repair_select_label(models.TransientModel):
    """ 
        Wiz manufacturing order for repair select label
    """
    _name = 'wiz.mo.repair.select.label'
    _description = 'Wiz manufacturing order for repair select label'
    _rec_name = 'wiz_mo_repair_id'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wiz_mo_repair_id = fields.Many2one('wiz.mo.repair', string='Manufacturing order for repair', required=False, ondelete='cascade')
    label_ids = fields.Many2many('stock.label', 'wiz_mo_repair_select_label_label_rel', 'wiz_id', 'label_id',  string='List of subset has disassembles')
    
    
    #===========================================================================
    # Button
    #===========================================================================
    @api.multi
    def action_validation(self):  
        wmrl_obj = self.env['wiz.mo.repair.label']
        for wiz in self:
            for label in wiz.label_ids:
                wmrl_obj.create({'wiz_mo_repair_id': wiz.wiz_mo_repair_id.id,
                                 'label_id': label.id,
                                 'uom_qty': label.origin_uom_qty,})
            
            return True
            
            
            
    