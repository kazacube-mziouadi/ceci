# -*- coding: utf-8 -*-
from openerp import models, api, fields
import time

class data_insert(models.Model):
    """
    Data insert
    """
    _name = 'data.insert'
    _description = 'Data insert'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    model = fields.Char(required=True)
    field = fields.Char(required=False, default='name')
    nb = fields.Integer(string='Nb of iterations', default=1, required=True)
    record_id = fields.Integer(string='Record to copy', default=0, required=True)
    
    @api.one
    def go(self):
        i = 0
        if self.field:
            change_def = self.field
        else:
            change_def = False
            
        product_rs = self.env[self.model].browse(self.record_id)
        while i < self.nb:
            if change_def:
                product_rs.copy({change_def: '%s %d'%(product_rs[change_def], i)})
            else:
                product_rs.copy()
                
            i += 1
            
        return True
    
class data_test(models.Model):
    """
    Data test
    """
    _name = 'data.test'
    _description = 'Data test'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True)
    model = fields.Char(required=True)
    method = fields.Char(required=True)
    nb = fields.Integer(string='Nb of iterations', default=1, required=True)

    @api.one
    def go(self):
        s = time.time()
        print 'START %s'%(self.method)
        for i in range(self.nb):
            s1 = time.time()
            getattr(self.env[self.model], self.method)()
            print 'Iteration %d: %s'%(i, time.time() - s1)
        
        
        print 'ALL: %s'%(time.time() - s)
        print 'END %s'%(self.method)
        return True
    
    def test_filtred(self):
        for cinfo in self.env['product.customerinfo'].search([]):
            print cinfo.pricelist_ids.filtered(lambda x: x.min_qty > 20)
            
        return True
    
    def test_filtred2(self):
        for cinfo in self.env['product.customerinfo'].search([]):
            print self.env['pricelist.customerinfo'].search([('cinfo_id', '=', cinfo.id), ('min_qty', '>', 20)])
            
        return True