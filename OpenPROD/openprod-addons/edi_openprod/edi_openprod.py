# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
import openerp
from datetime import datetime, timedelta
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm, ValidationError, Warning
from dateutil.relativedelta import relativedelta

from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from unidecode import unidecode
import time
from ftplib import FTP
import pprint
import base64
import StringIO
import logging

from common import format_path


SEPARATOR = '==============='
_logger = logging.getLogger('edi')



class edi_transformation_file(models.Model):
    """ 
    EDI Transformation file 
    """
    _name = 'edi.transformation.file'
    _description = 'EDI Transformation file'
    
    
    @api.one
    def _get_edi_file_binary_filesystem(self):
        attachment_obj = self.env['ir.attachment']
        attachment_rs = attachment_obj.search([('res_model','=',self._name),('res_id','=',self.id),('binary_field','=','edi_file')])
        if attachment_rs:
            self['edi_file'] = attachment_rs[0].datas
    
    @api.one
    def _set_edi_file_binary_filesystem(self):
        attachment_obj = self.env['ir.attachment']
        attachment_rs = attachment_obj.search([('res_model','=',self._name),('res_id','=',self.id),('binary_field','=','edi_file'),('is_binary_field','=',True)])
        if self.edi_file:
            if attachment_rs:
                attachment_rs.datas = self.edi_file
            else:
                attachment_obj.create({'res_model': self._name, 'res_id': self.id, 'name': 'edi_file datas' , 
                                       'is_binary_field': True, 'binary_field': 'edi_file', 
                                       'datas': self.edi_file, 'datas_fname': self.edi_file_fname})
        else:
            attachment_rs.unlink()
            
            
    @api.model
    def _type_get(self):
        return [
                ('send', _('Send')),
                ('get', _('Get')),
                       ]

    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('done', _('Done')),
                ('error', _('Error')),
                       ]

    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True, size=256)
    src = fields.Char(string='Source', size=256, required=True)
    file_date = fields.Datetime(string='File date')
    upload_date = fields.Datetime(string='Upload date', default=lambda self: fields.Datetime.now())
    last_date = fields.Datetime(string='Last execution date')
    edi_file  = fields.Binary(string='File', compute='_get_edi_file_binary_filesystem', inverse='_set_edi_file_binary_filesystem')
    edi_file_fname = fields.Char(string='edi_file_fname', size=256)
    processing_id = fields.Many2one('edi.transformation.processing', string='Processing', required=False, ondelete='restrict')
    history_id = fields.Many2one('edi.transformation.history', string='History', required=False, ondelete='set null')
    type = fields.Selection('_type_get', string='Type', required=True)
    log = fields.Text(string='Log')
    state = fields.Selection('_state_get', string='State', required=True, readonly=True, default='draft')
    user_id = fields.Many2one('res.users', string='User', required=False, ondelete='cascade')
    
    
    #===========================================================================
    # Functions
    #===========================================================================
    @api.multi
    def execute(self):
        """
            Execute toutes les procédure du traitement
        """
        for this in self:
            if this.processing_id:
                context = self.env.context.copy()
                try:
                    context['edi_file_id'] = this.id
                    run_ok, msg = this.processing_id.run_all(edi_file=this.edi_file)
                    if run_ok:
                        state = 'done'
                        msg = 'Execution OK'
                    else:
                        state = 'error'
                        if not msg:
                            msg = 'Processing error'
                        
                except Exception as e:
                    error = ''
                    if e and isinstance(e.args, tuple):
                        for i in e.args:
                            if error:
                                error = '%s\n%s'%(error, i)
                            else:
                                error = i
                                 
                    msg = error
                    state = 'error'

                this.write({'log': msg,
                            'state': state, 
                            'last_date': fields.Datetime.now()}) 
                
        return True



