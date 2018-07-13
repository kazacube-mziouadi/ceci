# coding: utf8
from openerp import models, fields, api, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from dateutil.rrule import rrule, MONTHLY
from dateutil.parser import parse

class product_valuation_wizard(models.TransientModel):
    """ 
    Valuation wizard for a single product 
    """
    _name = 'product.valuation.wizard'
    _description = 'Valuation wizard for a single product'
    
    @api.model
    def _month_get(self):
        return [
                    ('01', _('January')), 
                    ('02', _('February')), 
                    ('03', _('March')), 
                    ('04', _('April')), 
                    ('05', _('May')), 
                    ('06', _('June')), 
                    ('07', _('July')), 
                    ('08', _('August')), 
                    ('09', _('September')), 
                    ('10', _('October')), 
                    ('11', _('November')), 
                    ('12', _('December'))
           ]
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(product_valuation_wizard, self).default_get(fields_list=fields_list)
        now = datetime.now()
        month = str(now.month).zfill(2)
        year = now.year
        vals = {'month': month, 'year': year}
        res.update(vals)
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    month = fields.Selection('_month_get', string='Month', required=True)
    year = fields.Char(string='Year', size=4, required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, ondelete='cascade', default=lambda self: self.env.user.company_id)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=False, ondelete='cascade', help='If the warehouse is not chosen the calculated is done on all the warehouses of the company')
    
    @api.multi
    def calculate(self):
        valuation_obj = self.env['stock.valuation']
        warehouse_obj = self.env['stock.warehouse']
        if self.warehouse_id:
            valuation_obj.calculate_for_product(self.product_id, self.month, self.year, self.warehouse_id.id)
        else:
            warehouse_rcs = warehouse_obj.search([('company_id', '=', self.company_id.id)])
            for warehouse in warehouse_rcs:
                valuation_obj.calculate_for_product(self.product_id, self.month, self.year, warehouse.id)
                
        return {
                    "type": "ir.actions.act_window",
                    "res_model": "stock.valuation",
                    "views": [[False, "tree"], [False, "form"]],
                }



class all_products_valuation_wizard(models.TransientModel):
    """ 
    Valuation wizard for multiple products 
    """
    _name = 'all.products.valuation.wizard'
    _description = 'Valuation wizard for multiple products'
    
    @api.model
    def _month_get(self):
        return [
                    ('01', _('January')), 
                    ('02', _('February')), 
                    ('03', _('March')), 
                    ('04', _('April')), 
                    ('05', _('May')), 
                    ('06', _('June')), 
                    ('07', _('July')), 
                    ('08', _('August')), 
                    ('09', _('September')), 
                    ('10', _('October')), 
                    ('11', _('November')), 
                    ('12', _('December'))
           ]
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(all_products_valuation_wizard, self).default_get(fields_list=fields_list)
        now = datetime.now()
        month = str(now.month).zfill(2)
        year = now.year
        vals = {'month': month, 'year': year}
        res.update(vals)
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    month = fields.Selection('_month_get', string='Month', required=True)
    year = fields.Char(string='Year', size=4, required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, ondelete='cascade', default=lambda self: self.env.user.company_id)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=False, ondelete='cascade', help='If the warehouse is not chosen the calculated is done on all the warehouses of the company')
    
    @api.multi
    def calculate(self):
        valuation_obj = self.env['stock.valuation']
        warehouse_obj = self.env['stock.warehouse']
        if self.warehouse_id:
            valuation_obj.calculate_all_products(self.month, self.year, self.warehouse_id.id)
        else:
            warehouse_rcs = warehouse_obj.search([('company_id', '=', self.company_id.id)])
            for warehouse in warehouse_rcs:
                valuation_obj.calculate_all_products(self.month, self.year, warehouse.id)
        
        
        return {
                    "type": "ir.actions.act_window",
                    "res_model": "stock.valuation",
                    "views": [[False, "tree"], [False, "form"]],
                }
        
        
        
class wizard_limit_modif_move(models.TransientModel):
    """ 
        Wizard qui permet de modifier le champ date limite de modification des mouvements dans la fiche société
    """
    _name = 'wizard.limit.modif.move'
    _description = 'Wizard that lets you change the "date of modification of movements" field in the record company'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    date = fields.Date(string='Date', required=True)
    
    
    @api.multi
    def validate(self):
        for wiz in self:
            self.env.user.company_id.write({'limit_modif_move': wiz.date})
            
        return  {'type': 'ir.actions.act_window_close'}
    
    
    
