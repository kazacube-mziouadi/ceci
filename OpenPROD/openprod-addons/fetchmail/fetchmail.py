# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import poplib
import time
from imaplib import IMAP4
from imaplib import IMAP4_SSL
from poplib import POP3
from poplib import POP3_SSL
from openerp import models, api, fields
from openerp import tools, api, SUPERUSER_ID
from openerp.tools.translate import _
from openerp.exceptions import UserError

_logger = logging.getLogger(__name__)
MAX_POP_MESSAGES = 50
MAIL_TIMEOUT = 60

# Workaround for Python 2.7.8 bug https://bugs.python.org/issue23906
poplib._MAXLINE = 65536


class fetchmail_server(models.Model):
    """ 
    Incoming POP/IMAP mail server 
    """
    _name = 'fetchmail.server'
    _description = 'Incoming POP/IMAP mail server'
    _order = 'priority'

    
    @api.model
    def _state_get(self):
        return [
                ('draft', _('Not Confirmed')),
                ('done', _('Confirmed')),
                
                       ]

    
    @api.model
    def _type_get(self):
        return [
                ('pop', _('POP Server')),
                ('imap', _('IMAP Server')),
                ('local', _('Local Server')),
                       ]

    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(required=True, size=256)
    active = fields.Boolean(string='Active', default=True)
    state = fields.Selection('_state_get', string='State', default='draft')
    server = fields.Char(string='Server name', size=256, required=True, readonly=True, help="Hostname or IP of the mail server", states={'draft':[('readonly', False)]})
    port = fields.Integer(string='Port', required=True, readonly=True, states={'draft':[('readonly', False)]})
    type = fields.Selection('_type_get', string='Type', default='pop', select=True, required=True)
    is_ssl = fields.Boolean(string='SSL/TLS', help="Connections are encrypted with SSL/TLS through a dedicated port (default: IMAPS=993, POP3S=995)", default=False)
    attach = fields.Boolean(string='Keep Attachments', help="Whether attachments should be downloaded. "
                                                         "If not enabled, incoming emails will be stripped of any attachments before being processed", default=True)
    original = fields.Boolean(string='Keep Original', help="Whether a full original copy of each email should be kept for reference"
                                                        "and attached to each processed message. This will usually double the size of your message database.", default=False)
    date = fields.Datetime(string='Last Fetch Date', readonly=True)
    user = fields.Char(string='Username', size=256, readonly=True, states={'draft':[('readonly', False)]})
    password = fields.Char(string='Password', size=256, readonly=True, states={'draft':[('readonly', False)]})  
    action_id = fields.Many2one('ir.action.server', string='Server action', required=False, ondelete='restrict', help="Optional custom server action to trigger for each incoming mail, "
                                                                               "on the record that was created or updated by this mail")    
    object_id = fields.Many2one('ir.model', string='Create a New Record', help="Process each incoming mail as part of a conversation "
                                                                                             "corresponding to this document type. This will create "
                                                                                             "new documents for new conversations, or attach follow-up "
                                                                                             "emails to the existing conversations (documents).", required=True, ondelete='restrict')  
    priority = fields.Integer(string='Server Priority', default=10, readonly=True, states={'draft':[('readonly', False)]}, help="Defines the order of processing, "
                                                                                                                  "lower values mean higher priority")
    message_ids = fields.One2many('mail.mail', 'fetchmail_server_id',  string='Messages', readonly=True)
    configuration = fields.Text(string='Configuration', readonly=True)
    script = fields.Char(string='Script', size=256, readonly=True, default='/mail/static/scripts/openerp_mailgate.py')
    location_tmp = fields.Char(string='Location temporary', size=256, required=False, help="Specify a temporary location (ex: /tmp)")

    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('type', 'is_ssl', 'object_id')
    def onchange_server_type(self):
        port = 0
        if self.type == 'pop':
            port = self.is_ssl and 995 or 110
        elif self.type == 'imap':
            port = self.is_ssl and 993 or 143
        else:
            self.server = ''
            
        self.port = port
        conf = {
            'dbname' : self.env.cr.dbname,
            'uid' : self.env.user.id,
            'model' : 'MODELNAME',
        }
        if self.object_id:
            r = self.object_id.read(['model'])
            conf['model']=r[0]['model']
            
        self.configuration = """Use the below script with the following command line options with your Mail Transport Agent (MTA)

                                openerp_mailgate.py --host=HOSTNAME --port=PORT -u %(uid)d -p PASSWORD -d %(dbname)s
                                
                                Example configuration for the postfix mta running locally:
                                
                                /etc/postfix/virtual_aliases:
                                @youdomain openerp_mailgate@localhost
                                
                                /etc/aliases:
                                openerp_mailgate: "|/path/to/openerp-mailgate.py --host=localhost -u %(uid)d -p PASSWORD -d %(dbname)s"
                                
                                """ % conf


    #===========================================================================
    # Function/Button
    #===========================================================================
    @api.multi
    def set_draft(self):
        self.write({'state':'draft'})


    @api.one
    def connect(self):
        """
            Fonction de connexion au serveur de mail
        """
        if self.type == 'imap':
            if self.is_ssl:
                connection = IMAP4_SSL(self.server, int(self.port))
            else:
                connection = IMAP4(self.server, int(self.port))
            connection.login(self.user, self.password)
        elif self.type == 'pop':
            if self.is_ssl:
                connection = POP3_SSL(self.server, int(self.port))
            else:
                connection = POP3(self.server, int(self.port))
            #TODO: use this to remove only unread messages
            #connection.user("recent:"+server.user)
            connection.user(self.user)
            connection.pass_(self.password)
        # Add timeout on socket
        connection.sock.settimeout(MAIL_TIMEOUT)
        return connection
    
    
    @api.multi
    def button_confirm_login(self):
        """
            Fonction de confirmation de connexion
        """
        for server in self:
            try:
                connection = server.connect()
                server.write({'state':'done'})
            except Exception, e:
                _logger.info("Failed to connect to %s server %s.", server.type, server.name, exc_info=True)
                raise UserError(_("Connection test failed: %s") % tools.ustr(e))
            finally:
                try:
                    if connection:
                        if server.type == 'imap':
                            connection.close()
                        elif server.type == 'pop':
                            connection.quit()
                except Exception:
                    # ignored, just a consequence of the previous exception
                    pass
        return True
    
    
    @api.multi
    def _fetch_mails(self):
        if not self.ids:
            self = self.search([('state','=','done'), ('type','in',['pop', 'imap'])])
            
        return self.fetch_mail()

    
    @api.multi
    def fetch_mail(self):
        """WARNING: meant for cron usage only - will commit() after each email!"""
        context = self.env.context.copy()
        context['fetchmail_cron_running'] = True
        mail_thread = self.env['mail.thread']
        count_number_mail = {}
        for server in self:
            _logger.info('start checking for new emails on %s server %s', server.type, server.name)
            context.update({'fetchmail_server_id': server.id, 'server_type': server.type})
            count, failed = 0, 0
            imap_server = False
            pop_server = False
            count_number_mail[server.id] = 0
            if server.type == 'imap':
                try:
                    imap_server = server.connect()
                    if isinstance(imap_server, list):
                        imap_server = imap_server[0]
                        
                    imap_server.select()
                    result, data = imap_server.search(None, '(UNSEEN)')
                    for num in data[0].split():
                        res_id = None
                        result, data = imap_server.fetch(num, '(RFC822)')
                        imap_server.store(num, '-FLAGS', '\\Seen')
                        try:
                            res_id = mail_thread.message_process(server.object_id.model,
                                                                 data[0][1],
                                                                 save_original=server.original,
                                                                 strip_attachments=(not server.attach),
                                                                 context=context)
                        except Exception:
                            _logger.info('Failed to process mail from %s server %s.', server.type, server.name, exc_info=True)
                            failed += 1
                            
                        if res_id:
                            count_number_mail[server.id] += 1
                            
                        if res_id and server.action_id:
                            server.action_id.with_context({'active_id': res_id, 'active_ids': [res_id], 'active_model': context.get("thread_model", server.object_id.model)}).run()
                        
                        imap_server.store(num, '+FLAGS', '\\Seen')
                        self.env.cr.commit()
                        count += 1
                        
                    _logger.info("Fetched %d email(s) on %s server %s; %d succeeded, %d failed.", count, server.type, server.name, (count - failed), failed)
                except Exception:
                    _logger.info("General failure when trying to fetch mail from %s server %s.", server.type, server.name, exc_info=True)
                finally:
                    if imap_server:
                        imap_server.close()
                        imap_server.logout()
                        
            elif server.type == 'pop':