class edi_transformation_get_file(models.Model):
    """ 
    EDI Transformation get file 
    """
    _name = 'edi.transformation.get.file'
    _description = 'EDI Transformation get file'
    
    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('error', _('Error')),
                ('done', _('Done')),
                       ]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True, size=256)
    ftp_host = fields.Char(string='FTP Host', size=128, required=True)
    ftp_user = fields.Char(string='FTP User', size=128, required=True)
    ftp_password = fields.Char(string='FTP Password', size=128, required=True)
    ftp_directory = fields.Char(string='FTP Directory', size=256, required=True, help="Absolute path from ftp root.", default='/')
    ftp_archive = fields.Char(string='Ftp archive', size=128, required=False, help="Absolute path from ftp root or relative path from FTP directory path. \nIf this field is empty, file will be delete from FTP.")
    file_filter = fields.Char(string='Filter', size=128, required=True, default='*.*')
    is_active = fields.Boolean(string='Active', default=False)
    automatic_processing = fields.Boolean(string='Automatic processing', default=False)
    processing_id = fields.Many2one('edi.transformation.processing', string='Processing', required=False, ondelete='restrict')
    last_date = fields.Datetime(string='Last execution date')
    log = fields.Text(string='Log')
    ignore_file_errors = fields.Boolean(string='Ignore file errors', default=False)
    email_template_id = fields.Many2one('mail.template', string='Email Template', required=False, ondelete='restrict')
    cron_ids = fields.Many2many('ir.cron', 'cron_edi_get_file_rel', 'get_file_id', 'cron_id', string='Crons')
    state = fields.Selection('_state_get', string='State', default='draft', required=True, readonly=True)
    in_progress = fields.Boolean(string='In progress', default=False)
    
    
    #===========================================================================
    # Functions
    #===========================================================================
    def ftp_connect(self):
        """
            Connexion FTP
        """
        ftp = FTP(self.ftp_host)
        ftp.login(self.ftp_user, self.ftp_password)
        ftp.sendcmd('CWD %s'%(self.ftp_directory))
        return ftp
    
    
    @api.multi
    def execute(self):
        """
            - Transfert des fichier séléctionnés grâce au filtre du FTP sur /tmp
            - Création d'une ligne de fichier EDI
            - Archivage ou suppression du fichier sur le FTP
        """
        
        res = True
        for this in self:
            try:
                this.write({'in_progress': True})
                self.env.cr.commit()
                # Connexion au FTP
                ftp = this.ftp_connect()
                # Transfert du fichier du FTP vers le disque local
                edi_file_rcs, file_error = this.ftp_transert_files(ftp, '/tmp')
                if file_error:
                    msg = 'File not found'
                    state = 'error'
                elif edi_file_rcs:
                    # Execution du traitement si traitement auto est coché
                    if this.automatic_processing:
                        edi_file_rcs.execute()
                    
                    # Archivage ou suppression du fichier sur le FTP
                    self.ftp_archive_files(ftp, this.file_filter, this.ftp_archive)
                    msg = 'Execution OK'
                    state = 'done'
                else:
                    msg = 'Execution OK'
                    state = 'done'
                    
                ftp.quit()
            except Exception as e:
                error = ''
                if e and isinstance(e.args, tuple):
                    for i in e.args:
                        if error:
                            error = '%s\n%s'%(error, i)
                        else:
                            error = i
                             
                msg = error
                state = 'error'
                res = False
                 
            this.write({'in_progress': False,
                        'log': msg,
                        'state': state, 
                        'last_date': fields.Datetime.now()})
            self.env.cr.commit()
            
        return res

    
    def ftp_transert_files(self, ftp, dest_path):
        """
            - Transfert des fichier séléctionnés grâce à file_filter
            - Création d'une ligne de fichier EDI
        """
        edi_file_obj = self.env['edi.transformation.file']
        file_error = False
        edi_file_rcs = self.env['edi.transformation.file']
        # Liste des fichiers du FTP filtrée selon les paramètres file_filter et file_type
        # Première gestion du flag permettant d'ignorer les erreurs de fichier manquant (la gestion simple ci dessous ne marchait pas avec le FTP Gergonne)
        if self.ignore_file_errors:
            try:
                files = ftp.nlst('%s'%(self.file_filter))
            except:
                files = False
        else:
            files = ftp.nlst('%s'%(self.file_filter))
            
        if not files and not self.ignore_file_errors:
            file_error = True
            if self.email_template_id:
                self.email_template_id.send_mail(self.id, force_send=True)
        elif files:  
            for file_name in files:
                f = open("%s%s" %(format_path(dest_path), file_name), "wb")
                ftp.retrbinary('RETR %s' %(file_name), f.write)
                f.close()
                f = open("%s%s" %(format_path(dest_path), file_name), "rt")
                edi_file_rcs += edi_file_obj.create({
                                                     'name': file_name,
                                                     'src': 'Automatic',
                                                     'type': 'get',
                                                     'edi_file': base64.b64encode(f.read()),
                                                     'edi_file_fname': file_name,
                                                     'processing_id': self.processing_id and self.processing_id.id,
                                                    })
                f.close()

        return edi_file_rcs, file_error
     
 
    def ftp_archive_files(self, ftp, file_filter, ftp_archive=False):
        """
            - Archivage ou suppression du fichier sur le FTP selon si ftp_archive est remplit
        """
        # Liste des fichiers du FTP filtrée selon les paramètres file_filter
        for file_name in ftp.nlst('%s'%(file_filter)):                
            # Si un chemin d'archive est renseigné, archivage du fichier. Sinon suppression
            if ftp_archive:
                ftp.rename(file_name, '%s%s'%(format_path(ftp_archive), unidecode(file_name.decode('UTF-8'))))
            else:
                ftp.delete(file_name)
                 
        return True



