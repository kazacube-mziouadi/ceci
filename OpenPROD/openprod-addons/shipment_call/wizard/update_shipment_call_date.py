# -*- coding: utf-8 -*-
from openerp import models, api, fields

class update_shipment_call_date_wizard(models.TransientModel):
    """ 
    Update shipment call date 
    """
    _name = 'update.shipment.call.date.wizard'
    _description = 'Update shipment call date'
    _rec_name = 'shipment_call_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    shipment_call_id = fields.Many2one('shipment.call', string='Request for removal', required=True, ondelete='cascade')
    date = fields.Datetime(string='New date')

    
    @api.multi
    def change_date(self):
        for wizard_rc in self:
            if wizard_rc.shipment_call_id:
                wizard_rc.shipment_call_id.write({'real_departure_date': wizard_rc.date})
                wizard_rc.shipment_call_id.wkf_validated()
        
        return {'type': 'ir.actions.act_window_close'}

    
    @api.model
    def default_get(self, fields_list):
        res = super(update_shipment_call_date_wizard, self).default_get(fields_list)
        res['shipment_call_id'] = self.env.context.get('active_id', False)
        shipment_call_rc = self.env['shipment.call'].browse(res['shipment_call_id'])
        res['date'] = shipment_call_rc.forecast_arrival_date
        return res
    

