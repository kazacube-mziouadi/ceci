# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.addons.base_openprod.common import get_form_view
from openerp.addons.base_openprod import utils
from datetime import datetime
from dateutil.relativedelta import relativedelta
import string

class called_sale_order_line(models.TransientModel):
    """ 
        Sale called order lines
    """
    _name = 'called.sale.order.line'
    _description = 'Sale called order lines'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    called_order_id = fields.Many2one('generate.called.sale.order', string='Sale order', ondelete='set null')
    product_id = fields.Many2one('product.product', string='Product', readonly=True, ondelete='set null')
    quantity = fields.Float(string='Quantity', default=0.0, required=False)
    price = fields.Float(string='Price', default=0.0, required=False)
    sale_order_line_id = fields.Many2one('sale.order.line', string='Sale order line', required=False, ondelete='set null')
    
    @api.onchange('quantity', 'sale_order_line_id')
    def _onchange_product_quantity(self):
        """
            Au changement de la quantité vendue, on vérifie que cette quantité soit inférieure
            ou égale à la quantité de la ligne de vente, sinon on envoi un warning
        """
        res = {'warning': {}}
        if self.sale_order_line_id:
            if self.quantity > self.sale_order_line_id.sec_uom_qty:
                res['warning'] = {'title':_('Warning'), 'message':_('You have a quantity superior to the quantity in the '
                                                                    'sale line (%s)')%(self.sale_order_line_id.sec_uom_qty)}

        return res
    
    
    
class generate_called_sale_order(models.TransientModel):
    """ 
        Wizard to generate a called order from an open order
    """
    _name = 'generate.called.sale.order'
    _description = 'Wizard to generate a called order from an open order'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    date = fields.Date(string='Date', required=True)
    sale_id = fields.Many2one('sale.order', string='Sale order')
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)
    called_order_line_ids = fields.One2many('called.sale.order.line', 'called_order_id',  string='Sale order line')
    
    @api.model
    def default_get(self, fields_list):
        res = super(generate_called_sale_order, self).default_get(fields_list=fields_list)
        sale_id = self.env.context.get('active_id')
        if sale_id:
            list_line = []
            today = datetime.today()
            sale = self.env['sale.order'].browse(sale_id)
            if sale:
                date = datetime.strftime(today + relativedelta(days=sale.partner_id.sale_delivery_delay), '%Y-%m-%d')
                res['sale_id'] = sale_id
                res['date'] = date
                res['partner_id'] = sale.partner_id and sale.partner_id.id
                for line in sale.order_line_ids:
                    if line.remaining_called_qty > 0:
                        vals = {}
                        vals['sale_order_line_id'] = line.id
                        vals['product_id'] = line.product_id.id
                        vals['quantity'] = line.remaining_called_qty
                        vals['price'] = line.price_unit
                        list_line.append((0, 0, vals))
            
                res['called_order_line_ids'] = list_line
                
        return res
    
    
    @api.multi
    def generate_called_order(self):
        """
            Fonction permettant de créer une commande appelée à partir d'une commande ouverte
        """
        action_struc = {}
        new_sale = False
        #Génération du nom de la commande appelée
        sale = self.sale_id
        if sale:
            context2 = {'no_line_copy': True}
            context2.update(self.env.context)
            alpha_list = list(string.ascii_uppercase)
            seq_name = ''
            nb = 0
            if sale.called_order_ids:
                nb = len(sale.called_order_ids)
            
            x = nb / 26.0
            if x >= 1:
                nb -= (26 * int(x))
                x -= 1
                seq_name = '%s%s'%(alpha_list[int(x)], alpha_list[int(nb)]) 
            else:
                seq_name = alpha_list[nb]
                    
            #Copie de la vente pour récupérer toutes les informations
            name = "%s - %s"%(sale.name, seq_name)
            new_data = {
                        'open_order_id': sale.id,
                        'type': 'call',
                        'name': name,
                        'order_line_ids': [],
                        }
            new_sale = sale.with_context(context2).copy(new_data)
            vals2 = {'requested_date': self.date}
            
        if new_sale:
            #Copie des nouvelles lignes de vente
            for line in self.called_order_line_ids:
                vals = {
                        'sec_uom_qty': line.quantity,
                        'sale_order_id': new_sale.id
                        }
                vals.update(vals2)
                sale_line = line.sale_order_line_id and line.sale_order_line_id.copy(vals) or False
                if sale_line:
                    sale_line._onchange_sec_uom_qty(with_warning=False)
                    sale_line._onchange_uom_qty()
                    sale_line._onchange_uoi_qty()
                    sale_line.write({'price_unit': line.price})
            
            new_sale._onchange_order_line_ids()
            #On vérifie s'il reste encore des produits à réceptionner dans la commande ouverte
            #S'il n'y en a plus, on passe la commande ouverte en "Terminé"
            sale_doned = True
            for old_line in sale.order_line_ids:
                if old_line.remaining_called_qty > 0:
                    sale_doned = False
                    break
            
            if sale_doned:
                sale.find_and_exec_done_sale()
            
            action_dict = get_form_view(self, 'sale.sale_order_see_form')
            if action_dict and action_dict.get('id') and action_dict.get('type'):
                action = self.env[action_dict['type']].browse(action_dict['id'])
                action_struc = action.read()
                action_struc[0]['res_id'] = new_sale.id
                action_struc = action_struc[0]
                  
            return action_struc
        else:
            return  {'type': 'ir.actions.act_window_close'}
    
