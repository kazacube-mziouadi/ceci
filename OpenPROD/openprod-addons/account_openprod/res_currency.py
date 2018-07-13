# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import UserError
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime, timedelta

# Remettre le fichier dans les dépendances


class res_currency_rate(models.Model):
    _inherit = 'res.currency.rate'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Datetime(default=lambda *a: (datetime.now() + timedelta(minutes=5)).strftime(DEFAULT_SERVER_DATETIME_FORMAT))
    
    
    @api.onchange('name')
    def _onchange_name(self):
        if self.name and self.name < fields.Datetime.now():
            self['name'] = False
            return {'warning': {'title': 'User error', 'message': _('You can\'t program a date lower than now')}}
    
    
    @api.model
    def create(self, vals):
        if vals['name'] < fields.Datetime.now():
            raise UserError(_('You can\'t program a date lower than now'))
        
        return super(res_currency_rate, self).create(vals)