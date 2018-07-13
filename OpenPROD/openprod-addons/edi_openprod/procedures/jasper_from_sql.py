# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
import base64
from openerp import report


PROCEDURE = {'name': 'jasper_from_sql', 
             'label':  _('Jasper from SQL'),
             'params': [
                {'name': 'query', 'label': _('Query'), 'required': True, 'type': 'char', 'type_label': 'Char', 'help': 'SQL Query. To use the model and the id who start the procedure, you must write %object_id and %object_model'},
                {'name': 'jasper_id', 'label': _('Jasper document ID'), 'value': '', 'required': False, 'type': 'many2one', 'm2o_model': 'jasper.document', 'type_label': 'Many2One'},
                {'name': 'file_name', 'label': _('File name'), 'value': 'jasper_from_sql', 'required': True, 'type': 'char', 'type_label': 'Char', 'help': 'File name (/!\ File extension will be automatically provided by the report /!\). Ex: myfile\nParameters:\n\tOrigin:\n\t\t%ID\n\t\t%MODEL\n\tDates:\n\t\t%a: Locale’s abbreviated weekday name\n\t\t%A: Locale’s full weekday name\n\t\t%b: Locale’s abbreviated month name\n\t\t%B: Locale’s full month name\n\t\t%c: Locale’s appropriate date and time representation\n\t\t%d: Day of the month as a decimal number [01,31]\n\t\t%H: Hour (24-hour clock) as a decimal number [00,23]\n\t\t%I: Hour (12-hour clock) as a decimal number [01,12]\n\t\t%j: Day of the year as a decimal number [001,366]\n\t\t%m: Month as a decimal number [01,12]\n\t\t%M: Minute as a decimal number [00,59]\n\t\t%p: Locale’s equivalent of either AM or PM\n\t\t%S: Second as a decimal number [00,61]\n\t\t%U: Week number of the year (Sunday as the first day of the week) as a decimal number [00,53]. All days in a new year preceding the first Sunday are considered to be in week 0\n\t\t%w: Weekday as a decimal number [0(Sunday),6]\n\t\t%W: Week number of the year (Monday as the first day of the week) as a decimal number [00,53]. All days in a new year preceding the first Monday are considered to be in week 0\n\t\t%x: Locale’s appropriate date representation\n\t\t%X: Locale’s appropriate time representation\n\t\t%y: Year without century as a decimal number [00,99]\n\t\t%Y: Year with century as a decimal number\n\t\t%Z: Time zone name (no characters if no time zone exists)\n\t\t%%: A literal "%" character'},
#                 {'name': 'oerp_active_id', 'label': _('OERP Active ID'), 'value': '', 'required': True, 'type': 'char', 'type_label': 'Char', 'help': 'Provide %object_id to use the id who start the procedure'},
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
    
    
    def create_pdf(self, jasper_id, res_ids, user_id):
        ctx = self.env.context.copy()
        res = False
        jasper_obj = self.env['jasper.document']
        report_obj = self.env['ir.actions.report.xml']
        xml_report_to_print_id = jasper_obj.browse(jasper_id).read(['report_id'], load='_classic_write')[0]['report_id']
        if xml_report_to_print_id:
            # Retrieve data to generate the report
            report_data = report_obj.browse(xml_report_to_print_id).read(['model', 'report_name'])[0]
            datas = {'ids': res_ids, 'model': report_data['model']}
            if ctx and 'jasper' in ctx:
                datas['jasper'] = ctx['jasper']
            
            # Generate the file to print
            res = report.render_report(self.env.cr, user_id, res_ids, report_data['report_name'], datas, context=ctx), report_data['report_name']

        return res
    
    
    def jasper_from_sql(self, procedure, edi_file, query, jasper_id, file_name='jasper_from_sql'):
        """
            Export d'un SQL vers un Jasper
        """
        context = self.env.context.copy()
        try:
            jasper_id = int(jasper_id)
        except:
            jasper_id = False
            
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
            res_ids = [x[0] for x in query_res] 
        else:
            res_ids = []
        
        if context.get('edi_history_id') and res_ids:
            if procedure.edi_user_ids:
                user_rcs = self.env['res.users']
                for edi_user in procedure.edi_user_ids:
                    if edi_user.start_date <= fields.Date.today() and (not edi_user.end_date or edi_user.end_date >= fields.Date.today()):
                        user_rcs |= edi_user.user_id
                    
            else:
                user_rcs = edi_user.user_id
            
            for user in user_rcs:
                edi_file_obj = self.env['edi.transformation.file']
                file_name = self.compute_file_name('', file_name, context.get('object_id'), context.get('object_model'))
                (report_file, report_format), model_report = self.create_pdf(jasper_id, res_ids, user.id)
                binary = base64.b64encode(report_file)
                edi_file_obj.create({
                                     'type': 'send',
                                     'history_id': context['edi_history_id'],
                                     'edi_file_fname': '%s.%s'%(file_name, report_format.lower()),
                                     'edi_file': binary,
                                     'name': '%s [%s]%s'%(procedure.processing_id.name, procedure.sequence, procedure.name),
                                     'src': 'Model: %s, ID: %s'%(context.get('object_model', ''), context.get('object_id', '')),
                                     'file_date': fields.Datetime.now(),
                                     'user_id': user.id
                                    })
                    
        return True