# -*- coding: utf-8 -*-
from openerp import _, api, fields, models, tools, SUPERUSER_ID
from openerp.exceptions import UserError
import datetime, openerp, logging, dateutil.relativedelta as relativedelta
import base64
from openerp import report as odoo_report
from urllib import urlencode, quote as quote
_logger = logging.getLogger(__name__)
import email
from email.message import Message
import time
from email.header import decode_header
import dateutil.parser
import pytz



def decode(text):
    """Returns unicode() string conversion of the given encoded smtp header text"""
    if text:
        text = decode_header(text.replace('\r', ''))
        return ''.join([tools.ustr(x[0], x[1]) for x in text])
    
    

def format_tz(pool, cr, uid, dt, tz=False, format=False, context=None):
    context = dict(context or {})
    if tz:
        context['tz'] = tz or pool.get('res.users').read(cr, SUPERUSER_ID, uid, ['tz'])['tz'] or "UTC"
    timestamp = datetime.datetime.strptime(dt, tools.DEFAULT_SERVER_DATETIME_FORMAT)

    ts = openerp.osv.fields.datetime.context_timestamp(cr, uid, timestamp, context)

    if format:
        return ts.strftime(format)
    else:
        lang = context.get("lang")
        lang_params = {}
        if lang:
            res_lang = pool.get('res.lang')
            ids = res_lang.search(cr, uid, [("code", "=", lang)])
            if ids:
                lang_params = res_lang.read(cr, uid, ids[0], ["date_format", "time_format"])
        format_date = lang_params.get("date_format", '%B-%d-%Y')
        format_time = lang_params.get("time_format", '%I-%M %p')

        fdate = ts.strftime(format_date)
        ftime = ts.strftime(format_time)
        return "%s %s%s" % (fdate, ftime, (' (%s)' % tz) if tz else '')

try:
    # We use a jinja2 sandboxed environment to render mako templates.
    # Note that the rendering does not cover all the mako syntax, in particular
    # arbitrary Python statements are not accepted, and not all expressions are
    # allowed: only "public" attributes (not starting with '_') of objects may
    # be accessed.
    # This is done on purpose: it prevents incidental or malicious execution of
    # Python code that may break the security of the server.
    from jinja2.sandbox import SandboxedEnvironment
    mako_template_env = SandboxedEnvironment(
        block_start_string="<%",
        block_end_string="%>",
        variable_start_string="${",
        variable_end_string="}",
        comment_start_string="<%doc>",
        comment_end_string="</%doc>",
        line_statement_prefix="%",
        line_comment_prefix="##",
        trim_blocks=True,               # do not output newline after blocks
        autoescape=True,                # XML/HTML automatic escaping
    )
    mako_template_env.globals.update({
        'str': str,
        'quote': quote,
        'urlencode': urlencode,
        'datetime': datetime,
        'len': len,
        'abs': abs,
        'min': min,
        'max': max,
        'sum': sum,
        'filter': filter,
        'reduce': reduce,
        'map': map,
        'round': round,

        # dateutil.relativedelta is an old-style class and cannot be directly
        # instanciated wihtin a jinja2 expression, so a lambda "proxy" is
        # is needed, apparently.
        'relativedelta': lambda *a, **kw : relativedelta.relativedelta(*a, **kw),
    })
except ImportError:
    _logger.warning("jinja2 not available, templating features will not work!")
    
    
