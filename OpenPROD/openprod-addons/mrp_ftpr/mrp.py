# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
import openerp.addons.decimal_precision as dp

    
class mrp_ftpr(models.Model):
    """ 
    FTPR 
    """
    _name = 'mrp.ftpr'
    _description = 'FTPR'
    _inherits = {'mrp.bom': 'ftpr_bom_id'}
    
    
    @api.one
    @api.depends('routing_id', 'routing_id.consumed_component_ids')
    def _compute_consumed_component_ids(self):
        self.consumed_component_ids = self.routing_id and self.routing_id.consumed_component_ids.ids or False
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    ftpr_bom_id = fields.Many2one('mrp.bom', string='BoM', required=True, ondelete='cascade')
    routing_id = fields.Many2one('mrp.routing', string='Routing', required=False, ondelete='set null')
    routing_line_ids = fields.One2many('mrp.routing.line', 'ftpr_id',  string='Routing lines', copy=True)
    name_ftpr = fields.Char(string='Name', size=256, required=True)
    operation_consumed_ids = fields.One2many('mrp.operation.consumed', related='routing_ids.operation_consumed_ids', copy=True)
    consumed_component_ids = fields.Many2many('mrp.bom', 'mrp_ftpr_mrp_bom_rel', 'ftpr_id', 'bom_id', string='Components', compute='_compute_consumed_component_ids')


    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('product_id', 'prod_family_id', 'type')
    def _onchange_product_id(self):
        """
            Au changement du produit, changement de la catégorie de l'uom et de la référence
        """
        if self.type == 'family':
            self.uom_id = self.prod_family_id and self.prod_family_id.uom_id or False
            self.name = self.name_ftpr = self.prod_family_id and self.prod_family_id.name or '/'
            self.product_id = False
        else:
            self.uom_id = self.product_id and self.product_id.uom_id or False
            self.name = self.product_id and self.product_id.code or '/'
            self.name_ftpr = self.product_id and "[%s] %s"%(self.name, self.product_id.name) or self.name
            self.prod_family_id = False
    
    
    @api.onchange('uom_id')
    def _onchange_uom_id(self):
        """
            Au changement du produit, changement de la catégorie de l'uom et de la référence
        """
        if self.uom_id:
            self.round = self.uom_id.rounding
            self.uom_category_id = self.uom_id.category_id
        else:
            self.round = 0.0
            self.uom_category_id = False
    

    #===========================================================================
    # FUNCTION & BUTTONS
    #===========================================================================
    @api.multi
    def wkf_draft(self):
        bom_rcs = self.env['mrp.bom']
        for ftpr in self:
            bom_rcs += ftpr.ftpr_bom_id
        
        bom_rcs.wkf_draft()
    
    @api.multi
    def wkf_active(self):
        bom_rcs = self.env['mrp.bom']
        for ftpr in self:
            bom_rcs += ftpr.ftpr_bom_id
        
        context = self.env.context.copy()
        context['no_compute_price'] = True
        bom_rcs.with_context(context).wkf_active()
        self.action_compute_price()
    
    
    @api.multi
    def wkf_obsolete(self):
        bom_rcs = self.env['mrp.bom']
        for ftpr in self:
            bom_rcs += ftpr.ftpr_bom_id
        
        bom_rcs.wkf_obsolete()
    
    
    @api.multi
    def action_compute_price(self):
        """ 
            Calcul du prix unitaire et total de la BoM, des sous produits et des composants en fonction de: BoM, Sub product, Component
        """
        bom_rcs = self.env['mrp.bom']
        for ftpr in self:
            bom_rcs += ftpr.ftpr_bom_id
        
        bom_rcs.action_compute_price()
        return True         
            
            
    @api.model
    def create(self, vals):
        """
            A la création de la FTPR, création de la gamme et nomenclature
        """
        ftpr = super(mrp_ftpr, self).create(vals)
        routing = self.env['mrp.routing'].create({
                                                  'name': ftpr.name_ftpr,
                                                  'price_qty': ftpr.price_qty,
                                                  'ftpr_id': ftpr.id,
                                                  'bom_ids': [(4, ftpr.ftpr_bom_id.id)]})
        
        ftpr.write({'routing_id': routing.id})
        return ftpr
    
    
    @api.multi
    def copy(self, default=None):
        """
            Copie d'OT
        """
        if not default:
            default = {}
            
        if not self.env.context.get('duplication'):
            raise except_orm(_('Error'), _('You must use the duplicating wizard.'))
            
        return super(mrp_ftpr, self).copy(default=default)
    


class mrp_routing_line(models.Model):
    """ 
        Routing line 
    """
    _inherit = 'mrp.routing.line' 
    #===========================================================================
    # COLUMNS
    #===========================================================================
    ftpr_id = fields.Many2one('mrp.ftpr', string='FTPR', required=False, ondelete='cascade')
    
    
    #===========================================================================
    # FUNCTION & BUTTONS
    #===========================================================================
    @api.model
    def create(self, vals):
        """
            A la création de la ligne de gamme, on vérifie les liens entre ftpr, gamme et ligne de gamme
        """

        routing_line = super(mrp_routing_line, self).create(vals)
        if not routing_line.ftpr_id and routing_line.routing_id.ftpr_id:
            routing_line.write({'ftpr_id': routing_line.routing_id.ftpr_id.id})
        elif routing_line.ftpr_id and not routing_line.routing_id:
            routing_line.write({'routing_id': routing_line.ftpr_id.routing_id.id})
            
        return routing_line
    
    
    @api.multi
    def button_add_resource_valid(self):
        for rl in self:
            existing_lines = []
            for rl_resource_category in rl.rl_resource_category_ids:
                vals = {}
                for rl_resource in rl_resource_category.rl_resource_ids:
                    vals = {
                            'resource_id': rl_resource.resource_id.id, 
                            'rl_resource_category_id': rl_resource_category.id, 
                            'sequence': rl_resource.sequence}
                    existing_lines.append([0, 0, vals])
                    
            vals['routing_line_id'] = rl.id
            vals['existing_resource_ids'] = existing_lines
            res_rcs = self.env['wizard.add.resource.valid'].create(vals)
            return {
                    'name': _('Add resource valid'),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'wizard.add.resource.valid',
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'res_id': res_rcs.id,
                    'nodestroy': True,
                    }



