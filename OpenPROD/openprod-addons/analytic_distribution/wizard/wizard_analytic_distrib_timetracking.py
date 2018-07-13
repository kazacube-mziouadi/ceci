# -*- coding: utf-8 -*-
from openerp import models, fields, api, tools, _


class wizard_analytic_distrib_timetracking(models.TransientModel):
    """ 
        Wizard which allow to assign analytic distribution to time lines
    """
    _name = 'wizard.analytic.distrib.timetracking'
    _description = 'Wizard which allow to assign analytic distribution to time lines'
            
    #===========================================================================
    # COLUMNS
    #===========================================================================
    show_warning = fields.Boolean(string='Show warning', default=False)
    analytic_distribution_id = fields.Many2one('product.analytic.distribution', string='Analytic distribution', required=False, ondelete='set null')
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='set null', 
                                 domain=[('state', 'in', ('lifeserie', 'endlife')), ('sale_ok', '=', True)],
                                 help="The analytic line will take the expense account of this product", )
    
    @api.model
    def default_get(self, fields_list):
        """
            Surcharge du default_get pour afficher ou non le warning
        """
        res = super(wizard_analytic_distrib_timetracking, self).default_get(fields_list=fields_list)
        context = self.env.context
        if context.get('active_model') == 'resource.timetracking' and context.get('active_ids'):
            for time_read in self.env['resource.timetracking'].browse(context['active_ids']).read(['analytic_line_ids'], load='_classic_write'):
                if time_read.get('analytic_line_ids'):
                    res['show_warning'] = True
            
        return res
    
    
    @api.multi
    def create_analytic_lines(self):
        """
            On génère les lignes analytiques et on les assigne aux temps 
        """
        timetracking_obj = self.env['resource.timetracking']
        for wizard in self:
            if wizard.analytic_distribution_id and wizard.product_id and  self.env.context.get('active_ids'):
                timetracking_obj.browse(self.env.context['active_ids']).create_analytic_lines(wizard.analytic_distribution_id, wizard.product_id)
                
        return {'type': 'ir.actions.act_window_close'}
    

class wizard_delete_analytic_line_timetracking(models.TransientModel):
    """ 
        Wizard which allow to delete analytic lines linked to timetracking
    """
    _name = 'wizard.delete.analytic.line.timetracking'
    _description = 'Wizard which allow to assign analytic distribution to time lines'
            
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Name', size=32, required=False)
    
    
    @api.multi
    def delete_analytic_lines(self):
        """
            On supprime les lignes analytiques
        """
        timetracking_obj = self.env['resource.timetracking']
        for wizard in self:
            if self.env.context.get('active_ids'):
                timetracking_obj.browse(self.env.context['active_ids']).delete_analytic_lines()
                
        return {'type': 'ir.actions.act_window_close'}
