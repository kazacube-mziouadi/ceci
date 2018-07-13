# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
import openerp.addons.decimal_precision as dp

class mrp_planning_mo_at_earlier(models.TransientModel):
    """ 
        ManufacturingOrder Planning at earlier
    """
    _name = 'mrp.planning.mo.at.earlier'
    _description = 'ManufacturingOrder Planning at earlier'
    _rec_name = 'mo_id'
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(mrp_planning_mo_at_earlier, self).default_get(fields_list=fields_list)
        # Fonction permettant de passer par défaut l'id de l'OF ouvert
        if self.env.context.get('active_model') == 'mrp.simulation':
            mo = self.env['mrp.simulation'].browse(self.env.context.get('active_id')).mo_id
        else:
            mo = self.env['mrp.manufacturingorder'].browse(self.env.context.get('active_id'))
        
        res['mo_id'] = mo.id
        res['date'] = mo.min_start_date
            
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    date = fields.Datetime(string='Date', required=True)
    mo_id = fields.Many2one('mrp.manufacturingorder', string='Manufacturing Order', required=True, ondelete='cascade')
    is_procur_level_manufact = fields.Boolean(string='Procurement level', default=False)
    is_product_sublevel_manufact = fields.Boolean(string='Procurement Sublevel', default=False)
    is_procur_level_purchase = fields.Boolean(string='Procurement level', default=False)
    is_procur_sublevel_purchase = fields.Boolean(string='Procurement Sublevel', default=False)
    automatic_purchase = fields.Boolean(string='Generate Purchase', default=False)
    is_sublevel = fields.Boolean(string='Generate Full', default=False)
    change_resources = fields.Boolean(string='Load balancing', default=True)
    is_delay_rm = fields.Boolean(string='RM delay', default=False)
    is_from_simulation = fields.Boolean(default=False)
    
        
    #===========================================================================
    # Boutons
    #===========================================================================
    @api.multi
    def button_plannification_mo_at_earlier(self):
        """
            Bouton qui plannifie l'OF au plus tôt
        """
        wo_obj = self.env['mrp.workorder']
        for wiz in self:
            date = wiz.date_plannif()
            wo_obj.plannification_mo_at_earlier(date, 
                                              wiz.mo_id, 
                                              is_sublevel=wiz.is_sublevel, 
                                              is_procur_level_manufact=wiz.is_procur_level_manufact,
                                              is_product_sublevel_manufact=wiz.is_product_sublevel_manufact,
                                              is_procur_level_purchase=wiz.is_procur_level_purchase,
                                              automatic_purchase=wiz.automatic_purchase,
                                              is_procur_sublevel_purchase=wiz.is_procur_sublevel_purchase,
                                              first_mo_id=False,
                                              is_delay_rm=wiz.is_delay_rm,
                                              change_resources=wiz.change_resources, 
                                              no_modif_prio_date=False)
        return True
    
    
    def date_plannif(self):
        """
            Point d'entrée pour brightloop car eux on choisie d'avoir un champ date et de passer comme heure 12:00
        """
        return self.date
    
    #===========================================================================
    # On Change
    #===========================================================================
    @api.onchange('is_procur_level_manufact')
    def _onchange_is_procur_level_manufact(self):
        if not self.is_procur_level_manufact:
            self.is_product_sublevel_manufact = False
            
    
    @api.onchange('is_product_sublevel_manufact')
    def _onchange_is_product_sublevel_manufact(self):
        if self.is_product_sublevel_manufact:
            self.is_procur_level_manufact = True
    
    
    @api.onchange('is_procur_level_purchase')
    def _onchange_is_procur_level_purchase(self):
        if not self.is_procur_level_purchase:
            self.is_procur_sublevel_purchase = False
            
    
    @api.onchange('is_procur_sublevel_purchase')
    def _onchange_is_procur_sublevel_purchase(self):
        if self.is_procur_sublevel_purchase:
            self.is_procur_level_purchase = True
    
    
        
