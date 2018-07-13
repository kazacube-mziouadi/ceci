# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
import base64
import xlrd
from xlwt import Workbook, XFStyle
from xlutils.copy import copy
import distutils

PROCEDURE = {'name': 'xls_from_sql', 
             'label':  _('XLS from SQL'),
             'params': [
                {'name': 'query', 'label': _('Query'), 'required': True, 'type': 'char', 'type_label': 'Char', 'help': 'SQL Query. To use the model and the id who start the procedure, you must write %object_id and %object_model'},
                {'name': 'sheet', 'label': _('Sheet'), 'value': '0', 'required': True, 'type': 'int', 'type_label': 'Integer', 'help': '0 is the first sheet'},
                {'name': 'column', 'label': _('Column'), 'value': '0', 'required': True, 'type': 'int', 'type_label': 'Integer', 'help': '0 is column A'},
                {'name': 'line', 'label': _('Line'), 'value': '0', 'required': True, 'type': 'integer', 'type_label': 'Integer', 'help': '0 is the first line'},
                {'name': 'file_path', 'label': _('Tmp path'), 'value': '/tmp', 'required': True, 'type': 'char', 'type_label': 'Char', 'help': 'Absolute path and file name. Ex: /tmp'},
                {'name': 'file_name', 'label': _('File name'), 'value': 'xls_from_sql.xls', 'required': True, 'type': 'char', 'type_label': 'Char', 'help': 'File name. Ex: myfile.xls\nParameters:\n\tOrigin:\n\t\t%ID\n\t\t%MODEL\n\tDates:\n\t\t%a: Locale’s abbreviated weekday name\n\t\t%A: Locale’s full weekday name\n\t\t%b: Locale’s abbreviated month name\n\t\t%B: Locale’s full month name\n\t\t%c: Locale’s appropriate date and time representation\n\t\t%d: Day of the month as a decimal number [01,31]\n\t\t%H: Hour (24-hour clock) as a decimal number [00,23]\n\t\t%I: Hour (12-hour clock) as a decimal number [01,12]\n\t\t%j: Day of the year as a decimal number [001,366]\n\t\t%m: Month as a decimal number [01,12]\n\t\t%M: Minute as a decimal number [00,59]\n\t\t%p: Locale’s equivalent of either AM or PM\n\t\t%S: Second as a decimal number [00,61]\n\t\t%U: Week number of the year (Sunday as the first day of the week) as a decimal number [00,53]. All days in a new year preceding the first Sunday are considered to be in week 0\n\t\t%w: Weekday as a decimal number [0(Sunday),6]\n\t\t%W: Week number of the year (Monday as the first day of the week) as a decimal number [00,53]. All days in a new year preceding the first Monday are considered to be in week 0\n\t\t%x: Locale’s appropriate date representation\n\t\t%X: Locale’s appropriate time representation\n\t\t%y: Year without century as a decimal number [00,99]\n\t\t%Y: Year with century as a decimal number\n\t\t%Z: Time zone name (no characters if no time zone exists)\n\t\t%%: A literal "%" character'},
                {'name': 'template_name', 'label': _('Template name'), 'value': '/tmp/template.xls', 'required': False, 'type': 'char', 'type_label': 'Char', 'help': 'Absolute path of template file Ex: /tmp/template.xls'},
                {'name': 'exception_columns', 'label': _('Exception columns'), 'value': '[]', 'required': True, 'type': 'char', 'type_label': 'Char', 'help': 'Exception columns Ex: [1, 5, 19]'},
                       ]} 

