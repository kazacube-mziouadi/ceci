# -*- coding: utf-8 -*-
from openerp import models, api

class workflow(models.Model):
    _inherit = 'workflow'
    
    
    @api.multi
    def reinitialise_all_records(self):
        for wkf_rc in self:
            rcs = self.env[wkf_rc.osv].search([])
            if rcs:
                self.env.cr.execute('UPDATE %s SET wkf_id = %s'%(rcs._table, wkf_rc.id))
                for rc in rcs:
                    rc.reset_workflow()