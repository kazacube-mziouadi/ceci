# coding: utf-8
from openerp import models, fields, api, _
from openerp.exceptions import ValidationError


class stock_picking(models.Model):
    _inherit = 'stock.picking'

    #===========================================================================
    # COLUMNS
    #===========================================================================
    shipment_call_id = fields.Many2one('shipment.call', string='Request for removal', required=False, copy=False, ondelete='set null')
    shipment_call_state_related = fields.Selection(related='shipment_call_id.state', readonly=True)

    @api.multi
    def add_to_shipment_call(self):
        shipment_call_obj = self.env['shipment.call']
        shipment_call_rc = shipment_call_obj.search([
            ('incoterm_id', '=', self.incoterm_id.id), 
            ('address_id', '=', self.partner_id.address_id.id), 
            ('forwarding_agent_address_id', '=', self.forwarding_agent_id.address_id.id), 
            ('state', '=', 'draft'),
        ], limit=1)
        if not shipment_call_rc:
            shipment_call_rc = shipment_call_obj.create_shipment_call(self.partner_id, forwarder_agent_rc=self.forwarding_agent_id, incoterm_rc=self.incoterm_id, date=self.date)
            
        self.write({'shipment_call_id': shipment_call_rc.id})
        shipment_call_rc.recompute()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'shipment.call',
            'views': [[False, 'form']],
            'res_id': shipment_call_rc.id
        }

        
    def do_partial_shipment(self, lines):
        """
            Traite un picking en créant un reliquat si besoin
            :type self: stock.picking
            :param lines: Lignes de wizard de traitement du picking (chaque ligne représente un mouvement)
            :type lines: recordset list: stock.partial.picking.line
            :return: Nouveau picking si reliquat. Sinon False
            :rtype: recordset: stock.picking
        """
        new_picking = False
        move_to_copy = {}
        for line in lines:
            move = line.move_id
            if line.uom_qty > 0:
                if line.uom_qty > move.uom_qty:
                    move.write({'uom_qty': line.uom_qty, 'sec_uom_qty': line.sec_uom_qty, 'uoi_qty': line.uoi_qty})
                elif line.uom_qty < move.uom_qty:
                    if line.manage_scrap:
                        new_uom_qty = move.uom_qty - line.uom_qty
                        new_sec_uom_qty = move.sec_uom_qty - line.sec_uom_qty
                        new_uoi_qty = move.uoi_qty - line.uoi_qty
                        move_to_copy[move] = {'uom_qty': new_uom_qty, 'sec_uom_qty': new_sec_uom_qty, 'uoi_qty': new_uoi_qty}

                    move.write({'uom_qty': line.uom_qty, 'sec_uom_qty': line.sec_uom_qty, 'uoi_qty': line.uoi_qty})

        if move_to_copy:
            if self.invoice_state == 'none':
                invoice_state = 'none'
            else:
                invoice_state = '2binvoiced'

            new_picking = self.copy({'backorder_id': self.id, 'move_ids': False, 'invoice_state': invoice_state})
            if new_picking:
                for move, vals in move_to_copy.iteritems():
                    vals['picking_id'] = new_picking.id
                    move.copy(vals)

            new_picking.wkf_waiting()

        return new_picking


    @api.multi
    def remove_from_shipment_call(self):
        if (self.shipment_call_id.state == 'draft'):
            if len(self.shipment_call_id.picking_ids) == 1:
                self.shipment_call_id.write({'desired_arrival_date': False})
                
            self.write({'shipment_call_id': None})
            return {'type': 'ir.actions.client', 'tag': 'reload'}
        else:
            raise ValidationError(_('Error'), _('You can\'t modify a request for removal not in state draft'))