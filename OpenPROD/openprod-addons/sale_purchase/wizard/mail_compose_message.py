# -*- coding: utf-8 -*-

from openerp import models, api, fields, report
from openerp.tools.translate import _
from openerp.addons.base_openprod.common import get_form_view
from openerp.exceptions import except_orm, ValidationError

# If cStringIO is available, we use it
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
    
class mail_message(models.Model):
    _inherit = 'mail.message'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    model_template_id = fields.Many2one('mail.template', string='Model Mail', required=False, ondelete='restrict')
    
    def action_send_mail(self, email_to, model, edi_select, object_id, mail_id=False, update_context_other=None):
        """
            Surcharge de la méthode d'envoi de mail pour ajouter les éventuels plans et controles en
            PJ
        """
        product_id_list = []
        quality_obj = self.env['stock.quality.control']
        attachment_obj = self.env['ir.attachment']
        att_ids = []
        pdf_type = ''
        attachment_datas = {}
        res = super(mail_message, self).action_send_mail(email_to, model, edi_select, object_id, mail_id=mail_id, update_context_other=update_context_other)
        if not res.get('context'):
            res['context'] = {}
        
        #Récupération ids des produits des lignes d'achat ou de vente
        if model == 'purchase.order':
            purchase_rs = self.env['purchase.order'].browse(object_id)
            product_id_list = purchase_rs and [line.product_id.id for line in purchase_rs.purchase_order_line_ids] or []
            pdf_type = 'pdf_purchase_mail'
        elif model == 'sale.order':
            sale_rs = self.env['sale.order'].browse(object_id)
            product_id_list = sale_rs and [line.product_id.id for line in sale_rs.order_line_ids] or []
            pdf_type = 'pdf_sale_mail'
        
        for product_id in product_id_list:
            #Recherche des plans et controles
            printed_doc_list = quality_obj.search([('product_id', '=', product_id), 
                                                   ('type', '=', pdf_type), ('pdf_file', '!=', False)])
            for printed_doc in printed_doc_list:
                if printed_doc.type == pdf_type:
                    attachment_datas[printed_doc.pdf_file.name] = printed_doc.pdf_file.attachment
        
        for name, attach_data in attachment_datas.iteritems():
            #Création des PJ
            #Pas de res_id parce qu'on ne veut pas lier la PJ à l'achat/la vente
            data_attach = {
                'name': name,
                'datas': attach_data,
                'datas_fname': name,
                'description': name,
                'res_model' : model,
            }
            att_ids.append(attachment_obj.create(data_attach).id)
            
        if res['context'].get('default_attachment_ids'):
            res['context']['default_attachment_ids'].extend(att_ids)
        else:
            res['context']['default_attachment_ids'] = att_ids
        
        res['context']['no_mail_onchange'] = True
        return res
