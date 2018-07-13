# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.osv import fields as f

class update_variants(models.TransientModel):
    """ 
    Update variants 
    """
    _name = 'update.variants'
    _description = 'Update variants'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    variant_ids = fields.Many2many('product.product',  string='Variants')
    
    copy_fields = fields.Boolean(string='Copy fields')
    copy_customer_ref = fields.Boolean(string='Customer ref')
    copy_supplier_ref = fields.Boolean(string='Supplier ref')
    copy_stock_rule = fields.Boolean(string='Stock rule')
    copy_plan_ctrl = fields.Boolean(string='Plan and control')
    copy_internal_plans = fields.Boolean(string='Internal documents')
    copy_quality_control = fields.Boolean(string='Quality control')
    copy_attributes = fields.Boolean(string='Attributes')
    copy_parameters = fields.Boolean(string='Parameters')
    copy_characteristics = fields.Boolean(string='Characteristics')
    
    def _get_update_vals(self, rcs, remove_columns=[]):
        do_not_copy = ['id', '_log_access', 'create_date', 'create_uid', 'write_date', 'write_uid', 'model_id'] + remove_columns
        return {x:rcs[x] if not isinstance(y, f.many2one) else rcs[x].id for x, y in rcs._columns.iteritems() if not isinstance(y, (f.one2many, f.many2many)) and x not in do_not_copy}
    @api.multi
    def update_products(self):
        if not len(self.variant_ids):
            return
        model_id = self.variant_ids[0].model_id
        if self.copy_fields:
            update_vals = self._get_update_vals(model_id, ['is_model', 'categ_id', 'name', 'code'])
        for variant in self.variant_ids:
            if self.copy_fields:
                variant.write(update_vals)
            if self.copy_customer_ref:
                for cinfo in model_id.cinfo_ids:
                    cinfo_child = self.env['product.customerinfo'].search([('product_id', '=', variant.id), ('model_id', '=', cinfo.id)])
                    if len(cinfo_child):
                        vals = self._get_update_vals(cinfo, ['product_id'])
                        cinfo_child.write(vals)
                        for price in cinfo.pricelist_ids:
                            price_child = self.env['pricelist.customerinfo'].search([('cinfo_id', '=', cinfo_child.id), ('model_id', '=', price.id)])
                            if len(price_child):
                                vals = self._get_update_vals(price, ['cinfo_id'])
                                price_child.write(vals)
                            else:
                                price.copy({'cinfo_id':cinfo_child.id, 'model_id':price.id})
                    else:
                        cinfo.copy({'product_id':variant.id, 'model_id': cinfo.id})
            if self.copy_supplier_ref:
                for sinfo in model_id.sinfo_ids:
                    sinfo_child = self.env['product.supplierinfo'].search([('product_id', '=', variant.id), ('model_id', '=', sinfo.id)])
                    if len(sinfo_child):
                        vals = self._get_update_vals(sinfo, ['product_id'])
                        sinfo_child.write(vals)
                        for price in sinfo.pricelist_ids:
                            price_child = self.env['pricelist.supplierinfo'].search([('sinfo_id', '=', sinfo_child.id), ('model_id', '=', price.id)])
                            if len(price_child):
                                vals = self._get_update_vals(price, ['sinfo_id'])
                                price_child.write(vals)
                            else:
                                price.copy({'sinfo_id':sinfo_child.id, 'model_id':price.id})
                    else:
                        sinfo.copy({'product_id':variant.id, 'model_id':sinfo.id})
            if self.copy_stock_rule:
                for op in model_id.orderpoint_ids:
                    op_child = self.env['stock.warehouse.orderpoint'].search([('product_id', '=', variant.id), ('model_id', '=', op.id)])
                    if len(op_child):
                        vals = self._get_update_vals(op, ['product_id'])
                        op_child.write(vals)
                    else:
                        op.copy({'product_id':variant.id, 'model_id': op.id})
            if self.copy_plan_ctrl:
                for pc in model_id.plan_control_ids:
                    pc_child = self.env['stock.quality.control'].search([('product_id', '=', variant.id), ('model_id', '=', pc.id)])
                    if len(pc_child):
                        vals = self._get_update_vals(pc, ['product_id'])
                        pc_child.write(vals)
                    else:
                        pc.copy({'product_id':variant.id, 'model_id': pc.id})
            if self.copy_internal_plans:
                variant.write({'internal_plan_ids': [(4, internal_plan.id) for internal_plan in model_id.internal_plan_ids]})
                        
            if self.copy_quality_control:
                for qc in model_id.quality_control_ids:
                    qc_child = self.env['quality.control.product'].search([('product_id', '=', variant.id), ('model_id', '=', qc.id)])
                    if len(qc_child):
                        vals = self._get_update_vals(qc, ['product_id'])
                        qc_child.write(vals)
                    else:
                        qc.copy({'product_id':variant.id, 'model_id': qc.id})
            if self.copy_attributes:
                for attr in model_id.common_attribute_ids:
                    attr_child = self.env['common.attribute.model'].search([('product_ids', 'in', [variant.id]), ('model_id', '=', attr.id)])
                    if len(attr_child):
                        vals = self._get_update_vals(attr, ['product_id'])
                        attr_child.write(vals)
                    else:
                        attr.copy({'product_id':variant.id, 'model_id': attr.id})
            if self.copy_parameters:
                for param in model_id.parameter_ids:
                    param_child = self.env['parameter.dimension'].search([('product_id', '=', variant.id), ('model_id', '=', param.id)])
                    if len(param_child):
                        vals = self._get_update_vals(param, ['product_id'])
                        param_child.write(vals)
                    else:
                        param.copy({'product_id':variant.id, 'model_id': param.id})
            if self.copy_characteristics:
                model_id.update_characteristics_variant(variant.id)
            
            
        return {'type': 'ir.actions.client', 'tag': 'reload', }