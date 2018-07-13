# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
import base64

PROCEDURE = {'name': 'txt_from_sql', 
             'label':  _('TXT from SQL'),
             'params': [
                {'name': 'query', 'label': _('Query'), 'required': True, 'type': 'char', 'type_label': 'Char', 'help': 'SQL Query. To use the model and the id who start the procedure, you must write %object_id and %object_model'},
                {'name': 'end_line', 'label': _('End line'), 'value': '\\r\\n', 'required': True, 'type': 'char', 'type_label': 'Char', 'help': 'CRLF = \\r\\n'},
                {'name': 'file_path', 'label': _('File path'), 'value': '/tmp', 'required': True, 'type': 'char', 'type_label': 'Char', 'help': 'Absolute path and file name. Ex: /tmp'},
                {'name': 'file_name', 'label': _('File name'), 'value': 'txt_from_sql.txt', 'required': True, 'type': 'char', 'type_label': 'Char', 'help': 'File name. Ex: myfile.txt\nParameters:\n\tOrigin:\n\t\t%ID\n\t\t%MODEL\n\t\t%NUM: iteration number\n\tDates:\n\t\t%a: Locale’s abbreviated weekday name\n\t\t%A: Locale’s full weekday name\n\t\t%b: Locale’s abbreviated month name\n\t\t%B: Locale’s full month name\n\t\t%c: Locale’s appropriate date and time representation\n\t\t%d: Day of the month as a decimal number [01,31]\n\t\t%H: Hour (24-hour clock) as a decimal number [00,23]\n\t\t%I: Hour (12-hour clock) as a decimal number [01,12]\n\t\t%j: Day of the year as a decimal number [001,366]\n\t\t%m: Month as a decimal number [01,12]\n\t\t%M: Minute as a decimal number [00,59]\n\t\t%p: Locale’s equivalent of either AM or PM\n\t\t%S: Second as a decimal number [00,61]\n\t\t%U: Week number of the year (Sunday as the first day of the week) as a decimal number [00,53]. All days in a new year preceding the first Sunday are considered to be in week 0\n\t\t%w: Weekday as a decimal number [0(Sunday),6]\n\t\t%W: Week number of the year (Monday as the first day of the week) as a decimal number [00,53]. All days in a new year preceding the first Monday are considered to be in week 0\n\t\t%x: Locale’s appropriate date representation\n\t\t%X: Locale’s appropriate time representation\n\t\t%y: Year without century as a decimal number [00,99]\n\t\t%Y: Year with century as a decimal number\n\t\t%Z: Time zone name (no characters if no time zone exists)\n\t\t%%: A literal "%" character'},
                {'name': 'split_file', 'label': _('Split file'), 'value': '0', 'required': True, 'type': 'boolean', 'type_label': 'Boolean', 'help': 'If 1: creation of one file per line of SQL result (Add %NUM in the file name to add the iteration number)'},
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
    

    def txt_from_sql(self, procedure, edi_file, query, end_line='\r\n', file_path='/tmp', file_name='txt_from_sql.txt', split_file=False):
        """
            Export d'un SQL dans un TXT
        """
        context = self.env.context.copy()
        if '%object_id' in query:
            if 'object_id' in context:
                query = query.replace('%object_id', str(context['object_id']))
 
        if '%object_model' in query:
            if 'object_model' in context:
                query = query.replace('%object_model', context['object_model'].replace('.', '_'))
                 
        edi_file_obj = self.env['edi.transformation.file']
        self.env.cr.execute(query)
        query_res = self.env.cr.fetchall()
        if query_res:
            if split_file:
                i  = 0
                for query_res_line in query_res:
                    f_name = self.compute_file_name(file_path, file_name, context.get('object_id'), context.get('object_model'), iteration=i)
                    i += 1
                    with open(f_name, 'w') as f:
                        v = query_res_line[0]
                        f.write('%s%s'%(isinstance(v, unicode) and v.encode('utf-8') or v, end_line))
                        
                    if context.get('edi_history_id'):
                        binary = base64.encodestring(open(f_name, 'r').read())
                        edi_file_obj.create({
                                              'type': 'send',
                                              'history_id': context['edi_history_id'],
                                              'edi_file_fname': f_name.split('/')[-1],
                                              'edi_file': binary,
                                              'name': '%s [%s]%s'%(procedure.processing_id.name, procedure.sequence, procedure.name),
                                              'src': 'Model: %s, ID: %s'%(context.get('object_model', ''), context.get('object_id', '')),
                                              'file_date': fields.Datetime.now()
                                            })
            else:
                f_name = self.compute_file_name(file_path, file_name, context.get('object_id'), context.get('object_model'))
                with open(f_name, 'w') as f:
                    for query_res_line in query_res:
                        v = query_res_line[0]
                        f.write('%s%s'%(isinstance(v, unicode) and v.encode('utf-8') or v, end_line))
                         
                if context.get('edi_history_id'):
                    binary = base64.encodestring(open(f_name, 'r').read())
                    edi_file_obj.create({
                                          'type': 'send',
                                          'history_id': context['edi_history_id'],
                                          'edi_file_fname': f_name.split('/')[-1],
                                          'edi_file': binary,
                                          'name': '%s [%s]%s'%(procedure.processing_id.name, procedure.sequence, procedure.name),
                                          'src': 'Model: %s, ID: %s'%(context.get('object_model', ''), context.get('object_id', '')),
                                          'file_date': fields.Datetime.now()
                                        })
        return True