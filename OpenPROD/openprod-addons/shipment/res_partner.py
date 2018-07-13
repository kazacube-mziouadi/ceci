# -*- coding: utf-8 -*-
from openerp import models, api, fields

class res_partner(models.Model):
    _inherit = 'res.partner'
    #===========================================================================
    # COLUMNS
    #===========================================================================
    shipment_processing_id = fields.Many2one('edi.transformation.processing', string='Shipping advice', required=False, ondelete='restrict', help='EDI processing propagated in shipments and executed at the validation of it')
    carrier_processing_id = fields.Many2one('edi.transformation.processing', string='Carrier processing', required=False, ondelete='restrict', help='EDI processing propagated in shipments and executed upon sending it')