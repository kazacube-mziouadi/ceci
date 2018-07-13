# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError

class replacement_date(models.TransientModel):
    """ 
        Replacement date
    """
    _name = 'replacement.date'
    _description = 'Replacement date'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Date(string='New date', required=True)

    @api.multi
    def action_change_date_value(self):
        """
            Fonction permettant de passer la nouvelle valeur de la date dans 
            les lignes de vente. Va aussi modifier la date du move lié à la
            ligne de vente
        """
        if self.name:
            context = self.env.context
            if context.get('active_id') and context.get('active_model') == "sale.order.line":
                sale_line = self.env['sale.order.line'].browse(context['active_id'])
                if sale_line:
                    sale_line.write({'confirmed_departure_date': self.name})
                    #On recherche et modifie le ou les moves liés à la ligne de vente
                    move_ids = self.env['stock.move'].search([('sale_line_id', '=', sale_line.id), ('state', 'not in', ('done', 'cancel'))])
                    for move in move_ids:
                        move.write({
                                    'date_expected': self.name, 
                                    'date': self.name,
                                    'priority_date': self.name
                                    })
                    
        return  {'type': 'ir.actions.act_window_close'}
    