class Message(models.Model):
    """ Messages model: system notification (replacing res.log notifications),
        comments (OpenChatter discussion) and incoming emails. """
    _name = 'mail.message'
    _description = 'Message'
    
    @api.model
    def _get_default_author(self):
        return self.env.user.partner_id
    
    subject = fields.Char('Subject')
    body = fields.Html('Contents', default='', help='Automatically sanitized HTML contents')
    mail_server_id = fields.Many2one('ir.mail_server', 'Outgoing mail server', readonly=1)
    email_from = fields.Char(
        'From',
        help="Email address of the sender. This field is set when no matching partner is found and replaces the author_id field in the chatter.")
    reply_to = fields.Char('Reply-To', help='Reply email address. Setting the reply_to bypasses the automatic thread creation.')
    model = fields.Char('Related Document Model', select=1)
    res_id = fields.Integer('Related Document ID', select=1)
    date = fields.Datetime('Date', default=lambda self: fields.Datetime.now())
    author_id = fields.Many2one(
        'res.partner', 'Author', select=1,
        ondelete='set null', default=_get_default_author,
        help="Author of the message. If not set, email_from may hold an email address that did not match any partner.")
    record_name = fields.Char('Message Record Name', help="Name get of the related document.")
    #partner_ids = fields.Many2many('res.partner', string='Recipients')
    #email_recipients = fields.Char(string="To", required=True)
    message_id = fields.Char('Message-Id', help='Message unique identifier', select=1, readonly=1, copy=False)
    attachment_ids = fields.Many2many(
        'ir.attachment', 'message_attachment_rel',
        'message_id', 'attachment_id',
        string='Attachments',
        help='Attachments are linked to a document through model / res_id and to the message'
             'through this field.')
    message_type = fields.Selection([
        ('email', 'Email'),
        ('comment', 'Comment'),
        ('notification', 'System notification')],
        'Type', required=True, default='email',
        help="Message type: email for email message, notification for system "
             "message, comment for other messages such as user replies",
        oldname='type')
    user_id = fields.Many2one('res.users', string='User', required=False, ondelete='restrict')
    
    @api.model
    def default_get(self, fields_list):
        return super(Message, self).default_get(fields_list)
    
    
    def parse_message(self, message, save_original=False):
        """Parses a string or email.message.Message representing an
           RFC-2822 email, and returns a generic dict holding the
           message details.
 
           :param message: the message to parse
           :type message: email.message.Message | string | unicode
           :param bool save_original: whether the returned dict
               should include an ``original`` entry with the base64
               encoded source of the message.
           :rtype: dict
           :return: A dict with the following structure, where each
                    field may not be present if missing in original
                    message::
 
                    { 'message-id': msg_id,
                      'subject': subject,
                      'from': from,
                      'to': to,
                      'cc': cc,
                      'headers' : { 'X-Mailer': mailer,
                                    #.. all X- headers...
                                  },
                      'subtype': msg_mime_subtype,
                      'body_text': plaintext_body
                      'body_html': html_body,
                      'attachments': [('file1', 'bytes'),
                                       ('file2', 'bytes') }
                       # ...
                       'original': source_of_email,
                    }
        """
        msg_txt = message
        if isinstance(message, str):
            msg_txt = email.message_from_string(message)
 
        # Warning: message_from_string doesn't always work correctly on unicode,
        # we must use utf-8 strings here :-(
        if isinstance(message, unicode):
            message = message.encode('utf-8')
            msg_txt = email.message_from_string(message)
 
        message_id = msg_txt.get('message-id', False)
        msg = {}
 
        if save_original:
            # save original, we need to be able to read the original email sometimes
            msg['original'] = message.as_string() if isinstance(message, Message) \
                                                  else message
            msg['original'] = base64.b64encode(msg['original']) # binary fields are b64
 
        if not message_id:
            # Very unusual situation, be we should be fault-tolerant here
            message_id = time.time()
            msg_txt['message-id'] = message_id
            _logger.info('Parsing Message without message-id, generating a random one: %s', message_id)
 
        fields = msg_txt.keys()
        msg['id'] = message_id
        msg['message-id'] = message_id
        msg['list_name_no_create_crm_document'] = [] 
 
        if 'Subject' in fields:
            msg['subject'] = decode(msg_txt.get('Subject'))
 
        if 'Content-Type' in fields:
            msg['content-type'] = msg_txt.get('Content-Type')
 
        if 'From' in fields:
            msg['from'] = decode(msg_txt.get('From') or msg_txt.get_unixfrom())
 
        if 'To' in fields:
            msg['to'] = decode(msg_txt.get('To'))
 
        if 'Delivered-To' in fields:
            msg['to'] = decode(msg_txt.get('Delivered-To'))
 
        if 'CC' in fields:
            msg['cc'] = decode(msg_txt.get('CC'))
 
        if 'Cc' in fields:
            msg['cc'] = decode(msg_txt.get('Cc'))
 
        if 'Reply-To' in fields:
            msg['reply'] = decode(msg_txt.get('Reply-To'))
 
        if 'Date' in fields:
            try:
                date_hdr = decode(msg_txt.get('Date'))
                parsed_date = dateutil.parser.parse(date_hdr, fuzzy=True)
                if parsed_date.utcoffset() is None:
                    # naive datetime, so we arbitrarily decide to make it
                    # UTC, there's no better choice. Should not happen,
                    # as RFC2822 requires timezone offset in Date headers.
                    stored_date = parsed_date.replace(tzinfo=pytz.utc)
                else:
                    stored_date = parsed_date.astimezone(pytz.utc)
            except Exception:
                _logger.warning('Failed to parse Date header %r in incoming mail '
                                'with message-id %r, assuming current date/time.',
                                msg_txt.get('Date'), message_id)
                stored_date = datetime.datetime.now()
                 
            msg['date'] = stored_date.strftime("%Y-%m-%d %H:%M:%S")
 
        if 'Content-Transfer-Encoding' in fields:
            msg['encoding'] = msg_txt.get('Content-Transfer-Encoding')
 
        if 'References' in fields:
            msg['references'] = msg_txt.get('References')
 
        if 'In-Reply-To' in fields:
            msg['in-reply-to'] = msg_txt.get('In-Reply-To')
 
        msg['headers'] = {}
        msg['subtype'] = 'plain'
        for item in msg_txt.items():
            if item[0].startswith('X-'):
                msg['headers'].update({item[0]: item[1]})
        if not msg_txt.is_multipart() or 'text/plain' in msg.get('content-type', ''):
            encoding = msg_txt.get_content_charset()
            body = tools.ustr(msg_txt.get_payload(decode=True), encoding, errors='replace')
            if 'text/html' in msg.get('content-type', ''):
                msg['body_html'] =  body
                msg['subtype'] = 'html'
                body = tools.html2plaintext(body)
            else:
                msg['body_html'] =  body
                 
            msg['body_text'] = tools.ustr(body, encoding, errors='replace')
 
        attachments = []
        if msg_txt.is_multipart() or 'multipart/alternative' in msg.get('content-type', ''):
            body = ""
            if 'multipart/alternative' in msg.get('content-type', ''):
                msg['subtype'] = 'alternative'
            else:
                msg['subtype'] = 'mixed'
             
            msg['parse_content_id'] = {}
            for part in msg_txt.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
 
                encoding = part.get_content_charset()
                try:
                    filename = decode(part.get_filename())
                except:
                    filename = part.get_filename()
                    
                if part.get_content_maintype()=='text':
                    content = part.get_payload(decode=True)
                    if filename:
                        attachments.append((filename, content))
                    content = tools.ustr(content, encoding, errors='replace')
                    if part.get_content_subtype() == 'html':
                        msg['body_html'] = content
                        msg['subtype'] = 'html' # html version prevails
                        body = tools.ustr(tools.html2plaintext(content))
                        body = body.replace('&#13;', '')
                    elif part.get_content_subtype() == 'plain':
                        body = content
                        msg['body_html'] = content
                elif part.get_content_maintype() in ('application', 'image'):
                    if not filename and part.get_content_maintype() == 'image' and part.values() and len(part.values()) == 3:
                        filename = part.values()[-1].replace('>','')
                        filename = filename.replace('<','')
                         
                    if filename :
                        attachments.append((filename,part.get_payload(decode=True)))
                        if 'Content-ID' in part:
                            if part['Content-ID']:
                                content_id_msg = part['Content-ID'].replace('>','')
                                content_id_msg = content_id_msg.replace('<','')
                                msg['parse_content_id'][filename] = content_id_msg
                                msg.update({'body_html': msg['body_html'].replace(content_id_msg,filename)})
                    
                    else:
                        res = part.get_payload(decode=True)
                        body += tools.ustr(res, encoding, errors='replace')
 
            msg['body_text'] = body
        
        msg['attachments'] = attachments
        # for backwards compatibility:
        msg['body'] = msg['body_text']
        msg['sub_type'] = msg['subtype'] or 'plain'
        return msg

    

