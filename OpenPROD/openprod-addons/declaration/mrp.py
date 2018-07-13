# encoding: utf-8
from openerp import models, api, fields

class mrp_workorder(models.Model):
    _inherit = 'mrp.workorder'
    
    declared_time_tablet = fields.Float(string='Time declared on tablet', default=0.0, required=False)
    declaration_note = fields.Text(string='Declaration note')
    declare_tablet_cons = fields.Boolean(string='Declare consumption with tablet', default=False)
    
    @api.one
    def add_another_label(self, label_id, qty):
        '''
            Fonction qui créé un mrp.label.consumption et éventuellement le stock.move pour le produit associé
             à partir d'un label_id et d'une quantité
        :param label_id: ID d'un label
        :param qty: quantité du move
        '''
        label = self.env['stock.label'].browse(label_id)
        move = self.env['stock.move'].search([
                                              ('wo_incoming_id', '=', self.id),
                                              ('product_id', '=', label.product_id.id)
                                              ])
        location_obj = self.env['stock.location']
        location_id = self.first_resource_id and self.first_resource_id.location_id.id or False
        location_dest_rcs = location_obj.search([('usage', '=', 'production')], limit=1)
        efficient_unit_qty = self.quantity and qty/self.quantity or qty
        if not location_id:
            location_id = location_obj.search([('usage', '=', 'intern')], limit=1).id
        if not len(move):
            move = self.env['stock.move'].create_move(label.product_id,
                                                      location_id,
                                                      location_dest_rcs.id, 
                                                      qty=qty,
                                                      uom=label.product_id.uom_id or False,
                                                      other_data={'wo_incoming_id':self.id, 
                                                                  'efficient_unit_qty':efficient_unit_qty, 
                                                                  'is_forecast': self.is_forecast,},
                                                      in_product_uom=True)
            move.wkf_waiting()
        self.env['mrp.label.consumption'].create({
                                                  'wo_id': self.id,
                                                  'label_id': label_id,
                                                  'quantity': qty,
                                                  'use_consumption': True,
                                                  })