# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.addons.base_openprod.common import get_form_view
from openerp.addons.base_openprod import utils
from datetime import datetime
from dateutil.relativedelta import relativedelta
import string

class called_order_line(models.TransientModel):
    """ 
        Purchase called order lines
    """
    _name = 'called.order.line'
    _description = 'Purchase called order lines'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    called_order_id = fields.Many2one('generate.called.order', string='Purchase order', ondelete='set null')
    product_id = fields.Many2one('product.product', string='Product', readonly=True, ondelete='set null')
    quantity = fields.Float(string='Quantity', default=0.0, required=False)
    price = fields.Float(string='Price', default=0.0, required=False)
    purchase_order_line_id = fields.Many2one('purchase.order.line', string='Purchase order line', required=False, ondelete='set null')
    
    @api.onchange('quantity', 'purchase_order_line_id')
    def _onchange_product_quantity(self):
        """
            Au changement de la quantité achetée, on vérifie que cette quantité soit inférieure
            ou égale à la quantité de la ligne d'achat, sinon on envoi un waring
        """
        res = {'warning': {}}
        if self.purchase_order_line_id:
            if self.quantity > self.purchase_order_line_id.sec_uom_qty:
                res['warning'] = {'title':_('Warning'), 'message':_('You have a quantity superior to the quantity in the '
                                                                    'purchase line (%s)')%(self.purchase_order_line_id.sec_uom_qty)}

        return res
    
    
    
class generate_called_order(models.TransientModel):
    """ 
        Wizard to generate a called order from an open order
    """
    _name = 'generate.called.order'
    _description = 'Wizard to generate a called order from an open order'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    date = fields.Date(string='Date', required=True)
    purchase_id = fields.Many2one('purchase.order', string='Purchase order')
    partner_id = fields.Many2one('res.partner', string='Supplier', readonly=True)
    called_order_line_ids = fields.One2many('called.order.line', 'called_order_id',  string='Purchase order line')
    
    @api.model
    def default_get(self, fields_list):
        res = super(generate_called_order, self).default_get(fields_list=fields_list)
        purchase_id = self.env.context.get('active_id')
        if purchase_id:
            list_line = []
            today = datetime.today()
            purchase = self.env['purchase.order'].browse(purchase_id)
            if purchase:
                date = datetime.strftime(today + relativedelta(days=purchase.partner_id.purchase_delivery_delay), '%Y-%m-%d')
                res['purchase_id'] = purchase_id
                res['date'] = date
                res['partner_id'] = purchase.partner_id and purchase.partner_id.id
                for line in purchase.purchase_order_line_ids:
                    if line.remaining_called_qty > 0:
                        vals = {}
                        vals['purchase_order_line_id'] = line.id
                        vals['product_id'] = line.product_id.id
                        vals['quantity'] = line.remaining_called_qty
                        vals['price'] = line.price_unit
                        list_line.append((0, 0, vals))
            
                res['called_order_line_ids'] = list_line
                
        return res
    
    
    @api.multi
    def generate_called_order(self):
        """
            Fonction permettant de créer une commande appellée à partir d'une commande ouverte
        """
        action_struc = {}
        new_purchase = False
        #Génération du nom de la commande appelée
        if self.purchase_id:
            context2 = {'no_line_copy': True}
            context2.update(self.env.context)
            alpha_list = list(string.ascii_uppercase)
            seq_name = ''
            purchase = self.purchase_id
            nb = 0
            if purchase.called_order_ids:
                nb = len(purchase.called_order_ids)
            
            x = nb / 26.0
            if x >= 1:
                nb -= (26 * int(x))
                x -= 1
                seq_name = '%s%s'%(alpha_list[int(x)], alpha_list[int(nb)]) 
            else:
                seq_name = alpha_list[nb]
            
            #Copie de l'achat pour récupérer toutes les informations
            name = "%s - %s"%(purchase.name, seq_name)
            new_data = {
                        'open_order_id': purchase.id,
                        'purchase_type': 'call',
                        'name': name,
                        'purchase_order_line_ids': [],
                        }
            new_purchase = purchase.with_context(context2).copy(new_data)
            vals2 = {'expected_date': self.date}
            
        if new_purchase:
            #Copie des nouvelles lignes d'achat
            for line in self.called_order_line_ids:
                vals = {
                        'sec_uom_qty': line.quantity,
                        'purchase_order_id': new_purchase.id
                        }
                vals.update(vals2)
                purchase_line = line.purchase_order_line_id and line.purchase_order_line_id.copy(vals) or False
                if purchase_line:
                    purchase_line._onchange_sec_uom_qty(with_warning=False)
                    purchase_line._onchange_uom_qty()
                    purchase_line._onchange_uoi_qty()
                    purchase_line.write({'price_unit': line.price})
            
            new_purchase._onchange_purchase_order_line_ids()
            #On vérifie s'il reste encore des produits à réceptionner dans la commande ouverte
            #S'il n'y en a plus, on passe la commande ouverte en "Terminé"
            purchase_doned = True
            for old_line in purchase.purchase_order_line_ids:
                if old_line.remaining_called_qty > 0:
                    purchase_doned = False
                    break
            
            if purchase_doned:
                purchase.find_and_exec_done_purchase()
            
            action_dict = get_form_view(self, 'purchase.purchase_order_see_form')
            if action_dict and action_dict.get('id') and action_dict.get('type'):
                action = self.env[action_dict['type']].browse(action_dict['id'])
                action_struc = action.read()
                action_struc[0]['res_id'] = new_purchase.id
                action_struc = action_struc[0]
                  
            return action_struc
        else:
            return  {'type': 'ir.actions.act_window_close'}
    
