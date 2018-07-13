# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.addons.base_openprod.common import get_form_view

class create_quick_purchase(models.TransientModel):
    _inherit = 'create.quick.purchase'
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
            Surcharge du onchange des produits du wizard de création rapide d'achat,
            lorsqu'on sélectionne un produit on vérifie s'il dispose ou non d'un 
            warning et on l'affiche si c'est le cas.
        """
        res = super(create_quick_purchase, self)._onchange_product_id()
        product = self.product_id
        if product:
            if product.purchase_line_warn != 'no-message':
                res = {'warning': {'title': _("Warning for %s") % product.name,
                        'message': product.purchase_line_warn_msg,}
                }
                 
        return res
    
    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """
            Lorsqu'on sélectionne un partenaire on vérifie s'il dispose ou non d'un
            warning et on l'envoie si c'est le cas.
        """
        warning = {}
        title = False
        message = False
        partner = self.partner_id
        result = {}
        if partner:
            if partner.purchase_warn != 'no-message':
                title =  _("Warning for %s") % partner.name
                message = partner.purchase_warn_msg
                warning = {
                        'title': title,
                        'message': message,
                }
                result['warning'] = warning

        return result