# -*- coding: utf-8 -*-
from openerp import models, fields, api, report, _
from openerp.exceptions import except_orm
from openerp.addons.base_openprod.common import get_form_view


class wizard_print_partner_address(models.Model):
    """
        Wizard to print the partner address
    """
    _name = 'wizard.print.partner.address'
    _description = 'Wizard to print the partner address'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=False, default='/')
    printer_id = fields.Many2one('printers.list', string='Printer', required=True, ondelete='cascade')
    
    @api.multi
    def action_print_address(self):
        """
            Fonction permettant de lancer l'impression de l'adresse du partenaire
        """
        if self.printer_id:
            context = self.env.context
            if context.get('active_ids') and context.get('active_model') == "res.partner":
                for partner in self.env['res.partner'].browse(context['active_ids']):
                    partner.print_partner_address(self.printer_id)
                    
        return  {'type': 'ir.actions.act_window_close'}