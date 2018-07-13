# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import except_orm
from openerp.addons.base_openprod.common import get_form_view
from lxml import etree

class switch_document_wizard(models.Model):
    _inherit = 'switch.document.wizard'
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    routing_ids = fields.Many2many('mrp.routing.line',
            'document_openprod_routing_line_rel', 'switch_id', 'routing_line_id', string='Routing lines')
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """
            Surcharge du fields view get afin de récupérer les ids des gammes
            et de faire un domaine sur le champ
        """
        res = super(switch_document_wizard, self).fields_view_get(view_id=view_id, view_type=view_type, 
                                                                  toolbar=toolbar, submenu=submenu)
        doc = etree.XML(res['arch'])
        context = self.env.context
        if context and context.get('active_id'):
            document = self.env['document.openprod'].browse(context['active_id'])
        
        if document:
            routing_ids = document.find_routing_ids(return_line=True)
            for node in doc.xpath("//field[@name='routing_ids']"):
                domain = "[('id', 'in', %s)]"%(routing_ids)
                node.set('domain', domain)
            
        res['arch'] = etree.tostring(doc)
        return res