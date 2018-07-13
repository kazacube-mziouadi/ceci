# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
import time, datetime
import openerp.addons.decimal_precision as dp

class label_consumption(models.TransientModel):
    """ 
        Label consumption
    """
    _name = 'label.consumption'
    _description = 'Label consumption'
    _rec_name = 'wo_id'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wo_id = fields.Many2one('mrp.workorder', string='Work Order', required=True, ondelete='cascade')
    uc_label_ids = fields.Many2many('stock.label', 'stock_label_label_consumption_rel', 'wiz_id', 'label_id', string='Label consumption')
    quantity = fields.Float(string='Wo quantity', default=0.0, required=False)
    
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('wo_id')
    def _onchange_wo_id(self):
        self.quantity = self.wo_id and self.wo_id.quantity or 1.0
        

    @api.multi
    def do_consumption(self):
        for wizard in self:
            product_ids = [l.product_id and l.product_id.id or False for l in wizard.uc_label_ids]
            if len(set(product_ids)) > 1:
                raise except_orm(_("Error"), _("Error! Products are not the same."))
            
            if wizard.uc_label_ids and wizard.wo_id:
                wizard.wo_id.do_label_consumption(wizard.uc_label_ids, wizard.quantity or 1.0)
            else:
                raise except_orm(_("Error"), _("You must provide at least one UC label."))
                                 
            return {
                    'name': _('Workorder'),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'mrp.workorder',
                    'type': 'ir.actions.act_window',
                    'res_id': wizard.wo_id.id,
                    'target': 'current',
                    }



class label_consumption_grouped(models.TransientModel):
    """ 
        Label consumption grouped
    """
    _name = 'label.consumption.grouped'
    _description = 'Label consumption grouped'
    _rec_name = 'group_wo_id'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    group_wo_id = fields.Many2one('mrp.group.wo', string='Wo group', required=True, ondelete='cascade')
    uc_label_ids = fields.Many2many('stock.label', 'stock_label_label_consumption_grouped_rel', 'wiz_id', 'label_id', string='Label consumption')
    quantity = fields.Float(string='Wo quantity', default=0.0, required=False)
    
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('group_wo_id')
    def _onchange_group_wo_id(self):
        quantity = 0
        for wo in self.group_wo_id.wo_ids:
            quantity += wo.quantity
            
        self.quantity = quantity or 1.0
        

    @api.multi
    def do_consumption_grouped(self):
        for wizard in self:
            product_ids = [l.product_id and l.product_id.id or False for l in wizard.uc_label_ids]
            if len(set(product_ids)) > 1:
                raise except_orm(_("Error"), _("Error! Products are not the same."))
            
            if wizard.uc_label_ids and wizard.group_wo_id:
                wizard.group_wo_id.do_label_consumption_grouped(wizard.uc_label_ids, wizard.quantity or 1.0)
            else:
                raise except_orm(_("Error"), _("You must provide at least one UC label."))
                                 
            return {
                    'name': _('Workorder'),
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'mrp.workorder',
                    'type': 'ir.actions.act_window',
                    'domain': [('id', 'in', wizard.group_wo_id.wo_ids.ids)],
                    'target': 'current',
                    }