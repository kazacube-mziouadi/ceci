# -*- coding: utf-8 -*-

from openerp import models, api, _

class MailTemplate(models.Model):
    _inherit = 'mail.template'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    @api.model
    def _edi_select_get(self):
        res = super(MailTemplate, self)._edi_select_get()
        if not res:
            res = []
            
        res.extend([
            ('shipment_carrier', _('Shipment carrier'))
        ])
        return res