class mrp_planning_mo_at_the_latest(models.TransientModel):
    """ 
        ManufacturingOrder Planning at the latest
    """
    _name = 'mrp.planning.mo.at.the.latest'
    _description = 'ManufacturingOrder Planning at the latest'
    _rec_name = 'mo_id'
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(mrp_planning_mo_at_the_latest, self).default_get(fields_list=fields_list)
        # Fonction permettant de passer par défaut l'id de l'OF ouvert
        if self.env.context.get('active_model') == 'mrp.simulation':
            mo = self.env['mrp.simulation'].browse(self.env.context.get('active_id')).mo_id
        else:
            mo = self.env['mrp.manufacturingorder'].browse(self.env.context.get('active_id'))
            
        res['mo_id'] = mo.id
        res['date'] = mo.max_end_date
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    date = fields.Datetime(string='Date', required=True)
    mo_id = fields.Many2one('mrp.manufacturingorder', string='Manufacturing Order', required=True, ondelete='cascade')
    is_procur_level_manufact = fields.Boolean(string='Procurement level', default=False)
    is_product_sublevel_manufact = fields.Boolean(string='Procurement Sublevel', default=False)
    is_procur_level_purchase = fields.Boolean(string='Procurement level', default=False)
    is_procur_sublevel_purchase = fields.Boolean(string='Procurement Sublevel', default=False)
    automatic_purchase = fields.Boolean(string='Generate Purchase', default=False)
    is_sublevel = fields.Boolean(string='Generate Full', default=False)
    change_resources = fields.Boolean(string='Load balancing', default=True)
    is_from_simulation = fields.Boolean(default=False)
    
    
    #===========================================================================
    # Boutons
    #===========================================================================
    @api.multi
    def button_plannification_mo_at_the_latest(self):
        """
            Bouton qui plannifie l'OF au plus tard
        """
        wo_obj = self.env['mrp.workorder']
        for wiz in self:
            date = wiz.date_plannif()
            wo_obj.plannification_mo_at_the_latest(date, 
                                                  wiz.mo_id, 
                                                  is_sublevel=wiz.is_sublevel, 
                                                  is_procur_level_manufact=wiz.is_procur_level_manufact,
                                                  is_product_sublevel_manufact=wiz.is_product_sublevel_manufact,
                                                  is_procur_level_purchase=wiz.is_procur_level_purchase,
                                                  automatic_purchase=wiz.automatic_purchase,
                                                  is_procur_sublevel_purchase=wiz.is_procur_sublevel_purchase, first_pass=True,
                                                  change_resources=wiz.change_resources, 
                                                  no_modif_prio_date=False)
        
        return True
    
    
    def date_plannif(self):
        """
            Point d'entrée pour brightloop car eux on choisie d'avoir un champ date et de passer comme heure 12:00
        """
        return self.date
        
        
    #===========================================================================
    # On Change
    #===========================================================================
    @api.onchange('is_procur_level_manufact')
    def _onchange_is_procur_level_manufact(self):
        if not self.is_procur_level_manufact:
            self.is_product_sublevel_manufact = False
            
    
    @api.onchange('is_product_sublevel_manufact')
    def _onchange_is_product_sublevel_manufact(self):
        if self.is_product_sublevel_manufact:
            self.is_procur_level_manufact = True
    
    
    @api.onchange('is_procur_level_purchase')
    def _onchange_is_procur_level_purchase(self):
        if not self.is_procur_level_purchase:
            self.is_procur_sublevel_purchase = False
            
    
    @api.onchange('is_procur_sublevel_purchase')
    def _onchange_is_procur_sublevel_purchase(self):
        if self.is_procur_sublevel_purchase:
            self.is_procur_level_purchase = True
            
            
            
class mrp_planning_mo_done(models.TransientModel):
    """ 
        ManufacturingOrder Planning Done
    """
    _name = 'mrp.planning.mo.done'
    _description = 'ManufacturingOrder Planning done'
    _rec_name = 'mo_id'
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(mrp_planning_mo_done, self).default_get(fields_list=fields_list)
        # Fonction permettant de passer par défaut l'id de l'OF ouvert
        if self.env.context.get('active_model') == 'mrp.simulation':
            mo = self.env['mrp.simulation'].browse(self.env.context.get('active_id')).mo_id
        else:
            mo = self.env['mrp.manufacturingorder'].browse(self.env.context.get('active_id'))
            
        res['mo_id'] = mo.id
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    mo_id = fields.Many2one('mrp.manufacturingorder', string='Manufacturing Order', required=True, ondelete='cascade')
    is_sublevel = fields.Boolean(string='Plannification Done Full', default=False)            
    automatic_purchase = fields.Boolean(string='Generate Purchase', default=True)

    
    #===========================================================================
    # Boutons
    #===========================================================================
    @api.multi
    def button_plannification_mo_done(self):
        """
            Bouton qui termine la plannification l'OF ou des OFs
        """
        for wiz in self:
            wiz.mo_id.plannification_mo_done(is_sublevel=wiz.is_sublevel, automatic_purchase=wiz.automatic_purchase)
            
        return True



class mrp_planning_wo_done(models.TransientModel):
    """ 
        WorkOrder Planning Done
    """
    _name = 'mrp.planning.wo.done'
    _description = 'WorkOrder Planning done'
    _rec_name = 'wo_id'
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(mrp_planning_wo_done, self).default_get(fields_list=fields_list)
        mo_obj = self.env['mrp.workorder']
        # Fonction permettant de passer par défaut l'id de l'OT ouvert
        mo = mo_obj.browse(self._context.get('active_id'))
        res['wo_id'] = mo.id
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wo_id = fields.Many2one('mrp.workorder', string='Workorder', required=True, ondelete='cascade')
    automatic_purchase = fields.Boolean(string='Generate Purchase', default=True)
    
    
    #===========================================================================
    # Boutons
    #===========================================================================
    @api.multi
    def button_plannification_wo_done(self):
        """
            Bouton qui termine la plannification l'OT
        """
        for wiz in self:
            wiz.wo_id.plannification_wo_done(wiz.automatic_purchase)
                
        return True
    
    
    