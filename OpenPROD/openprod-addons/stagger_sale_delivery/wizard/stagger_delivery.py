# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm
from openerp.addons.base_openprod.common import get_form_view

class stagger_sale_delivery(models.TransientModel):
    """ 
        Wizard which allow to staggered the sale delivery
    """
    _name = 'stagger.sale.delivery'
    _description = 'Wizard which allow to staggered the sale delivery'
    _rec_name = 'sale_line_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    sale_id = fields.Many2one('sale.order', string='Sale', required=False, ondelete='set null', 
                                  readonly=True)
    sale_line_id = fields.Many2one('sale.order.line', string='Sale line', required=False, ondelete='set null', 
                                  readonly=True)
    new_date = fields.Date(string='New date', required=True)
    quantity = fields.Float(string='Quantity', default=0.0, required=True)
    uom_id = fields.Many2one('product.uom', string='UOM', required=False, ondelete='set null', readonly=True)
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(stagger_sale_delivery, self).default_get(fields_list=fields_list)
        so_line_id = self.env.context.get('active_id')
        if so_line_id:
            so_line = self.env['sale.order.line'].browse(so_line_id)
            res['sale_line_id'] = so_line_id
            res['sale_id'] = so_line.sale_order_id.id
            res['uom_id'] = so_line.sec_uom_id.id
            
        return res
    
    
    @api.multi
    def action_stagger_sale_delivery(self):
        """
            Fonction permettant d'échelonner la livraison d'une ligne de vente
        """
        for wizard in self:
            #On vérifie que la quantité entrée est inférieure à la quantité de la ligne 
            #de vente
            sale_line = wizard.sale_line_id
            price_unit = sale_line.price_unit
            if wizard.quantity <= 0:
                raise except_orm(_("Error"), _('You must enter a quantity superior to 0'))
                
            if wizard.quantity >= sale_line.sec_uom_qty:
                raise except_orm(_("Error"), _('You must enter a quantity inferior to the initial sale '
                                               'line quantity'))
                
            #On récupère les valeurs entrées dans le wizard
            values = {'sec_uom_qty': wizard.quantity,
                      'requested_date': wizard.new_date}
            new_line = sale_line.copy(values)
            new_line._onchange_sec_uom_qty(with_warning=False)
            new_line._onchange_uom_qty()
            new_line._onchange_uoi_qty()
            new_line.write({'price_unit': price_unit})
            #On décrémente la ligne initiale de la quantité de la nouvelle ligne (car celle-ci respecte forcément
            #le multiple et le minimum)
            sale_line.write({'sec_uom_qty': sale_line.sec_uom_qty - wizard.quantity})
            sale_line._onchange_sec_uom_qty(with_warning=False)
            sale_line._onchange_uom_qty()
            sale_line._onchange_uoi_qty()
            sale_line.write({'price_unit': price_unit})
            #On retourne la vente
            if wizard.sale_id:
                action_dict = get_form_view(self, 'sale.sale_order_see_form')
                if action_dict and action_dict.get('id') and action_dict.get('type'):
                    action = self.env[action_dict['type']].browse(action_dict['id'])
                    action_struc = action.read()
                    action_struc[0]['res_id'] = wizard.sale_id.id
                    action_struc = action_struc[0]
                      
                return action_struc
            else:
                return  {'type': 'ir.actions.act_window_close'}