# -*- coding: utf-8 -*-

from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.addons.base_openprod.common import roundingUp
from decimal import Decimal

class AccountInvoiceLine(models.Model):
    _inherit = 'account.invoice.line'
    
    @api.multi
    def write(self, vals=None):
        modif_price = False
        if 'price_unit' in vals:
            modif_price = True
            price_unit = vals['price_unit']
        
        res = super(AccountInvoiceLine, self).write(vals=vals)
        regul_invoice_price = self.env['stock.config.settings'].get_param('regul_invoice_price')
        if regul_invoice_price and modif_price:
            uom_obj = self.env['product.uom']
            move_obj = self.env['stock.move']
            move_rcs = move_obj.search([('invoice_line_id', 'in', self.ids)])
            uoi_id = self.uoi_id.id
            for move in move_rcs.read(['uoi_id'], load='_classic_write'):
                factor = uom_obj._compute_qty(uoi_id, 1, move['uoi_id'])
                price_unit_move = factor and price_unit / factor or price_unit
                move_obj.browse(move['id']).write({'partner_price': price_unit_move})
            
        return res
    
    
