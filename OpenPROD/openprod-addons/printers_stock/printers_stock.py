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


class stock_move(models.Model):
    _inherit = 'stock.move'
    
    @api.one
    def print_move_label(self):
        """
            Fonction associée au bouton du move, permet, pour un move choisi, d'imprimer
            les étiquettes qui lui sont liées
        """
        label_rs = self.env['stock.label']
        for move_label in self.move_label_ids:
            label_rs += move_label.label_id
            
        label_rs.do_print_label()
        return True
    
    
class stock_label_template(models.Model):
    _inherit = 'stock.label.template'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    report_id = fields.Many2one('ir.actions.report.xml', string='Report', required=True, ondelete='restrict')
    printer_type_id = fields.Many2one('printers.type', string='Printer type', required=True, ondelete='restrict')
    active_report = fields.Boolean(string='Active report', default=False)
    
    
    
class stock_label(models.Model):
    _inherit = 'stock.label'
    
    @api.one
    def print_one_label(self):
        """
            Fonction associée au bouton de l'étiquette, permet d'imprimer
            une seule étiquette
        """
        self.do_print_label()
        return True
    
    
    @api.multi
    def do_print_label(self, send_printer_list=None, send_printer_id=None):
        """ 
            Fonction permettant de retrouver l'imprimante pour chaque étiquettes et de lancer 
            l'impression
            :type self: stock.label
            :param send_printer_list: Dictionnaire contenant la liste des imprimantes de l'utilisateur
            :type send_printer_list: dict
            :param send_printer_id: id de l'imprimante envoyée
            :type send_printer_id: integer
            :return: True ou liste datas des étiquettes
            :rtype: bool
        """
        printer_list = {}
        printer_report_label_ids = {}
        user = self.env.user
        pdf_to_merge = []
        #On récupère les imprimantes entrées dans les préférences utilisateur
        if send_printer_list:
            printer_list = send_printer_list
        else:
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
        
        for label in self:
            printer_id = False
            key = ()
            #Pour chaque étiquette, si le template a la case "report actif" de cochée, on récupère les informations
            if label.template_id.active_report:
                printer_type = label.template_id.printer_type_id.id
                report_rs = label.template_id.report_id
                report_id = report_rs and report_rs.id or False
                #On sélectionne l'imprimante choisie par l'utilisateur
                for type, printer in printer_list.items():
                    if type == printer_type:
                        printer_id = printer
                        break
                    
                if not printer_id:
                    raise except_orm(_('Error'), _('No printer found for the label %s.') % (label.name))
                else:
                    key = (report_id, printer_id)
                
                if (not send_printer_id) or (send_printer_id != printer_id): 
                    if key in printer_report_label_ids:
                        printer_report_label_ids[key].append(label.id)
                    else:
                        printer_report_label_ids[key]= [label.id]
                elif send_printer_id and send_printer_id == printer_id:
                    (data, report_format) = report.render_report(self.env.cr, self.env.uid, [label.id], report_rs.report_name, {'model': 'stock.label'})
                    if report_format == 'PDF':
                        datas = StringIO()
                        datas.write(data)
                        pdf_to_merge.append(datas)
        
        #Lancement des impressions
        for k, v in printer_report_label_ids.items():
            #On fait des listes des étiquettes (par 120)
            hashed_label_ids = hash_list(v, 120)
            for l_ids in hashed_label_ids:
                k[1].send_printer(k[0], l_ids)
                self.env.cr.execute("""UPDATE stock_adv_label 
                                SET print_nb = print_nb + 1,
                                    print_user_id = %s,
                                    print_date = %s
                                  WHERE id in %s""", (self.env.cr.user.id, fields.Datetime.now(), tuple(l_ids),))
        
        if pdf_to_merge:
            return pdf_to_merge
        else:
            return True
    
    

