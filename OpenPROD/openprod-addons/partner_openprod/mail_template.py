# -*- coding: utf-8 -*-

from openerp import models, fields, api, _

class MailTemplate(models.Model):
    _inherit = 'mail.template'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    @api.model
    def _edi_select_get(self):
        return [
                ('ar', _('Envoie AR')),
                ('confirmation', _('Confirmation')),
                ('quotation', _('Quotation')), 
                ('reminder', _('Reminder')),
                ('mass_partner', _('Mass partner')), 
                       ]
    
    edi_select = fields.Selection('_edi_select_get', string='Edi select')        
        