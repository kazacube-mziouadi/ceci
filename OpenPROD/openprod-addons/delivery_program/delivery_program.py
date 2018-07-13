# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from datetime import date
from openerp.exceptions import UserError
import openerp.addons.decimal_precision as dp


class delivery_program(models.Model):
    _name = 'delivery.program'
    _description = 'Delivery program'


    @api.model
    def _get_state(self):
        return [
            ('draft', _('Draft')),
            ('progress', _('In progress')),
            ('done', _('Done')),
            ('obsolet', _('Obsolet')),
            ('cancel', _('Cancel'))
        ]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Name', required=True)
    state = fields.Selection('_get_state', string='State', default='draft')
    customer_id = fields.Many2one('res.partner', string='Customer', required=True, domain=[('is_customer', '=', True)], ondelete='restrict')
    creation_date = fields.Date(string='Creation date', default=lambda *a: fields.Datetime.now())
    product_id = fields.Many2one('product.product', string='Product', ondelete='restrict')
    is_generate_reservation = fields.Boolean(string='Generate reservation', default=False)
    delivery_program_line_ids = fields.One2many('delivery.program.line', 'delivery_program_id', string='Delivery program lines')
    move_ids = fields.One2many('stock.move', 'delivery_program_id', string='Reservation', readonly=True)
    notes = fields.Text(string='Notes')
    is_forecast = fields.Boolean(string='Forecast', default=False)


    @api.multi
    def compute(self):
        previous_product_id = False
        previous_date = False
        cumulate_need_ungenerated = False
        for move in self.move_ids:
            move.wkf_cancel()
            
        for delivery_program_line in self.delivery_program_line_ids:
            current_product = delivery_program_line.product_id                
            # Calcul du besoin non généré
            # 0 si flag sur la ligne généré les réservations est à True sinon c'est la qty de la ligne si pas de commande ou la commande n'est pas validé
            delivery_program_line.need_ungenerated = (not delivery_program_line.sale_order_id or (delivery_program_line.sale_order_id.display_state != 'confirmed_sale' and delivery_program_line.sale_order_id.display_state != 'done')) and delivery_program_line.quantity or 0
            # Génération des réservations
            if delivery_program_line.is_generate_reservation and delivery_program_line.need_ungenerated != 0.0:
                delivery_program_line.generate_reservation()
                   
            delivery_program_line.need_ungenerated = not delivery_program_line.is_generate_reservation and delivery_program_line.need_ungenerated or 0                
            # Calcul du Stock à date
            if current_product.id == previous_product_id:
                cumulate_need_ungenerated += delivery_program_line.need_ungenerated
            else:
                previous_date = date.min
                cumulate_need_ungenerated = delivery_program_line.need_ungenerated
            
            delivery_program_line.stock_date = current_product.get_available_stock(to_date=delivery_program_line.date) - cumulate_need_ungenerated
            # Calcul de l'OF ferme
            # M2M (tags) des OF fermes non terminé ≤ a la date de la ligne et > a date de la ligne précédente
            delivery_program_line.closed_mo_ids = [(6, 0, self.env['mrp.manufacturingorder'].search([('product_id', '=', current_product.id), ('is_forecast', '=', False), ('state', '!=', 'done'), ('planned_end_date', '<=', delivery_program_line.date), ('planned_end_date', '>', previous_date)]).ids)]
            # Calcul de l'OF prev
            # M2M (tags) des OF prev  ≤ a la date de la ligne et > a date de la ligne précédente
            forecast_manufacturingorder_rcs = self.env['mrp.manufacturingorder'].search([('product_id', '=', current_product.id), ('is_forecast', '=', True), ('state', '!=', 'done'), ('planned_end_date', '<=', delivery_program_line.date), ('planned_end_date', '>', previous_date)])
            delivery_program_line.forecast_mo_ids = [(6, 0, forecast_manufacturingorder_rcs.ids)]
            # Calcul des lignes d'achat
            # M2M (tags) des lignes d'achat draft, qui n'ont pas étaient totalement receptionnées et dont la date de confirmation, ou d'expedition ≤ a la date de la ligne et > a date de la ligne précédente
            purchase_order_line_rcs = self.env['purchase.order.line'].search([('product_id', '=', current_product.id), ('purchase_state', '!=', 'draft'), ('to_received', '>', 0.0), '|', '&', '&', ('confirmed_date', '!=', False), ('confirmed_date', '<=', delivery_program_line.date), ('confirmed_date', '>', previous_date), '&', '&', ('confirmed_date', '=', False), ('expected_date', '<=', delivery_program_line.date), ('expected_date', '>', previous_date)])
            delivery_program_line.purchase_order_line_ids = [(6, 0, purchase_order_line_rcs.ids)]
            # Calcul QT OF prev
            delivery_program_line.forecast_quantity = sum([forecast_manufacturingorder.quantity for forecast_manufacturingorder in forecast_manufacturingorder_rcs])
            previous_product_id = delivery_program_line.product_id.id
            previous_date = delivery_program_line.date


    @api.multi
    def add_delivery_program_line(self):    
        data_pool = self.env['ir.model.data']
        action_model, action_id = data_pool.get_object_reference('delivery_program', 'delivery_program_line_act')
        if action_model:
            action_pool = self.env[action_model]
            action = action_pool.browse(action_id).read()[0]
            action['context'] = {'search_default_delivery_program_id': self.ids[0], 'default_delivery_program_id': self.ids[0]}
            return action
    
    
    @api.multi
    def wkf_draft(self):
        return self.write({'state': 'draft'})
    
    
    @api.multi
    def wkf_progress(self):
        return self.write({'state': 'progress'})
    
    
    @api.multi
    def wkf_done(self):
        for move in self.move_ids:
            move.wkf_cancel()
            
        return self.write({'state': 'done'})
    
    
    @api.multi
    def wkf_obsolet(self):
        for move in self.move_ids:
            move.wkf_cancel()
            
        return self.write({'state': 'obsolet'})
    
    
    @api.multi
    def wkf_cancel(self):
        for move in self.move_ids:
            move.wkf_cancel()
            
        return self.write({'state': 'cancel'})



