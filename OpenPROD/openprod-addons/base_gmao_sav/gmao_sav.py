# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from datetime import datetime, timedelta
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm, ValidationError, Warning
from dateutil.relativedelta import relativedelta


class park(models.Model):
    """ 
        Park 
    """
    _name = 'park'
    _description = 'Park'
    
    
    @api.model
    def _type_get(self):
        return [
                ('intern', _('Intern')),
                ('external', _('External')),
                       ]
    
    
    @api.model
    def _state_get(self):
        return [
                ('inactive', _('Inactive')),
                ('activity', _('In activity')),
                ('maintenance', _('Under maintenance')),
                       ]
    
    
    @api.one
    @api.depends('guarantee_start_date', 'piece_guarantee')
    def _compute_piece_guarantee_end_date(self):
        """
            Fonction qui calcule la date de fin de garantie pour les pièces
        """
        piece_guarantee_end_date = False
        if self.guarantee_start_date:
            if self.piece_guarantee:
                piece_guarantee_end_date = fields.Date.to_string(fields.Date.from_string(self.guarantee_start_date) + relativedelta(months=self.piece_guarantee))
            else:
                piece_guarantee_end_date = self.guarantee_start_date
                
        self.piece_guarantee_end_date = piece_guarantee_end_date
    
    
    @api.one
    @api.depends('guarantee_start_date', 'workforce_guarantee')
    def _compute_workforce_guarantee_end_date(self):
        """
            Fonction qui calcule la date de fin de garantie pour la main d'oeuvre
        """
        workforce_guarantee_end_date = False
        if self.guarantee_start_date:
            if self.workforce_guarantee:
                workforce_guarantee_end_date = fields.Date.to_string(fields.Date.from_string(self.guarantee_start_date) + relativedelta(months=self.workforce_guarantee))
            else:
                workforce_guarantee_end_date = self.guarantee_start_date
                
        self.workforce_guarantee_end_date = workforce_guarantee_end_date


    @api.one
    @api.depends('num_serie_id')
    def _compute_num_serie_id(self):
        """
            Fonction qui calcule la date de fin de garantie pour la main d'oeuvre
        """
        product_id = False
        is_active_label = False
        if self.num_serie_id:
            product_id = self.num_serie_id.product_id.id
            is_active_label = self.num_serie_id.is_active
            
        self.product_id = product_id
        self.is_active_label = is_active_label
        
        
    @api.one
    def _get_picture_binary_filesystem(self):
        attachment_obj = self.env['ir.attachment']
        attachment_rs = attachment_obj.search([('res_model','=',self._name),('res_id','=',self.id),('binary_field','=','picture')])
        if attachment_rs:
            self['picture'] = attachment_rs[0].datas
    
    
    @api.one
    def _set_picture_binary_filesystem(self):
        attachment_obj = self.env['ir.attachment']
        attachment_rs = attachment_obj.search([('res_model','=',self._name),('res_id','=',self.id),('binary_field','=','picture'),('is_binary_field','=',True)])
        if self.picture:
            if attachment_rs:
                attachment_rs.datas = self.picture
            else:
                attachment_obj.create({'res_model': self._name, 
                                       'res_id': self.id, 
                                       'name': 'picture datas' , 
                                       'is_binary_field': True, 
                                       'binary_field': 'picture', 
                                       'datas': self.picture, 
                                       'datas_fname': 'picture datas', 
                                       'type': 'binary'})
        else:
            attachment_rs.unlink()
        
    
    @api.one
    @api.depends('maintenance_operation_ids')
    def _all_operation_compute(self):
        """
            All resource pour le domaine
        """
        self.all_operation_ids = [x.maintenance_operation_id.id for x in self.maintenance_operation_ids]
    
    
    def compute_recursive_park(self):
        park_ids = [self.id]
        park_child_rcs = self.search([('parent_equipment_id', '=', self.id), ('is_equipment', '=', True)])
        for park_child in park_child_rcs:
            park_ids.extend(park_child.compute_recursive_park())
        
        return park_ids
    
    
    def compute_child_structure_ids(self):
        """
            Fonction qui calcule la structure
        """
        park_ids = []
        park_child_rcs = self.search([('parent_equipment_id', '=', self.id), ('is_equipment', '=', True)])
        if park_child_rcs:
            park_ids = park_child_rcs.ids
            
        return park_ids
    
    
    def _compute_child_structure_complete_ids(self):
        """
            Fonction qui calcule la structure
        """
        park_ids = []
        park_child_rcs = self.search([('parent_equipment_id', '=', self.id), ('is_equipment', '=', True)])
        for park_child in park_child_rcs:
            park_ids.extend(park_child.compute_recursive_park())
            
        return park_ids
    
    
    @api.one         
    def _compute_child_structure_ids(self):
        """
            Fonction qui calcule la structure
        """
        park_ids = self.compute_child_structure_ids()
        self.child_structure_ids = park_ids
    
    
    def additional_function_domain(self, arg):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de mrp_resource
        """
        arg0, arg1, arg_1 = False, False, False
        if arg and arg[0] == 'domain_park':
            arg0 = 'id'
            arg1 = 'in'
            already_used_park_ids = []
            all_park_ids = self.search([]).ids
            if arg[-1]:
                for x in arg[-1]:
                    if x[1] not in already_used_park_ids:
                        already_used_park_ids.append(x[1])
            
            if already_used_park_ids and all_park_ids:
                all_park_ids = list(set(all_park_ids) - set(already_used_park_ids))
            
            arg_1 = list(set(all_park_ids))
            
        if arg[0] == 'domain_certificate_management':
            arg0 = 'id'
            arg1 = arg[1]
            arg_1 = eval(arg[-1])
            
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
        return super(park,self).search(args=args_modified, offset=offset, limit=limit, order=order, count=count) 
    
    
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
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=False, size=256)
    state = fields.Selection('_state_get', string='State', default='activity', required=True)
    num_serie_id = fields.Many2one('stock.label', string='Serial num', required=False, ondelete='restrict')
    product_id = fields.Many2one('product.product', string='Product', compute='_compute_num_serie_id', ondelete='restrict', store=True)
    type = fields.Selection('_type_get', string='Type', required=True)
    customer_id = fields.Many2one('res.partner', string='Customer', required=False, ondelete='restrict')
    supplier_id = fields.Many2one('res.partner', string='Supplier', required=False, ondelete='restrict')
    resource_id = fields.Many2one('mrp.resource', string='Resource', required=False, ondelete='restrict')
    is_equipment = fields.Boolean(string='Equipment', default=False)
    is_active_label = fields.Boolean(string='Active label', compute='_compute_num_serie_id')
    #historique
    date_create = fields.Date(string='Create date')
    delivery_date = fields.Date(string='Delivery date')
    commissioning_date = fields.Date(string='Commissioning date')
    guarantee_start_date = fields.Date(string='Guarantee start date')
    guarantee = fields.Integer(string='Guarantee', default=0, required=False)
    guarantee_unity_id = fields.Many2one('product.uom', string='Guarantee unity', required=False, ondelete='restrict')
    description = fields.Text(string='Description')
    #equipment
    manufacturing_name = fields.Char(string='Manufacturing name', size=256, required=False)
    release_date = fields.Date(string='Release date')
    workforce_guarantee = fields.Integer(string='Workforce guarantee (months)', default=0, required=False)
    workforce_guarantee_end_date = fields.Date(string='Workforce guarantee end date', compute='_compute_workforce_guarantee_end_date', store=True)
    piece_guarantee = fields.Integer(string='Pieces guarantee (months)', default=0, required=False)
    piece_guarantee_end_date = fields.Date(string='Piece guarantee end date', compute='_compute_piece_guarantee_end_date', store=True)
    picture = fields.Binary(string='Picture', compute='_get_picture_binary_filesystem', inverse='_set_picture_binary_filesystem', help='help')
    parent_equipment_id = fields.Many2one('park', string='Parent park', required=False, ondelete='restrict')
    #maintenance
    all_operation_ids = fields.One2many('maintenance.operation', compute='_all_operation_compute',  string='All operations')
    maintenance_operation_ids = fields.One2many('park.maintenance.operation', 'park_id', 'Park maintenances operations')
    counter_ids = fields.One2many('park.counter', 'park_id',  string='Counters')
    #plan
    document_ids = fields.Many2many('document.openprod', 'park_document_openprod_rel', 'park_id', 'document_id',  string='Document')
    note_ids = fields.One2many('note.openprod', 'park_id', string='Notes')
    #structure
    child_structure_ids = fields.One2many('park', compute='_compute_child_structure_ids')
    child_structure_complete_ids = fields.One2many('park', compute='_compute_child_structure_complete_ids')
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('num_serie_id', 'is_equipment', 'customer_id')
    def _onchange_product_id(self):
        """
            Onchange du produit
        """
        name, guarantee, guarantee_unity_id = self.onchange_product_id(self.num_serie_id, self.is_equipment, self.customer_id)
        if self.num_serie_id and self.num_serie_id.product_id:
            self.name = name
            
        self.guarantee = guarantee
        self.guarantee_unity_id = guarantee_unity_id
    
    
    def onchange_product_id(self, num_serie, is_equipment, customer=False):
        """
            Onchange du produit
        """
        guarantee = 0
        guarantee_unity_id = False
        name = ''
        if num_serie and num_serie.product_id:
            product_read = num_serie.product_id.read(['guarantee', 'guarantee_unity_id', 'name', 'code'], load='_classic_write')
            name = '[%s/%s] %s'%(num_serie.name, product_read[0]['code'], product_read[0]['name'])
            if not is_equipment:
                if customer:
                    customer_read = customer.read(['guarantee', 'guarantee_unity_id'], load='_classic_write')
                else:
                    customer_read = False
                    
                if customer_read and customer_read[0]['guarantee']:
                    guarantee = customer_read[0]['guarantee']
                    guarantee_unity_id = customer_read[0]['guarantee_unity_id']
                else:
                    guarantee = product_read[0]['guarantee']
                    guarantee_unity_id = product_read[0]['guarantee_unity_id']
        
        return name, guarantee, guarantee_unity_id
    
    
    @api.onchange('type', 'is_equipment')
    def _onchange_type(self):
        if self.type == 'external' or not self.is_equipment:
            self.resource_id = False
    
    
    @api.onchange('num_serie_id')
    def _onchange_num_serie_id(self):
        if self.num_serie_id:
            self.date_create = self.num_serie_id.read(['create_date'])[0]['create_date']
            move_obj = self.env['stock.move']
            move_label_obj = self.env['stock.move.label']
            move_label_rcs = move_label_obj.search([('label_id', '=', self.num_serie_id.id)])
            move_ids = [move_label_read['move_id'] for move_label_read in move_label_rcs.read(['move_id'], load='_classic_write')]
            if move_ids:
                move_ids = list(set(move_ids))
                arg_move = [('type', '=', 'out'), ('id', 'in', move_ids), ('picking_id', '!=', False)]
                move_rcs = move_obj.search(arg_move, order='date asc', limit=1)
                if move_rcs:
                    self.delivery_date = move_rcs.date
                    
                arg_move_customer = [('type', '=', 'out'), ('id', 'in', move_ids), ('picking_id', '!=', False), 
                                     ('picking_id', '!=', False), ('sale_line_id', '!=', False)]
                move_customer_rcs = move_obj.search(arg_move_customer, order='date asc', limit=1)
                if move_customer_rcs:
                    self.customer_id = move_customer_rcs.sale_line_id.sale_partner_id.id
            
    
    def onchange_num_serie_id(self, num_serie):
        customer_id = False
        delivery_date = False
        if num_serie:
            date_create = num_serie.read(['create_date'])[0]['create_date']
            move_obj = self.env['stock.move']
            move_label_obj = self.env['stock.move.label']
            move_label_rcs = move_label_obj.search([('label_id', '=', num_serie.id)])
            move_ids = [move_label_read['move_id'] for move_label_read in move_label_rcs.read(['move_id'], load='_classic_write')]
            if move_ids:
                move_ids = list(set(move_ids))
                arg_move = [('type', '=', 'out'), ('id', 'in', move_ids), ('picking_id', '!=', False)]
                move_rcs = move_obj.search(arg_move, order='date asc', limit=1)
                if move_rcs:
                    delivery_date = move_rcs.date
                    
                arg_move_customer = [('type', '=', 'out'), ('id', 'in', move_ids), ('picking_id', '!=', False), 
                                     ('picking_id', '!=', False), ('sale_line_id', '!=', False)]
                move_customer_rcs = move_obj.search(arg_move_customer, order='date asc', limit=1)
                if move_customer_rcs:
                    customer_id = move_customer_rcs.sale_line_id.sale_partner_id.id
        
        return customer_id, delivery_date, date_create
    
    
    
    #===========================================================================
    # Button
    #===========================================================================
    @api.multi
    def delete_operation(self):
        for park in self:
            if park.maintenance_operation_ids:
                park.maintenance_operation_ids.unlink()
        
        return True

    
    @api.multi
    def button_list_intervention(self):
        interv_obj = self.env['intervention']
        for park in self:
            intervention_rcs = interv_obj.search([('park_id', '=', park.id)])
            intervention_ids = intervention_rcs and intervention_rcs.ids or []
            return {'name': _('Interventions'),
                        'view_type': 'form',
                        'view_mode': 'tree,form',
                        'res_model': 'intervention',
                        'type': 'ir.actions.act_window',
                        'domain': [('id', 'in', intervention_ids)],
                        'target': 'current',
                        'nodestroy': True,
                        }
            
    
    @api.multi
    def button_list_purchase(self):
        interv_obj = self.env['intervention']
        pmi_obj = self.env['piece.maintenance.intervention']
        for park in self:
            intervention_rcs = interv_obj.search([('park_id', '=', park.id)])
            purchase_ids = []
            if intervention_rcs:
                pmi_rcs = pmi_obj.search([('intervention_id', 'in', intervention_rcs.ids), ('purchase_id', '!=', False)])
                purchase_ids = [x.purchase_id.id for x in pmi_rcs]
                
            return {'name': _('Purchases'),
                        'view_type': 'form',
                        'view_mode': 'tree,form',
                        'res_model': 'purchase.order',
                        'type': 'ir.actions.act_window',
                        'domain': [('id', 'in', purchase_ids)],
                        'target': 'current',
                        'nodestroy': True,
                        }
            
        
    @api.multi
    def button_list_timetracking(self):
        interv_obj = self.env['intervention']
        timetracking_obj = self.env['resource.timetracking']
        for park in self:
            intervention_rcs = interv_obj.search([('park_id', '=', park.id)])
            timetracking_ids = []
            if intervention_rcs:
                timetracking_rcs = timetracking_obj.search([('intervention_id', 'in', intervention_rcs.ids)])
                timetracking_ids = timetracking_rcs and timetracking_rcs.ids or []
                
            return {'name': _('Time tracking'),
                        'view_type': 'form',
                        'view_mode': 'tree,form',
                        'res_model': 'resource.timetracking',
                        'type': 'ir.actions.act_window',
                        'domain': [('id', 'in', timetracking_ids)],
                        'target': 'current',
                        'nodestroy': True,
                        }   
        
    
    @api.multi
    def button_list_picking(self):
        interv_obj = self.env['intervention']
        pmi_obj = self.env['piece.maintenance.intervention']
        move_obj = self.env['stock.move']
        move_label_obj = self.env['stock.move.label']
        for park in self:
            intervention_rcs = interv_obj.search([('park_id', '=', park.id)])
            picking_ids = []
            if intervention_rcs:
                pmi_rcs = pmi_obj.search([('intervention_id', 'in', intervention_rcs.ids), ('picking_id', '!=', False)])
                picking_ids = [x.picking_id.id for x in pmi_rcs]
            
            if park.num_serie_id:
                move_label_rcs = move_label_obj.search([('label_id', '=', park.num_serie_id.id)])
                move_ids = [move_label_read['move_id'] for move_label_read in move_label_rcs.read(['move_id'], load='_classic_write')]
                if move_ids:
                    move_ids = list(set(move_ids))
                    arg_move = [('type', '=', 'out'), ('id', 'in', move_ids), ('picking_id', '!=', False)]
                    if picking_ids:
                        arg_move.append(('picking_id', 'not in', picking_ids))
                        
                    move_rcs = move_obj.search(arg_move)
                    for move_read in move_rcs.read(['picking_id'], load='_classic_write'):
                        if move_read['picking_id'] not in picking_ids:
                            picking_ids.append(move_read['picking_id'])
                
            return {'name': _('Pickings'),
                        'view_type': 'form',
                        'view_mode': 'tree,form',
                        'res_model': 'stock.picking',
                        'type': 'ir.actions.act_window',
                        'domain': [('id', 'in', picking_ids)],
                        'target': 'current',
                        'nodestroy': True,
                        }
    
    
    @api.multi
    def button_list_sale(self):
        interv_obj = self.env['intervention']
        sale_obj = self.env['sale.order']
        move_obj = self.env['stock.move']
        sol_obj = self.env['sale.order.line']
        move_label_obj = self.env['stock.move.label']
        for park in self:
            intervention_rcs = interv_obj.search([('park_id', '=', park.id)])
            sale_ids = []
            if intervention_rcs:
                sale_ids.append(intervention_rcs.sale_id.id)
            
            if park.num_serie_id:
                move_label_rcs = move_label_obj.search([('label_id', '=', park.num_serie_id.id)])
                move_ids = [move_label_read['move_id'] for move_label_read in move_label_rcs.read(['move_id'], load='_classic_write')]
                if move_ids:
                    move_ids = list(set(move_ids))
                    arg_move = [('type', '=', 'out'), ('id', 'in', move_ids), ('picking_id', '!=', False), ('sale_line_id', '!=', False)]
                          
                    move_rcs = move_obj.search(arg_move)
                    sale_line_ids = []
                    for move_read in move_rcs.read(['sale_line_id'], load='_classic_write'):
                        sale_line_ids.append(move_read['sale_line_id'])
                    
                    if sale_line_ids:
                        for sol_read in sol_obj.browse(sale_line_ids).read(['sale_order_id'], load='_classic_write'):
                            if sol_read['sale_order_id'] not in sale_ids:
                                sale_ids.append(sol_read['sale_order_id'])
            
            
            return {'name': _('Sales'),
                        'view_type': 'form',
                        'view_mode': 'tree,form',
                        'res_model': 'sale.order',
                        'type': 'ir.actions.act_window',
                        'domain': [('id', 'in', sale_ids)],
                        'target': 'current',
                        'nodestroy': True,
                        }
    
    
    @api.multi
    def button_return_move(self):
        move_label_obj = self.env['stock.move.label']
        move_obj = self.env['stock.move']
        for park in self:
            move_label_rcs = move_label_obj.search([('label_id', '=', park.num_serie_id.id)])
            move_ids = [move_label_read['move_id'] for move_label_read in move_label_rcs.read(['move_id'], load='_classic_write')]
            if move_ids:
                move_ids = list(set(move_ids))
                arg_move = [('type', '=', 'out'), ('id', 'in', move_ids), ('picking_id', '!=', False), ('sale_line_id', '!=', False), ('state', '!=', 'cancel')]
                move_rcs = move_obj.search(arg_move, order='date desc', limit=1)
                if not move_rcs:
                    arg_move = [('type', '=', 'out'), ('id', 'in', move_ids), ('picking_id', '!=', False), ('state', '!=', 'cancel')]
                    move_rcs = move_obj.search(arg_move, order='date desc', limit=1)
                
                if move_rcs:
                    picking_id = move_rcs.picking_id.id
                    move_and_label_rcs = [(move_rcs.id, park.num_serie_id.id, park.num_serie_id.origin_uom_qty)]
                    return {
                            'name': _('Return picking'),
                            'view_type': 'form',
                            'view_mode': 'form',
                            'res_model': 'stock.return.picking',
                            'type': 'ir.actions.act_window',
                            'target': 'new',
                            'nodestroy': True,
                            'context': {'move_and_label_rcs': move_and_label_rcs, 'picking_id': picking_id, 'park_id': park.id, 'authorize_return': True}
                    }
                
                else:
                    raise except_orm(_('Error'), _('No move out.'))
            
        return True
    
    @api.multi
    def wkf_activity(self):
        self.write({'state': 'activity'})
    
    
    @api.multi
    def wkf_maintenance(self):
        self.write({'state': 'maintenance'})
        
        
    @api.multi
    def button_create_intervention(self):
        interv_obj = self.env['intervention']
        for park in self:
            vals = {'start_date_requested': fields.Date.today(),
                    'emergency': 'high',
                    'park_id': park.id,
                    'type': 'preventive'
            }
            if park.type == 'external':
                vals['customer_id'] = park.customer_id.id
                vals['currency_id'] = park.customer_id.currency_id.id
            
            vals['type_invoice'] = 'billable'
            intervention_rcs = interv_obj.create(vals)
            park.wkf_maintenance()
            if park.type == 'external':
                return intervention_rcs.id
            else:
                return {
                        'name': _('Intervention'),
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'intervention',
                        'type': 'ir.actions.act_window',
                        'target': 'current',
                        'res_id': intervention_rcs.id,
                        'nodestroy': True,
                }
            
        return True
    
    
    def create_park(self, label, type, is_equipment=False):
        vals = {'num_serie_id': label.id}
        customer_id, delivery_date, date_create = self.onchange_num_serie_id(label)
        name, guarantee, guarantee_unity_id = self.onchange_product_id(label, is_equipment, customer=self.env['res.partner'].browse(customer_id))
        vals['name'] = name
        vals['type'] = type
        vals['guarantee'] = guarantee
        vals['guarantee_unity_id'] = guarantee_unity_id
        vals['customer_id'] = customer_id
        vals['delivery_date'] = delivery_date
        vals['date_create'] = date_create
        vals['is_equipment'] = is_equipment
        if type == 'external' or not is_equipment:
            vals['resource_id'] = False
        
        return self.create(vals)
    
    

class park_maintenance_operation(models.Model):
    """ 
        Park maintenance operation
    """
    _name = 'park.maintenance.operation'
    _description = 'Park maintenance operation'
    _rec_name = 'maintenance_operation_id'
    
    
    @api.one
    @api.depends('maintenance_operation_id')
    def _compute_time_spent(self):
        self.time_spent = self.maintenance_operation_id.intervention_time
    
    
    @api.one
    @api.depends('park_id')
    def _compute_intervention_last_date(self):
        last_intervention_rcs = self.env['intervention'].search([('state', '=', 'done'), 
                                                                 ('park_id', '=', self.park_id.id), 
                                                                 ('ended_date_real', '!=', False)], order='ended_date_real desc')
        
        intervention_last_date = False
        if last_intervention_rcs:
            intervention_last_date = last_intervention_rcs.read(['ended_date_real'], load='_classic_write')[0]['ended_date_real']
            
        self.intervention_last_date = intervention_last_date
        
    
    @api.one
    @api.depends('park_id')
    def _compute_intervention_next_date(self):
        intervention_next_date = False
        if self.intervention_last_date and self.maintenance_operation_id and self.maintenance_operation_id.trigger_mode == 'calendar' and self.maintenance_operation_id.frequency and self.maintenance_operation_id.frequency_type:
            if self.maintenance_operation_id.frequency_type == 'quarter':
                frequency = self.maintenance_operation_id.frequency*3
                intervention_next_date = fields.Date.to_string(fields.Date.from_string(self.intervention_last_date) + relativedelta(months=frequency))
            elif self.maintenance_operation_id.frequency_type == 'day':
                intervention_next_date = fields.Date.to_string(fields.Date.from_string(self.intervention_last_date) + timedelta(days=self.maintenance_operation_id.frequency))
            elif self.maintenance_operation_id.frequency_type == 'week':
                frequency = self.maintenance_operation_id.frequency*7
                intervention_next_date = fields.Date.to_string(fields.Date.from_string(self.intervention_last_date) + timedelta(days=frequency))
            elif self.maintenance_operation_id.frequency_type == 'month':
                intervention_next_date = fields.Date.to_string(fields.Date.from_string(self.intervention_last_date) + relativedelta(months=self.maintenance_operation_id.frequency))
            elif self.maintenance_operation_id.frequency_type == 'year':
                intervention_next_date = fields.Date.to_string(fields.Date.from_string(self.intervention_last_date) + relativedelta(years=self.maintenance_operation_id.frequency))
        
        self.intervention_next_date = intervention_next_date
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    park_id = fields.Many2one('park', string='Park', required=True, ondelete='restrict')
    maintenance_operation_id = fields.Many2one('maintenance.operation', string='Maintenance operation', required=True, ondelete='restrict')
    time_spent = fields.Float(string='Time spent', compute='_compute_time_spent', required=False, digits=dp.get_precision('Product quantity'))
    intervention_last_date = fields.Date(string='Intervention last date', compute='_compute_intervention_last_date')
    intervention_next_date = fields.Date(string='Intervention next date', compute='_compute_intervention_next_date')



class park_counter(models.Model):
    """ 
        Park counter
    """
    _name = 'park.counter'
    _description = 'Park counter'
    _rec_name = 'counter_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    park_id = fields.Many2one('park', string='Park', required=False, ondelete='restrict')
    counter_id = fields.Many2one('counter', string='Counter', required=True, ondelete='restrict')
    value = fields.Float(string='Value', default=0.0, required=False, digits=dp.get_precision('Product quantity'))
    remark = fields.Text(string='Remark')
    date = fields.Date(string='Date', default=lambda self: fields.Date.today(), required=True)
    
    

class counter(models.Model):
    """ 
        Counter 
    """
    _name = 'counter'
    _description = 'Counter'
    
    
    @api.multi
    def name_get(self):
        """
            Name get de la nomenclature [name_bom] name_product
        """
        result = []
        for event in self:
            if event.min_limit and event.max_limit:
                name = '%s [%.2f-%.2f] '%(event.name, event.min_limit, event.max_limit)
            else:
                name = event.name
                
            result.append((event.id, name))
            
        return result
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Name', size=256, required=True)
    uom_id = fields.Many2one('product.uom', string='UoM', required=False, ondelete='restrict')
    min_limit = fields.Float(string='Min limit', default=0.0, required=False, digits=dp.get_precision('Product quantity'))
    max_limit = fields.Float(string='Max limit', default=0.0, required=False, digits=dp.get_precision('Product quantity'))
    comment = fields.Text(string='Comment')



class maintenance_operation(models.Model):
    """ 
        Maintenance operation 
    """
    _name = 'maintenance.operation'
    _description = 'Maintenance operation'

    
    @api.model
    def _type_get(self):
        return [
                ('preventive', _('Preventive')),
                ('corrective', _('Corrective')),
                ('security', _('Security')),
                ]

    
    @api.model
    def _tolerance_get(self):
        return [
                ('day', _('Day')),
                ('week', _('Week')),
                ('month', _('Month')),
                ('quarter', _('Quarter')),
                ('year', _('Year')),
                ]

    
    @api.model
    def _trigger_mode_get(self):
        return [
                ('manual', _('Manual')),
                ('counter', _('Counter')),
                ('calendar', _('Calendar')),
                       ]
    
    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('active', _('Active')),
                ('obsolete', _('Obsolete')),
                       ]
    
    
    @api.one
    @api.depends('categ_resource_ids')
    def _all_resource_compute(self):
        """
            All resource pour le domaine
        """
        all_resource_ids = []
        for crmo in self.categ_resource_ids:
            for resource in crmo.categ_resource_id.resource_ids:
                if resource.id not in all_resource_ids:
                    all_resource_ids.append(resource.id)
            
        self.all_resource_ids = all_resource_ids 
    
    
    def additional_function_domain(self, arg):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de mrp_resource
        """
        arg0, arg1, arg_1 = False, False, False
        if arg and arg[0] == 'domain_maintenance_operation':
            arg0 = 'id'
            arg1 = 'in'
            already_used_operation_ids = []
            all_operation_ids = self.search([]).ids
            if arg[-1]:
                for x in arg[-1]:
                    if x[1] not in already_used_operation_ids:
                        already_used_operation_ids.append(x[1])
            
            if already_used_operation_ids and all_operation_ids:
                all_operation_ids = list(set(all_operation_ids) - set(already_used_operation_ids))
        
            arg_1 = list(set(all_operation_ids))
        elif arg and arg[0] == 'domain_park_id':
            arg0 = 'id'
            arg1 = 'in'
            maintenance_operation_ids = []
            if arg[-1]:
                pmo_rcs = self.env['park.maintenance.operation'].search([('park_id', '=', arg[-1])])
                for pmo in pmo_rcs:
                    if pmo.maintenance_operation_id:
                        maintenance_operation_ids.append(pmo.maintenance_operation_id.id)
                
            arg_1 = maintenance_operation_ids
          
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
        return super(maintenance_operation,self).search(args=args_modified, offset=offset, limit=limit, order=order, count=count) 
    
    
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=1000):
        """
            Fonction name_search
        """
        args.append(('name', 'ilike', name))
        args = self.compute_domain_args_resource(args)
        recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()
    
    
    @api.one
    @api.depends('park_ids')
    def _all_park_compute(self):
        """
            All park pour le domaine
        """
        self.all_park_ids = [x.park_id.id for x in self.park_ids]
        
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Name', size=256, required=True)
    type = fields.Selection('_type_get', string='Type', required=True)
    state = fields.Selection('_state_get', string='State', required=True, default='draft')
    tolerance = fields.Selection('_tolerance_get', string='Tolerance')
    responsible_id = fields.Many2one('res.users', string='Responsible', required=True, ondelete='restrict')
    intervention_time = fields.Float(string='Time of intervention (HH:MM)', default=0.0, required=False, digits=dp.get_precision('Product quantity'))
    time_synchro_resource = fields.Boolean(string='Time synchronized with the resources', default=True)
    description = fields.Text(string='Description')
    #Park
    park_ids = fields.One2many('park.maintenance.operation', 'maintenance_operation_id', 'Maintenances operations park')
    all_park_ids = fields.One2many('park', compute='_all_park_compute',  string='All parks')
    #ressource
    piece_maintenance_ids = fields.One2many('piece.maintenance', 'maintenance_operation_id',  string='Pieces maintenance')
    categ_resource_ids = fields.One2many('categ.resource.maintenance.operation', 'maintenance_operation_id',  string='Categ resource')
    resource_ids = fields.Many2many('mrp.resource', 'resource_maintenance_operation', 'maintenance_operation_id', 'resource_id',  string='Resources')
    all_resource_ids = fields.One2many('mrp.resource', compute='_all_resource_compute',  string='All resources')
    #instruction_notes
    trigger_mode = fields.Selection('_trigger_mode_get', string='Trigger mode')
    counter_id = fields.Many2one('counter', string='Counter', required=False, ondelete='restrict')
    frequency = fields.Integer(string='Frequency', default=0.0, required=False, digits=dp.get_precision('Product quantity'))
    frequency_type = fields.Selection('_tolerance_get', string='Frequency type')
    note = fields.Text(string='Note')
    instruction_maintenance_ids = fields.One2many('instruction.maintenance', 'maintenance_operation_id',  string='Instructions')
        
        
    #===========================================================================
    # Button
    #===========================================================================
    @api.multi
    def delete_park(self):
        for operation in self:
            if operation.park_ids:
                operation.park_ids.unlink()
        
        return True
    
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('time_synchro_resource', 'intervention_time')
    def _onchange_maintenance_operation_id(self):
        """
            Onchange de l'operation de maintenance 
        """
        if self.time_synchro_resource:
            for categ_resource in self.categ_resource_ids:
                categ_resource.time = self.intervention_time
    
    

