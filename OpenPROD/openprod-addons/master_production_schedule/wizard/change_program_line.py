# -*- coding: utf-8 -*-
from openerp.tools.translate import _
from openerp import models, fields, api
from openerp.exceptions import except_orm, ValidationError


class change_program_line(models.TransientModel):
    """ 
        Wizard to change program line
    """
    _name = 'change.program.line'
    _description = 'Wizard to change program line'
    _rec_name = 'product_id'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='cascade')
    has_customer = fields.Boolean(string='Has a customer', default=False)
    line_mid_period = fields.Date(string='Start date of the line')
    period_id = fields.Many2one('master.production.period', string='Period', required=False, ondelete='cascade')
    production_schedule_id = fields.Many2one('master.production.schedule', string='Production schedule', required=False, ondelete='cascade')
    uom_id = fields.Many2one('product.uom', string='Management unit', required=False, ondelete='cascade', readonly=True)
    qty_firm_order = fields.Float(string='Quantity firm order', default=0.0, required=False, readonly=True)
    qty_forecast_order = fields.Float(string='Quantity forecast order', default=0.0, required=False, readonly=True)
    qty_firm_procurement = fields.Float(string='Quantity firm procurement', default=0.0, required=False, readonly=True)
    qty_forecast_procurement = fields.Float(string='Quantity forecast procurement', default=0.0, required=False, readonly=True)
    available_stock_firm = fields.Float(string='Available stock (firm)', default=0.0, required=False, readonly=True)
    available_stock_firm_forecast = fields.Float(string='Available stock (firm + forecast)', default=0.0, 
                                                       required=False, readonly=True)
    #Onglet approvisionnement
    appro_quantity = fields.Float(string='Quantity', default=0.0, required=False)
    mo_ids = fields.Many2many('mrp.manufacturingorder', 'program_manufacturingorder_rel', 'change_program_id', 
                                       'manufacturingorder_id', string='Procurements', readonly=True)
    #Onglet commande
    order_quantity = fields.Float(string='Quantity', default=0.0, required=False)
    customer_id = fields.Many2one('res.partner', string='Customer', required=False, ondelete='cascade', 
                                  domain=['|','&', ('is_company', '=', True), ('is_customer', '=', True),
                                          '&', ('is_company', '=', False), ('can_order', '=', True)])
    sale_line_ids = fields.Many2many('sale.order.line', 'program_sale_line_rel', 'change_program_id', 
                                       'sale_order_line_id', string='Sales', readonly=True)
    stock_move_ids = fields.Many2many('stock.move', 'program_stock_move_rel', 'change_program_id', 
                                       'stock_move_id', string='Consumption', readonly=True)
    
    @api.model
    def default_get(self, fields_list):
        """
            Récupération des informations de la ligne
        """
        res = super(change_program_line, self).default_get(fields_list=fields_list)
        if self.env.context.get('active_model', '') == 'master.production.schedule.line' and self.env.context.get('active_id', False):
            line = self.env['master.production.schedule.line'].browse(self.env.context.get('active_id'))
            if line and line.product_id:
                start_date = line.start_date
                end_date = line.end_date
                #Récupération des quantités et des données du produit
                res2 = {'product_id': line.product_id.id,
                        'uom_id': line.uom_id and line.uom_id.id or False,
                        'production_schedule_id': line.master_production_id and line.master_production_id.id or False,
                        'line_mid_period': line.mid_period,
                        'period_id': line.period_id and line.period_id.id or False,
                        'qty_firm_order': line.qty_firm_order,
                        'qty_forecast_order': line.qty_forecast_order,
                        'qty_firm_procurement': line.qty_firm_procurement,
                        'qty_forecast_procurement': line.qty_forecast_procurement,
                        'available_stock_firm': line.available_stock_firm,
                        'available_stock_firm_forecast': line.available_stock_firm_forecast}
                res.update(res2)
                #Arguments de recherche des moves et des lignes de vente
                args = [('product_id', '=', line.product_id.id), 
                        ('date', '<=', end_date), 
                        ('state', '!=', 'cancel'), 
                        ('is_forecast', '=', True),
                        ('date', '>=', start_date),
                        ('wo_outgoing_id', '!=', False)]
                sale_args = [('product_id', '=', line.product_id.id), 
                        ('sale_state', '!=', 'cancel'),
                        ('sale_type', '=', 'forecast'),
                        '|', '&', ('confirmed_departure_date', '!=', False), ('confirmed_departure_date', '<=', end_date), 
                        '&', ('confirmed_departure_date', '=', False), ('departure_date', '<=', end_date),
                        '|', '&', ('confirmed_departure_date', '!=', False), ('confirmed_departure_date', '>=', start_date), 
                        '&', ('confirmed_departure_date', '=', False),('departure_date', '>=', start_date)]
                args_in = [('type', '=', 'in')]
                args_out = [('type', '=', 'out')]
                #Si on a un client, on récupère uniquement les OT et les lignes de vente de ce client
                customer_id = line.customer_id and line.customer_id.id
                if customer_id:
                    res['customer_id'] = customer_id
                    res['has_customer'] = True
                    args_in.append(('wo_outgoing_id.customer_id', '=', customer_id))
                    args_out.append(('wo_incoming_id.customer_id', '=', customer_id))
                    sale_args.append(('sale_partner_id', '=', customer_id))
                
                #Recherche et récupération des ids des OF
                mo_ids = []
                args_in.extend(args)
                move_rs = self.env['stock.move'].search(args_in)
                wo_rs_list = [move.wo_outgoing_id for move in move_rs if move.wo_outgoing_id]
                if wo_rs_list:
                    mo_ids = [wo.mo_id.id for wo in wo_rs_list if wo.mo_id]
                    
                if wo_rs_list:
                    res['mo_ids'] = [(6, 0, mo_ids)]
                
                #Recherche et récupération des ids des lignes de vente
                so_rs = self.env['sale.order.line'].search(sale_args)
                if so_rs:
                    res['sale_line_ids'] = [(6, 0, so_rs.ids)]
                    
                #Recherche et récupération des ids des mouvements
                args_out.extend(args)
                smo_rs = self.env['stock.move'].search(args_out)
                if smo_rs:
                    res['stock_move_ids'] = [(6, 0, smo_rs.ids)]
                    
        return res
    
    
    @api.multi
    def create_procurement_line(self):
        """
            Bouton qui crée un OF et assigne la ligne au M2M
        """
        if self.product_id and self.product_id.produce_ok and self.line_mid_period and self.production_schedule_id:
            if self.appro_quantity == 0:
                raise except_orm(_('Error'), _('Please enter a quantity'))
            
            other_data={'is_forecast': True,
                        'requested_date': self.line_mid_period}
            if self.has_customer and self.customer_id:
                other_data['customer_id'] = self.customer_id.id
            
            #Création de l'OF
            mo, qty_mo = self.env['mrp.manufacturingorder'].create_mo(self.product_id, quantity=self.appro_quantity, uom=self.uom_id,
                                                                      other_data=other_data, options=[])
            if mo:
                #On génère les OTs et on les planifie au plus tard
                mo.action_generating_wo()
                self.env['mrp.workorder'].plannification_mo_at_the_latest(date=self.line_mid_period, mo=mo, is_sublevel=False, 
                                                                          is_procur_level_manufact=True,
                                                                          is_product_sublevel_manufact=True,
                                                                          is_procur_level_purchase=False,
                                                                          automatic_purchase=False,
                                                                          is_procur_sublevel_purchase=False, first_pass=True,
                                                                          change_resources=True, no_modif_prio_date=False)
                return self.update_program()
            else:
                raise except_orm(_('Error'), _('There is an error with the technical datas of your product and the system can\'t create the manufacturing order.'
                                               'Check the routing and the bom of your product.'))
                
        return True
    
    
    @api.multi
    def create_sale_order_line(self):
        """
            Bouton qui crée une ligne de vente et une vente et assigne la ligne au M2M
        """
        if self.product_id and self.product_id.sale_ok and self.line_mid_period and self.production_schedule_id and self.customer_id:
            if self.order_quantity == 0:
                raise except_orm(_('Error'), _('Please enter a quantity'))
            
            other_data = {'type': 'forecast'}
            so_line = {self.product_id: {'sec_uom_qty': self.order_quantity}}
            self.env['sale.order'].create_sale(self.customer_id, so_line, self.line_mid_period, other_data)
            return self.update_program()
                
        return True
    
    
    def return_program_view(self, production_schedule_id=False):
        """
            Retourne la vue du programme
        """
        return {'type':'ir.actions.act_window_view_reload'}
    
    
    def update_program(self, product_id=False, period_id=False, production_schedule_id=False):
        """
            Fonction qui met à jour le PDP et retourne la vue du programme
        """
        if not product_id:
            product_id = self.product_id.id
            
        if not period_id:
            period_id = self.period_id.id
            
        if not production_schedule_id:
            production_schedule_id = self.production_schedule_id.id
            
        #On relance le calcul du PDP
        self.env['master.production.schedule']._import_program_lines(master_production_id=production_schedule_id, 
                                                          period_id=period_id, 
                                                          product_id=product_id,
                                                          delete_all_lines=False)
        #On renvoie la vue du programme
        action = self.return_program_view(production_schedule_id=production_schedule_id)
        return action



