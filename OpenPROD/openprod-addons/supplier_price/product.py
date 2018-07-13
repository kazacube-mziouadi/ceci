# coding: utf-8
from openerp import models, api, fields, _
    
        
        
class pricelist_supplierinfo(models.Model):
    """
    pricelist supplierinfo
    """
    _inherit = 'pricelist.supplierinfo'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    supp_product_code = fields.Char(related='sinfo_id.supp_product_code', string='Supplier product code')
    supp_product_name = fields.Char(related='sinfo_id.supp_product_name', string='Supplier product name')
    
        
        
class product_supplierinfo(models.Model):
    """
    Product supplierinfo
    """
    _inherit = 'product.supplierinfo'

    
    @api.multi
    def name_get(self):
        result = []
        for supplierinfo in self:
            result.append((supplierinfo.id, '[%s] - %s - [%s] - %s'%(supplierinfo.product_id.code, supplierinfo.product_id.name, supplierinfo.partner_id.reference, supplierinfo.partner_id.name)))
             
        return result