# Fonction qui permet de transformer les styles de la feuille de lecture en styles d'écriture
# https://secure.simplistix.co.uk/svn/xlrd/trunk/xlrd/doc/xlrd.html?p=4966
# https://secure.simplistix.co.uk/svn/xlwt/trunk/xlwt/doc/xlwt.html?p=4966
# https://github.com/shaung/xlpy/blob/master/xlpy/xlutils/utils.py
def get_xlwt_style_list(rdbook):
    wt_style_list = []
    for rdxf in rdbook.xf_list:
        wtxf = XFStyle()
        #
        # number format
        #
        wtxf.num_format_str = rdbook.format_map[rdxf.format_key].format_str
        #
        # font
        #
        wtf = wtxf.font
        rdf = rdbook.font_list[rdxf.font_index]
        wtf.height = rdf.height
        wtf.italic = rdf.italic
        wtf.struck_out = rdf.struck_out
        wtf.outline = rdf.outline
        wtf.shadow = rdf.outline
        wtf.colour_index = rdf.colour_index
        wtf.bold = rdf.bold #### This attribute is redundant, should be driven by weight
        wtf._weight = rdf.weight #### Why "private"?
        wtf.escapement = rdf.escapement
        wtf.underline = rdf.underline_type ####
        # wtf.???? = rdf.underline #### redundant attribute, set on the fly when writing
        wtf.family = rdf.family
        wtf.charset = rdf.character_set
        wtf.name = rdf.name
        #
        # protection
        #
        wtp = wtxf.protection
        rdp = rdxf.protection
        wtp.cell_locked = rdp.cell_locked
        wtp.formula_hidden = rdp.formula_hidden
        #
        # border(s) (rename ????)
        #
        wtb = wtxf.borders
        rdb = rdxf.border
        wtb.left   = rdb.left_line_style
        wtb.right  = rdb.right_line_style
        wtb.top    = rdb.top_line_style
        wtb.bottom = rdb.bottom_line_style
        wtb.diag   = rdb.diag_line_style
        wtb.left_colour   = rdb.left_colour_index
        wtb.right_colour  = rdb.right_colour_index
        wtb.top_colour    = rdb.top_colour_index
        wtb.bottom_colour = rdb.bottom_colour_index
        wtb.diag_colour   = rdb.diag_colour_index
        wtb.need_diag1 = rdb.diag_down
        wtb.need_diag2 = rdb.diag_up
        #
        # background / pattern (rename???)
        #
        wtpat = wtxf.pattern
        rdbg = rdxf.background
        wtpat.pattern = rdbg.fill_pattern
        wtpat.pattern_fore_colour = rdbg.pattern_colour_index
        wtpat.pattern_back_colour = rdbg.background_colour_index
        #
        # alignment
        #
        wta = wtxf.alignment
        rda = rdxf.alignment
        wta.horz = rda.hor_align
        wta.vert = rda.vert_align
        wta.dire = rda.text_direction
        # wta.orie # orientation doesn't occur in BIFF8! Superceded by rotation ("rota").
        wta.rota = rda.rotation
        wta.wrap = rda.text_wrapped
        wta.shri = rda.shrink_to_fit
        wta.inde = rda.indent_level
        # wta.merg = ????
        #
        wt_style_list.append(wtxf)
    return wt_style_list



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
    
    
    def xls_from_sql(self, procedure, edi_file, query, sheet='0', column='0', line='0', file_path='/tmp', file_name='xls_from_sql.xls', template_name=False, exception_columns='[]'):
        """
            Export d'un SQL dans un XLS
        """
        context = self.env.context.copy()
        
        # Permet à partir d'un wizard d'envoyer une requete à une transformation qui sera reprise dans les procédures
        if context.get('edi_custom_query') and not query:
            query = context['edi_custom_query']
            
        if '%object_id' in query:
            if 'object_id' in context:
                query = query.replace('%object_id', str(context['object_id']))

        if '%object_model' in query:
            if 'object_model' in context:
                query = query.replace('%object_model', context['object_model'].replace('.', '_'))
        
        try:
            exception_columns = eval(exception_columns)
        except:
            exception_columns = []
            
        edi_file_obj = self.env['edi.transformation.file']
        self.env.cr.execute(query)
        query_res = self.env.cr.fetchall()
        file_name = self.compute_file_name(file_path, file_name, context.get('object_id'), context.get('object_model'))
        if query:
            rs = False
            style_list = []
            style = False
            # Copie du template
            if template_name:
                model = True
                copy_xls = distutils.file_util.copy_file(template_name, file_name)
                # Ouverture de la copie
                rb = xlrd.open_workbook(file_name, formatting_info=True, ragged_rows=True)
                sheets = rb.sheets()
                # Compter le nombre de feuille             
                nb_sheet = len(sheets)
                # Savoir s'il est possible d'écrire dans la page indiqué dans l'abonnement
                write_sheet = sheet
                if sheet >= nb_sheet: 
                    write_sheet = 0
                    
                # Sélection de la page dans laquelle on va écrire
                rs = rb.sheet_by_index(write_sheet)
                wb = copy(rb)
                sheet = wb.get_sheet(write_sheet)
                style_list = get_xlwt_style_list(rb)
            # Création d'un fichier
            else:
                model = False
                book = Workbook(encoding='utf-8')
                sheet = book.add_sheet('new file')
            
            # Colonne avec exception ne pas mettre de valeur
            if exception_columns:
                tmpListe = list(exception_columns)
                tmpListe.sort()
                exception_columns = list(tmpListe)
            
            # Bouclage sur chaque ligne
            for x in query_res:
                actual_column = column
                for y in x:
                    # Test exception de colonne
                    if exception_columns and actual_column in exception_columns:
                        while actual_column in exception_columns:
                            actual_column += 1
                            
                    # Remplissage de la colonne pour la ligne
                    # Si on ne doit pas ecrire
                    if y == None:
                        pass
                    else:
                        # S'il y a un modèle
                        if rs and style_list:
                            # S'il y a un style sur les lignes et les colonnes
                            try:
                                style = style_list[rs.cell_xf_index(line, actual_column)]
                                style_test = True
                            except:
                                # S'il y a un style que sur les lignes
                                try:
                                    style = style_list[rs.rowinfo_map[line].xf_index]
                                    style_test = True
                                except:
                                    # S'il y a un style que sur les colonnes
                                    try:
                                        style = style_list[rs.colinfo_map[actual_column].xf_index]
                                        style_test = True
                                    except:
                                        # S'il y a pas de style
                                        style_test = False
                            if style_test:
                                sheet.write(line, actual_column, label=y, style=style)
                                del style
                            else:
                                sheet.write(line,actual_column,label=y)
                        else:
                            sheet.write(line, actual_column, label=y)
                    actual_column += 1
                line += 1
            
            if context.get('protect_sheet'):
                sheet.protect = True
                if context.get('password_protect'):
                    sheet.password = context['password_protect']
                else:
                    sheet.password = ''
                    
            if model:
                wb.save(file_name)
                del rs
                del sheet
                del query_res
                del rb
                del copy_xls
                del style_list
            else:
                book.save(file_name)
                del book
                del sheet
                del query_res
                    
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