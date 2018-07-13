# -*- coding: utf-8 -*-
from openerp import models, api, fields, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import ValidationError


class create_packing_list(models.TransientModel):
    """ 
        Create packing list 
    """
    _name = 'create.packing.list'
    _description = 'Create packing list'

    
    @api.one
    @api.depends('chosen_label_ids')
    def _compute_nb_uc(self):
        self.nb_uc = len(self.chosen_label_ids)
          
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    shipment_id = fields.Many2one('shipment', string='Shipment', required=False, ondelete='cascade')
    label_ids = fields.Many2many('stock.label', 'wiz_create_packing_label_rel', 'wiz_id', 'label_id',  string='Labels')
    chosen_label_ids = fields.Many2many('stock.label', 'wiz_create_chosen_packing_label_rel', 'wiz_id', 'label_id',  string='Chosen labels')
    partner_id = fields.Many2one('res.partner', string='Partner', required=False, ondelete='cascade')
    label_template_id = fields.Many2one('stock.label.template', string='Template', required=True, ondelete='cascade')
    gross_weight = fields.Float(default=0.0, required=True)
    net_weight = fields.Float(default=0.0, required=True)
    nb_uc = fields.Integer(string='Nb UC', compute='_compute_nb_uc')
    length = fields.Float(digits=dp.get_precision('Stock Weight'), )
    width = fields.Float(digits=dp.get_precision('Stock Weight'), )
    height = fields.Float(digits=dp.get_precision('Stock Weight'), )
    volume = fields.Float('Volume (M3)', digits=dp.get_precision('Stock Weight'), )
    pallet_type_id = fields.Many2one('stock.pallet.type', string='Pallet type', required=False, ondelete='cascade')
    
    
    @api.onchange('pallet_type_id')
    def _onchange_pallet_type_id(self):
        if self.pallet_type_id:
            self.length = self.pallet_type_id.length
            self.width = self.pallet_type_id.width
    
    
    @api.onchange('length', 'width', 'height')
    def onchange_volume(self):
        self.volume = self.length * self.width * self.height / 1000000.0

    
    def compute_net_weight(self, gross_weight, nb_uc):
        return gross_weight
    
    
    @api.onchange('gross_weight', 'chosen_label_ids')
    def onchange_gross_weight(self):
        net_weight = self.compute_net_weight(self.gross_weight, self.nb_uc)
        if net_weight < 0:
            net_weight = self.gross_weight
             
        self.net_weight = net_weight
        
    
    @api.multi
    def create_packing_list(self):
        label_obj = self.env['stock.label']
        for wizard_rc in self:
            um_label_rc = label_obj.create({
                'template_id': wizard_rc.label_template_id.id,
                'name': wizard_rc.label_template_id.sequence_id.next_by_id(),
                'gross_weight': wizard_rc.gross_weight,
                'net_weight': wizard_rc.net_weight,
                'nb_uc': wizard_rc.nb_uc,
                'length': wizard_rc.length,
                'width': wizard_rc.width,
                'height': wizard_rc.height,
                'volume': wizard_rc.volume,
            })
            wizard_rc.chosen_label_ids.assign_um_label(um_label_rc)
            
        return True
        
        
    @api.model
    def default_get(self, fields):
        res = super(create_packing_list, self).default_get(fields)
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