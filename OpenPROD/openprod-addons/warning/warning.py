# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _


WARNING_HELP = _('Selecting the "Warning" option will notify user with the message. The Message has to be written in the next field.')

class res_partner(models.Model):
    _inherit = 'res.partner'
    
    @api.model
    def _warning_message_get(self):
        return [
            ('no-message', _('No Message')),
            ('warning', _('Warning')),
        ]
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    sale_warn = fields.Selection('_warning_message_get', string='Sales Order', default='no-message', help=WARNING_HELP, required=True)
    sale_warn_msg = fields.Text(string='Message for Sales Order')
    purchase_warn = fields.Selection('_warning_message_get', string='Purchases Order', default='no-message', help=WARNING_HELP, required=True)
    purchase_warn_msg = fields.Text(string='Message for Purchases Order')
        


class product_customerinfo(models.Model):
    _inherit = 'product.customerinfo'
    
    @api.model
    def _warning_message_get(self):
        return [
            ('no-message', _('No Message')),
            ('warning', _('Warning')),
        ]
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    warn = fields.Selection('_warning_message_get', string='Warning', default='no-message', help=WARNING_HELP, required=True)
    warn_msg = fields.Text(string='Warning message')
    


class sale_order(models.Model):
    _inherit = 'sale.order'
    
    @api.onchange('partner_id')
    def _onchange_sale_customer(self):
        """
            Surcharge du onchange des ventes, lorsqu'on sélectionne un partenaire on
            vérifie s'il dispose ou non d'un warning et on l'envoie si c'est le cas.
        """
        warning = {}
        title = False
        message = False
        partner = self.partner_id
        result = super(sale_order, self)._onchange_sale_customer()
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
        
        
        
class purchase_order(models.Model):
    _inherit = 'purchase.order'
    
    @api.onchange('partner_id')
    def _onchange_purchase_supplier(self):
        """
            Surcharge du onchange des achats, lorsqu'on sélectionne un partenaire on
            vérifie s'il dispose ou non d'un warning et on l'envoie si c'est le cas.
        """
        warning = {}
        title = False
        message = False
        partner = self.partner_id
        result = super(purchase_order, self)._onchange_purchase_supplier()
        if not result:
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



class product_product(models.Model):
    _inherit = 'product.product'
    
    @api.model
    def _warning_message_get(self):
        return [
            ('no-message', _('No Message')),
            ('warning', _('Warning')),
        ]
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    sale_line_warn = fields.Selection('_warning_message_get', string='Sales Order Line', help=WARNING_HELP, default='no-message', required=True)
    sale_line_warn_msg = fields.Text(string='Message for Sales Order Line')
    purchase_line_warn = fields.Selection('_warning_message_get', string='Purchases Order Line', help=WARNING_HELP, default='no-message', required=True)
    purchase_line_warn_msg = fields.Text(string='Message for Purchases Order Line')
    


class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
    
    @api.onchange('product_id', 'property_ids')
    def _onchange_product_id(self):
        """
            Surcharge du onchange des lignes de vente, lorsqu'on sélectionne un produit on
            vérifie s'il dispose ou non d'un warning et on l'envoie si c'est le cas.
        """
        res = super(sale_order_line, self)._onchange_product_id()
        product_rc = self.product_id
        if product_rc:
            if product_rc.sale_line_warn != 'no-message':
                res = {
                    'warning': {
                        'title': _("Warning for %s")%product_rc.name,
                        'message': product_rc.sale_line_warn_msg,
                    }
                }
                
        if not product_rc.free_sale:
            cinfo_rc = product_rc.get_cinfo(partner_id=self.sale_order_id.partner_id.id, property_ids=self.property_ids)
            if cinfo_rc and cinfo_rc.warn == 'warning' and cinfo_rc.warn_msg:
                res = {
                    'warning': {
                        'title': _("Warning"),
                        'message': cinfo_rc.warn_msg
                    }
                }
                
        return res



class purchase_order_line(models.Model):
    _inherit = 'purchase.order.line'
    
    @api.onchange('product_id', 'property_ids')
    def _onchange_product_id(self):
        """
            Surcharge du onchange des lignes d'achat. Lorsqu'on sélectionne un produit on
            vérifie s'il dispose ou non d'un warning et on l'envoie si c'est le cas.
        """
        res = super(purchase_order_line, self)._onchange_product_id()
        product = self.product_id
        if product:
            if product.purchase_line_warn != 'no-message':
                res = {
                    'warning': {'title': _("Warning for %s")%product.name,
                    'message': product.purchase_line_warn_msg,}
                }
                 
        return res