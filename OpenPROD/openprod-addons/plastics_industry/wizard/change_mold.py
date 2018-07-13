# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _


class change_mold(models.TransientModel):
    """ 
    Wizard change mold 
    """
    _name = 'change.mold'
    _description = 'Wizard change mold'
    _rec_name = 'wo_id'
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(change_mold, self).default_get(fields_list=fields_list)
        wo = self.env['mrp.workorder'].browse(self._context.get('active_id'))
        vals = {
            'wo_id': wo.id,
            'mo_id': wo.mo_id.id,
            'mold_id': wo.mold_id and wo.mold_id.id or False,
            'type_mold': wo.type_mold,
            'number_imprint': wo.number_imprint,
            'group_id': wo.group_wo_id and wo.group_wo_id.id or False,
        }
        
        res.update(vals)
        return res

    
    @api.model
    def _type_mold_get(self):
        return [
                ('50', _('50/50')),
                ('100', _('100%')),
                ('75', _('75/25')),
                ('25', _('25/75')),
                       ]

    @api.one
    @api.depends('wo_id')
    def _compute_with_wo_id(self):
        self.product_id = self.wo_id and self.wo_id.final_product_id and self.wo_id.final_product_id.id or False
        self.quantity = self.wo_id and self.wo_id.quantity or 0.0
        
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    product_id = fields.Many2one('product.product', string='Product', compute='_compute_with_wo_id')
    quantity = fields.Float(string='Quantity', compute='_compute_with_wo_id')
    date = fields.Datetime(string='Start date')
    mo_id = fields.Many2one('mrp.manufacturingorder', string='Mo', required=False, ondelete='set null')
    wo_id = fields.Many2one('mrp.workorder', string='WO', required=False, ondelete='set null')
    routing_id = fields.Many2one('mrp.routing', string='Routing', required=False, ondelete='set null')
    routing_line_id = fields.Many2one('mrp.routing.line', string='Routing line', required=False, ondelete='set null')
    resource_id = fields.Many2one('mrp.resource', string='Machin', required=False, ondelete='set null')
    mold_id = fields.Many2one('product.product', string='Mold', required=False, ondelete='set null')
    type_mold = fields.Selection('_type_mold_get', string='Type mold')
    number_imprint = fields.Integer(string='Number of imprint', default=0, required=False)
    group_id = fields.Many2one('mrp.group.wo', string='Group', required=False, ondelete='set null')
    
    
    @api.onchange('routing_id')
    def onchange_routing(self):
        routing_line_id = False
        mold_id = False
        type_mold = ''
        number_imprint = 0
        if self.routing_id:
            routing_line_rcs = self.env['mrp.routing.line'].search([('routing_id', '=', self.routing_id.id)], order='sequence asc', limit=1)
            if routing_line_rcs:
                routing_line_id = routing_line_rcs.id
                mold_id = routing_line_rcs.mold_id and routing_line_rcs.mold_id.id or False
                type_mold = routing_line_rcs.type_mold
                number_imprint = routing_line_rcs.number_imprint
                
        self.routing_line_id = routing_line_id
        self.mold_id = mold_id
        self.type_mold = type_mold
        self.number_imprint = number_imprint


    @api.multi
    def button_validate(self):
        wo_obj = self.env['mrp.workorder']
        for wiz in self:
            wo_rcs = wiz.wo_id
            if wiz.group_id:
                wo_rcs = self.env['mrp.workorder']
                for wo in wiz.group_id.wo_ids:
                    wo_rcs += wo
            
            for wo in wo_rcs:  
                mo =  wo.mo_id 
                mo.wkf_cancel()
                mo.workorder_ids.unlink()
                mo.wkf_draft()
                mo.action_generating_wo()
                new_wo = wo_obj.search([('mo_id', '=', mo.id), ('prev_wo_ids', '=', False)], limit=1)
                mold_id = wiz.mold_id and wiz.mold_id.id or False
                nb_product_parallel = new_wo.compute_mold(mold_id, wiz.type_mold, wiz.number_imprint)
                new_wo.wo_resource_ids.write({'nb_product_parallel': nb_product_parallel})
                modif_time_int = 1 + new_wo.modif_time_int
                vals_wo = {'mold_id': mold_id, 'type_mold': wiz.type_mold, 'number_imprint': wiz.number_imprint, 'modif_time_int': modif_time_int}
                if wiz.group_id:
                    vals_wo['group_wo_id'] = wiz.group_id.id
                    
                new_wo.write(vals_wo)
                if wiz.resource_id and new_wo.first_resource_id != wiz.resource_id:
                    new_wo.change_resource(new_wo.first_wo_resource_id, wiz.resource_id, new_wo.first_wo_resource_id.rl_resource_category_id, add_resource_rl=False, no_plannif=True)
                
                if wiz.date:
                    wo_obj.plannification_mo_at_earlier(wiz.date, 
                                                      mo, 
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
        
        return {'type':'ir.actions.act_window_view_reload'}
    
    
    
    
    