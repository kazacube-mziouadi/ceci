# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
import base64


PROCEDURE = {
                'name': 'execute_method', 
                'label':  _('Execute method'),
                'params': [
                    {'name': 'model', 'label': _('Model name'), 'required': True, 'type': 'char', 'type_label': 'Char', 'help': 'Ex: sale.order.line'},
                    {'name': 'method', 'label': _('Method name'), 'required': True, 'type': 'char', 'type_label': 'Char', 'help': 'Ex: do_something'},
                    {'name': 'file_name', 'label': _('File name'), 'value': 'method_result.csv', 'required': False, 'type': 'char', 'type_label': 'Char', 'help': 'File name (only if method generate and return a file). Ex: myfile.csv\nParameters:\n\tOrigin:\n\t\t%ID\n\t\t%MODEL\n\tDates:\n\t\t%a: Locale’s abbreviated weekday name\n\t\t%A: Locale’s full weekday name\n\t\t%b: Locale’s abbreviated month name\n\t\t%B: Locale’s full month name\n\t\t%c: Locale’s appropriate date and time representation\n\t\t%d: Day of the month as a decimal number [01,31]\n\t\t%H: Hour (24-hour clock) as a decimal number [00,23]\n\t\t%I: Hour (12-hour clock) as a decimal number [01,12]\n\t\t%j: Day of the year as a decimal number [001,366]\n\t\t%m: Month as a decimal number [01,12]\n\t\t%M: Minute as a decimal number [00,59]\n\t\t%p: Locale’s equivalent of either AM or PM\n\t\t%S: Second as a decimal number [00,61]\n\t\t%U: Week number of the year (Sunday as the first day of the week) as a decimal number [00,53]. All days in a new year preceding the first Sunday are considered to be in week 0\n\t\t%w: Weekday as a decimal number [0(Sunday),6]\n\t\t%W: Week number of the year (Monday as the first day of the week) as a decimal number [00,53]. All days in a new year preceding the first Monday are considered to be in week 0\n\t\t%x: Locale’s appropriate date representation\n\t\t%X: Locale’s appropriate time representation\n\t\t%y: Year without century as a decimal number [00,99]\n\t\t%Y: Year with century as a decimal number\n\t\t%Z: Time zone name (no characters if no time zone exists)\n\t\t%%: A literal "%" character'},
                ]
             }


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
    

    def execute_method(self, procedure, edi_file, model_name, method_name, file_name='method_result.csv'):
        """
            Execution d'une méthode
        """
        context= self.env.context.copy()
        model = self.env[model_name]
        method = getattr(model, method_name)
        res = method()
        if res and file_name:
            if isinstance(res, str):
                if context.get('edi_history_id'):
                    file_name = self.compute_file_name('', file_name, context.get('object_id'), context.get('object_model'))
                    binary = base64.encodestring(res)
                    self.env['edi.transformation.file'].create({
                        'type': 'send',
                        'history_id': context['edi_history_id'],
                        'edi_file_fname': file_name.split('/')[-1],
                        'edi_file': binary,
                        'name': '%s [%s]%s'%(procedure.processing_id.name, procedure.sequence, procedure.name),
                        'src': 'Model: %s, ID: %s'%(context.get('object_model', ''), context.get('object_id', '')),
                        'file_date': fields.Datetime.now()
                    })
                    
            elif isinstance(res, (list, tuple)):
                i = 1
                for result in res:
                    if isinstance(result, str):
                        if len(res) > 1:
                            new_file_name = '%d_%s'%(i, file_name)
                            i += 1
                            
                        if context.get('edi_history_id'):
                            new_file_name = self.compute_file_name('', new_file_name, context.get('object_id'), context.get('object_model'))
                            binary = base64.encodestring(result)
                            self.env['edi.transformation.file'].create({
                                'type': 'send',
                                'history_id': context['edi_history_id'],
                                'edi_file_fname': new_file_name.split('/')[-1],
                                'edi_file': binary,
                                'name': '%s [%s]%s'%(procedure.processing_id.name, procedure.sequence, procedure.name),
                                'src': 'Model: %s, ID: %s'%(context.get('object_model', ''), context.get('object_id', '')),
                                'file_date': fields.Datetime.now()
                            })
        return True