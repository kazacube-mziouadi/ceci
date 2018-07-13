# -*- coding: utf-8 -*-
from openerp import models, fields, api, report, _
from openerp.exceptions import except_orm
from openerp.addons.base_openprod.common import get_form_view


class res_partner(models.Model):
    _inherit = 'res.partner'
    
    @api.one
    def print_partner_address(self, printer):
        """
            Fonction associée au bouton du partenaire, permet d'imprimer une étiquette
            contenant les informations du partenaire
        """
        if printer:
            #On recherche le report associé aux adresses des partenaire
            object_model, object_id = self.env['ir.model.data'].get_object_reference('printers_res_partner', 'report_address_partner')
            printer_report = object_id and self.env['printers.report'].browse(object_id) or False
            if printer_report and printer_report.active_report:
                report_id = printer_report.report_id.id
                if report_id:
                    #Envoie de la commande d'impression
                    printer.send_printer(report_id, [self.id])
                else:
                    raise except_orm(_('Error'), _('No active report found for this partner %s.') % (self.name))
            else:
                raise except_orm(_('Error'), _('No active report found for this partner %s.') % (self.name))
            
        return True

