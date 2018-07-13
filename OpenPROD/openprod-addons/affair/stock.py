# -*- coding: utf-8 -*-
from openerp import models, api, fields


class procurement_order(models.Model):
    _inherit = 'procurement.order'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    affair_id = fields.Many2one('affair', string='Affair', required=False, ondelete='restrict')
    

    def create_mo_update_other_wo_data(self):
        res = super(procurement_order, self).create_mo_update_other_wo_data()
        if self.affair_id:
            res['affair_id'] = self.affair_id.id
            
        return res

    
    def create_wo_update_other_wo_data(self):
        res = super(procurement_order, self).create_wo_update_other_wo_data()
        if self.affair_id:
            res['affair_id'] = self.affair_id.id
            
        return res
    
    
    def create_po_update_pol_datas(self):
        res = super(procurement_order, self).create_po_update_pol_datas()
        if self.affair_id:
            res['affair_id'] = self.affair_id.id
            
        return res



class stock_move(models.Model):
    _inherit = 'stock.move'
        
    def update_procurement_vals(self):
        res = super(stock_move, self).update_procurement_vals()
        if self.wo_incoming_id.affair_id:
            res['affair_id'] = self.wo_incoming_id.affair_id.id
        elif self.sale_line_id.affair_id:
            res['affair_id'] = self.sale_line_id.affair_id.id
            
        return res