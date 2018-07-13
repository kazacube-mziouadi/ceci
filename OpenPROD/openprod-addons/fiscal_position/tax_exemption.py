# coding: utf-8
from openerp import models, api, _, fields

class tax_exemption(models.Model):
    _name = 'tax.exemption'
    _rec_name = 'id'


    _sql_constraints = [('date_start_inf_date_end', 'CHECK(date_end is null or date_start <= date_end)', 'The start date is superior than the end date.')]
    
    
    @api.one
    def _get_tax_exemption_binary_filesystem(self):
        attachment_obj = self.env['ir.attachment']
        attachment_rs = attachment_obj.search([('res_model', '=', self._name), ('res_id', '=', self.id), ('binary_field', '=', 'tax_exemption')])
        if attachment_rs:
            self['tax_exemption'] = attachment_rs[0].datas
        else:
            self.file = False
    
    
    @api.one
    def _set_tax_exemption_binary_filesystem(self):
        attachment_obj = self.env['ir.attachment']
        attachment_rs = attachment_obj.search([('res_model', '=', self._name), ('res_id', '=', self.id), ('binary_field', '=', 'tax_exemption'), ('is_binary_field', '=', True)])
        if self.file:
            if attachment_rs:
                attachment_rs.datas = self.file
            else:
                attachment_obj.create({'res_model': self._name, 'res_id': self.id, 'name': 'tax_exemption datas' , 'is_binary_field': True, 'binary_field': 'tax_exemption', 'datas': self.file, 'datas_fname': 'tax_exemption datas'})
                
        else:
            attachment_rs.unlink()
    
  
    @api.one
    @api.depends('date_start', 'date_end')
    def _compute_is_active(self):
        current_date = fields.Date.today()
        self.is_active = self.date_start and self.date_start <= current_date and (not self.date_end or current_date <= self.date_end)
    

    def _is_active_search(self, operator, value):
        current_date = fields.Date.today()
        res = [tax_exemption.id for tax_exemption in self.search([('date_start', '<=', current_date), '|', ('date_end', '=', False), ('date_end', '>=', current_date)])]
        return [('id', 'in', res)]
    
            
    #===========================================================================
    # COLUMNS
    #===========================================================================
    date_start = fields.Date(string='Start date', required=True)
    date_end = fields.Date(string='End date')
    partner_id = fields.Many2one('res.partner', string='Invoiced customer', required=True, domain=[('is_customer', '=', True), ('can_be_charged', '=', True), ('state', '=', 'qualified')])
    max_amount = fields.Integer(string='Invoice maximum amount without taxes')
    currency_id = fields.Many2one('res.currency', related='partner_id.currency_id', string='Currency', readonly=True)
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal position', required=True, ondelete='restrict')
    note_invoice = fields.Text(string='Note printed on invoice', required=True)
    file = fields.Binary(string='File', compute='_get_tax_exemption_binary_filesystem', inverse='_set_tax_exemption_binary_filesystem')
    is_active = fields.Boolean(compute='_compute_is_active', string='Is active', search='_is_active_search')
    exception_tax = fields.Text(string='Exception tax printed on invoice')
    
    
    def get_fiscal_position(self, current_invoice):
        res = False
        # Recherche de la tax exemption :
        tax_exemption_rc = self.search([('partner_id', '=', current_invoice.partner_id.id), ('is_active', '=', True)])
        if tax_exemption_rc:
            # Si max_amount inexistant
            if not tax_exemption_rc.max_amount or tax_exemption_rc.max_amount == 0:
                res = tax_exemption_rc
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
                
                if amounts - credits + current_invoice.amount_untaxed < tax_exemption_rc.max_amount:
                    res = tax_exemption_rc
                
        return res