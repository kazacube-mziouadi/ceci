# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm
from openerp.addons.base_openprod.common import get_form_view

class stagger_purchase_delivery(models.TransientModel):
    """ 
        Wizard which allow to staggered the purchase delivery
    """
    _name = 'stagger.purchase.delivery'
    _description = 'Wizard which allow to staggered the purchase delivery'
    _rec_name = 'purchase_line_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    purchase_id = fields.Many2one('purchase.order', string='Purchase', required=False, ondelete='set null', 
                                  readonly=True)
    purchase_line_id = fields.Many2one('purchase.order.line', string='Purchase line', required=False, ondelete='set null', 
                                  readonly=True)
    new_date = fields.Date(string='New date', required=True)
    quantity = fields.Float(string='Quantity', default=0.0, required=True)
    uom_id = fields.Many2one('product.uom', string='UOM', required=False, ondelete='set null', readonly=True)
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(stagger_purchase_delivery, self).default_get(fields_list=fields_list)
        po_line_id = self.env.context.get('active_id')
        if po_line_id:
            po_line = self.env['purchase.order.line'].browse(po_line_id)
            res['purchase_line_id'] = po_line_id
            res['purchase_id'] = po_line.purchase_order_id.id
            res['uom_id'] = po_line.sec_uom_id.id
            
        return res
    
    
    @api.multi
    def action_stagger_purchase_delivery(self):
        """
            Fonction permettant de modifier le fournisseur d'un achat
        """
        for wizard in self:
            #On vérifie que la quantité entrée est inférieure à la quantité de la ligne 
            #d'achat 
            purchase_line = wizard.purchase_line_id
            price_unit = purchase_line.price_unit
            if wizard.quantity <= 0:
                raise except_orm(_("Error"), _('You must enter a quantity superior to 0'))
                
            if wizard.quantity >= purchase_line.sec_uom_qty:
                raise except_orm(_("Error"), _('You must enter a quantity inferior to the initial purchase '
                                               'line quantity'))
                
            #On récupère les valeurs entrées dans le wizard
            values = {'sec_uom_qty': wizard.quantity,
                      'expected_date': wizard.new_date}
            new_line = purchase_line.copy(values)
            new_line._onchange_sec_uom_qty(with_warning=False)
            new_line._onchange_uom_qty()
            new_line._onchange_uoi_qty()
            new_line.write({'price_unit': price_unit})
            #On décrémente la ligne initiale de la quantité de la nouvelle ligne (car celle-ci respecte forcément
            #le multiple et le minimum
            purchase_line.write({'sec_uom_qty': purchase_line.sec_uom_qty - wizard.quantity})
            purchase_line._onchange_sec_uom_qty(with_warning=False)
            purchase_line._onchange_uom_qty()
            purchase_line._onchange_uoi_qty()
            purchase_line.write({'price_unit': price_unit})
            #On retourne l'achat
            if wizard.purchase_id:
                action_dict = get_form_view(self, 'purchase.purchase_order_see_form')
                if action_dict and action_dict.get('id') and action_dict.get('type'):
                    action = self.env[action_dict['type']].browse(action_dict['id'])
                    action_struc = action.read()
                    action_struc[0]['res_id'] = wizard.purchase_id.id
                    action_struc = action_struc[0]
                      
                return action_struc
            else:
                return  {'type': 'ir.actions.act_window_close'}