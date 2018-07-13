# -*- coding: utf-8 -*-
from openerp import models, fields, api



class mrp_resource(models.Model):
    """ 
        Resource 
    """
    _inherit = 'mrp.resource'
    
    
    def additional_function_domain(self, arg):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de mrp_resource
        """
        arg0, arg1, arg_1 = super(mrp_resource, self).additional_function_domain(arg)
        if arg and arg[0] == 'domain_resource_gmao':
            arg0 = 'id'
            arg1 = 'in'
            resource_ids = []
            if arg[-1]:
                for x in arg[-1]:
                    if x[1] not in resource_ids:
                        resource_ids.append(x[1])
            
            arg_1 = list(set(resource_ids))
            
        return arg0, arg1, arg_1



class mrp_workorder(models.Model):
    """ 
        Workorder 
    """
    _inherit = 'mrp.workorder'
     
     
    #===========================================================================
    # COLUMNS
    #===========================================================================
    intervention_id = fields.Many2one('intervention', string='Intervention', required=False, ondelete='restrict')
 
 
 
class mrp_manufacturingorder(models.Model):
    """ 
        Manufacturing order 
    """
    _inherit = 'mrp.manufacturingorder'
     
     
    #===========================================================================
    # COLUMNS
    #===========================================================================
    intervention_id = fields.Many2one('intervention', string='Intervention', required=False, ondelete='restrict')
    
    
    def validate_move_fp_intervention(self):
        """
            Fonction utilisé dans la GMAO qui permet lors de la plannification au plus tard de valider les mouvements finaux du premier OT qui sont les matières 
            démontées pour ne pas lancer la production ou l'achat des produits à remonter dans le dernier OT.
        """
        res = super(mrp_manufacturingorder, self).validate_move_fp_intervention()
        if self.intervention_id:
            first_workorder_rcs = self.env['mrp.workorder'].search([('mo_id', '=', self.id), ('state', 'not in', ('cancel', 'done'))], order='sequence asc', limit=1)
            if first_workorder_rcs:
                fp_draft_rcs = self.env['stock.move'].search([('state', '=', 'draft'), '|', ('wo_outgoing_id', '=', first_workorder_rcs.id), ('wo_fp_subcontracting_id', '=', first_workorder_rcs.id)])
                if fp_draft_rcs:
                    fp_draft_rcs.wkf_waiting()

        return res
    


class mrp_routing_line(models.Model):
    """ 
        mrp_routing_line 
    """
    _inherit = 'mrp.routing.line'
    
    
    def additional_function_domain(self, arg):
        """
            Fonction qui permet de faire un point d'entrée pour modifier le domain du search dans un module qui hérite de mrp_resource
        """
        arg0, arg1, arg_1 = False, False, False
        if arg and arg[0] == 'domain_operation_mo_repair':
            arg0 = 'id'
            arg1 = 'in'
            operation_ids = []
            arg_1 = operation_ids
            all_operation_ids = []
            if arg[-1] and arg[-1][0] and arg[-1][0][0]:
                all_operation_ids = arg[-1][0][0][-1]
            
            used_all_operation_ids = []
            if arg[-1] and arg[-1][1] and arg[-1][1][0]:
                used_all_operation_ids = arg[-1][1][0][-1]

            if all_operation_ids:
                if used_all_operation_ids:
                    operation_ids = list(set(all_operation_ids) - set(used_all_operation_ids))
                else:
                    operation_ids = all_operation_ids
            
            arg_1 = operation_ids
            
        return arg0, arg1, arg_1
    
    
    
    
    
    
    
    