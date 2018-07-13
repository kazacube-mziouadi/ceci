# -*- coding: utf-8 -*-
from openerp import models, fields, api, _

class sale_order(models.Model):
    _inherit = 'sale.order'
    
            
    #===========================================================================
    # COLUMNS
    #===========================================================================
    customer_with_exoneration = fields.Text(string='Customer with exoneration')
    related_customer_with_exoneration = fields.Text(related='customer_with_exoneration', string='Customer with exoneration', readonly=True)
    
    
    def compute_fiscal_position(self):
        """
            Fonction permettant de recalculer la position fiscale
        """
        self.subject_deb = False
        self.customer_with_exoneration = False
        if self.delivered_country_id and self.company_id and self.company_id.partner_id:
            # Si le pays livré est le même que le pays de la société, position fiscale de la compagnie
            if self.company_id.partner_id.country_id and self.delivered_country_id.id == self.company_id.partner_id.country_id.id:
                self.sale_account_system_id = self.company_id.country_fiscal_position.id
            # Si le pays est dans l'UE
            elif self.delivered_country_id.id in [country.id for country in self.env.ref('base.europe').country_ids]:
                # Si pas de numero de TVA, recuperation de la position fiscale de la compagnie
                if not self.tva_number:
                    self.sale_account_system_id = self.company_id.country_fiscal_position.id
                # Si num TVA, flag deb a vrai
                else:
                    self.subject_deb = True
                    # Si le pays du facturé est le même que le pays de la société, position fiscaler UE service
                    if self.invoicing_address_id.country_id and self.company_id.partner_id.country_id and self.invoicing_address_id.country_id.id == self.company_id.partner_id.country_id.id:
                        self.sale_account_system_id = self.company_id.free_exchange_area_service_fiscal_position
                    # Sinon position fiscale export UE
                    else:
                        self.sale_account_system_id = self.company_id.high_export_fiscal_position
            
            # Si le pays de livraison est hors UE et hors de la compagny
            else:
                # Si le pays du facturé est le même que le pays de la société, position fiscaler export service
                if self.invoicing_address_id.country_id and self.company_id.partner_id.country_id and self.invoicing_address_id.country_id.id == self.company_id.partner_id.country_id.id:
                    self.sale_account_system_id = self.company_id.high_export_service_fiscal_position
                # Sinon position fiscale export
                else:
                    self.sale_account_system_id = self.company_id.high_export_fiscal_position
                  
        if self.env['tax.exemption'].search([('partner_id', '=', self.delivered_customer_id.id), ('is_active', '=', True)]):
            self.customer_with_exoneration = _('Customer subject to exemption, tax final compute at the invoicing time.')
    
    
    def compute_tva(self):
        """
            Fonction permettant de recalculer la TVA
        """
        taxes_grouped = self.get_taxes_values()
        tax_lines = self.tax_line_ids.browse([])
        for tax in taxes_grouped.values():
            tax_lines += tax_lines.new(tax)
            
        self.tax_line_ids = tax_lines
    
    
    @api.onchange('delivered_customer_id')
    def _onchange_delivered_customer_id(self):
        res = super(sale_order, self)._onchange_delivered_customer_id()
        self.compute_fiscal_position()
        return res
    
    
    @api.onchange('delivered_country_id')
    def _onchange_delivered_country_id(self):
        # Récupération du numéro de TVA
        res = super(sale_order, self)._onchange_delivered_country_id()
        self.compute_fiscal_position()
        # On relance le calcule de la TVA
        self.compute_tva()
        return res
    
    
    @api.onchange('company_id')
    def _onchange_company_id(self):
        self.compute_fiscal_position()
    
    
    @api.onchange('tva_number')
    def _onchange_tva_number(self):            
        self.compute_fiscal_position()
        # Si numero de TVA vide, on relance le calcule de la TVA
        if not self.tva_number:
            self.compute_tva()
    
    
    @api.onchange('invoicing_address_id')
    def _onchange_invoicing_address_id(self):
        self.compute_fiscal_position()