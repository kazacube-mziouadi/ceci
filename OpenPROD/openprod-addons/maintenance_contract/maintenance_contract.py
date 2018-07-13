# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from datetime import datetime, timedelta
import openerp.addons.decimal_precision as dp
from openerp.exceptions import except_orm, ValidationError, Warning
from openerp.addons.base_openprod.common import get_form_view, roundingUp
from dateutil.relativedelta import relativedelta


class maintenance_contract(models.Model):
    """ 
        Maintenance contract 
    """
    _name = 'maintenance.contract'
    _description = 'Maintenance contract'

    
    @api.model
    def _type_get(self):
        return [
                ('customer', _('Customer')),
                ('supplier', _('Supplier')),
                       ]
    
    
    @api.model
    def _tolerance_get(self):
        return [
                ('day', _('Day')),
                ('week', _('Week')),
                ('month', _('Month')),
                ('quarter', _('Quarter')),
                ('year', _('Year')),
                ]


    @api.one
    def last_date_invoice_compute(self):
        """
            On récupère la date de facture de la facture la plus récente
        """
        invoice_rcs = self.env['account.invoice'].search([('maintenance_contract_id', '=', self.id), ('date_invoice', '!=', False)], 
                                                         order='date_invoice desc', limit=1)
        if invoice_rcs: 
            last_date_invoice = invoice_rcs.date_invoice
        else:
            last_date_invoice = False
            
        self.last_date_invoice = last_date_invoice 
        
        
    @api.model
    def _state_get(self):
        return [
                ('waiting', _('Waiting')),
                ('validate', _('Validate')),
                ('done', _('Done')),
                ('cancel', _('Cancel')),
                       ]
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    #Entete
    name = fields.Char(required=True, size=256)
    type = fields.Selection('_type_get', string='Type', required=True)
    save_old_type = fields.Selection('_type_get', string='Type')
    supplier_id = fields.Many2one('res.partner', string='Supplier', required=False, ondelete='restrict')
    save_old_supplier_id = fields.Many2one('res.partner', string='Customer', required=False, ondelete='set null')
    customer_id = fields.Many2one('res.partner', string='Customer', required=False, ondelete='restrict')
    save_old_customer_id = fields.Many2one('res.partner', string='Customer', required=False, ondelete='set null')
    date_create = fields.Date(string='Create date', required=1, default=lambda self: fields.Date.today())
    start_date = fields.Date(string='Start date', required=1, default=lambda self: fields.Date.today())
    end_date = fields.Date(string='End date')
    frequency = fields.Integer(string='Frequency', default=0.0, required=True, digits=dp.get_precision('Product quantity'))
    frequency_type = fields.Selection('_tolerance_get', string='Frequency type', required=True)
    state = fields.Selection('_state_get', string='State', default='waiting')
    #Facturation
    last_date_invoice = fields.Date(string='Last date invoice', compute='last_date_invoice_compute')
    line_ids = fields.One2many('maintenance.contract.line', 'maintenance_contract_id',  string='Lines')
    description = fields.Text(string='Description')
    invoice_ids = fields.One2many('account.invoice', 'maintenance_contract_id',  string='Invoices')
    #Document
    document_ids = fields.Many2many('document.openprod', 'maintenance_contract_document_openprod_rel', 
                                    'maintenance_contract_id', 'document_id', string='Documents', copy=False)
    note_ids = fields.One2many('note.openprod', 'maintenance_contract_id', string='Notes')
    
    
    #===========================================================================
    # ONCHANGE
    #===========================================================================
    @api.onchange('type', 'customer_id', 'supplier_id')
    def _onchange_warning_type_id(self):
        res = {'warning': {}}
        if self.line_ids:
            if self.save_old_customer_id:
                self.customer_id = self.save_old_customer_id.id
            
            if self.save_old_supplier_id:
                self.supplier_id = self.save_old_supplier_id.id
                
            if self.save_old_type:
                self.type = self.save_old_type
                
            res['warning'] = {'title': _('Warning'), 'message': _('You can not change either the partner or the type because there are already lines.')}
        else:
            if self.supplier_id:
                self.save_old_supplier_id = self.supplier_id.id
            
            if self.customer_id:
                self.save_old_customer_id = self.customer_id.id
            
            if self.type:
                self.save_old_type = self.type
            
        return res  
    
    #===========================================================================
    # BUTTON
    #===========================================================================
    @api.multi
    def wkf_done(self):
        self.write({'state': 'done'})
    
    
    @api.multi
    def wkf_cancel(self):
        for maintenance_contract in self:
            if maintenance_contract.invoice_ids:
                raise except_orm(_('Error'), _('No cancel because there are invoices lines.'))
                
        self.write({'state': 'cancel'})
    
    @api.multi
    def wkf_waiting(self):
        self.write({'state': 'waiting'})   
        
        
    @api.multi
    def wkf_validate(self):
        self.write({'state': 'validate'})            
            
            
    @api.multi
    def button_generate_invoice_mc(self, date_now=False, last_date=False, no_frequency=False):
        """
            Fonction qui permet de créer la facture pour le contract en fonction de la fréquence et de la dernière facture
        """
        invoice_obj = self.env['account.invoice']
        invoice_line_obj = self.env['account.invoice.line']
        create_invoice = False
        for maintenance_contract in self:
            if not date_now:
                date_now = fields.Date.today()
            if not last_date:
                last_date = maintenance_contract.last_date_invoice
            
            if maintenance_contract.state == 'validate' and maintenance_contract.frequency > 0:
                if maintenance_contract.end_date and date_now > maintenance_contract.end_date:
                    maintenance_contract.wkf_done()
                elif maintenance_contract.start_date <= date_now and \
                    (maintenance_contract.end_date and date_now <= maintenance_contract.end_date or not maintenance_contract.end_date) and \
                    (maintenance_contract.last_date_invoice and maintenance_contract.last_date_invoice < date_now or not maintenance_contract.last_date_invoice):
                    stop_invoice = False
                    if last_date and not no_frequency:
                        next_date = False
                        if maintenance_contract.frequency_type == 'quarter':
                            frequency = maintenance_contract.frequency*3
                            next_date = fields.Date.to_string(fields.Date.from_string(last_date) + relativedelta(months=frequency))
                        elif maintenance_contract.frequency_type == 'day':
                            next_date = fields.Date.to_string(fields.Date.from_string(last_date) + 
                                                                                      timedelta(days=maintenance_contract.frequency))
                        elif maintenance_contract.frequency_type == 'week':
                            frequency = maintenance_contract.frequency*7
                            next_date = fields.Date.to_string(fields.Date.from_string(last_date) + timedelta(days=frequency))
                        elif maintenance_contract.frequency_type == 'month':
                            next_date = fields.Date.to_string(fields.Date.from_string(last_date) + 
                                                                                      relativedelta(months=maintenance_contract.frequency))
                        elif maintenance_contract.frequency_type == 'year':
                            next_date = fields.Date.to_string(fields.Date.from_string(last_date) + 
                                                                                      relativedelta(years=maintenance_contract.frequency))
                        if next_date and next_date > date_now:
                            stop_invoice = True
                        
                    
                    if not stop_invoice:
                        if maintenance_contract.type == 'customer':
                            invoice_rcs = invoice_obj.create_invoice(maintenance_contract.customer_id.id, maintenance_contract.customer_id.address_id.id, 
                                                       'out_invoice', other_data={'maintenance_contract_id': maintenance_contract.id, 'date_invoice': date_now})
                        else:
                            invoice_rcs = invoice_obj.create_invoice(maintenance_contract.supplier_id.id, maintenance_contract.supplier_id.address_id.id, 
                                                       'in_invoice', other_data={'maintenance_contract_id': maintenance_contract.id, 'date_invoice': date_now})
            
                        create_invoice = True
                        for line in maintenance_contract.line_ids:
                            invoice_line_rcs = invoice_line_obj.create_invoice_line(invoice_rcs.id, line.product_id.id, from_invoice=True, 
                                                                                    other_data={'uom_id': line.uoi_id.id,
                                                                                                'sec_uom_id': line.uoi_id.id,
                                                                                                'uoi_id': line.uoi_id.id,
                                                                                                'uom_qty': line.qty,
                                                                                                'sec_uom_qty': line.qty,
                                                                                                'quantity': line.qty,
                                                                                                'maintenance_contract_id': maintenance_contract.id,})    
                            
                            if line.currency_id and invoice_rcs.currency_id.id != line.currency_id.id:
                                context2 = {}
                                context2.update(self.env.context)
                                if invoice_rcs.date_invoice:
                                    context2['date'] = invoice_rcs.date_invoice
                                    
                                price = invoice_rcs.currency_id.with_context(context2).compute(line.price, line.currency_id)
                            else:
                                price = line.price
                                
                            invoice_line_rcs.write({'price_unit': price})
            
                        
        return create_invoice
    
    
    @api.multi
    def show_customer_invoice(self):
        """
            Fonction qui cherche et retourne les factures pour un contract de maintenance client
        """
        for maintenance_contract in self:
            action_struc = {}
            action_dict = get_form_view(self, 'sale.sale_invoice_action')
            invoice_ids = [x.id for x in maintenance_contract.invoice_ids]
            if action_dict and action_dict.get('id') and action_dict.get('type'):
                action = self.env[action_dict['type']].browse(action_dict['id'])
                action_struc = action.read()
                action_struc[0]['context'] = {'invoice_ids': invoice_ids}
                action_struc = action_struc[0]
              
        return action_struc
    
    
    @api.multi
    def show_supplier_invoice(self):
        """
            Fonction qui cherche et retourne les factures pour un contract de maintenance fournisseur
        """
        for maintenance_contract in self:
            action_struc = {}
            action_dict = get_form_view(self, 'purchase.purchase_invoice_action')
            invoice_ids = [x.id for x in maintenance_contract.invoice_ids]
            if action_dict and action_dict.get('id') and action_dict.get('type'):
                action = self.env[action_dict['type']].browse(action_dict['id'])
                action_struc = action.read()
                action_struc[0]['context'] = {'invoice_ids': invoice_ids}
                action_struc = action_struc[0]
              
        return action_struc
    
    @api.multi
    def show_customer_line_invoice_line(self):
        """
            Fonction qui cherche et retourne les lignes de facture de la ligne de vente
        """
        for maintenance_contract in self:
            action_struc = {}
            action_dict = get_form_view(self, 'sale.sale_line_invoice_action')
            line_rcs = self.env['account.invoice.line'].search([('maintenance_contract_id', '=', maintenance_contract.id)])
            line_ids = line_rcs and line_rcs.ids or []
            if action_dict and action_dict.get('id') and action_dict.get('type'):
                action = self.env[action_dict['type']].browse(action_dict['id'])
                action_struc = action.read()
                action_struc[0]['context'] = {'invoice_ids': line_ids}
                action_struc = action_struc[0]
              
        return action_struc
    
    
    @api.multi
    def show_supplier_line_invoice_line(self):
        """
            Fonction qui cherche et retourne les lignes de facture de la ligne d'achat
        """
        for maintenance_contract in self:
            action_struc = {}
            action_dict = get_form_view(self, 'purchase.purchase_line_invoice_action')
            line_rcs = self.env['account.invoice.line'].search([('maintenance_contract_id', '=', maintenance_contract.id)])
            line_ids = line_rcs and line_rcs.ids or []
            if action_dict and action_dict.get('id') and action_dict.get('type'):
                action = self.env[action_dict['type']].browse(action_dict['id'])
                action_struc = action.read()
                action_struc[0]['context'] = {'invoice_ids': line_ids}
                action_struc = action_struc[0]
              
        return action_struc


            
