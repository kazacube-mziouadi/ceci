# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp.tools import ustr
from openerp.exceptions import except_orm, ValidationError


class mrp_add_operation(models.TransientModel):
    """ 
        Ajout d'operation à partir d'une gamme dans un OT
    """
    _name = 'mrp.add.operation'
    _description = "Ajout d'operation a partir d'une gamme dans un OT"
    _rec_name = 'wo_id'
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(mrp_add_operation, self).default_get(fields_list=fields_list)
        res['wo_id'] = self._context.get('active_id')
        wo = self.env['mrp.workorder'].browse(self._context.get('active_id'))
        if not wo.next_wo_ids:
            res['last_wo'] = True
            
        return res
    
    @api.one
    @api.depends('wo_id')
    def _compute_wo(self):
        last_wo = False
        if self.wo_id and not self.wo_id.next_wo_ids:
            last_wo = True
            
        self.last_wo = last_wo
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wo_id = fields.Many2one('mrp.workorder', string='WO', required=False, ondelete='cascade')
    routing_id = fields.Many2one('mrp.routing', string='Routing', required=False, ondelete='cascade')
    routing_line_ids = fields.Many2many('mrp.routing.line', 'mrp_routing_line_add_operation_rel', 'routing_id', 'bom_id', string='BoMs')
    solution1 = fields.Boolean(string='Solution1', default=False)
    solution2 = fields.Boolean(string='Solution2', default=False)
    solution3 = fields.Boolean(string='Solution3', default=False)
    solution4 = fields.Boolean(string='Solution4', default=False)
    last_wo = fields.Boolean(string='Last WO', _compute='_compute_wo')
    
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('routing_id')
    def _onchange_routing_id(self):
        """
        """
        routing_line_ids = []
        if self.routing_id and self.routing_id.routing_line_ids:
            routing_line_ids = [(6, 0, self.routing_id.routing_line_ids.ids)]
        
        self.routing_line_ids = routing_line_ids
    
    
    #===========================================================================
    # Boutons
    #===========================================================================
    @api.multi
    def button_validation(self):
        """
            Bouton de validation
        """
        for wiz in self:
            routing_line_ids = wiz.routing_line_ids and wiz.routing_line_ids.ids or []
            wiz.wo_id.add_operation_wo(routing_line_ids, wiz.solution1, wiz.solution2, wiz.solution3, wiz.solution4)
            
        return True