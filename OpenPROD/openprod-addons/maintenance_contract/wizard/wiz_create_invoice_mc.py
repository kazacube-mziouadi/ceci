# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp.exceptions import except_orm, ValidationError, Warning

class wiz_create_invoice_mc(models.TransientModel):
    """ 
        Wiz create invoice mc
    """
    _name = 'wiz.create.invoice.mc'
    _description = 'Wiz create invoice mc'
    _rec_name = 'maintenance_contract_id'
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(wiz_create_invoice_mc, self).default_get(fields_list=fields_list)
        res['maintenance_contract_id'] = self._context.get('active_id')
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    maintenance_contract_id = fields.Many2one('maintenance.contract', string='Maintenance contract', required=False, ondelete='cascade')
    end_date = fields.Date(string='Limit create end date', required=True, default=lambda self: fields.Date.today())
    
    
    #===========================================================================
    # Bouton
    #===========================================================================
    @api.multi
    def action_validation(self):
        """
            Bouton de validation
        """
        for wiz in self:
            if wiz.maintenance_contract_id:
                create_invoice = False
                create_invoice_int = False
                
                if wiz.maintenance_contract_id.last_date_invoice:
                    first_create = False
                    next_date = wiz.maintenance_contract_id.last_date_invoice 
                else:
                    next_date = fields.Date.today()
                    first_create = True
                    
                while (next_date < wiz.end_date) or next_date == False:
                    if first_create:
                        first_create = False
                        create_invoice_int = wiz.maintenance_contract_id.button_generate_invoice_mc(date_now=next_date, last_date=False, no_frequency=True)
                        if create_invoice_int:
                            create_invoice = True

                    if wiz.maintenance_contract_id.frequency_type == 'quarter':
                        frequency = wiz.maintenance_contract_id.frequency*3
                        next_date = fields.Date.to_string(fields.Date.from_string(next_date) + wiz.maintenance_contract_id(months=frequency))
                    elif wiz.maintenance_contract_id.frequency_type == 'day':
                        next_date = fields.Date.to_string(fields.Date.from_string(next_date) + 
                                                                                  timedelta(days=wiz.maintenance_contract_id.frequency))
                    elif wiz.maintenance_contract_id.frequency_type == 'week':
                        frequency = wiz.maintenance_contract_id.frequency*7
                        next_date = fields.Date.to_string(fields.Date.from_string(next_date) + timedelta(days=frequency))
                    elif wiz.maintenance_contract_id.frequency_type == 'month':
                        next_date = fields.Date.to_string(fields.Date.from_string(next_date) + 
                                                                                  relativedelta(months=wiz.maintenance_contract_id.frequency))
                    elif wiz.maintenance_contract_id.frequency_type == 'year':
                        next_date = fields.Date.to_string(fields.Date.from_string(next_date) + 
                                                                                  relativedelta(years=wiz.maintenance_contract_id.frequency))

                    if next_date <= wiz.end_date:
                        create_invoice_int = wiz.maintenance_contract_id.button_generate_invoice_mc(date_now=next_date, last_date=False, no_frequency=True)
                        if create_invoice_int:
                            create_invoice = True
                        
                if not create_invoice:
                    raise except_orm(_('Error'), _('No create invoice, please check the consistency between the time and frequency.'))
                
        return {'type': 'ir.actions.act_window_close'}



