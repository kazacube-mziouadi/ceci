# -*- coding: utf-8 -*-
from openerp import models, api, fields
import openerp.addons.decimal_precision as dp
    
    
class shipment_call_volume_calculate(models.TransientModel):
    _name = 'shipment.call.volume.calculate'
    
    
    @api.one
    @api.depends('nb_1', 'nb_2', 'nb_3', 'nb_4', 'nb_5', 'nb_6', 'nb_7', 'nb_8', 'nb_9', 'nb_10',
                 'length_1', 'length_2', 'length_3', 'length_4', 'length_5', 'length_6', 'length_7', 'length_8', 'length_9', 'length_10',
                 'width_1', 'width_2', 'width_3', 'width_4', 'width_5', 'width_6', 'width_7', 'width_8', 'width_9', 'width_10',
                 'height_1', 'height_2', 'height_3', 'height_4', 'height_5', 'height_6', 'height_7', 'height_8', 'height_9', 'height_10')
    def _compute_volume(self):
        self.total_volume = 0.0
        for i in range(1, 11):
            self['volume_%d'%(i)] = self['nb_%d'%(i)] * self['length_%d'%(i)] * self['width_%d'%(i)] * self['height_%d'%(i)] / 1000000.0
            self.total_volume += self['volume_%d'%(i)]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    shipment_call_id = fields.Many2one('shipment.call', string='Shipment', required=True, ondelete='cascade')
    nb_1 = fields.Integer(default=0, required=False)
    nb_2 = fields.Integer(default=0, required=False)
    nb_3 = fields.Integer(default=0, required=False)
    nb_4 = fields.Integer(default=0, required=False)
    nb_5 = fields.Integer(default=0, required=False)
    nb_6 = fields.Integer(default=0, required=False)
    nb_7 = fields.Integer(default=0, required=False)
    nb_8 = fields.Integer(default=0, required=False)
    nb_9 = fields.Integer(default=0, required=False)
    nb_10 = fields.Integer(default=0, required=False)
    length_1 = fields.Float(string='Length 1 (CM)', default=0.0, required=False)
    length_2 = fields.Float(string='Length 2 (CM)', default=0.0, required=False)
    length_3 = fields.Float(string='Length 3 (CM)', default=0.0, required=False)
    length_4 = fields.Float(string='Length 4 (CM)', default=0.0, required=False)
    length_5 = fields.Float(string='Length 5 (CM)', default=0.0, required=False)
    length_6 = fields.Float(string='Length 6 (CM)', default=0.0, required=False)
    length_7 = fields.Float(string='Length 7 (CM)', default=0.0, required=False)
    length_8 = fields.Float(string='Length 8 (CM)', default=0.0, required=False)
    length_9 = fields.Float(string='Length 9 (CM)', default=0.0, required=False)
    length_10 = fields.Float(string='Length 10 (CM)', default=0.0, required=False)
    width_1 = fields.Float(string='Width 1 (CM)', default=0.0, required=False)
    width_2 = fields.Float(string='Width 2 (CM)', default=0.0, required=False)
    width_3 = fields.Float(string='Width 3 (CM)', default=0.0, required=False)
    width_4 = fields.Float(string='Width 4 (CM)', default=0.0, required=False)
    width_5 = fields.Float(string='Width 5 (CM)', default=0.0, required=False)
    width_6 = fields.Float(string='Width 6 (CM)', default=0.0, required=False)
    width_7 = fields.Float(string='Width 7 (CM)', default=0.0, required=False)
    width_8 = fields.Float(string='Width 8 (CM)', default=0.0, required=False)
    width_9 = fields.Float(string='Width 9 (CM)', default=0.0, required=False)
    width_10 = fields.Float(string='Width 10 (CM)', default=0.0, required=False)
    height_1 = fields.Float(string='Height 1 (CM)', default=0.0, required=False)
    height_2 = fields.Float(string='Height 2 (CM)', default=0.0, required=False)
    height_3 = fields.Float(string='Height 3 (CM)', default=0.0, required=False)
    height_4 = fields.Float(string='Height 4 (CM)', default=0.0, required=False)
    height_5 = fields.Float(string='Height 5 (CM)', default=0.0, required=False)
    height_6 = fields.Float(string='Height 6 (CM)', default=0.0, required=False)
    height_7 = fields.Float(string='Height 7 (CM)', default=0.0, required=False)
    height_8 = fields.Float(string='Height 8 (CM)', default=0.0, required=False)
    height_9 = fields.Float(string='Height 9 (CM)', default=0.0, required=False)
    height_10 = fields.Float(string='Height 10 (CM)', default=0.0, required=False)
    volume_1 = fields.Float(string='Volume 1 (M3)', compute='_compute_volume', digits_compute=dp.get_precision('Product UoM'))
    volume_2 = fields.Float(string='Volume 2 (M3)', compute='_compute_volume', digits_compute=dp.get_precision('Product UoM'))
    volume_3 = fields.Float(string='Volume 3 (M3)', compute='_compute_volume', digits_compute=dp.get_precision('Product UoM'))
    volume_4 = fields.Float(string='Volume 4 (M3)', compute='_compute_volume', digits_compute=dp.get_precision('Product UoM'))
    volume_5 = fields.Float(string='Volume 5 (M3)', compute='_compute_volume', digits_compute=dp.get_precision('Product UoM'))
    volume_6 = fields.Float(string='Volume 6 (M3)', compute='_compute_volume', digits_compute=dp.get_precision('Product UoM'))
    volume_7 = fields.Float(string='Volume 7 (M3)', compute='_compute_volume', digits_compute=dp.get_precision('Product UoM'))
    volume_8 = fields.Float(string='Volume 8 (M3)', compute='_compute_volume', digits_compute=dp.get_precision('Product UoM'))
    volume_9 = fields.Float(string='Volume 9 (M3)', compute='_compute_volume', digits_compute=dp.get_precision('Product UoM'))
    volume_10 = fields.Float(string='Volume 10 (M3)', compute='_compute_volume', digits_compute=dp.get_precision('Product UoM'))
    total_volume = fields.Float(string='Total volume', compute='_compute_volume', digits_compute=dp.get_precision('Product UoM'))

    
    @api.multi
    def validate(self):
        for wiz in self:
            if wiz.total_volume and wiz.shipment_call_id:
                wiz.shipment_call_id.write({'volume': wiz.total_volume})
                
        return True
        
        
    @api.model    
    def default_get(self, fields):
        res = super(shipment_call_volume_calculate, self).default_get(fields)
        res['shipment_call_id'] = self.env.context['active_id']
        return res