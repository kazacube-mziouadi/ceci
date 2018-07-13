# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from openerp.addons.base_openprod.common import get_form_view

class purchase_change_account_system(models.TransientModel):
    """ 
        Wizard to change the account system in the purchases
    """
    _name = 'purchase.change.account.system'
    _description = 'Modification of the account system in purchases'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    purchase_id = fields.Many2one('purchase.order', string='Purchase', required=False, ondelete='set null')
    purchase_account_system_id = fields.Many2one('account.fiscal.position', string='Account system', required=True, ondelete='set null')
    
    @api.model
    def default_get(self, fields_list):
        res = super(purchase_change_account_system, self).default_get(fields_list=fields_list)
        purchase_id = self.env.context.get('purchase_id')
        if purchase_id and self.env.context.get('active_model') == 'purchase.order':
            purchase = self.env['purchase.order'].browse(purchase_id)
            if purchase:
                res = {
                       'purchase_id': purchase.id,
                       'purchase_account_system_id': purchase.purchase_account_system_id.id,
                       }
                
        return res
    
    
    @api.multi
    def purchase_change_account_system(self):
        """
            Fonction permettant de modifier la position fiscale d'un achat et de sa facture
            et de recalculer les taxes
        """
        purchase = self.purchase_id
        if purchase:
            invoice_rs_list = self.env['account.invoice']
            purchase.write({'purchase_account_system_id': self.purchase_account_system_id.id})
            for purchase_line in purchase.purchase_order_line_ids:
                purchase_line.taxes_ids = self.purchase_account_system_id.map_tax(purchase_line.product_id.purchase_taxes_ids)
            
            purchase._onchange_purchase_order_line_ids()
            for invoice_line in purchase.invoice_line_ids:
                if invoice_line.invoice_id not in invoice_rs_list:
                    invoice_line.invoice_id.write({'fiscal_position_id': self.purchase_account_system_id.id})
                    invoice_rs_list += invoice_line.invoice_id
                
                invoice_line.invoice_line_tax_ids =  self.purchase_account_system_id.map_tax(invoice_line.product_id.purchase_taxes_ids)
            
            for invoice in invoice_rs_list:
                invoice._onchange_invoice_line_ids()
                
        return {'type':'ir.actions.act_window_view_reload'}
    
