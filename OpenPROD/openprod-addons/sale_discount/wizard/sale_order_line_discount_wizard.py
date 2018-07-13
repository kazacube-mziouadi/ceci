# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
import time, datetime
import openerp.addons.decimal_precision as dp

class sol_discount_wizard(models.TransientModel):
    """ 
        SOL discount wizard
    """
    _name = 'sol.discount.wizard'
    _description = 'Sale order line variable discount'
    _rec_name = 'sale_line_id'
    
    @api.model
    def default_get(self, fields_list):
        res = super(sol_discount_wizard, self).default_get(fields_list=fields_list)
        sale_line = self.env['sale.order.line'].browse(self._context.get('active_id'))
        is_fixed = self._context.get('is_fixed_wizard', False)
        is_variable = self._context.get('is_variable_wizard', False)
        vals_fixed_line = []
        vals_variable_line = []
        if is_fixed:
            fixed_line_rcs = self.env['sale.order.line.fixed.discount'].search([('sale_line_id', '=', sale_line.id)])
            for fixed_line in fixed_line_rcs:
                vals_line = fixed_line.read(load='_classic_write')[0]
                vals_line['discount_id'] = vals_line['id']
                if 'id' in vals_line: del vals_line['id']
                if 'create_uid' in vals_line: del vals_line['create_uid']
                if 'create_date' in vals_line: del vals_line['create_date']
                if 'write_uid' in vals_line: del vals_line['write_uid']
                if 'write_date' in vals_line: del vals_line['write_date']
                if '__last_update' in vals_line: del vals_line['__last_update']
                if 'display_name' in vals_line: del vals_line['display_name']
                vals_fixed_line.append((0, 0, vals_line))
        
        elif is_variable:
            variable_line_rcs = self.env['sale.order.line.variable.discount'].search([('sale_line_id', '=', sale_line.id)])
            for variable_line in variable_line_rcs:
                vals_line = variable_line.read(load='_classic_write')[0]
                vals_line['discount_id'] = vals_line['id']
                if 'id' in vals_line: del vals_line['id']
                if 'create_uid' in vals_line: del vals_line['create_uid']
                if 'create_date' in vals_line: del vals_line['create_date']
                if 'write_uid' in vals_line: del vals_line['write_uid']
                if 'write_date' in vals_line: del vals_line['write_date']
                if '__last_update' in vals_line: del vals_line['__last_update']
                if 'display_name' in vals_line: del vals_line['display_name']
                vals_variable_line.append((0, 0, vals_line))
            
        vals = {
            'sale_line_id': sale_line.id,
            'is_fixed': is_fixed,
            'is_variable': is_variable,
            'fixed_line_ids': vals_fixed_line,
            'variable_line_ids': vals_variable_line,
        }
        res.update(vals)
            
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    sale_line_id = fields.Many2one('sale.order.line', string='Sale line', required=False, ondelete='cascade')
    is_fixed = fields.Boolean(string='Fixed', default=False)
    is_variable = fields.Boolean(string='Variable', default=False)
    fixed_line_ids = fields.One2many('sol.fixed.discount.wizard', 'wizard_id',  string='Fixed lines')
    variable_line_ids = fields.One2many('sol.variable.discount.wizard', 'wizard_id',  string='Variable lines')


    @api.multi
    def validate(self):
        solfd_obj = self.env['sale.order.line.fixed.discount']
        solvd_obj = self.env['sale.order.line.variable.discount']
        for wiz in self:
            if wiz.is_fixed:
                discount_rcs = solfd_obj.search([('sale_line_id', '=', wiz.sale_line_id.id)])
                discount_ids = discount_rcs.ids or []
                fixed_amount = 0
                for fixed_line in wiz.fixed_line_ids:
                    vals_line = fixed_line.read(load='_classic_write')[0]
                    if 'id' in vals_line: del vals_line['id']
                    if 'create_uid' in vals_line: del vals_line['create_uid']
                    if 'create_date' in vals_line: del vals_line['create_date']
                    if 'write_uid' in vals_line: del vals_line['write_uid']
                    if 'write_date' in vals_line: del vals_line['write_date']
                    if '__last_update' in vals_line: del vals_line['__last_update']
                    if 'display_name' in vals_line: del vals_line['display_name']
                    if 'wizard_id' in vals_line: del vals_line['wizard_id']
                    if fixed_line.discount_id:
                        if 'discount_id' in vals_line:  
                            discount_id = vals_line['discount_id']
                            if discount_id in discount_ids:
                                discount_ids.remove(discount_id)

                            del vals_line['discount_id']
                            solfd_obj.browse(discount_id).write(vals_line)
                    else:
                        if 'discount_id' in vals_line: del vals_line['discount_id']
                        vals_line['sale_line_id'] = wiz.sale_line_id.id
                        solfd_obj.create(vals_line)
                    
                    if 'amount' in vals_line:
                        fixed_amount += vals_line['amount']
                
                if discount_ids:
                    solfd_obj.browse(discount_ids).unlink()
                    
                wiz.sale_line_id.write({'fixed_discount': fixed_amount})
            elif wiz.is_variable:
                variable_amount = 0
                type = False
                discount_rcs = solvd_obj.search([('sale_line_id', '=', wiz.sale_line_id.id)])
                discount_ids = discount_rcs.ids or []
                for variable_line in wiz.variable_line_ids:
                    if not type:
                        type = variable_line.type
                    elif type != variable_line.type:
                        raise except_orm(_('All lines must be of the same type!'))
                    
                    vals_line = variable_line.read(load='_classic_write')[0]
                    if 'id' in vals_line: del vals_line['id']
                    if 'create_uid' in vals_line: del vals_line['create_uid']
                    if 'create_date' in vals_line: del vals_line['create_date']
                    if 'write_uid' in vals_line: del vals_line['write_uid']
                    if 'write_date' in vals_line: del vals_line['write_date']
                    if '__last_update' in vals_line: del vals_line['__last_update']
                    if 'display_name' in vals_line: del vals_line['display_name']
                    if 'wizard_id' in vals_line: del vals_line['wizard_id']
                    if variable_line.discount_id:
                        if 'discount_id' in vals_line:  
                            discount_id = vals_line['discount_id']
                            if discount_id in discount_ids:
                                discount_ids.remove(discount_id)
                                
                            del vals_line['discount_id']
                            solvd_obj.browse(discount_id).write(vals_line)
                    else:
                        if 'discount_id' in vals_line: del vals_line['discount_id']
                        vals_line['sale_line_id'] = wiz.sale_line_id.id
                        solvd_obj.create(vals_line)
                    
                    if 'amount' in vals_line:
                        if type == 'cumulative':
                            variable_amount += vals_line['amount']
                        else:
                            if variable_amount == 0:
                                variable_amount = 1
                                
                            variable_amount *= (vals_line['amount']/100+1)
                                                
                if type:
                    if type != 'cumulative':
                        variable_amount = variable_amount and variable_amount*100-100 or 0
                
                if discount_ids:
                    solvd_obj.browse(discount_ids).unlink()
                    
                wiz.sale_line_id.write({'variable_discount': variable_amount})
                
            
        return {'type': 'ir.actions.act_window_close'}