class MailTemplate(models.Model):
    "Templates for sending email"
    _name = "mail.template"
    _description = 'Email Templates'
    
    
    body_html = fields.Html('Body', translate=True, sanitize=False, help="Rich-text/HTML version of the message (placeholders may be used here)")
    report_name = fields.Char('Report Filename', translate=True,
                              help="Name to use for the generated report file (may contain placeholders)\n"
                                   "The extension can be omitted and will then come from the report type.")
    report_template = fields.Many2one('ir.actions.report.xml', 'Optional report to print and attach')
    email_to = fields.Char('To (Emails)', help="Comma-separated recipient addresses (placeholders may be used here)")
    email_cc = fields.Char('Cc', help="Carbon copy recipients (placeholders may be used here)")
    reply_to = fields.Char('Reply-To', help="Preferred response address (placeholders may be used here)")
    ref_ir_act_window = fields.Many2one('ir.actions.act_window', 'Sidebar action', readonly=True, copy=False,
                                        help="Sidebar action to make this template available on records "
                                             "of the related document model")
    subject = fields.Char('Subject', translate=True, help="Subject (placeholders may be used here)")
    name = fields.Char('Name')
    attachment_ids = fields.Many2many('ir.attachment', 'email_template_attachment_rel', 'email_template_id',
                                      'attachment_id', 'Attachments',
                                      help="You may attach files to this template, to be added to all "
                                           "emails created from this template")
    user_signature = fields.Boolean('Add Signature',
                                    help="If checked, the user's signature will be appended to the text version "
                                         "of the message")
    email_from = fields.Char('From',
                             help="Sender address (placeholders may be used here). If not set, the default "
                                  "value will be the author's email alias if configured, or email address.")
    model_id = fields.Many2one('ir.model', 'Applies to', help="The kind of document with with this template can be used")
    model = fields.Char('Related Document Model', related='model_id.model', select=True, store=True, readonly=True)
    lang = fields.Char('Language',
                       help="Optional translation language (ISO code) to select when sending out an email. "
                            "If not set, the english version will be used. "
                            "This should usually be a placeholder expression "
                            "that provides the appropriate language, e.g. "
                            "${object.partner_id.lang}.",
                       placeholder="${object.partner_id.lang}")
    mail_server_id = fields.Many2one('ir.mail_server', 'Outgoing Mail Server', readonly=False,
                                     help="Optional preferred server for outgoing mails. If not set, the highest "
                                          "priority one will be used.")
    model_object_field = fields.Many2one('ir.model.fields', string="Field",
                                         help="Select target field from the related document model.\n"
                                              "If it is a relationship field you will be able to select "
                                              "a target field at the destination of the relationship.")
    sub_object = fields.Many2one('ir.model', 'Sub-model', readonly=True,
                                 help="When a relationship field is selected as first field, "
                                      "this field shows the document model the relationship goes to.")
    sub_model_object_field = fields.Many2one('ir.model.fields', 'Sub-field',
                                             help="When a relationship field is selected as first field, "
                                                  "this field lets you select the target field within the "
                                                  "destination document model (sub-model).")
    null_value = fields.Char('Default Value', help="Optional value to use if the target field is empty")
    copyvalue = fields.Char('Placeholder Expression', help="Final placeholder expression, to be copy-pasted in the desired template field.")

    use_default_to = fields.Boolean(
        'Default recipients',
        help="Default recipients of the record:\n"
             "- partner (using id on a partner or the partner_id field) OR\n"
             "- email (using email_from or email field)")

    @api.multi
    def get_email_template(self, res_ids):
        multi_mode = True
        if isinstance(res_ids, (int, long)):
            res_ids = [res_ids]
            multi_mode = False

        if res_ids is None:
            res_ids = [None]
        results = dict.fromkeys(res_ids, False)

        if not self.ids:
            return results
        self.ensure_one()

        langs = self.render_template(self.lang, self.model_id.model, res_ids)
        for res_id, lang in langs.iteritems():
            if lang:
                template = self.with_context(lang=lang)
            else:
                template = self
            results[res_id] = template

        return multi_mode and results or results[res_ids[0]]

    @api.model
    def render_template(self, template_txt, model, res_ids, post_process=False):
        """ Render the given template text, replace mako expressions ``${expr}``
        with the result of evaluating these expressions with an evaluation
        context containing:

         - ``user``: browse_record of the current user
         - ``object``: record of the document record this mail is related to
         - ``context``: the context passed to the mail composition wizard

        :param str template_txt: the template text to render
        :param str model: model name of the document record this mail is related to.
        :param int res_ids: list of ids of document records those mails are related to.
        """
        multi_mode = True
        if isinstance(res_ids, (int, long)):
            multi_mode = False
            res_ids = [res_ids]

        results = dict.fromkeys(res_ids, u"")

        # try to load the template
        try:
            template = mako_template_env.from_string(tools.ustr(template_txt))
        except Exception:
            _logger.info("Failed to load template %r", template_txt, exc_info=True)
            return multi_mode and results or results[res_ids[0]]

        # prepare template variables
        records = self.env[model].browse(filter(None, res_ids))  # filter to avoid browsing [None]
        res_to_rec = dict.fromkeys(res_ids, None)
        for record in records:
            res_to_rec[record.id] = record
        variables = {
            'format_tz': lambda dt, tz=False, format=False, context=self._context: format_tz(self.pool, self._cr, self._uid, dt, tz, format, context),
            'user': self.env.user,
            'ctx': self._context,  # context kw would clash with mako internals
        }
        for res_id, record in res_to_rec.iteritems():
            variables['object'] = record
            try:
                render_result = template.render(variables)
            except Exception:
                _logger.info("Failed to render template %r using values %r" % (template, variables), exc_info=True)
                raise UserError(_("Failed to render template %r using values %r")% (template, variables))
                render_result = u""
            if render_result == u"False":
                render_result = u""
            results[res_id] = render_result