class mrp_routing(models.Model):
    """ 
        Routing 
    """
    _inherit = 'mrp.routing' 
    #===========================================================================
    # COLUMNS
    #===========================================================================
    ftpr_id = fields.Many2one('mrp.ftpr', string='FTPR', required=False, ondelete='cascade')
    
    
    #===========================================================================
    # FUNCTION & BUTTONS
    #===========================================================================
    @api.multi
    def wkf_draft(self):
        res = super(mrp_routing, self).wkf_draft()
        ctx = self.env.context.copy()
        if 'no_recursive_ftpr_routing' not in ctx or ( 'no_recursive_ftpr_routing' in ctx and not ctx['no_recursive_ftpr_routing']):
            ctx['no_recursive_ftpr_routing'] = True
            for routing in self:
                if routing.ftpr_id:
                    routing.ftpr_id.ftpr_bom_id.with_context(ctx).wkf_draft()
                
        return res
    
    
    @api.multi
    def wkf_active(self):
        res = super(mrp_routing, self).wkf_active()
        ctx = self.env.context.copy()
        if 'no_recursive_ftpr_routing' not in ctx or ( 'no_recursive_ftpr_routing' in ctx and not ctx['no_recursive_ftpr_routing']):
            ctx['no_recursive_ftpr_routing'] = True
            for routing in self:
                if routing.ftpr_id:
                    routing.ftpr_id.ftpr_bom_id.with_context(ctx).wkf_active()
                    
        return res
    
    
    @api.multi
    def wkf_obsolete(self):
        res = super(mrp_routing, self).wkf_obsolete()
        ctx = self.env.context.copy()
        if 'no_recursive_ftpr_routing' not in ctx or ( 'no_recursive_ftpr_routing' in ctx and not ctx['no_recursive_ftpr_routing']):
            ctx['no_recursive_ftpr_routing'] = True
            for routing in self:
                if routing.ftpr_id:
                    routing.ftpr_id.ftpr_bom_id.with_context(ctx).wkf_obsolete()
                    
        return res


    @api.multi
    def write(self, vals=None):
        """
            Redéfinition pour les gammes
        """
        res = super(mrp_routing, self).write(vals=vals)
        ctx = self.env.context.copy()
        if 'price_qty' in vals and ('no_recursive_ftpr_product' not in ctx or ('no_recursive_ftpr_product' in ctx and not ctx['no_recursive_ftpr_product'])):
            ctx['no_recursive_ftpr_routing'] = True
            for routing in self:
                if routing.ftpr_id:
                    routing.ftpr_id.product_id.with_context(ctx).write({'price_qty': vals['price_qty']}) 
                    
        return res
    
    

class mrp_bom(models.Model):
    """ 
        BOM
    """
    _inherit = 'mrp.bom' 
    
    
    @api.multi
    def wkf_draft(self):
        res = super(mrp_bom, self).wkf_draft()
        ctx = self.env.context.copy()
        ftpr_obj = self.env['mrp.ftpr']
        if 'no_recursive_ftpr_bom' not in ctx or ( 'no_recursive_ftpr_bom' in ctx and not ctx['no_recursive_ftpr_bom']):
            ctx['no_recursive_ftpr_bom'] = True
            for bom in self:
                ftpr_rcs = ftpr_obj.search([('ftpr_bom_id', '=', bom.id)])
                if ftpr_rcs:
                    ftpr_rcs.routing_id.with_context(ctx).wkf_draft()
                                                                        
        return res
    
    
    @api.multi
    def wkf_active(self):
        res = super(mrp_bom, self).wkf_active()
        ctx = self.env.context.copy()
        ftpr_obj = self.env['mrp.ftpr']
        if 'no_recursive_ftpr_bom' not in ctx or ( 'no_recursive_ftpr_bom' in ctx and not ctx['no_recursive_ftpr_bom']):
            ctx['no_recursive_ftpr_bom'] = True
            for bom in self:
                ftpr_rcs = ftpr_obj.search([('ftpr_bom_id', '=', bom.id)])
                if ftpr_rcs:
                    ftpr_rcs.routing_id.with_context(ctx).wkf_active()
                    
        return res
    
    
    @api.multi
    def wkf_obsolete(self):
        res = super(mrp_bom, self).wkf_obsolete()
        ctx = self.env.context.copy()
        ftpr_obj = self.env['mrp.ftpr']
        if 'no_recursive_ftpr_bom' not in ctx or ( 'no_recursive_ftpr_bom' in ctx and not ctx['no_recursive_ftpr_bom']):
            ctx['no_recursive_ftpr_bom'] = True
            for bom in self:
                ftpr_rcs = ftpr_obj.search([('ftpr_bom_id', '=', bom.id)])
                if ftpr_rcs:
                    ftpr_rcs.routing_id.with_context(ctx).wkf_obsolete()
                    
        return res    

