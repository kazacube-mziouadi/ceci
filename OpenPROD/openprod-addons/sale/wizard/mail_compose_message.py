# -*- coding: utf-8 -*-

from openerp import models, api, fields
from openerp.tools.translate import _

class mail_compose_message(models.TransientModel):
    _inherit = 'mail.compose.message'
    
    @api.multi
    def send_mail(self):
        """
            Surcharge de la fonction d'envoi du mail. En fonction du bouton
            utilisé, on traite la vente différemment.
        """
        context = self.env.context
        if self.model == 'sale.order' and self.id_active:
            sale = self.env['sale.order'].browse(self.id_active)
            if sale.sale_communication_method == 'email':
                wizard_context = dict(context)
                wizard_context['default_sale_id'] = self.id_active
                # Si c'est un devis qu'on envoie, on passe la vente en attente et on rempli les champs de date et d'utilisateur pour le devis
                if context.get('send_quotation'):
                    sale.write({'quotation_date': fields.Date.today(),
                                'quotation_user_id': self.env.user.id})
                    sale.signal_workflow('sale_waiting')
                # Si on valide la commande, on va remplir les dates de départ confirmée des lignes de vente s'il n'y en a pas et on crée le picking et/ou la facture
                # On passe la vente en "En cours"
                elif context.get('validate_order'):
                    generate_picking = False
                    for line in sale.order_line_ids:
                        if not line.confirmed_departure_date:
                            line.write({'confirmed_departure_date': line.departure_date})
                        if (line.product_id.type != 'service') or (line.product_id.type == 'service' and line.product_id.manage_service_delivery):
                            generate_picking = True
                     
                    if sale.sale_invoice_trigger_postpaid:
                        sale.generate_invoice(invoice_trigger='postpaid')
                        
                    if generate_picking:
                        sale.action_generate_picking()
                     
                    sale.signal_workflow('sale_validate')
                    sale.write({'confirmation_date': fields.Datetime.now(),
                                'confirmation_user_id': self.env.user.id})
                         
                elif context.get('conf_delay'):
                    sale.signal_workflow('sale_conf_delay')
                         
                # Si on envoie un accusé de réception, on va remplir la date et l'utilisateur pour l'accusé de réception
                elif context.get('send_ar'):
                    sale.write({'ar_send_date': fields.Datetime.now(),
                                'ar_user_id': self.env.user.id})
                
        context2 = self.env.context.copy()
        context2['thread_model'] = 'sale.order'
        context2['mail_create_nosubscribe'] = True
        return super(mail_compose_message, self.with_context(context2)).send_mail()
    
    
    @api.model
    def get_mail_values(self, res_ids):
        """
            Surcharge de la fonction de création du mail afin de lier le mail à la vente
        """
        results = super(mail_compose_message, self).get_mail_values(res_ids)
        if self.env.context and self.env.context.get('model_objet', '') == 'sale.order':
            for res_id in res_ids:
                results[res_id]['sale_id'] = res_id
            
        return results