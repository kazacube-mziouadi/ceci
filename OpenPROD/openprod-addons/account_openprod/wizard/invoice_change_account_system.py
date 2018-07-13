# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.addons.base_openprod.common import get_form_view

class invoice_change_account_system(models.TransientModel):
    """ 
        Wizard to change the account system
    """
    _name = 'invoice.change.account.system'
    _description = 'Modification of the account system'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    invoice_id = fields.Many2one('account.invoice', string='Invoice', required=False, ondelete='set null')
    invoice_account_system_id = fields.Many2one('account.fiscal.position', string='Account system', required=True, ondelete='set null')
    
    @api.model
    def default_get(self, fields_list):
        res = super(invoice_change_account_system, self).default_get(fields_list=fields_list)
        invoice_id = self.env.context.get('active_id')
        if invoice_id and self.env.context.get('active_model') == 'account.invoice':
            invoice = self.env['account.invoice'].browse(invoice_id)
            if invoice:
                res = {
                       'invoice_id': invoice.id,
                       'invoice_account_system_id': invoice.fiscal_position_id.id,
                       }
                
        return res
    
    
    @api.multi
    def invoice_change_account_system(self):
        """
            Fonction permettant de modifier la position fiscale d'une facture
            et de recalculer les taxes
        """
        invoice = self.invoice_id
        if invoice and invoice.state == 'draft':
            invoice.write({'fiscal_position_id': self.invoice_account_system_id.id})
            if invoice.type in ['out_invoice', 'out_refund']:
                tax_field = 'sale_taxes_ids'
            else:
                tax_field = 'purchase_taxes_ids'
                
            for invoice_line in invoice.invoice_line_ids:
                invoice_line.invoice_line_tax_ids =  self.invoice_account_system_id.map_tax(invoice_line.product_id[tax_field])
            
            invoice._onchange_invoice_line_ids()
            
        return {'type':'ir.actions.act_window_view_reload'}