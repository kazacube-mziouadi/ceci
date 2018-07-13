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
    
    
    @api.multi
    def compute_taxes(self):
        """
            Calcul des taxes
        """
        tax_line_obj = self.env['account.purchase.tax']
        old_tax_lines_rcs = tax_line_obj.search([('purchase_id', 'in', self.po_ids.ids)])
        if old_tax_lines_rcs:
            old_tax_lines_rcs.unlink()
            
        for po_rc in self.po_ids:
            taxes_grouped = po_rc.get_taxes_values()
            tax_lines = self.env['account.purchase.tax']
            for tax in taxes_grouped.values():
                tax_lines += tax_line_obj.create(tax)
        
    
    @api.model
    def default_get(self, fields_list):
        res = super(wizard_compute_taxes, self).default_get(fields_list=fields_list)
        res['po_ids'] = self.env.context.get('active_ids', [])
        return res