class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
    
    
    @api.multi
    def delete_so_from_program(self):
        """
            Bouton qui supprime la ligne de vente
        """
        if self.sale_state == 'draft':
            self.unlink()
        else:
            raise except_orm(_('Error'), _("The line is not in draft, you can only delete the draft lines"))
        
        #On relance le calcul du PDP et on affiche sa vue
        context = self.env.context
        if context.get('product_id') and context.get('period_id') and context.get('production_schedule_id'):
            return self.env['change.program.line'].update_program(context['product_id'], context['period_id'], context['production_schedule_id'])
            
        return True
    
    
    @api.multi
    def confirm_so_from_program(self):
        """
            Bouton qui lance la fonction permettant de passer la vente en type "Séries"
        """
        if self.sale_state == 'draft':
            self.confirm_forecast_line()
        else:
            raise except_orm(_('Error'), _("The line is not in draft, you can only confirm the forecast draft lines"))
        
        #On relance le calcul du PDP et on affiche sa vue
        context = self.env.context
        if context.get('product_id') and context.get('period_id') and context.get('production_schedule_id'):
            return self.env['change.program.line'].update_program(context['product_id'], context['period_id'], context['production_schedule_id'])
            
        return True
    
    
    @api.multi
    def change_so_quantity_from_program(self):
        """
            Bouton qui permet de modifier la quantité de la ligne de vente
        """
        context = self.env.context
        new_quantity = context.get('new_quantity') and context['new_quantity'] or 0
        if new_quantity:
            if self.sale_state == 'draft':
                self.write({'uom_qty': new_quantity})
                self._onchange_uom_qty()
            else:
                raise except_orm(_('Error'), _("The line is not in draft, you can only change the draft lines"))
            
            #On relance le calcul du PDP et on affiche sa vue
            if context.get('product_id') and context.get('period_id') and context.get('production_schedule_id'):
                return self.env['change.program.line'].update_program(context['product_id'], context['period_id'], context['production_schedule_id'])
            
        else:
            raise except_orm(_('Error'), _('Please enter a quantity'))
            
        return True
    
    
    
    
