# -*- coding: utf-8 -*-
from openerp import api, tools
from openerp import models, fields, api
    
    
class mail_message(models.Model):
    _inherit = 'mail.message'
    
    @api.model
    def create(self, vals):
        """
            On passe le modèle réel pour l'écriture des messages
        """
        if self.env.context.get('real_thread_model'):
            vals['model'] = self.env.context['real_thread_model']
            
        return super(mail_message, self).create(vals)
    
    
    
class mail_compose_message(models.TransientModel):
    _inherit = 'mail.compose.message'
    
    @api.multi
    def send_mail(self):
        """
            Send mail pour workflow
        """
        context2 = self.env.context.copy()
        if self.model and self.id_active and self.env.context.get('send_mail_wkf_signal'):
            obj = self.env[self.model].browse(self.id_active)
            obj.signal_workflow(self.env.context['send_mail_wkf_signal'])
            context2['thread_model'] = self.model
        if self.model and self.id_active and self.env.context.get('send_mail_method_next'):
            obj = self.env[self.model].browse(self.id_active)
            getattr(obj, self.env.context['send_mail_method_next'])()
                    
        return super(mail_compose_message, self.with_context(context2)).send_mail()