# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.addons.base_openprod.common import get_form_view

class create_quick_sale(models.TransientModel):
    _inherit = 'create.quick.sale'
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
            Surcharge du onchange des produits du wizard de création rapide de vente,
            lorsqu'on sélectionne un produit on vérifie s'il dispose ou non d'un 
            warning et on l'affiche si c'est le cas.
        """
        res = super(create_quick_sale, self)._onchange_product_id()
        product = self.product_id
        if product:
            if product.sale_line_warn != 'no-message':
                res = {'warning': {'title': _("Warning for %s") % product.name,
                        'message': product.sale_line_warn_msg,}
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
            if partner.sale_warn != 'no-message':
                title =  _("Warning for %s") % partner.name
                message = partner.sale_warn_msg
                warning = {
                        'title': title,
                        'message': message,
                }
                result['warning'] = warning
        
        return result