class edi_transformation_send_file(models.Model):
    """ 
    EDI Transformation send file 
    """
    _name = 'edi.transformation.send.file'
    _description = 'EDI Transformation send file'

    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('error', _('Error')),
                ('done', _('Done')),
                       ]
    

    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True, size=256)
    ftp_host = fields.Char(string='FTP Host', size=128, required=True)
    ftp_user = fields.Char(string='FTP User', size=128, required=True)
    ftp_password = fields.Char(string='FTP Password', size=128, required=True)
    ftp_directory = fields.Char(string='FTP Directory', size=256, required=True, help="Absolute path from ftp root.", default='/')
    is_active = fields.Boolean(string='Active', default=False)
    last_date = fields.Datetime(string='Last execution date')
    log = fields.Text(string='Log')
    state = fields.Selection('_state_get', string='State', default='draft', required=True, readonly=True)
    
    
    #===========================================================================
    # Functions
    #===========================================================================
    def ftp_connect(self):
        """
            Connexion FTP
        """
        ftp = FTP(self.ftp_host)
        ftp.login(self.ftp_user, self.ftp_password)
        ftp.sendcmd('CWD %s'%(self.ftp_directory))
        return ftp
    
    
    def send(self, edi_file):
        """
            - Transfert du fichier passé en paramètre vers le FTP avec la connexion de l'id send_file_id
        """
        res = True
        try:
            # Connexion au FTP
            ftp = self.ftp_connect()
            # Upload
            ftp.storbinary('STOR ' + edi_file.edi_file_fname, StringIO.StringIO(base64.decodestring(edi_file.edi_file))) 
            ftp.quit()
            msg = 'Execution OK'
            state = 'done'
        except Exception as e:
            error = ''
            if e and isinstance(e.args, tuple):
                for i in e.args:
                    if error:
                        error = '%s\n%s'%(error, i)
                    else:
                        error = i
                         
            msg = error
            state = 'error'
            res = False
             
        self.write({
            'log': msg,
            'state': state, 
            'last_date': fields.Datetime.now()
        })
        return res



