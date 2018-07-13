# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _



class purchase_order_line(models.Model):
    """ 
        description 
    """
    _inherit = 'purchase.order.line'
    
    @api.one
    @api.depends('product_id')
    def _compute_substituent_ids(self):
        """
            Calcul des produits de substitions déjà utilisés
        """
        is_substitution = False
        component = False
        # Partie soustraitance PF
        if self.wo_fp_subcontracting_id:
            is_substitution = False
        # Partie soustraitance MP
        elif self.wo_rm_subcontracting_id:
            component = self.subc_origin_move_id and self.subc_origin_move_id.component_id or False
        # Partie MP
        else:
            procurement = self.env['procurement.order'].search([('pol_id', '=', self.id), ('origin_wo_id', '!=', False), ('move_id', '!=', False)], limit=1)
            if procurement:
                component = procurement.move_id and procurement.move_id.component_id or False
        
        if component:
            product_ids = component.return_substitution_product_ids()
            if component.product_id.id != self.product_id.id:
                product_ids.append(component.product_id.id)

            if self.product_id.id in product_ids:
                product_ids.remove(self.product_id.id)
            
            if product_ids:
                is_substitution = True

        self.is_substitution = is_substitution
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    is_substitution = fields.Boolean(compute='_compute_substituent_ids',  string='Is substitution')
