# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError

class procurement_choose_partner(models.TransientModel):
    """ 
        Replacement confirmed date for purchase line
    """
    _name = 'procurement.choose.partner'
    _description = 'Choose partner'
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(procurement_choose_partner, self).default_get(fields_list=fields_list)
        if self.env.context.get('active_model', '') == 'procurement.order' and self.env.context.get('active_id', False):
            proc = self.env['procurement.order'].browse(self.env.context.get('active_id'))
            res['procurement_id'] = proc.id
            res['product_id'] = proc.product_id.id
            
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    procurement_id = fields.Many2one('procurement.order', string='Procurement', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Partner', required=True, ondelete='cascade')


    @api.multi
    def create_po(self):
        partner = self.partner_id
        for this in self:
            this.procurement_id.create_po(partner=partner)
         
        return True
    