class edi_transformation_sql_authorization(models.Model):
    """ 
    EDI SQL authorization 
    """
    _name = 'edi.transformation.sql.authorization'
    _description = 'EDI SQL authorization'

    
    @api.model
    def _type_get(self):
        return [
                ('update', _('UPDATE')),
                ('insert', _('INSERT INTO')),
                ('delete', _('DELETE FROM')),
                       ]
    

    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True, size=64)
    is_active = fields.Boolean(string='Active', default=True)
    table_ids = fields.One2many('edi.transformation.sql.authorization.line', 'authorization_id',  string='Tables')
    processing_ids = fields.Many2many('edi.transformation.processing', 'edi_procedure_authorization_rel', 'authorization_id', 'processing_id', 
                                      string='Processing', help='Let this field empty to apply authorization to all processing')
    type = fields.Selection('_type_get', string='Type', required=True)
    
    
    #===========================================================================
    # Functions
    #===========================================================================
    def check_authorization(self, field, procedure):
        """
            Verification qu'il existe une autorisation pour une requête et une table données
        """
        res = False
        query = procedure[field]
        if query: 
            if query.lower().split()[0] in ('select', 'vacuum', 'reindex'):
                res = True
            elif procedure.processing_id and field == 'action_sql':
                if len(query) > 2:
                    query = query.lower().split()
                    if query[0] == 'insert' and query[1] == 'into':
                        table = query[2].lower()
                        query_type = query[0]
                    elif query[0] == 'update':
                        table = query[1].lower()
                        query_type = query[0]
                    elif query[0] == 'delete' and query[1] == 'from':
                        table = query[2].lower()
                        query_type = query[0]
                    elif query[0] == 'create' and query[1] == 'or' and query[2] == 'replace' and query[3] == 'function':
                        res = True
                        table = False
                        query_type = False
                    else:
                        table = False
                        query_type = False
                    
                    if table and query_type:
                        autho_rcs = self.search([('type', '=', query_type), 
                                           ('is_active', '=', True), 
                                           '|', ('processing_ids', 'in', [procedure.processing_id.id]),
                                           ('processing_ids', '=', False)])
                        if autho_rcs:
                            line_ids = self.env['edi.transformation.sql.authorization.line'].search([('name', '=', table), 
                                                                                                     ('authorization_id', 'in', autho_rcs.ids)], limit=1)
                            if line_ids:
                                res = True
        
        else:
            res = True
                 
        return res
    


class edi_transformation_sql_authorization_line(models.Model):
    """ 
    EDI SQL authorization line 
    """
    _name = 'edi.transformation.sql.authorization.line'
    _description = 'EDI SQL authorization line'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Table name', required=True, size=128)
    authorization_id = fields.Many2one('edi.transformation.sql.authorization', string='Authorization', required=False, ondelete='cascade')


    #===========================================================================
    # ONCHANGE
    #===========================================================================
    @api.onchange('name', 'verification_sql', 'domain_sql')
    def onchange_name(self):
        self.name = self.name and self.name.lower() or ''
        
            

class edi_transformation_processing_category(models.Model):
    """ 
        EDI Transformation processing category
    """
    _name = 'edi.transformation.processing.category'
    _description = 'EDI Transformation processing category'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True, size=256)
    description = fields.Text(string='Description')