#         if post_process:
#             for res_id, result in results.iteritems():
#                 results[res_id] = self.render_post_process(result)

        return multi_mode and results or results[res_ids[0]]
    
    
    @api.multi
    def generate_email(self, res_ids, fields=None):
        """Generates an email from the template for given the given model based on
        records given by res_ids.

        :param template_id: id of the template to render.
        :param res_id: id of the record to use for rendering the template (model
                       is taken from template definition)
        :returns: a dict containing all relevant fields for creating a new
                  mail.mail entry, with one extra key ``attachments``, in the
                  format [(report_name, data)] where data is base64 encoded.
        """
        self.ensure_one()
        multi_mode = True
        if isinstance(res_ids, (int, long)):
            res_ids = [res_ids]
            multi_mode = False
        if fields is None:
            fields = ['subject', 'body_html', 'email_from', 'email_to', 'email_cc', 'reply_to']

        res_ids_to_templates = self.get_email_template(res_ids)

        # templates: res_id -> template; template -> res_ids
        templates_to_res_ids = {}
        for res_id, template in res_ids_to_templates.iteritems():
            templates_to_res_ids.setdefault(template, []).append(res_id)

        results = dict()
        for template, template_res_ids in templates_to_res_ids.iteritems():
            Template = self.env['mail.template']
            # generate fields value for all res_ids linked to the current template
            if template.lang:
                Template = Template.with_context(lang=template._context.get('lang'))
            for field in fields:
                generated_field_values = Template.render_template(
                    getattr(template, field), template.model_id.model, template_res_ids,
                    post_process=(field == 'body_html'))
                for res_id, field_value in generated_field_values.iteritems():
                    results.setdefault(res_id, dict())[field] = field_value
            # update values for all res_ids
            for res_id in template_res_ids:
                values = results[res_id]
                # body: add user signature, sanitize
                if 'body_html' in fields and template.user_signature:
                    signature = self.env.user.signature
                    if signature:
                        values['body_html'] = tools.append_content_to_html(values['body_html'], signature, plaintext=False)
                if values.get('body_html'):
                    values['body'] = tools.html_sanitize(values['body_html'])
                # technical settings
                values.update(
                    mail_server_id=template.mail_server_id.id or False,
                    model=template.model_id.model,
                    res_id=res_id or False,
                    attachment_ids=[attach.id for attach in template.attachment_ids],
                )
            # Add report in attachments: generate once for all template_res_ids
            if template.report_template and not 'report_template_in_attachment' in self.env.context:
                for res_id in template_res_ids:
                    attachments = []
                    report_name = self.render_template(template.report_name, template.model, res_id)
                    report = template.report_template
                    report_service = report.report_name

                    if report.report_type in ['qweb-html', 'qweb-pdf']:
                        result, format = self.pool['report'].get_pdf(self._cr, self._uid, [res_id], report_service, context=Template._context), 'pdf'
                    else:
                        result, format = odoo_report.render_report(self._cr, self._uid, [res_id], report_service, {'model': template.model}, Template._context)

                    # TODO in trunk, change return format to binary to match message_post expected format
                    result = base64.b64encode(result)
                    if not report_name:
                        report_name = 'report.' + report_service
                    ext = "." + format
                    if not report_name.endswith(ext):
                        report_name += ext
                    attachments.append((report_name, result))
                    results[res_id]['attachments'] = attachments

        return multi_mode and results or results[res_ids[0]]
    
    
    @api.multi
    def send_mail(self, res_id, force_send=False, raise_exception=False, email_to=False, return_browse=False):
        """Generates a new mail message for the given template and record,
           and schedules it for delivery through the ``mail`` module's scheduler.

           :param int res_id: id of the record to render the template with
                              (model is taken from the template)
           :param bool force_send: if True, the generated mail.message is
                immediately sent after being created, as if the scheduler
                was executed for this message only.
           :returns: id of the mail.message that was created
        """
        self.ensure_one()
        Mail = self.env['mail.mail']
        # create a mail_mail based on values, without attachments
        values = self.generate_email(res_id)
        # add a protection against void email_from
        if 'email_from' in values and not values.get('email_from'):
            values.pop('email_from')
            
        if not values.get('email_to') and email_to:
            values['email_to'] = email_to
                
        mail = Mail.create(values)
        if force_send:
            mail.send(raise_exception=raise_exception)
        
        if return_browse:
            return mail  # TDE CLEANME: return mail + api.returns ?
        else:
            return mail.id

    def build_expression(self, field_name, sub_field_name, null_value):
        """Returns a placeholder expression for use in a template field,
        based on the values provided in the placeholder assistant.
        :param field_name: main field name
        :param sub_field_name: sub field name (M2O)
        :param null_value: default value if the target value is empty
        :return: final placeholder expression """
        expression = ''
        if field_name:
            expression = "${object." + field_name
            if sub_field_name:
                expression += "." + sub_field_name
            if null_value:
                expression += " or '''%s'''" % null_value
            expression += "}"
        return expression

    @api.onchange('model_object_field', 'sub_model_object_field', 'null_value')
    def onchange_sub_model_object_value_field(self):
        if self.model_object_field:
            if self.model_object_field.ttype in ['many2one', 'one2many', 'many2many']:
                models = self.env['ir.model'].search([('model', '=', self.model_object_field.relation)])
                if models:
                    self.sub_object = models.id
                    self.copyvalue = self.build_expression(self.model_object_field.name, self.sub_model_object_field and self.sub_model_object_field.name or False, self.null_value or False)
            else:
                self.sub_object = False
                self.sub_model_object_field = False
                self.copyvalue = self.build_expression(self.model_object_field.name, False, self.null_value or False)
        else:
            self.sub_object = False
            self.copyvalue = False
            self.sub_model_object_field = False
            self.null_value = False
            
    @api.multi
    def create_action(self):
        ActWindowSudo = self.env['ir.actions.act_window'].sudo()
        IrValuesSudo = self.env['ir.values'].sudo()
        view = self.env.ref('mail.email_compose_message_wizard_form')

        for template in self:
            src_obj = template.model_id.model

            button_name = _('Send Mail (%s)') % template.name
            action = ActWindowSudo.create({
                'name': button_name,
                'type': 'ir.actions.act_window',
                'res_model': 'mail.compose.message',
                'src_model': src_obj,
                'view_type': 'form',
                'context': "{'default_composition_mode': 'mass_mail', 'default_template_id' : %d, 'default_use_template': True}" % (template.id),
                'view_mode': 'form,tree',
                'view_id': view.id,
                'target': 'new',
                'auto_refresh': 1})
            ir_value = IrValuesSudo.create({
                'name': button_name,
                'model': src_obj,
                'key2': 'client_action_multi',
                'value': "ir.actions.act_window,%s" % action.id})
            template.write({
                'ref_ir_act_window': action.id,
                'ref_ir_value': ir_value.id,
            })

        return True

    @api.model
    def create(self , vals):
        mail_temp = super(MailTemplate, self).create(vals)
        # Ajout du mail dans ir_translation pour toutes les langues
        languages = self.env['res.lang'].sudo().search([])
        for lang in languages:
            values = { 'name': 'mail.template,body_html',
                       'type': 'model',  
                       'state': 'to_translate', 
                       'lang': lang.code, 
                       'res_id': mail_temp.id,
                       'src': vals['body_html'],
                       'value': vals['body_html'],}
            self.env['ir.translation'].sudo().create(values)
        return mail_temp
