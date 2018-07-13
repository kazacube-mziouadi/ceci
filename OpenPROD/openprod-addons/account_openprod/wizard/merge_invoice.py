# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.exceptions import except_orm
from openerp.tools.translate import _

class merge_invoice(models.TransientModel):
    """ 
        Merge invoices 
    """
    _name = 'merge.invoice'
    _description = 'Merge invoices'
    
    @api.multi
    def merge(self):
        """
            Merge de factures
        """
        invoice_obj = self.env['account.invoice']
        context = self.env.context
        invoice_nb = 0
        if context.get("active_ids"):
            for invoice in invoice_obj.browse(context['active_ids']):
                invoice_nb += 1
                if invoice.state != 'draft':
                    raise except_orm(_("Error"), _('You can\'t merge a non-draft invoice (%s)!')%(invoice.number or invoice.id))
                
            if invoice_nb <= 1:
                raise except_orm(_("Error"), _('You need more than one invoice to make a merge!'))
            
            return invoice_obj.browse(context['active_ids']).do_merge()
        else:
            return True
        