class edi_transformation_processing(models.Model):
    """ 
        EDI Transformation processing
    """
    _name = 'edi.transformation.processing'
    _description = 'EDI Transformation processing'
    _order = 'sequence ASC'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True, size=256)
    sequence = fields.Integer(string='Sequence', default=1, required=True)
    in_progress = fields.Boolean(string='In progress', default=False)
    mail_error = fields.Boolean(string='Mail error', default=False, help='Send mail if processing generate an error')
    category_id = fields.Many2one('edi.transformation.processing.category', string='Category', required=False, ondelete='restrict')
    email_template_id = fields.Many2one('mail.template', string='Email Template', required=False, ondelete='restrict')
    procedure_ids = fields.One2many('edi.transformation.procedure', 'processing_id',  string='Procedures')
    cron_ids = fields.Many2many('ir.cron', 'edi_transformation_ir_cron_rel', 'transformation_id', 'cron_id', string='Crons')
    
    
    #===========================================================================
    # Functions
    #===========================================================================
    @api.multi
    def goto_procedure(self):
        data_pool = self.env['ir.model.data']
        action_model, action_id = data_pool.get_object_reference('edi_openprod', 'act_edi_transformation_procedure')
        if action_model:
            action_pool = self.env[action_model]
            action = action_pool.browse(action_id).read()[0]
            action['context'] = {'search_default_processing_id': self.ids[0], 'default_processing_id': self.ids[0]}
            return action

    
    @api.multi
    def run_all(self, edi_file=None):
        """
            Traitement de toutes les procédures du traitement
        """
        context = self.env.context.copy()
        res = True
        msg = False
        history_obj = self.env['edi.transformation.history']
        for sql_processing in self:
            sql_processing.write({'in_progress': True})
            self.env.cr.commit()
            history_rcs = False
            history_rcs = history_obj.create({
                                                'processing_id': sql_processing.id,
                                                'start_date': fields.Datetime.now(), 
                                                'object_model': context.get('object_model', None), 
                                                'object_id': context.get('object_id', None)})
            
            if history_rcs:
                context['edi_history_id'] = history_rcs.id
                
            sql_processing.procedure_ids.write({'check': 'draft'})
            for procedure in sql_processing.procedure_ids:
                if procedure.state == 'active':
                    res, msg = procedure.with_context(context).run_all(edi_file=edi_file)
                    self.env.cr.commit()
                    if not res:
                        # Envoie du mail d'erreur
                        if sql_processing.mail_error and sql_processing.email_template_id:
                            if sql_processing.email_template_id:
                                sql_processing.email_template_id.send_mail(sql_processing.id, force_send=True)
                        break
            
            if history_rcs:
                history_rcs.write({'check': res and 'done' or 'error', 
                                   'end_date': fields.Datetime.now()})
           
            sql_processing.write({'in_progress': False})
            self.env.cr.commit()
            
        return res, msg
    
    
    @api.one
    def copy(self, default=None):
        """
            Pas de copie des procédures lors de la copie du traitement
        """
        if not default: 
            default = {}
            
        default['procedure_ids'] = False
        return super(edi_transformation_processing, self).copy(default=default)
          
          

