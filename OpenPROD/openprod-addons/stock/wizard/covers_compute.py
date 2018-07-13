# -*- coding: utf-8 -*-
from openerp import models, api, fields, _
from openerp.exceptions import except_orm


class covers_compute_wizard(models.TransientModel):
    """ 
    Covers compute wizard 
    """
    _name = 'covers.compute.wizard'
    _description = 'Covers compute wizard'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    product_ids = fields.Many2many('product.product', 'covers_wizard_id', 'product_id', string='Products', help='If this field is empty, the covers of all products will be compute')


    @api.multi
    def covers_compute(self):
        for wizard in self:
            if wizard.product_ids:
                wizard.product_ids.cover_compute()
            else:
                self.env['product.product'].browse(self.env['stock.move'].search_group(fields=['product_id'], 
                                                                                       groupby=['product_id'], 
                                                                                       args=[('type', 'in', ('in', 'out')), 
                                                                                             ('state', '=', 'waiting')])
                                                   ).cover_compute()
        
        return True