# -*- coding: utf-8 -*-
from openerp import models, fields, api, _

class account_invoice(models.Model):
    _inherit = 'account.invoice'
    
            
    #===========================================================================
    # COLUMNS
    #===========================================================================
    tax_exemption_id = fields.Many2one('tax.exemption', string='Tax exemption', ondelete='restrict')
    customer_with_exoneration = fields.Text(string='Customer with exoneration')
    related_fiscal_position_id = fields.Many2one('account.fiscal.position', related='fiscal_position_id', string='Fiscal position', readonly=True)
    related_tax_exemption_id = fields.Many2one('tax.exemption', related='tax_exemption_id', string='Tax exemption', readonly=True)
    related_customer_with_exoneration = fields.Text(related='customer_with_exoneration', string='Customer with exoneration', readonly=True)
    
    
    def compute_fiscal_position_and_tax(self):
        """
            Fonction permettant de recalculer la position fiscale
        """
        self.declaration_deb = False
        self.tax_exemption_id = False
        self.customer_with_exoneration = False
        previous_fiscal_position_id = self.fiscal_position_id
        # Si le client exonéré validé, on prend la position fiscale de l'exonération
        # Recherche de la tax exemption :
        is_exempted = False
        tax_exemption_rc = self.env['tax.exemption'].search([('partner_id', '=', self.partner_id.id), ('is_active', '=', True)])
        if tax_exemption_rc:
            self.customer_with_exoneration = _('Customer subject to exemption, tax final compute at the invoicing time.')
            # Si max_amount inexistant
            if not tax_exemption_rc.max_amount or tax_exemption_rc.max_amount == 0:
                is_exempted = True
            else:
                # Calcul de l'exoneration fiscale
                search_list = [('state', 'in', ['draft', 'open', 'paid']), ('partner_id', '=', tax_exemption_rc.partner_id.id), ('tax_exemption_id', '!=', False), ('date_invoice', '>=', tax_exemption_rc.date_start)]
                if tax_exemption_rc.date_end:
                    search_list.append(('date_invoice', '<=', tax_exemption_rc.date_end))
                 
                invoices_rcs = self.env['account.invoice'].search(search_list)
                amounts = 0
                credits = 0
                for invoice in invoices_rcs:
                    if invoice.journal_id.type == 'sale':
                        amounts += invoice.amount_untaxed
                    elif invoice.journal_id.type == 'purchase':
                        credits += invoice.amount_untaxed
                
                if amounts - credits + self.amount_untaxed < tax_exemption_rc.max_amount:
                    is_exempted = True
                    
        if is_exempted:
            self.fiscal_position_id = tax_exemption_rc.fiscal_position_id
            self.tax_exemption_id = tax_exemption_rc.id
        elif self.delivery_partner_id:
            # Si le pays livré est le même que celui de la société, position fiscale de la compagnie
            if self.partner_id.company_id and self.delivery_country_id.id == self.partner_id.company_id.partner_id.country_id.id:
                self.fiscal_position_id = self.partner_id.company_id.country_fiscal_position.id
            # Sinon, si le pays de livraison est dans l'UE
            elif self.delivery_country_id.id in [country.id for country in self.env.ref('base.europe').country_ids]:
                # Si pas de numero de TVA, recuperation de la position fiscale de la compagnie
                if not self.tva_number:
                    self.fiscal_position_id = self.partner_id.company_id.country_fiscal_position.id
                # Si num TVA, flag deb a vrai
                else:
                    self.declaration_deb = True
                    # Si le pays du facturé est le même que le pays de la société, position fiscaler UE service
                    if self.partner_id.company_id.partner_id.country_id and self.country_id.id == self.partner_id.company_id.partner_id.country_id.id:
                        self.fiscal_position_id = self.partner_id.company_id.free_exchange_area_service_fiscal_position
                    # Sinon position fiscale export UE
                    else:
                        self.fiscal_position_id = self.partner_id.company_id.high_export_fiscal_position
            
            # Si le pays de livraison est hors UE et hors de la compagny
            else:
                # Si le pays du facturé est le même que le pays de la société, position fiscaler export service
                if self.partner_id.company_id.partner_id.country_id and self.country_id.id == self.partner_id.company_id.partner_id.country_id.id:
                    self.fiscal_position_id = self.partner_id.company_id.high_export_service_fiscal_position
                # Sinon position fiscale export
                else:
                    self.fiscal_position_id = self.partner_id.company_id.high_export_fiscal_position
        
        # Si la position fiscale a changé, on recalcul les tax           
        if self.fiscal_position_id != previous_fiscal_position_id:
            if self.type in ['out_invoice', 'out_refund']:
                tax_field = 'sale_taxes_ids'
            else:
                tax_field = 'purchase_taxes_ids'
                
            for invoice_line in self.invoice_line_ids:
                invoice_line.invoice_line_tax_ids =  self.fiscal_position_id.map_tax(invoice_line.product_id[tax_field])
            
            self._onchange_invoice_line_ids()
    
    
    @api.multi
    def action_move_create(self):
        self.compute_fiscal_position_and_tax()
        res = super(account_invoice, self).action_move_create()
        return res
    

    @api.multi
    def button_reset_taxes(self):
        res = super(account_invoice, self).button_reset_taxes()
        self.compute_fiscal_position_and_tax()
        return res
    
    
    @api.onchange('delivery_country_id')
    def _onchange_delivery_country_id(self):
        self.compute_fiscal_position_and_tax()
    
    
    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        super(account_invoice, self)._onchange_partner_id()
        self.compute_fiscal_position_and_tax()
    
    
    @api.onchange('paid_by_id')
    def _onchange_paid_by_id(self):
        super(account_invoice, self)._onchange_paid_by_id()
        self.compute_fiscal_position_and_tax()
    
    
    @api.onchange('tva_number')
    def _onchange_tva_number(self):
        self.compute_fiscal_position_and_tax()