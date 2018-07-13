# coding: utf-8
from openerp import models, fields, api, _
from openerp.exceptions import ValidationError


class stock_picking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def _shipment_state_get(self):
        return [
            ('toprint', _('To print')),
            ('todo', _('To do')),
            ('tovalidate', _('To validate')),
            ('done', _('Done')),
        ]

    #===========================================================================
    # COLUMNS
    #===========================================================================
    shipment_id = fields.Many2one('shipment', string='Shipment', required=False, copy=False, ondelete='set null')
    shipment_state = fields.Selection('_shipment_state_get', default='toprint', copy=False)
    shipment_state_related = fields.Selection(related='shipment_id.state', readonly=True)


    @api.multi
    def add_to_shipment(self):
        shipment_obj = self.env['shipment']
        shipment_rc = shipment_obj.search([
            ('incoterm_id', '=', self.incoterm_id.id), 
            ('street', '=', self.street), 
            ('street2', '=', self.street2), 
            ('zip', '=', self.zip), 
            ('city', '=', self.city), 
            ('region_id', '=', self.region_id.id), 
            ('country_id', '=', self.country_id.id), 
            ('address_name', '=', self.address_name), 
            ('forwarding_agent_id', '=', self.forwarding_agent_id.id),
            ('state', '=', 'draft'),
        ], limit=1)
        if not shipment_rc:
            shipment_rc = shipment_obj.create_shipment(self.partner_id, address_rc=self.address_id, incoterm_rc=self.incoterm_id, date=self.date)
            
        self.write({'shipment_id': shipment_rc.id})
        shipment_rc.recompute()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'shipment',
            'views': [[False, 'form']],
            'res_id': shipment_rc.id
        }
        
    
    @api.multi
    def print_picking_button(self):
        """
            Impression du BL et passage à l'état de préparation To do
        """
        for picking_rc in self:
            picking_rc.do_print_picking()
            if picking_rc.shipment_state == 'toprint':
                picking_rc.shipment_wkf_todo()


    def do_partial(self, lines, make_done=True, transfer_origin_move_rc=False):
        res = super(stock_picking, self).do_partial(lines, make_done=make_done, transfer_origin_move_rc=transfer_origin_move_rc)
        if self.type == 'out':
            self.shipment_wkf_done()
            
        return res
        
        
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
    def remove_from_shipment(self):
        if (self.shipment_id.state == 'draft'):
            if len(self.shipment_id.picking_ids) == 1:
                self.shipment_id.write({'desired_arrival_date': False})
                
            self.write({'shipment_id': None})
            return {'type': 'ir.actions.client', 'tag': 'reload'}
        else:
            raise ValidationError(_('Error'), _('You can\'t modify a shipment not in state draft'))
        
    
    def shipment_check_tovalidate(self):
        res = False
        for picking_rc in self:
            for move_rc in picking_rc.move_ids:
                if move_rc.move_label_ids or not move_rc.track_label_product:
                    return True
                else:
                    res = False
                
        return res

        
    def shipment_wkf_todo(self):
        for picking_rc in self:
            if picking_rc.shipment_state == 'toprint':
                picking_rc.write({'shipment_state': 'todo'})
                if picking_rc.shipment_check_tovalidate():
                    picking_rc.shipment_wkf_tovalidate()

    
    def shipment_wkf_tovalidate(self):
        self.write({'shipment_state': 'tovalidate'})
        
        
    def shipment_wkf_done(self):
        self.write({'shipment_state': 'done'})

    
    @api.multi
    def wkf_cancel(self, with_move=True, manage_sale_purchase_state=True, keep_move_dates=False):
        res = super(stock_picking, self).wkf_cancel(with_move=with_move, manage_sale_purchase_state=manage_sale_purchase_state, keep_move_dates=keep_move_dates)
        self.write({'shipment_state': 'toprint'})
        return res
    
        
class stock_move(models.Model):
    _inherit = 'stock.move'
    
    def assign_label(self, labels, dict_label_qty=None, with_scrap=True, with_write=False, with_move=True, inactive=False):
        res = super(stock_move, self).assign_label(labels, dict_label_qty=dict_label_qty, with_scrap=with_scrap, with_write=with_write, with_move=with_move, inactive=inactive)
        if self.picking_id:
            self.picking_id.shipment_wkf_tovalidate()
            
        return res