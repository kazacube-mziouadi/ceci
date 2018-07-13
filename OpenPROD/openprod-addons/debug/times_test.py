# -*- coding: utf-8 -*-
from openerp import models, api, fields
import time

class times_test(models.Model):
    """
    Times test
    """
    _name = 'times.test'
    _description = 'Times test'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    model = fields.Char(required=True)
    function = fields.Char(required=False, default='name')
    res_ids = fields.Char(size=2048, string='Ids', default='[]')
    args = fields.Text(default = '()')
    result = fields.Text(readonly=True)
    time = fields.Char(size=128, readonly=True)
    
    @api.onchange('model')
    def onchange_model(self):
        if not self.name and self.model:
            self.name = self.model
    
    @api.one
    def go(self):
        start = time.time()
        s = self.env[self.model].search([('id', 'in', eval(self.res_ids))])
        str_call = 'getattr(s, self.function)%s'%(str(tuple([e for e in eval(self.args)])))
        res = eval(str_call)
        self.write({'time': time.time() - start, 'result': str(res)})

        return True