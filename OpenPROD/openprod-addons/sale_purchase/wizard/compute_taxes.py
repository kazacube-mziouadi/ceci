# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.exceptions import except_orm
from openerp.tools.translate import _

class wizard_compute_taxes(models.TransientModel):
    """ 
        Wizard compute taxes 
    """
    _name = 'wizard.compute.taxes'
    _description = 'Wizard compute taxes'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    po_ids = fields.Many2many('purchase.order', 'wizard_compute_taxe_po_rel', 'wizard_id', 'po_id',  string='Purchase orders')
    so_ids = fields.Many2many('sale.order', 'wizard_compute_taxe_so_rel', 'wizard_id', 'so_id',  string='Sale orders')
    model = fields.Char(size=64, required=False)
    compute_all = fields.Boolean(default=False, help='Check this field to compute all records')
    
    
    @api.multi
    def compute_taxes(self):
        """
            Calcul des taxes
        """
        if self.model == 'purchase.order':
            tax_line_obj = self.env['account.purchase.tax']
            tax_lines = self.env['account.purchase.tax']
            if self.compute_all:
                order_rcs = self.env['purchase.order'].search([])
            else:
                order_rcs = self.po_ids
                
            old_tax_lines_rcs = tax_line_obj.search([('purchase_id', 'in', order_rcs.ids)])
            if old_tax_lines_rcs:
                old_tax_lines_rcs.unlink()
                
        elif self.model == 'sale.order':
            tax_line_obj = self.env['account.sale.tax']
            tax_lines = self.env['account.sale.tax']
            if self.compute_all:
                order_rcs = self.env['sale.order'].search([])
            else:
                order_rcs = self.so_ids

            old_tax_lines_rcs = tax_line_obj.search([('sale_id', 'in', order_rcs.ids)])
            if old_tax_lines_rcs:
                old_tax_lines_rcs.unlink()
                
        else:
            order_rcs = []
            
        for orcer_rc in order_rcs:
            taxes_grouped = orcer_rc.get_taxes_values()
            for tax in taxes_grouped.values():
                tax_lines += tax_line_obj.create(tax)
        
    
    @api.model
    def default_get(self, fields_list):
        res = super(wizard_compute_taxes, self).default_get(fields_list=fields_list)
        if self.env.context.get('active_model', '') == 'purchase.order':
            res['po_ids'] = self.env.context.get('active_ids', [])
            res['model'] = 'purchase.order'
        elif self.env.context.get('active_model', '') == 'sale.order':
            res['so_ids'] = self.env.context.get('active_ids', [])
            res['model'] = 'sale.order'
            
        return res