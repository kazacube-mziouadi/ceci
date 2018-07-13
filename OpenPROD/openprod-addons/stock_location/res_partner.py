# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.translate import _

class res_partner(models.Model):
    _inherit = 'res.partner'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    # Onglet administration
    customer_location_id = fields.Many2one('stock.location', string='Customer location', required=False, ondelete='restrict',
                                           help='This stock location will be used instead of the default location for the goods'
                                           'sent to this customer')
    supplier_location_id = fields.Many2one('stock.location', string='Supplier location', required=False, ondelete='restrict',
                                           help='This stock location will be used instead of the default location for the goods'
                                           'received from this supplier')
    company_id = fields.Many2one('res.company', string='Company', required=False, ondelete='restrict')