class piece_maintenance(models.Model):
    """ 
        Pieces of maintenance 
    """
    _name = 'piece.maintenance'
    _description = 'Pieces of maintenance'
    _rec_name = 'description'
    
    
    @api.one
    @api.depends('product_id')
    def _uom_category_compute(self):
        """
            Category UoM
        """
        uom_category_id = False
        if self.product_id:
            uom_category_id = self.uom_id.category_id.id
            
        self.uom_category_id = uom_category_id
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='restrict')
    maintenance_operation_id = fields.Many2one('maintenance.operation', string='Maintenance operation', required=False, ondelete='restrict')
    description = fields.Text(string='Description', required=True)
    qty = fields.Float(string='Qty', default=1.0, required=True, digits=dp.get_precision('Product quantity'))
    uom_id = fields.Many2one('product.uom', string='UoM', required=True, ondelete='restrict')
    uom_category_id = fields.Many2one('product.uom.category', compute='_uom_category_compute', string="UOM category", readonly=True)
    
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
            Onchange du produit
        """
        uom_id = False
        description = ''
        category_id = False
        if self.product_id:
            uom_id = self.product_id.uom_id.id
            category_id = self.product_id.uom_id.category_id.id
            description = '[%s] %s'%(self.product_id.code, self.product_id.name)
            
        self.uom_id = uom_id
        self.description = description
        self.category_id = category_id
        
        

class categ_resource_maintenance_operation(models.Model):
    """ 
        Categ resource maintenance operation
    """
    _name = 'categ.resource.maintenance.operation'
    _description = 'Categ resource maintenance operation'
    _rec_name = 'categ_resource_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    maintenance_operation_id = fields.Many2one('maintenance.operation', string='Maintenance operation', required=False, ondelete='restrict')
    categ_resource_id = fields.Many2one('mrp.resource.category', string='Resource category', required=True, ondelete='restrict')
    time = fields.Float(string='Time', digits=dp.get_precision('Product quantity'), default=0.0)
    
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('maintenance_operation_id', 'maintenance_operation_id.time_synchro_resource', 'maintenance_operation_id.intervention_time')
    def _onchange_maintenance_operation_id(self):
        """
            Onchange de l'operation de maintenance 
        """
        if self.maintenance_operation_id and self.maintenance_operation_id.time_synchro_resource:
            self.time = self.maintenance_operation_id.intervention_time

    
    
class resource_maintenance_operation(models.Model):
    """ 
        Resource maintenance operation
    """
    _name = 'resource.maintenance.operation'
    _description = 'Resource maintenance operation'
    _rec_name = 'resource_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    maintenance_operation_id = fields.Many2one('maintenance.operation', string='Maintenance operation', required=False, ondelete='restrict')
    resource_id = fields.Many2one('mrp.resource', string='Resource', required=True, ondelete='restrict')



class instruction_maintenance(models.Model):
    """ 
        Instruction maintenance
    """
    _name = 'instruction.maintenance'
    _description = 'Instruction maintenance'
    _order = 'sequence asc'

    #===========================================================================
    # COLUMNS
    #===========================================================================
    maintenance_operation_id = fields.Many2one('maintenance.operation', string='Maintenance operation', required=False, ondelete='restrict')
    sequence = fields.Integer(string='Sequence', default=0, required=True)
    name = fields.Char(string='Name', size=256, required=True)
    description = fields.Html(string='Description')
    plan_id = fields.Many2one('document.openprod', string='Plan', required=False, ondelete='restrict')
    time = fields.Float(string='Time', default=0.0, required=False, digits=dp.get_precision('Time'))



class intervention(models.Model):
    """ 
        Intervention
    """
    _name = 'intervention'
    _description = 'Intervention'
    
     
    @api.model
    def _type_get(self):
        return [
                ('preventive', _('Preventive maintenance')),
                ('corrective', _('Corrective maintenance')),
                ('security', _('Security')),
                ('repair_sav', _('Simple SAV repair')),
                ('repair_sav_mo', _('MO SAV repair')),
                ]
 
     
    @api.model
    def _emergency_get(self):
        return [
                ('critical', _('Critical')),
                ('high', _('High')),
                ('medium', _('Medium')),
                ('low', _('Low')),
                ]
         
         
    @api.model
    def _tolerance_get(self):
        return [
                ('day', _('Day')),
                ('week', _('Week')),
                ('month', _('Month')),
                ('quarter', _('Quarter')),
                ('year', _('Year')),
                ]


    @api.model
    def _state_get(self):
        return [
                ('waiting', _('Waiting')),
                ('affect', _('Affect')),
                ('performed', _('Performed')),
                ('done', _('Done')),
                ('cancel', _('Cancel')),
                ]
    
    
    @api.model
    def _park_type_get(self):
        return [
                ('intern', _('Intern')),
                ('external', _('External')),
                       ]
    
    
    @api.one
    @api.depends('start_date_requested', 'tolerance', 'start_date_planned')
    def _compute_alert(self):
        """
            Fonction qui permet de savoir si la date planifié est > date demandé + tolérance
        """
        alert = False
        if self.start_date_requested and self.start_date_requested and self.start_date_planned:
            if self.tolerance == 'quarter':
                date_inter = fields.Date.to_string(fields.Date.from_string(self.start_date_requested) + relativedelta(months=3))
            elif self.tolerance == 'day':
                date_inter = fields.Date.to_string(fields.Date.from_string(self.start_date_requested) + timedelta(days=1))
            elif self.tolerance == 'week':
                date_inter = fields.Date.to_string(fields.Date.from_string(self.start_date_requested) + timedelta(days=7))
            elif self.tolerance == 'month':
                date_inter = fields.Date.to_string(fields.Date.from_string(self.start_date_requested) + relativedelta(months=1))
            elif self.tolerance == 'year':
                date_inter = fields.Date.to_string(fields.Date.from_string(self.start_date_requested) + relativedelta(years=1))
            else:
                date_inter = False
                
            if date_inter and self.start_date_planned > date_inter:
                alert = True
            
        self.alert = alert
     
     
    @api.one
    @api.depends('name')
    def _compute_time_real_interv(self):
        """
            Fonction qui calcule la somme des heures réelle pointé sur l'intervention
        """
        time_real_interv = False
        self.time_real_interv = time_real_interv
     
     
    @api.one
    def _compute_mail(self):
        self.mail_ids = self.env['mail.mail'].search([('model', '=', 'intervention'), ('res_id', '=', self.id)]).ids
        
        
    @api.one
    @api.depends('park_id')
    def _compute_park(self):
        """
            type du park
        """
        self.park_type = self.park_id and self.park_id.type or ''
        self.park_num_serie_id = self.park_id and self.park_id.num_serie_id and self.park_id.num_serie_id.id or False
    
    @api.one
    def _compute_color_kanban(self):
        if self.alert:
            color_kanban = 2
        elif self.start_date_planned and fields.Date.today() > self.start_date_planned:
            color_kanban = 3
        else:
            color_kanban = 0
        
        self.color_kanban = color_kanban
    
    
    @api.one
    @api.depends('start_date_planned')
    def _compute_start_date(self):
        """
        Fonction qui calcule la semaine, le mois et l'année de la date de début
        """
        is_today = False
        is_week = False
        is_month = False
        
        ri_vals = self.read(['start_date_planned'])
        if ri_vals[0]['start_date_planned']:
            date = '%s'%(ri_vals[0]['start_date_planned'][0:10])
            date = datetime.strptime(date, '%Y-%m-%d')
            isocal = date.isocalendar()
            now = datetime.now()
            if now.strftime('%Y-%m-%d') == date:
                is_today = True
            
            if (now + timedelta(days=7)) >= date and date >= now:
                is_week = True
                
            if (now + relativedelta(months=30)) >= date and date >= now:
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
        
        self.is_today = is_today
        self.is_week = is_week
        self.is_month = is_month
    
    
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
        
    def _search_is_today(self, operator, value):
        """
            Fonction search qui permet de retrouver tous les OTs qui sont de cette semaine
        """
        request = """
        SELECT 
            x.id 
        FROM
            (SELECT     
            to_char(start_date_planned, 'YYYY-MM-DD') as date,
            to_char((current_date), 'YYYY-MM-DD') as date_now,
            id
             FROM 
             intervention 
             WHERE
             start_date_planned is not null)  x
        
        where 
            x.date = x.date_now"""
        self.env.cr.execute(request)
        res_ids = self.env.cr.fetchall()          
        return [('id', 'in', res_ids)]
    
    
    def _search_is_week(self, operator, value):
        """
            Fonction search qui permet de retrouver tous les OTs qui sont de cette semaine
        """
        request = """
        SELECT 
            x.id 
        FROM
            (SELECT
            to_char(start_date_planned, 'YYYY-MM-DD') as date,
            to_char((current_date), 'YYYY-MM-DD') as date_now,     
            id
             FROM 
             intervention 
             WHERE
             start_date_planned is not null)  x
        
        where 
            x.date >= x.date_now and
            (x.date_now::date + interval '7 days')::date >= x.date::date
            """
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
            to_char(start_date_planned, 'YYYY-MM-DD') as date,
            to_char((current_date), 'YYYY-MM-DD') as date_now,     
            id
             FROM 
             intervention 
             WHERE
             start_date_planned is not null)  x
        
        where 
            x.date >= x.date_now and
            (x.date_now::date + interval '30 days')::date >= x.date::date"""
        self.env.cr.execute(request)
        res_ids = self.env.cr.fetchall()          
        return [('id', 'in', res_ids)]
    
    
    @api.one
    @api.depends('ended_date_planned', 'state')
    def _compute_is_late(self):
        """
            Fonction qui si l'intervention est en retard, on regarde si l'intervention n'est pas terminée ou annulée ou en attente et que sa date de fin plannifiée n'est pas inférieur à la date du jour
        """
        is_late = False
        if self.state not in ('waiting', 'done', 'cancel'):
            now = datetime.now()
            if now.strftime('%Y-%m-%d %H:%M:%S') > self.ended_date_planned and self.ended_date_planned:
                is_late = True
        
        self.is_late = is_late
    
    
    def _search_is_late(self, operator, value):
        """
            Fonction qui si l'intervention est en retard, on regarde si l'intervention n'est pas terminée ou annulée ou en attente et que sa date de fin plannifiée n'est pas inférieur à la date du jour
        """
        request = """
        SELECT 
            x.id 
        FROM
            (SELECT
            to_char(ended_date_planned, 'YYYY-MM-DD HH:MM:SS') as date,
            to_char((current_date), 'YYYY-MM-DD HH:MM:SS') as date_now,     
            id
             FROM 
             intervention 
             WHERE
             ended_date_planned is not null and
             state not in ('waiting', 'done', 'cancel'))  x
        
        where 
            x.date_now > x.date """
        self.env.cr.execute(request)
        res_ids = self.env.cr.fetchall()          
        return [('id', 'in', res_ids)]
    
    
    @api.model
    def _type_guarantee_get(self):
        return [
                ('under_guarantee', _('Under guarantee')),
                ('no_guarantee', _('No guarantee')),
                       ]
        
    
    @api.model
    def _type_invoice_get(self):
        return [
                ('billable', _('Billable')),
                ('no_billable', _('No billable')),
                       ]
    
    
    @api.one
    @api.depends('company_id')
    def _compute_company_id(self):
        self.warehouse_id = self.company_id and self.company_id and self.company_id.warehouse_id and self.company_id.warehouse_id.id or False
        
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Name', size=256, required=True, default=lambda self: self.env['ir.sequence'].get('intervention'))
    state = fields.Selection('_state_get', string='State', default='waiting', required=True)
    type = fields.Selection('_type_get', string='Type', required=False)
    park_id = fields.Many2one('park', string='Park', required=True, ondelete='restrict')
    applicant_id = fields.Many2one('res.users', string='Applicant', required=True, ondelete='restrict', default=lambda self: self.env.uid)
    responsible_id = fields.Many2one('res.users', string='Responsible', required=False, ondelete='restrict')
    maintenance_operation_id = fields.Many2one('maintenance.operation', string='Maintenance operation', required=False, ondelete='restrict')
    emergency = fields.Selection('_emergency_get', string='Emergency', default='medium', required=True)
    description = fields.Text(string='Description')
    park_type = fields.Selection('_park_type_get', string='Park type', compute='_compute_park', store=True)
    park_num_serie_id = fields.Many2one('stock.label', string='Park type', compute='_compute_park', store=True)
    is_intern = fields.Boolean(string='Intern', default=False)
    contact_id = fields.Many2one('res.partner', string='Contact', required=False, ondelete='restrict')
    type_guarantee = fields.Selection('_type_guarantee_get', string='Type guarantee')
    type_invoice = fields.Selection('_type_invoice_get', string='Type invoice')
    #Planning
    date_create = fields.Date(string='Create date intervention', required=True, default=lambda self: fields.Date.today())
    time_synchro_resource = fields.Boolean(string='Time synchronized with the resources', default=False)
    start_date_requested = fields.Date(string='Start date requested', required=True)
    time_theo_interv = fields.Float(string='Time theo intervention (HH:MM)', default=0.0, required=False, digits=dp.get_precision('Product quantity'))
    ended_date_requested = fields.Date(string='Ended date requested')
    start_date_planned = fields.Datetime(string='Start date planned')
    tolerance = fields.Selection('_tolerance_get', string='Tolerance')
    alert = fields.Boolean(string='Alert', compute='_compute_alert', store=True)
    ended_date_planned = fields.Datetime(string='Ended date planned')
    start_date_real = fields.Datetime(string='Start date real')
    time_real_interv = fields.Float(string='Time real intervention (HH:MM)', compute='_compute_time_real_interv', digits=dp.get_precision('Time'))
    ended_date_real = fields.Datetime(string='Ended date real')
    #Temps
    invoice_product_id = fields.Many2one('product.product', string='Invoice product', required=False, ondelete='restrict')
    invoice_price = fields.Float(string='Invoice price (hours)', default=0.0, required=False, digits=dp.get_precision('Product price'))
    currency_id = fields.Many2one('res.currency', string='Currency')
    currency_invoice_id = fields.Many2one('res.currency', string='Currency', required=False, ondelete='restrict', default=lambda self: self.env.user.company_id.currency_id)
    timetracking_ids = fields.One2many('resource.timetracking', 'intervention_id',  string='Timetracking')
    note_time = fields.Text(string='Note time')
    #Resource
    piece_maintenance_ids = fields.One2many('piece.maintenance.intervention', 'intervention_id',  string='Piece maintenance')
    resource_intervention_ids = fields.One2many('resource.intervention', 'intervention_id',  string='Resource intervention')
    move_piece_ids = fields.One2many('stock.move', 'intervention_id',  string='Moves pieces')
    #Note
    instruction_intervention_ids = fields.One2many('instruction.intervention', 'intervention_id',  string='Instructions')
    note = fields.Text(string='Note')
    #mail
    mail_ids = fields.One2many('mail.mail', string='Mails', compute='_compute_mail', readonly=True)
    #devis
    customer_id = fields.Many2one('res.partner', string='Customer', required=False, ondelete='restrict')
    quotation_ids = fields.One2many('quotation.intervention', 'intervention_id',  string='string')
    sale_id = fields.Many2one('sale.order', string='Sales', required=False, ondelete='restrict')
    sale_line_ids = fields.One2many('sale.order.line', 'intervention_id',  string='Sales')
    invoicing_spare_part = fields.Boolean(string='Ingest spares in the quote', default=False)
    mo_ids = fields.One2many('mrp.manufacturingorder', 'intervention_id',  string='MOs')
    #analisys
    type_failure_id = fields.Many2one('type.failure.intervention', string='Type of failure', required=False, ondelete='restrict')
    cause_id = fields.Many2one('cause.intervention', string='Cause', required=False, ondelete='restrict')
    color_kanban = fields.Integer(string='Color Kanban', compute='_compute_color_kanban')
    month = fields.Selection('_month_get', string='Month', compute='_compute_start_date', store=True)
    week_number = fields.Char(string='Week number', size=2, compute='_compute_start_date', store=True) 
    year = fields.Char(string='Year', size=4, compute='_compute_start_date', store=True)
    is_today = fields.Boolean(string='Is today', compute='_compute_start_date', search='_search_is_today')
    is_week = fields.Boolean(string='Is week', compute='_compute_start_date', search='_search_is_week')
    is_month = fields.Boolean(string='Is month', compute='_compute_start_date', search='_search_is_month')
    is_late = fields.Boolean(string='Late', compute='_compute_is_late', search='_search_is_late')
    
    #Facture
    is_invoice_piece_maintenance = fields.Boolean(string='Invoicing of maintenance pieces', default=False)
    is_invoice_times_past = fields.Boolean(string='Invoicing of times past', default=False)
    invoice_ids = fields.One2many('account.invoice', 'intervention_id',  string='Invoices')
    picking_id = fields.Many2one('stock.picking', string='Picking', required=False, ondelete='set null')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', compute='_compute_company_id', store=False)
    company_id = fields.Many2one('res.company', string='Company', required=False, ondelete='restrict')
    is_create_quotation = fields.Boolean(string='Create quotation', default=False)
    is_create_invoice = fields.Boolean(string='Create invoice', default=False)
    
    
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('time_synchro_resource', 'time_theo_interv', 'start_date_planned')
    def _onchange_time(self):
        """
            Onchange temps
        """
        for resource_intervention in self.resource_intervention_ids:
            resource_intervention.start_date = self.start_date_planned
            if self.time_synchro_resource:
                resource_intervention.time = self.time_theo_interv
                
    
    @api.onchange('time_theo_interv', 'start_date_planned')
    def _onchange_date_planned(self):
        """
            Onchange temps
        """
        ended_date_planned = self.start_date_planned
        if self.time_theo_interv:
            ended_date_planned = self.env.user.company_id.partner_id.calendar_id.get_dates(ended_date_planned, self.time_theo_interv)['end_date']
        
        self.ended_date_planned = ended_date_planned 
    
    
    @api.onchange('park_id')
    def _onchange_park(self):
        """
            Onchange temps
        """
        customer_id = False
        if self.park_id and self.park_id.type == 'external':
            customer_id = self.park_id.customer_id.id
        
        self.customer_id = customer_id
        
    
    @api.onchange('invoice_price')
    def _onchange_invoice_price(self):
        """
            Onchange invoice_price
        """
        for timetracking in self.timetracking_ids:
            timetracking.hourly_cost = self.invoice_price
    
    
    @api.onchange('customer_id')
    def _onchange_customer_id(self):
        """
            Onchange invoice_price
        """
        self.currency_id = self.customer_id and self.customer_id.currency_id and self.customer_id.currency_id.id or False
    
    
    @api.onchange('type')
    def _onchange_type(self):
        """
            Onchange type
        """
        if self.type == 'repair_sav_mo':
            self.invoicing_spare_part = False 
            self.is_invoice_times_past = False 
            self.is_invoice_piece_maintenance = False 

    
    #===========================================================================
    # Button
    #===========================================================================
    @api.multi
    def button_importation_maintenance_operation(self):
        """ 
            Bouton qui permet d'importer certaines information de la maintenance opérationnelle choisie
        """
        instruction_intervention_obj = self.env['instruction.intervention']
        resource_intervention_obj = self.env['resource.intervention']
        piece_maintenance_intervention_obj = self.env['piece.maintenance.intervention']
        for intervention in self:
            if intervention.maintenance_operation_id:
                maintenance_operation = intervention.maintenance_operation_id
                vals = {'type': maintenance_operation.type,
                        'responsible_id': maintenance_operation.responsible_id.id,
                        'time_synchro_resource': maintenance_operation.time_synchro_resource,
                        'time_theo_interv': maintenance_operation.intervention_time,
                        'tolerance': maintenance_operation.tolerance,
                }
                intervention.write(vals)
                #Partie pièce de maitenance
                already_use_piece_maintenance_ids = [x.piece_maintenance_id.id for x in intervention.piece_maintenance_ids]
                for piece_maintenance in maintenance_operation.piece_maintenance_ids:
                    if (already_use_piece_maintenance_ids and piece_maintenance.id not in already_use_piece_maintenance_ids) or not already_use_piece_maintenance_ids:
                        product_id = piece_maintenance.product_id and piece_maintenance.product_id.id or False
                        uom_category_id = piece_maintenance.uom_category_id and piece_maintenance.uom_category_id.id or False
                        vals_piece_maintenance = {
                                                  'intervention_id': intervention.id,
                                                  'piece_maintenance_id': piece_maintenance.id,
                                                  'product_id': product_id,
                                                  'description': piece_maintenance.description,
                                                  'qty': piece_maintenance.qty,
                                                  'uom_id': piece_maintenance.uom_id.id,
                                                  'uom_category_id': uom_category_id,
                                                 }
                        piece_maintenance_intervention_obj.create(vals_piece_maintenance)
                
                #Partie pièce de maitenance
                already_use_resource_intervention_ids = [x.categ_resource_maint_oper_id.id for x in intervention.resource_intervention_ids]
                for categ_resource_mo in maintenance_operation.categ_resource_ids:
                    if (already_use_resource_intervention_ids and categ_resource_mo.id not in already_use_resource_intervention_ids) or not already_use_resource_intervention_ids:
                        vals_resource_intervention = {
                                                      'intervention_id': intervention.id,
                                                      'categ_resource_maint_oper_id': categ_resource_mo.id,
                                                      'time': categ_resource_mo.time,
                                                      'categ_resource_id': categ_resource_mo.categ_resource_id.id,
                                                      'start_date': intervention.start_date_planned,
                                                      'maintenance_operation_id': intervention.maintenance_operation_id.id
                                                     }
                        
                        resource_intervention_obj.create(vals_resource_intervention)
                
                #Partie instruction de maitenance
                already_use_instruction_maintenance_ids = [x.instruction_maintenance_id.id for x in intervention.instruction_intervention_ids]
                for instruction_maintenance in maintenance_operation.instruction_maintenance_ids:
                    if (already_use_instruction_maintenance_ids and instruction_maintenance.id not in already_use_instruction_maintenance_ids) or not already_use_instruction_maintenance_ids:
                        plan_id = instruction_maintenance.plan_id and instruction_maintenance.plan_id.id or False
                        vals_instruction_intervention = {
                                                         'intervention_id': intervention.id,
                                                         'instruction_maintenance_id': instruction_maintenance.id,
                                                         'name': instruction_maintenance.name,
                                                         'sequence': instruction_maintenance.sequence,
                                                         'description': instruction_maintenance.description,
                                                         'plan_id': plan_id,
                                                         'time': instruction_maintenance.time,
                                                        }
                        
                        instruction_intervention_obj.create(vals_instruction_intervention)
                
        return True
    
    
    @api.multi
    def button_create_invoice_intervention(self):
        """ 
            Bouton qui permet de créer la facture des temps
        """
        invoice_obj = self.env['account.invoice']
        invoice_line_obj = self.env['account.invoice.line']
        for intervention in self:
            invoice_rcs = False
            if intervention.sale_id:
                for invoice_line in intervention.sale_id.invoice_line_ids:
                    if invoice_line.invoice_id.state != 'cancel':
                        raise except_orm(_('Error'), _('Sale already invoiced.'))
                
                invoice_rcs = intervention.sale_id.generate_invoice(return_id_invoice=True)
                if isinstance(invoice_rcs, list):
                    invoice_rcs = invoice_rcs[0]
                    invoice_rcs.write({'intervention_id': intervention.id})
                
            if intervention.is_invoice_piece_maintenance:
                pmi_rcs = self.env['piece.maintenance.intervention']
                for pmi in intervention.piece_maintenance_ids:
                    if pmi.is_to_invoice and not pmi.invoice_line_id and not pmi.type_add_back == 'get_back':
                        pmi_rcs += pmi
                
                if pmi_rcs:
                    if not invoice_rcs:
                        invoice_rcs = invoice_obj.create_invoice(intervention.customer_id.id, intervention.customer_id.address_id.id, 
                                                   'out_invoice', other_data={'intervention_id': intervention.id})
                    
                    for piece_maintenance in pmi_rcs:
                        invoice_line_rcs = invoice_line_obj.create_invoice_line(invoice_rcs.id, piece_maintenance.product_id.id, from_invoice=True, 
                                                                                other_data={'uom_id': piece_maintenance.uom_id.id,
                                                                                            'sec_uom_id': piece_maintenance.uom_id.id,
                                                                                            'uoi_id': piece_maintenance.uom_id.id,
                                                                                            'uom_qty': piece_maintenance.qty,
                                                                                            'sec_uom_qty': piece_maintenance.qty,
                                                                                            'quantity': piece_maintenance.qty,})    
                        piece_maintenance.write({'invoice_line_id': invoice_line_rcs.id})
                        
                        if intervention.currency_id and invoice_rcs.currency_id.id != intervention.currency_id.id:
                            context2 = {}
                            context2.update(self.env.context)
                            if invoice_rcs.date_invoice:
                                context2['date'] = invoice_rcs.date_invoice
                                
                            price = invoice_rcs.currency_id.with_context(context2).compute(piece_maintenance.price, intervention.currency_id)
                        else:
                            price = piece_maintenance.price
                            
                        invoice_line_rcs.write({'price_unit': price})
                    
                
            if intervention.is_invoice_times_past:
                if not intervention.invoice_product_id:
                    raise except_orm(_('Error'), _('Please indicate the invoice product for the times.'))
                
                dict_invoice_line = {}
                for timetracking in intervention.timetracking_ids:
                    if timetracking.is_to_invoice and not timetracking.invoice_line_id:
                        if timetracking.hourly_cost:
                            if timetracking.hourly_cost in dict_invoice_line:
                                dict_invoice_line[timetracking.hourly_cost]['time'] += timetracking.time
                                dict_invoice_line[timetracking.hourly_cost]['timetracking_rcs'] += timetracking
                            else:
                                dict_invoice_line[timetracking.hourly_cost] = {'time': timetracking.time, 
                                                                               'timetracking_rcs': timetracking}
                
                if dict_invoice_line:
                    if not invoice_rcs:
                        invoice_rcs = invoice_obj.create_invoice(intervention.customer_id.id, intervention.customer_id.address_id.id, 
                                                   'out_invoice', other_data={'intervention_id': intervention.id})
                    
                    for key_invoice_line in dict_invoice_line:
                        invoice_line_rcs = invoice_line_obj.create_invoice_line(invoice_rcs.id, intervention.invoice_product_id.id, from_invoice=True, 
                                                                                other_data={'uom_id': intervention.invoice_product_id.uom_id.id,
                                                                                            'sec_uom_id': intervention.invoice_product_id.uom_id.id,
                                                                                            'uoi_id': intervention.invoice_product_id.uom_id.id,
                                                                                            'uom_qty': dict_invoice_line[key_invoice_line]['time'],
                                                                                            'sec_uom_qty': dict_invoice_line[key_invoice_line]['time'],
                                                                                            'quantity': dict_invoice_line[key_invoice_line]['time'],})
                        invoice_line_rcs.write({'price_unit': key_invoice_line})
                        dict_invoice_line[key_invoice_line]['timetracking_rcs'].write({'invoice_line_id': invoice_line_rcs.id})
                
                intervention.write({'is_create_invoice': True})
                
            if not invoice_rcs:
                raise except_orm(_('Error'), _('No invoice create.'))
            
            return {'name': _('Invoice'),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'account.invoice',
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'res_id': invoice_rcs.id,
                    'nodestroy': True,
                    }
        
        
        return True
    
    
    @api.multi
    def button_open_wiz_create_quotation(self):
        """ 
            Bouton qui permet de créer le devis de l'intervention
        """
        wiq_obj = self.env['wiz.intervention.quotation']
        product_obj = self.env['product.product']
        for intervention in self:
            vals_quotation = []
            vals_no_quotation = []
            customerinfo_ids = self.env['product.customerinfo'].search([('partner_id', '=', intervention.customer_id.id), ('state', '!=', 'obsolete')])
            customer_product_ids = [customerinfo.product_id.id for customerinfo in customerinfo_ids]
            all_product_rcs = product_obj.search([('sale_ok', '=', True), ('state', 'in', ['dev','lifeserie','endlife']), '|', 
                                                  ('id', 'in', customer_product_ids), ('free_sale', '=', True)])
            for quotation in intervention.quotation_ids:
                description = '[%s] %s'%(quotation.product_id.code, quotation.product_id.name)
                if quotation.product_id.id in all_product_rcs.ids:
                    vals_quotation.append((0, 0, {
                                      'description': description,
                                      'product_id': quotation.product_id.id,
                                      'qty': quotation.qty,
                                      'price': quotation.price,
                                      'uom_id': quotation.uom_id.id,
                                      'currency_id': quotation.currency_id.id,
                                      'uom_category_id': quotation.uom_category_id.id,
                                      'qi_id': quotation.id
                                      }))
                else:
                    vals_no_quotation.append((0, 0, {
                                      'description': description,
                                      'product_id': quotation.product_id.id,
                                      }))
            
            if intervention.invoicing_spare_part:
                for piece_maintenance in intervention.piece_maintenance_ids:
                    if ((piece_maintenance.product_id and piece_maintenance.product_id.id in all_product_rcs.ids) or not piece_maintenance.product_id) and not piece_maintenance.type_add_back == 'get_back':
                        product_id = piece_maintenance.product_id and piece_maintenance.product_id.id or False
                        uom_category_id = piece_maintenance.uom_category_id and piece_maintenance.uom_category_id.id or False
                        currency_id = intervention.currency_id and intervention.currency_id.id or intervention.customer_id.currency_id.id
                        vals_quotation.append((0, 0,{
                                      'description': piece_maintenance.description,
                                      'product_id': product_id,
                                      'qty': piece_maintenance.qty,
                                      'price': piece_maintenance.price,
                                      'uom_id': piece_maintenance.uom_id.id,
                                      'currency_id': currency_id,
                                      'uom_category_id': uom_category_id,
                                      'pmi_id': piece_maintenance.id,
                                      }))
                    else:
                        vals_no_quotation.append((0, 0, {
                                      'description': piece_maintenance.description,
                                      'product_id': piece_maintenance.product_id.id,
                                      }))
            
            vals_wiq = {'intervention_id': intervention.id, 'customer_id': intervention.customer_id.id}
            if vals_quotation:
                vals_wiq['line_ids'] = vals_quotation
            
            if vals_no_quotation:
                vals_wiq['no_order_line_ids'] = vals_no_quotation
                
            wiq_rcs = wiq_obj.create(vals_wiq)
            return {'name': _('Create quotation of intervention'),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'wiz.intervention.quotation',
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'res_id': wiq_rcs.id,
                    'nodestroy': True,
                    }
            
        return True
    
    
    @api.multi
    def button_create_mo_repair(self):
        """ 
            Bouton qui permet de créer le devis de l'intervention
        """
        for gmao in self:
            origin_num_serie_id = gmao.park_num_serie_id and gmao.park_num_serie_id.id or False
            return {'name': _('Manufacturing order for repair'),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'wiz.mo.repair',
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'context': {'default_intervention_id': gmao.id, 'default_origin_num_serie_id': origin_num_serie_id},
                    'nodestroy': True,
                    }
            
        return True
    
    
    @api.multi
    def action_send_mail(self):
        return self.env['mail.message'].action_send_mail(False, 'intervention', '',self.id)
    
    
    @api.multi
    def button_search_create_piece_maintenance(self):
        """
            Bouton qui permet dans les interventions de rechercher toutes les matières consommées dans les OFs qui ne sont pas sorties afin de pouvoir créer des pièces de maitenances.
            Ne pas passer par le wizard d'ajout des matières demandent de raphael, solution:
                On supprime les pièces de maintenances précédement créées
                On prend tous les matières premières et les produits sortant, on les compare, pour tous les produits entrant positif, on crée les pièces de maintenances
        """
        uom_obj = self.env['product.uom']
        pmi_obj = self.env['piece.maintenance.intervention']
        for interv in self:
            if interv.mo_ids:
                del_pm_rcs = self.env['piece.maintenance.intervention']
                for pm in interv.piece_maintenance_ids:
                    if pm.is_wo_rm:
                        if pm.invoice_line_id:
                            raise except_orm(_('Error'), _('The line "%s" is already invoiced.')%(pm.description))
                        else:
                            del_pm_rcs += pm
                
                if del_pm_rcs:
                    del_pm_rcs.unlink()
                
                dic_move_in_product = {}
                dic_move_out_product = {}
                list_dic_create_product = []
                for mo in interv.mo_ids:
                    for wo in mo.workorder_ids:
                        rm_rcs = wo.rm_draft_ids + wo.rm_done_ids
                        dic_move_in_product = self.return_dico_product_qty(rm_rcs, dic_move_in_product, uom_obj)
                        fp_rcs = wo.fp_draft_ids + wo.fp_done_ids
                        dic_move_out_product = self.return_dico_product_qty(fp_rcs, dic_move_out_product, uom_obj)
                
                
                if dic_move_in_product:
                    if dic_move_out_product:
                        for in_product in dic_move_in_product:
                            if in_product in dic_move_out_product:
                                if dic_move_out_product[in_product]['uom'] != dic_move_in_product[in_product]['uom']:
                                    qty_out = uom_obj._compute_qty_obj(dic_move_out_product[in_product]['uom'], dic_move_out_product[in_product]['qty'], 
                                                                       dic_move_in_product[in_product]['uom'], with_raise=False, with_round=False)
                                    qty_final = dic_move_in_product[in_product]['qty'] - qty_out
                                        
                                else:     
                                    qty_final = dic_move_in_product[in_product]['qty'] - dic_move_out_product[in_product]['qty'] 
                                     
                                        
                            else:
                                qty_final = dic_move_in_product[in_product]['qty']
                            
                            if qty_final > 0:
                                description = description = '[%s] %s'%(in_product.code, in_product.name)
                                vals = {'product_id': in_product.id,
                                        'description': description,
                                        'qty': qty_final,
                                        'uom_id': dic_move_in_product[in_product]['uom'].id,
                                        'category_id': dic_move_in_product[in_product]['uom'].category_id.id,
                                        'intervention_id': interv.id,
                                        'is_wo_rm': True,
                                        'is_to_invoice': True
                                }
                                list_dic_create_product.append(vals)
                    
                    else:
                        for in_product in dic_move_in_product:
                            vals = {'product_id': in_product.id,
                                    'description': description,
                                    'qty': dic_move_in_product[in_product]['qty'],
                                    'uom_id': dic_move_in_product[in_product]['uom'].id,
                                    'category_id': dic_move_in_product[in_product]['uom'].category_id.id,
                                    'intervention_id': interv.id,
                                    'is_wo_rm': True,
                                    'is_to_invoice': True
                            }
                            list_dic_create_product.append(vals)
                
                    for create_product in list_dic_create_product:
                        pmi_obj.create(create_product)
        
        return True

    
    def return_dico_product_qty(self, move_rcs, dic_move_product, uom_obj):
        for move in move_rcs:
            if move.state != 'cancel':
                if move.product_id in dic_move_product:
                    if move.uoi_id.id != dic_move_product[move.product_id]['uom']:
                        dic_move_product[move.product_id]['qty'] += uom_obj._compute_qty_obj(move.uoi_id, move.uoi_qty, 
                                                                                             dic_move_product[move.product_id]['uom'], with_raise=False, with_round=False)
                    else:
                        dic_move_product[move.product_id]['qty'] += move.uoi_qty
        
                else:
                    dic_move_product[move.product_id] = {'qty': move.uoi_qty,
                                                         'uom': move.uoi_id,}
        
        return dic_move_product
    
    
    def gernerate_move_piece_maintenance(self):
        move_lot_obj = self.env['stock.move.lot']
        move_obj = self.env['stock.move']
        prod_location_id = self.warehouse_id and self.warehouse_id.production_location_id and self.warehouse_id.production_location_id.id or False
        if not prod_location_id:
            raise except_orm(_('Error'), _('There is not production location.'))
        
        sav_location_id = self.warehouse_id and self.warehouse_id.location_sav_id and self.warehouse_id.location_sav_id.id or False
        if not sav_location_id:
            raise except_orm(_('Error'), _('There is not SAV location.'))
        
        for piece_maintenance in self.piece_maintenance_ids:
            if not piece_maintenance.move_piece_maintenance_id:
                if piece_maintenance.type_add_back == 'add':
                    if piece_maintenance.label_id and piece_maintenance.label_id.state == 'inactive':
                        qty = piece_maintenance.label_id.origin_uom_qty
                        uom_qty = piece_maintenance.label_id.uom_id
                    else:
                        qty = piece_maintenance.qty
                        uom_qty = piece_maintenance.uom_id

                    move_rcs = move_obj.create_move(
                        piece_maintenance.product_id, 
                        sav_location_id, 
                        prod_location_id, 
                        qty=qty, 
                        uom=uom_qty, 
                        other_data={'intervention_id': self.id}, 
                        in_product_uom=True
                    )
                    if piece_maintenance.lot_id and move_rcs:
                        move_rcs.move_lot_ids.unlink()
                        move_lot_obj.create({
                            'move_id': move_rcs.id,
                            'lot_id': piece_maintenance.lot_id.id
                        })
                        
                    if piece_maintenance.label_id:
                        move_rcs.assign_label(piece_maintenance.label_id, with_scrap=False)
                        
                    move_rcs.wkf_waiting()
                    # TODO THOMAS: le faite d'appeler warehouse_id rafraichit le browse ou les covers. regarder pourquoi
                    # Si on essaye de faire cette action avec un autre user qu'admin, on a une contrainte sur le stock alors qu'il y a du stock.
                    move_rcs.warehouse_id
                    move_rcs.wkf_done()
                    piece_maintenance.write({'move_piece_maintenance_id': move_rcs.id})
                    
                elif piece_maintenance.type_add_back == 'get_back':
                    if piece_maintenance.label_id and piece_maintenance.label_id.state == 'inactive':
                        qty = piece_maintenance.label_id.origin_uom_qty
                        uom_qty = piece_maintenance.label_id.uom_id
                    else:
                        qty = piece_maintenance.qty
                        uom_qty = piece_maintenance.uom_id
                        
                    move_rcs = move_obj.create_move(
                        piece_maintenance.product_id, 
                        prod_location_id, 
                        sav_location_id, 
                        qty=qty, 
                        uom=uom_qty, 
                        other_data={'intervention_id': self.id}, in_product_uom=True
                    )
                    if piece_maintenance.lot_id and move_rcs:
                        move_lot_obj.create({
                            'move_id': move_rcs.id,
                            'lot_id': piece_maintenance.lot_id.id
                        })
                    if piece_maintenance.label_id:
                        ctx = self.env.context.copy()
                        ctx['authorize_return'] = True
                        move_rcs.with_context(ctx).assign_label(piece_maintenance.label_id, with_scrap=False)
                    
                    move_rcs.wkf_waiting()
                    move_rcs.wkf_done()
                    piece_maintenance.write({'move_piece_maintenance_id': move_rcs.id})
        
        return True
    
    
    @api.multi
    def write(self, vals=None):
        """
            Write intervention
        """
        if not vals:
            vals = {}
            
        if 'state' in vals and vals['state'] == 'done':
            vals['ended_date_real'] = fields.Datetime.now()
        
        if 'state' in vals and vals['state'] == 'performed' and not self.start_date_real and ('start_date_real' not in vals or vals['start_date_real'] == False):
            vals['start_date_real'] = fields.Datetime.now()
        
        if 'invoicing_spare_part' in vals and vals['invoicing_spare_part']:
            vals['is_invoice_piece_maintenance'] = False
        
        res =  super(intervention, self).write(vals)
        for interv in self:
            if interv.type in ('repair_sav', 'repair_sav_mo') and interv.park_type == 'intern':
                raise except_orm(_('Error'), _('Type "sav repair" can only be used in SAV.'))
        
            if 'state' in vals and vals['state'] in ('performed', 'done') and interv.park_type ==  'external':
                interv.gernerate_move_piece_maintenance()
            
            if 'state' in vals and vals['state'] in ('waiting', 'affect', 'cancel') and interv.park_type ==  'external':
                interv.move_piece_ids.wkf_cancel()
                interv.piece_maintenance_ids.write({'move_piece_maintenance_id': False})
        
        return res


    @api.model
    def create(self, vals=None):
        """
            Create intervention
        """
        
        if 'invoicing_spare_part' in vals and vals['invoicing_spare_part']:
            vals['is_invoice_piece_maintenance'] = False
            
        vals['company_id'] = self.env.user.company_id.id
        res = super(intervention, self).create(vals=vals)
        if res.type == 'repair_sav' and res.park_type == 'intern':
            raise except_orm(_('Error'), _('Type "sav repair" can only be used in SAV.'))
        
        park = res.park_id
        vals_int = {}
        uom_obj = self.env['product.uom']
        if park and not park.is_equipment:
            if park.guarantee_start_date and park.guarantee_unity_id and park.guarantee:
                categ_time_rc = self.env.ref('product.uom_categ_wtime')
                if categ_time_rc and categ_time_rc.id == park.guarantee_unity_id.category_id.id:
                    categ_day_rc = uom_obj.search([('category_id', '=', categ_time_rc.id), ('type', '=', 'reference')])
                    if categ_day_rc:
                        nb_day = int(uom_obj._compute_qty_obj(park.guarantee_unity_id, park.guarantee, categ_day_rc, with_raise=False, with_round=False))
                        date = fields.Date.to_string(fields.Date.from_string(park.guarantee_start_date) + relativedelta(days=nb_day))
                        if date > fields.Date.today():
                            vals_int['type_guarantee'] = 'under_guarantee'
                            vals_int['type_invoice'] = 'no_billable'
                        else:
                            vals_int['type_guarantee'] = 'no_guarantee'
                    else:
                        vals_int['type_guarantee'] = 'no_guarantee'
                else:
                    vals_int['type_guarantee'] = 'no_guarantee'
                    
            else:
                vals_int['type_guarantee'] = 'no_guarantee'
            
        if vals_int:
            res.write(vals_int)
        
        return res
    
    
    @api.multi
    def button_return_product(self):
        for interv in self:
            if interv.park_id and interv.park_id.num_serie_id and interv.park_id.num_serie_id.state == 'available':
                new_picking = self.env['stock.picking'].create_picking('out', 
                                                                       partner=interv.customer_id, 
                                                                       product_qty_uom={interv.park_id.num_serie_id.product_id: 
                                                                                                         {'uom_qty': interv.park_id.num_serie_id.uom_qty, 
                                                                                                          'uom_id': interv.park_id.num_serie_id.uom_id, 
                                                                                                          'sec_uom_qty': interv.park_id.num_serie_id.sec_uom_qty or interv.park_id.num_serie_id.uom_qty, 
                                                                                                          'sec_uom_id': interv.park_id.num_serie_id.sec_uom_qty and interv.park_id.num_serie_id.sec_uom_id or interv.park_id.num_serie_id.uom_id, 
                                                                                                          }}, 
                                                                       warehouse_rs=interv.park_id.num_serie_id.warehouse_id)
                
                new_picking.move_ids[0].write({'trigger_supply': 'make_to_order_with_stock'})
                new_picking.move_ids[0].assign_label(interv.park_id.num_serie_id, with_scrap=False)
                interv.park_id.wkf_activity()
                interv.write({'picking_id': new_picking.id, 'state': 'done'})
                new_picking.wkf_waiting()
                return new_picking.get_form_view()
            else:
                raise except_orm(_('Error'), _('Please check the state of the label.'))
    