class edi_transformation_procedure(models.Model):
    """ 
        EDI Transformation procedure
    """
    _name = 'edi.transformation.procedure'
    _description = 'EDI Transformation procedure'
    _order = 'sequence ASC'

    
    @api.model
    def _action_type_get(self):
        return [
                ('sql', _('Sql')),
                ('method', _('Method')),
                       ]
    
    
    @api.model
    def _check_get(self):
        return [
                ('draft', _('Draft')),
                ('done', _('Done')),
                ('error', _('Error')),
                       ]

    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Draft')),
                ('active', _('Active')),
                ('cancel', _('Cancel')),
                       ]

    
    @api.model
    def _method_get(self):
        return []

    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    # Général
        # En tete
    name = fields.Char(required=True, size=256)
    processing_id = fields.Many2one('edi.transformation.processing', string='Processing', required=False, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10, required=True)
    action_type = fields.Selection('_action_type_get', string='Action type', default='sql')
        # Administration
    check = fields.Selection('_check_get', string='Check', default='draft')
    last_start_date = fields.Datetime(string='Last start date')
    last_date = fields.Datetime(string='Last date')
    state = fields.Selection('_state_get', string='State', required=True, default='draft')
    log = fields.Text(string='Log')
    # SQL
        # Domain
    domain_sql = fields.Text(string='Domain (SQL)')
    domain_sql_result = fields.Text(string='Domain (result)')
        # Action
    action_sql = fields.Text(string='Action (SQL)')
    action_sql_result = fields.Text(string='Action (result)')
    action_sql_formatting = fields.Boolean(string='Formating result', default=True)
    action_method = fields.Char(string='Action method', size=256, required=False)
        # Verification
    verification_sql = fields.Text(string='Verification (SQL)')
    verification_sql_result = fields.Text(string='Verification (result)')
    verification_sql_formatting = fields.Boolean(string='Formating result', default=True)
    # Methode
    method = fields.Selection('_method_get', string='Method')
    param_ids = fields.One2many('edi.transformation.procedure.method.param', 'procedure_id',  string='Parameters')
    edi_user_ids = fields.One2many('edi.transformation.users', 'procedure_id',  string='Users')
    is_edi_users = fields.Boolean(string='Is edi users', default=False)
    is_doc_by_user = fields.Boolean(string='Doc/User', default=False, help="Send only the user's documents.")
    
    
    #===========================================================================
    # ONCHANGE
    #===========================================================================
    @api.onchange('action_sql', 'verification_sql', 'domain_sql')
    def _onchange_warning_product_id(self):
        """
            Onchange pour ne pas pouvoir entrer plusieurs requêtes SQL dans un champ
        """
        self.action_sql = self.action_sql and not self.action_sql.lower().startswith('create or replace function') and self.action_sql.split(';')[0] or self.action_sql
        self.verification_sql = self.verification_sql and not self.verification_sql.lower().startswith('create or replace function') and self.verification_sql.split(';')[0] or self.verification_sql
        self.domain_sql = self.domain_sql and not self.domain_sql.lower().startswith('create or replace function') and self.domain_sql.split(';')[0] or self.domain_sql
        
    
    def update_params(self, method):
        """
            Méthode déstinée à être redéfinie par les procédures pour remplir les paramètres
        """
        return []
    
    
    @api.onchange('method')
    def onchange_method(self):
        """
            Onchange sur la méthode pour vider/remplir la table des paramètres
        """
        self.is_edi_users = self.method in ('jasper_from_sql', 'send_files_mail') and True or False
        self.param_ids = self.update_params(self.method)
    
    
    #===========================================================================
    # FUNCTIONS & BUTTONS
    #===========================================================================
    
    def do_autocommit(self, q):
        with openerp.api.Environment.manage():
            with openerp.registry(self.env.cr.dbname).cursor() as new_cr:
                new_cr.connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
                new_cr.execute(q)
                new_cr.commit()

        return True
    
    
    def run_sql(self, field, write=True, id_only=False, formatting=False, 
                query_args=None, bool_res=False):
        """
            Execution d'une procédure de type SQL
        """
        if not query_args:
            query_args = {}
            
        res = []
        print_res = ''
        if self[field]:
            query = self[field]
            query = query.replace('%', '%%')
            query = query.replace('%%(domain)s', '%(domain)s')
            query = query%query_args
            query_list = query.split()
            try:
                if query_list and query_list[0].lower() in ('vacuum', 'reindex'):
                    self.do_autocommit(query)
                else:
                    self.env.cr.execute(query)
                    
                if query_list and query_list[0].lower() == 'select':
                    if bool_res:
                        res = self.env.cr.fetchone()
                        res = res and res[0] or False
                    else:
                        res = self.env.cr.dictfetchall()
                        
                    log = self.env.cr.statusmessage
                    if id_only:
                        res = print_res = [x['id'] for x in res]
                    elif formatting:
                        print_res = pprint.pformat(res)
                    else:
                        print_res = res
                       
                # Pas de resultat (update par exemple) 
                else:
                    print_res = ''
                    log = self.env.cr.statusmessage
                    
                error = False
                    
            except Exception as e:
                self.env.cr.rollback()
                log = ''
                error = True
                if e and isinstance(e.args, tuple):
                    for i in e.args:
                        if log:
                            log = '%s\n%s'%(log, i)
                        else:
                            log = i
            
            query = self.env.cr.query
            if write:
                self.write({'%s_result'%(field): '\n%(separator)sQUERY%(separator)s\n'\
                                                 '%(query)s\n'\
                                                 '\n%(separator)sRESULT%(separator)s\n'\
                                                 '%(res)s\n'\
                                                 '\n%(separator)sLOG%(separator)s\n'\
                                                 '%(log)s\n'%({'separator': SEPARATOR,
                                                               'query': query,
                                                               'res': print_res,
                                                               'log': log})})
        else:
            error = False
            if write:
                self.write({'%s_result'%(field): ''})
                
        return res, error
    
    
    def get_procedure(self):
        if len(self.ids) > 1:
            procedure = self[0]
        else:
            procedure = self
        
        return procedure
    
    
    @api.multi
    def run_domain(self, write=True):
        """
            Execution du domain d'une procédure de type SQL
        """
        procedure = self.get_procedure()
        if self.env['edi.transformation.sql.authorization'].check_authorization('domain_sql', procedure):
            res, error = procedure.run_sql('domain_sql', write=write, id_only=True)
        else:
            procedure.write({'domain_sql_result': 'Authorization error'})
            error = True
            res = False
            
        return res, error
    
    
    @api.multi
    def run_action(self, write=True, query_args=None):
        """
            Execution de l'action d'une procédure de type SQL
        """
        if not query_args:
            query_args = {}
            
        procedure = self.get_procedure()
        if self.env['edi.transformation.sql.authorization'].check_authorization('action_sql', procedure):
            if not query_args:
                domain, dummy = procedure.run_domain(write=write)
                query_args['domain'] = str(tuple(domain))
                
            res, error = procedure.run_sql('action_sql', write=write, formatting=procedure.action_sql_formatting, query_args=query_args)
        else:
            procedure.write({'action_sql_result': 'Authorization error'})
            error = True
            
        return error
    
    
    @api.multi
    def run_verification(self, write=True, query_args=None):
        """
            Execution de la verification d'une procédure de type SQL
        """
        if not query_args:
            query_args = {}
        
        procedure = self.get_procedure()
        if self.env['edi.transformation.sql.authorization'].check_authorization('verification_sql', procedure):
            res, error = procedure.run_sql('verification_sql', write=write, formatting=procedure.verification_sql_formatting, query_args=query_args, bool_res=True)
            if not error:
                if isinstance(res, bool):
                    error = not res
                elif procedure.verification_sql:
                    error = True

                if error:
                    self.env.cr.rollback()  
                    procedure.write({'verification_sql_result': 'Verification error'})
                
        else:
            self.env.cr.rollback()  
            procedure.write({'verification_sql_result': 'Authorization error'})
            error = True
          
            
        return error
    
    
    def run_method(self, edi_file=None):
        """
            Execution d'une procédure de type Méthode
        """
        param_list = []
        procedure = self.get_procedure()
        # Liste des paramètres
        for param in procedure.param_ids:
            if param.value:
                if param.name == 'query':
                    param.value = ' '.join(param.value.split())
                    
                if param.type == 'char':
                    param_list.append("'%s'"%(param.value.replace("'", "\\'")))
                else:
                    param_list.append(param.value)
                    
            else:
                param_list.append("''")
        
        # Appel dynamique de la méthode
        return eval('getattr(self.with_context(self.env.context.copy()), procedure.method)(procedure, edi_file, %s)'%(param_list and '%s, '%(', '.join(param_list)) or ''))
    
    
    @api.multi
    def run_all(self, write=True, edi_file=None):
        """
            Execution d'une procédure
        """
        context = self.env.context.copy()
        procedure = self.get_procedure()
        procedure.write({'last_start_date': fields.Datetime.now()})
        self.env.cr.commit()
        msg = ''
        if procedure.action_type == 'sql':
            domain, error = procedure.with_context(context).run_domain(write=write)
            if not error:
                query_args = {'domain': str(tuple(domain))}
                error = procedure.with_context(context).run_action(write=write, query_args=query_args)
                if not error:
                    error = procedure.with_context(context).run_verification(write=write, query_args=query_args)
            
        elif procedure.action_type == 'method':
            try:
                procedure.with_context(context).run_method(edi_file=edi_file)
                error = False
            except Exception as e:
                error = True
                if e and isinstance(e.args, tuple):
                    for i in e.args:
                        if msg:
                            msg = '%s\n%s'%(error, i)
                        else:
                            msg = i
        
                    _logger.warning(msg)

        try:
            procedure.write({'last_date': fields.Datetime.now(), 'check': error and 'error' or 'done', 'log': msg})
        except:
            pass
        
        return not error, msg
    
    
    def compute_file_name(self, path, name, record_id=0, model='?', iteration=0):
        if path and path[-1] != '/':
            path = '%s/'%(path)
            
        name = name.replace(' ', '_')
        if '%ID' in name:
            name = name.replace('%ID', str(record_id))
            
        if '%MODEL' in name:
            name = name.replace('%MODEL', model)
            
        if '%NUM' in name:
            name = name.replace('%NUM', str(iteration))
            
        name = time.strftime(name)
        return '%s%s'%(path, name)
    
    
    @api.multi
    def wkf_draft(self):
        self.write({'state': 'draft'})
        return True
    
    
    @api.multi
    def wkf_active(self):
        self.write({'state': 'active'})
        return True
    
    
    @api.multi
    def wkf_cancel(self):
        self.write({'state': 'cancel'})
        return True
    

 
