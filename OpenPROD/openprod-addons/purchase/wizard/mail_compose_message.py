# -*- coding: utf-8 -*-

from openerp import models, api, fields
from openerp.tools.translate import _

class mail_compose_message(models.TransientModel):
    _inherit = 'mail.compose.message'
    

    @api.model
    def get_mail_values(self, res_ids):
        """
            Surcharge de la fonction de création du mail afin de lier le mail à l'achat
        """
        results = super(mail_compose_message, self).get_mail_values(res_ids)
        if self.env.context and self.env.context.get('model_objet', '') == 'purchase.order':
            for res_id in res_ids:
                results[res_id]['purchase_id'] = res_id
            
        return results

    @api.model
    def default_get(self, fields):
        res = super(mail_compose_message, self).default_get(fields)
        if self.env.context.get('model_objet') == 'purchase.order' and 'id_active' in res:
            res['active_domain'] = False
            res['use_active_domain'] = False
            res['res_id'] = res['id_active']
            res['model'] = 'purchase.order'
        return res