class product_valuation_lot_wizard(models.TransientModel):
    """ 
    Valuation lot wizard for a single product 
    """
    _name = 'product.valuation.lot.wizard'
    _description = 'Valuation lot wizard for a single product'
    
    
    @api.model
    def _month_get(self):
        return [
                    ('01', _('January')), 
                    ('02', _('February')), 
                    ('03', _('March')), 
                    ('04', _('April')), 
                    ('05', _('May')), 
                    ('06', _('June')), 
                    ('07', _('July')), 
                    ('08', _('August')), 
                    ('09', _('September')), 
                    ('10', _('October')), 
                    ('11', _('November')), 
                    ('12', _('December'))
           ]
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(product_valuation_lot_wizard, self).default_get(fields_list=fields_list)
        now = datetime.now()
        month = str(now.month).zfill(2)
        year = now.year
        vals = {'month': month, 'year': year}
        res.update(vals)
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    month = fields.Selection('_month_get', string='Month', required=True)
    year = fields.Char(string='Year', size=4, required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, ondelete='cascade', default=lambda self: self.env.user.company_id)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=False, ondelete='cascade', help='If the warehouse is not chosen the calculated is done on all the warehouses of the company')
    
    
    @api.multi
    def calculate(self):
        valuation_lot_obj = self.env['stock.valuation.lot']
        warehouse_obj = self.env['stock.warehouse']
        for wiz in self:
            if wiz.warehouse_id:
                valuation_lot_obj.calculate_for_products([wiz.product_id.id], wiz.month, wiz.year, wiz.company_id.id, wiz.warehouse_id.id)
            else:
                warehouse_rcs = warehouse_obj.search([('company_id', '=', wiz.company_id.id)])
                for warehouse in warehouse_rcs:
                    valuation_lot_obj.calculate_for_products([wiz.product_id.id], wiz.month, wiz.year, wiz.company_id.id, warehouse.id)
                
        return {
                    "type": "ir.actions.act_window",
                    "res_model": "stock.valuation.lot",
                    "views": [[False, "tree"], [False, "form"]],
                }



class all_products_valuation_lot_wizard(models.TransientModel):
    """ 
    Valuation lot wizard for multiple products 
    """
    _name = 'all.products.valuation.lot.wizard'
    _description = 'Valuation lot wizard for multiple products'
    
    @api.model
    def _month_get(self):
        return [
                    ('01', _('January')), 
                    ('02', _('February')), 
                    ('03', _('March')), 
                    ('04', _('April')), 
                    ('05', _('May')), 
                    ('06', _('June')), 
                    ('07', _('July')), 
                    ('08', _('August')), 
                    ('09', _('September')), 
                    ('10', _('October')), 
                    ('11', _('November')), 
                    ('12', _('December'))
           ]
    
    
    @api.model
    def default_get(self, fields_list):
        res = super(all_products_valuation_lot_wizard, self).default_get(fields_list=fields_list)
        now = datetime.now()
        month = str(now.month).zfill(2)
        year = now.year
        vals = {'month': month, 'year': year}
        res.update(vals)
        return res
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    month = fields.Selection('_month_get', string='Month', required=True)
    year = fields.Char(string='Year', size=4, required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, ondelete='cascade', default=lambda self: self.env.user.company_id)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=False, ondelete='cascade', help='If the warehouse is not chosen the calculated is done on all the warehouses of the company')
    
    @api.multi
    def calculate(self):
        valuation_lot_obj = self.env['stock.valuation.lot']
        warehouse_obj = self.env['stock.warehouse']
        product_rcs = self.env['product.product'].search([('is_int', '!=', True), ('type', '=', 'stockable'), ('track_label', '=', True)])
        for wiz in self:
            if wiz.warehouse_id:
                valuation_lot_obj.calculate_for_products(product_rcs.ids, wiz.month, wiz.year, wiz.company_id.id, wiz.warehouse_id.id)
            else:
                warehouse_rcs = warehouse_obj.search([('company_id', '=', wiz.company_id.id)])
                for warehouse in warehouse_rcs:
                    valuation_lot_obj.calculate_for_products(product_rcs.ids, wiz.month, wiz.year, wiz.company_id.id, warehouse.id)
                    
            return {
                        "type": "ir.actions.act_window",
                        "res_model": "stock.valuation.lot",
                        "views": [[False, "tree"], [False, "form"]],
                    }
    
    