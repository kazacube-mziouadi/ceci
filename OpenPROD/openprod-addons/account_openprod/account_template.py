# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.addons.base_openprod import utils

class account_fiscal_position_template(models.Model):
    _inherit = 'account.fiscal.position.template'
    
    @api.multi
    def update_fp(self):
        fp_obj = self.env['account.fiscal.position']
        fp_tax_obj = self.env['account.fiscal.position.tax']
        tax_obj = self.env['account.tax']
        for template_fp_rs in self:
            fp_rss = fp_obj.search([('name', '=', template_fp_rs.name)])
            if not fp_rss:
                fp_rss = fp_obj.create({'name': template_fp_rs.name})
            
            if fp_rss:
                fp_rss.tax_ids.unlink()
                tax_ref_dict = {}
                for tax_template in template_fp_rs.tax_ids:
                    if tax_template.tax_src_id.id not in tax_ref_dict:
                        tax_ref_dict[tax_template.tax_src_id.id] = tax_obj.search([('name', '=', tax_template.tax_src_id.name)], limit=1).id
                        
                    if tax_template.tax_dest_id.id not in tax_ref_dict:
                        tax_ref_dict[tax_template.tax_dest_id.id] = tax_obj.search([('name', '=', tax_template.tax_dest_id.name)], limit=1).id
                    
                    if tax_ref_dict[tax_template.tax_src_id.id] and tax_ref_dict[tax_template.tax_dest_id.id]:
                        if not fp_tax_obj.search([('position_id', '=', fp_rss.id),
                                                  ('tax_src_id', '=', tax_ref_dict[tax_template.tax_src_id.id]),
                                                  ('tax_dest_id', '=', tax_ref_dict[tax_template.tax_dest_id.id])]):
                            fp_tax_obj.create({'position_id': fp_rss.id,
                                               'tax_src_id': tax_ref_dict[tax_template.tax_src_id.id],
                                               'tax_dest_id': tax_ref_dict[tax_template.tax_dest_id.id]})
        
        return True
                    
    
    
class account_tax_template(models.Model):
    _inherit = 'account.tax.template'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    account_payment_id = fields.Many2one('account.account.template', 'Invoice tax account (On payment)', help='Set the account that will be set by default on invoice tax lines for refunds. Leave empty to use the expense account.')
    tax_on_payment = fields.Boolean(default=False)
    refund_account_payment_id = fields.Many2one('account.account.template', 'Refund Tax Account (On payment)', help='Set the account that will be set by default on invoice tax lines for refunds. Leave empty to use the expense account.')
    
    
    def get_fields_to_update(self):
        return ['name',
                'sequence',
                'amount',
                'type',
                'applicable_type',
                'domain',
                'child_depend',
                'python_compute',
                'python_compute_inv',
                'python_applicable',
                'base_sign',
                'tax_sign',
                'ref_base_sign',
                'ref_tax_sign',
                'include_base_amount',
                'description',
                'type_tax_use',
                'price_include',
                'tax_on_payment']
    
    
    @api.multi
    def update_taxes(self):
        tax_obj = self.env['account.tax']
        account_obj = self.env['account.account']
        tax_code_obj = self.env['account.tax.code']
        code = account_obj.search([('type', '=', 'other')], limit=1).code
        code_digits = code and len(account_obj.search([('type', '=', 'other')], limit=1).code) or 0
        for template_rs in self:
            vals = {}
            for f in self.get_fields_to_update():
                vals[f] = template_rs[f]
            
            for account_field in ['account_id', 'refund_account_id', 'account_payment_id', 'refund_account_payment_id']:
                account_template = template_rs[account_field]
                code_main = account_template.code and len(account_template.code) or 0
                code_acc = account_template.code or ''
                if code_main > 0 and code_main <= code_digits and account_template.type != 'view':
                    code_acc = str(code_acc) + (str('0'*(code_digits-code_main)))
                    vals[account_field] = account_obj.search([('code', '=', code_acc)], limit=1).id
                    
            for tax_code_field in ['ref_base_code_id', 'ref_tax_code_id', 'base_code_id', 'tax_code_id']:
                vals[tax_code_field] = tax_code_obj.search([('name', '=', account_template.name)], limit=1).id
                
            vals['parent_id'] = tax_obj.search([('name', '=', account_template.parent_id.name)], limit=1).id
            vals = utils.transform_to_ids(self, vals)
            tax_rs = tax_obj.search([('name', '=', template_rs.name)])
            if tax_rs:
                tax_rs.write(vals)
            else:
                tax_obj.create(vals)
        
        return True
