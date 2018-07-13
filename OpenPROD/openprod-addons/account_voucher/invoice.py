# -*- coding: utf-8 -*-


from openerp.osv import osv
from openerp.tools.translate import _

class invoice(osv.osv):
    _inherit = 'account.invoice'

    def invoice_pay_customer(self, cr, uid, ids, context=None):
        if not ids: return []
        dummy, view_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account_voucher', 'view_vendor_receipt_dialog_form')

        inv = self.browse(cr, uid, ids[0], context=context)
        if inv.type in ('out_invoice','out_refund'):
            account_partner_id = inv.partner_id.property_account_receivable_id and inv.partner_id.property_account_receivable_id.id or False
        else:
            account_partner_id = inv.partner_id.property_account_payable_id and inv.partner_id.property_account_payable_id.id or False
            
        return {
            'name':_("Pay Invoice"),
            'view_mode': 'form',
            'view_id': view_id,
            'view_type': 'form',
            'res_model': 'account.voucher',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'new',
            'domain': '[]',
            'context': {
                'payment_expected_currency': inv.currency_id.id,
                'default_partner_id': inv.partner_id.id,
                'default_account_partner_id': account_partner_id,
                'default_amount': inv.type in ('out_refund', 'in_refund') and -inv.residual or inv.residual,
                'default_reference': inv.name,
                'close_after_process': True,
                'invoice_type': inv.type,
                'invoice_id': inv.id,
                'default_type': inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment',
                'type': inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment'
            }
        }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