#                 try:
                while True:
                    pop_server = server.connect()
                    if isinstance(pop_server, list):
                        pop_server = pop_server[0]
                        
                    (numMsgs, totalSize) = pop_server.stat()
                    pop_server.list()
                    for num in range(1, min(MAX_POP_MESSAGES, numMsgs) + 1):
                        (header, msges, octets) = pop_server.retr(num)
                        msg = '\n'.join(msges)
                        res_id = None
                        try:
                            res_id = mail_thread.message_process(server.object_id.model, msg, custom_values=None, save_original=server.original, strip_attachments=(not server.attach), context=context)
                            pop_server.dele(num)
                        except Exception:
                            _logger.info('Failed to process mail from %s server %s.', server.type, server.name, exc_info=True)
                            failed += 1
                        
                        if res_id:
                            count_number_mail[server.id] += 1
                            
                        if res_id and server.action_id:
                            server.action_id.with_context({'active_id': res_id, 'active_ids': [res_id], 'active_model': context.get("thread_model", server.object_id.model)}).run()
                        
                        self.env.cr.commit()
                        
                    if numMsgs < MAX_POP_MESSAGES:
                        break
                    
                    pop_server.quit()
                    _logger.info("Fetched %d email(s) on %s server %s; %d succeeded, %d failed.", numMsgs, server.type, server.name, (numMsgs - failed), failed)
