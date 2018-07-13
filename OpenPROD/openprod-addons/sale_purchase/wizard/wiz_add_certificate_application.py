# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError

class wiz_add_certificate_application(models.TransientModel):
    """ 
        Wiz add certificate application
    """
    _name = 'wiz.add.certificate.application'
    _description = 'Wiz add certificate application'
    
    
    @api.model
    def _type_get(self):
        return [
                ('resource', _('Resource')),
                ('customer', _('Customer')),
                ('ref_customer', _('Ref customer')),
                ('supplier', _('Supplier')),
                ('ref_supplier', _('Ref supplier')),
                       ]
    
    @api.one
    @api.depends('certicate_template_id')
    def _list_ids_text_compute(self):
        """
            Champ fonction qui permet de stocker la liste des ids de l'objet choisi pour faire un domain et ne pas pouvoir sélectionner un valeur déjà choisie
        """
        self.list_ids_text = self.certicate_template_id and self.certicate_template_id.list_ids_text or '[]'
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    certicate_template_id = fields.Many2one('certificate.template', string='Certificate template', required=True, ondelete='cascade')
    type = fields.Selection('_type_get', string='Type', related='certicate_template_id.type')
    resource_ids = fields.Many2many('mrp.resource', 'mrp_resource_reserve_wiz_aca_rel', 'waca_id', 
                                    'resource_id', string='Resources')
    customer_ids = fields.Many2many('res.partner', 'res_partner_cus_reserve_wiz_aca_rel', 'waca_id', 
                                    'partner_id', string='Customers')
    supplier_ids = fields.Many2many('res.partner', 'res_partner_sup_reserve_wiz_aca_rel', 'waca_id', 
                                    'partner_id', string='Supplier')
    ref_customer_ids = fields.Many2many('product.customerinfo', 'product_customerinfo_reserve_wiz_aca_rel', 'waca_id', 
                                    'customerinfo_id', string='Ref customers')
    ref_supplier_ids = fields.Many2many('product.supplierinfo', 'product_supplierinfo_reserve_wiz_aca_rel', 'waca_id', 
                                    'supplierinfo_id', string='Ref customers')
    list_ids_text = fields.Text(string='List ids text', compute='_list_ids_text_compute')
    
    #===========================================================================
    # BUTTON
    #===========================================================================
    @api.multi
    def button_validate(self):
        """
            Fonction de créer des certificats d'applications
        """
        for wiz in self:
            list_vals = wiz.prepa_create_line()
            if list_vals:
                cla_obj = self.env['certificate.line.application']
                for vals in list_vals:
                    cla_obj.create(vals)
                
            return True
    
    
    def prepa_create_line(self):
        """
            Préparation création certificat d'application
        """
        list_vals = []
        if self.type == 'resource' and self.resource_ids:
            for resource in self.resource_ids:
                list_vals.append({'resource_id': resource.id, 'certicate_template_id': self.certicate_template_id.id, 'name': resource.name})
                
        elif self.type == 'supplier' and self.supplier_ids:
            for supplier in self.supplier_ids:
                list_vals.append({'supplier_id': supplier.id, 'certicate_template_id': self.certicate_template_id.id, 'name': supplier.name})
                
        elif self.type == 'ref_supplier' and self.ref_supplier_ids:
            for ref_supplier in self.ref_supplier_ids:
                list_vals.append({'ref_supplier_id': ref_supplier.id, 'certicate_template_id': self.certicate_template_id.id, 'name': ref_supplier.partner_id.name})
                
        elif self.type == 'customer' and self.customer_ids:
            for customer in self.customer_ids:
                list_vals.append({'customer_id': customer.id, 'certicate_template_id': self.certicate_template_id.id, 'name': customer.name})
                
        elif self.type == 'ref_customer' and self.ref_customer_ids:
            for ref_customer in self.ref_customer_ids:
                list_vals.append({'ref_customer_id': ref_customer.id, 'certicate_template_id': self.certicate_template_id.id, 'name': ref_customer.partner_id.name})
            
        return list_vals
            
            
            
        
        