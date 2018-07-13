# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.exceptions import except_orm
from openerp.tools.translate import _

class merge_purchase(models.TransientModel):
    """ 
        Merge purchases 
    """
    _name = 'merge.purchase'
    _description = 'Merge purchases'
    
    @api.multi
    def merge(self):
        """
            Merge d'achats
        """
        if len(self.env.context.get('active_ids'))<= 1:
            raise except_orm(_("Error"), _('You need more than one purchase to make a merge!'))
            
        res = self.env['purchase.order'].browse(self.env.context.get('active_ids')).do_merge()
        res['context'] = {'active_id': res['res_id'], 'active_domain': ""}
        return res
    
    
class merge_purchase_line(models.TransientModel):
    """ 
        Merge purchases lines
    """
    _name = 'merge.purchase.line'
    _description = 'Merge purchases lines'
    
    @api.multi
    def merge(self):
        """
            Merge des lignes d'achats
        """
        if len(self.env.context.get('active_ids'))<= 1:
            raise except_orm(_("Error"), _('You need more than one purchase line to make a merge!'))
        
        return self.env['purchase.order.line'].browse(self.env.context.get('active_ids')).do_merge_lines()