#                 except Exception:
#                     _logger.info("General failure when trying to fetch mail from %s server %s.", server.type, server.name, exc_info=True)
#                 finally:
#                     if pop_server:
#                         pop_server.quit()
                        
            server.write({'date': time.strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)})
        
        if 'return_count_number_mail' in context and context['return_count_number_mail']:
            return count_number_mail
        else:
            return True

    
    @api.model
    def _update_cron(self):
        context = self.env.context.copy()
        if context and context.get('fetchmail_cron_running'):
            return

        try:
            cron = self.env['ir.model.data'].get_object('fetchmail', 'ir_cron_mail_gateway_action')
        except ValueError:
            # Nevermind if default cron cannot be found
            return

        # Enabled/Disable cron based on the number of 'done' server of type pop or imap
        cron.toggle(model=self._name, domain=[('state','=','done'), ('type','in',['pop','imap'])])
        

    @api.model
    def create(self, vals=None):
        context = self.env.context.copy()
        res = super(fetchmail_server, self).create(vals)
        self.with_context(context)._update_cron()
        return res


    @api.multi
    def write(self, vals=None):
        context = self.env.context.copy()
        res = super(fetchmail_server, self).write(vals)
        self.with_context(context)._update_cron()
        return res

    @api.multi
    def unlink(self):
        context = self.env.context.copy()
        res = super(fetchmail_server, self).unlink()
        self.with_context(context)._update_cron()
        return res
    
    
    
class mail_mail(models.Model):
    _inherit = "mail.mail"
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    fetchmail_server_id = fields.Many2one('fetchmail.server', string='Inbound Mail Server', required=False, 
                                          ondelete='restrict',readonly=True, select=True,oldname='server_id')
    mail_import_fetchmail = fields.Char(string='Mail import fetchmail', size=256)
    
    @api.model
    def create(self, vals=None):
        context = self.env.context.copy()
        fetchmail_server_id = context.get('fetchmail_server_id')
        if fetchmail_server_id:
            vals['fetchmail_server_id'] = fetchmail_server_id
            
        return super(mail_mail, self).create(vals)


    @api.multi
    def write(self, vals=None):
        context = self.env.context.copy()
        fetchmail_server_id = context.get('fetchmail_server_id')
        if fetchmail_server_id:
            vals['fetchmail_server_id'] = fetchmail_server_id
            
        res = super(mail_mail, self).write(vals)
        return res
    
    
    
