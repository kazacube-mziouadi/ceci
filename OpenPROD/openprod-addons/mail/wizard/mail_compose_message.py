# -*- coding: utf-8 -*-

import base64
import re

from openerp import _, api, fields, models, SUPERUSER_ID
from openerp import tools
from openerp.tools.safe_eval import safe_eval as eval


# main mako-like expression pattern
EXPRESSION_PATTERN = re.compile('(\$\{.+?\})')


def _reopen(self, res_id, model):
    return {'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': res_id,
            'res_model': self._name,
            'target': 'new',
            # save original model in context, because selecting the list of available
            # templates requires a model in context
            'context': {
                'default_model': model,
            },
            }


class MailComposer(models.TransientModel):
    """ Generic message composition wizard. You may inherit from this wizard
        at model and view levels to provide specific features.
    """
    _name = 'mail.compose.message'
    _inherit = 'mail.message'
    _description = 'Email composition wizard'
    _log_access = True
    _batch_size = 500

    @api.model
    def default_get(self, fields):
        """ Handle composition mode. Some details about context keys:
            - comment: default mode, model and ID of a record the user comments
                - default_model or active_model
                - default_res_id or active_id
            - reply: active_id of a message the user replies to
                - default_parent_id or message_id or active_id: ID of the
                    mail.message we reply to
                - message.res_model or default_model
                - message.res_id or default_res_id
            - mass_mail: model and IDs of records the user mass-mails
                - active_ids: record IDs
                - default_model or active_model
        """
        result = super(MailComposer, self).default_get(fields)

        result['model'] = result.get('model', self._context.get('active_model'))
        result['res_id'] = result.get('res_id', self._context.get('active_id'))
        parent_id = self.env.context.get('default_parent_id')
        if parent_id:
            mail_id = self.env['mail.mail'].search([('mail_message_id', '=', parent_id)])
            result['subject'] = 'Re: ' + mail_id.subject
            result['email_from'] = mail_id.email_from
            result['email_to'] = mail_id.email_to
        vals = {}
        
        if 'active_domain' in self._context and self._context['active_domain']:  # not context.get() because we want to keep global [] domains
            vals['use_active_domain'] = True
            vals['active_domain'] = '%s' % self._context.get('active_domain')

        for field in vals:
            if field in fields:
                result[field] = vals[field]

        if fields is not None:
            [result.pop(field, None) for field in result.keys() if field not in fields]
        
        return result

    email_to = fields.Char(string="To", required=True)
    use_active_domain = fields.Boolean('Use active domain')
    active_domain = fields.Text('Active domain', readonly=True)
    attachment_ids = fields.Many2many(
        'ir.attachment', 'mail_compose_message_ir_attachments_rel',
        'wizard_id', 'attachment_id', 'Attachments')
    subject = fields.Char(default=False)
    # mass mode options
    notify = fields.Boolean('Notify followers', help='Notify followers of the document (mass post only)')
    template_id = fields.Many2one(
        'mail.template', 'Use template', select=True,
        domain="[('model', '=', model)]")
    email_cc = fields.Char('Cc', help='Carbon copy message recipients')

    @api.multi
    def check_access_rule(self, operation):
        """ Access rules of mail.compose.message:
            - create: if
                - model, no res_id, I create a message in mass mail mode
            - then: fall back on mail.message acces rules
        """
        # Author condition (CREATE (mass_mail))
        if operation == 'create' and self._uid != SUPERUSER_ID:
            # read mail_compose_message.ids to have their values
            message_values = {}
            self._cr.execute('SELECT DISTINCT id, model, res_id FROM "%s" WHERE id = ANY (%%s) AND res_id = 0' % self._table, (self.ids,))
            for mid, rmod, rid in self._cr.fetchall():
                message_values[mid] = {'model': rmod, 'res_id': rid}
            # remove from the set to check the ids that mail_compose_message accepts
            author_ids = [mid for mid, message in message_values.iteritems()
                          if message.get('model') and not message.get('res_id')]
            self = self.browse(list(set(self.ids) - set(author_ids)))  # not sure slef = ...

        return super(MailComposer, self).check_access_rule(operation)

    @api.multi
    def _notify(self, force_send=False, user_signature=True):
        """ Override specific notify method of mail.message, because we do
            not want that feature in the wizard. """
        return

    @api.model
    def get_record_data(self, values):
        """ Returns a defaults-like dict with initial values for the composition
        wizard when sending an email related a previous email (parent_id) or
        a document (model, res_id). This is based on previously computed default
        values. """
        result, subject = {}, False
        if values.get('parent_id'):
            parent = self.env['mail.message'].browse(values.get('parent_id'))
            result['record_name'] = parent.record_name,
            subject = tools.ustr(parent.subject or parent.record_name or '')
            if not values.get('model'):
                result['model'] = parent.model
            if not values.get('res_id'):
                result['res_id'] = parent.res_id
        elif values.get('model') and values.get('res_id'):
            doc_name_get = self.env[values.get('model')].browse(values.get('res_id')).name_get()
            result['record_name'] = doc_name_get and doc_name_get[0][1] or ''
            subject = tools.ustr(result['record_name'])

        re_prefix = _('Re:')
        if subject and not (subject.startswith('Re:') or subject.startswith(re_prefix)):
            subject = "%s %s" % (re_prefix, subject)
        result['subject'] = subject

        return result

    #------------------------------------------------------
    # Wizard validation and send
    #------------------------------------------------------
    # action buttons call with positionnal arguments only, so we need an intermediary function
    # to ensure the context is passed correctly
    @api.multi
    def send_mail_action(self):
        return self.send_mail()

    @api.multi
    def send_mail(self, auto_commit=False):
        """ Process the wizard content and proceed with sending the related
            email(s), rendering any template patterns on the fly if needed. """
        for wizard in self:
            Mail = self.env['mail.mail']
            # Duplicate attachments linked to the email.template.
            # Indeed, basic mail.compose.message wizard duplicates attachments in mass
            # mailing mode. But in 'single post' mode, attachments of an email template
            # also have to be duplicated to avoid changing their ownership.
            if wizard.template_id:
                # template user_signature is added when generating body_html
                # mass mailing: use template auto_delete value -> note, for emails mass mailing only
                Mail = Mail.with_context(mail_notify_user_signature=False, mail_server_id=wizard.template_id.mail_server_id.id)

            # Mass Mailing
            res_ids = [wizard.res_id]

            batch_size = int(self.env['ir.config_parameter'].sudo().get_param('mail.batch_size')) or self._batch_size
            sliced_res_ids = [res_ids[i:i + batch_size] for i in range(0, len(res_ids), batch_size)]

            for res_ids in sliced_res_ids:
                batch_mails = Mail
                all_mail_values = wizard.get_mail_values(res_ids)
                for res_id, mail_values in all_mail_values.iteritems():    
                    batch_mails |= Mail.create(mail_values)
                batch_mails.send(auto_commit=auto_commit)

        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def get_mail_values(self, res_ids):
        """Generate the values that will be used by send_mail to create mail_messages
        or mail_mails. """
        self.ensure_one()
        results = dict.fromkeys(res_ids, False)
        
        # render all template-based value at once
        rendered_values = self.render_message(res_ids)
        # compute alias-based reply-to in batch
        reply_to_value = dict.fromkeys(res_ids, None)

        for res_id in res_ids:
            # static wizard (mail.message) values
            mail_values = {
                'subject': self.subject,
                'body': self.body or '',
                'attachment_ids': [attach.id for attach in self.attachment_ids],
                'author_id': self.author_id.id,
                'email_from': self.email_from,
                'record_name': self.record_name,
                'email_to': self.email_to,
                'email_cc': self.email_cc,
            }
            # mass mailing: rendering override wizard static values
            # always keep a copy, reset record name (avoid browsing records)
            mail_values.update(notification=True, model=self.model, res_id=res_id, record_name=False)
            # auto deletion of mail_mail
            if 'mail_auto_delete' in self._context:
                mail_values['auto_delete'] = self._context.get('mail_auto_delete')
            # rendered values using template
            email_dict = rendered_values[res_id]
            mail_values.update(email_dict)
            mail_values.pop('reply_to')
            if reply_to_value.get(res_id):
                mail_values['reply_to'] = reply_to_value[res_id]
            if not mail_values.get('reply_to'):
                mail_values['reply_to'] = mail_values['email_from']
            # mail_mail values: body -> body_html
            mail_values['body_html'] = mail_values.get('body', '')

            # process attachments: should not be encoded before being processed by message_post / mail_mail create
            mail_values['attachments'] = [(name, base64.b64decode(enc_cont)) for name, enc_cont in email_dict.pop('attachments', list())]
            attachment_ids = []
            for attach_id in mail_values.pop('attachment_ids'):
                new_attach_id = self.env['ir.attachment'].browse(attach_id).copy({'res_model': self._name, 'res_id': self.id})
                attachment_ids.append(new_attach_id.id)
            mail_values['attachment_ids'] = self._message_preprocess_attachments(
                mail_values.pop('attachments', []),
                attachment_ids, 'mail.message', 0)
            
            mail_values['email_cc'] = self.email_cc
            results[res_id] = mail_values
        return results

    @api.model
    def _message_preprocess_attachments(self, attachments, attachment_ids, attach_model, attach_res_id):
        """ Preprocess attachments for mail_thread.message_post() or mail_mail.create().

        :param list attachments: list of attachment tuples in the form ``(name,content)``,
                                 where content is NOT base64 encoded
        :param list attachment_ids: a list of attachment ids, not in tomany command form
        :param str attach_model: the model of the attachments parent record
        :param integer attach_res_id: the id of the attachments parent record
        """
        m2m_attachment_ids = []
        if attachment_ids:
            filtered_attachment_ids = self.env['ir.attachment'].sudo().search([
                ('res_model', '=', 'mail.compose.message'),
                ('create_uid', '=', self._uid),
                ('id', 'in', attachment_ids)])
            if filtered_attachment_ids:
                filtered_attachment_ids.write({'res_model': attach_model, 'res_id': attach_res_id})
            m2m_attachment_ids += [(4, id) for id in attachment_ids]
        # Handle attachments parameter, that is a dictionary of attachments
        for name, content in attachments:
            if isinstance(content, unicode):
                content = content.encode('utf-8')
            data_attach = {
                'name': name,
                'datas': base64.b64encode(str(content)),
                'datas_fname': name,
                'description': name,
                'res_model': attach_model,
                'res_id': attach_res_id,
            }
            m2m_attachment_ids.append((0, 0, data_attach))
        return m2m_attachment_ids

    #------------------------------------------------------
    # Template methods
    #------------------------------------------------------

    @api.multi
    @api.onchange('template_id')
    def onchange_template_id_wrapper(self):
        self.ensure_one()
        values = self.onchange_template_id(self.template_id.id, self.model, self.res_id)['value']
        for fname, value in values.iteritems():
            setattr(self, fname, value)

    @api.multi
    def onchange_template_id(self, template_id, model, res_id):
        """ - mass_mailing: we cannot render, so return the template values
            - normal mode: return rendered values
            /!\ for x2many field, this onchange return command instead of ids
        """
        values = {}
        if not self.env.context.get('no_mail_onchange'):
            if template_id:
                values = self.generate_email_for_composer(template_id, [res_id])[res_id]
                # transform attachments into attachment_ids; not attached to the document because this will
                # be done further in the posting process, allowing to clean database if email not send
                Attachment = self.env['ir.attachment']
                for attach_fname, attach_datas in values.pop('attachments', []):
                    data_attach = {
                        'name': attach_fname,
                        'datas': attach_datas,
                        'datas_fname': attach_fname,
                        'res_model': 'mail.compose.message',
                        'res_id': 0,
                        'type': 'binary',  # override default_type from context, possibly meant for another model!
                    }
                    values.setdefault('attachment_ids', list()).append(Attachment.create(data_attach).id)
            else:
                default_values = self.with_context(default_model=model, default_res_id=res_id).default_get(['model', 'res_id', 'parent_id', 'subject', 'body', 'email_from', 'reply_to', 'attachment_ids', 'mail_server_id'])
                values = dict((key, default_values[key]) for key in ['subject', 'body', 'email_from', 'reply_to', 'attachment_ids', 'mail_server_id'] if key in default_values)
     
            if values.get('body_html'):
                values['body'] = values.pop('body_html')
     
            # This onchange should return command instead of ids for x2many field.
            # ORM handle the assignation of command list on new onchange (api.v8),
            # this force the complete replacement of x2many field with
            # command and is compatible with onchange api.v7
            values = self._convert_to_write(self._convert_to_cache(values))

        return {'value': values}

    @api.multi
    def save_as_template(self):
        """ hit save as template button: current form value will be a new
            template attached to the current document. """
        for record in self:
            models = self.env['ir.model'].search([('model', '=', record.model or 'mail.message')])
            model_name = ''
            if models:
                model_name = models.name
            template_name = "%s: %s" % (model_name, tools.ustr(record.subject))
            values = {
                'name': template_name,
                'subject': record.subject or False,
                'body_html': record.body or False,
                'model_id': models.id or False,
                'attachment_ids': [(6, 0, [att.id for att in record.attachment_ids])],
            }
            template = self.env['mail.template'].create(values)
            # generate the saved template
            record.write({'template_id': template.id})
            record.onchange_template_id_wrapper()
            return _reopen(self, record.id, record.model)

    #------------------------------------------------------
    # Template rendering
    #------------------------------------------------------

    @api.multi
    def render_message(self, res_ids):
        """Generate template-based values of wizard, for the document records given
        by res_ids. This method is meant to be inherited by email_template that
        will produce a more complete dictionary, using Jinja2 templates.

        Each template is generated for all res_ids, allowing to parse the template
        once, and render it multiple times. This is useful for mass mailing where
        template rendering represent a significant part of the process.

        Default recipients are also computed, based on mail_thread method
        message_get_default_recipients. This allows to ensure a mass mailing has
        always some recipients specified.

        :param browse wizard: current mail.compose.message browse record
        :param list res_ids: list of record ids

        :return dict results: for each res_id, the generated template values for
                              subject, body, email_from and reply_to
        """
        self.ensure_one()
        multi_mode = True
        if isinstance(res_ids, (int, long)):
            multi_mode = False
            res_ids = [res_ids]

        subjects = self.render_template(self.subject, self.model, res_ids)
        bodies = self.render_template(self.body, self.model, res_ids, post_process=True)
        emails_from = self.render_template(self.email_from, self.model, res_ids)
        replies_to = self.render_template(self.reply_to, self.model, res_ids)

        results = dict.fromkeys(res_ids, False)
        for res_id in res_ids:
            results[res_id] = {
                'subject': subjects[res_id],
                'body': bodies[res_id],
                'email_from': emails_from[res_id],
                'reply_to': replies_to[res_id],
            }

        # generate template-based values
        if self.template_id:
            template_values = self.generate_email_for_composer(
                self.template_id.id, res_ids,
                fields=['email_cc', 'attachment_ids', 'mail_server_id'])
        else:
            template_values = {}

        for res_id in res_ids:
            if template_values.get(res_id):
                # recipients are managed by the template
                # remove attachments from template values as they should not be rendered
                template_values[res_id].pop('attachment_ids', None)
            else:
                template_values[res_id] = dict()
            # update template values by composer values
            template_values[res_id].update(results[res_id])

        return multi_mode and template_values or template_values[res_ids[0]]

    @api.model
    def generate_email_for_composer(self, template_id, res_ids, fields=None):
        """ Call email_template.generate_email(), get fields relevant for
            mail.compose.message, transform email_cc and email_to into partner_ids """
        multi_mode = True
        if isinstance(res_ids, (int, long)):
            multi_mode = False
            res_ids = [res_ids]

        if fields is None:
            fields = ['subject', 'body_html', 'email_from', 'email_cc',  'reply_to', 'attachment_ids', 'mail_server_id', 'email_to']
        returned_fields = fields + ['attachments']
        values = dict.fromkeys(res_ids, False)

        template_values = self.env['mail.template'].with_context(tpl_partners_only=True).browse(template_id).generate_email(res_ids, fields=fields)
        for res_id in res_ids:
            res_id_values = dict((field, template_values[res_id][field]) for field in returned_fields if template_values[res_id].get(field))
            res_id_values['body'] = res_id_values.pop('body_html', '')
            values[res_id] = res_id_values
        
        return multi_mode and values or values[res_ids[0]]

    @api.model
    def render_template(self, template, model, res_ids, post_process=False):
        return self.env['mail.template'].render_template(template, model, res_ids, post_process=post_process)
