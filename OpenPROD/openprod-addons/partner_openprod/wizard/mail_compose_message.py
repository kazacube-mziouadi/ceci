# -*- coding: utf-8 -*-

from openerp import models, api, fields
from openerp.tools.translate import _
from openerp.addons.base_openprod.common import get_form_view
from openerp.exceptions import except_orm, ValidationError

class mail_message(models.Model):
    _inherit = 'mail.message'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    model_template_id = fields.Many2one('mail.template', string='Model Mail', required=False, ondelete='restrict')
    no_recup = fields.Boolean(string='No recup', default=False)
    
    def action_send_mail(self, email_to, model, edi_select, object_id, mail_id=False, update_context_other=None):
        """
            Fonction qui permet de remplir et d'appeller le wizard d'envoi des mails
            :param email_to: Partenaire auquel on souhaite envoyer le mail
            :type email_to: recordset(res.partner)
            :param model: Objet pour lequel on recherchera un modèle de mail
            :type model: Char (exemple:'sale.order')
            :param edi_select: Permet de passer une valeur edi pour la recherche du modèle
            :type edi_select: Char
            :param object_id: Id de l'objet depuis lequel on envoie le mail
            :type object_id: integer
            :param mail_id: Optionnel: permet de forcer un template de mail
            :type mail_id: recordset(mail.template)
        """
        templates_obj = self.env['mail.template']
        model_obj = self.env['ir.model']
        model_id = model_obj.search([('model', '=', model)], limit=1)
        #Si on a pas passé de modèle spécifique, on recherche celui lié à l'edi et au modèle d'objet
        if not mail_id:
            mail_id = templates_obj.search([('edi_select', '=', edi_select),('model_id', '=', model_id.id)], limit=1)
            if not mail_id:
                mail_id = templates_obj.search([('model_id', '=', model_id.id)], limit=1)
             
        mail_dict = mail_id.get_email_template([object_id])
        attachments = {}
        if mail_dict and mail_dict.get(object_id):
            mail = mail_dict[object_id]
            #On rempli le wizard (destinataire, sujet...)
            context = self.env.context.copy()
            context.update({ 'default_email_from':templates_obj.render_template(mail.email_from, mail.model_id.model, object_id),
                        'default_email_to':templates_obj.render_template(mail.email_to, mail.model_id.model, object_id),
                        'default_email_cc':templates_obj.render_template(mail.email_cc, mail.model_id.model, object_id),
                        'default_reply_to':templates_obj.render_template(mail.reply_to, mail.model_id.model, object_id),
                        'default_subject':templates_obj.render_template(mail.subject, mail.model_id.model, object_id),
                        'default_body':templates_obj.render_template(mail.body_html, mail.model_id.model, object_id),
                        'default_template_id': mail_id.id,
                        'default_use_template': bool(mail),
                        'model_objet': model,
                        'default_id_active': object_id,
                       })
            
            if update_context_other:
                context.update(update_context_other)
                
            #Ajout des éventuelles pièces jointes
            for attach in mail.attachment_ids:
                attachments[attach.datas_fname] = attach.datas
              
            if attachments:
                attachment = attachments
                attachment_obj = self.env['ir.attachment']
                att_ids = []
                for fname, fcontent in attachment.iteritems():
                    data_attach = {
                        'name': fname,
                        'datas': fcontent,
                        'datas_fname': fname,
                        'description': fname,
                        'res_model' : mail.model_id.model,
                        'res_id' : object_id,
                    }
                    att_ids.append(attachment_obj.create(data_attach).id)
             
                context['default_attachment_ids'] = att_ids
            
            #Recherche et renvoi de l'action du wizard
            action_struc = {}
            obj = self.env[model].browse(object_id)
            action_dict = get_form_view(obj, 'partner_openprod.wizard_send_mail')
            if action_dict and action_dict.get('id') and action_dict.get('type'):
                action = self.env[action_dict['type']].browse(action_dict['id'])
                action_struc = action.read()
                action_struc[0]['context'] = context
                action_struc = action_struc[0]
                  
            return action_struc
        else:
            raise ValidationError(_('There is no mail template for %s. Please create a mail model '
                                  'in the configuration menu.'%(model)))
        
        return False
    
    
    
class mail_compose_message(models.TransientModel):
    _inherit = 'mail.compose.message'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    model_template_id = fields.Many2one('mail.template', string='Model Mail', required=False, ondelete='cascade')
    id_active = fields.Integer(string='Active ID', default=0, required=False)
    
    
    @api.multi
    def get_mail_values(self, res_ids):
        results = super(mail_compose_message, self).get_mail_values(res_ids)
        for res_id in results:
            results[res_id]['model_template_id'] = self.template_id and self.template_id.id or False
            
        return results
    
    
    
class wizard_partner_mass_mail(models.TransientModel):
    _name = 'wizard.partner.mass.mail'
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(wizard_partner_mass_mail, self).default_get(fields_list=fields_list)
        res['partner_ids'] = self.env.context.get('active_ids')
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    name = fields.Char(string='Name', size=32, required=False)
    partner_ids = fields.Many2many('res.partner', 'wizard_partner_mass_mail_res_partner_rel', 'wiz_id', 'partner_id', 
                                         string='Patner', copy=False)
    
    
    @api.multi
    def action_validate(self):
        """
            Fonction permettant d'envoyer un mail libre en mass
        """
        for wiz in self:
            context = self.env.context.copy()
            context['default_parent_id'] = False
            email_to = ''
            for partner in wiz.partner_ids:
                if partner.email:
                    if not email_to:
                        email_to = partner.email
                    else:
                        email_to = '%s,%s'%(email_to, partner.email)
                    
            context['default_email_to'] = email_to
            return self.env['mail.message'].with_context(context).action_send_mail(False, partner._name, 'mass_partner', partner.id, update_context_other={'default_email_to': email_to})
    
    
        