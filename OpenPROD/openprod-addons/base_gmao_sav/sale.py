# -*- coding: utf-8 -*-
from openerp import models, fields, api, _



class sale_order_line(models.Model):
    """ 
    Sale module 
    """
    _inherit = 'sale.order.line'
    #===========================================================================
    # COLUMNS
    #===========================================================================
    intervention_id = fields.Many2one('intervention', string='Intervention', required=False, ondelete='restrict')
    
    
    
class sale_order(models.Model):
    """ 
    Sale module 
    """
    _inherit = 'sale.order'    
    
    
    @api.model
    def _type_get(self):
        res = super(sale_order, self)._type_get()
        res.append(('sav', _('SAV')))
        return res
    
    
    def more_other_data_invoice(self):
        res = super(sale_order, self).more_other_data_invoice()
        if self.type == 'sav':
            line_rc = self.env['sale.order.line'].search([('sale_order_id', '=', self.id), ('intervention_id', '!=', False)], limit=1)
            if line_rc:
                res['intervention_id'] = line_rc.intervention_id.id
            
        return res