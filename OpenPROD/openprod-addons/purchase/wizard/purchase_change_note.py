# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _

class purchase_change_note(models.TransientModel):
    """ 
        Wizard to change the note in the purchases
    """
    _name = 'purchase.change.note'
    _description = 'Modification of the note in the purchases'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    purchase_id = fields.Many2one('purchase.order', string='Purchase', required=False, ondelete='set null')
    supplier_note = fields.Html(string='Supplier note')
    delivery_note = fields.Html(string='Delivery note')
    invoice_note = fields.Html(string='Invoice note')
    inter_note = fields.Text(string='Internal note')
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(purchase_change_note, self).default_get(fields_list=fields_list)
        purchase_id = self.env.context.get('purchase_id')
        if purchase_id and self.env.context.get('active_model') == 'purchase.order':
            purchase = self.env['purchase.order'].browse(purchase_id)
            if purchase:
                res = {
                       'purchase_id': purchase_id,
                       'inter_note': purchase.inter_note,
                       'delivery_note': purchase.delivery_note,
                       'invoice_note': purchase.invoice_note,
                       'supplier_note': purchase.supplier_note,
                       }
                
        return res
    
    
    @api.multi
    def change_note(self):
        """
            Fonction permettant de modifier les notes d'un achat
        """
        for wiz in self:
            purchase = wiz.purchase_id
            if purchase:
                invoice_list = self.env['account.invoice']
                purchase.write({
                            'inter_note': wiz.inter_note,
                            'delivery_note': wiz.delivery_note,
                            'invoice_note': wiz.invoice_note,
                            'supplier_note': wiz.supplier_note,
                            })
                for invoice_line in purchase.invoice_line_ids:
                    if not invoice_line.invoice_id in invoice_list:
                        invoice_list += invoice_line.invoice_id
    
                invoice_list.write({
                                  'note_invoice_header': wiz.invoice_note,
                                  'note_invoice_intern': wiz.inter_note,
                                  })
                picking_rs = purchase.picking_ids
                picking_rs.write({
                                  'internal_note': wiz.inter_note,
                                  'printed_note': wiz.delivery_note,
                                  })
                
        return {'type':'ir.actions.act_window_view_reload'}
    
    
    