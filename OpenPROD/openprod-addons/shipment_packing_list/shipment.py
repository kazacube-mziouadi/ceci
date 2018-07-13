# coding: utf-8
from openerp import models, fields, api, _

class shipment(models.Model):
    """ 
    Shipment 
    """
    _inherit = 'shipment'
    
        
    @api.one
    @api.depends('picking_ids')
    def _um_label_ids_compute(self):
        res = []
        for picking_rc in self.picking_ids:
            for move_rc in picking_rc.move_ids:
                if move_rc.state != 'cancel':
                    for move_label_rs in move_rc.move_label_ids:
                        if move_label_rs.label_id.um_label_id:
                            res.append(move_label_rs.label_id.um_label_id.id)
            
        self.um_label_ids = list(set(res))
        
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    um_label_ids = fields.One2many('stock.label', compute='_um_label_ids_compute', string='Packing list')
    
    
    @api.multi
    def retrieve_packing_list_informations(self):
        for shipment_rc in self:
            pallet_number = 0
            package_number = 0
            weight = 0
            label_number = 0
            um_label_ids = []
            uc_label_ids = []
            for picking_rc in shipment_rc.picking_ids:
                for move_rc in picking_rc.move_ids:
                    if move_rc.state != 'cancel':
                        for move_label_rc in move_rc.move_label_ids:
                            label_rc = move_label_rc.label_id
                            if label_rc and label_rc.id not in uc_label_ids:
                                package_number += 1
                                uc_label_ids.append(label_rc.id)
                                if label_rc.um_label_id and label_rc.um_label_id.id not in um_label_ids:
                                    pallet_number += 1
                                    label_number += 1
                                    weight += label_rc.um_label_id.gross_weight
                                    um_label_ids.append(label_rc.um_label_id.id)
    
            shipment_rc.write({
                'pallet_number': pallet_number, 
                'label_number': label_number, 
                'package_number': package_number, 
                'weight': weight
            })
    
        return True