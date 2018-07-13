# -*- coding: utf-8 -*-
from openerp import models, fields, api, report, _
from openerp.exceptions import except_orm, ValidationError
from openerp.addons.base_openprod.common import get_form_view, hash_list
from pyPdf import PdfFileWriter, PdfFileReader

import base64

# If cStringIO is available, we use it
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO  # noqa


class mrp_workorder(models.Model):
    _inherit = 'mrp.workorder'
    
    @api.one
    def print_wo(self):
        """
            Fonction associée au bouton du picking, permet d'imprimer
            des pickings
        """
        super(mrp_workorder, self).print_wo()
        self.do_print_picking()
        return True
      
      
    def do_print_wo(self, print_plan=False, print_plan_mo=False):
        """ 
            Fonction permettant d'imprimer le work order ainsi que les plans liés à la ligne de
            gamme du work order
        """
        super(mrp_workorder, self).do_print_wo()
        printer_list = {}
        printer_report_ids = {}
        data_obj = self.env['ir.model.data']
        report_object = self.env['printers.report']
        user = self.env.user
        #On récupère les imprimantes entrées dans les préférences utilisateur
        if user.context_printer_id:
            user.context_printer_id.type_id and printer_list.update({user.context_printer_id.type_id.id:user.context_printer_id})
              
        if user.context_printer_medium_id:
            user.context_printer_medium_id.type_id and printer_list.update({user.context_printer_medium_id.type_id.id:user.context_printer_medium_id})
              
        if user.context_printer_small_id:
            user.context_printer_small_id.type_id and printer_list.update({user.context_printer_small_id.type_id.id:user.context_printer_small_id})
              
        if user.context_printer_4_id:
            user.context_printer_4_id.type_id and printer_list.update({user.context_printer_4_id.type_id.id:user.context_printer_4_id})
              
        if user.context_printer_5_id:
            user.context_printer_5_id.type_id and printer_list.update({user.context_printer_5_id.type_id.id:user.context_printer_5_id})
        
        for wo in self:
            report_id = False
            printer_id = False
            object_model = False
            key = ()
            pdf_to_merge = []
            #On recherche le rapport associé au work order
            object_model, object_id = data_obj.get_object_reference('printers_mrp', 'report_work_order')
            #On récupère le report du work order, en vérifiant qu'il est actif. 
            if object_model and object_model == 'printers.report':
                printer_report = report_object.browse(object_id)
                if printer_report.active_report == True:
                    printer_type = printer_report.printer_type_id.id
                    report_id = printer_report.report_id.id
                    #On sélectionne l'imprimante choisie par l'utilisateur
                    for type, printer in printer_list.items():
                        if type == printer_type:
                            printer_id = printer
                            break
                    
                    if not printer_id:
                        raise except_orm(_('Error'), _('No printer found for the work order %s.') % (wo.name))
                    else:
                        key = (report_id, printer_id)
                    
                    if key in printer_report_ids:
                        printer_report_ids[key]['work_order'].append(wo.id)
                    else:
                        printer_report_ids[key]= {'work_order': [wo.id]}
            
            #Si on ne récupère aucun report, on envoie un message d'erreur
            if not report_id:
                raise except_orm(_('Error'), _('No active report found for this work order %s.') % (wo.name))
            
            # Impression des plans dans les Ots
            if print_plan and wo.rl_document_ids:
                for document in wo.rl_document_ids:
                    if document.attachment:
                        datas = StringIO()
                        datas.write(base64.decodestring(document.attachment))
                        pdf_to_merge.append(datas)
            
            # Impression des plans dans les OFs
            if print_plan_mo and wo.mo_id.internal_plan_ids:
                for document in wo.mo_id.internal_plan_ids:
                    if document.attachment:
                        datas = StringIO()
                        datas.write(base64.decodestring(document.attachment))
                        pdf_to_merge.append(datas)
                
                #Gestion des documents jasper
                product_id = wo.mo_id.product_id.id
                printed_doc_list = self.env['stock.quality.control'].search([('product_id', '=', product_id), ('type', '=', 'jasper_production'),
                                                                        ('report_id', '!=', False)])
                for printed_doc in printed_doc_list:
                    (data, report_format) = report.render_report(self.env.cr, self.env.uid, [printed_doc.id], printed_doc.report_id.report_name, {'model': 'stock.quality.control'})
                    if report_format == 'PDF':
                        datas = StringIO()
                        datas.write(data)
                        pdf_to_merge.append(datas)
            
            #Si on a récupéré aucune imprimante, on récupère la première de la liste des préférences des
            #utilisateurs
            if not printer_id:
                for type, printer in printer_list.items():
                    printer_id = printer
                    break
                    
                if not printer_id:
                    raise except_orm(_('Error'), _('No printer found in your preference'))
            
            if printer_report_ids and pdf_to_merge:
                printer_report_ids[key]['pdf_to_merge'] = pdf_to_merge
        
        #Lancement des impressions
        for k, v in printer_report_ids.items():
            k[1].send_printer(k[0], v['work_order'], v.get('pdf_to_merge', []))
                    
        return True