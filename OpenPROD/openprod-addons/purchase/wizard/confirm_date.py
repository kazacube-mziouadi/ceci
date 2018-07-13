# -*- coding: utf-8 -*-
from openerp import models, fields, api
import openerp.addons.decimal_precision as dp

class confirm_date_wizard(models.TransientModel):
    """ 
    Confirm sale delay
    """
    _inherit = 'confirm.date.wizard'
    _description = 'Confirm sale delay'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    pol_id = fields.Many2one('purchase.order.line', string='PoL', required=False, ondelete='cascade')
    
    @api.multi
    def confirm_date(self):
        res = super(confirm_date_wizard, self).confirm_date()
        this = self[0]
        if this.pol_id:
            this.pol_id.write({'need_delay_validation': False})
            proc_rs = self.env['procurement.order'].search([('pol_id', '=', this.pol_id.id)])
            if proc_rs:
                proc_rs.update_delay(this.date)
                
        return res
    