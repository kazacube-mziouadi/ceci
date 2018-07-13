# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _


PROCEDURE = {'name': 'clear_file_list', 
             'label':  _('Clear file list'),
             'params': []} 


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
    

    def clear_file_list(self, procedure, edi_file):
        """
            Vide la liste des fichiers de l'historique
        """
        context = self.env.context.copy()
        history_rcs = self.env['edi.transformation.history'].get_history(
                                                                         context.get('object_model'), 
                                                                         context.get('object_id', 0), 
                                                                         procedure.processing_id.id, 
                                                                         )
        if history_rcs and history_rcs.file_ids:
            history_rcs.file_ids.unlink()

        return True