class instruction_intervention(models.Model):
    """ 
        Instruction intervention
    """
    _name = 'instruction.intervention'
    _description = 'Instruction intervention'
    _order = 'sequence asc'
    
    @api.model
    def _state_get(self):
        return [
                ('to_do', _('To do')),
                ('done', _('Done')),
                ('cancel', _('Cancel')),
                       ]

    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    intervention_id = fields.Many2one('intervention', string='Intervention', required=False, ondelete='cascade')
    instruction_maintenance_id = fields.Many2one('instruction.maintenance', string='Instruction maintenance', required=False, ondelete='restrict')
    name = fields.Char(string='Name', size=256, required=True)
    sequence = fields.Integer(string='Sequence', default=0, required=True)
    description = fields.Html(string='Description')
    plan_id = fields.Many2one('document.openprod', string='Plan', required=False, ondelete='restrict')
    time = fields.Float(string='Time (HH:MM)', default=0.0, required=False, digits=dp.get_precision('Time'))
    state = fields.Selection('_state_get', string='State', default='to_do')
    date = fields.Date(string='Date', default=lambda self: fields.date.today())
    user_id = fields.Many2one('res.users', string='User', required=False, ondelete='restrict', default=lambda self: self.env.uid)
    
    
    #===========================================================================
    # Buttons
    #===========================================================================
    @api.multi
    def wkf_done(self):
        self.write({'state': 'done'})
    
    
    @api.multi
    def wkf_cancel(self):
        self.write({'state': 'cancel'})
        
        
    @api.multi
    def wkf_todo(self):
        self.write({'state': 'to_do'})            
            
          
                
