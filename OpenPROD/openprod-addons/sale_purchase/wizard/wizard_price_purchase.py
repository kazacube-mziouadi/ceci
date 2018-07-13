# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.exceptions import except_orm, ValidationError

class wizard_price(models.TransientModel):
    """ 
    Wizard price
    """
    _name = 'wizard.price'
    _description = 'Wizard Price'
    _rec_name = 'product_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    @api.model
    def _type_get(self):
        return [
                ('sale', _('Sale')),
                ('purchase', _('Purchase')),
                       ]
    
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Partner', required=False, ondelete='cascade')
    qty = fields.Float(string='Quantity', default=0.0, required=True)
    sec_uom_id = fields.Many2one('product.uom', string='UoM', required=False, ondelete='cascade')
    property_ids = fields.Many2many('purchase.property', string='Properties')
    type = fields.Selection('_type_get', string='Type')
    date = fields.Date(string='Date')
    
    line_purchase_ids = fields.One2many('wizard.price.line.purchase', 'wizard_price_id',  string='Lines Purchase')
    line_sale_ids = fields.One2many('wizard.price.line.sale', 'wizard_price_id',  string='Lines Sale')
    
    
    
    @api.onchange('product_id','partner_id','qty','sec_uom_id','type','date','property_ids')
    def _onchange_wizard_price_id(self):
        """
            Onchange qui permet à partir d'un partenaire et d'un produit de ressortir les référencements clients et fournisseurs
        """
        line_purchase_ids = []
        line_sale_ids = []
        if self.sec_uom_id and self.product_id:
            if self.product_id.purchase_ok == True and (self.type == 'purchase' or self.type == False):
                if self.product_id.free_purchase:
                    price = self.product_id.get_price_purchase(self.partner_id, self.property_ids, qty_uop=self.qty, 
                                                               uop=self.sec_uom_id, date=self.date, type='price', state_dev=False)
                    uoi_id = self.product_id.purchase_uoi_id and self.product_id.purchase_uoi_id.id or False
                    dic_purchase = {
                        'free_purchase': True,
                        'price': price,
                        'uoi_id': uoi_id,
                    }
                    line_purchase_ids.append((0, 0, dic_purchase))
                else:
                    if self.partner_id:
                        pricelist = self.product_id.get_price_purchase(self.partner_id, self.property_ids, qty_uop=self.qty, 
                                                                       uop=self.sec_uom_id, date=self.date, type='pricelist', state_dev=False)
                        if pricelist:
                            supp_info = pricelist.sinfo_id
                            uoi_id = supp_info.uoi_id and supp_info.uoi_id.id or False
                            dic_purchase = {
                                'free_purchase': False,
                                'suppinfo_id': supp_info.id,
                                'date_start': pricelist and pricelist.date_start or '',
                                'date_stop': pricelist and pricelist.date_stop or '',
                                'min_qty': pricelist and pricelist.min_qty or 0.0,
                                'price': pricelist and pricelist.price or 0.0,
                                'uoi_id': uoi_id,
                            }
                            line_purchase_ids.append((0, 0, dic_purchase))
                    else:
                        list_supplier = []
                        for supp_info in self.product_id.sinfo_ids:
                            if supp_info.partner_id.id not in list_supplier:
                                list_supplier.append(supp_info.partner_id.id)
                                pricelist = self.product_id.get_price_purchase(supp_info.partner_id, self.property_ids, qty_uop=self.qty, uop=self.sec_uom_id, 
                                                                               date=self.date, type='pricelist', state_dev=False)
                                
                                if pricelist:
                                    uoi_id = supp_info.uoi_id and supp_info.uoi_id.id or False
                                    dic_purchase = {
                                        'free_purchase': False,
                                        'suppinfo_id': supp_info.id,
                                        'date_start': pricelist and pricelist.date_start or '',
                                        'date_stop': pricelist and pricelist.date_stop or '',
                                        'min_qty': pricelist and pricelist.min_qty or 0.0,
                                        'price': pricelist and pricelist.price or 0.0,
                                        'uoi_id': uoi_id,
                                    }
                                    line_purchase_ids.append((0, 0, dic_purchase))
                        
            if self.product_id.sale_ok == True and (self.type == 'sale' or self.type == False):
                if self.product_id.free_sale:
                    price = self.product_id.get_price_sale(self.partner_id, self.property_ids, qty_uos=self.qty, uos=self.sec_uom_id, date=self.date, type='price')
                    uoi_id = self.product_id.sale_uoi_id and self.product_id.sale_uoi_id.id or False
                    dic_sale = {
                        'free_sale': True,
                        'price': price,
                        'uoi_id': uoi_id,
                    }
                    line_sale_ids.append((0, 0, dic_sale))
                else:
                    if self.partner_id:
                        pricelist = self.product_id.get_price_sale(self.partner_id, self.property_ids, qty_uos=self.qty, uos=self.sec_uom_id, date=self.date, type='pricelist')
                        if pricelist:
                            cus_info = pricelist.cinfo_id
                            uoi_id = cus_info.uoi_id and cus_info.uoi_id.id or False
                            dic_sale = {
                                'free_sale': False,
                                'cusinfo_id': cus_info.id,
                                'date_start': pricelist and pricelist.date_start or '',
                                'date_stop': pricelist and pricelist.date_stop or '',
                                'min_qty': pricelist and pricelist.min_qty or 0.0,
                                'price': pricelist and pricelist.price or 0.0,
                                'uoi_id': uoi_id,
                            }
                            line_sale_ids.append((0, 0, dic_sale))
                    else:
                        list_customer = []
                        for cus_info in self.product_id.cinfo_ids:
                            if cus_info.partner_id.id not in list_customer:
                                list_customer.append(cus_info.partner_id.id)
                                pricelist = self.product_id.get_price_sale(cus_info.partner_id, self.property_ids, qty_uos=self.qty, uos=self.sec_uom_id, date=self.date, type='pricelist')
                                if pricelist:
                                    uoi_id = cus_info.uoi_id and cus_info.uoi_id.id or False
                                    dic_sale = {
                                        'free_sale': False,
                                        'cusinfo_id': cus_info.id,
                                        'date_start': pricelist and pricelist.date_start or '',
                                        'date_stop': pricelist and pricelist.date_stop or '',
                                        'min_qty': pricelist and pricelist.min_qty or 0.0,
                                        'price': pricelist and pricelist.price or 0.0,
                                        'uoi_id': uoi_id,
                                    }
                                    line_sale_ids.append((0, 0, dic_sale))
        
        self.line_purchase_ids = line_purchase_ids
        self.line_sale_ids = line_sale_ids
        
        
        
