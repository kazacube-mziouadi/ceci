# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
import time, datetime

class add_operation_in_park(models.TransientModel):
    """ 
        ADD operation in park
    """
    _name = 'add.operation.in.park'
    _description = 'ADD operation in park'
    _rec_name = 'park_id'
    
    @api.model
    def default_get(self, fields_list):
        res = super(add_operation_in_park, self).default_get(fields_list=fields_list)
        res['park_id'] = self._context.get('active_id')
        return res
    
    
    @api.one
    @api.depends('park_id')
    def _all_operation_compute(self):
        """
            All resource pour le domaine
        """
        self.all_operation_ids = [x.maintenance_operation_id.id for x in self.park_id.maintenance_operation_ids]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    park_id = fields.Many2one('park', string='Park', required=False, ondelete='cascade')
    all_operation_ids = fields.One2many('maintenance.operation', compute='_all_operation_compute',  string='All operations')
    maintenance_operation_ids = fields.Many2many('maintenance.operation', 'wiz_add_operation_maintenance_operation', 'wiz_id', 'operation_id',  string='Maintenance operations')
    
    #===========================================================================
    # Bouton
    #===========================================================================
    @api.multi
    def action_validation(self):
        """
            Bouton de validation
        """
        pmo_obj = self.env['park.maintenance.operation']
        for wiz in self:
            if wiz.maintenance_operation_ids and wiz.park_id:
                for maintenance_operation in wiz.maintenance_operation_ids:
                    pmo_obj.create({'maintenance_operation_id': maintenance_operation.id, 'park_id': wiz.park_id.id})
                
        return {'type': 'ir.actions.act_window_close'}



class add_park_in_operation(models.TransientModel):
    """ 
        ADD park in operation
    """
    _name = 'add.park.in.operation'
    _description = 'ADD park in operation'
    _rec_name = 'maintenance_operation_id'
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(add_park_in_operation, self).default_get(fields_list=fields_list)
        res['maintenance_operation_id'] = self._context.get('active_id')
        return res
    
    
    @api.one
    @api.depends('park_ids')
    def _all_park_compute(self):
        """
            All park pour le domaine
        """
        self.all_park_ids = [x.park_id.id for x in self.maintenance_operation_id.park_ids]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    maintenance_operation_id = fields.Many2one('maintenance.operation', string='Maintenance operation', required=False, ondelete='cascade')
    all_park_ids = fields.One2many('park', compute='_all_park_compute',  string='All parks')
    park_ids = fields.Many2many('park', 'wiz_add_park_maintenance_operation', 'wiz_id', 'park_id',  string='Parks')
    
    #===========================================================================
    # Bouton
    #===========================================================================
    @api.multi
    def action_validation(self):
        """
            Bouton de validation
        """
        pmo_obj = self.env['park.maintenance.operation']
        for wiz in self:
            if wiz.park_ids and wiz.maintenance_operation_id:
                for park in wiz.park_ids:
                    pmo_obj.create({'maintenance_operation_id': wiz.maintenance_operation_id.id, 'park_id': park.id})
                
        return {'type': 'ir.actions.act_window_close'}

    