# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError

import base64


PROCEDURE = {'name': 'fixed_txt_import', 
             'label':  _('Text import (fixed width)'),
             'params': [
                    {'name': 'table_name', 'label': _('Table'), 'required': True, 'type': 'char', 'type_label': _('Char')},
                    {'name': 'columns_list', 'label': _('Columns list'), 'required': True, 'type': 'char', 'type_label': _('List'), 'value': '[\'c1\', \'c2\', \'c3\', \'c4\', \'c5\', \'c6\']'},
                    {'name': 'columns_width', 'label': _('Columns width'), 'required': True, 'type': 'char', 'type_label': _('List'), 'value': '[25, 30, 25, 30, 123, 4]'},
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
    

    def fixed_txt_import(self, procedure, edi_file, table_name, columns_list, columns_width):
        """
            Import du TXT
        """
        # Test de l'existence de la table
        self.env.cr.execute('SELECT exists(SELECT 1 from pg_tables where tablename = %s)', (table_name,))
        exist = self.env.cr.fetchone()[0]
        if exist:
            res = self.txt_insert_table(edi_file, table_name, eval(columns_list), eval(columns_width))
        else:
            raise except_orm(_('Error'), _('No table %s found.')%(table_name))
            
        return res
   
   
    def txt_insert_table(self, edi_file, table_name, columns_list, columns_width):
        """
            - Remplissage de la table par rapport à un binary (edi_file)
        """
        res = True
        if edi_file and table_name and columns_width:
            lines = base64.b64decode(edi_file).split('\r\n')
            decode_lines_list = []
            for line in lines:
                if line:
                    values = []
                    pos = 0
                    for column_length in columns_width:
                        values.append(line[pos:pos + column_length].strip().decode('utf-8'))
                        pos += column_length
                    
                    decode_lines_list.append(values)

            values_str = '%s, ' * len(columns_width)
            values_str = values_str[:-2]
            self.env.cr.executemany('INSERT INTO ' + table_name + ' (' + ', '.join(columns_list) + ') VALUES (' + values_str + ')', decode_lines_list)
            
        return res