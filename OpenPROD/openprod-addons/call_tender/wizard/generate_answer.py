# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from lxml import etree
from openerp.exceptions import except_orm

class generate_answer_quantity(models.Model):
    """ 
        Quantity for answer generation
    """
    _name = 'generate.answer.quantity'
    _description = 'Quantity for answer generation'
    _rec_name = 'generate_answer_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    generate_answer_id = fields.Many2one('generate.answer', string='Generate answer', required=False, ondelete='cascade')
    quantity = fields.Float(string='Quantity', default=0.0, required=True)
    
    
    
class generate_answer(models.Model):
    """ 
        Wizard which enable to create call for tender answers quickly
    """
    _name = 'generate.answer'
    _description = 'Wizard which enable to create call for tender answers quickly'
    _rec_name = 'call_tender_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    call_tender_id = fields.Many2one('call.tender', string='Call for tender', required=False, ondelete='set null')
    date_from = fields.Date(string='Date from', required=True)
    date_to = fields.Date(string='Date to', required=False)
    product_ids = fields.Many2many('product.product', 'generate_answer_product_rel', 'generate_answer_id', 'product_id', 
                                 string='Products')
    supplier_ids = fields.Many2many('res.partner', 'generate_answer_res_partner_rel', 'generate_answer_id', 'partner_id', 
                                 string='Suppliers')
    quantity_ids = fields.One2many('generate.answer.quantity', 'generate_answer_id',  string='Quantities')
    
    
    @api.model
    def default_get(self, fields_list):
        """
            On récupère par défaut les produits et les fournisseurs de l'appel d'offre
        """
        res = super(generate_answer, self).default_get(fields_list=fields_list)
        context = self.env.context
        if context.get('active_id', False) and context.get('active_model') == 'call.tender':
            call_tender = self.env['call.tender'].browse(context['active_id'])
            if call_tender:
                res2 = {'call_tender_id': call_tender.id,
                        'product_ids': [x.product_id.id for x in call_tender.product_ids],
                        'supplier_ids': [y.supplier_id.id for y in call_tender.supplier_ids]}
                res.update(res2)
                
        return res
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """
            Surcharge du fields view get afin de récupérer les ids des produits et des fournisseurs
            et de faire un domaine sur les champs
        """
        res = super(generate_answer, self).fields_view_get(view_id=view_id, view_type=view_type, 
                                                                  toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])
        context = self.env.context
        if context and context.get('active_id') and context.get('active_model') == 'call.tender':
            product_ids = []
            supplier_ids = []
            call_product_list = self.env['product.call.tender'].search_read([('tender_id', '=', context['active_id'])], ['product_id'])
            call_supplier_list = self.env['supplier.call.tender'].search_read([('tender_id', '=', context['active_id'])], ['supplier_id'])
            if call_product_list:
                product_ids += [call_product['product_id'][0] for call_product in call_product_list if call_product['product_id'] and isinstance(call_product['product_id'][0], int)]

            if call_supplier_list:
                supplier_ids += [call_supplier['supplier_id'][0] for call_supplier in call_supplier_list if call_supplier['supplier_id'] and isinstance(call_supplier['supplier_id'][0], int)]
                 
            for node in doc.xpath("//field[@name='product_ids']"):
                domain = "[('id', 'in', %s)]"%(product_ids)
                node.set('domain', domain)

            for node in doc.xpath("//field[@name='supplier_ids']"):
                domain = "[('id', 'in', %s)]"%(supplier_ids)
                node.set('domain', domain)
             
        res['arch'] = etree.tostring(doc)
        return res
    
    
    @api.multi
    def create_call_answer(self):
        """
            Fonction permettant de créer les lignes de réponse
        """
        call_tender = self.call_tender_id
        if call_tender:
            call_tender_id = call_tender.id
            supplierinfo_obj = self.env['product.supplierinfo']
            answer_obj = self.env['tender.answer']
            product_id_list = self.product_ids.ids
            supplier_id_list = self.supplier_ids.ids
            quantity_list = [x.quantity for x in self.quantity_ids]
            date_from = self.date_from
            date_to = self.date_to
            for product_id in product_id_list:
                standard_vals = {}
                for supplier_id in supplier_id_list:
                    supplierinfo_rs = supplierinfo_obj.search([('product_id', '=', product_id),
                                             ('partner_id', '=', supplier_id),
                                             ('state', '=', 'active')], limit=1)
                    if supplierinfo_rs:
                        standard_vals = {'product_id': product_id,
                                         'supplier_id': supplier_id,
                                         'currency_id': supplierinfo_rs.currency_id.id,
                                         'tender_id': call_tender_id,
                                         'uop_id': supplierinfo_rs.uop_id.id,
                                         'uop_category_id': supplierinfo_rs.uop_category_id.id,
                                         'uoi_id': supplierinfo_rs.uoi_id.id,
                                         'multiple_qty': supplierinfo_rs.multiple_qty,
                                         'min_qty': supplierinfo_rs.min_qty,
                                         'delivery_delay': supplierinfo_rs.delivery_delay,
                                         'factor': supplierinfo_rs.factor,
                                         'divisor': supplierinfo_rs.divisor,
                                         'date_from': date_from,
                                         'date_to': date_to}
                    else:
                        if not (call_tender.currency_id and call_tender.uop_id and call_tender.uoi_id and call_tender.uop_category_id):
                            raise except_orm(_('Error'), _("You must choose a currency, an unit of purchase and an unit of invoice in "
                                                           "the call for tender to create new referencing"))
                        
                        standard_vals = {'product_id': product_id,
                                         'supplier_id': supplier_id,
                                         'currency_id': call_tender.currency_id.id,
                                         'tender_id': call_tender_id,
                                         'uop_id': call_tender.uop_id.id,
                                         'uop_category_id': call_tender.uop_category_id.id,
                                         'uoi_id': call_tender.uoi_id.id,
                                         'multiple_qty': call_tender.multiple_qty or 1,
                                         'min_qty': call_tender.min_qty or 1,
                                         'delivery_delay': call_tender.delivery_delay or 0,
                                         'factor': call_tender.factor or 1,
                                         'divisor': call_tender.divisor or 1,
                                         'date_from': date_from,
                                         'date_to': date_to}
                    
                    for quantity in quantity_list:
                        line_vals = {'quantity': quantity, 'price': 0}
                        line_vals.update(standard_vals)
                        answer_obj.create(line_vals)

        return {'type':'ir.actions.act_window_view_reload'}
    
    
    