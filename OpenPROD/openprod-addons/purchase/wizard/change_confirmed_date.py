# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError

class replacement_confirmed_date(models.TransientModel):
    """ 
        Replacement confirmed date for purchase line
    """
    _name = 'replacement.confirmed.date'
    _description = 'Replacement confirmed date'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Date(string='New date', required=True)

    @api.multi
    def action_change_date_value(self):
        """
            Fonction permettant de passer la nouvelle valeur de la date dans 
            les lignes d'achat. Va aussi modifier la date du move lié à la
            ligne d'achat
        """
        if self.name:
            context = self.env.context
            if context.get('active_id') and context.get('active_model') == "purchase.order.line":
                purchase_line = self.env['purchase.order.line'].browse(context['active_id'])
                if purchase_line:
                    purchase_line.write({'confirmed_date': self.name})
                    #On recherche et modifie le ou les moves liés à la ligne d'achat
                    move_rcs = self.env['stock.move'].search([('purchase_line_id', '=', purchase_line.id), ('state', 'not in', ('done', 'cancel'))])
                    move_rcs.write({
                                    'date_expected': self.name, 
                                    'date': self.name,
                                    'priority_date': self.name
                                    })
                    
        return  {'type': 'ir.actions.act_window_close'}
    
