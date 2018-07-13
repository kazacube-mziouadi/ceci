# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
import csv
import base64


PROCEDURE = {'name': 'csv_from_sql', 
             'label':  _('CSV from SQL'),
             'params': [
                {'name': 'query', 'label': _('Query'), 'required': True, 'type': 'char', 'type_label': 'Char', 'help': 'SQL Query. To use the model and the id who start the procedure, you must write %object_id and %object_model'},
                {'name': 'delimiter', 'label': _('Delimiter'), 'value': ';', 'required': False, 'type': 'char', 'type_label': 'Char'},
                {'name': 'quotechar', 'label': _('Quotechar'), 'value': '"', 'required': False, 'type': 'char', 'type_label': 'Char'},
                {'name': 'escapechar', 'label': _('Escapechar'), 'value': '\\\\', 'required': False, 'type': 'char', 'type_label': 'Char'},
                {'name': 'header', 'label': _('Header'), 'value': 'SQL', 'required': True, 'type': 'char', 'type_label': 'Char', 'help': 'Possible values:\n\t- SQL\n\t- EMPTY\n\t- List of header values. Ex: ["col1", "col2"]'},
                {'name': 'end_line', 'label': _('End line'), 'value': '\\r\\n', 'required': True, 'type': 'char', 'type_label': 'Char', 'help': 'CRLF = \\r\\n'},
                {'name': 'file_path', 'label': _('File path'), 'value': '/tmp', 'required': True, 'type': 'char', 'type_label': 'Char', 'help': 'Absolute path and file name. Ex: /tmp'},
                {'name': 'file_name', 'label': _('File name'), 'value': 'csv_from_sql.csv', 'required': True, 'type': 'char', 'type_label': 'Char', 'help': 'File name. Ex: myfile.csv\nParameters:\n\tOrigin:\n\t\t%ID\n\t\t%MODEL\n\tDates:\n\t\t%a: Locale’s abbreviated weekday name\n\t\t%A: Locale’s full weekday name\n\t\t%b: Locale’s abbreviated month name\n\t\t%B: Locale’s full month name\n\t\t%c: Locale’s appropriate date and time representation\n\t\t%d: Day of the month as a decimal number [01,31]\n\t\t%H: Hour (24-hour clock) as a decimal number [00,23]\n\t\t%I: Hour (12-hour clock) as a decimal number [01,12]\n\t\t%j: Day of the year as a decimal number [001,366]\n\t\t%m: Month as a decimal number [01,12]\n\t\t%M: Minute as a decimal number [00,59]\n\t\t%p: Locale’s equivalent of either AM or PM\n\t\t%S: Second as a decimal number [00,61]\n\t\t%U: Week number of the year (Sunday as the first day of the week) as a decimal number [00,53]. All days in a new year preceding the first Sunday are considered to be in week 0\n\t\t%w: Weekday as a decimal number [0(Sunday),6]\n\t\t%W: Week number of the year (Monday as the first day of the week) as a decimal number [00,53]. All days in a new year preceding the first Monday are considered to be in week 0\n\t\t%x: Locale’s appropriate date representation\n\t\t%X: Locale’s appropriate time representation\n\t\t%y: Year without century as a decimal number [00,99]\n\t\t%Y: Year with century as a decimal number\n\t\t%Z: Time zone name (no characters if no time zone exists)\n\t\t%%: A literal "%" character'},
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


    def csv_from_sql(self, procedure, edi_file, query, delimiter=';', quotechar='"', escapechar='\\', header='SQL', lineterminator='\n', file_path='/tmp', file_name='csv_from_sql.csv'):
        """
            Export d'un SQL dans un CSV
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
        file_name = self.compute_file_name(file_path, file_name, record_id=context.get('object_id'), model=context.get('object_model'))
        if query_res:
            with open(file_name, 'w') as csvfile:
                if quotechar:
                    csvfile = csv.writer(csvfile, delimiter=delimiter, quotechar=quotechar, lineterminator=lineterminator)
                else:
                    csvfile = csv.writer(csvfile, delimiter=delimiter, quoting=csv.QUOTE_NONE, escapechar=escapechar, lineterminator=lineterminator)
                    
                if header == 'SQL':
                    csvfile.writerow([d[0] for d in self.env.cr.description])
                else:
                    try:
                        header = eval(header)
                        if isinstance(header, list) or isinstance(header, tuple):
                            csvfile.writerow(header)
                    except:
                        pass
                    
                for query_res_line in query_res:
                    csvfile.writerow([isinstance(v, unicode) and v.encode('utf-8') or v for v in query_res_line])
                    
            if context.get('edi_history_id'):
                binary = base64.encodestring(open(file_name, 'r').read())
                edi_file_obj.create({
                                      'type': 'send',
                                      'history_id': context['edi_history_id'],
                                      'edi_file_fname': file_name.split('/')[-1],
                                      'edi_file': binary,
                                      'name': '%s [%s]%s'%(procedure.processing_id.name, procedure.sequence, procedure.name),
                                      'src': 'Model: %s, ID: %s'%(context.get('object_model', ''), context.get('object_id', '')),
                                      'file_date': fields.Datetime.now()
                                    })
                    
        return True