class wizard_price_line_purchase(models.TransientModel):
    """ 
        Wizard price line purchase
    """
    _name = 'wizard.price.line.purchase'
    _description = 'Wizard price line purchase' 
    _rec_name = 'suppinfo_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wizard_price_id = fields.Many2one('wizard.price', string='Wizard price', required=False, ondelete='cascade')
    free_purchase = fields.Boolean(string='Free purchase', default=False)
    suppinfo_id = fields.Many2one('product.supplierinfo', string='Suppinfo', required=False, ondelete='cascade')
    date_start = fields.Date(string='Date start')
    date_stop = fields.Date(string='Date stop')
    min_qty = fields.Float(string='Quantity', default=0.0, required=False)
    price = fields.Float(string='Price', default=0.0, required=False)
    uoi_id = fields.Many2one('product.uom', string='UoI', required=False, ondelete='cascade')
    
    
    
class wizard_price_line_sale(models.TransientModel):
    """ 
        Wizard price line sale
    """
    _name = 'wizard.price.line.sale'
    _description = 'Wizard price line sale' 
    _rec_name = 'cusinfo_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    wizard_price_id = fields.Many2one('wizard.price', string='Wizard price', required=False, ondelete='cascade')
    free_sale = fields.Boolean(string='Free sale', default=False)
    cusinfo_id = fields.Many2one('product.customerinfo', string='Cusinfo', required=False, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=False, ondelete='cascade')
    date_start = fields.Date(string='Date start')
    date_stop = fields.Date(string='Date stop')
    min_qty = fields.Float(string='Quantity', default=0.0, required=False)
    price = fields.Float(string='Price', default=0.0, required=False)
    uoi_id = fields.Many2one('product.uom', string='UoI', required=False, ondelete='cascade')
    