class edi_transformation_procedure_method_param(models.Model):
    """ 
    EDI transformation procedure method parameters 
    """
    _name = 'edi.transformation.procedure.method.param'
    _description = 'EDI transformation procedure method parameters'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True, size=128)    
    label = fields.Char(string='Parameter name', size=64, required=False)
    required = fields.Boolean(string='Required', default=False)
    value = fields.Text(string='Value')
    help = fields.Text(string='Help')
    type = fields.Char(string='Type', size=8, required=False)
    m2o_model = fields.Char(string='M2O model', size=128, required=False)
    type_label = fields.Char(string='Type', size=32, required=False)
    note = fields.Char(string='Note', size=512, required=False)
    procedure_id = fields.Many2one('edi.transformation.procedure', string='Procedure', required=True, ondelete='cascade')

    
    #===========================================================================
    # FUNCTIONS & BUTTONS
    #===========================================================================
    @api.multi
    def choose_wizard(self):
        for param in self:
            choose_rcs = self.env['edi.choose.m2o'].create({
                                                           'model': param.m2o_model, 
                                                           'param_id': param.id,
                                                           })
            return {
                    'name': _('Choose a record'),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'edi.choose.m2o',
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'context': {'edi_comodel_name': param.m2o_model},
                    'res_id': choose_rcs.id,
                    'nodestroy': True,
                    }