class piece_maintenance_intervention(models.Model):
    """ 
        Pieces of maintenance intervention
    """
    _name = 'piece.maintenance.intervention'
    _description = 'Pieces of maintenance intervention'
    _rec_name = 'description'
    
    
    @api.one
    @api.depends('product_id')
    def _uom_category_compute(self):
        """
            Category UoM
        """
        uom_category_id = False
        if self.product_id:
            uom_category_id = self.uom_id.category_id.id
            
        self.uom_category_id = uom_category_id
    
    
    @api.one
    @api.depends('intervention_id.park_id', 'intervention_id.park_id.type')
    def _compute_park_type(self):
        """
            type du park
        """
        self.park_type = self.intervention_id and self.intervention_id.park_id and self.intervention_id.park_id.type or ''
    
    
    @api.model
    def _park_type_get(self):
        return [
                ('intern', _('Intern')),
                ('external', _('External')),
                       ]
    
    
    @api.model
    def _type_invoice_get(self):
        return [
                ('billable', _('Billable')),
                ('no_billable', _('No billable')),
                       ]
    
    
    @api.one
    @api.depends('intervention_id', 'intervention_id.type_invoice')
    def _compute_type_invoice(self):
        """
            type du park
        """
        self.type_invoice = self.intervention_id and self.intervention_id.type_invoice or ''
    
    @api.one
    @api.depends('product_id', 'product_id.track_label')
    def _compute_is_track_label(self):
        """
            type du park
        """
        self.is_track_label = self.product_id and self.product_id.track_label or False
        self.is_track_out_lot = self.product_id and self.product_id.track_out_lot or False
        self.is_track_in_lot = self.product_id and self.product_id.track_in_lot or False
        
        
    @api.model
    def _type_add_back_get(self):
        return [
            ('add', _('To add')),
            ('get_back', _('To get back')),
        ]

    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='restrict')
    intervention_id = fields.Many2one('intervention', string='Intervention', required=False, ondelete='cascade')
    piece_maintenance_id = fields.Many2one('piece.maintenance', string='Piece maintenance', required=False, ondelete='set null')
    description = fields.Text(string='Description', required=True)
    qty = fields.Float(string='Qty', default=1.0, required=True, digits=dp.get_precision('Product quantity'))
    uom_id = fields.Many2one('product.uom', string='UoM', required=True, ondelete='restrict')
    uom_category_id = fields.Many2one('product.uom.category', compute='_uom_category_compute', string="UOM category", readonly=True)
    price = fields.Float(string='Invoice price', default=0.0, required=False, digits=dp.get_precision('Product price'))
    purchase_id = fields.Many2one('purchase.order', string='Purchase', required=False, ondelete='restrict')
    picking_id = fields.Many2one('stock.picking', string='Picking', required=False, ondelete='restrict')
    park_type = fields.Selection('_park_type_get', string='Park type', compute='_compute_park_type', store=True)
    is_to_invoice = fields.Boolean(string='To Invoice', default=False)
    invoice_line_id = fields.Many2one('account.invoice.line', string='Invoice line', required=False, ondelete='set null')
    is_wo_rm = fields.Boolean(string='WO RM', default=False)
    type_invoice = fields.Selection('_type_invoice_get', string='Type invoice', compute='_compute_type_invoice', store=True)
    type_add_back = fields.Selection('_type_add_back_get', string='Type')
    label_id = fields.Many2one('stock.label', string='Label', required=False, ondelete='restrict')
    is_track_label = fields.Boolean(string='Track label', compute='_compute_is_track_label', store=True)
    is_track_in_lot = fields.Boolean(compute='_compute_is_track_label', store=True)
    is_track_out_lot = fields.Boolean(compute='_compute_is_track_label', store=True)
    lot_id = fields.Many2one('stock.lot', string='Lot', required=False, ondelete='restrict')
    move_piece_maintenance_id = fields.Many2one('stock.move', string='move_piece_maintenance', required=False, ondelete='set null')
    sale_line_id = fields.Many2one('sale.order.line', string='Sale line', required=False, ondelete='set null')
    
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('product_id', 'intervention_id.customer_id', 'qty', 'uom_id')
    def _onchange_product_id(self):
        """
            Onchange du produit
        """
        uom_id, description, category_id = self.onchange_product_id(self.product_id)
        self.uom_id = uom_id
        self.description = description
        self.category_id = category_id   
        self.price = self.product_id.get_price_sale(self.intervention_id.customer_id, False, qty_uom=self.qty, uom=self.uom_id, 
                                                    type='price', with_uoi=self.uom_id)
        
    
    def onchange_product_id(self, product):
        """
            Fonction Onchange du produit
        """
        uom_id = False
        description = ''
        category_id = False
        if product:
            uom_id = product.uom_id.id
            category_id = product.uom_id.category_id.id
            description = '[%s] %s'%(product.code, product.name)
            
        return uom_id, description, category_id
    
    
    @api.onchange('label_id', 'qty', 'uom_id')
    def _onchange_label(self):
        if self.label_id:
            self.qty = self.label_id.uom_qty
            self.uom_id = self.label_id.uom_id.id
            
    
    @api.onchange('product_id')
    def _onchange_product_id2(self):
        self.label_id = False
        
    
    #===========================================================================
    # Buttons
    #===========================================================================
    @api.multi
    def button_create_purchase(self):
        """
            bouton qui lance le wizard de création rapide d'achat
        """
        cqp_obj = self.env['create.quick.purchase']
        for piece_maintenance in self:
            if piece_maintenance.product_id:
                cqp_rcs = cqp_obj.create({'product_id': piece_maintenance.product_id.id,
                                          'date': fields.Date.today(),
                                          'quantity': piece_maintenance.qty,
                                          'uom_forced_id': piece_maintenance.uom_id.id,
                                          'pm_intervention_id': piece_maintenance.id})
                
                return {'name': _('Create quick purchase'),
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'create.quick.purchase',
                        'type': 'ir.actions.act_window',
                        'target': 'new',
                        'res_id': cqp_rcs.id,
                        'nodestroy': True,
                        }
    
    
    @api.multi
    def button_create_picking(self):
        """
            bouton qui lance le wizard de création rapide d'une livraison
        """
        cpi_obj = self.env['create.picking.intervention']
        for piece_maintenance in self:
            if piece_maintenance.product_id:
                customer_id = piece_maintenance.intervention_id and piece_maintenance.intervention_id.customer_id and piece_maintenance.intervention_id.customer_id.id or False
                cpi_rcs = cpi_obj.create({'product_id': piece_maintenance.product_id.id,
                                          'date': fields.Date.today(),
                                          'uom_qty': piece_maintenance.qty,
                                          'uom_id': piece_maintenance.uom_id.id,
                                          'type': 'out',
                                          'partner_id': customer_id,
                                          'customer_id': customer_id,
                                          'pm_intervention_id': piece_maintenance.id})
                
                return {'name': _('Create picking'),
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'create.picking.intervention',
                        'type': 'ir.actions.act_window',
                        'target': 'new',
                        'res_id': cpi_rcs.id,
                        'nodestroy': True,
                        }
                
                
        
