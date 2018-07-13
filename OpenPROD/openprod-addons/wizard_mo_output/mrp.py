# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError



class mrp_reservation(models.Model):
    """ 
    MRP reservation 
    """
    _name = 'mrp.reservation'
    _description = 'Mrp reservation'
    _rec_name = 'product_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wo_id = fields.Many2one('mrp.workorder', string='WO', required=False, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='cascade')
    move_id = fields.Many2one('stock.move', string='Move', required=False, ondelete='cascade')
    uom_id = fields.Many2one('product.uom', string='UoM', required=False, ondelete='cascade')
    qty = fields.Float(string='Qty', default=0.0, required=False)
    qty_taken_stock = fields.Float(string='Qty taken stock', default=0.0, required=False)
    user_id = fields.Many2one('res.users', string='User', required=False, ondelete='cascade')
    date = fields.Date(string='Date')
    label_ids = fields.Many2many('stock.label', 'mrp_reservation_stock_label_rel', 'wizard_id', 'label_id', string='Label')
    qty_mo = fields.Float(string='Qty MO', default=0.0, required=False)

    
    #===========================================================================
    # Boutons
    #===========================================================================
    @api.multi
    def wkf_unlink(self):
        self.unlink()
        
        return {'type': 'ir.actions.act_window_view_reload'}
            
        

class mrp_workorder(models.Model):
    _inherit = 'mrp.workorder'

    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    reservation_ids = fields.One2many('mrp.reservation', 'wo_id',  string='Reservations')
    
    
    #===========================================================================
    # Boutons
    #===========================================================================
    @api.multi
    def wkf_ready(self, no_recursion_fct=False):
        res = super(mrp_workorder, self).wkf_ready(no_recursion_fct=no_recursion_fct)
        for wo in self:
            if wo.rm_draft_ids and not wo.reservation_ids:
                raise except_orm(_('Error'), _('It is necessary to first make the output of the materials.'))
        
        return res
    
    
    