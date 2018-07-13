# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.exceptions import except_orm
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError


class pay_more_invoice_wiz(models.TransientModel):
    """ 
        Pay more invoices
    """
    _name = 'pay.more.invoice.wiz'
    _description = 'Pay more invoices'

    
    @api.model
    def default_get(self, fields_list):
        """
            Par défaut on prend l'année en cours
        """
        res = super(pay_more_invoice_wiz, self).default_get(fields_list=fields_list)
        invoice_ids = [(4, id) for id in self.env.context.get('active_ids', [])]
        res['invoice_ids'] = invoice_ids
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='string', size=32, required=False)
    invoice_ids = fields.Many2many(
        'account.invoice', 'pay_more_invoice_account_invoice_rel',
        'wizard_id', 'invoice_id', 'Invoice')
    
    
    
    @api.multi
    def validate(self):
        for wiz in self:
            paid_by_id = False
            inv_type = False
            for inv in wiz.invoice_ids:
                if not inv_type:
                    inv_type = inv.type
                
                if not paid_by_id:
                    paid_by_id = inv.paid_by_id.id
                    
                if inv_type != inv.type:
                    raise except_orm(_('Error'), _('The type must be the same.'))
                
                if paid_by_id != inv.paid_by_id.id:
                    raise except_orm(_('Error'), _('The pay by must be the same.'))
                
                if inv.state != 'open':
                    raise except_orm(_('Error'), _('The invoices must be in the open state.'))
                
            return wiz.invoice_ids.pay_more_invoice()