class resource_intervention(models.Model):
    """ 
        Resource intervention
    """
    _name = 'resource.intervention'
    _description = 'Resource intervention'
    _rec_name = 'categ_resource_id'
    
    
    @api.one
    @api.depends('categ_resource_id', 'maintenance_operation_id')
    def _all_resource_compute(self):
        """
            All resource pour le domaine si la ligne provient d'une maintenance opérationnelle ou si elle a été créée manuellement
        """
        all_resource_intermediate_ids = self.categ_resource_id and self.categ_resource_id.resource_ids and self.categ_resource_id.resource_ids.ids or []
        # Si provient d'unemaintenance opérationnelle
        if self.maintenance_operation_id:
            all_resource_maintenance_ope_ids = self.maintenance_operation_id.resource_ids and self.maintenance_operation_id.resource_ids.ids or []
            # Si des ressources ont été définies
            if all_resource_maintenance_ope_ids:
                all_resource_ids = []
                for all_resource_intermediate in all_resource_intermediate_ids:
                    # On récupère que les ressources de la categ si elles ont été définies dans la maintenance opérationnelle
                    if all_resource_intermediate in all_resource_maintenance_ope_ids:
                        all_resource_ids.append(all_resource_intermediate)
                        
            else:
                all_resource_ids = all_resource_intermediate_ids
                
        else:
            all_resource_ids = all_resource_intermediate_ids
        
        self.all_resource_ids = all_resource_ids
    
    
    @api.one
    @api.depends('start_date', 'time', 'resource_id')
    def _end_date_compute(self):
        end_date = False
        if self.resource_id and self.start_date:
            if self.time:
                dict_end_date = self.resource_id.calendar_id.get_dates(self.start_date, self.time)
                end_date = dict_end_date and dict_end_date['end_date'] or self.start_date
            else:
                end_date = self.start_date
        
        self.end_date = end_date
    
    
    @api.one
    @api.depends('start_date')
    def _compute_start_date(self):
        """
        Fonction qui calcule la semaine, le mois et l'année de la date de début
        """
        is_today = False
        is_week = False
        is_month = False
        
        ri_vals = self.read(['start_date'])
        if ri_vals[0]['start_date']:
            date = '%s'%(ri_vals[0]['start_date'][0:10])
            date = datetime.strptime(date, '%Y-%m-%d')
            isocal = date.isocalendar()
            now = datetime.now()
            if now.strftime('%Y-%m-%d') == date:
                is_today = True
            
            if (now + timedelta(days=7)) >= date and date >= now:
                is_week = True
                
            if (now + relativedelta(months=30)) >= date and date >= now:
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
        
        self.is_today = is_today
        self.is_week = is_week
        self.is_month = is_month
    
    
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
        
    def _search_is_today(self, operator, value):
        """
            Fonction search qui permet de retrouver tous les OTs qui sont de cette semaine
        """
        request = """
        SELECT 
            x.id 
        FROM
            (SELECT     
            to_char(start_date, 'YYYY-MM-DD') as date,
            to_char((current_date), 'YYYY-MM-DD') as date_now,
            id
             FROM 
             resource_intervention 
             WHERE
             start_date is not null)  x
        
        where 
            x.date = x.date_now"""
        self.env.cr.execute(request)
        res_ids = self.env.cr.fetchall()          
        return [('id', 'in', res_ids)]
    
    
    def _search_is_week(self, operator, value):
        """
            Fonction search qui permet de retrouver tous les OTs qui sont de cette semaine
        """
        request = """
        SELECT 
            x.id 
        FROM
            (SELECT
            to_char(start_date, 'YYYY-MM-DD') as date,
            to_char((current_date), 'YYYY-MM-DD') as date_now,     
            id
             FROM 
             resource_intervention 
             WHERE
             start_date is not null)  x
        
        where 
            x.date >= x.date_now and
            (x.date_now::date + interval '7 days')::date >= x.date::date
            """
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
            to_char(start_date, 'YYYY-MM-DD') as date,
            to_char((current_date), 'YYYY-MM-DD') as date_now,     
            id
             FROM 
             resource_intervention 
             WHERE
             start_date is not null)  x
        
        where 
            x.date >= x.date_now and
            (x.date_now::date + interval '30 days')::date >= x.date::date"""
        self.env.cr.execute(request)
        res_ids = self.env.cr.fetchall()          
        return [('id', 'in', res_ids)]
    
    
    @api.one
    @api.depends('intervention_id', 'intervention_id.start_date_requested', 'intervention_id.tolerance', 'intervention_id.start_date_planned')
    def _compute_intervention(self):
        """
            Fonction qui permet de savoir si la date planifié est > date demandé + tolérance dans l'intervention
        """
        self.alert = self.intervention_id and self.intervention_id.alert or False
        self.park_id = self.intervention_id and self.intervention_id.park_id.id or False
        self.park_type = self.intervention_id and self.intervention_id.park_id and self.intervention_id.park_id.type or ''
    
    
    @api.one
    def _compute_color_kanban(self):
        if self.alert:
            color_kanban = 2
        elif fields.Date.today() > self.start_date:
            color_kanban = 3
        else:
            color_kanban = 0
        
        self.color_kanban = color_kanban
    
    
    @api.model
    def _park_type_get(self):
        return [
                ('intern', _('Intern')),
                ('external', _('External')),
                       ]
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    intervention_id = fields.Many2one('intervention', string='Intervention', required=False, ondelete='cascade')
    categ_resource_id = fields.Many2one('mrp.resource.category', string='Resource category', required=True, ondelete='restrict')
    resource_id = fields.Many2one('mrp.resource', string='Resource', required=False, ondelete='restrict')
    all_resource_ids = fields.One2many('mrp.resource', compute='_all_resource_compute',  string='All resources')
    start_date = fields.Datetime(string='Start date')
    end_date = fields.Datetime(string='End date', compute='_end_date_compute', store=True)
    time = fields.Float(string='Time', default=0.0, required=False, digits=dp.get_precision('Time'))
    categ_resource_maint_oper_id = fields.Many2one('categ.resource.maintenance.operation', string='Resource maintenance operation', required=False, ondelete='set null')
    maintenance_operation_id = fields.Many2one('maintenance.operation', string='Maintenance operation', required=False, ondelete='restrict')
    park_id = fields.Many2one('park', string='Park', compute='_compute_intervention', store=True)
    month = fields.Selection('_month_get', string='Month', compute='_compute_start_date', store=True)
    week_number = fields.Char(string='Week number', size=2, compute='_compute_start_date', store=True) 
    year = fields.Char(string='Year', size=4, compute='_compute_start_date', store=True)
    is_today = fields.Boolean(string='Is today', compute='_compute_start_date', search='_search_is_today')
    is_week = fields.Boolean(string='Is week', compute='_compute_start_date', search='_search_is_week')
    is_month = fields.Boolean(string='Is month', compute='_compute_start_date', search='_search_is_month')
    alert = fields.Boolean(string='Alert', compute='_compute_intervention', store=True)
    park_type = fields.Selection('_park_type_get', string='Park type', compute='_compute_intervention', store=True)
    color_kanban = fields.Integer(string='Color Kanban', compute='_compute_color_kanban')

    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('categ_resource_id')
    def _onchange_categ_resource_id(self):
        self.resource_id = False
        
    
    @api.onchange('intervention_id', 'intervention_id.time_synchro_resource', 'intervention_id.time_theo_interv', 'intervention_id.start_date_planned')
    def _onchange_maintenance_operation_id(self):
        """
            Onchange de l'operation de maintenance 
        """
        if self.intervention_id:
            self.start_date = self.intervention_id.start_date_planned
            if self.intervention_id.time_synchro_resource:
                self.time = self.intervention_id.time_theo_interv
            


class quotation_intervention(models.Model):
    """ 
        Quotation intervention
    """
    _name = 'quotation.intervention'
    _description = 'Quotation intervention'
    _rec_name = 'product_id'
    
    
    @api.one
    @api.depends('product_id')
    def _uom_category_compute(self):
        """
            Category UoM
        """
        uom_category_id = False
        if self.product_id:
            uom_category_id = self.uom_id.category_id.id
            
        self.uom_category_id = uom_category_id
    
    @api.one
    @api.depends('intervention_id')
    def _customer_id_compute(self):
        """
            Category customer_id
        """
        customer_id = False
        if self.intervention_id:
            customer_id = self.intervention_id.customer_id.id
            
        self.customer_id = customer_id
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    intervention_id = fields.Many2one('intervention', string='Intervention', required=False, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='restrict')
    qty = fields.Float(string='Qty', default=0.0, required=True, digits=dp.get_precision('Product quantity'))
    price = fields.Float(string='Invoice price', default=0.0, required=True, digits=dp.get_precision('Product price'))
    uom_id = fields.Many2one('product.uom', string='UoM', required=True, ondelete='restrict')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, ondelete='restrict', default=lambda self: self.env.user.company_id.currency_id)
    uom_category_id = fields.Many2one('product.uom.category', compute='_uom_category_compute', string="UOM category", readonly=True)
    customer_id = fields.Many2one('res.partner', string='Customer', compute='_customer_id_compute', store=True)
    sale_line_id = fields.Many2one('sale.order.line', string='Sale line', required=False, ondelete='set null')
    
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
            Onchange du produit
        """
        uom_id = False
        category_id = False
        if self.product_id:
            uom_id = self.product_id.uom_id.id
            category_id = self.product_id.uom_id.category_id.id
            
        self.uom_id = uom_id
        self.uom_category_id = category_id
        self.price = self.product_id.get_price_sale(self.intervention_id.customer_id, False, qty_uom=self.qty, uom=self.uom_id, 
                                                    type='price', with_uoi=self.uom_id)
        
        
        
class type_failure_intervention(models.Model):
    """ 
        Type of failure intervention
    """
    _name = 'type.failure.intervention'
    _description = 'Type of failure intervention'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Name', size=256, required=True)



class cause_intervention(models.Model):
    """ 
        Cause intervention
    """
    _name = 'cause.intervention'
    _description = 'Cause intervention'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Name', size=256, required=True)