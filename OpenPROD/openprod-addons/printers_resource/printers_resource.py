# -*- coding: utf-8 -*-
from openerp import models, fields, api, report, _
from openerp.exceptions import except_orm, ValidationError

    
class mrp_resource(models.Model):
    _inherit = 'mrp.resource'
    
    @api.one
    def print_mrp_resource(self, printer):
        """
            Fonction associée au bouton de la ressource, permet d'imprimer une étiquette
            contenant les informations de la resource
        """
        printer_fields = ['context_printer_id', 'context_printer_medium_id', 'context_printer_small_id', 'context_printer_4_id', 'context_printer_5_id']
        printer = False 
        #On recherche le report associé aux adresses des partenaire
        object_model, object_id = self.env['ir.model.data'].get_object_reference('printers_resource', 'report_mrp_resource_barcode')
        printer_report = object_id and self.env['printers.report'].browse(object_id) or False
        if printer_report and printer_report.active_report:
            user = self.env.user
            #On recherche dans les préférences utilisateur l'imprimante correspondant au type d'imprimante
            printer_type = printer_report.printer_type_id
            printers_list = [user[printer_f] for printer_f in printer_fields]
            for user_printer in printers_list:
                if user_printer.type_id == printer_type:
                    printer = user_printer
                    break
                
            if not printer:
                raise except_orm(_('Error'), _('There is no printer of type %s in your user preference.') % (printer_type.name))
            else:
                report_id = printer_report.report_id.id
                if report_id:
                    #Envoie de la commande d'impression
                    printer.send_printer(report_id, [self.id])
                else:
                    raise except_orm(_('Error'), _('No active report found for this resource %s.') % (self.name))
        else:
            raise except_orm(_('Error'), _('No active report found for this resource %s.') % (self.name))
            
        return True
    
    
