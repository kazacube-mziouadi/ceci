# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
import time, datetime
import openerp.addons.decimal_precision as dp

class wo_change_mo_qty(models.TransientModel):
    """ 
        Changer la quantité du produit de facturation dans un OT
    """
    _name = 'wo.change.mo.qty'
    _description = 'WO Change mo qty'
    
    @api.model
    def default_get(self, fields_list):
        res = super(wo_change_mo_qty, self).default_get(fields_list=fields_list)
        wo_obj = self.env['mrp.workorder']
        # Fonction permettant de passer par défaut l'id de l'OT ouvert
        if self._context.get('mo_change_qty', False):
            wo = wo_obj.search([('mo_id', '=', self._context.get('active_id'))], order='sequence asc', limit=1)
            if not wo:
                raise except_orm('Error', 'There is not WO')
            
            vals = {
                'wo_id': wo.id,
                'old_qty': wo.quantity,
                'new_qty': wo.quantity,
                'factor': 1,
                'spread': True,
                'is_mo': True
            }
        else:
            wo = wo_obj.browse(self._context.get('active_id'))
            vals = {
                'wo_id': wo.id,
                'old_qty': wo.quantity,
                'new_qty': wo.quantity,
                'factor': 1
            }
        
        res.update(vals)
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    @api.one
    def _compute_old_qty(self):
        """
            Fonction qui récupère le produit et l'UdM dans l'OT
        """
        self._compute_old_qty = self.wo_id and self.wo_id.quantity or False
        
        
    wo_id = fields.Many2one('mrp.workorder', string='Workorder', required=False, ondelete='cascade')
    old_qty = fields.Float(string='Old Quantity', digits=dp.get_precision('Product quantity'), compute='_compute_old_qty')
    new_qty = fields.Float(string='New Quantity', default=0.0, digits=dp.get_precision('Product quantity'), required=True)
    factor = fields.Float(string='Factor', default=0.0, digits=dp.get_precision('Product quantity'), required=True)
    spread = fields.Boolean(string='Spread', default=False, help='If field is checked, all next WO will change quantity')
    is_mo = fields.Boolean(string='MO', default=False)
    
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('factor')
    def onchange_factor(self):
        self.new_qty = self.old_qty * self.factor

    
    @api.onchange('new_qty')
    def onchange_new_qty(self):
        self.factor = self.old_qty and self.new_qty / self.old_qty or 0.0

    
    #===========================================================================
    # Bouton
    #===========================================================================
    @api.multi
    def action_validation(self):
        """
            Bouton de validation
        """
        for wiz in self:
            if wiz.wo_id.state not in ('draft', 'waiting', 'ready','plan'):
                raise except_orm('Error', _("The Work order state must be Draft or Waiting or Ready"))
            
            wiz.change_qty()
            
        return True

    
    def change_qty(self):
        """
            Fonction qui change la qty
        """
        if not self.factor or not self.wo_id.quantity:
            raise except_orm('Error', "You cannot change Work order quantity with factor of 0")
        
        self.wo_id.change_qty(self.new_qty / self.wo_id.quantity, self.spread)
        return True

    