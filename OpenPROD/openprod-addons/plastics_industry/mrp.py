# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError


class mrp_routing_line(models.Model):
    """ 
        MRP Routing Line 
    """
    _inherit = 'mrp.routing.line'

    
    @api.model
    def _type_mold_get(self):
        return [
                ('50', _('50/50')),
                ('100', _('100%')),
                ('75', _('75/25')),
                ('25', _('25/75')),
                       ]
        
        
    @api.one
    @api.depends('tool_ids', 'tool_ids.product_id')
    def compute_mold(self):
        """
            Calcul la première ressource et sa catégorie
        """
        mold_id = False
        type_mold = ''
        number_imprint = ''
        for tool in self.tool_ids:
            if tool.product_id.is_mold and tool.product_id.state in ('lifeserie', 'endlife'):
                mold_id = tool.product_id.id
                type_mold = tool.product_id.type_mold
                number_imprint = tool.product_id.number_imprint
                break
        
        self.mold_id = mold_id
        self.type_mold = type_mold
        self.number_imprint = number_imprint
            

    #===========================================================================
    # COLUMNS
    #===========================================================================
    mold_id = fields.Many2one('product.product', string='Mold', compute='compute_mold')
    type_mold = fields.Selection('_type_mold_get', string='Type mold', compute='compute_mold')
    number_imprint = fields.Integer(string='Number of imprint', default=0, required=False, compute='compute_mold')


    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('tool_ids', 'tool_ids.product_id')
    def _onchange_rl_resource_category_ids(self):
        """
            Calcul séquence
        """
        if self.mold_id:
            if self.type_mold == '50':
                nb_product_parallel = self.number_imprint / 2 or 1
            elif self.type_mold == '75':
                nb_product_parallel = self.number_imprint * 0.75 or 1
            elif self.type_mold == '25':
                nb_product_parallel = self.number_imprint * 0.25 or 1
            else:
                nb_product_parallel = self.number_imprint or 1
            
            self.nb_product_parallel = nb_product_parallel
        else:
            self.nb_product_parallel = 1