class maintenance_contract_line(models.Model):
    """ 
        Maintenance contract line
    """
    _name = 'maintenance.contract.line'
    _description = 'Maintenance contract line'
    _rec_name = 'description'
    
    
    @api.one
    @api.depends('product_id')
    def _uoi_compute(self):
        """
            UoI
        """
        uoi_id = False
        if self.product_id and self.type:
            if self.type == 'customer':
                    type_uoms = 'out'
            else:
                type_uoms = 'in'
                
            res_uoms = self.product_id.get_uoms(partner=self.partner_id, pinfo=False, type=type_uoms, property_ids=False, with_factor=False, with_pinfo=False)
            if 'uoi_id' in res_uoms and res_uoms['uoi_id']:
                uoi_id = res_uoms['uoi_id'].id
            else:
                uoi_id = self.product_id.uom_id.id
        
        
        self.uoi_id = uoi_id 
    
    
    @api.one
    @api.depends('qty', 'price')
    def _total_price_compute(self):
        """
            Total price
        """
        total_price = 0.0
        self.total_price = total_price
        
    
    @api.one
    @api.depends('maintenance_contract_id')
    def _maintenance_contract_id_compute(self):
        """
            Total price
        """
        partner_id = False
        if self.maintenance_contract_id and self.maintenance_contract_id.type == 'customer':
            partner_id = self.maintenance_contract_id.customer_id and self.maintenance_contract_id.customer_id.id or False
        else:
            partner_id = self.maintenance_contract_id.supplier_id and self.maintenance_contract_id.supplier_id.id or False
        
        self.type = self.maintenance_contract_id and self.maintenance_contract_id.type or ''
        self.partner_id = partner_id
    
    
    @api.model
    def _type_get(self):
        return [
                ('customer', _('Customer')),
                ('supplier', _('Supplier')),
                       ]
    
        
    #===========================================================================
    # COLUMNS
    #===========================================================================
    maintenance_contract_id = fields.Many2one('maintenance.contract', string='Maintenance contract', required=False, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=0, required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='restrict')
    description = fields.Char(string='Description', size=256, required=True)
    qty = fields.Float(string='Qty', default=0.0, required=True, digits=dp.get_precision('Product quantity'))
    price = fields.Float(string='Invoice price', default=0.0, required=True, digits=dp.get_precision('Product price'))
    uoi_id = fields.Many2one('product.uom', string='UoI', compute='_uoi_compute')
    total_price = fields.Float(string='Total price', compute='_total_price_compute')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, ondelete='restrict', default=lambda self: self.env.user.company_id.currency_id)
    partner_id = fields.Many2one('res.partner', string='Partner', compute='_maintenance_contract_id_compute')
    type = fields.Selection('_type_get', string='Type', compute='_maintenance_contract_id_compute')
    
    
    #===========================================================================
    # Onchange
    #===========================================================================
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
            Onchange du produit
        """
        description = ''
        if self.product_id:
            description = '[%s] %s'%(self.product_id.code, self.product_id.name)
            if self.type == 'customer':
                type_uoms = 'out'
            else:
                type_uoms = 'in'
                
            res_uoms = self.product_id.get_uoms(partner=self.partner_id, pinfo=False, type=type_uoms, property_ids=False, with_factor=False, with_pinfo=False)
            if 'uoi_id' in res_uoms and res_uoms['uoi_id']:
                uoi_rcs = res_uoms['uoi_id']
            else:
                uoi_rcs = self.product_id.uom_id
            
            self.uoi_id = uoi_rcs.id
            if self.type == 'customer':
                currency_price_return = self.currency_id or self.env.user.company_id.currency_id
                price_unit = self.product_id.get_price_sale(self.partner_id, properties=False, currency_price_return=currency_price_return, 
                                                            qty_uom=False, uom=False, qty_uos=self.qty, uos=uoi_rcs, date='', type='price', 
                                                            force_price=False, with_uoi=False, sale_line_rcs=False)
                self.price = price_unit
            else:
                currency_price_return = self.currency_id or self.env.user.company_id.currency_id
                price_unit = self.product_id.get_price_purchase(self.partner_id, properties=False, currency_price_return=currency_price_return, 
                                                                qty_uom=False, uom=False, qty_uop=self.qty, uop=uoi_rcs, date='', type='price', 
                                                                force_price=False, state_dev=False, with_uoi=False)
                self.price = price_unit
            
        self.description = description
    
    @api.onchange('qty')
    def _onchange_qty(self):
        if self.product_id and self.uoi_id:
            if self.type == 'customer':
                currency_price_return = self.currency_id or self.env.user.company_id.currency_id
                price_unit = self.product_id.get_price_sale(self.partner_id, properties=False, currency_price_return=currency_price_return, 
                                                            qty_uom=False, uom=False, qty_uos=self.qty, uos=self.uoi_id, date='', type='price', 
                                                            force_price=False, with_uoi=False, sale_line_rcs=False)
                if price_unit:
                    self.price = price_unit
            else:
                currency_price_return = self.currency_id or self.env.user.company_id.currency_id
                price_unit = self.product_id.get_price_purchase(self.partner_id, properties=False, currency_price_return=currency_price_return, 
                                                                qty_uom=False, uom=False, qty_uop=self.qty, uop=self.uoi_id, date='', type='price', 
                                                                force_price=False, state_dev=False, with_uoi=False)
                if price_unit:
                    self.price = price_unit
        
        
        
    
    