class delivery_program_line(models.Model):
    _name = 'delivery.program.line'
    _description = 'Delivery program line'
    _order = 'product_id, date'


    @api.model
    def _get_type(self):
        return [
            ('forecast', _('Forecast')),
            ('closed', _('Closed'))
        ]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    delivery_program_id = fields.Many2one('delivery.program', string='Delivery program', ondelete='cascade')
    date = fields.Date(string='Date', default=lambda *a: fields.Datetime.now(), required=True)
    product_id = fields.Many2one('product.product', string='Product', ondelete='restrict', required=True)
    quantity = fields.Float(string='Quantity', digits=dp.get_precision('Product quantity'), default=0.0)
    unit_id = fields.Many2one('product.uom', string='Unit', related='product_id.uom_id', readonly=True)
    sale_order_id = fields.Many2one('sale.order', related='sale_order_line_id.sale_order_id', string='Order number', ondelete='restrict')
    sale_order_line_id = fields.Many2one('sale.order.line', string='Sale order line', ondelete='restrict')
    type = fields.Selection('_get_type', string='Type', default='closed')
    stock_date = fields.Float(string='Stock date', digits=dp.get_precision('Product quantity'), readonly=True, default=0.0)
    closed_mo_ids = fields.Many2many('mrp.manufacturingorder', 'dp_closed_mo_rel', 'delivery_program_id', 'mo_id', string='Closed MO')
    forecast_mo_ids = fields.Many2many('mrp.manufacturingorder', 'dp_forecast_mo_rel', 'delivery_program_id', 'mo_id', string='Forecast MO')
    purchase_order_line_ids = fields.Many2many('purchase.order.line', 'dp_pol_rel', 'delivery_program_id', 'pol_id', string='Purchase order line')
    forecast_quantity = fields.Float(string='Forecast quantity', digits=dp.get_precision('Product quantity'), readonly=True, default=0.0)
    is_generate_reservation = fields.Boolean(string='Generate reservation')
    need_ungenerated = fields.Float(string='Need ungenerated', digits=dp.get_precision('Product quantity'), default=0.0)
    is_forecast = fields.Boolean(related='delivery_program_id.is_forecast', string='Forecast')
    remaining_quantity = fields.Float(related='sale_order_line_id.remaining_qty', string='Remaining quantity', digits=dp.get_precision('Product quantity'), readonly=True)
    
    
    @api.multi
    def create_quick_mo_standard(self):
        context = self.env.context.copy()
        context.update({'is_forecast': False})
        return {
            'name': _('Create quick MO'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'create.quick.mo',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context
        }
        
        
    @api.multi
    def create_quick_mo_forecast(self):
        context = self.env.context.copy()
        context.update({'is_forecast': True})
        return {
            'name': _('Create quick MO'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'create.quick.mo',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context
        }
    

    @api.multi
    def generate_reservation(self):
        company_rc = self.env['res.users'].browse(self.env.uid).company_id
        warehouse_rc = company_rc.warehouse_id
        other_data = {'delivery_program_id': self.delivery_program_id.id}
        move_rc = self.env['stock.move'].create_move(product=self.product_id, src_location=warehouse_rc.reservation_location_id, dst_location=warehouse_rc.production_location_id, qty=(not self.sale_order_id or (self.sale_order_id.display_state != 'confirmed_sale' and self.sale_order_id.display_state != 'done')) and self.need_ungenerated or 0, uom=self.unit_id, date=self.date, other_data=other_data)
        move_rc.wkf_waiting()
    
    
    @api.model
    def create(self, vals):
        context = self.env.context
        if 'default_delivery_program_id' in context:
            raise UserError(_("You can't create a delivery program line with this button"))
        
        return super(delivery_program_line, self).create(vals)