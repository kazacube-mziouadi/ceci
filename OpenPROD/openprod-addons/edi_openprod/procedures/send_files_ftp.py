# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _


PROCEDURE = {'name': 'send_files_ftp', 
             'label':  _('Send files'),
             'params': [
                {'name': 'send_file_id', 'label': _('ID send file'), 'required': True, 'type': 'many2one', 'm2o_model': 'edi.transformation.send.file', 'type_label': 'Many2One'},
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
    

    def send_files_ftp(self, procedure, edi_file, send_file_id):
        """
            Envoie les fichiers contenus dans l'historique
        """
        context = self.env.context
        if procedure and procedure.processing_id:
            history_rcs = self.env['edi.transformation.history'].get_history(context.get('object_model'), 
                                                                             context.get('object_id', 0), 
                                                                             procedure.processing_id.id)
            if history_rcs:
                for edi_file in history_rcs.file_ids:
                    res = self.env['edi.transformation.send.file'].browse(send_file_id).send(edi_file)
                    if not res:
                        raise (_('Error'), _('Send file FTP error'))
                        
        return True