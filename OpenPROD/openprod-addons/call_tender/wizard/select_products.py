# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
from lxml import etree

class select_products_wizard(models.TransientModel):
    """ 
        Wizard to select products in the call for tender
    """
    _name = 'select.products.wizard'
    _description = 'Wizard to select products in the call for tender'
    _rec_name = 'call_tender_id'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    product_ids = fields.Many2many('product.product', 'select_product_wizard_rel', 'select_product_id', 'product_id', 
                                 string='Products')
    call_tender_id = fields.Many2one('call.tender', string='Call for tender', required=False, ondelete='set null')
    
    @api.model
    def default_get(self, fields_list):
        res = super(select_products_wizard, self).default_get(fields_list=fields_list)
        res['call_tender_id'] = self.env.context.get('active_id', False)
        return res
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """
            Surcharge du fields view get afin de récupérer les ids des produits
            et de faire un domaine sur le champ
        """
        res = super(select_products_wizard, self).fields_view_get(view_id=view_id, view_type=view_type, 
                                                                  toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])
        context = self.env.context
        if context and context.get('active_id') and context.get('active_model') == 'call.tender':
            product_ids = []
            call_product_list = self.env['product.call.tender'].search_read([('tender_id', '=', context['active_id'])], ['product_id'])
            if call_product_list:
                product_ids += [call_product['product_id'][0] for call_product in call_product_list if call_product['product_id'] and isinstance(call_product['product_id'][0], int)]
                 
            for node in doc.xpath("//field[@name='product_ids']"):
                domain = "[('purchase_ok', '=', True), ('free_purchase', '=', False), ('id', 'not in', %s)]"%(product_ids)
                node.set('domain', domain)
             
        res['arch'] = etree.tostring(doc)
        return res
    
    
    @api.multi
    def select_call_products(self):
        """
            Fonction permettant de créer les lignes de produit de l'appel d'offre
        """
        call_tender = self.call_tender_id
        product_tender_obj = self.env['product.call.tender'] 
        if call_tender:
            sequence_list = [x.sequence for x in call_tender.product_ids]
            if sequence_list:
                max_sequence = max(sequence_list)
            else:
                max_sequence = 0
            
            call_tender_id = call_tender.id
            for product_id in self.product_ids.ids:
                max_sequence += 10
                create_vals = {'sequence': max_sequence,
                               'product_id': product_id,
                               'tender_id': call_tender_id}
                product_tender_obj.create(create_vals)

        return {'type':'ir.actions.act_window_view_reload'}
    
    
    