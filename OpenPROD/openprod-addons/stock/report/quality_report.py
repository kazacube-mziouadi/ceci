# -*- coding: utf-8 -*-

from openerp import models, api, fields, tools, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm


class quality_control_line_result_report(models.Model):
    """ 
        Quality Control Declaration Lines Result
    """
    _name = 'quality.control.line.result.report'
    _description = 'Quality Control Declaration Lines Result'
    _auto = False
    _rec_name = 'control_id'
    
    
    @api.model
    def _result_get(self):
        return [
                ('ok', _('OK')),
                ('quarantine', _('Quarantine')),
                ('hs', _('HS')),
                       ]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    control_id = fields.Many2one('quality.control', string='Control', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    picking_id = fields.Many2one('stock.picking', string='Picking', readonly=True)
    min = fields.Float(string='Min', readonly=True, group_operator="avg")
    max = fields.Float(string='Max', readonly=True, group_operator="avg")
    value_target = fields.Float(string='Value Target', readonly=True, group_operator="avg")
    result = fields.Selection('_result_get', string='Result', readonly=True)
    user_id = fields.Many2one('res.users', string='User', readonly=True)
    #Date
    date = fields.Datetime(string='Create date', readonly=True)


    def init(self, cr):
        tools.drop_view_if_exists(cr, self._table)
        cr.execute("""
            create or replace view quality_control_line_result_report as (
            SELECT id,
                   control_id,
                   product_id, 
                   picking_id, 
                   min, 
                   max, 
                   value_target, 
                   user_id,
                   result,
                   date
              FROM quality_control_declaration_line_result
              where type_control='numeric') """)
                
                
    def unlink(self, cr, uid, ids, context={}):
        raise except_orm(_('Error !'), _('You cannot delete any record!'))
    
    
    
    
    
    
    
    
    
    
    