class sol_fixed_discount_wizard(models.TransientModel):
    """ 
        Sale order line fixed discount
    """
    _name = 'sol.fixed.discount.wizard'
    _description = 'Sale order line fixed discount'
    _inherit = 'sale.order.line.fixed.discount'
    _rec_name = 'descriptive'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wizard_id = fields.Many2one('sol.discount.wizard', string='Wizard', required=False, ondelete='cascade')
    discount_id = fields.Many2one('sale.order.line.fixed.discount', string='Discount link', required=False, ondelete='cascade')
    
    

class sol_variable_discount_wizard(models.TransientModel):
    """ 
        Sale order line variable discount
    """
    _name = 'sol.variable.discount.wizard'
    _description = 'Sale order line variable discount'
    _inherit = 'sale.order.line.variable.discount'
    _rec_name = 'descriptive'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wizard_id = fields.Many2one('sol.discount.wizard', string='Wizard', required=False, ondelete='cascade')
    discount_id = fields.Many2one('sale.order.line.variable.discount', string='Discount link', required=False, ondelete='cascade')
    
    
    
class so_discount_wizard(models.TransientModel):
    """ 
        SO discount wizard
    """
    _name = 'so.discount.wizard'
    _description = 'So discount wizard'
    _rec_name = 'sale_id'
    

    @api.model
    def default_get(self, fields_list):
        res = super(so_discount_wizard, self).default_get(fields_list=fields_list)
        mod_obj = self.env['ir.model.data']
        product_id = mod_obj.get_object_reference('sale_discount', 'int_product_discount') and mod_obj.get_object_reference('sale_discount', 'int_product_discount')[-1] or False
        sale = self.env['sale.order'].browse(self._context.get('active_id'))
        price_unit = 0.0
        sec_uom_qty = 1
        if product_id:
            product = self.env['product.product'].browse(product_id)
            customer = product.get_cinfo(partner_id=sale.partner_id.id, property_ids=False)
            uoms = product.get_uoms(pinfo=customer, partner=sale.partner_id, type='out', property_ids=False, with_factor=True)
            qtys = product.get_qtys(1, 
                                     uom_id=uoms['uom_id'], 
                                     sec_uom_id=uoms['sec_uom_id'], 
                                     uoi_id=uoms['uoi_id'], 
                                     by_field='uom', 
                                     dual_unit=product.dual_unit, 
                                     dual_unit_type=product.dual_unit_type, 
                                     factor=uoms['factor'], 
                                     divisor=uoms['divisor'], 
                                     with_raise=True)
            sec_uom_qty = qtys['sec_uom_qty']
        vals = {
            'sale_id': sale.id,
            'partner_id': sale.partner_id.id,
            'product_id': product_id,
            'sec_uom_qty': sec_uom_qty,
        }
        res.update(vals)
        return res
    
    
    @api.model
    def _type_get(self):
        return [
                ('fixed', _('Fixed')),
                ('variable', _('Variable')),
                       ]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    sale_id = fields.Many2one('sale.order', string='Sale', required=False, ondelete='cascade')
    type = fields.Selection('_type_get', string='Type', default='fixed', required=True)
    partner_id = fields.Many2one('res.partner', string='Partner', required=False, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    value = fields.Float(string='Value', default=0.0, required=True)
    sec_uom_qty = fields.Float(string='uom_qty', default=0.0, required=False)
    section_id = fields.Many2one('sale.order.line.section', string='Section', required=False, ondelete='cascade')
    
    
    @api.multi
    def create_sale_line(self):
        sol_obj = self.env['sale.order.line']
        for wiz in self:
            date = wiz.sale_id.requested_date or fields.Datetime.now()
            values = {'sec_uom_qty': wiz.sec_uom_qty, 'requested_date': date}
            if wiz.type == 'fixed':
                price_unit = -wiz.value
                values['name'] = _('Discount %.2f')%(wiz.value)
            else:
                price_unit = -wiz.sale_id.amount_ex_taxes*wiz.value/100
                values['name'] = _('Discount %.2f %%')%(wiz.value)
            
            if wiz.section_id:
                values['section_id'] = wiz.section_id.id
            
            sol_obj.create_sale_order_line(sale=wiz.sale_id, product=wiz.product_id, values=values, forced_qty=True, forced_price_unit=price_unit)
        
        return {'type': 'ir.actions.act_window_close'}
    