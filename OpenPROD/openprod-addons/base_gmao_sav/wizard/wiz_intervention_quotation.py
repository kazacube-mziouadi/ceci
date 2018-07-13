# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError
import time, datetime
import openerp.addons.decimal_precision as dp
from docutils.nodes import line

class wiz_intervention_quotation(models.TransientModel):
    """ 
        Wiz intervention quotation
    """
    _name = 'wiz.intervention.quotation'
    _description = 'Wiz intervention quotation'
    
    @api.model
    def default_get(self, fields_list):
        res = super(wiz_intervention_quotation, self).default_get(fields_list=fields_list)
        res['intervention_id'] = self._context.get('active_id')
        return res
    
    
    @api.one
    @api.depends('park_id')
    def _all_operation_compute(self):
        """
            All resource pour le domaine
        """
        self.all_operation_ids = [x.maintenance_operation_id.id for x in self.park_id.maintenance_operation_ids]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    intervention_id = fields.Many2one('intervention', string='Intervention', required=False, ondelete='cascade')
    customer_id = fields.Many2one('res.partner', string='Customer', required=False, ondelete='cascade')
    line_ids = fields.One2many('wiz.intervention.quotation.line', 'intervention_quotation_id',  string='Lines')
    date = fields.Date(string='Date', default=lambda self: fields.Date.today(), required=False)
    no_order_line_ids = fields.One2many('wiz.intervention.quotation.noorder', 'intervention_quotation_id',  string='Lines')
    
    #===========================================================================
    # Button
    #===========================================================================
    @api.multi
    def action_validation(self):  
        sol_obj = self.env['sale.order.line']
        so_obj = self.env['sale.order']
        product_obj = self.env['product.product']
        for wiz in self:
            if not wiz.line_ids:
                raise except_orm(_('Error'), _('There are not lines.'))
            
            if wiz.intervention_id.sale_id:
                sale_rcs = wiz.intervention_id.sale_id
                if sale_rcs.state != 'draft':
                    raise except_orm(_('Error'), _('The sale has to be in the state draft.'))
                
            else:
                sale_rcs = so_obj.create_sale(customer=wiz.customer_id.id, so_line=None, date=wiz.date, other_data={'requested_date': wiz.date, 'type': 'sav'}, forced_qty=False)
#                                                                                                                 'sale_account_invoice_trigger': 'manual', 
#                                                                                                                 'sale_account_invoiced_on': 'order'
                wiz.intervention_id.write({'sale_id': sale_rcs.id})
                
            currency_rcs = sale_rcs.currency_id
#             sale_rcs.write({'sale_account_invoice_trigger': 'manual', 'sale_account_invoiced_on': 'order'})
            for line in wiz.line_ids:
                if currency_rcs.id != line.currency_id.id:
                    price = product_obj._calcul_price_rate_devise(currency_rcs, line.price, line.currency_id)
                else:
                    price = line.price
                
                values = {'name': line.description,
                          'uom_id': line.uom_id.id,
                          'sec_uom_id': line.uom_id.id,
                          'uoi_id': line.uom_id.id,
                          'uom_qty': line.qty,
                          'sec_uom_qty': line.qty,
                          'uoi_qty': line.qty,
                          'requested_date': wiz.date,
                          'intervention_id': wiz.intervention_id.id,
                        }
                if (line.pmi_id and not line.pmi_id.sale_line_id or not line.pmi_id) and (line.qi_id and not line.qi_id.sale_line_id or not line.qi_id):
                    sol_rc = sol_obj.create_sale_order_line(sale=sale_rcs, product=line.product_id, values=values, forced_qty=True, forced_price_unit=price)
                    if line.pmi_id:
                        line.pmi_id.write({'sale_line_id': sol_rc.id})
                    
                    if line.qi_id:
                        line.qi_id.write({'sale_line_id': sol_rc.id})
                        
                elif line.pmi_id.sale_line_id:
                    values['price_unit'] = price
                    line.pmi_id.sale_line_id.write(values)
                elif line.qi_id.sale_line_id:
                    values['price_unit'] = price
                    line.pmi_id.sale_line_id.write(values)
            
            wiz.intervention_id.write({'is_create_quotation': True})
            return {'name': _('Sale order'),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sale.order',
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'res_id': sale_rcs.id,
                    'nodestroy': True,
                    }
            
        return {'type': 'ir.actions.act_window_close'}
    
    

class wiz_intervention_quotation_line(models.TransientModel):
    """ 
        Wiz intervention quotation line
    """
    _name = 'wiz.intervention.quotation.line'
    _description = 'Wiz intervention quotation line'
    _rec_name = 'product_id'
    
    
    @api.one
    @api.depends('product_id')
    def _uom_category_compute(self):
        """
            Category UoM
        """
        uom_category_id = False
        if self.product_id:
            uom_category_id = self.uom_id.category_id.id
            
        self.uom_category_id = uom_category_id
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    intervention_quotation_id = fields.Many2one('wiz.intervention.quotation', string='Intervention quotation', required=False, ondelete='cascade')
    description = fields.Text(string='Description')
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='cascade')
    qty = fields.Float(string='Qty', default=0.0, required=True, digits=dp.get_precision('Product quantity'))
    price = fields.Float(string='Invoice price', default=0.0, required=True, digits=dp.get_precision('Product price'))
    uom_id = fields.Many2one('product.uom', string='UoM', required=True, ondelete='cascade')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, ondelete='cascade', default=lambda self: self.env.user.company_id.currency_id)
    uom_category_id = fields.Many2one('product.uom.category', compute='_uom_category_compute', string="UOM category", readonly=True)
    pmi_id = fields.Many2one('piece.maintenance.intervention', string='PMI', required=False, ondelete='cascade')
    qi_id = fields.Many2one('quotation.intervention', string='QI', required=False, ondelete='cascade')

    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
            Onchange du produit
        """
        uom_id = False
        category_id = False
        if self.product_id:
            uom_id = self.product_id.uom_id.id
            category_id = self.product_id.uom_id.category_id.id
            
        self.uom_id = uom_id
        self.uom_category_id = category_id
        
        
        
class wiz_intervention_quotation_noorder(models.TransientModel):
    """ 
        Wiz intervention quotation noorder
    """
    _name = 'wiz.intervention.quotation.noorder'
    _description = 'Wiz intervention quotation noorder'
    _rec_name = 'product_id'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    intervention_quotation_id = fields.Many2one('wiz.intervention.quotation', string='Intervention quotation', required=False, ondelete='cascade')
    description = fields.Text(string='Description')
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='cascade')
    