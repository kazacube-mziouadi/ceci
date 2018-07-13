# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError

class mrp_replacement_resource(models.Model):
    """ 
    Replacement resource
    """
    _name = 'mrp.replacement.resource'
    _description = 'Replacement resource'
    _rec_name = 'resource_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    resource_id = fields.Many2one('mrp.resource', string='Resource', required=True, ondelete='cascade')
    new_resource_id = fields.Many2one('mrp.resource', string='New Resource', required=True, ondelete='cascade')
    line_ids = fields.One2many('mrp.replacement.resource.line', 'modif_resource_id',  string='Line')
    is_valid = fields.Boolean(string='Valid', default=False)
    validation_date = fields.Date(string='Validation Date')
    
    @api.onchange('resource_id')
    def _onchange_resource_id(self):
        # Onchange sur les ressources
        list_resource = []
        if self.resource_id:
            rl_resource_obj = self.env['mrp.rl.resource']
            rl_obj = self.env['mrp.routing.line']
            rl_resource_ids = rl_resource_obj.search([('resource_id', '=', self.resource_id.id)])
            for rl_resource in rl_resource_ids:
                if rl_resource.rl_category_id:
                    routing_line_ids = rl_obj.search([('rl_resource_category_ids', '=', rl_resource.rl_category_id.id)])
                    for routing_line in routing_line_ids:
                        if routing_line.product_id:
                            dict_replacement_resource_line = {'routing_id':routing_line.routing_id.id, 'product_id': routing_line.product_id.id, 
                                                              'routing_line_id': routing_line.id, 'resource_valid_id': rl_resource.id}
                            list_resource.append((0, 0, dict_replacement_resource_line))
        else:
            self.new_resource_id = False
         
        self.line_ids = list_resource
        
        
    @api.multi
    def action_validate(self):
        # Action de validation
        if not self.resource_id: 
            raise except_orm(_('There is not resource.'))
        
        if not self.new_resource_id: 
            raise except_orm(_('There is not new resource'))
        
        if not self.line_ids: 
            raise except_orm(_('There is not lines.'))
        
        rl_res_rs = self.env['mrp.rl.resource']
        for line in self.line_ids:
            if line.resource_valid_id:
                rl_res_rs += line.resource_valid_id
                
        if rl_res_rs:
            rl_res_rs.write({'resource_id': self.new_resource_id.id})
            self.write({'is_valid':True})
        
        self.write({'validation_date': fields.Date.today()})
        return {'type': 'ir.actions.act_window_close'}
    
        
class mrp_replacement_resource_line(models.Model):
    """ 
        Replacement resource line
    """
    _name = 'mrp.replacement.resource.line'
    _description = 'Replacement resource line' 
    _rec_name = 'product_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='cascade')
    modif_resource_id = fields.Many2one('mrp.replacement.resource', string='Modif resource', required=True, ondelete='cascade')
    routing_id = fields.Many2one('mrp.routing', string='Routing', required=False, ondelete='cascade')
    routing_line_id = fields.Many2one('mrp.routing.line', string='Routing line', required=False, ondelete='cascade')
    resource_valid_id = fields.Many2one('mrp.rl.resource', string='Resource', required=False, ondelete='cascade')