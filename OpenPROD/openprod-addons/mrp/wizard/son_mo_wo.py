# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
import time, datetime
import openerp.addons.decimal_precision as dp

class son_mo_wiz(models.TransientModel):
    """ 
        See MOs son of the MO
    """
    _name = 'son.mo.wiz'
    _description = 'See MOs son of the MO'
    _rec_name = 'mo_id'
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(son_mo_wiz, self).default_get(fields_list=fields_list)
        mo_obj = self.env['mrp.manufacturingorder']
        #Fonction permettant de passer par défaut l'id de l'OT ouvert
        mo = mo_obj.browse(self._context.get('active_id'))
        recursion_son_mo_wo = mo.recursion_son_mo_wo()
        mo_ids = recursion_son_mo_wo['mo_rcs'].ids or []
        vals = {
            'mo_id': mo.id,
            'mo_ids': mo_ids,
        }
        res.update(vals)
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    mo_id = fields.Many2one('mrp.manufacturingorder', string='MO', required=True, ondelete='cascade')
    mo_ids = fields.Many2many('mrp.manufacturingorder', 'son_mo_wiz_mrp_mo_rel', 'wiz_id', 'mo_id', string='Son MO')
    
    
    
    
    #===========================================================================
    # Boutons
    #===========================================================================
    @api.multi
    def action_cancel(self):
        for wiz in self:
            wiz.mo_ids.wkf_cancel()
    
        return True
    
    
    @api.multi
    def action_delete(self):
        self.action_cancel()
        for wiz in self:
            for mo in wiz.mo_ids:
                if mo:
                    try:
                        mo.state
                        delete = True
                    except:
                        delete = False
                    
                    if delete:
                        mo.unlink()
                
        return True
    
    

class son_wo_wiz(models.TransientModel):
    """ 
        See WOs son of the WO
    """
    _name = 'son.wo.wiz'
    _description = 'See WOs son of the WO'
    _rec_name = 'mo_id'
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(son_wo_wiz, self).default_get(fields_list=fields_list)
        mo_obj = self.env['mrp.manufacturingorder']
        #Fonction permettant de passer par défaut l'id de l'OT ouvert
        mo = mo_obj.browse(self._context.get('active_id'))
        recursion_son_mo_wo = mo.recursion_son_mo_wo()
        wo_ids = recursion_son_mo_wo['wo_rcs'].ids or []
        vals = {
            'mo_id': mo.id,
            'wo_ids': wo_ids,
        }
        res.update(vals)
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    mo_id = fields.Many2one('mrp.manufacturingorder', string='MO', required=True, ondelete='cascade')
    wo_ids = fields.Many2many('mrp.workorder', 'son_wo_wiz_mrp_wo_rel', 'wiz_id', 'wo_id', string='Son WO')

    
    #===========================================================================
    # Boutons
    #===========================================================================
    @api.multi
    def action_cancel(self):
        for wiz in self:
            wiz.wo_ids.wkf_cancel()
    
        return True
    
    
    @api.multi
    def action_delete(self):
        self.action_cancel()
        for wiz in self:
            for wo in wiz.wo_ids:
                if wo:
                    try:
                        wo.state
                        delete = True
                    except:
                        delete = False
                    
                    if delete:
                        wo.unlink()
                
        return True
        