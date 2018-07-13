# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError

class select_confirm_date(models.TransientModel):
    """ 
        Confirmed date for purchase and purchase line
    """
    _name = 'select.confirm.date'
    _description = 'Select confirmed date for purchase and purchase line'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Date(string='New date', required=True)

    @api.multi
    def action_select_confirmed_date(self):
        """
            Fonction permettant de sélectionner la date de confirmation de 
            la commande
        """
        if self.name:
            context = self.env.context
            if context.get('active_id') and context.get('active_model') == "purchase.order":
                purchase = self.env['purchase.order'].browse(context['active_id'])
                if purchase:
                    date = '%s 12:00:00'%(self.name)
                    purchase.change_confirmed_date(self.name)
                    
        return  {'type': 'ir.actions.act_window_close'}
    
