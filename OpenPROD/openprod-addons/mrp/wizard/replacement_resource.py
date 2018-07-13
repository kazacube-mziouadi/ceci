# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError

class replacement_resource(models.TransientModel):
    """ 
    Replacement resource
    """
    _name = 'replacement.resource'
    _description = 'Replacement resource'
    _rec_name = 'resource_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    resource_id = fields.Many2one('mrp.resource', string='Resource', required=True, ondelete='cascade')
    new_resource_id = fields.Many2one('mrp.resource', string='New Resource', required=True, ondelete='cascade')
    line_ids = fields.One2many('replacement.resource.line', 'modif_resource_id',  string='Line')
    
    @api.onchange('resource_id')
    def _onchange_resource_id(self):
        # TODO: commentaire
        list = []
        if self.resource_id:
            rl_resource_obj = self.env['mrp.rl.resource']
            rl_obj = self.env['mrp.routing.line']
            rl_resource_ids = rl_resource_obj.search([('resource_id', '=', self.resource_id.id)])
            if rl_resource_ids:
                for rl_resource in rl_resource_ids:
                    if rl_resource.rl_category_id:
                        routing_line_ids = rl_obj.search([('rl_resource_category_ids', '=', rl_resource.rl_category_id.id)])
                        for routing_line in routing_line_ids:
                            if routing_line.product_id:
                                list.append({'product_id': routing_line.product_id.id, 'routing_line_id': routing_line.id, 'resource_valid_id': rl_resource.id})
                                
        else:
            self.new_resource_id = False
            
        self.line_ids = list
        
        
    @api.multi
    def action_validate(self):
        # TODO: commentaire
        if not self.resource_id: raise except_orm('There is not resource.')
        if not self.new_resource_id: raise except_orm('There is not new resource')
        if not self.line_ids: raise except_orm(_('There is not lines.'))
        
        rl_res_rs = self.env['mrp.rl.resource']
        for line in self.line_ids:
            if line.resource_valid_id:
                rl_res_rs += line.resource_valid_id
                
        if rl_res_rs:
            rl_res_rs.write({'resource_id': self.new_resource_id.id})
            
        return {'type': 'ir.actions.act_window_close'}
    
        
        
class replacement_resource_line(models.TransientModel):
    """ 
    Replacement resource line
    """
    _name = 'replacement.resource.line'
    _description = 'Replacement resource line' 
    _rec_name = 'product_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='cascade')
    modif_resource_id = fields.Many2one('replacement.resource', string='Modif resource', required=False, ondelete='cascade')
    routing_line_id = fields.Many2one('mrp.routing.line', string='Routing line', required=False, ondelete='cascade')
    resource_valid_id = fields.Many2one('mrp.rl.resource', string='Resource', required=False, ondelete='cascade')