class edi_transformation_history(models.Model):
    """ 
        EDI Transformation history
    """
    _name = 'edi.transformation.history'
    _description = 'EDI Transformation history'
    _order = 'id desc'
    _rec_name = 'processing_id'

    
    @api.model
    def _check_get(self):
        return [
                ('draft', _('Draft')),
                ('done', _('Done')),
                ('error', _('Error')),
                       ]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    processing_id = fields.Many2one('edi.transformation.processing', string='Processing', required=False, ondelete='cascade')
    object_model = fields.Char(string='Object model', size=128, required=False)
    object_id = fields.Integer(string='Object id', default=0, required=False)
    start_date = fields.Datetime(string='Start date')
    end_date = fields.Datetime(string='End date')
    file_ids = fields.One2many('edi.transformation.file', 'history_id',  string='Files')
    check = fields.Selection('_check_get', string='Check')

    
    def get_history(self, object_model, object_id, processing_id, browse=True):
        h_rcs = self.search([ 
                              ('object_model', '=', object_model), 
                              ('object_id', '=', object_id), 
                              ('processing_id', '=', processing_id)], order='start_date desc', limit=browse and 1 or None)
        if h_rcs:
            if browse:
                res = h_rcs
            else:
                res = h_rcs.ids
                
        else:
            if browse:
                res = h_rcs
            else:
                res = []
                
        return res



class edi_transformation_users(models.Model):
    """ 
    EDI Transformation users 
    """
    _name = 'edi.transformation.users'
    _description = 'EDI Transformation users'
    _rec_name = 'user_id'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='cascade')
    procedure_id = fields.Many2one('edi.transformation.procedure', string='Procedure', required=False, ondelete='cascade')
    start_date = fields.Date(string='Start date', required=True, default=lambda self: fields.Date.today())
    end_date = fields.Date(string='End date')
    mail = fields.Char(string='Mail', size=256, required=True)
    
    
    #===========================================================================
    # ONCHANGE
    #===========================================================================
    @api.onchange('user_id')
    def uos_id_change_modifier(self):
        mail = ''
        if self.user_id:
            mail = self.user_id.email
        
        self.mail = mail



