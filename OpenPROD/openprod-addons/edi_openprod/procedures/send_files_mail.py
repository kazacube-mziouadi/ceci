# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _



PROCEDURE = {'name': 'send_files_mail', 
             'label':  _('Send mail'),
             'params': [
                {'name': 'template_mail_id', 'label': _('Template mail ID'), 'required': False, 'type': 'many2one', 'm2o_model': 'mail.template', 'type_label': 'Many2One'},
                {'name': 'query', 'label': _('Query'), 'required': False, 'type': 'char', 'type_label': 'Char', 'help': 'SQL Query. To use the model and the id who start the procedure, you must write %object_id and %object_model'},
                        ]} 


class edi_transformation_procedure(models.Model):
    """ 
        EDI Transformation procedure
    """
    _inherit = 'edi.transformation.procedure'
    
    
    @api.model
    def _method_get(self):
        res = super(edi_transformation_procedure, self)._method_get()
        if PROCEDURE['name'] not in [t[0] for t in res]:
            res.append((PROCEDURE['name'], PROCEDURE['label']))
            
        return res


    def update_params(self, method):
        """
            Ajout des paramètres pour qu'ils soit remplis par le onchange de la méthode
        """
        res = super(edi_transformation_procedure, self).update_params(method)
        if method == PROCEDURE['name']:
            res.extend([[0, False, param] for param in PROCEDURE['params']])
            
        return res
    
    
    def send_files_mail(self, procedure, edi_file, template_mail_id, query):
        """
            Envoie les fichiers contenus dans l'historique
        """
        context = self.env.context.copy()
        if procedure and procedure.processing_id:
            if procedure.edi_user_ids:
                user_mail_rcs = []
                for edi_user in procedure.edi_user_ids:
                    if edi_user.start_date <= fields.Date.today() and (not edi_user.end_date or edi_user.end_date >= fields.Date.today()):
                        user_mail_rcs.append((edi_user.user_id, edi_user.mail))
                    
            else:
                user_mail_rcs = [(self.env.user, '')]      
                    
            for user_mail in user_mail_rcs:     
                if query:
                    if '%object_id' in query:
                        if 'object_id' in context:
                            query = query.replace('%object_id', str(context['object_id']))
            
                    if '%object_model' in query:
                        if 'object_model' in context:
                            query = query.replace('%object_model', context['object_model'].replace('.', '_'))
            
                
                    self.env.cr.execute(query)
                    query_res = self.env.cr.fetchone()
                    if query_res:
                        res_id = query_res[0] 
                    else:
                        res_id = procedure.id
                        
                elif context.get('object_id', None):
                    res_id = context['object_id']
                else:
                    res_id = procedure.id
                   
                attachment_obj = self.env['ir.attachment']
                attachment_ids = self.env['ir.attachment']
                msg_rcs = self.env['mail.template'].browse(template_mail_id).send_mail(res_id, force_send=False, return_browse=True)
                if user_mail[1]:
                    msg_rcs.write({'email_to': user_mail[1]})
                
                history_rcs = self.env['edi.transformation.history'].get_history(context.get('object_model'), 
                                                                                  context.get('object_id', 0), 
                                                                                  procedure.processing_id.id)
                for edi_file in history_rcs.file_ids:
                    if not procedure.is_doc_by_user or (procedure.is_doc_by_user and edi_file.user_id == user_mail[0]):
                        attachment_ids |= attachment_obj.search([
                                                                 ('res_model', '=', edi_file._name), 
                                                                 ('res_id', '=', edi_file.id), 
                                                                 ('type', '=', 'binary'),
                                                               ])
                
                if attachment_ids:
                    msg_rcs.write({'attachment_ids': [(6, 0, attachment_ids.ids)]})
                    
                msg_rcs.send()

        return True