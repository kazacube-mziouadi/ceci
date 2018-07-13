# -*- coding: utf-8 -*-
from openerp import models, api, fields


class mrp_bom(models.Model):
    _inherit = 'mrp.bom'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    affair_id = fields.Many2one('affair', string='Affair', required=False, ondelete='restrict')
    
    
    
class mrp_routing_line(models.Model):
    _inherit = 'mrp.routing.line'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    affair_id = fields.Many2one('affair', string='Affair', required=False, ondelete='restrict')
    
    
    
        
class mrp_manufacturingorder(models.Model):
    _inherit = 'mrp.manufacturingorder'

    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    affair_id = fields.Many2one('affair', string='Affair', required=False, ondelete='restrict', select=True)


        
class mrp_workorder(models.Model):
    _inherit = 'mrp.workorder'
    
    @api.one
    @api.depends('mo_id.affair_id')
    def _compute_affair_id(self):
        """
            Fonction qui récupère l'affaire de l'OF
        """
        self.affair_id = self.mo_id.affair_id.id
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    affair_id = fields.Many2one('affair', string='Affair', compute='_compute_affair_id', store=True, select=True)
    
    def plannification_mo_at_earlier(self, date, mo, is_sublevel=False, is_procur_level_manufact=False,
                                           is_product_sublevel_manufact=False, is_procur_level_purchase=False, automatic_purchase=False,
                                           is_procur_sublevel_purchase=False, first_mo_id=False, is_delay_rm=False, change_resources=False, no_modif_prio_date=False):

        res = super(mrp_workorder, self).plannification_mo_at_earlier(date, 
                                                                                   mo, 
                                                                                   is_sublevel=is_sublevel, 
                                                                                   is_procur_level_manufact=is_procur_level_manufact,
                                                                                   is_product_sublevel_manufact=is_product_sublevel_manufact, 
                                                                                   is_procur_level_purchase=is_procur_level_purchase, 
                                                                                   automatic_purchase=automatic_purchase,
                                                                                   is_procur_sublevel_purchase=is_procur_sublevel_purchase, 
                                                                                   first_mo_id=first_mo_id,
                                                                                   is_delay_rm=is_delay_rm,
                                                                                   change_resources=change_resources, 
                                                                                   no_modif_prio_date=no_modif_prio_date)
        if mo.affair_id and not first_mo_id:
            wo_rs = self.search([('affair_id', '=', mo.affair_id.id)])
            if wo_rs:
                wo_rs.compute_sorting_level()
            
        return res


    def plannification_mo_at_the_latest(self, date, mo, is_sublevel=False, is_procur_level_manufact=False,
                                              is_product_sublevel_manufact=False, is_procur_level_purchase=False, automatic_purchase=False,
                                              is_procur_sublevel_purchase=False, first_pass=False, change_resources=False, no_modif_prio_date=False):
        res = super(mrp_workorder, self).plannification_mo_at_the_latest(date, 
                                                   mo, 
                                                   is_sublevel=is_sublevel, 
                                                   is_procur_level_manufact=is_procur_level_manufact, 
                                                   is_product_sublevel_manufact=is_product_sublevel_manufact, 
                                                   is_procur_level_purchase=is_procur_level_purchase, 
                                                   automatic_purchase=automatic_purchase,
                                                   is_procur_sublevel_purchase=is_procur_sublevel_purchase, 
                                                   first_pass=first_pass, change_resources=change_resources, 
                                                   no_modif_prio_date=no_modif_prio_date)

        if mo.affair_id and first_pass:
            wo_rs = self.search([('affair_id', '=', mo.affair_id.id)])
            if wo_rs:
                wo_rs.compute_sorting_level()
            
        return res
    