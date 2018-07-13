# -*- coding: utf-8 -*-
from openerp import models, api, fields, _
from openerp.exceptions import except_orm
from openerp.addons.base_openprod.common import get_form_view

class note_openprod(models.Model):
    _inherit = 'note.openprod'
    
    
    #===========================================================================
    # COLUMNS
    #===========================================================================
    nonconformity_file_id = fields.Many2one('nonconformity.file', string='Nonconformity', required=False, ondelete='cascade')
    
    
class document_openprod(models.Model):
    _inherit = 'document.openprod'
    
    
    def find_product_search_args(self):
        """
            Fonction qui permet de chercher les ids des produits liés au document
        """
        search_args = [('pdf_file', '=', self.id), ('type', 'in', ('pdf_receipt', 'pdf_delivery'))]
        return search_args
    
    
    def find_product_ids(self):
        """
            Fonction qui permet de chercher les ids des produits liés au document
        """
        product_ids = super(document_openprod, self).find_product_ids()
        #On récupère les ids des produits liés à ce document via les documents imprimés
        search_args = self.find_product_search_args()
        printed_documents = self.env['stock.quality.control'].search_read(search_args, ['product_id'])
        if printed_documents:
            product_ids += [document['product_id'][0] for document in printed_documents 
                                     if document['product_id'] and isinstance(document['product_id'][0], int)]
                
        return product_ids
    
    
    def update_link_objects(self, new_document_id=False, datas=False):
        """
            On recherche tous les documents imprimés liés à l'ancienne
            version du document et on remplace par la nouvelle version
        """
        super(document_openprod, self).update_link_objects(new_document_id=new_document_id, datas=datas)
        search_args = [('pdf_file', '=', self.id)]
        if datas:
            if datas.get('product_ids'):
                search_args += [('product_id', 'in', datas['product_ids'].ids)]
            else:
                return True
            
        document = self.env['stock.quality.control'].search(search_args)
        document.write({'pdf_file': new_document_id})
        return True
    
    
    def find_picking_ids(self):
        """
            Fonction qui permet de chercher les ids des pickings liés au document
        """
        query = "SELECT move_id FROM move_document_openprod_rel WHERE document_id = %s"%(self.id) 
        self.env.cr.execute(query)
        move_ids = [x[0] for x in self.env.cr.fetchall()]  
        picking_read = self.env['stock.move'].browse(move_ids).read(['picking_id'])
        picking_ids = [x['picking_id'][0] for x in picking_read]
        return picking_ids
    
    
    @api.multi
    def show_picking_from_document(self):
        """
            Fonction qui cherche et retourne les picking liés à ce document
        """
        action_struc = {}
        for document in self:
            action_dict = get_form_view(self, 'stock.action_see_all_picking')
            picking_ids = document.find_picking_ids()
            picking_ids = list(set(picking_ids))
            if action_dict and action_dict.get('id') and action_dict.get('type'):
                action = self.env[action_dict['type']].browse(action_dict['id'])
                action_struc = action.read()
                action_struc[0]['domain'] = [('id', 'in', picking_ids)]
                action_struc = action_struc[0]
              
        return action_struc
