# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError

class product_product(models.Model):
    _inherit = 'product.product'
    _description = 'Product'


    @api.model
    def _type_mold_get(self):
        return [
                ('50', _('50/50')),
                ('100', _('100%')),
                ('75', _('75/25')),
                ('25', _('25/75')),
                       ]

    #===========================================================================
    # COLUMNS
    #===========================================================================
    is_mold = fields.Boolean(string='Mold', default=False)
    type_mold = fields.Selection('_type_mold_get', string='Type mold')
    number_imprint = fields.Integer(string='Number of imprint', default=0, required=False)
    
    
    def additional_function_domain(self, arg):
        """
        """
        arg0, arg1, arg_1 = super(product_product, self).additional_function_domain(arg)
        if arg[0] == 'domain_plastic_industry_mold':
            arg0 = 'id'
            arg1 = arg[1]
            arg_1 = []
            routing_id, resource_id, mo_id = arg[-1][0], arg[-1][1], arg[-1][-1]
            if mo_id:
                self.env.cr.execute("""
                    select
                        (select id from mrp_routing_line where routing_id = all_routing.routing_id order by sequence asc limit 1) as rl_id
                    from
                        (select 
                            routing_id 
                        from 
                            mrp_bom_mrp_routing_rel 
                        where 
                            bom_id = (select bom_id from mrp_manufacturingorder where id = %s)) all_routing
                """, (mo_id,))
                res_rl = self.env.cr.fetchall()  
                if res_rl:
                    rl_ids = [x[0] for x in res_rl]
                    
                if routing_id:
                    rl_ids = self.env['mrp.routing.line'].search([('id', 'in', rl_ids), ('routing_id', '=', routing_id)]).ids   
                
                if resource_id:
                    mrrc_obj = self.env['mrp.rl.resource.category']
                    rl_temp_ids = []
                    for rl in self.env['mrp.routing.line'].browse(rl_ids):
                        mrrc_rcs = mrrc_obj.search([('routing_line_id', '=', rl.id)], order='sequence asc', limit=1)
                        if mrrc_rcs.rl_resource_ids:
                            for rl_resource in mrrc_rcs.rl_resource_ids:
                                if rl_resource.resource_id and rl_resource.resource_id.id == resource_id:
                                    rl_temp_ids.append(rl.id)
                                    break 
                        else:
                            for resource in mrrc_rcs.category_id.resource_ids:
                                if resource.id == resource_id:
                                    rl_temp_ids.append(rl.id)
                    
                    rl_ids = rl_temp_ids
                
                rl_tool_rcs = self.env['mrp.rl.tools'].search([('routing_line_id', 'in', rl_ids)])
                for rl_tool in rl_tool_rcs:
                    if rl_tool.product_id and rl_tool.product_id.id not in arg_1:
                        arg_1.append(rl_tool.product_id.id)
                
        return arg0, arg1, arg_1