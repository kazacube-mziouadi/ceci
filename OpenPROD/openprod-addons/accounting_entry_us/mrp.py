# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp



class mrp_manufacturingorder(models.Model):
    _inherit = 'mrp.manufacturingorder'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    account_move_line_ids = fields.One2many('account.move.line', 'mo_id',  string='Account move line')
    real_rm_cost_aml = fields.Float(string='Material first cost account move line', default=0.0, digits=dp.get_precision('Product price'))

    
    
    @api.multi    
    def button_compute_real_costs(self):
        res = super(mrp_manufacturingorder, self).button_compute_real_costs()
        for mo in self:
            self.env.cr.execute("""
                    select 
                        sum(debit)
                    
                    from 
                        account_move_line
                    where 
                        mo_id = %s and
                        is_wo_rm = true
            """, (mo.id,))
            res_value_sql = self.env.cr.dictfetchall()
            real_rm_cost_aml = res_value_sql and res_value_sql[0]['sum'] or 0
            mo.write({'real_rm_cost_aml': real_rm_cost_aml,})
            
        return res