class stock_picking(models.Model):
    _inherit = 'stock.picking'
    
    @api.one
    def print_picking(self):
        """
            Fonction associée au bouton du picking, permet d'imprimer
            des pickings
        """
        self.do_print_picking()
        return True
      
      
    def do_print_picking(self):
        """ 
            Fonction permettant d'imprimer le picking ainsi que les controles et plans liés aux produits
            du picking et les étiquettes liées aux moves (en fonction des booléens cochés)
        """
        super(stock_picking, self).do_print_picking()
        printer_list = {}
        printer_report_ids = {}
        data_obj = self.env['ir.model.data']
        report_object = self.env['printers.report']
        plans_obj = self.env['stock.quality.control']
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
        
        for picking in self:
            report_id = False
            printer_id = False
            object_model = False
            product_plans_jasper_type = ''
            key = ()
            pdf_to_merge = []
            #On regarde si au moins l'une des 3 cases est cochée, sinon on envoie un message d'erreur
            if not picking.print_picking_report and not picking.print_control and not picking.print_label:
                raise except_orm(_('Error'), _('You need to check at least one case in the printing part for the picking '
                                               '%s (information tab).') % (picking.name))
                
            #Pour chaque picking, on recherche le rapport associé en fonction de son type
            #et de l'option avec ou sans prix
            if picking.type == 'in':
                product_plans_jasper_type = 'jasper_receipt'
                object_model, object_id = data_obj.get_object_reference('printers_stock', 'report_receipt_order')
            elif picking.type == 'out':
                product_plans_jasper_type = 'jasper_delivery'
                if picking.report_type == 'with_price':
                    object_model, object_id = data_obj.get_object_reference('printers_stock', 'report_delivery_order_with_price')
                elif picking.report_type == 'without_price' or not picking.report_type:
                    object_model, object_id = data_obj.get_object_reference('printers_stock', 'report_delivery_order_without_price')
            
            #Lorsque la case d'impression du rapport du picking est cochée
            if picking.print_picking_report:
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
                            raise except_orm(_('Error'), _('No printer found for the picking %s.') % (picking.name))
                        else:
                            key = (report_id, printer_id)
                        
                        if key in printer_report_ids:
                            printer_report_ids[key]['picking'].append(picking.id)
                        else:
                            printer_report_ids[key]= {'picking': [picking.id]}
                
#                 if not report_id:
#                     raise except_orm(_('Error'), _('No active report found for this picking %s.') % (picking.name))
            
            #Lorsque la case d'impression des plans et controles est cochée
            if picking.print_control:
                for document in picking.quality_control_ids:
                    datas = StringIO()
                    datas.write(base64.decodestring(document.attachment))
                    pdf_to_merge.append(datas)
                        
                #On va chercher tous les controles et plans éventuels ramenés 
                product_list = [x.product_id.id for x in picking.move_ids]
                plans_list = plans_obj.search([('product_id', 'in', product_list)])
                for plan in plans_list:
                    #S'il possède un report jasper, on crée le report, on vérifie qu'il soit bien sous format PDF et on l'ajoute
                    #aux PDF à merger
                    if plan.type == product_plans_jasper_type and plan.report_id:
                        (data, report_format) = report.render_report(self.env.cr, self.env.uid, [plan.id], plan.report_id.report_name, {'model': 'stock.quality.control'})
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
            
            #Si la case "Imprimer les étiquettes" est cochée dans le picking, on lance l'impression de toutes les étiquettes
            if picking.print_label:
                #On récupère toutes les étiquettes de tous les moves du picking
                label_rs = self.env['stock.label']
                for move in picking.move_ids:
                    for move_label in move.move_label_ids:
                        label_rs += move_label.label_id
                
                #Si on a un report, ou déjà un pdf, on envoie l'id de l'imprimante à la méthode d'impression des étiquettes
                #Si pour une ou plusieurs étiquettes on trouve la même imprimante, on va merger le tout afin de ne créer qu'un seul
                #PDF. Sinon, on lance directement l'impression des étiquettes
                if report_id or pdf_to_merge:
                    label_result = label_rs.do_print_label(printer_list, printer_id)
                    if isinstance(label_result, list):
                        pdf_to_merge += label_result
                        
                else:
                    label_rs.do_print_label(send_printer_list=printer_list, send_printer_id=False)
                    
                
            if printer_report_ids and pdf_to_merge:
                printer_report_ids[key]['pdf_to_merge'] = pdf_to_merge
            #Si on a pas à imprimer le picking mais que l'on doit imprimer les plans et les controles,
            #on va aller chercher les PDF à imprimer.
            elif not printer_report_ids and pdf_to_merge:
                fo_pdf = StringIO()
                ret = PdfFileWriter()
                for current_pdf in pdf_to_merge:
                    current_pdf.seek(0)
                    tmp_pdf = PdfFileReader(current_pdf)
                    for page in range(tmp_pdf.getNumPages()):
                        ret.addPage(tmp_pdf.getPage(page))
            
                ret.write(fo_pdf)
                printer_id.print_raw_data(fo_pdf.getvalue())
        
        #Lancement des impressions
        for k, v in printer_report_ids.items():
            k[1].send_printer(k[0], v['picking'], v.get('pdf_to_merge', []))
                    
        return True
    
    
    @api.model
    def _report_type_get(self):
        return [
                ('with_price', _('With price')),
                ('without_price', _('Without price')),
                       ]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    print_picking_report = fields.Boolean(string='Print picking', default=False)
    print_control = fields.Boolean(string='Print control and plans', default=False)
    print_label = fields.Boolean(string='Print labels', default=False)
    report_type = fields.Selection('_report_type_get', default='without_price')
    
    
