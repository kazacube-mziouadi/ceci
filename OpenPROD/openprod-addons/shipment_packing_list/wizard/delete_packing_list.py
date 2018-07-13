# -*- coding: utf-8 -*-
from openerp import models, api, fields, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import ValidationError


class delete_packing_list(models.TransientModel):
    """ 
        Delete packing list 
    """
    _name = 'delete.packing.list'
    _description = 'Delete packing list'

    
    @api.one
    @api.depends('chosen_label_ids')
    def _compute_nb_uc(self):
        self.nb_uc = len(self.chosen_label_ids)
          
           
    #===========================================================================
    # COLUMNS
    #===========================================================================
    shipment_id = fields.Many2one('shipment', string='Shipment', required=False, ondelete='cascade')
    label_ids = fields.Many2many('stock.label', 'wiz_create_packing_label_rel', 'wiz_id', 'label_id',  string='Labels')
    chosen_label_ids = fields.Many2many('stock.label', 'wiz_create_packing_choosen_label_rel', 'wiz_id', 'label_id',  string='Chosen labels')
    um_label_ids = fields.Many2many('stock.label', 'wiz_create_packing_um_label_rel', 'wiz_id', 'label_id',  string='Chosen labels')
        
    
    @api.multi
    def delete_packing_list(self):
        for wizard_rc in self:
            wizard_rc.chosen_label_ids.write({'um_label_id': False})
            
        return True
    
    
    @api.onchange('chosen_label_ids')
    def onchange_chosen_label_ids(self):
        res = []
        for label_rc in self.chosen_label_ids:
            if label_rc.um_label_id:
                res.append(label_rc.um_label_id.id) 
           
        self.um_label_ids = res
    
        
    @api.model
    def default_get(self, fields):
        res = super(delete_packing_list, self).default_get(fields)
        if self.env.context.get('active_id', False):
            res['shipment_id'] = self.env.context['active_id']
            shipment_rc = self.env['shipment'].browse(res['shipment_id'])
            label_ids = []
            for picking_rc in shipment_rc.picking_ids:
                for move_rc in picking_rc.move_ids:
                    for move_label_rs in move_rc.move_label_ids:
                        label_ids.append(move_label_rs.label_id.id)
            
            res['label_ids'] = list(set(label_ids))
            
        return res