# -*- coding: utf-8 -*-
from openerp.tools.translate import _
from openerp import models, fields, api
from openerp.exceptions import except_orm, ValidationError


class mrp_manufacturingorder(models.Model):
    _inherit = 'mrp.manufacturingorder'
    
    
    @api.multi
    def delete_mo_from_program(self):
        """
            Bouton qui lance la fonction permettant de supprimer l'OF sélectionné et tous ses fils
        """
        self.button_del_mo_and_son_mo()
        #On relance le calcul du PDP et on affiche sa vue
        context = self.env.context
        if context.get('product_id') and context.get('period_id') and context.get('production_schedule_id'):
            return self.env['change.program.line'].update_program(context['product_id'], context['period_id'], context['production_schedule_id'])
        
        return True
    
    
    @api.multi
    def confirm_mo_from_program(self):
        """
            Bouton qui lance la fonction permettant de confirmer l'OF
        """
        self.button_validate_forecast()
        #On relance le calcul du PDP et on affiche sa vue
        context = self.env.context
        if context.get('product_id') and context.get('period_id') and context.get('production_schedule_id'):
            return self.env['change.program.line'].update_program(context['product_id'], context['period_id'], context['production_schedule_id'])
            
        return True
    
    
    @api.multi
    def change_mo_quantity_from_program(self):
        """
            Bouton qui lance la fonction permettant de modifier la quantité de l'OF
        """
        #TODO voir plus tard si on autorise le changement de quantité, car ne propage pas 
        #le changement dans les OF fils pour l'instant
        context = self.env.context
        new_quantity = context.get('new_quantity') or 0
        if new_quantity > 0:
            #On commence par récupérer le premir OT de l'OF
            wo = self.env['mrp.workorder'].search([('mo_id', '=', self.id)], order='sequence asc', limit=1)
            if wo and wo.quantity != 0:
            #On appelle la fonction de changement de la quantité
                wo.change_qty(new_quantity / wo.quantity, True)
            
            #On relance le calcul du PDP et on affiche sa vue
            if context.get('product_id') and context.get('period_id') and context.get('production_schedule_id'):
                return self.env['change.program.line'].update_program(context['product_id'], context['period_id'], context['production_schedule_id'])
            
        else:
            raise except_orm(_('Error'), _('Please enter a quantity'))
            
        return True
    
