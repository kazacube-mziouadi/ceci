# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
from decimal import Decimal

class quick_creation_mo(models.TransientModel):
    """ 
        Wizard quick creation of MO
    """
    _inherit = 'quick.creation.mo'
    _description = 'Wizard quick creation of MO'
    
    
    intervention_id = fields.Many2one('intervention', string='Intervention', required=False, ondelete='cascade')
    

    @api.model
    def default_get(self, fields_list):
        res = super(quick_creation_mo, self).default_get(fields_list=fields_list)
        vals = {}
        component = False
        #Si on est dans une intervention
        if self._context.get('active_model') == 'intervention':
            interv = self.env['intervention'].browse(self._context.get('active_id'))
            vals_interv = {'product_id': interv.park_id.product_id.id,
                           'qty': interv.park_id.num_serie_id.uom_qty,
                           'uom_id': interv.park_id.product_id.uom_id.id,
                           'requested_date': interv.start_date_requested,
                           'warehouse_id': interv.warehouse_id.id,
                           'label_rm_ids': [(4, interv.park_id.num_serie_id.id)],
                           'label_fp_ids': [(4, interv.park_id.num_serie_id.id)]}
            
            vals.update(vals_interv)
            vals['intervention_id'] = interv.id
            
        res.update(vals)
        return res
    
    
    def function_entry_point(self, mo):
        self.intervention_id.write({'mo_ids': [(4, mo.id)]})
        return True