class mrp_routing(models.Model):
    """ 
        MRP Routing 
    """
    _inherit = 'mrp.routing'    
    
    
    def additional_function_domain(self, arg):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de mrp_resource
        """
        arg0, arg1, arg_1 = super(mrp_routing, self).additional_function_domain(arg)
        if arg[0] == 'domain_plastic_industry_routing':
            arg0 = 'id'
            arg1 = arg[1]
            arg_1 = []
            resource_id, mold_id, mo_id = arg[-1][0], arg[-1][1], arg[-1][-1]
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
                    if mold_id:
                        rl_tool_rcs = self.env['mrp.rl.tools'].search([('routing_line_id', 'in', rl_ids), ('product_id', '=', mold_id)])
                        rl_ids = []
                        for rl_tool in rl_tool_rcs:
                            rl_ids.append(rl_tool.routing_line_id.id)
                    
                    for rl in self.env['mrp.routing.line'].browse(rl_ids):
                        if rl.routing_id.id not in arg_1:
                            arg_1.append(rl.routing_id.id)
                            
                    if resource_id:
                        arg_1 = []
                        mrrc_obj = self.env['mrp.rl.resource.category']
                        for rl in self.env['mrp.routing.line'].browse(rl_ids):
                            mrrc_rcs = mrrc_obj.search([('routing_line_id', '=', rl.id)], order='sequence asc', limit=1)
                            if mrrc_rcs.rl_resource_ids:
                                for rl_resource in mrrc_rcs.rl_resource_ids:
                                    if rl_resource.resource_id and rl_resource.resource_id.id == resource_id:
                                        arg_1.append(rl.routing_id.id)
                                        break 
                            else:
                                for resource in mrrc_rcs.category_id.resource_ids:
                                    if resource.id == resource_id:
                                        arg_1.append(rl.routing_id.id)
                                        break    

        return arg0, arg1, arg_1



class mrp_workorder(models.Model):
    """ 
        Workorder 
    """
    _inherit = 'mrp.workorder'

    
    
    @api.model
    def _type_mold_get(self):
        return [
                ('50', _('50/50')),
                ('100', _('100%')),
                ('75', _('75/25')),
                ('25', _('25/75')),
                       ]
        
    
    @api.one
    def _compute_need_delay_validation(self):
        self.need_delay_validation = self.mo_id and self.mo_id.need_delay_validation or False
        
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    mold_id = fields.Many2one('product.product', string='Mold', required=False, ondelete='restrict')
    type_mold = fields.Selection('_type_mold_get', string='Type mold')
    number_imprint = fields.Integer(string='Number of imprint', default=0, required=False)
    need_delay_validation = fields.Boolean(compute="_compute_need_delay_validation")
    

    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('tool_ids', 'tool_ids.product_id')
    def _onchange_tools_mold(self):
        """
            Calcul séquence
        """
        mold_id, type_mold, number_imprint = self.compute_tools_mold()
        self.mold_id = mold_id
        self.type_mold = type_mold
        self.number_imprint = number_imprint
    
    
    def compute_tools_mold(self):
        mold_id = False
        type_mold = ''
        number_imprint = ''
        for tool in self.tool_ids:
            if tool.product_id.is_mold and tool.product_id.state in ('lifeserie', 'endlife'):
                mold_id = tool.product_id.id
                type_mold = tool.product_id.type_mold
                number_imprint = tool.product_id.number_imprint
                break
        
        return mold_id, type_mold, number_imprint
    
    
    @api.onchange('mold_id', 'type_mold', 'number_imprint')
    def _onchange_mold(self):
        """
            Calcul séquence
        """
        nb_product_parallel = self.compute_mold(self.mold_id, self.type_mold, self.number_imprint)
        for wo_resource in self.wo_resource_ids:
            wo_resource.nb_product_parallel = nb_product_parallel

    
    def compute_mold(self, mold_id, type_mold, number_imprint):
        if mold_id:
            if type_mold == '50':
                nb_product_parallel = number_imprint / 2.0 or 1
            elif type_mold == '75':
                nb_product_parallel = number_imprint * 0.75 or 1
            elif type_mold == '25':
                nb_product_parallel = number_imprint * 0.25 or 1
            else:
                nb_product_parallel = number_imprint or 1
            
            nb_product_parallel = nb_product_parallel
        else:
            nb_product_parallel = 1
        
        return nb_product_parallel
        
        
    def vals_platics_industry(self):
        res = super(mrp_workorder, self).vals_platics_industry()
        mold_id, type_mold, number_imprint = self.compute_tools_mold()
        nb_product_parallel = self.compute_mold(mold_id, type_mold, number_imprint)
        self.write({'mold_id': mold_id, 'type_mold': type_mold, 'number_imprint': number_imprint})
        self.wo_resource_ids.write({'nb_product_parallel': nb_product_parallel})
        return res
    
    
    @api.multi
    def conf_delay_button(self):
        for wo in self:
            return wo.mo_id.conf_delay_button()
        
        
    
class mrp_group_wo(models.Model):
    _inherit = 'mrp.group.wo'    
    
    
    def no_constraint(self):
        return True
    
    
    @api.onchange('wo_ids')
    def _onchange_wo_ids(self):
        for wo in self.wo_ids:
            self.duration = wo.total_time_theo
  
  
    @api.model
    def create(self, vals=None):
        """
        """
        if 'wo_ids' in vals:
            wo_ids = [x[1] for x in vals['wo_ids'] if x[0] == 4]
            resource_id = False
            mold_id = False
            routing_line_id = False
            for wo in self.env['mrp.workorder'].browse(wo_ids):
                if (wo.routing_line_id and wo.routing_line_id.id == routing_line_id) or not routing_line_id:
                    routing_line_id = wo.routing_line_id.id
                else:
                    raise except_orm(_('Error'), _('Work orders must have the same routing line.'))
                
                if (wo.mold_id and wo.mold_id.id == mold_id) or not mold_id:
                    mold_id = wo.mold_id.id
                else:
                    raise except_orm(_('Error'), _('Work orders must have the same mold.'))
                
                if (wo.first_resource_id and wo.first_resource_id.id == resource_id) or not resource_id:
                    resource_id = wo.first_resource_id.id
                else:
                    raise except_orm(_('Error'), _('Work orders must have the same resource.'))
                
        
        res = super(mrp_group_wo, self).create(vals=vals)
        return res   
                
            
            
class mrp_resource(models.Model):
    """ 
        resource 
    """
    _inherit = 'mrp.resource'
    
    
    def additional_function_domain(self, arg):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de mrp_resource
        """
        arg0, arg1, arg_1 = super(mrp_resource, self).additional_function_domain(arg)
        if arg[0] == 'domain_plastic_industry_resource':
            arg0 = 'id'
            arg1 = arg[1]
            arg_1 = []
            routing_id, mold_id, mo_id = arg[-1][0], arg[-1][1], arg[-1][-1]
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
                    
                    if mold_id:
                        rl_tool_rcs = self.env['mrp.rl.tools'].search([('routing_line_id', 'in', rl_ids), ('product_id', '=', mold_id)])
                        rl_ids = []
                        for rl_tool in rl_tool_rcs:
                            rl_ids.append(rl_tool.routing_line_id.id)
                    
                    mrrc_obj = self.env['mrp.rl.resource.category']
                    for rl in self.env['mrp.routing.line'].browse(rl_ids):
                        mrrc_rcs = mrrc_obj.search([('routing_line_id', '=', rl.id)], order='sequence asc', limit=1)
                        if mrrc_rcs.rl_resource_ids:
                            for rl_resource in mrrc_rcs.rl_resource_ids:
                                if rl_resource.resource_id and rl_resource.resource_id.id not in arg_1:
                                    arg_1.append(rl_resource.resource_id.id)
                        else:
                            for resource in mrrc_rcs.category_id.resource_ids:
                                if resource.id not in arg_1:
                                    arg_1.append(resource.id)
        
        return arg0, arg1, arg_1
    
    
    
    
                