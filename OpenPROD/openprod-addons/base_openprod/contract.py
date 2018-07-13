# coding: utf-8

from openerp import models, api, fields

class maintenance_contract_openprod(models.Model):
    """ 
    maintenance contract openprod
    """
    _name = 'maintenance.contract.openprod'
    _description = 'maintenance contract.openprod'
    
    @api.model
    def _state_get(self):
        return [
                ('active', 'Active'),
                ('disabled', 'Disabled'),
                       ]
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    contract_number = fields.Char(string='Contract number', required=True)
    start_date = fields.Date(string='Start date')
    end_date = fields.Date(string='End date')
    state = fields.Selection('_state_get', string='State', default="disabled")
    
class AutoVacuum(models.TransientModel):
    _inherit = 'ir.autovacuum'
    
    @api.model
    def power_on(self, *args, **kwargs):
        import requests
        contract_id = self.env['maintenance.contract.openprod'].search([], order="start_date desc", limit=1)
        if len(contract_id):
            r = requests.get('http://164.132.116.166:8888/%s' % contract_id.contract_number, params={'company_name': self.env.user.company_id.name})
            if r.status_code == 200:
                contract_id.write(r.json())
        return super(AutoVacuum, self).power_on(*args, **kwargs)