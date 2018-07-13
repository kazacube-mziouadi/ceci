# -*- coding: utf-8 -*-

from openerp import models, api, fields, tools, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm


class quality_control_line_result_report(models.Model):
    """ 
        Quality Control Declaration Lines Result
    """
    _inherit = 'quality.control.line.result.report'
    _description = 'Quality Control Declaration Lines Result'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wo_id = fields.Many2one('mrp.workorder', string='WO', readonly=True)
    wo_produce_id = fields.Many2one('mrp.wo.produce', string='Production declaration', readonly=False)


    def init(self, cr):
        tools.drop_view_if_exists(cr, self._table)
        cr.execute("""
            create or replace view quality_control_line_result_report as (
            SELECT id,
                   control_id,
                   product_id, 
                   wo_id, 
                   wo_produce_id, 
                   picking_id, 
                   min, 
                   max, 
                   value_target, 
                   user_id,
                   result,
                   date
              FROM quality_control_declaration_line_result
              where type_control='numeric') """)
                
                
    
    
    
    
    
    
    
    
    