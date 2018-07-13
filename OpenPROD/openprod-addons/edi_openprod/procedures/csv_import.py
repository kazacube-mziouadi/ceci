# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
import csv
import base64
import re
import StringIO


PROCEDURE = {'name': 'csv_import', 
             'label':  _('CSV Import'),
             'params': [
                    {'name': 'table', 'label': _('Table'), 'required': True, 'type': 'char', 'type_label': 'Char'},
                    {'name': 'delimiter', 'label': _('Delimiter'), 'required': False, 'type': 'char', 'type_label': 'Char'},
                    {'name': 'quotechar', 'label': _('Quotechar'), 'required': False, 'type': 'char', 'type_label': 'Char'},
                    {'name': 'escapechar', 'label': _('Escapechar'), 'required': True, 'type': 'char', 'type_label': 'Char'},
                    {'name': 'temporary_table', 'label': _('Temporary table'), 'required': False, 'type': 'char', 'type_label': 'Char', 'help': _('Lets not import multiple times the same lines, you just put the name of the temporary table.')},
                    {'name': 'condition', 'label': _('Condition'), 'required': False, 'type': 'char', 'type_label': 'Char', 'help': _('Allows a condition in the query example "(table.name_columnsA is not null and table.name_columnsB! = false)".')},
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

    def csv_import(self, procedure, edi_file, table, delimiter=';', quotechar='"', escapechar='\\', temporary_table=False, condition=False):
        """
            Import du CSV
        """
        
        # Test de l'existence de la table
        self.env.cr.execute('SELECT exists(SELECT 1 from pg_tables where tablename = %s)', (table,))
        exist = self.env.cr.fetchone()[0]
        return self.insert_table(edi_file, delimiter, quotechar, escapechar, temporary_table, condition, table, create=not exist)
   
   
    def insert_table(self, edi_file, delimiter, quotechar, escapechar, temporary_table=False, condition=False, table_name=False, create=False):
        """
            - Création de la table si elle n'existe pas
            - Remplissage de la table par rapport à un binary (edi_file)
        """
        res = True
        if edi_file:
            col_list = []
            lines_list = []
            data = base64.b64decode(edi_file)
            data = data.replace('\x00', '')
            read = csv.DictReader(StringIO.StringIO(data), delimiter=delimiter, dialect=csv.excel, escapechar=escapechar)
            first = True
            for row in read:
                if first:
                    first = False
                    col_list = [re.sub('[^0-9a-zA-Z]+', '_', col.lower()) for col in row.keys()]

                values = [x or False for x in row.values()] #.replace("'", "#simplequote#").replace("u'", "#uquote#")
                lines_list.append(values)

            # Mise en forme de la liste (si colonne nommée end ou colonne vide)
            i = 0
            j = 1
            for col in col_list[:]:
                if not col:
                    col_list[i] = 'c%d'%(j)
                    j += 1
                elif col == 'end':
                    col_list[i] = 'end2'
                elif col == 'desc':
                    col_list[i] = 'desc2'
                elif col == 'asc':
                    col_list[i] = 'asc2'
                elif col in ['oid', 'tableoid', 'xmin', 'cmin', 'xmax', 'cmax', 'ctid']:
                    col_list[i] = '%s2'%(col)
                    
                i += 1
                    
            col_list = ['"%s"'%(x) for x in col_list[:]]
            if create:
                columns = []
                for col_name in col_list:
                    columns.append('%s text'%(col_name))
                
                if columns:
                    create_query = """
                                    CREATE TABLE %(table_name)s (
                                                                 id serial NOT NULL CONSTRAINT %(table_name)s_pkey PRIMARY KEY, 
                                                                 %(columns)s
                                                                )
                                   """%({'table_name': table_name, 
                                         'columns': ', '.join(columns)
                                        })
                                   
                    self.env.cr.execute(create_query)

            decode_lines_list = []
            for ll in lines_list:
                temp_list = []
                for value_item in ll:
                    temp_list.append(value_item and value_item.decode('utf-8', errors='replace') or None)
                
                decode_lines_list.append(temp_list)
                
            values_str = '%s, ' * len(col_list)
            values_str = values_str[:-2]
            
            # Si utilisation d'une table temporaire pour éviter d'importer des doublons si des lignes ont déjà été importées
            if temporary_table:
                columns_temp = []
                for col_name in col_list:
                    columns_temp.append('%s text'%(col_name))
                    
                create_query2 = """
                                    CREATE TEMPORARY TABLE %(table_name)s (
                                                                 id serial NOT NULL CONSTRAINT %(table_name)s_pkey PRIMARY KEY, 
                                                                 %(columns)s
                                                                ) on commit drop
                                   """%({'table_name': temporary_table, 
                                         'columns': ', '.join(columns_temp)
                                        })
 
                self.env.cr.execute(create_query2)
                self.env.cr.executemany('INSERT INTO ' + temporary_table + ' (' + ', '.join(col_list) + ') VALUES (' + values_str + ')', decode_lines_list)
                col_list2 = [x.replace('"','') for x in col_list]
                col_list3 = [temporary_table+'.'+x for x in col_list2]
                nb_col = len(col_list3)
                y = 0
                col_list4 = []
                while y != nb_col:
                    vals = col_list3[y] + ' is not distinct from ' + table_name + '.' + col_list2[y]
                    col_list4.append(vals)
                    y += 1
                
                if condition:
                    self.env.cr.execute('INSERT INTO ' + table_name +  ' (' + ', '.join(col_list) + ')' + ' select '+ ', '.join(col_list3) +' from '+ temporary_table +' where not exists( select 1 from ' + table_name +' where ' + ' and '.join(col_list4) + '  ) and ' + condition)
                else:
                    self.env.cr.execute('INSERT INTO ' + table_name +  ' (' + ', '.join(col_list) + ')' + ' select '+ ', '.join(col_list3) +' from '+ temporary_table +' where not exists( select 1 from ' + table_name +' where ' + ' and '.join(col_list4) + '  )')
            else:
                if condition:
                    self.env.cr.executemany('INSERT INTO ' + table_name + ' (' + ', '.join(col_list) + ') VALUES (' + values_str + ') where '+ condition, decode_lines_list)
                else:
                    self.env.cr.executemany('INSERT INTO ' + table_name + ' (' + ', '.join(col_list) + ') VALUES (' + values_str + ')', decode_lines_list)
            
        return res